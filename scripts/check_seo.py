#!/usr/bin/env python3
"""Quick checks for the technical SEO pass.

Confirms there are no internal index.html hrefs, every JSON-LD block parses,
and every sitemap URL points at a file that exists. Also checks the title,
description, canonical, affiliate, breadcrumb, and image rules from this pass.

    python3 scripts/check_seo.py
"""

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://bjornsjeldrup.github.io/early-trends/"
SKIP = {"google192c75b4b1b41826.html"}
PRODUCT_SKIP = {"index.html", "how-we-spot-trends.html"}
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
errors = []


def fail(message):
    errors.append(message)


def pages():
    for path in sorted(ROOT.rglob("*.html")):
        if path.name in SKIP:
            continue
        text = path.read_text(encoding="utf-8")
        if "<html" not in text.lower():
            continue
        yield path, text


def expected_canonical(path):
    rel = path.relative_to(ROOT)
    if rel.name == "index.html":
        parent = rel.parent.as_posix()
        if parent == ".":
            return BASE
        return BASE + parent + "/"
    return BASE + rel.as_posix()


def loc_to_path(loc):
    if not loc.startswith(BASE):
        return None
    relative = loc[len(BASE) :]
    if relative == "" or relative.endswith("/"):
        relative += "index.html"
    return ROOT / relative


def is_internal(url):
    if url.startswith(("mailto:", "javascript:", "data:", "//")):
        return False
    if url.startswith(("http://", "https://")):
        return (urlsplit(url).hostname or "") == "bjornsjeldrup.github.io"
    return True


def is_amazon(url):
    host = (urlsplit(url).hostname or "").lower()
    return host == "amazon.com" or host.endswith(".amazon.com") or host == "amzn.to" or host.endswith(".amzn.to")


