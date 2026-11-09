"""Checks on the built site. The fixture builds into a temporary folder, not the repository."""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build  # noqa: E402

PRODUCT_NAMES = re.compile(r"\b(kern|narvi|narya|mellon|nosilo|cockpit)\b", re.I)
JSONLD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
QUESTION_SECTIONS = ("How it works", "Evidence", "What this does not prove", "Sources")


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[build.Page]]:
    root = tmp_path_factory.mktemp("site")
    pages = build.load_site()
    build.write_site(pages, root, root / "generated.json")
    return root, pages


def read(root: Path, page: build.Page) -> str:
    return (root / page.path / "index.html").read_text(encoding="utf-8")


def structured(text: str) -> dict:
    return json.loads(JSONLD.search(text).group(1))


def test_builds_every_page_type(site):
    _, pages = site
    assert {page.kind for page in pages} == set(build.PAGE_TYPES)


def test_question_pages_lead_with_the_answer(site):
    root, pages = site
    for page in build.questions_of(pages):
        text = read(root, page)
        after_byline = text.split('<p class="byline">', 1)[1].split("</p>", 1)[1]
        assert after_byline.lstrip().startswith('<p class="answer">'), page.slug
        for heading in QUESTION_SECTIONS:
            assert f"<h2>{heading}</h2>" in text, (page.slug, heading)


def test_question_pages_cite_a_source_with_a_link(site):
    root, pages = site
    for page in build.questions_of(pages):
        assert any(citation.url for citation in page.cites), page.slug
        assert re.search(r'<ul class="sources">.*?<a href="https://', read(root, page), re.S), page.slug


def test_pages_name_the_author_and_the_date(site):
    root, pages = site
    for page in pages:
        if page.kind in ("question", "note"):
            text = read(root, page)
            assert 'href="../marcos-stipicich/">Marcos Stipicich</a>' in text, page.slug
            assert f'<time datetime="{page.published.isoformat()}">' in text, page.slug


def test_structured_data(site):
    root, pages = site
    expected = {"home": "WebSite", "question": "Article", "note": "Article",
                "author": "ProfilePage", "book": "Book"}
    for page in pages:
        data = structured(read(root, page))
        assert data["@context"] == "https://schema.org"
        assert data["@type"] == expected[page.kind], page.slug
        person = data.get("author") or data.get("mainEntity")
        assert person["name"] == "Marcos Stipicich"
        assert build.LINKEDIN in person["sameAs"]
        if page.kind == "question":
            assert data["citation"] and data["isBasedOn"].startswith("https://")


def test_head_tags(site):
    root, pages = site
    for page in pages:
        text = read(root, page)
        assert '<html lang="en">' in text
        assert f'<link rel="canonical" href="{page.url}">' in text
        assert '<meta name="color-scheme" content="dark">' in text
        assert "noindex" not in text
        description = re.search(r'<meta name="description" content="([^"]*)">', text).group(1)
        assert 50 <= len(html.unescape(description)) <= 160, (page.slug, len(description))


def test_robots_lets_search_and_training_bots_in(site):
    root, _ = site
    lines = (root / "robots.txt").read_text(encoding="utf-8").splitlines()
    for bot in (*build.SEARCH_BOTS, *build.TRAINING_BOTS, "*"):
        assert f"User-agent: {bot}" in lines
    assert "Allow: /" in lines
    assert "Disallow: /" not in lines
    assert "Disallow: /src/" in lines
    assert f"Sitemap: {build.SITE_URL}/sitemap.xml" in lines


def test_sitemap_lists_every_page(site):
    root, pages = site
    locs = re.findall(r"<loc>(.*?)</loc>", (root / "sitemap.xml").read_text(encoding="utf-8"))
    assert sorted(locs) == sorted(page.url for page in pages)
    assert all(loc.startswith("https://") and loc.endswith("/") for loc in locs)


def test_no_product_names(site):
    root, _ = site
    for path in root.rglob("*.html"):
        assert not PRODUCT_NAMES.search(path.read_text(encoding="utf-8")), path


def test_question_pages_do_not_link_to_each_other(site):
    root, pages = site
    questions = build.questions_of(pages)
    for page in questions:
        text = read(root, page)
        for other in questions:
            if other.slug != page.slug:
                assert f'href="../{other.path}"' not in text, (page.slug, other.slug)


def test_internal_links_resolve(site):
    root, _ = site
    for path in root.rglob("index.html"):
        for target in re.findall(r'href="([^"#]*)(?:#[^"]*)?"', path.read_text(encoding="utf-8")):
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (path.parent / target).resolve()
            if target.endswith("/"):
                resolved = resolved / "index.html"
            assert resolved.exists(), (path, target)


def test_theme_is_dark_only(site):
    root, _ = site
    css = (root / "style.css").read_text(encoding="utf-8")
    assert "color-scheme: dark" in css
    assert "prefers-color-scheme" not in css


def test_stale_folders_are_removed(tmp_path):
    pages = build.load_site()
    manifest = tmp_path / "generated.json"
    stale = tmp_path / "old-page"
    stale.mkdir()
    (stale / "index.html").write_text("old", encoding="utf-8")
    manifest.write_text(json.dumps(["old-page"]), encoding="utf-8")
    build.write_site(pages, tmp_path, manifest)
    assert not stale.exists()
    assert "old-page" not in json.loads(manifest.read_text(encoding="utf-8"))


def test_front_matter_errors_are_explicit(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("no front matter here\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing front matter"):
        build.load_page(bad)
