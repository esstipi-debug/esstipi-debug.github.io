"""What a finger has to hit is at least 44px tall (2.75rem), also where the letters are small.

Three cases the audit of 2026-11-19 found on the reading pages: a list whose items are links, a link that is
most of a small line (a source, an origin, a byline), and the page pills of the book reader. A link inside a
sentence is not one of them. The fixture builds into a temporary folder, not the repository.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build  # noqa: E402

TAP = "2.75rem"            # 44px at the default size of the type
REACH = 0.8                # in rem: what a small line's link adds above and below its letters to get there
CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
SMALL_LINES = (".src a", ".origin a", ".byline a")


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[build.Page]]:
    root = tmp_path_factory.mktemp("site")
    pages = build.load_site()
    build.write_site(pages, root, root / "generated.json")
    return root, pages


def read(site, slug: str) -> str:
    root, pages = site
    return (root / build.find(pages, slug).path / "index.html").read_text(encoding="utf-8")


def declarations(site, selector: str) -> str:
    """Everything the style sheet declares for a selector, wherever it stands in a list of selectors."""
    css = CSS_COMMENT.sub("", (site[0] / "style.css").read_text(encoding="utf-8"))
    found = [block for selectors, block in RULE.findall(css)
             if selector in [part.strip() for part in selectors.split(",")]]
    assert found, selector
    return " ".join(found)


def test_a_list_of_links_gives_each_link_a_row(site):
    root, pages = site
    notes = [note for note in build.notes_of(pages) if build.questions_of(pages, note.slug)]
    assert notes
    for note in notes:
        assert '<h2>Questions these field notes answer</h2>\n<ul class="links">' in read(site, note.slug), note.slug
    hiring = read(site, build.AUTHOR_SLUG).split("If you are hiring</h2>", 1)[1].split("<h2", 1)[0]
    assert re.search(r'<div class="links">\s*<ul>', hiring)
    assert re.search(r'<div class="links">\s*<ul>\s*<li>Email: <a href="mailto:', read(site, "contact"))
    assert f"min-height: {TAP}" in declarations(site, ".links a")
    assert "margin: 0" in declarations(site, ".links li")       # the row is the link's height, with no gap to miss


def test_a_link_that_is_most_of_a_small_line_reaches_past_its_letters(site):
    for selector in SMALL_LINES:
        reach = re.search(r"padding-block:\s*([\d.]+)rem", declarations(site, selector))
        assert reach and float(reach.group(1)) >= REACH, selector


def test_the_pills_of_the_book_reader_are_tall_enough(site):
    for selector in (".book-pill", ".book-pill-m"):
        assert f"min-height: {TAP}" in declarations(site, selector), selector


def test_the_page_pills_of_a_phone_share_one_row(site):
    """Seven pills do not fit side by side at their full width on a narrow phone: they share the row and
    narrow together, so that none is left alone on a second line."""
    row = declarations(site, ".book-nav-mob .book-pills")
    assert "grid-auto-flow: column" in row and "grid-auto-columns: minmax(0," in row


def test_a_link_of_two_lines_keeps_air_around_it(site):
    """In a list of links, a link that wraps is taller than 44px: it still keeps a little air above and below,
    so that two of them do not run together."""
    assert re.search(r"padding-block:\s*\.\d+rem", declarations(site, ".links a"))
