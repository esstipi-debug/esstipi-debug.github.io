"""The proof and engagements pages as working drawings (the owner's choice of 2026-11-19).

Rows and lines in place of boxes: figures that jump to their section, lists that fold on a phone, the claims
drawing shared with the home page, the engagements as a rate sheet, and what happens after the work drawn as
two spans on one scale. The fixture builds into a temporary folder, not the repository.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build  # noqa: E402
import page_parts  # noqa: E402
import risks  # noqa: E402

CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
FIGURE_ROW = re.compile(r'<a class="fig" href="#([a-z-]+)"><span class="fig-g">(.*?)</span><span class="fig-n">(.*?)</span>'
                        r'<span class="fig-t">(.*?)</span><span class="fig-go">(.*?)</span></a>', re.S)
HEADLINE_FIGURES = ("50,000", "USD 30M", "2,708", "10,756")   # the four the proof page opens with, in its order
BUTTON = re.compile(r'<p class="actions"><a class="btn btn-contact" href="([^"]+)">(.*?)</a></p>')
CLOSING = re.compile(r'<p class="page-close"><a class="page-close-link" href="([^"]+)">(.*?)</a></p>')
ROW = re.compile(r"<li><details class=\"row\"( open)?><summary><strong>(.*?)</strong></summary><p>(.*?)</p></details></li>", re.S)
CLAIMS = re.compile(r'<span class="claims" role="img".*?</svg>.*?</span>\n</span>', re.S)
SPAN = re.compile(r'<span class="after-from">(.*?)</span>\s*<span class="after-span[^"]*" style="--days: (\d+)">'
                  r'<span class="cota"><span>(.*?)</span></span></span>', re.S)
BODY = re.compile(r'<div class="eng-body">\s*<div class="eng-name"><h2>(.*?)</h2><p class="eng-idx">(.*?)</p></div>\s*'
                  r'<p class="eng-price">(.*?)</p>\s*<div class="eng-text">(.*?)</div>\s*<div class="eng-deal">(.*?)</div>\s*</div>',
                  re.S)
DAYS_IN = {"days": 1, "months": 365 / 12}   # a span is drawn in days: its label says how many, in days or months
OLD_CLASSES = ("proof-strip", "proof-kpi", "band-deep", "band-panel", "plate-card", "track-grid", "sys-grid",
               "audit-spotlight", "audit-bar", "audit-legend", "promise-grid", "promise-card", "eng-art", "eng-head")


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[build.Page]]:
    root = tmp_path_factory.mktemp("site")
    pages = build.load_site()
    build.write_site(pages, root, root / "generated.json")
    return root, pages


def read(site, slug: str) -> str:
    root, pages = site
    return (root / build.find(pages, slug).path / "index.html").read_text(encoding="utf-8")


def words_of(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def style_sheet(site) -> str:
    return CSS_COMMENT.sub("", (site[0] / "style.css").read_text(encoding="utf-8"))


def media_block_of(css: str, needle: str) -> str:
    """The condition of the @media block a rule stands in, or an empty string when it stands in none."""
    before = css[:css.index(needle)]
    opened = before.rfind("@media")
    if opened < 0 or before.count("{", opened) - before.count("}", opened) < 1:
        return ""
    return before[opened:].split("{", 1)[0].removeprefix("@media").strip()


# ---------------------------------------------------------------- the proof page

def test_the_proof_figures_carry_their_grade_and_jump_to_their_section(site):
    text = read(site, "proof")
    listed = text.split('<div class="fig-list fig-jumps"', 1)[1].split("</div>", 1)[0]
    rows = FIGURE_ROW.findall(listed)
    assert [number for _, _, number, _, _ in rows] == list(HEADLINE_FIGURES), listed[:200]
    grades = set(build.FIGURE_GRADES) | set(risks.GRADES)
    for anchor, grade, _, _, label in rows:
        assert html.unescape(grade) in grades, grade
        heading = re.search(rf'<h2 id="{anchor}">(.*?)</h2>', text)
        assert heading and heading.group(1) == label, (anchor, label)   # the jump says where it lands


def test_the_proof_button_stands_under_the_headline_and_the_close_repeats_it(site):
    text = read(site, "proof")
    button, closing = BUTTON.search(text), CLOSING.search(text)
    assert button and closing
    assert text.index("</hgroup>") < button.start() < text.index('class="fig-list')
    assert (closing.group(1), closing.group(2)) == (button.group(1), button.group(2))   # one address, the same words
    assert text.index("Writing</h2>") < closing.start()
    assert "<!-- contact -->" not in text


def test_a_page_without_the_contact_marker_keeps_its_button_at_the_end(site):
    text = read(site, "engagements")
    assert not CLOSING.search(text)
    assert text.index("Best fit</h2>") < BUTTON.search(text).start()


def test_field_work_and_the_systems_are_rows_that_fold(site):
    text = read(site, "proof")
    lists = re.findall(r'<ul class="rows">(.*?)</ul>', text, re.S)
    assert [len(ROW.findall(rows)) for rows in lists] == [5, 4]
    for rows in lists:
        found = ROW.findall(rows)
        assert len(found) == rows.count("<li>")                       # every item is a row, none is left as it was
        assert [bool(is_open) for is_open, _, _ in found] == [True] + [False] * (len(found) - 1)
        assert all(title.strip() and body.strip() for _, title, body in found)
    field_work = text.split('id="track-record"', 1)[1].split("</section>", 1)[0]
    assert '<ul class="rows">' in field_work and "independent consulting" in field_work


def test_the_rows_stand_open_on_a_wide_screen(site):
    css = style_sheet(site)
    forced = ".row::details-content { content-visibility: visible; }"
    assert forced in css
    assert media_block_of(css, forced).startswith("(min-width:")
    assert "@supports selector(::details-content)" in css[:css.index(forced)]


def test_rows_are_made_from_a_marked_list_and_nothing_else():
    marked = '<div class="rows">\n<ul>\n<li><strong>One.</strong> First body.</li>\n<li><strong>Two.</strong> Second <em>body</em>.</li>\n</ul>\n</div>'
    made = page_parts.fold_rows(marked)
    assert ROW.findall(made) == [(" open", "One.", "First body."), ("", "Two.", "Second <em>body</em>.")]
    assert made.startswith('<ul class="rows">') and "<div" not in made
    plain = "<ul>\n<li><strong>One.</strong> First body.</li>\n</ul>"
    assert page_parts.fold_rows(plain) == plain
    with pytest.raises(ValueError, match="a row needs a title in bold"):
        page_parts.fold_rows('<div class="rows">\n<ul>\n<li>No title here.</li>\n</ul>\n</div>')


def test_the_proof_page_draws_the_claims_as_the_home_page_does(site):
    proof, home = read(site, "proof"), read(site, "index")
    audit = proof.split('id="sample-audit"', 1)[1].split("</section>", 1)[0]
    drawing = CLAIMS.search(audit)
    assert drawing and drawing.group(0) in home                       # one drawing, made once
    widths = [int(width) for width in re.findall(r'<rect class="seg-[a-z]+" x="\d+" y="0" width="(\d+)"', drawing.group(0))]
    assert widths == [count for _, _, count in build.CLAIMS_TRIAGE]
    assert "Lengths to scale." in words_of(audit)
    assert "<!-- drawing:" not in proof


def test_the_audit_headline_is_the_share_the_counts_give(site):
    audit = read(site, "proof").split('id="sample-audit"', 1)[1].split("</section>", 1)[0]
    (_, _, late), (_, _, flagged), (_, _, rest) = build.CLAIMS_TRIAGE
    total = late + flagged + rest
    assert f'<span class="audit-big">{round(100 * late / total)}%</span>' in audit
    assert f"of {total:,} " in words_of(re.search(r'<span class="audit-sub">(.*?)</span>', audit, re.S).group(1))


def test_an_unknown_drawing_marker_stops_the_build():
    with pytest.raises(ValueError, match="unknown drawing 'hexagon'"):
        page_parts.with_drawings("<p>A</p>\n<!-- drawing: hexagon -->\n", pages=[])


def test_each_block_of_the_two_pages_is_a_section_with_its_heading(site):
    proof, engagements = read(site, "proof"), read(site, "engagements")
    heads = lambda text: [html.unescape(head) for head in re.findall(r'<section class="band">\s*<h2[^>]*>(.*?)</h2>', text)]
    assert heads(proof) == ["What each claim rests on", "Field work", "Published audit you can re-run", "Built systems", "Writing"]
    assert heads(engagements) == ["After the work", "Who to hire for what"]
    root, pages = site
    for page in pages:
        text = (root / page.path / "index.html").read_text(encoding="utf-8")
        classes = {token for value in re.findall(r'class="([^"]+)"', text) for token in value.split()}
        assert not classes & set(OLD_CLASSES), (page.slug, sorted(classes & set(OLD_CLASSES)))


# ---------------------------------------------------------------- the engagements page

def test_each_engagement_is_a_line_of_a_rate_sheet(site):
    root, pages = site
    text = read(site, "engagements")
    bodies = BODY.findall(text)
    offers = build.find(pages, "engagements").offers
    assert [html.unescape(name) for name, _, _, _, _ in bodies] == [offer.name for offer in offers[:len(bodies)]]
    assert len(bodies) == text.count('<article class="eng-card"') == 4
    for (_, terms, price, what, deal), offer in zip(bodies, offers):
        assert terms.strip() and what.strip()
        assert f"USD {offer.amount:,}" in price, offer.name
        assert len(re.findall(r'<a class="eng-cta" href="mailto:', deal)) == 1, offer.name   # how it is paid, then the link
        assert "eng-cta" not in what


def test_the_engagements_stand_open_on_a_wide_screen_and_fold_on_a_phone(site):
    css = style_sheet(site)
    gone = ".eng-pick, .eng-hit, .eng-rail { display: none; }"
    assert gone in css and media_block_of(css, gone) == "(min-width: 62rem)"   # no radio button to tab through there
    for number in "1234":
        gives_way = f':where(#eng-{number}:checked) ~ .eng-cards .eng-card:not([data-card="{number}"]) .eng-body'
        assert media_block_of(css, gives_way) == "(max-width: 61.99rem)", number   # nothing gives way on a wide screen


def test_after_the_work_draws_its_two_spans_on_one_scale(site):
    text = read(site, "engagements")
    section = text.split("After the work</h2>", 1)[1].split("</section>", 1)[0]
    figure = section.split('<figure class="after">', 1)[1].split("</figure>", 1)[0]
    rows = section.split('<div class="after-rows">', 1)[1]
    spans = SPAN.findall(figure)
    assert len(spans) == 2
    said = words_of(rows).lower()
    for start, days, label in spans:
        amount, unit = label.split()
        assert int(days) == round(int(amount) * DAYS_IN[unit]), label          # the width is the label, in days
        assert start.lower() in said, start                                   # each span starts where its promise says
    assert sorted(int(days) for _, days, _ in spans) == [90, 365]
    assert "Lengths to scale." in words_of(figure)
    drawing = re.search(r'<div\b[^>]*\bclass="after-dwg"[^>]*>', figure).group(0)   # Markdown reorders the attributes
    said_aloud = re.search(r'aria-label="([^"]+)"', drawing).group(1)
    assert 'role="img"' in drawing and all(label in said_aloud for _, _, label in spans)
    assert rows.count('<div class="after-row">') == 3                         # the three promises, one row each
    assert re.findall(r'<span class="after-k">(.*?)</span>', rows) == ["90 days", "No fee", "20% less"]
