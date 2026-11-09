"""Regenerate the generated tables in README.md (between <!-- BEGIN:x --> / <!-- END:x --> markers)."""
import datetime
import os
import re

from _common import REPO, item_dirs, read_json

ARTIFACT_TYPES = ("Design", "Slides", "Motion", "Design System")


def file_count(path):
    return sum(len(fs) for _, _, fs in os.walk(path)) if os.path.isdir(path) else 0


def status(meta):
    return f"removed in Claude {meta['removedFromClaude']}" if meta.get("removedFromClaude") else ""


def cell(text):
    return str(text or "").replace("|", "/").replace("\n", " ").strip()


def skills_table():
    manifest = read_json(os.path.join(REPO, "skills", "_manifest.json"), {}) or {}
    manifest.setdefault("skills", [])
    rows = ["| Skill | Last updated in Claude | Description | Status |", "|---|---|---|---|"]
    for s in sorted(manifest["skills"], key=lambda s: s["name"]):
        desc = " ".join(s["description"].split())
        desc = desc[:157].rstrip() + "…" if len(desc) > 160 else desc
        rows.append(f"| [`{s['name']}`](skills/{s['name']}/SKILL.md) | {s['updatedAt'][:10]} | {cell(desc)} | {status(s)} |")
    last = manifest.get("lastUpdated")
    last = datetime.datetime.fromtimestamp(last / 1000, datetime.timezone.utc).date().isoformat() if last else "never"
    return rows, len(manifest["skills"]), last


def design_tables():
    root = os.path.join(REPO, "design")
    artifacts, standalone, last = [], [], ""
    for slug in item_dirs("design"):
        meta = read_json(os.path.join(root, slug, "meta.json"), {})
        last = max(last, meta.get("backedUp", ""))
        files = file_count(os.path.join(root, slug, "project")) + file_count(os.path.join(root, slug, "db"))
        assets = file_count(os.path.join(root, slug, "assets"))
        if meta.get("type") in ARTIFACT_TYPES:
            src = f"[artifact]({meta['artifact']})"
            artifacts.append(f"| [`{slug}`](design/{slug}) | {cell(meta['title'])} | {meta['type']} | {cell(meta.get('owner'))} | {src} | {files} | {assets} | {status(meta)} |")
        else:
            src = f"[project]({meta['projectUrl']})" if meta.get("projectUrl") else ""
            standalone.append(f"| [`{slug}`](design/{slug}) | {cell(meta['title'])} | {cell(meta.get('owner'))} | {src} | {files} | {cell(meta.get('note'))} {status(meta)} |")
    a = ["| Folder | Title | Type | Owner | Source | Files | Assets | Status |", "|---|---|---|---|---|---|---|---|"] + artifacts
    s = ["| Folder | Title | Owner | Source | Files | Notes |", "|---|---|---|---|---|---|"] + standalone
    return a, s, len(artifacts) + len(standalone), last or "never"


def projects_table():
    root = os.path.join(REPO, "projects")
    rows, last = [], ""
    metas = [(slug, read_json(os.path.join(root, slug, "meta.json"), {})) for slug in item_dirs("projects")]
    for slug, meta in sorted(metas, key=lambda x: x[1].get("name", "").strip().lower().lstrip("[{")):
        last = max(last, meta.get("backedUp", ""))
        content = []
        if meta.get("has_instructions"):
            content.append("instructions")
        if meta.get("docs"):
            content.append(f"{len(meta['docs'])} docs")
        got = [f for f in meta.get("files", []) if f.get("file")]
        missing = [f for f in meta.get("files", []) if not f.get("file")]
        if got:
            content.append(f"{len(got)} files")
        if missing:
            content.append(f"{len(missing)} missing")
        access = "private" if meta.get("is_private") else "org"
        rows.append(f"| [`{slug}`](projects/{slug}) | {cell(meta.get('name'))} | {cell(meta.get('creator'))} | {access} | {', '.join(content) or 'empty'} | {status(meta)} |")
    return ["| Folder | Project | Creator | Access | Content | Status |", "|---|---|---|---|---|---|"] + rows, len(rows), last or "never"


def replace_block(text, name, lines):
    pattern = re.compile(rf"(<!-- BEGIN:{name} -->\n).*?(<!-- END:{name} -->)", re.S)
    if not pattern.search(text):
        raise SystemExit(f"README.md is missing the {name} markers")
    return pattern.sub(lambda m: m.group(1) + "\n".join(lines) + "\n" + m.group(2), text)


def main():
    path = os.path.join(REPO, "README.md")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    skills, n_skills, skills_date = skills_table()
    artifacts, standalone, n_design, design_date = design_tables()
    projects, n_projects, projects_date = projects_table()
    log = ["| Section | Last change | Items |", "|---|---|---|",
           f"| `skills/` | {skills_date} (Claude Team sync) | {n_skills} |",
           f"| `design/` | {design_date} | {n_design} |",
           f"| `projects/` | {projects_date} | {n_projects} |"]
    for name, lines in (("backup-log", log), ("skills", skills), ("design-artifacts", artifacts),
                        ("design-standalone", standalone), ("projects", projects)):
        text = replace_block(text, name, lines)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("README.md tables regenerated")


if __name__ == "__main__":
    main()
