#!/usr/bin/env python3
"""Assert the SEO surface of conjugo.me is intact.

Run after changing pages, front matter, _config.yml or the layout:

    bundle exec jekyll build && python3 script/check-seo.py

Exits non-zero listing what is wrong. Modelled on the trinitysports
`seo-surface` skill, which exists because /sitemap.xml 404'd in production for
weeks while working locally — nobody checks a file they assume is generated.

No third-party dependencies: this must run anywhere, including CI, without a
virtualenv.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "_site"

# Google truncates meta descriptions past roughly this width; a cut-off
# sentence in a search result is a self-inflicted wound.
MAX_DESCRIPTION = 157

# Image weight budget. The site once shipped one 1 MB, 1024px PNG as its
# favicon, touch icon AND social card, plus a 990 KB hero screenshot shown at
# 280px — every visit downloaded ~2 MB of pixels nobody could see.
MAX_IMAGE_BYTES = 150 * 1024
MAX_FAVICON_BYTES = 8 * 1024
OG_SIZE = (1200, 630)
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".ico"}

failures: list[str] = []


def fail(message: str) -> None:
    failures.append(message)


def page_files() -> list[Path]:
    """Every built HTML page."""
    return sorted(SITE.rglob("*.html"))


def url_for(path: Path) -> str:
    rel = path.relative_to(SITE)
    if rel.name == "index.html":
        parent = str(rel.parent)
        return "/" if parent == "." else f"/{parent}/"
    return f"/{rel}"


def main() -> int:
    if not SITE.is_dir():
        print("_site does not exist — run `bundle exec jekyll build` first.")
        return 1

    # --- the three files that must exist and be reachable -------------------
    for name in ("sitemap.xml", "robots.txt", "llms.txt"):
        if not (SITE / name).is_file():
            fail(f"/{name} was not generated")

    if failures:
        for f in failures:
            print(f"✗ {f}")
        return 1

    sitemap = (SITE / "sitemap.xml").read_text()
    robots = (SITE / "robots.txt").read_text()
    llms = (SITE / "llms.txt").read_text()

    sitemap_urls = set(re.findall(r"<loc>([^<]+)</loc>", sitemap))

    # --- robots points at the sitemap --------------------------------------
    if "Sitemap:" not in robots:
        fail("robots.txt does not declare a Sitemap:")
    for url in re.findall(r"Sitemap:\s*(\S+)", robots):
        if not url.endswith("/sitemap.xml"):
            fail(f"robots.txt Sitemap: points somewhere unexpected — {url}")

    # --- every real page is in the sitemap and in llms.txt ------------------
    for path in page_files():
        html = path.read_text()
        url = url_for(path)
        full = f"https://conjugo.me{url}"

        # 404 pages and anything deliberately noindexed are exempt.
        if 'name="robots" content="noindex' in html:
            continue

        if full not in sitemap_urls:
            fail(f"{url} is missing from sitemap.xml")
        if full not in llms:
            fail(f"{url} is missing from llms.txt")

        # --- exactly one of each head tag that must not be duplicated ------
        for tag, pattern in (
            ("canonical", r'<link rel="canonical"'),
            ("og:title", r'property="og:title"'),
            ("title", r"<title>"),
        ):
            count = len(re.findall(pattern, html))
            if count != 1:
                fail(f"{url} has {count} {tag} tags, expected exactly 1")

        # --- meta description present and not over-long --------------------
        match = re.search(r'<meta name="description" content="([^"]*)"', html)
        if not match:
            fail(f"{url} has no meta description")
        elif len(match.group(1)) > MAX_DESCRIPTION:
            fail(
                f"{url} meta description is {len(match.group(1))} chars, "
                f"over the {MAX_DESCRIPTION} Google will show"
            )

        # --- every JSON-LD block must parse --------------------------------
        for i, block in enumerate(
            re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        ):
            try:
                data = json.loads(block)
            except json.JSONDecodeError as exc:
                fail(f"{url} JSON-LD block {i} is not valid JSON — {exc}")
                continue

            # Checked against the parsed structure, not the raw HTML: an
            # explanatory comment mentioning a property is not the same as
            # declaring it, and the first version of this check confused the two.
            if isinstance(data, dict) and "aggregateRating" in data:
                fail(
                    f"{url} JSON-LD declares an aggregateRating — only keep this "
                    "if the App Store rating is real and current"
                )

    # --- image weight: nothing served may blow the budget -----------------
    for img in sorted(p for p in SITE.rglob("*") if p.suffix.lower() in IMAGE_EXTS):
        size = img.stat().st_size
        rel = img.relative_to(SITE)
        limit = MAX_FAVICON_BYTES if img.name.startswith("favicon") else MAX_IMAGE_BYTES
        if size > limit:
            fail(f"/{rel} is {size // 1024} KB, over the {limit // 1024} KB budget")

    # --- every <img> reserves its space, or the page jumps as it loads ----
    for path in page_files():
        html = path.read_text()
        for tag in re.findall(r"<img\b[^>]*>", html):
            if not (re.search(r'\swidth="\d+"', tag) and re.search(r'\sheight="\d+"', tag)):
                src = re.search(r'src="([^"]+)"', tag)
                fail(f"{url_for(path)} has an <img> without width/height: {src.group(1) if src else tag[:60]}")

    # --- the social card is a real card, and it exists --------------------
    home_html = (SITE / "index.html").read_text()
    og = re.search(r'<meta property="og:image" content="([^"]+)"', home_html)
    if not og:
        fail("homepage has no og:image")
    else:
        local = SITE / og.group(1).replace("https://conjugo.me/", "")
        if not local.is_file():
            fail(f"og:image points at a file that is not built: {og.group(1)}")
        w = re.search(r'<meta property="og:image:width" content="(\d+)"', home_html)
        h = re.search(r'<meta property="og:image:height" content="(\d+)"', home_html)
        declared = (int(w.group(1)), int(h.group(1))) if w and h else None
        if declared != OG_SIZE:
            fail(f"og:image declares {declared}, expected {OG_SIZE} — Slack and "
                 "LinkedIn render summary_large_image cards at this ratio")

    # --- IndexNow key file is published and matches the configured key ---
    config = (SITE.parent / "_config.yml").read_text()
    key_m = re.search(r'^indexnow_key:\s*"([0-9a-f]{32})"', config, re.M)
    if key_m:
        key_file = SITE / f"{key_m.group(1)}.txt"
        if not key_file.is_file():
            fail(f"IndexNow key file /{key_file.name} is not published")
        elif key_file.read_text().strip() != key_m.group(1):
            fail("IndexNow key file content does not match indexnow_key")

    # --- the homepage carries the app schema and a real store link ---------
    home = (SITE / "index.html").read_text()
    if "MobileApplication" not in home:
        fail("homepage is missing the MobileApplication JSON-LD")
    if "apps.apple.com" not in home:
        fail("homepage has no App Store link")
    if 'href="#"' in home:
        fail("homepage still contains a placeholder href=\"#\"")

    # --- sitemap must not list anything that does not exist ----------------
    built = {url_for(p) for p in page_files()}
    for url in sitemap_urls:
        path = url.replace("https://conjugo.me", "") or "/"
        if path not in built:
            fail(f"sitemap lists {path}, which is not a built page")

    if failures:
        print(f"✗ SEO surface has {len(failures)} problem(s):\n")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(
        f"✓ SEO surface intact — {len(page_files())} pages, "
        f"{len(sitemap_urls)} in sitemap, robots + llms.txt agree"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
