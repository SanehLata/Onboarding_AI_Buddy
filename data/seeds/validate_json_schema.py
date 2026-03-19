# validate_json_schema.py
# @Author: Saneh Lata
# Standalone JSON schema validator — run before gen_db.py and at any time
# after editing teams.json, systems.json, or dl_groups.json.
#
# Usage:
#   python data/seeds/validate_json_schema.py
#
# Returns exit code 0 if all files are valid, 1 if any errors are found.
# Safe to run repeatedly — does not touch the database.

import sys
import json
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR       = Path(__file__).resolve().parent.parent
TEAMS_JSON     = BASE_DIR / "mock_db" / "teams.json"
SYSTEMS_JSON   = BASE_DIR / "mock_db" / "systems.json"
DL_GROUPS_JSON = BASE_DIR / "mock_db" / "dl_groups.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def print_header(text: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print(f"{'─' * 60}")

# ── JSON Schema Validation ────────────────────────────────────────────────────
# Defines required keys for every JSON file and every nested object.
# Catches key mismatches (like the "email" vs "dl_email" bug) before
# the DB is created and the app is started.

# Schema definition format:
#   {
#     "file_description":   human-readable name for error messages
#     "file_path":          Path constant for the JSON file
#     "root_key":           top-level list key in the JSON
#     "required_keys":      keys every item in the list must have
#     "nested":             optional — { "key": [required sub-keys] }
#   }

JSON_SCHEMAS = [
    {
        "description":   "teams.json",
        "path":          TEAMS_JSON,
        "root_key":      "teams",
        "required_keys": [
            "team_id", "team_name", "department", "manager",
            "manager_email", "required_systems", "required_skills", "doc_tags",
        ],
        "nested": {},
    },
    {
        "description":   "systems.json",
        "path":          SYSTEMS_JSON,
        "root_key":      "systems",
        "required_keys": [
            "system_id", "system_name", "category", "ticket_type",
            "ticket_summary_template", "ticket_fields", "sla",
            "access_levels", "default_access_level",
            "requires_approval", "requires_security_review",
        ],
        "nested": {
            "sla":           ["response_hours", "resolution_hours"],
            "ticket_fields": ["priority", "issue_type"],
        },
    },
    {
        "description":   "dl_groups.json",
        "path":          DL_GROUPS_JSON,
        "root_key":      "distribution_lists",
        "required_keys": ["team_id", "team_name", "dl_groups"],
        "nested": {},
        "child_list_key": "dl_groups",
        "child_required_keys": [
            "dl_id", "dl_name", "dl_email",
            "owner_name", "owner_email",
            "email_template",
        ],
        "child_nested": {
            "email_template": ["subject", "body"],
        },
    },
]


def validate_json_files() -> bool:
    """
    Validate all three JSON data files against their expected schemas.

    Checks:
      - File exists
      - Valid JSON (no syntax errors)
      - Root key present
      - All required keys present in every item
      - All required nested sub-keys present
      - Child list items validated for dl_groups.json

    Prints a clear report and returns True if all pass, False if any fail.
    Call this before creating the database — fail fast, fail clearly.
    """
    print_header("JSON Schema Validation")
    print()

    all_passed  = True
    total_files = 0
    total_items = 0
    total_errors = 0

    for schema in JSON_SCHEMAS:
        desc     = schema["description"]
        path     = schema["path"]
        root_key = schema["root_key"]

        # ── File existence ────────────────────────────────────────────────────
        if not path.exists():
            print(f"  ❌  {desc}")
            print(f"       File not found: {path}")
            all_passed = False
            total_errors += 1
            continue

        # ── JSON syntax ───────────────────────────────────────────────────────
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  ❌  {desc}")
            print(f"       Invalid JSON: {e}")
            all_passed = False
            total_errors += 1
            continue

        # ── Root key ──────────────────────────────────────────────────────────
        if root_key not in data:
            print(f"  ❌  {desc}")
            print(f"       Missing root key: '{root_key}'")
            all_passed = False
            total_errors += 1
            continue

        items      = data[root_key]
        file_errors = []

        # ── Required keys on each top-level item ──────────────────────────────
        for idx, item in enumerate(items):
            item_label = item.get("team_id") or item.get("system_id") or f"item[{idx}]"

            for key in schema["required_keys"]:
                if key not in item:
                    file_errors.append(
                        f"  [{item_label}] missing required key: '{key}'"
                    )

            # ── Nested sub-keys ───────────────────────────────────────────────
            for parent_key, sub_keys in schema.get("nested", {}).items():
                if parent_key in item:
                    for sub_key in sub_keys:
                        if sub_key not in item[parent_key]:
                            file_errors.append(
                                f"  [{item_label}] '{parent_key}' missing sub-key: '{sub_key}'"
                            )

            # ── Child list validation (dl_groups inside distribution_lists) ───
            child_key = schema.get("child_list_key")
            if child_key and child_key in item:
                child_required = schema.get("child_required_keys", [])
                child_nested   = schema.get("child_nested", {})

                for cidx, child in enumerate(item[child_key]):
                    child_label = child.get("dl_id") or f"dl[{cidx}]"

                    for key in child_required:
                        if key not in child:
                            file_errors.append(
                                f"  [{item_label} → {child_label}] "
                                f"missing required key: '{key}'"
                            )

                    for parent_key, sub_keys in child_nested.items():
                        if parent_key in child:
                            for sub_key in sub_keys:
                                if sub_key not in child[parent_key]:
                                    file_errors.append(
                                        f"  [{item_label} → {child_label}] "
                                        f"'{parent_key}' missing sub-key: '{sub_key}'"
                                    )

        total_files += 1
        total_items += len(items)

        if file_errors:
            print(f"  ❌  {desc}  ({len(items)} items, {len(file_errors)} error(s))")
            for err in file_errors:
                print(f"       {err}")
            all_passed   = False
            total_errors += len(file_errors)
        else:
            print(f"  ✅  {desc}  ({len(items)} items — all keys valid)")

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print(f"  {'─' * 56}")
    print(f"  Files validated : {total_files} / {len(JSON_SCHEMAS)}")
    print(f"  Items checked   : {total_items}")
    print(f"  Errors found    : {total_errors}")
    print()

    if all_passed:
        print("  ✅  All JSON files valid — safe to create database.\n")
    else:
        print("  ❌  Fix the errors above before running gen_db.py.\n")
        print("  Tip: Check key names in your JSON files match the schema.")
        print("       The 'dl_email' key in dl_groups.json is a common mismatch.\n")

    return all_passed


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    passed = validate_json_files()
    sys.exit(0 if passed else 1)