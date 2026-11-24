"""Generate organization.json from the three CSVs in data/."""

import argparse
from collections import Counter
import csv
from datetime import date, datetime, timezone
import json
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parent


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        yield from csv.DictReader(source)


def split_list(value):
    return [part.strip() for part in value.split(";") if part.strip()]


def build_organization(data_dir, name, founded, timestamp):
    departments = {}
    for row in rows(data_dir / "departments.csv"):
        departments[row["id"]] = {
            "id": row["id"],
            "name": row["name"],
            "budget": float(row["budget"]),
            "employees": [],
            "projects": [],
        }

    skills = Counter()
    employee_ids = {}
    employee_count = total_years = 0
    for row in rows(data_dir / "employees.csv"):
        department_id = row["department_id"]
        employee = {
            "id": row["id"],
            "name": row["name"],
            "position": row["position"],
            "skills": split_list(row["skills"]),
            "years_of_service": int(row["years_of_service"]),
        }
        if employee["id"] in employee_ids:
            raise ValueError(f"Duplicate employee ID: {employee['id']}")
        employee_ids[employee["id"]] = department_id
        departments[department_id]["employees"].append(employee)
        skills.update(set(employee["skills"]))
        employee_count += 1
        total_years += employee["years_of_service"]

    statuses = Counter()
    for row in rows(data_dir / "projects.csv"):
        department_id = row["department_id"]
        members = split_list(row["member_ids"])
        for member in members:
            if employee_ids.get(member) != department_id:
                raise ValueError(f"Invalid member {member} for project {row['name']}")
        departments[department_id]["projects"].append({
            "name": row["name"],
            "status": row["status"],
            "members": members,
            "deadline": date.fromisoformat(row["deadline"]).isoformat(),
        })
        statuses[row["status"]] += 1

    return {
        "metadata": {
            "version": "1.0.0",
            "timestamp": timestamp,
            "generator": "generate_organization.py",
        },
        "organization": {
            "name": name,
            "founded": founded.isoformat(),
            "departments": list(departments.values()),
        },
        "statistics": {
            "averageDepartmentBudget": mean(d["budget"] for d in departments.values()),
            "totalEmployees": employee_count,
            "skillDistribution": dict(sorted(skills.items())),
            "departmentSizes": {
                d["name"]: len(d["employees"]) for d in departments.values()
            },
            "projectStatusDistribution": dict(sorted(statuses.items())),
            "averageYearsOfService": total_years / employee_count,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, default=ROOT / "organization.json")
    # The sample CSVs do not contain organization-level metadata.
    parser.add_argument("--name", default="Example Organization")
    parser.add_argument("--founded", type=date.fromisoformat, default=date(2000, 1, 1))
    parser.add_argument("--timestamp", type=datetime.fromisoformat,
                        help="Timezone-aware ISO timestamp; defaults to the current UTC time.")
    args = parser.parse_args()
    timestamp = args.timestamp or datetime.now(timezone.utc)
    if timestamp.utcoffset() is None:
        parser.error("--timestamp must include a time zone")
    timestamp = timestamp.astimezone(timezone.utc).isoformat(timespec="seconds")
    document = build_organization(args.data_dir, args.name, args.founded, timestamp)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
