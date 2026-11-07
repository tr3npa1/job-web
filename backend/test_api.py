"""Offline boundary/security tests. These do not claim live MariaDB coverage."""

import os
import unittest
from unittest.mock import patch
from mysql.connector import Error

os.environ.setdefault("SECRET_KEY", "unit-test-secret-not-for-deployment-12345")
from app import app
import recruitment as r
from db import transaction

HEADERS = {"X-Requested-With": "job-web", "Origin": "http://127.0.0.1:5173"}
CLIENT = {
    "name": "Client",
    "email": "client@example.com",
    "type": "client",
    "profile": {"CID": 1},
}
RECRUITER = {
    "name": "Recruiter",
    "email": "recruiter@example.com",
    "type": "recruiter",
    "profile": {"RID": 2},
}


class ApiTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY="test-only")
        self.client = app.test_client()

    def test_anonymous_protected_endpoints(self):
        for path in ("/api/me", "/api/jobs", "/api/applications"):
            self.assertEqual(self.client.get(path).status_code, 401)

    def test_csrf_header_required(self):
        self.assertEqual(self.client.post("/api/login", json={}).status_code, 403)

    def test_untrusted_origin(self):
        self.assertEqual(
            self.client.post(
                "/api/login",
                json={},
                headers={**HEADERS, "Origin": "https://evil.example"},
            ).status_code,
            403,
        )

    def test_json_object_required(self):
        self.assertEqual(
            self.client.post("/api/login", json=[], headers=HEADERS).status_code, 400
        )

    def test_login_and_logout_session(self):
        with patch("app.service.login", return_value=CLIENT):
            self.assertEqual(
                self.client.post("/api/login", json={}, headers=HEADERS).status_code,
                200,
            )
        with self.client.session_transaction() as session:
            self.assertEqual(session["email"], CLIENT["email"])
        self.assertEqual(
            self.client.post("/api/logout", json={}, headers=HEADERS).status_code, 200
        )
        self.assertEqual(self.client.get("/api/me").status_code, 401)

    def test_database_failure_is_sanitized(self):
        with patch("app.transaction", side_effect=Error("secret connection detail")):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret", response.get_data(as_text=True))

    def test_wrong_role_cannot_create_job(self):
        with patch("app.user", return_value=CLIENT):
            self.assertEqual(
                self.client.post("/api/jobs", json={}, headers=HEADERS).status_code, 403
            )

    def test_wrong_role_cannot_apply(self):
        with patch("app.user", return_value=RECRUITER):
            self.assertEqual(
                self.client.post(
                    "/api/jobs/1/apply", json={}, headers=HEADERS
                ).status_code,
                403,
            )

    def test_password_confirmation(self):
        with self.assertRaises(r.Problem):
            r.register(
                {
                    "name": "Test",
                    "email": "test@example.com",
                    "password": "one",
                    "confirm": "two",
                }
            )

    def test_integer_bounds_and_injection(self):
        for value in (
            "-1",
            "1.2",
            "1; DROP TABLE Job",
            2147483648,
            True,
            "9" * 5000,
            None,
            [],
            "²",
        ):
            with self.assertRaises(r.Problem):
                r.number({"Salary": value}, "Salary")

    def test_job_delete_checks_owner_before_any_delete(self):
        with patch("recruitment.transaction") as tx:
            cursor = tx.return_value.__enter__.return_value
            cursor.fetchone.return_value = None
            with self.assertRaises(r.Problem) as error:
                r.delete_job(RECRUITER, 99)
            self.assertEqual(error.exception.status, 404)
            self.assertEqual(cursor.execute.call_count, 1)
            self.assertEqual(cursor.execute.call_args.args[1], (99, 2))

    def test_duplicate_application_rejected(self):
        with patch("recruitment.transaction") as tx:
            cursor = tx.return_value.__enter__.return_value
            cursor.fetchone.side_effect = [{"RID": 2}, {"AID": 5}]
            with self.assertRaises(r.Problem) as error:
                r.apply(CLIENT, 99)
            self.assertEqual(error.exception.status, 409)
            self.assertEqual(cursor.execute.call_count, 2)

    def test_withdraw_scopes_client(self):
        with patch("recruitment.transaction") as tx:
            cursor = tx.return_value.__enter__.return_value
            cursor.rowcount = 0
            with self.assertRaises(r.Problem):
                r.withdraw(CLIENT, 99)
            self.assertEqual(cursor.execute.call_args.args[1], (99, 1))

    def test_legacy_password_upgraded(self):
        with patch("recruitment.transaction") as tx, patch(
            "recruitment.profile", return_value=CLIENT
        ):
            cursor = tx.return_value.__enter__.return_value
            cursor.fetchone.return_value = {"password": "legacy"}
            self.assertEqual(
                r.login({"email": CLIENT["email"], "password": "legacy"}), CLIENT
            )
            stored = cursor.execute.call_args.args[1][0]
            self.assertNotEqual(stored, "legacy")
            self.assertTrue(r.check_password_hash(stored, "legacy"))

    def test_transaction_commit_close(self):
        with patch("db.mysql.connector.connect") as connect:
            with transaction():
                pass
            connect.return_value.commit.assert_called_once()
            connect.return_value.close.assert_called_once()

    def test_transaction_failure_rollback_close(self):
        with patch("db.mysql.connector.connect") as connect:
            with self.assertRaises(RuntimeError):
                with transaction():
                    raise RuntimeError("failure")
            connect.return_value.rollback.assert_called_once()
            connect.return_value.commit.assert_not_called()
            connect.return_value.close.assert_called_once()

    def test_unexpected_error_is_json(self):
        with patch("app.transaction", side_effect=RuntimeError("private detail")):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private detail", response.get_data(as_text=True))
        self.assertIn("error", response.json)

    def test_origin_allowlist_ignores_whitespace(self):
        with patch.dict(
            os.environ,
            {"ALLOWED_ORIGINS": "http://localhost:5173, http://127.0.0.1:5173"},
        ):
            response = self.client.post("/api/logout", json={}, headers=HEADERS)
        self.assertEqual(response.status_code, 200)

    def test_client_registration_binds_all_profile_values(self):
        data = dict(
            name="Test",
            email="client@example.test",
            password="secret",
            confirm="secret",
            type="client",
            gender="M",
            location="Pune",
            age=24,
            experience=2,
        )
        with patch("recruitment.transaction") as tx, patch(
            "recruitment.profile", return_value=CLIENT
        ):
            self.assertEqual(r.register(data), CLIENT)
            query, values = (
                tx.return_value.__enter__.return_value.execute.call_args.args
            )
            self.assertEqual(query.count("%s"), len(values))
            self.assertEqual(values[2], 24)

    def test_connection_closes_if_cursor_close_fails(self):
        with patch("db.mysql.connector.connect") as connect:
            connect.return_value.cursor.return_value.close.side_effect = RuntimeError(
                "close failed"
            )
            with self.assertRaises(RuntimeError):
                with transaction():
                    pass
            connect.return_value.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
