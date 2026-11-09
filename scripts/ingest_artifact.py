"""Store one Claude Design artifact (Design, Slides, Motion, Design System) under design/<slug>/.

Usage:
  python3 scripts/ingest_artifact.py --url URL --title TITLE --type TYPE --version VERSION --owner OWNER
      [--project-dir DIR]   folder holding the downloaded `project/` tree (the Artifact read output dir)
      [--db-dir DIR]        Motion only: folder with film/, modules/, assets/ JSON documents
      [--asset ID=PATH ...] asset-store files (id is the 32 hex chars after /_blob/)

The item maps to its folder by artifact URL; it is rewritten only when its files changed.
"""
import argparse
import os
import shutil
import tempfile

from _common import REPO, TODAY, index_meta, read_json, slugify, trees_equal, unique_slug, write_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--type", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--project-dir")
    ap.add_argument("--db-dir")
    ap.add_argument("--asset", action="append", default=[])
    args = ap.parse_args()

    design_dir = os.path.join(REPO, "design")
    slug = index_meta("design", "artifact").get(args.url)
    is_new = slug is None
    if is_new:
        slug = unique_slug(slugify(args.title), set(os.listdir(design_dir)))

    with tempfile.TemporaryDirectory() as tmp:
        staged = os.path.join(tmp, slug)
        os.makedirs(staged)
        if args.project_dir and os.path.isdir(os.path.join(args.project_dir, "project")):
            shutil.copytree(os.path.join(args.project_dir, "project"), os.path.join(staged, "project"))
        if args.db_dir:
            shutil.copytree(args.db_dir, os.path.join(staged, "db"))
        amap = {}
        for spec in args.asset:
            asset_id, path = spec.split("=", 1)
            os.makedirs(os.path.join(staged, "assets"), exist_ok=True)
            name = os.path.basename(path)
            shutil.copy(path, os.path.join(staged, "assets", name))
            amap[f"/_blob/{asset_id}"] = f"assets/{name}"

        dest = os.path.join(design_dir, slug)
        old_meta = read_json(os.path.join(dest, "meta.json"), {})
        # The artifact version bumps on reads too, so only file changes count as a change.
        if not is_new and trees_equal(staged, dest, ignore=("meta.json",)) and not old_meta.get("removedFromClaude"):
            print(f"design: no changes: {slug}")
            return

        meta = {k: v for k, v in old_meta.items() if k != "removedFromClaude"}
        meta.update({"title": args.title, "artifact": args.url, "type": args.type, "version": args.version,
                     "owner": args.owner, "backedUp": TODAY, "assets": amap})
        write_json(os.path.join(staged, "meta.json"), meta)
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        shutil.copytree(staged, dest)
        print(f"design: {'added' if is_new else 'updated'}: {slug}")


if __name__ == "__main__":
    main()
