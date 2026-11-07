"""Explicit live integration check. Uses unique fixtures and removes only its own data.

Run against a development database after importing schema, views and triggers.
The API must use the same database configuration as this script.
No mocked connection is used. Requires the configured DB user to administer fixtures.
"""

import argparse
import concurrent.futures
import http.cookiejar
import json
import secrets
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import mysql.connector

from db import transaction

BASE = "http://127.0.0.1:5173/api"
TAG = "qa" + uuid.uuid4().hex[:12]
PASSWORD = secrets.token_urlsafe(24)


class Browser:
    def __init__(self):
        self.open = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        ).open

    def request(self, path, method="GET", data=None, status=200):
        parts = urlsplit(BASE)
        headers = {
            "X-Requested-With": "job-web",
            "Origin": f"{parts.scheme}://{parts.netloc}",
        }
        body = None
        if method != "GET":
            headers["Content-Type"] = "application/json"
            body = json.dumps(data or {}).encode()
        req = urllib.request.Request(
            BASE + path, data=body, headers=headers, method=method
        )
        try:
            response = self.open(req, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            payload = json.loads(response.read())
        assert response.status == status, (path, response.status, payload)
        return payload


def run():
    owner, other, client, second = Browser(), Browser(), Browser(), Browser()
    fixtures = []

    def register(browser, role, suffix):
        email = f"{TAG}{suffix}@example.test"
        fixtures.append(email)
        data = dict(
            name="QA " + suffix,
            email=email,
            password=PASSWORD,
            confirm=PASSWORD,
            type=role,
            gender="M",
            location="Pune",
            company="QA Company",
            age=24,
            experience=2,
            skills="Python, SQL",
            qualification="BE",
        )
        account = browser.request("/register", "POST", data, 201)["user"]
        with transaction() as cursor:
            cursor.execute("SELECT email FROM Users WHERE email=%s", (email,))
            assert (
                cursor.fetchone() is not None
            ), "API and test database configuration differ"
        return account

    try:
        assert Browser().request("/health")["database"] == "connected"
        Browser().request("/jobs", status=401)
        recruiter = register(owner, "recruiter", "owner")
        register(other, "recruiter", "other")
        candidate = register(client, "client", "client")
        register(second, "client", "second")
        job = dict(
            JobRole="QA Developer's role",
            JobType="FullTime",
            Qualification="BE",
            MinExp=1,
            Salary=50000,
        )
        jid = owner.request("/jobs", "POST", job, 201)["id"]
        assert any(j["JID"] == jid for j in client.request("/jobs")["jobs"])
        assert all(j["JID"] != jid for j in other.request("/jobs")["jobs"])
        other.request(f"/jobs/{jid}", "DELETE", status=404)
        client.request("/jobs", "POST", job, 403)
        owner.request(f"/jobs/{jid}/apply", "POST", status=403)
        aid = client.request(f"/jobs/{jid}/apply", "POST", status=201)["id"]
        client.request(f"/jobs/{jid}/apply", "POST", status=409)
        assert any(
            a["AID"] == aid for a in owner.request("/applications")["applications"]
        )
        assert not other.request("/applications")["applications"]
        second.request(f"/applications/{aid}", "DELETE", status=404)
        with transaction() as cur:
            cur.execute(
                "SELECT ApplicationCount FROM job_web_activity WHERE JID=%s", (jid,)
            )
            assert cur.fetchone()["ApplicationCount"] == 1
        # Execute the actual demonstration script with real records available.
        statements = 0
        with transaction() as cur:
            cur.execute(
                (Path(__file__).parents[1] / "database/queries.sql").read_text(
                    encoding="utf-8"
                )
            )
            while True:
                if cur.with_rows:
                    cur.fetchall()
                statements += 1
                if not cur.nextset():
                    break
        print(f"PASS: demonstration SQL ({statements} statements), view with live data")
        # Constraints protect direct SQL writers, independently of the API.
        for sql, values, expected in [
            (
                "INSERT INTO Application (JID,CID) VALUES (%s,%s)",
                (jid, candidate["profile"]["CID"]),
                1062,
            ),
            (
                "INSERT INTO Application (JID,CID) VALUES (%s,%s)",
                (-1, candidate["profile"]["CID"]),
                1452,
            ),
        ]:
            try:
                with transaction() as cur:
                    cur.execute(sql, values)
            except mysql.connector.Error as error:
                assert error.errno == expected
            else:
                raise AssertionError("Database constraint did not reject invalid data")
        with transaction() as cur:
            cur.execute(
                "SELECT Skill FROM ClientSkill WHERE CID=%s ORDER BY Skill",
                (candidate["profile"]["CID"],),
            )
            assert [row["Skill"] for row in cur.fetchall()] == ["Python", "SQL"]
            for table, removed in [
                ("Application", "RID"),
                ("Client", "CSkills"),
                ("Client", "CName"),
                ("Recruiter", "RName"),
            ]:
                cur.execute(
                    "SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s",
                    (table, removed),
                )
                assert cur.fetchone() is None, (table, removed)
        # All five role guards reject mismatched profiles or role changes.
        for sql, values in [
            (
                "INSERT INTO Recruiter (REmail,CompanyName,CompanyLocation,RGender) VALUES (%s,'QA','Pune','M')",
                (candidate["email"],),
            ),
            (
                "INSERT INTO Client (CEmail,CAge,CLocation,CGender,CExp,CQualification) VALUES (%s,24,'Pune','M',0,'BE')",
                (recruiter["email"],),
            ),
            (
                "UPDATE Recruiter SET REmail=%s WHERE RID=%s",
                (candidate["email"], recruiter["profile"]["RID"]),
            ),
            (
                "UPDATE Client SET CEmail=%s WHERE CID=%s",
                (recruiter["email"], candidate["profile"]["CID"]),
            ),
            ("UPDATE Users SET type='Recruiter' WHERE email=%s", (candidate["email"],)),
        ]:
            try:
                with transaction() as cur:
                    cur.execute(sql, values)
            except mysql.connector.Error as error:
                assert error.errno == 1644
            else:
                raise AssertionError("Role trigger did not reject invalid data")
        client.request(f"/applications/{aid}", "DELETE")

        # Simultaneous submissions via independent HTTP sessions.
        def concurrent_apply(_):
            browser = Browser()
            browser.request(
                "/login", "POST", dict(email=candidate["email"], password=PASSWORD)
            )
            try:
                browser.request(f"/jobs/{jid}/apply", "POST", status=201)
                return 201
            except AssertionError as error:
                assert error.args[0][1] == 409, error
                return 409

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(concurrent_apply, range(2))) == [201, 409]
        owner.request(f"/jobs/{jid}", "DELETE")
        assert not client.request("/applications")["applications"]
        # Existing plaintext passwords are accepted, then hashed in place.
        with transaction() as cur:
            cur.execute(
                "UPDATE Users SET password=%s WHERE email=%s",
                ("legacy-test", candidate["email"]),
            )
        client.request("/logout", "POST")
        client.request("/me", status=401)
        client.request(
            "/login", "POST", dict(email=candidate["email"], password="legacy-test")
        )
        with transaction() as cur:
            cur.execute(
                "SELECT password FROM Users WHERE email=%s", (candidate["email"],)
            )
            assert cur.fetchone()["password"].startswith("scrypt:")
        # A failure after multiple writes rolls back the whole transaction.
        orphan = f"{TAG}orphan@example.test"
        fixtures.append(orphan)
        try:
            with transaction() as cur:
                cur.execute(
                    "INSERT INTO Users (name,email,type,password) VALUES ('QA',%s,'Recruiter','test-only')",
                    (orphan,),
                )
                cur.execute(
                    "INSERT INTO Recruiter (REmail,CompanyName,CompanyLocation,RGender) VALUES (%s,'QA','Pune','M')",
                    (orphan,),
                )
                raise RuntimeError("Intentional rollback check")
        except RuntimeError as error:
            assert str(error) == "Intentional rollback check"
        with transaction() as cur:
            cur.execute("SELECT email FROM Users WHERE email=%s", (orphan,))
            assert cur.fetchone() is None
            cur.execute("SELECT RID FROM Recruiter WHERE REmail=%s", (orphan,))
            assert cur.fetchone() is None
        print(
            "PASS: registration, login/logout, role/ownership isolation, posting, browsing, application, withdrawal, deletion"
        )
        print(
            "PASS: concurrent duplicate prevention, database uniqueness, foreign keys, atomic skills, legacy password migration, rollback, five role triggers"
        )
    finally:
        with transaction() as cur:
            for email in fixtures:
                cur.execute(
                    "DELETE a FROM Application a JOIN Job j ON a.JID=j.JID LEFT JOIN Recruiter r ON j.RID=r.RID LEFT JOIN Client c ON a.CID=c.CID WHERE r.REmail=%s OR c.CEmail=%s",
                    (email, email),
                )
                cur.execute(
                    "DELETE j FROM Job j JOIN Recruiter r ON j.RID=r.RID WHERE r.REmail=%s",
                    (email,),
                )
                cur.execute("DELETE FROM Recruiter WHERE REmail=%s", (email,))
                cur.execute("DELETE FROM Client WHERE CEmail=%s", (email,))
                cur.execute("DELETE FROM Users WHERE email=%s", (email,))
        print("Cleaned only this run's uniquely named fixtures.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url", default=BASE, help="API URL for the development instance"
    )
    args = parser.parse_args()
    BASE = args.base_url.rstrip("/")
    if not __debug__:
        parser.error("Run without -O; integration assertions must be enabled.")
    run()