def main():
    titles = {}
    for path, text in pages():
        rel = path.relative_to(ROOT).as_posix()
        for match in re.finditer(r'\bhref\s*=\s*(["\'])([^"\']+)\1', text, re.I):
            url = html.unescape(match.group(2))
            path_part = url.split("#", 1)[0].split("?", 1)[0]
            if is_internal(url) and path_part.endswith("index.html"):
                fail(f"internal index.html href in {rel}: {url}")
        for match in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError as exc:
                fail(f"invalid JSON-LD in {rel}: {exc}")
                continue
            blob = json.dumps(data)
            if "index.html" in blob and "bjornsjeldrup.github.io" in blob:
                fail(f"JSON-LD still mentions index.html in {rel}")
            if "SearchAction" in blob:
                fail(f"SearchAction in {rel}")
            if re.search(r'"@type"\s*:\s*"(Offer|Product)"', blob):
                fail(f"price-bearing schema in {rel}")
            if "price" in blob.lower() and "Offer" in blob:
                fail(f"offer price in {rel}")
        title_match = re.search(r"<title>(.*?)</title>", text, re.S)
        if not title_match:
            fail(f"missing title {rel}")
        else:
            title = html.unescape(re.sub(r"\s+", " ", title_match.group(1)).strip())
            if len(title) > 65:
                fail(f"title {len(title)} chars {rel}: {title}")
            titles.setdefault(title, []).append(rel)
            og = re.search(r'<meta property="og:title" content="([^"]*)"', text)
            if rel in {
                "index.html",
                "trends/sony-mdr-3r.html",
                "press/holiday-2026.html",
                "trend-of-the-week/index.html",
                "trends/air-up-case-study.html",
                "trends/labubu-case-study.html",
                "trends/squeeze-please-scented-marshmallow.html",
            }:
                if not og or html.unescape(og.group(1)) != title:
                    fail(f"og:title does not match title in {rel}")
        if rel == "index.html" and title_match and "Early Trends" not in html.unescape(title_match.group(1)):
            fail("homepage title is missing Early Trends")
        desc = re.search(r'<meta name="description" content="([^"]*)"', text)
        if desc:
            plain = html.unescape(desc.group(1))
            if len(plain) > 160:
                fail(f"description {len(plain)} chars {rel}")
            if re.search(r"People also (?:search|look up|type)", plain, re.I):
                fail(f"description still has a People also tail in {rel}")
            ogd = re.search(r'<meta property="og:description" content="([^"]*)"', text)
            if not ogd or html.unescape(ogd.group(1)) != plain:
                fail(f"og:description does not match meta description in {rel}")
            tw = re.search(r'<meta name="twitter:description" content="([^"]*)"', text)
            if tw and html.unescape(tw.group(1)) != plain:
                fail(f"twitter:description does not match meta description in {rel}")
        canonical = re.search(r'<link rel="canonical" href="([^"]+)"', text)
        expected = expected_canonical(path)
        if not canonical or canonical.group(1) != expected:
            fail(f"canonical {rel}: {canonical.group(1) if canonical else 'missing'} != {expected}")
        elif path.name == "index.html" and not expected.endswith("/"):
            fail(f"index canonical is not a slash URL: {expected}")
        for match in re.finditer(r"<a\b[^>]*>", text, re.I):
            tag = match.group(0)
            href = re.search(r'\bhref\s*=\s*(["\'])([^"\']+)\1', tag, re.I)
            if not href or not is_amazon(html.unescape(href.group(2))):
                continue
            rel_attr = re.search(r'\brel\s*=\s*(["\'])([^"\']*)\1', tag, re.I)
            if not rel_attr or rel_attr.group(2) != "sponsored nofollow noopener":
                fail(f"amazon rel in {rel}: {tag[:180]}")
        imgs = list(re.finditer(r"<img\b[^>]*>", text, re.I))
        for index, match in enumerate(imgs):
            tag = match.group(0)
            if index == 0:
                if re.search(r'\bloading="lazy"', tag):
                    fail(f"first image is lazy in {rel}")
            else:
                if 'loading="lazy"' not in tag or 'decoding="async"' not in tag:
                    fail(f"below-fold image missing lazy/async in {rel}: {tag[:140]}")
        if rel == "index.html":
            if '"@type": "Organization"' not in text or '"@type": "WebSite"' not in text:
                fail("homepage is missing Organization or WebSite JSON-LD")
            if "SearchAction" in text:
                fail("homepage has SearchAction")
        if rel == "about.html":
            if "The site uses Amazon affiliate links." not in text:
                fail("about page is missing present-tense affiliate wording")
            if "As an Amazon Associate we earn from qualifying purchases." not in text:
                fail("about page is missing the Amazon Associate sentence")
            if "In the future it may earn" in text:
                fail("about page still uses future-tense affiliate wording")
        if rel.startswith("trends/") and path.name not in PRODUCT_SKIP:
            blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
            crumbs = None
            posting = None
            for block in blocks:
                try:
                    data = json.loads(block)
                except json.JSONDecodeError:
                    continue
                if data.get("@type") == "BreadcrumbList":
                    crumbs = data
                if data.get("@type") == "BlogPosting":
                    posting = data
            if not crumbs:
                fail(f"product page missing BreadcrumbList {rel}")
            else:
                items = crumbs.get("itemListElement") or []
                if len(items) != 3:
                    fail(f"breadcrumb length {len(items)} in {rel}")
                elif items[0].get("name") != "Home" or not str(items[0].get("item", "")).endswith("/"):
                    fail(f"breadcrumb home is wrong in {rel}")
                elif "/categories/" not in str(items[1].get("item", "")) or str(items[1].get("item", "")).endswith("index.html"):
                    fail(f"breadcrumb category is wrong in {rel}: {items[1].get('item')}")
                elif items[2].get("item") != expected:
                    fail(f"breadcrumb product URL is wrong in {rel}")
            visible = re.search(r'<nav class="crumbs"[^>]*>(.*?)</nav>', text, re.S)
            if not visible or "Home" not in visible.group(1) or "/categories/" not in visible.group(1):
                fail(f"visible breadcrumb is not Home > category > product in {rel}")
            if not posting:
                fail(f"product page missing BlogPosting {rel}")
            else:
                image = posting.get("image")
                if not isinstance(image, str) or "/assets/products/" not in image:
                    fail(f"BlogPosting image is not a product photo in {rel}")
                og_image = re.search(r'<meta property="og:image" content="([^"]+)"', text)
                tw_image = re.search(r'<meta name="twitter:image" content="([^"]+)"', text)
                if not og_image or og_image.group(1) != image:
                    fail(f"og:image is not the product photo in {rel}")
                if not tw_image or tw_image.group(1) != image:
                    fail(f"twitter:image is not the product photo in {rel}")
                if image.startswith(BASE):
                    photo = ROOT / image[len(BASE) :]
                    if not photo.is_file():
                        fail(f"product photo missing {image}")
                modified = posting.get("dateModified")
                if not isinstance(modified, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", modified):
                    fail(f"dateModified is missing or not a date in {rel}")

    for title, owners in titles.items():
        if len(owners) > 1:
            fail(f"duplicate title {title!r}: {', '.join(owners)}")

    for path in ROOT.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"invalid JSON file {path.relative_to(ROOT)}: {exc}")

    sitemap = ROOT / "sitemap.xml"
    try:
        tree = ET.parse(sitemap)
    except ET.ParseError as exc:
        fail(f"sitemap.xml is not valid XML: {exc}")
        tree = None
    if tree is not None:
        for url in tree.findall("sm:url", NS):
            loc = url.findtext("sm:loc", default="", namespaces=NS)
            lastmod = url.findtext("sm:lastmod", default="", namespaces=NS)
            target = loc_to_path(loc)
            if target is None or not target.is_file():
                fail(f"sitemap URL has no file: {loc}")
                continue
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", lastmod or ""):
                fail(f"sitemap lastmod is missing or not a date for {loc}")

    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    if "Sitemap: https://bjornsjeldrup.github.io/early-trends/sitemap.xml" not in robots:
        fail("robots.txt does not reference the absolute sitemap URL")
    key = ROOT / "0aec9157c3884ef681d0e7c8d6180b9a.txt"
    if not key.is_file():
        fail("IndexNow key file is missing")

    for name, limit in (
        ("labubu-shop-window.jpg", 150000),
        ("sony-mdr-3r.jpg", 150000),
        ("fishwife-tinned-fish.jpg", 150000),
    ):
        size = (ROOT / "assets/products" / name).stat().st_size
        if size >= limit:
            fail(f"{name} is {size} bytes, not under 150 KB")

    if errors:
        print(f"{len(errors)} problem(s):")
        for item in errors:
            print(" -", item)
        return 1
    print("ok: no internal index.html hrefs, JSON-LD parses, sitemap files exist")
    return 0


if __name__ == "__main__":
    sys.exit(main())
