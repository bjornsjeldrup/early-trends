#!/usr/bin/env python3
"""Set sitemap lastmod, and product dateModified, from git history.

Each URL in sitemap.xml is mapped back to a file. lastmod becomes the date of
that file's latest commit (`git log -1 --format=%cs`). Product articles under
trends/ (not the index or the method page) get the same date in BlogPosting
dateModified.

Run from the repository root:

    python3 scripts/build_sitemap.py
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITEMAP = ROOT / "sitemap.xml"
PREFIX = "https://bjornsjeldrup.github.io/early-trends/"
PRODUCT_SKIP = {"index.html", "how-we-spot-trends.html"}


def git_date(path):
    relative = path.relative_to(ROOT).as_posix()
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", relative],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    date = result.stdout.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise SystemExit(f"no git commit date for {relative}")
    return date


def loc_to_path(loc):
    if not loc.startswith(PREFIX):
        raise SystemExit(f"sitemap URL is outside the site: {loc}")
    relative = loc[len(PREFIX) :]
    if relative == "" or relative.endswith("/"):
        relative += "index.html"
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit(f"sitemap URL has no file: {loc} -> {relative}")
    return path


def update_sitemap():
    text = SITEMAP.read_text(encoding="utf-8")

    def repl(match):
        loc, old = match.group(1), match.group(2)
        date = git_date(loc_to_path(loc))
        return match.group(0).replace(f"<lastmod>{old}</lastmod>", f"<lastmod>{date}</lastmod>", 1)

    updated, count = re.subn(
        r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>",
        repl,
        text,
    )
    if count < 1:
        raise SystemExit("sitemap.xml has no lastmod entries")
    if updated != text:
        SITEMAP.write_text(updated, encoding="utf-8")
    return count


def update_product_dates():
    changed = 0
    for path in sorted((ROOT / "trends").glob("*.html")):
        if path.name in PRODUCT_SKIP:
            continue
        text = path.read_text(encoding="utf-8")
        if '"dateModified"' not in text:
            raise SystemExit(f"{path.name} has no dateModified")
        date = git_date(path)
        updated, count = re.subn(
            r'"dateModified"\s*:\s*"\d{4}-\d{2}-\d{2}"',
            f'"dateModified": "{date}"',
            text,
            count=1,
        )
        if count != 1:
            raise SystemExit(f"could not set dateModified on {path.name}")
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed += 1
        print(f"{path.relative_to(ROOT).as_posix()} dateModified {date}")
    return changed


def main():
    urls = update_sitemap()
    pages = update_product_dates()
    print(f"sitemap lastmod entries: {urls}; product dates rewritten: {pages}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
