import os
import uuid
import random
from faker import Faker

fake = Faker()


def generate_organization(conn):
    org_id = str(uuid.uuid4())
    name = os.getenv("ORG_NAME", "NimbusFlow Inc.")
    domain = os.getenv("ORG_DOMAIN", "nimbusflow.com")

    conn.execute(
        "INSERT INTO organizations (org_id, name, domain) VALUES (?, ?, ?)",
        (org_id, name, domain),
    )
    return org_id


def generate_teams(conn, org_id):
    num_teams = int(os.getenv("NUM_TEAMS", "50"))
    teams = []

    # simple distribution over functions
    functions = (
        ["engineering"] * 20
        + ["marketing"] * 10
        + ["sales"] * 10
        + ["operations"] * 10
    )

    for i in range(num_teams):
        team_id = str(uuid.uuid4())
        function = functions[i % len(functions)]
        if function == "engineering":
            name = f"Eng – {fake.color_name()} Squad"
        elif function == "marketing":
            name = f"Marketing – {fake.word().title()} Campaigns"
        elif function == "sales":
            name = f"Sales – {fake.word().title()} Region"
        else:
            name = f"Ops – {fake.word().title()} Team"

        conn.execute(
            """
            INSERT INTO teams (team_id, org_id, name, function)
            VALUES (?, ?, ?, ?)
            """,
            (team_id, org_id, name, function),
        )
        teams.append({"team_id": team_id, "function": function})

    return teams


def generate_users(conn, org_id, teams):
    num_users = int(os.getenv("NUM_USERS", "500"))
    domain = os.getenv("ORG_DOMAIN", "nimbusflow.com")

    users = []
    team_ids = [t["team_id"] for t in teams]

    for _ in range(num_users):
        user_id = str(uuid.uuid4())
        first = fake.first_name()
        last = fake.last_name()
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}@{domain}"

        title = random.choice(
            [
                "Product Manager",
                "Backend Engineer",
                "Frontend Engineer",
                "Data Scientist",
                "Marketing Manager",
                "Content Strategist",
                "Sales Executive",
                "Customer Success Manager",
                "Operations Analyst",
            ]
        )
        timezone = random.choice(["UTC", "US/Pacific", "US/Eastern", "Europe/Berlin", "Asia/Kolkata"])

        conn.execute(
            """
            INSERT INTO users (user_id, org_id, name, email, title, timezone)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, org_id, name, email, title, timezone),
        )

        users.append(
            {
                "user_id": user_id,
                "title": title,
            }
        )

        # assign user to 1–2 teams
        memberships = random.sample(team_ids, k=random.choice([1, 1, 2]))
        for team_id in memberships:
            conn.execute(
                """
                INSERT INTO team_memberships (team_id, user_id)
                VALUES (?, ?)
                """,
                (team_id, user_id),
            )

    return users
