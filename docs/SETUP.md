# Setup

## Requirements

The supported local environment is Windows with PowerShell, Python 3.11 or later, Node.js 22.12+ or 24 LTS, and XAMPP containing MariaDB 10.4+. Commands below run from the repository root unless stated otherwise. The checkout may be located in any directory, including a path containing spaces.

Download XAMPP from [Apache Friends](https://www.apachefriends.org/). Install it independently of the repository and complete its installation or relocation procedure. XAMPP binaries, database storage, and local credentials are not part of the project.

## Database initialization

1. Start **MySQL** and **Apache** in the XAMPP control panel. XAMPP labels its MariaDB service MySQL. Apache is needed for phpMyAdmin, not for Flask.
2. Open [phpMyAdmin](http://localhost/phpmyadmin/). If Apache uses another port, include it in the URL.
3. If `mydb` already exists, export a backup before proceeding.
4. Import `database/schema.sql`. It creates the database and five tables if absent. New tables use InnoDB and utf8mb4. The script widens a legacy password column shorter than 255 characters without rewriting its values. It does not rebuild existing tables, change existing collations, or remove records.
5. Import `database/views.sql` to create `job_web_activity`. Existing views are left unchanged.
6. Optionally import `database/triggers.sql` once. Its two triggers enforce application/job recruiter consistency for direct Application writes. They are required for the full live test. A repeated import reports duplicate trigger names; inspect existing definitions rather than dropping them automatically.

The SQL targets the MariaDB service included with XAMPP. `CREATE VIEW IF NOT EXISTS` is MariaDB syntax. A standalone MySQL installation may require removing that clause after checking that the view does not already exist.

All tables must use InnoDB for foreign keys and transactional rollback. Inspect customized legacy schemas before importing. The scripts default to `mydb`; for another database name, adjust its declaration and `USE` statements in schema, views, and triggers, and set `DB_NAME` consistently. `queries.sql` uses the connection's selected database.

### Database account

Create a dedicated local account through phpMyAdmin's **User accounts** page with a password of your choice. Match the host to your connection (the example uses `127.0.0.1`) and grant `SELECT`, `INSERT`, `UPDATE`, and `DELETE` on `mydb`. The application does not require schema administration privileges. Use the administrator account to import SQL scripts.

For a separate development/test account, the full integration test additionally needs `CREATE TEMPORARY TABLES` and permission to select `job_web_activity`. The view executes with the caller's table permissions. Fresh XAMPP installations may have an empty root password, but existing credentials must not be reset to match an example.

## Dependencies

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements.txt
npm.cmd --prefix frontend ci
```

Using the virtual environment's interpreter directly avoids activation and execution-policy issues. If `venv` creates the interpreter but fails during pip installation, a host Python with pip can install into it:

```powershell
python -m pip --python backend/.venv/Scripts/python.exe install -r backend/requirements.txt
```

Direct Python dependencies are version-pinned. `npm ci` installs the frontend lockfile and fails if it does not match `package.json`. Both installation commands require access to their package registries.

## Configuration

If `.env` does not already exist:

```powershell
Copy-Item backend/.env.example backend/.env
backend/.venv/Scripts/python -c "import secrets; print(secrets.token_hex(32))"
```

Edit `.env`, set `SECRET_KEY` to the generated value, and supply the database account's settings. Do not overwrite an existing configuration. Flask reads this file relative to `backend/db.py`, independent of the current directory. Process environment variables take precedence.

| Variable | Purpose |
| --- | --- |
| `DB_HOST` | Database host; default `127.0.0.1` |
| `DB_PORT` | Database port; default `3306`, valid range 1–65535 |
| `DB_USER` | Database username; template suggests `job_web` |
| `DB_PASSWORD` | Password for that account |
| `DB_NAME` | Recruitment database; default `mydb` |
| `SECRET_KEY` | Required random session-signing secret, at least 32 characters |
| `ALLOWED_ORIGINS` | Comma-separated browser origins; defaults to localhost and 127.0.0.1 on port 5173 |
| `COOKIE_SECURE` | `false` for local HTTP; `true` only when serving over HTTPS |

Keep `.env` private. Changing `SECRET_KEY` invalidates existing cookies. The backend fails at startup if the secret is missing or too short. Omitted database credentials use the dedicated username `job_web` and an empty password; configure its actual password before connecting. Existing `.env` settings are not changed by application startup.

## Running the application

Start XAMPP MySQL first. Then open two terminals at the repository root:

```powershell
# Terminal 1
backend/.venv/Scripts/python backend/app.py
```

```powershell
# Terminal 2
npm.cmd --prefix frontend run dev
```

Open [job-web](http://127.0.0.1:5173). Flask listens only on `127.0.0.1:5000`; Vite listens on `127.0.0.1:5173` and forwards `/api` requests to Flask. Use one browser hostname consistently because cookies are host-specific.

Verify database connectivity:

```powershell
Invoke-RestMethod http://127.0.0.1:5173/api/health
```

Expected response: `status: ok`, `database: connected`. This checks connectivity, not schema completeness. Registration and the live tests verify the tables and workflows.

Stop each application server with Ctrl+C; stop MySQL/Apache through XAMPP when no longer needed.

### Optional Windows launcher

After dependencies, `.env`, database imports, and XAMPP startup are complete:

```powershell
powershell -ExecutionPolicy Bypass -File backend/local.ps1 start
powershell -ExecutionPolicy Bypass -File backend/local.ps1 stop
```

Run the second command when finished. The execution-policy flag applies only to that PowerShell process. The launcher starts Flask and Vite in hidden windows and stores logs/process records in the project's ignored `.local` directory. It resolves paths relative to itself, supports spaces, refuses occupied application ports, and cleans up its processes if startup fails. Stopping verifies recorded process identities before terminating their trees; unfinished requests may be interrupted and database connections roll back uncommitted work. XAMPP remains independently managed, so the script never assumes administrative database credentials or shuts down a shared database service.

### Build preview

```powershell
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run preview
```

Stop Vite development mode before starting preview: both use port 5173. Preview serves `frontend/dist` and forwards `/api` to the separately running Flask server. Neither server is a production deployment configuration.

## Tests

Offline checks:

```powershell
backend/.venv/Scripts/python -m unittest discover -s backend -p "test_*.py" -v
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

Backend tests cover request validation, authorization, ownership, password migration, and transaction cleanup using mocked database boundaries. Frontend tests use Node's built-in test runner to check Fetch requests and error handling; they are not full browser tests.

With the servers and a development database running, after importing the view and triggers:

```powershell
backend/.venv/Scripts/python backend/verify_live.py
```

The API and test process must use the same database configuration. The script creates uniquely named fixture records, verifies that they are visible through the configured database connection, then tests registration, authentication, posting, applications, withdrawal, deletion, concurrent duplicate prevention, rollback, the view, and both triggers. It also executes `queries.sql`, which includes a temporary-table DML exercise. Fixture cleanup runs on success or failure; an unavailable database can prevent cleanup. Do not run this against production data or with Python's `-O` flag.

For a different frontend address, pass `--base-url http://localhost:5173/api` and ensure the origin is allowed in backend configuration. The default tests use 127.0.0.1.

For manual evaluation, register a recruiter and a client, post a job, submit an application, inspect it as the recruiter, withdraw it as the client, and delete the test posting. Verify refresh persistence, filtering, empty states, and narrow layouts. The application starts without sample records.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Flask reports an invalid secret | Generate a random value and set `SECRET_KEY` in `backend/.env`. |
| Database error / HTTP 503 | Check XAMPP MySQL, host/port, account permissions, database name, and SQL imports. |
| Unknown table, column, or invalid data | Compare the installed schema to `schema.sql`; existing tables are not rebuilt by `IF NOT EXISTS`. |
| Account profile missing | Repair the legacy Users/profile relationship using verified account data and a backup. |
| Registration conflict | Email is unique in Users and the corresponding profile table; check for orphaned legacy profiles. |
| Browser cannot reach the API | Keep Flask on 5000 and Vite on 5173, or update both proxy and origin configuration together. |
| Session disappears | Use one hostname, keep the signing secret stable, and leave secure cookies disabled for local HTTP. |
| Launcher reports occupied ports | Stop the existing app process; the launcher will not take control of it. |
| Launcher fails its health check | Read `.local/flask-error.log` and `.local/vite-error.log`; verify XAMPP is already running. |
| Live tests report trigger/view errors | Import the optional triggers and view with an administrator; ensure the test account has the documented permissions. |
