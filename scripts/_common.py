"""Shared helpers for the backup scripts (stdlib only)."""
import datetime
import filecmp
import json
import os
import re
import shutil
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = datetime.date.today().isoformat()


def slugify(text):
    text = text.lower()
    for src, dst in (("áàä", "a"), ("éèë", "e"), ("íìï", "i"), ("óòö", "o"), ("úùü", "u"), ("ñ", "n")):
        text = re.sub(f"[{src}]", dst, text)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "untitled"


def unique_slug(base, taken):
    slug, n = base, 2
    while slug in taken:
        slug, n = f"{base}-{n}", n + 1
    return slug


def safe_name(name):
    name = name.replace("/", "_").replace("\\", "_").strip()
    return name.lstrip(".") or "untitled"


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def trees_equal(a, b, ignore=()):
    """True when two directory trees hold the same relative files with the same bytes."""
    if not (os.path.isdir(a) and os.path.isdir(b)):
        return os.path.isdir(a) == os.path.isdir(b)

    def files(root):
        out = set()
        for d, _, fs in os.walk(root):
            for f in fs:
                rel = os.path.relpath(os.path.join(d, f), root)
                if rel not in ignore:
                    out.add(rel)
        return out

    fa, fb = files(a), files(b)
    if fa != fb:
        return False
    return all(filecmp.cmp(os.path.join(a, f), os.path.join(b, f), shallow=False) for f in fa)


def replace_dir(src, dst):
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def safe_extract(zip_path, dest):
    """Extract a zip, refusing absolute paths and parent-directory escapes."""
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            if name.startswith("/") or ".." in name.split("/"):
                raise ValueError(f"unsafe path in {zip_path}: {name}")
        z.extractall(dest)


def item_dirs(section):
    """Item folders of a section (design/ or projects/), skipping placeholder files such as .gitkeep."""
    root = os.path.join(REPO, section)
    return sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))


def index_meta(section, key):
    """Map meta[key] -> folder name for every item in a section (design/ or projects/)."""
    out = {}
    root = os.path.join(REPO, section)
    for slug in os.listdir(root):
        if not os.path.isdir(os.path.join(root, slug)):
            continue
        meta = read_json(os.path.join(root, slug, "meta.json"))
        if meta and meta.get(key):
            out[meta[key]] = slug
    return out
