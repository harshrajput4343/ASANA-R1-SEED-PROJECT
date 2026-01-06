import os
import uuid
import random
from datetime import date, timedelta


def _project_name(function):
    if function == "engineering":
        return random.choice(
            [
                "API Platform – Q1 Roadmap",
                "Billing Service – Reliability",
                "Auth Service – Hardening",
                "Data Pipeline – Refactor",
            ]
        )
    if function == "marketing":
        return random.choice(
            [
                "Product Launch – Q2 Campaign",
                "Content Calendar – Blog & SEO",
                "ABM – Enterprise Outreach",
                "Webinar Series – Customer Stories",
            ]
        )
    if function == "sales":
        return random.choice(
            [
                "Mid-Market Expansion Program",
                "Enterprise Pipeline – Q3",
                "Partner Co-Selling Motion",
            ]
        )
    return random.choice(
        [
            "Onboarding Process Improvement",
            "Vendor Management Program",
            "Internal Tools Rollout",
        ]
    )


def _project_type(function):
    if function == "engineering":
        return "product_dev"
    if function == "marketing":
        return "marketing"
    return "operations"


def generate_projects(conn, org_id, teams):
    projects_per_team = int(os.getenv("PROJECTS_PER_TEAM", "4"))

    today = date.today()
    projects = []

    for team in teams:
        for _ in range(projects_per_team):
            project_id = str(uuid.uuid4())
            name = _project_name(team["function"])
            project_type = _project_type(team["function"])

            start_offset_days = random.randint(0, 90)
            start_date = today - timedelta(days=start_offset_days)
            end_date = start_date + timedelta(days=random.randint(30, 120))

            description = f"{name} for {org_id}: {project_type} initiative."

            conn.execute(
                """
                INSERT INTO projects
                (project_id, org_id, team_id, name, description, project_type, start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    org_id,
                    team["team_id"],
                    name,
                    description,
                    project_type,
                    start_date.isoformat(),
                    end_date.isoformat(),
                ),
            )
            projects.append(
                {
                    "project_id": project_id,
                    "team_function": team["function"],
                    "project_type": project_type,
                }
            )

    return projects


def generate_sections(conn, projects):
    sections = []
    for proj in projects:
        if proj["project_type"] == "product_dev":
            names = ["Backlog", "In Progress", "In Review", "Done"]
        elif proj["project_type"] == "marketing":
            names = ["Planned", "In Production", "Scheduled", "Launched"]
        else:
            names = ["To Do", "In Progress", "Blocked", "Completed"]

        for position, name in enumerate(names):
            section_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO sections (section_id, project_id, name, position)
                VALUES (?, ?, ?, ?)
                """,
                (section_id, proj["project_id"], name, position),
            )
            sections.append(
                {
                    "section_id": section_id,
                    "project_id": proj["project_id"],
                    "name": name,
                }
            )

    return sections
