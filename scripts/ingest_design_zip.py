"""Store standalone claude.ai/design exports under design/<slug>/.

Usage:
  python3 scripts/ingest_design_zip.py everything <Claude Design projects.zip> --owner OWNER
  python3 scripts/ingest_design_zip.py project <Project.zip> --url PROJECT_URL --title TITLE --owner OWNER

`everything` is the "Download everything" export (one `<Title> <id>/` folder per owned project).
`project` is one project's Share > Project HTML > Project archive (project files at the zip root).
Projects map to folders by project URL; a folder is rewritten only when its files changed.
"""
import argparse
import os
import re
import shutil
import tempfile

from _common import REPO, TODAY, item_dirs, read_json, safe_extract, slugify, trees_equal, unique_slug, write_json

DESIGN = os.path.join(REPO, "design")


def find_slug(project_id):
    for slug in item_dirs("design"):
        meta = read_json(os.path.join(DESIGN, slug, "meta.json"), {})
        if project_id and project_id in (meta.get("projectUrl") or ""):
            return slug
    return None


def store(staged, url, title, owner, source):
    project_id = url.rstrip("/").split("/")[-1].split("?")[0]
    slug = find_slug(project_id)
    is_new = slug is None
    if is_new:
        slug = unique_slug(slugify(title), set(os.listdir(DESIGN)))
    dest = os.path.join(DESIGN, slug)
    old_meta = read_json(os.path.join(dest, "meta.json"), {})
    # EXPORT-README.md carries the export date, so it is not a content change on its own.
    if not is_new and trees_equal(staged, dest, ignore=("meta.json", "EXPORT-README.md")) and not old_meta.get("removedFromClaude"):
        print(f"design: no changes: {slug}")
        return
    meta = {k: v for k, v in old_meta.items() if k != "removedFromClaude"}
    meta.update({"title": title, "source": source, "projectUrl": url, "type": "Claude Design project (standalone)",
                 "owner": owner, "backedUp": TODAY})
    write_json(os.path.join(staged, "meta.json"), meta)
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(staged, dest)
    print(f"design: {'added' if is_new else 'updated'}: {slug}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("everything", "project"))
    ap.add_argument("zip")
    ap.add_argument("--owner", required=True)
    ap.add_argument("--url")
    ap.add_argument("--title")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        extracted = os.path.join(tmp, "x")
        safe_extract(args.zip, extracted)
        if args.mode == "project":
            staged = os.path.join(tmp, "staged")
            os.makedirs(staged)
            shutil.copytree(extracted, os.path.join(staged, "project"))
            store(staged, args.url, args.title, args.owner, "standalone claude.ai/design (Share → Project HTML → Project archive)")
            return
        for folder in sorted(os.listdir(extracted)):
            m = re.match(r"(.+) ([0-9a-f]{8}-[0-9a-f]{4})$", folder)
            if not m:
                continue
            title, id_prefix = m.groups()
            slug = find_slug(id_prefix)
            url = read_json(os.path.join(DESIGN, slug, "meta.json"), {}).get("projectUrl") if slug else None
            staged = os.path.join(tmp, "staged-" + id_prefix)
            os.makedirs(staged)
            shutil.copytree(os.path.join(extracted, folder, "project"), os.path.join(staged, "project"))
            shutil.copy(os.path.join(extracted, folder, "README.md"), os.path.join(staged, "EXPORT-README.md"))
            store(staged, url or f"https://claude.ai/design/p/{id_prefix}", title, args.owner,
                  "standalone claude.ai/design (Download everything export)")


if __name__ == "__main__":
    main()
