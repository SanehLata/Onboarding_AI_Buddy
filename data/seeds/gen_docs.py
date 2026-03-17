# gen_docs.py
# @Author: Saneh Lata
# Walks mock_docs/ directory, confirms all expected files exist,
# prints a count summary and word count per file.

import os
import sys
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
MOCK_DOCS_DIR = BASE_DIR / "mock_docs"

EXPECTED_FILES = {
    "onboarding": [
        "day1_checklist.md",
        "team_norms.md",
        "communication_channels.md",
        "tools_setup.md",
        "vpn_access.md",
        "access_provisioning.md",
        "code_review_guide.md",
        "on_call_guide.md",
        "30_60_90_day_plan.md",
    ],
    "architecture": [
        "system_overview.md",
        "auth_service.md",
        "payments_api.md",
        "data_pipeline.md",
        "microservices_map.md",
        "api_design_standards.md",
    ],
    "runbooks": [
        "deployment_guide.md",
        "incident_response.md",
        "database_failover.md",
        "logging_standards.md",
        "kafka_consumer_runbook.md",
        "secrets_config_management.md",
    ],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def print_header(text: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print(f"{'─' * 60}")


def word_count(filepath: Path) -> int:
    return len(filepath.read_text(encoding="utf-8").split())


def file_size_kb(filepath: Path) -> str:
    size = filepath.stat().st_size / 1024
    return f"{size:.1f} KB"


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print_header("Onboarding Buddy — Knowledge Base Validator")

    if not MOCK_DOCS_DIR.exists():
        print(f"\n  ❌  mock_docs/ directory not found at: {MOCK_DOCS_DIR}")
        print("      Create the directory and add markdown files before running this script.")
        sys.exit(1)

    total_files       = 0
    total_words       = 0
    missing_files     = []
    unexpected_files  = []
    all_results       = {}

    # ── Check expected files ──────────────────────────────────────────────────
    for subfolder, filenames in EXPECTED_FILES.items():
        folder_path = MOCK_DOCS_DIR / subfolder
        folder_results = []

        for filename in filenames:
            filepath = folder_path / filename
            if filepath.exists():
                words = word_count(filepath)
                size  = file_size_kb(filepath)
                folder_results.append(("✅", filename, words, size))
                total_files += 1
                total_words += words
            else:
                folder_results.append(("❌", filename, 0, "—"))
                missing_files.append(str(filepath.relative_to(BASE_DIR)))

        all_results[subfolder] = folder_results

    # ── Detect unexpected files ───────────────────────────────────────────────
    for subfolder in MOCK_DOCS_DIR.iterdir():
        if not subfolder.is_dir():
            continue
        folder_name = subfolder.name
        expected_in_folder = EXPECTED_FILES.get(folder_name, [])
        for f in subfolder.iterdir():
            if f.suffix == ".md" and f.name not in expected_in_folder:
                unexpected_files.append(str(f.relative_to(BASE_DIR)))

    # ── Print results by folder ───────────────────────────────────────────────
    for subfolder, results in all_results.items():
        print(f"\n  📁  mock_docs/{subfolder}/")
        print(f"  {'File':<40} {'Words':>6}  {'Size':>8}")
        print(f"  {'─' * 58}")
        for status, filename, words, size in results:
            word_display = str(words) if words else "—"
            print(f"  {status}  {filename:<38} {word_display:>6}  {size:>8}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print_header("Summary")

    total_expected = sum(len(v) for v in EXPECTED_FILES.values())
    found          = total_expected - len(missing_files)

    print(f"\n  Files found   : {found} / {total_expected}")
    print(f"  Total words   : {total_words:,}")
    print(f"  Total size    : {sum((MOCK_DOCS_DIR / s / f).stat().st_size for s, files in EXPECTED_FILES.items() for f in files if (MOCK_DOCS_DIR / s / f).exists()) / 1024:.1f} KB")

    # ── Folder breakdown ──────────────────────────────────────────────────────
    print(f"\n  {'Folder':<20} {'Files':>5}  {'Words':>8}")
    print(f"  {'─' * 38}")
    for subfolder, results in all_results.items():
        folder_files = sum(1 for r in results if r[0] == "✅")
        folder_words = sum(r[2] for r in results)
        print(f"  {subfolder:<20} {folder_files:>5}  {folder_words:>8,}")

    # ── Issues ────────────────────────────────────────────────────────────────
    if missing_files:
        print(f"\n  ⚠️   Missing files ({len(missing_files)}):")
        for f in missing_files:
            print(f"       - {f}")

    if unexpected_files:
        print(f"\n  ℹ️   Unexpected files found ({len(unexpected_files)}) — not in expected list:")
        for f in unexpected_files:
            print(f"       - {f}")

    # ── Final status ──────────────────────────────────────────────────────────
    print()
    if missing_files:
        print("  ❌  Validation FAILED — missing files listed above.")
        print("      Add the missing files before running embed_docs.py\n")
        sys.exit(1)
    else:
        print("  ✅  All expected files present. Knowledge base is ready.")
        print("      Next step: run  python data/seeds/embed_docs.py\n")


if __name__ == "__main__":
    run()
