"""Flag design/ items that no longer exist in Claude (they are kept, never deleted).

Usage: python3 scripts/mark_design_missing.py <listing.json>

listing.json: {"artifacts": [every artifact URL seen today], "standalone": [every claude.ai/design project URL seen today]}
Standalone projects that were moved to Claude still count as present. A file is used instead of CLI
arguments so shells that do not word-split variables (zsh) cannot collapse the lists.
"""
import os
import sys

from _common import REPO, TODAY, item_dirs, read_json, write_json


def project_id(url):
    return url.rstrip("/").split("/")[-1].split("?")[0]


def main():
    listing = read_json(sys.argv[1])
    artifacts = set(listing.get("artifacts", []))
    standalone = {project_id(u) for u in listing.get("standalone", [])}
    if not artifacts or not standalone:
        raise SystemExit("Refusing to run with an empty listing: both 'artifacts' and 'standalone' are required.")

    design = os.path.join(REPO, "design")
    changed = 0
    for slug in item_dirs("design"):
        path = os.path.join(design, slug, "meta.json")
        meta = read_json(path)
        if not meta or meta.get("removedFromClaude"):
            continue
        if meta.get("artifact"):
            present = meta["artifact"] in artifacts
        else:
            # New projects from "Download everything" may only know an id prefix, so match either way.
            stored = project_id(meta.get("projectUrl", "")) or "-"
            present = any(pid.startswith(stored) or stored.startswith(pid) for pid in standalone)
        if not present:
            meta["removedFromClaude"] = TODAY
            write_json(path, meta)
            changed += 1
            print(f"design: removed in Claude (kept): {slug}")
    if not changed:
        print("design: nothing removed")


if __name__ == "__main__":
    main()
