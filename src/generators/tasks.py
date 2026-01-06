import os
import uuid
import random
from datetime import datetime, timedelta
from collections import defaultdict


def _random_created_at(date_range_months: int):
    now = datetime.utcnow()
    max_days = date_range_months * 30
    days_ago = random.randint(0, max_days)
    created = now - timedelta(days=days_ago)

    # bias towards Mon–Wed
    if created.weekday() >= 3:  # Thu, Fri, Sat, Sun
        created -= timedelta(days=random.randint(0, 2))
    return created


def _random_due_date(created_at: datetime):
    r = random.random()
    if r < 0.10:
        return None  # no due date

    if r < 0.35:
        delta_days = random.randint(1, 7)
    elif r < 0.75:
        delta_days = random.randint(8, 30)
    elif r < 0.95:
        delta_days = random.randint(31, 90)
    else:
        # overdue: due date before today but after created
        delta_days = random.randint(1, 30)

    due = created_at + timedelta(days=delta_days)

    # avoid weekend: move to Monday
    if due.weekday() == 5:  # Saturday
        due += timedelta(days=2)
    elif due.weekday() == 6:  # Sunday
        due += timedelta(days=1)

    return due


def _task_name(project_type: str):
    if project_type == "product_dev":
        return random.choice(
            [
                "Auth – Fix token refresh bug",
                "Billing – Implement proration logic",
                "Dashboard – Add usage analytics widget",
                "API – Improve rate limiting error messages",
                "Data – Backfill missing usage events",
            ]
        )
    if project_type == "marketing":
        return random.choice(
            [
                "Q2 Launch – Draft landing page copy",
                "SEO – Update pillar page internal links",
                "Email – Set up nurture sequence",
                "Webinar – Confirm speakers and schedule",
                "Social – Prepare launch announcement assets",
            ]
        )
    return random.choice(
        [
            "Onboarding – Update checklist for new hires",
            "Vendor – Review contract renewals",
            "Finance – Reconcile monthly invoices",
            "Support – Document escalation playbook",
        ]
    )


def _task_description(project_type: str):
    # simple varied-length descriptions
    r = random.random()
    if r < 0.2:
        return None
    if r < 0.7:
        return "Short task description with 1–3 sentences describing the work and expected outcome."
    return (
        "Detailed task description:\n"
        "- Context about the customer or feature.\n"
        "- Steps required to complete the work.\n"
        "- Acceptance criteria and edge cases.\n"
    )


def _completion_probability(project_type: str):
    # approximated from productivity benchmarks & typical sprint completion variance [web:18][web:21]
    if project_type == "product_dev":
        return random.uniform(0.7, 0.85)
    if project_type == "marketing":
        return random.uniform(0.6, 0.75)
    return random.uniform(0.4, 0.6)


def _priority():
    return random.choices(
        ["P0", "P1", "P2", "P3"],
        weights=[0.1, 0.25, 0.4, 0.25],
        k=1,
    )[0]


