"""Adapted from the original register/client/recruiter SQL workflows (see LICENSE).

Tkinter state is replaced by explicit arguments. The normalized schema retains
the workflows and response fields through joins, aliases and transactions.
"""

import hmac
import re
from werkzeug.security import generate_password_hash, check_password_hash
from db import transaction


def skills(value):
    """The form accepts comma-separated skills; storage contains one skill per row."""
    return sorted({item.strip() for item in value.split(",") if item.strip()})


CLIENT_COLUMNS = """c.*, u.name AS CName,
    COALESCE((SELECT GROUP_CONCAT(s.Skill ORDER BY s.Skill SEPARATOR ', ')
              FROM ClientSkill s WHERE s.CID=c.CID), '') AS CSkills"""


class Problem(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


def string(data, key, limit=45, optional=False):
    value = data.get(key, "")
    if not isinstance(value, str):
        raise Problem(f"{key} must be text.")
    value = value.strip() if key not in ("password", "confirm") else value
    if not value and not optional:
        raise Problem(f"{key} is required.")
    if len(value) > limit:
        raise Problem(f"{key} must be at most {limit} characters.")
    return value


def number(data, key, minimum=0, maximum=2147483647):
    value = data.get(key, "")
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise Problem(f"{key} must be an integer.")
    value = str(value)
    if (
        len(value) > 10
        or not re.fullmatch(r"[0-9]+", value)
        or not minimum <= int(value) <= maximum
    ):
        raise Problem(f"{key} must be an integer from {minimum} to {maximum}.")
    return int(value)


def profile(cur, email):
    cur.execute("SELECT name,email,type FROM Users WHERE email=%s", (email,))
    user = cur.fetchone()
    if not user:
        raise Problem("Please sign in.", 401)
    user["type"] = user["type"].lower()
    if user["type"] not in ("recruiter", "client"):
        raise Problem(
            "Account role is invalid. Contact the database administrator.", 409
        )
    if user["type"] == "recruiter":
        cur.execute(
            "SELECT r.*,u.name AS RName FROM Recruiter r JOIN Users u ON u.email=r.REmail WHERE r.REmail=%s",
            (email,),
        )
    else:
        cur.execute(
            f"SELECT {CLIENT_COLUMNS} FROM Client c JOIN Users u ON u.email=c.CEmail WHERE c.CEmail=%s",
            (email,),
        )
    user["profile"] = cur.fetchone()
    if not user["profile"]:
        raise Problem(
            "Account profile is missing. Contact the database administrator.", 409
        )
    return user


def register(data):
    name, email = string(data, "name"), string(data, "email", 120)
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise Problem("Enter a valid email address.")
    password = string(data, "password", 256)
    if password != string(data, "confirm", 256):
        raise Problem("Passwords do not match.")
    role, gender = string(data, "type"), string(data, "gender", 2)
    if role not in ("recruiter", "client") or gender not in ("M", "F"):
        raise Problem("Choose a valid role and gender.")
    location = string(data, "location")
    if role == "recruiter":
        values = (email, string(data, "company"), location, gender)
        query = "INSERT INTO Recruiter (REmail,CompanyName,CompanyLocation,RGender) VALUES (%s,%s,%s,%s)"
    else:
        values = (
            email,
            number(data, "age", 1, 150),
            location,
            gender,
            number(data, "experience"),
            string(data, "qualification", optional=True),
        )
        client_skills = skills(string(data, "skills", optional=True))
        query = "INSERT INTO Client (CEmail,CAge,CLocation,CGender,CExp,CQualification) VALUES (%s,%s,%s,%s,%s,%s)"
    with transaction() as cur:
        cur.execute(
            "INSERT INTO Users (name,email,type,password) VALUES (%s,%s,%s,%s)",
            (name, email, role.title(), generate_password_hash(password)),
        )
        cur.execute(query, values)
        if role == "client" and client_skills:
            cid = cur.lastrowid
            cur.executemany(
                "INSERT INTO ClientSkill (CID,Skill) VALUES (%s,%s)",
                [(cid, skill) for skill in client_skills],
            )
        return profile(cur, email)


def login(data):
    email, password = string(data, "email", 120), string(data, "password", 256)
    with transaction() as cur:
        cur.execute("SELECT password FROM Users WHERE email=%s FOR UPDATE", (email,))
        row = cur.fetchone()
        stored = row["password"] if row else None
        # Original passwords fit VARCHAR(45), including ones that resemble a hash prefix.
        hashed = bool(
            stored and len(stored) > 45 and stored.startswith(("scrypt:", "pbkdf2:"))
        )
        try:
            valid = bool(stored) and (
                check_password_hash(stored, password)
                if hashed
                else hmac.compare_digest(stored.encode(), password.encode())
            )
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise Problem("Invalid email or password.", 401)
        if not hashed:
            cur.execute(
                "UPDATE Users SET password=%s WHERE email=%s",
                (generate_password_hash(password), email),
            )
        return profile(cur, email)


def require(user, role):
    if user["type"] != role:
        raise Problem("This action is not available for your account.", 403)


def jobs(user):
    with transaction() as cur:
        query = """SELECT j.*,r.CompanyName,r.CompanyLocation,
                   (SELECT COUNT(*) FROM Application a WHERE a.JID=j.JID) AS application_count
                   FROM Job j JOIN Recruiter r ON j.RID=r.RID"""
        params = ()
        if user["type"] == "recruiter":
            query += " WHERE j.RID=%s"
            params = (user["profile"]["RID"],)
        cur.execute(query + " ORDER BY j.JID DESC", params)
        return cur.fetchall()


def create_job(user, data):
    require(user, "recruiter")
    kind = string(data, "JobType")
    if kind not in ("FullTime", "PartTime", "Intern"):
        raise Problem("Choose a valid job type.")
    values = (
        user["profile"]["RID"],
        string(data, "JobRole"),
        kind,
        string(data, "Qualification"),
        number(data, "MinExp"),
        number(data, "Salary"),
    )
    with transaction() as cur:
        cur.execute(
            "INSERT INTO Job (RID,JobRole,JobType,Qualification,MinExp,Salary) VALUES (%s,%s,%s,%s,%s,%s)",
            values,
        )
        return cur.lastrowid


def delete_job(user, jid):
    require(user, "recruiter")
    with transaction() as cur:
        cur.execute(
            "SELECT JID FROM Job WHERE JID=%s AND RID=%s FOR UPDATE",
            (jid, user["profile"]["RID"]),
        )
        if not cur.fetchone():
            raise Problem("Job not found.", 404)
        cur.execute("DELETE FROM Application WHERE JID=%s", (jid,))
        cur.execute("DELETE FROM Job WHERE JID=%s", (jid,))


def applications(user):
    with transaction() as cur:
        if user["type"] == "recruiter":
            cur.execute(
                f"""SELECT a.AID,j.JobRole,{CLIENT_COLUMNS} FROM Application a
                JOIN Client c ON a.CID=c.CID JOIN Users u ON u.email=c.CEmail
                JOIN Job j ON a.JID=j.JID
                WHERE j.RID=%s ORDER BY a.AID DESC""",
                (user["profile"]["RID"],),
            )
        else:
            cur.execute(
                """SELECT a.AID,j.*,r.CompanyName,r.CompanyLocation FROM Application a
                JOIN Job j ON a.JID=j.JID JOIN Recruiter r ON j.RID=r.RID
                WHERE a.CID=%s ORDER BY a.AID DESC""",
                (user["profile"]["CID"],),
            )
        return cur.fetchall()


def apply(user, jid):
    require(user, "client")
    with transaction() as cur:
        # Same parent lock as deletion; serializes duplicate submissions via this API.
        cur.execute("SELECT RID FROM Job WHERE JID=%s FOR UPDATE", (jid,))
        job = cur.fetchone()
        if not job:
            raise Problem("Job not found.", 404)
        cid = user["profile"]["CID"]
        cur.execute(
            "SELECT AID FROM Application WHERE CID=%s AND JID=%s FOR UPDATE", (cid, jid)
        )
        if cur.fetchone():
            raise Problem("You have already applied to this job.", 409)
        cur.execute(
            "INSERT INTO Application (JID,CID) VALUES (%s,%s)",
            (jid, cid),
        )
        return cur.lastrowid


def withdraw(user, aid):
    require(user, "client")
    with transaction() as cur:
        cur.execute(
            "DELETE FROM Application WHERE AID=%s AND CID=%s",
            (aid, user["profile"]["CID"]),
        )
        if not cur.rowcount:
            raise Problem("Application not found.", 404)
