# job-web

A recruitment management application built with React, Flask, and XAMPP MariaDB. The project migrates a desktop recruitment system to a web interface while retaining its database entities and recruiter/client workflows. It is intended for local development and university DBMS evaluation.

## Features

- Recruiter and client registration, sign-in, and sign-out.
- Recruiter-owned job postings and applicant lists.
- Job browsing, text search, employment-type filters, and sorting.
- Application submission, duplicate prevention, and withdrawal.
- Transactional registration and job deletion.
- Recruitment SQL examples covering joins, aggregates, subqueries, CTEs, views, and optional integrity triggers.

## Technology

| Component | Implementation |
| --- | --- |
| Frontend | React, Vite, JavaScript, native Fetch, plain CSS |
| Backend | Python, Flask, mysql.connector |
| Database | MySQL/MariaDB service supplied by XAMPP |
| Administration | phpMyAdmin |

```text
Browser / React → Vite API proxy → Flask → mysql.connector → XAMPP MariaDB
```

## Getting started

The supported setup uses Windows, PowerShell, Python 3.11+, Node.js 22.12+ or 24 LTS, and XAMPP with MariaDB 10.4+. Run the following commands from the repository root.

1. Start MySQL and Apache in XAMPP. In phpMyAdmin, import `database/schema.sql`, followed by `database/views.sql`. Back up an existing `mydb` before importing. Triggers are optional for normal use and required for the complete integration test.
2. Install dependencies:

   ```powershell
   python -m venv backend/.venv
   backend/.venv/Scripts/python -m pip install -r backend/requirements.txt
   npm.cmd --prefix frontend ci
   ```

3. Copy the configuration template **only if `backend/.env` does not exist**:

   ```powershell
   Copy-Item backend/.env.example backend/.env
   backend/.venv/Scripts/python -c "import secrets; print(secrets.token_hex(32))"
   ```

   Set the generated value as `SECRET_KEY` and configure the database account in `.env`. The example uses a dedicated `job_web` account; create it as described in [Setup](docs/SETUP.md), or supply an existing development account. Never commit `.env`.

4. Start the application in two terminals:

   ```powershell
   # Terminal 1, repository root
   backend/.venv/Scripts/python backend/app.py
   ```

   ```powershell
   # Terminal 2, repository root
   npm.cmd --prefix frontend run dev
   ```

Open [job-web](http://127.0.0.1:5173) and register an account. No sample users or jobs are installed. For full setup, optional process management, configuration, and troubleshooting, see [SETUP.md](docs/SETUP.md).

## Verification

```powershell
backend/.venv/Scripts/python -m unittest discover -s backend -p "test_*.py" -v
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

With Flask, Vite, and a development database running, and the view and optional triggers installed:

```powershell
backend/.venv/Scripts/python backend/verify_live.py
```

The live check creates uniquely named test records, exercises real HTTP and SQL operations, and removes its records afterward. Use a development database. Unit tests mock database boundaries; frontend tests exercise the HTTP client. Neither replaces integration or browser testing.

## Repository layout

```text
backend/     Flask routes, database access, recruitment logic, tests and launcher
frontend/    React source, static assets, package manifest and lockfile
database/   Schema, recruitment queries, view and optional triggers
docs/       Architecture, features and setup documentation
README.md
LICENSE
```

Database, backend, and frontend contributors can work within their respective directories. Coordinate schema and API changes across components and update the relevant documentation before integration.

## Documentation

- [Architecture](docs/ARCHITECTURE.md): request flow, API, schema, transactions, and design decisions.
- [Features](docs/FEATURES.md): supported roles and workflows.
- [Setup](docs/SETUP.md): fresh-machine installation, configuration, operation, and verification.

## Scope

The source application has no resume uploads, application statuses, date fields, job editing, or account recovery. Salary has no currency or period field. These limitations are retained rather than inferred from other recruitment products. The bundled Flask and Vite servers are for local development; publishing the source on GitHub does not deploy a production service.

## License and attribution

Distributed under the [MIT License](LICENSE). Adapted from [RaghavGupta2910/Hire-Me-Recruitment-Management-System](https://github.com/RaghavGupta2910/Hire-Me-Recruitment-Management-System), copyright © 2025 Raghav Gupta. The web implementation preserves the original recruitment tables and workflows; parameterized queries, sessions, password hashing, and transaction checks replace the desktop application's presentation-bound operations. `database/schema.sql` is the maintained schema definition.
