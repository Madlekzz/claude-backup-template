"""Apply a claude.ai projects export (from scripts/export_projects.js) to projects/.

Usage: python3 scripts/ingest_projects.py <export.json>

Each project maps to its folder by uuid, so renames keep the folder. A folder is rewritten only when its
instructions, attachments or metadata changed. Projects missing from the export are kept and flagged with
`removedFromClaude` in their meta.json.
"""
import base64
import os
import shutil
import sys
import tempfile

from _common import REPO, TODAY, index_meta, read_json, safe_name, slugify, trees_equal, unique_slug, write_json

MIME_EXT = {"image/webp": ".webp", "image/png": ".png", "image/jpeg": ".jpg", "application/pdf": ".pdf"}
VOLATILE = ("backedUp",)


def unique_path(path):
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(path):
        path, n = f"{base} ({n}){ext}", n + 1
    return path


def build(project, root, backed_up):
    """Write one project (instructions.md, attachments/, meta.json) into an empty folder."""
    att = os.path.join(root, "attachments")
    os.makedirs(att)
    if project.get("prompt_template"):
        with open(os.path.join(root, "instructions.md"), "w", encoding="utf-8") as f:
            f.write(project["prompt_template"])

    docs = []
    for d in project["docs"]:
        name = safe_name(d.get("file_name") or d["uuid"])
        if not os.path.splitext(name)[1]:
            name += ".md"
        dest = unique_path(os.path.join(att, name))
        with open(dest, "w", encoding="utf-8") as f:
            f.write(d.get("content") or "")
        docs.append({"file": os.path.relpath(dest, root), "uuid": d["uuid"], "created_at": d.get("created_at"), "kind": "text (knowledge doc)"})

    files = []
    for fl in project["files"]:
        entry = {"original_name": fl["file_name"], "file_kind": fl["file_kind"], "size_bytes": fl["size_bytes"], "variant": fl.get("variant")}
        if fl.get("data"):
            name = safe_name(fl["file_name"])
            if fl["variant"] == "preview":
                name = os.path.splitext(name)[0] + MIME_EXT.get((fl.get("contentType") or "").split(";")[0], "")
            dest = unique_path(os.path.join(att, name))
            with open(dest, "wb") as f:
                f.write(base64.b64decode(fl["data"]))
            entry["file"] = os.path.relpath(dest, root)
        else:
            entry["file"] = None
            entry["note"] = "Not downloadable through claude.ai (no asset URL); not backed up."
        files.append(entry)

    if not os.listdir(att):
        os.rmdir(att)
    write_json(os.path.join(root, "meta.json"), {
        "name": project["name"],
        "uuid": project["uuid"],
        "url": f"https://claude.ai/project/{project['uuid']}",
        "creator": project.get("creator"),
        "is_private": project.get("is_private"),
        "description": project.get("description"),
        "created_at": project.get("created_at"),
        "updated_at": project.get("updated_at"),
        "has_instructions": bool(project.get("prompt_template")),
        "docs": docs,
        "files": files,
        "backedUp": backed_up,
    })


def same_except_volatile(new_root, old_root):
    if not trees_equal(new_root, old_root, ignore=("meta.json",)):
        return False
    new_meta = read_json(os.path.join(new_root, "meta.json"), {})
    old_meta = read_json(os.path.join(old_root, "meta.json"), {})
    strip = lambda m: {k: v for k, v in m.items() if k not in VOLATILE + ("removedFromClaude",)}
    return strip(new_meta) == strip(old_meta) and not old_meta.get("removedFromClaude")


def main():
    data = read_json(sys.argv[1])
    projects_dir = os.path.join(REPO, "projects")
    by_uuid = index_meta("projects", "uuid")
    taken = set(os.listdir(projects_dir))
    changes = []

    with tempfile.TemporaryDirectory() as tmp:
        for p in data["projects"]:
            slug = by_uuid.get(p["uuid"])
            if not slug:
                slug = unique_slug(slugify(p["name"]), taken)
                taken.add(slug)
            staged = os.path.join(tmp, slug)
            build(p, staged, TODAY)
            dest = os.path.join(projects_dir, slug)
            if os.path.isdir(dest) and same_except_volatile(staged, dest):
                continue
            changes.append(("updated" if os.path.isdir(dest) else "added", slug))
            if os.path.isdir(dest):
                shutil.rmtree(dest)
            shutil.copytree(staged, dest)

    present = {p["uuid"] for p in data["projects"]}
    for uuid, slug in by_uuid.items():
        meta_path = os.path.join(projects_dir, slug, "meta.json")
        meta = read_json(meta_path)
        if uuid not in present and not meta.get("removedFromClaude"):
            meta["removedFromClaude"] = TODAY
            write_json(meta_path, meta)
            changes.append(("removed in Claude (kept)", slug))

    for missing in data.get("missing", []):
        print(f"projects: not downloadable: {missing}")
    for kind, slug in changes:
        print(f"projects: {kind}: {slug}")
    if not changes:
        print("projects: no changes")


if __name__ == "__main__":
    main()
