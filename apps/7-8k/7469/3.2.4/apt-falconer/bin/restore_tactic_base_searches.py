from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEWS_DIR = ROOT / "default" / "data" / "ui" / "views"
TECHNIQUES_DIR = ROOT / "appserver" / "static" / "data" / "techniques"

LEGACY_VIEW_NAMES = {
    "c2": "command_and_control.xml",
}


PANEL_BLOCK_RE = re.compile(r'<panel id="([^"]+)"[\s\S]*?</panel>', re.MULTILINE)
SEARCH_BASE_RE = re.compile(r'<search[^>]*\sbase="([^"]+)"')


def legacy_view_for_tactic(tactic: str) -> Path:
    return VIEWS_DIR / LEGACY_VIEW_NAMES.get(tactic, f"{tactic}.xml")


def load_panel_bases(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    panel_bases: dict[str, str] = {}
    for match in PANEL_BLOCK_RE.finditer(text):
        panel_id = match.group(1)
        panel_body = match.group(0)
        base_match = SEARCH_BASE_RE.search(panel_body)
        if base_match:
            panel_bases[panel_id] = base_match.group(1)
    return panel_bases


def main() -> int:
    updated_files = 0
    updated_techniques = 0

    for json_path in sorted(TECHNIQUES_DIR.glob("*.json")):
        tactic = json_path.stem
        legacy_view = legacy_view_for_tactic(tactic)
        if not legacy_view.exists():
            continue

        panel_bases = load_panel_bases(legacy_view)
        if not panel_bases:
            continue

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        changed = False

        for technique in payload.get("techniques", []):
            query = (technique.get("query") or technique.get("search") or "").strip()
            panel_id = technique.get("id")
            base = panel_bases.get(panel_id)

            if not base or not query.startswith("|"):
                continue

            if technique.get("base_search") == base:
                continue

            technique["base_search"] = base
            updated_techniques += 1
            changed = True

        if changed:
            json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            print(f"updated {json_path.name}")
            updated_files += 1

    print(f"updated_files={updated_files}")
    print(f"updated_techniques={updated_techniques}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
