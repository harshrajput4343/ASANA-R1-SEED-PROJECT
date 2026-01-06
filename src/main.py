import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from src.generators.users import generate_organization, generate_teams, generate_users
from src.generators.projects import generate_projects, generate_sections
from src.generators.tasks import generate_tasks, generate_comments_and_metadata

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "output" / "asana_simulation.sqlite"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def run_schema(conn):
    with open(SCHEMA_PATH, "r") as f:
        sql = f.read()
    conn.executescript(sql)


def main():
    load_dotenv()

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH.as_posix())
    conn.execute("PRAGMA foreign_keys = ON;")

    run_schema(conn)

    org_id = generate_organization(conn)
    teams = generate_teams(conn, org_id)
    users = generate_users(conn, org_id, teams)

    projects = generate_projects(conn, org_id, teams)
    sections = generate_sections(conn, projects)

    tasks = generate_tasks(conn, projects, sections, users)

    generate_comments_and_metadata(conn, tasks, org_id, users)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
