"""Upgrade a stopped legacy installation, preserving a restorable SQL backup.

MariaDB DDL commits implicitly. This migration is restartable, not transactional.
Conflicting records are rejected before any schema change; they are never discarded.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from db import transaction
from recruitment import skills

ROOT = Path(__file__).resolve().parents[1]
TABLES = ("Users", "Recruiter", "Client", "Job", "Application", "ClientSkill")


def identifier(value):
    return "`" + value.replace("`", "``") + "`"


def run_script(cur, filename):
    sql = (ROOT / "database" / filename).read_text(encoding="utf-8-sig")
    sql = re.sub(r"^USE mydb;\s*", "", sql, flags=re.MULTILINE)
    cur.execute(sql)
    while True:
        if cur.with_rows:
            cur.fetchall()
        if not cur.nextset():
            break


def columns(cur, table):
    cur.execute(f"SHOW COLUMNS FROM {identifier(table)}")
    return {row["Field"]: row for row in cur.fetchall()}


def reject(cur, query, message):
    cur.execute(query)
    if cur.fetchone():
        raise RuntimeError(
            message + " Resolve the conflicting records before migrating."
        )


def backup(cur, existing):
    directory = ROOT / ".local" / "backups"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"before-bcnf-{stamp}-{uuid4().hex[:8]}.sql"
    cur.execute("SELECT DATABASE() AS name")
    database = cur.fetchone()["name"]

    def portable_ddl(sql):
        sql = sql.replace(identifier(database) + ".", "")
        return re.sub(r"DEFINER=`[^`]*`@`[^`]*`\s*", "", sql)

    def literal(value):
        if value is None:
            return "NULL"
        if isinstance(value, int):
            return str(value)
        encoded = str(value).encode("utf-8").hex()
        return f"CONVERT(X'{encoded}' USING utf8mb4)"

    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write("-- Private backup: includes password hashes and personal data.\n")
        output.write(
            "-- Select a NEW EMPTY database before importing. No DROP commands.\n"
        )
        output.write("SET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\n")
        for table in existing:
            cur.execute(f"SHOW CREATE TABLE {identifier(table)}")
            output.write(cur.fetchone()["Create Table"] + ";\n")
            cur.execute(f"SELECT * FROM {identifier(table)}")
            for row in cur.fetchall():
                names = ",".join(identifier(name) for name in row)
                values = ",".join(literal(value) for value in row.values())
                output.write(
                    f"INSERT INTO {identifier(table)} ({names}) VALUES ({values});\n"
                )
        cur.execute("SHOW FULL TABLES WHERE Table_type='VIEW'")
        for row in cur.fetchall():
            name = next(iter(row.values()))
            cur.execute(f"SHOW CREATE VIEW {identifier(name)}")
            output.write(portable_ddl(cur.fetchone()["Create View"]) + ";\n")
        cur.execute("SHOW TRIGGERS")
        triggers = cur.fetchall()
        if triggers:
            output.write("DELIMITER //\n")
            for trigger in triggers:
                cur.execute(f"SHOW CREATE TRIGGER {identifier(trigger['Trigger'])}")
                output.write(
                    portable_ddl(cur.fetchone()["SQL Original Statement"]) + "//\n"
                )
            output.write("DELIMITER ;\n")
        output.write("SET FOREIGN_KEY_CHECKS=1;\n")
    return path


def migrate():
    with transaction() as cur:
        cur.execute(
            "SELECT GET_LOCK(CONCAT(DATABASE(), ':job-web-bcnf'), 0) AS acquired"
        )
        if cur.fetchone()["acquired"] != 1:
            raise RuntimeError("Another migration is running.")
        try:
            cur.execute("SHOW FULL TABLES WHERE Table_type='BASE TABLE'")
            present = {next(iter(row.values())).lower() for row in cur.fetchall()}
            if not {table.lower() for table in TABLES[:5]}.issubset(present):
                raise RuntimeError(
                    "Expected the five legacy recruitment tables. Use schema.sql for a new database."
                )
            cur.execute(
                "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND ENGINE <> 'InnoDB'"
            )
            if cur.fetchone():
                raise RuntimeError("All tables must use InnoDB before migration.")
            for table, email, name, role in (
                ("Recruiter", "REmail", "RName", "Recruiter"),
                ("Client", "CEmail", "CName", "Client"),
            ):
                reject(
                    cur,
                    f"SELECT 1 FROM {table} p LEFT JOIN Users u ON u.email=p.{email} WHERE u.email IS NULL OR u.type <> '{role}' LIMIT 1",
                    f"{table} has a missing or wrong-role account.",
                )
                if name in columns(cur, table):
                    reject(
                        cur,
                        f"SELECT 1 FROM {table} p JOIN Users u ON u.email=p.{email} WHERE BINARY p.{name} <> BINARY u.name LIMIT 1",
                        f"{table} and Users names disagree.",
                    )
            reject(
                cur,
                "SELECT 1 FROM Application GROUP BY CID,JID HAVING COUNT(*)>1 LIMIT 1",
                "Duplicate client/job applications exist.",
            )
            application_columns = columns(cur, "Application")
            if "RID" in application_columns:
                reject(
                    cur,
                    "SELECT 1 FROM Application a JOIN Job j ON j.JID=a.JID WHERE a.RID<>j.RID LIMIT 1",
                    "An application names the wrong recruiter.",
                )
            client_columns = columns(cur, "Client")
            reject(
                cur,
                "SELECT 1 FROM Users WHERE type NOT IN ('Recruiter','Client') LIMIT 1",
                "Invalid account role.",
            )
            backup_path = backup(
                cur, [table for table in TABLES if table.lower() in present]
            )
            print(f"Backup created: {backup_path.relative_to(ROOT)}")

            # Equalize profile email domains before adding account foreign keys.
            cur.execute("SHOW FULL COLUMNS FROM Users LIKE 'email'")
            email_collation = cur.fetchone()["Collation"]
            if not re.fullmatch(r"[a-zA-Z0-9_]+", email_collation or ""):
                raise RuntimeError("Unsupported email collation.")
            charset = email_collation.split("_")[0]
            for table, email, name, constraint in (
                ("Recruiter", "REmail", "RName", "fk_recruiter_user"),
                ("Client", "CEmail", "CName", "fk_client_user"),
            ):
                cur.execute(
                    "SELECT 1 FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s AND REFERENCED_TABLE_NAME='Users'",
                    (table, email),
                )
                if not cur.fetchone():
                    cur.execute(
                        f"ALTER TABLE {table} MODIFY {email} VARCHAR(120) CHARACTER SET {charset} COLLATE {email_collation} NOT NULL, ADD CONSTRAINT {constraint} FOREIGN KEY ({email}) REFERENCES Users(email)"
                    )
                if name in columns(cur, table):
                    cur.execute(f"ALTER TABLE {table} DROP COLUMN {name}")

            # Reuse the canonical ClientSkill definition; no parallel schema constants.
            schema = (ROOT / "database/schema.sql").read_text(encoding="utf-8-sig")
            definition = re.search(
                r"CREATE TABLE IF NOT EXISTS ClientSkill \(.*?;", schema, re.DOTALL
            ).group()
            cur.execute(definition)
            if "CSkills" in client_columns:
                cur.execute("SELECT CID,CSkills FROM Client")
                for row in cur.fetchall():
                    for skill in skills(row["CSkills"]):
                        cur.execute(
                            "INSERT INTO ClientSkill (CID,Skill) VALUES (%s,%s) ON DUPLICATE KEY UPDATE Skill=VALUES(Skill)",
                            (row["CID"], skill),
                        )
                cur.execute("ALTER TABLE Client DROP COLUMN CSkills")

            for name in (
                "job_web_application_owner_insert",
                "job_web_application_owner_update",
            ):
                cur.execute(f"DROP TRIGGER IF EXISTS {name}")
            if "RID" in application_columns:
                cur.execute(
                    "SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='Application' AND COLUMN_NAME='RID' AND REFERENCED_TABLE_NAME IS NOT NULL"
                )
                for row in cur.fetchall():
                    cur.execute(
                        f"ALTER TABLE Application DROP FOREIGN KEY {identifier(row['CONSTRAINT_NAME'])}"
                    )
                cur.execute("ALTER TABLE Application DROP COLUMN RID")
            cur.execute(
                "SELECT 1 FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='Application' AND INDEX_NAME='uq_application_client_job'"
            )
            if not cur.fetchone():
                cur.execute(
                    "ALTER TABLE Application ADD CONSTRAINT uq_application_client_job UNIQUE (CID,JID)"
                )
            password_type = columns(cur, "Users")["password"]["Type"]
            width = re.fullmatch(r"varchar\((\d+)\)", password_type, re.IGNORECASE)
            if width and int(width.group(1)) < 255:
                cur.execute("ALTER TABLE Users MODIFY password VARCHAR(255) NULL")
            run_script(cur, "views.sql")
            run_script(cur, "triggers.sql")
            print(
                "BCNF migration complete. Existing IDs, accounts, jobs and applications retained."
            )
        finally:
            cur.execute("SELECT RELEASE_LOCK(CONCAT(DATABASE(), ':job-web-bcnf'))")
            cur.fetchone()


if __name__ == "__main__":
    print("Run only while all application servers and database writers are stopped.")
    migrate()