def generate_tasks(conn, projects, sections, users):
    tasks_per_project = int(os.getenv("TASKS_PER_PROJECT", "80"))
    date_range_months = int(os.getenv("DATE_RANGE_MONTHS", "6"))

    sections_by_project = defaultdict(list)
    for s in sections:
        sections_by_project[s["project_id"]].append(s)

    # map: project_id -> project_type
    proj_type = {p["project_id"]: p["project_type"] for p in projects}

    # simple mapping of project to users (by org scale; for simplicity, sample any user)
    user_ids = [u["user_id"] for u in users]

    tasks = []

    for project in projects:
        project_id = project["project_id"]
        project_type = project["project_type"]
        project_sections = sections_by_project[project_id]

        base_comp_prob = _completion_probability(project_type)

        parent_tasks = []

        for i in range(tasks_per_project):
            task_id = str(uuid.uuid4())
            created_at = _random_created_at(date_range_months)
            due_date = _random_due_date(created_at)

            # some tasks unassigned: 15–25% [web:21]
            if random.random() < 0.2:
                assignee_id = None
            else:
                assignee_id = random.choice(user_ids)

            # completion logic
            # older tasks more likely completed (approximate by time since creation) [web:18]
            age_days = (datetime.utcnow() - created_at).days
            age_factor = min(age_days / (date_range_months * 30), 1.0)
            p_complete = base_comp_prob * (0.5 + 0.5 * age_factor)
            completed = random.random() < p_complete

            completed_at = None
            if completed:
                if due_date:
                    latest = min(due_date, datetime.utcnow())
                else:
                    latest = datetime.utcnow()
                if latest <= created_at:
                    latest = created_at + timedelta(days=1)
                delta = random.randint(1, max(2, (latest - created_at).days))
                completed_at = created_at + timedelta(days=delta)

            name = _task_name(project_type)
            description = _task_description(project_type)
            priority = _priority()

            # section by status
            if completed:
                candidates = [s for s in project_sections if "Done" in s["name"] or "Launched" in s["name"] or "Completed" in s["name"]]
                if not candidates:
                    candidates = project_sections
            else:
                candidates = [s for s in project_sections if "Backlog" in s["name"] or "Planned" in s["name"] or "To Do" in s["name"]]
                if not candidates:
                    candidates = project_sections
            section = random.choice(candidates)
            section_id = section["section_id"]

            parent_task_id = None
            if random.random() < 0.25 and parent_tasks:
                parent_task_id = random.choice(parent_tasks)

            conn.execute(
                """
                INSERT INTO tasks
                (task_id, project_id, section_id, parent_task_id, name, description,
                 assignee_id, due_date, created_at, completed, completed_at, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    project_id,
                    section_id,
                    parent_task_id,
                    name,
                    description,
                    assignee_id,
                    due_date.isoformat() if due_date else None,
                    created_at.isoformat(timespec="seconds"),
                    int(completed),
                    completed_at.isoformat(timespec="seconds") if completed_at else None,
                    priority,
                ),
            )

            tasks.append(
                {
                    "task_id": task_id,
                    "project_id": project_id,
                    "project_type": project_type,
                }
            )

            if not parent_task_id:
                parent_tasks.append(task_id)

    return tasks


def generate_comments_and_metadata(conn, tasks, org_id, users):
    # tags
    tag_names = [
        "Customer Escalation",
        "Tech Debt",
        "Regression",
        "Launch Blocker",
        "Nice to Have",
        "Churn Risk",
        "Security",
        "Performance",
        "UX Feedback",
        "Internal Only",
    ]
    tags = []
    for name in tag_names:
        tag_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO tags (tag_id, org_id, name) VALUES (?, ?, ?)",
            (tag_id, org_id, name),
        )
        tags.append({"tag_id": tag_id, "name": name})

    # custom fields: Priority, Effort
    priority_field_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO custom_field_definitions (field_id, org_id, name, field_type, enum_options)
        VALUES (?, ?, ?, ?, ?)
        """,
        (priority_field_id, org_id, "Priority", "enum", '["P0","P1","P2","P3"]'),
    )

    effort_field_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO custom_field_definitions (field_id, org_id, name, field_type, enum_options)
        VALUES (?, ?, ?, ?, ?)
        """,
        (effort_field_id, org_id, "Effort", "number", None),
    )

    # comments & field values & tags
    for t in tasks:
        task_id = t["task_id"]

        # comments on 40% of tasks
        if random.random() < 0.4:
            n_comments = random.randint(1, 5)
            for _ in range(n_comments):
                comment_id = str(uuid.uuid4())
                body = random.choice(
                    [
                        "Added more details based on stakeholder feedback.",
                        "Please review before the end of sprint.",
                        "Blocked on dependency from another team.",
                        "Customer reported this again, increasing priority.",
                        "Updated acceptance criteria to cover edge cases.",
                    ]
                )
                created_at = datetime.utcnow() - timedelta(days=random.randint(0, 60))
                # Pick a random user from the users list
                user_id = random.choice(users)["user_id"]

                conn.execute(
                    """
                    INSERT INTO comments (comment_id, task_id, user_id, body, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (comment_id, task_id, user_id, body, created_at.isoformat(timespec="seconds")),
                )

        # custom field values
        effort = random.randint(1, 8)
        conn.execute(
            """
            INSERT OR REPLACE INTO custom_field_values (task_id, field_id, value_text, value_number)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, priority_field_id, None, None),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO custom_field_values (task_id, field_id, value_text, value_number)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, effort_field_id, None, float(effort)),
        )

        # tags: 0–3 tags per task
        if random.random() < 0.7:
            n_tags = random.randint(0, 3)
            for tag in random.sample(tags, k=n_tags):
                conn.execute(
                    """
                    INSERT OR IGNORE INTO task_tags (task_id, tag_id)
                    VALUES (?, ?)
                    """,
                    (task_id, tag["tag_id"]),
                )
