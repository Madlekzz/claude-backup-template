"""Copy new or changed org-authored skills from the local Claude Team sync into skills/.

Claude Code keeps a local copy of your organization's skills under ~/.claude/skills/synced/<org-uuid>_<name>/.
Only skills your org created (`source: plugin` in that manifest) are copied; Anthropic's built-in skills are
skipped because Anthropic ships and restores them.

If you belong to more than one organization, set CLAUDE_ORG_UUID to the one to back up.
Skills that disappear from Claude are kept and flagged with `removedFromClaude` in skills/_manifest.json.
"""
import glob
import os
import sys

from _common import REPO, TODAY, read_json, replace_dir, trees_equal, write_json


def find_sync_manifest():
    root = os.path.expanduser("~/.claude/skills/synced")
    org = os.environ.get("CLAUDE_ORG_UUID")
    matches = sorted(glob.glob(os.path.join(root, f"{org}_*" if org else "*", "manifest.json")))
    if not matches:
        sys.exit(f"No Claude Team skills sync found under {root}/ (open Claude Code once while signed in to your org).")
    if len(matches) > 1:
        names = ", ".join(os.path.basename(os.path.dirname(m)) for m in matches)
        sys.exit(f"Several org syncs found ({names}). Set CLAUDE_ORG_UUID to the org to back up.")
    return matches[0]


def main():
    manifest_path = find_sync_manifest()
    src_root = os.path.dirname(manifest_path)
    src_manifest = read_json(manifest_path)
    dst_root = os.path.join(REPO, "skills")
    repo_manifest = read_json(os.path.join(dst_root, "_manifest.json"), {"skills": []})
    known = {s["name"]: s for s in repo_manifest["skills"]}

    current = [s for s in src_manifest["skills"] if s.get("source") == "plugin"]
    changes = []
    for s in current:
        src, dst = os.path.join(src_root, s["name"]), os.path.join(dst_root, s["name"])
        if not trees_equal(src, dst):
            changes.append(("added" if not os.path.isdir(dst) else "updated", s["name"]))
            replace_dir(src, dst)
        known[s["name"]] = dict(s)

    present = {s["name"] for s in current}
    for name, entry in known.items():
        if name not in present and not entry.get("removedFromClaude"):
            entry["removedFromClaude"] = TODAY
            changes.append(("removed in Claude (kept)", name))

    new_manifest = {"lastUpdated": src_manifest.get("lastUpdated") if changes else repo_manifest.get("lastUpdated"),
                    "skills": sorted(known.values(), key=lambda s: s["name"])}
    if changes:
        write_json(os.path.join(dst_root, "_manifest.json"), new_manifest)
    for kind, name in changes:
        print(f"skills: {kind}: {name}")
    if not changes:
        print("skills: no changes")


if __name__ == "__main__":
    main()
