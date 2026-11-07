import os
from datetime import timedelta

from flask import Flask, jsonify, request, session
from mysql.connector import Error, IntegrityError
from werkzeug.exceptions import HTTPException

import recruitment as service
from db import transaction

secret_key = os.getenv("SECRET_KEY", "")
if len(secret_key.strip()) < 32:
    raise RuntimeError(
        "Set SECRET_KEY to a random value of at least 32 characters in backend/.env."
    )

app = Flask(__name__)
app.config.update(
    SECRET_KEY=secret_key,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE") == "true",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=16384,
)


@app.before_request
def csrf_check():
    if request.method in ("POST", "DELETE", "PUT", "PATCH"):
        if not request.is_json or request.headers.get("X-Requested-With") != "job-web":
            raise service.Problem("A JSON request from job-web is required.", 403)
        origin = request.headers.get("Origin")
        if origin and origin not in {
            value.strip()
            for value in os.getenv(
                "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
        }:
            raise service.Problem("Origin is not allowed.", 403)


@app.after_request
def headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.errorhandler(service.Problem)
def problem(error):
    return jsonify(error=error.message), error.status


@app.errorhandler(Error)
def database_error(error):
    app.logger.error("Database error code: %s", error.errno)
    if isinstance(error, IntegrityError):
        return (
            jsonify(error="This record already exists or conflicts with related data."),
            409,
        )
    return (
        jsonify(
            error="Database unavailable or schema not ready. Check XAMPP and database setup."
        ),
        503,
    )


@app.errorhandler(HTTPException)
def http_error(error):
    return jsonify(error=error.description), error.code


@app.errorhandler(Exception)
def unexpected_error(error):
    app.logger.exception("Unhandled request error")
    return jsonify(error="An unexpected server error occurred."), 500


def data():
    value = request.get_json()
    if not isinstance(value, dict):
        raise service.Problem("Expected a JSON object.")
    return value


def user():
    if "email" not in session:
        raise service.Problem("Please sign in.", 401)
    with transaction() as cur:
        return service.profile(cur, session["email"])


@app.get("/api/health")
def health():
    with transaction() as cur:
        cur.execute("SELECT 1 AS connected")
        cur.fetchone()
    return jsonify(status="ok", database="connected")


@app.get("/api/me")
def me():
    return jsonify(user=user())


@app.post("/api/<action>")
def authentication(action):
    if action == "logout":
        session.clear()
        return jsonify(message="Signed out.")
    if action not in ("login", "register"):
        raise service.Problem("Not found.", 404)
    account = service.login(data()) if action == "login" else service.register(data())
    session.clear()
    session["email"] = account["email"]
    session.permanent = True
    return jsonify(user=account), 201 if action == "register" else 200


@app.route("/api/jobs", methods=["GET", "POST"])
def jobs():
    account = user()
    if request.method == "GET":
        return jsonify(jobs=service.jobs(account))
    return jsonify(id=service.create_job(account, data())), 201


@app.delete("/api/jobs/<int:jid>")
def delete_job(jid):
    service.delete_job(user(), jid)
    return jsonify(message="Job and its applications deleted.")


@app.get("/api/applications")
def applications():
    return jsonify(applications=service.applications(user()))


@app.post("/api/jobs/<int:jid>/apply")
def apply(jid):
    return jsonify(id=service.apply(user(), jid)), 201


@app.delete("/api/applications/<int:aid>")
def withdraw(aid):
    service.withdraw(user(), aid)
    return jsonify(message="Application withdrawn.")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
