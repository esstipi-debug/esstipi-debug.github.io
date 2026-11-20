"""The field notes on the author page, as a shelf (the owner's choice of 2026-11-19: "everything in view").

A title alone does not say what a note is about, so every entry opens with it, in the words of the note's own
description, and then says what the reader takes away. The entries stand under the reader the note is written
for and a filter leaves one reader, with radio buttons and no script. On a phone the list opens one note at a
time; on a wide screen every entry stands open. The fixture builds into a temporary folder, not the repository.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build  # noqa: E402
import home  # noqa: E402
import shelf  # noqa: E402

CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
ENTRY = re.compile(r'<li class="shelf-note">\n(.*?)\n</li>', re.S)
GROUP = re.compile(r'<div class="shelf-group" data-for="([a-z]+)">\n<h3 class="shelf-for">(.*?)</h3>\n'
                   r'<ul class="shelf-list">\n(.*?)\n</ul>\n</div>', re.S)
PICK = re.compile(r'<input class="shelf-pick" type="radio" name="([a-z-]+)" id="([a-z0-9-]+)"( aria-label="[^"]*")?( checked)?>')
NARROW, WIDE = "@media (max-width: 63.99rem)", "@media (min-width: 64rem)"
WORD = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[build.Page]]:
    root = tmp_path_factory.mktemp("site")
    pages = build.load_site()
    build.write_site(pages, root, root / "generated.json")
    return root, pages


def author(site) -> str:
    root, _ = site
    return (root / build.AUTHOR_SLUG / "index.html").read_text(encoding="utf-8")


def shelf_of(site) -> str:
    """The shelf as the author page prints it, from its opening tag to the line of the manuscript under it."""
    return author(site).split('<div class="shelf">', 1)[1].split('<p class="shelf-book">', 1)[0]


def style_sheet(site) -> str:
    return CSS_COMMENT.sub("", (site[0] / "style.css").read_text(encoding="utf-8"))


def media_block(css: str, opening: str) -> str:
    """Everything the style sheet says inside the blocks that open with `opening`."""
    found, start = [], css.find(opening)
    while start >= 0:
        depth, index = 0, css.index("{", start)
        for index in range(index, len(css)):
            depth += (css[index] == "{") - (css[index] == "}")
            if depth == 0:
                break
        found.append(css[css.index("{", start) + 1:index])
        start = css.find(opening, index)
    return "\n".join(found)


def words(text: str) -> list[str]:
    return WORD.findall(html.unescape(text).lower().replace("’", ""))


def test_the_author_page_shelves_every_note_once(site):
    """One entry per note: what it is about, what the reader takes away, its name with the way to its page and
    its file. No summary is printed twice."""
    _, pages = site
    notes = build.notes_of(pages)
    entries = ENTRY.findall(shelf_of(site))
    assert len(entries) == len(notes) >= 2
    page = author(site)
    for note in notes:
        mine = [entry for entry in entries if f'href="../{note.slug}/"' in entry]
        assert len(mine) == 1, note.slug
        entry = mine[0]
        assert re.search(rf'<label class="shelf-about" for="shelf-note-\d+">{re.escape(build.esc(note.about))}</label>', entry), note.slug
        assert f'<p class="shelf-takeaway">{build.esc(note.takeaway)}</p>' in entry, note.slug
        assert f'<a class="shelf-name" href="../{note.slug}/"><em>{build.esc(note.title)}</em></a>' in entry, note.slug
        assert f'<a class="shelf-file" href="{build.esc(note.pdf)}">PDF, {note.pdf_pages} pages</a>' in entry, note.slug
        assert page.count(build.esc(note.about)) == 1 and page.count(build.esc(note.takeaway)) == 1, note.slug


def test_a_note_says_what_it_is_about_in_the_words_of_its_description(site):
    """The two lines of an entry are the note's description, cut in two: the same words in the same order, with
    the label that names the reader left out and, at most, the "and" that joined the two halves."""
    _, pages = site
    for note in build.notes_of(pages):
        label, colon, said = note.description.partition(": ")
        assert colon, note.slug
        about, takeaway = words(note.about), words(note.takeaway)
        assert about and takeaway, note.slug
        assert words(said) in (about + takeaway, about + ["and"] + takeaway), (note.slug, note.about, note.takeaway)
        for line in (note.about, note.takeaway):
            assert line[0].isupper() and line.endswith("."), (note.slug, line)


@pytest.mark.parametrize("key", ["about", "takeaway"])
def test_a_note_without_one_of_its_two_lines_stops_the_build(tmp_path, key):
    source = (build.PAGES_DIR / "the-shortcut-is-not-a-lapse.md").read_text(encoding="utf-8")
    kept = [line for line in source.splitlines() if not line.startswith(f"{key}:")]
    assert len(kept) == len(source.splitlines()) - 1      # the note had the line, and now it does not
    page = tmp_path / "the-shortcut-is-not-a-lapse.md"
    page.write_text("\n".join(kept) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=f"missing {key}"):
        build.load_page(page)


def test_the_notes_stand_under_the_reader_they_are_written_for(site):
    """A group per reader, in the order of the shelf, then the notes that name no reader under the line each
    carries over its title. Inside a group the notes keep the order of the site."""
    _, pages = site
    notes = build.notes_of(pages)
    expected = []
    for reader in shelf.READERS:
        theirs = [note.slug for note in notes if re.search(rf"for the {reader}\b", note.description)]
        if theirs:
            expected.append((reader.lower(), f"For the {reader}", theirs))
    unnamed = [note for note in notes if not re.search(r"for the (CEO|COO|CFO)\b", note.description)]
    for kicker in dict.fromkeys(note.kicker for note in unnamed):
        expected.append(("all", kicker, [note.slug for note in unnamed if note.kicker == kicker]))
    found = [(key, html.unescape(label), re.findall(r'<a class="shelf-name" href="\.\./([a-z0-9-]+)/">', body))
             for key, label, body in GROUP.findall(shelf_of(site))]
    assert found == expected
    assert sum(len(slugs) for _, _, slugs in found) == len(notes)
    assert "<section" not in shelf_of(site)      # a group is part of one section of the page, Writing, not one of its own
    assert {key for key, _, _ in found} >= {reader.lower() for reader in shelf.READERS}   # today, a note for each


def test_one_filter_leaves_one_reader(site):
    """A radio button per reader and one for all of them, which opens the page. The only rule that hides a group
    names the pick of another reader: with every note in view, nothing is hidden."""
    readers = [reader.lower() for reader in shelf.READERS]
    picks = [(name, pick, bool(checked)) for name, pick, _, checked in PICK.findall(shelf_of(site)) if name == "shelf-for"]
    assert picks == [("shelf-for", "shelf-all", True)] + [("shelf-for", f"shelf-{reader}", False) for reader in readers]
    labels = re.search(r'<p class="shelf-filter">(.*?)</p>', shelf_of(site), re.S).group(1)
    assert re.findall(r'<label for="(shelf-[a-z]+)">(.*?)</label>', labels) == \
        [("shelf-all", "All")] + [(f"shelf-{reader}", reader.upper()) for reader in readers]
    for name, pick, label, _ in PICK.findall(shelf_of(site)):
        if name == "shelf-for":      # a short label in view, and the whole of it for whoever does not see the page
            said = {"shelf-all": "All field notes"}.get(pick, f"Field notes for the {pick.removeprefix('shelf-').upper()}")
            assert label == f' aria-label="{said}"', pick
    css = style_sheet(site)
    hides = [selector.strip() for selectors, block in RULE.findall(css) if "display: none" in block
             for selector in selectors.split(",") if ".shelf-group" in selector]
    assert sorted(hides) == sorted(f'#shelf-{reader}:checked ~ .shelf-groups .shelf-group:not([data-for="{reader}"])'
                                   for reader in readers)
    for reader in ("all", *readers):
        assert f'#shelf-{reader}:checked ~ .shelf-filter label[for="shelf-{reader}"]' in css, reader
        assert f'#shelf-{reader}:focus-visible ~ .shelf-filter label[for="shelf-{reader}"]' in css, reader


def test_every_radio_button_stands_before_what_it_rules(site):
    """The selectors reach forward, from a radio button to the siblings after it. So the buttons of the filter
    stand before the groups, as children of the shelf itself, and the button of a note stands first in its
    entry: moved after what it rules, a button would still be on the page and would do nothing."""
    whole = shelf_of(site)
    before_groups, groups = whole.split('<div class="shelf-groups">', 1)
    filters = [pick for name, pick, _, _ in PICK.findall(before_groups) if name == "shelf-for"]
    assert filters and not [name for name, _, _, _ in PICK.findall(groups) if name == "shelf-for"]
    assert before_groups.index('<p class="shelf-filter">') > max(before_groups.index(f'id="{pick}"') for pick in filters)
    assert "<div" not in before_groups and "</div>" not in before_groups      # the buttons, their labels and nothing around them
    for entry in ENTRY.findall(whole):
        assert entry.startswith('<input class="shelf-pick" type="radio" name="shelf-note"'), entry[:60]
        after = [entry.index(part) for part in ('class="shelf-cover"', 'class="shelf-about"', 'class="shelf-takeaway"', 'class="shelf-links"')]
        assert after == sorted(after) and after[0] > 0, entry[:60]


def test_every_note_shows_the_cover_of_its_file(site):
    """The first page of the note's PDF, small, beside what the note is about. It says nothing the entry does
    not say, so it carries no words of its own, and it has its size. The cover of the entry that opens the list
    comes with the page; the others wait to be seen before they are fetched."""
    root, pages = site
    width, height = shelf.COVER_SIZE
    entries = ENTRY.findall(shelf_of(site))
    for note in build.notes_of(pages):
        mine = next(entry for entry in entries if f'href="../{note.slug}/"' in entry)
        waits = "eager" if " checked>" in mine else "lazy"
        tag = (f'<img class="shelf-cover" src="../files/covers/{note.slug}.webp" alt="" width="{width}" '
               f'height="{height}" loading="{waits}" decoding="async">')
        assert sum(tag in entry for entry in entries) == 1, note.slug
        cover = root / "files" / "covers" / f"{note.slug}.webp"
        assert cover.is_file(), note.slug
        data = cover.read_bytes()
        assert data[:4] == b"RIFF" and data[8:12] == b"WEBP", note.slug
        assert len(data) < 16_000, (note.slug, len(data))      # a small picture: ten of them weigh less than one page of the book
    assert sorted(path.stem for path in (root / "files" / "covers").iterdir()) == sorted(note.slug for note in build.notes_of(pages))


def test_a_cover_has_the_size_the_page_states(site):
    pytest.importorskip("PIL")
    from PIL import Image
    root, pages = site
    for note in build.notes_of(pages):
        with Image.open(root / "files" / "covers" / f"{note.slug}.webp") as image:
            assert image.size == shelf.COVER_SIZE, note.slug


def test_a_note_without_its_cover_keeps_its_entry(site, tmp_path, monkeypatch):
    """Pictures gate on their file, like the desk of the home page: where a cover is missing the entry prints
    without one and the page still builds. That every note of the site has its cover is the test above."""
    _, pages = site
    monkeypatch.setattr(build, "FILES_DIR", tmp_path)
    bare = shelf.shelf(pages, 1)
    assert "<img" not in bare and "covers/" not in bare
    assert len(ENTRY.findall(bare)) == len(build.notes_of(pages))
    for note in build.notes_of(pages):
        assert build.esc(note.about) in bare and f'href="../{note.slug}/"' in bare, note.slug


def test_the_shelf_folds_on_a_phone_and_stands_open_on_a_wide_screen(site):
    """On a phone the list opens one note at a time, and the first opens the list. A shut entry still says what
    the note is about and names it: the rules that hide its cover, what it leaves and its file all name a note
    that is not picked, and live under the narrow width. From 64rem up the radio buttons leave the page."""
    notes = [(pick, bool(checked)) for name, pick, _, checked in PICK.findall(shelf_of(site)) if name == "shelf-note"]
    assert [pick for pick, _ in notes] == [f"shelf-note-{number}" for number in range(1, len(notes) + 1)]
    assert [checked for _, checked in notes] == [True] + [False] * (len(notes) - 1)
    css = style_sheet(site)
    narrow, wide = media_block(css, NARROW), media_block(css, WIDE)
    for hidden in (".shelf-pick:not(:checked) ~ .shelf-cover", ".shelf-pick:not(:checked) ~ .shelf-takeaway",
                   ".shelf-pick:not(:checked) ~ .shelf-links .shelf-file"):
        blocks = [block for selectors, block in RULE.findall(narrow) if hidden in [part.strip() for part in selectors.split(",")]]
        assert blocks and any("display: none" in block for block in blocks), hidden
    outside = css.replace(narrow, "")
    for selectors, block in RULE.findall(outside):
        if "display: none" in block or "visibility: hidden" in block or "opacity: 0" in block:
            for selector in (part.strip() for part in selectors.split(",")):
                assert not re.search(r"\.shelf-(cover|about|takeaway|links|name|file)\b", selector), selector
    for selectors, block in RULE.findall(narrow):          # what a shut entry keeps is never hidden
        if "display: none" in block:
            for selector in (part.strip() for part in selectors.split(",")):
                assert not selector.endswith((".shelf-about", ".shelf-name")), selector
    assert re.search(r"\.shelf-note > \.shelf-pick\s*\{[^}]*display: none", wide)
    # With its radio button gone, the line that opened a note is a line of text: nothing to press.
    assert re.search(r"(?<![\w-])\.shelf-about\s*\{[^}]*pointer-events: none", wide)
    assert "pointer-events: none" not in " ".join(block for selectors, block in RULE.findall(outside.replace(wide, ""))
                                                  if ".shelf-about" in selectors)


def test_the_links_of_an_entry_carry_their_own_underline(site):
    """The column of the author page underlines every link in it; the home page does not. The shelf stands on both
    and has to look the same on both, so its links say what they are with no help from the page around them."""
    css = style_sheet(site)

    def blocks(selector: str) -> list[str]:
        return [block for selectors, block in RULE.findall(css) if selector in [part.strip() for part in selectors.split(",")]]

    assert any("text-decoration: underline" in block and "text-decoration-color: var(--accent)" in block
               for block in blocks(".shelf-links a"))
    assert any("color: var(--accent)" in block for block in blocks(".shelf-links a:hover"))


def test_the_shelf_leaves_the_reading_column(site):
    """The page is a column of text; the shelf is wider than it, and everything else stays in the column."""
    css = style_sheet(site)
    assert re.search(r"main\.wrap > article:has\(\.shelf\)\s*\{[^}]*max-width: none", css)
    assert re.search(r"main\.wrap > article:has\(\.shelf\) > :not\(\.shelf\)\s*\{[^}]*max-width: 44rem", css)


def test_the_manuscript_stands_under_the_shelf(site):
    page = author(site)
    assert '<h2 id="writing">Writing</h2>\n<div class="shelf">' in page
    after = page.split('<div class="shelf">', 1)[1]
    line = f'<p class="shelf-book"><a href="../{build.BOOK_SLUG}/"><em>The Deployment Chasm</em></a>, a manuscript</p>'
    assert line in after and after.index(line) < after.index("<h2>Contact</h2>")
    assert "<ul>" not in page.split('<h2 id="writing">', 1)[1].split("<h2>Contact</h2>", 1)[0]     # the plain list is gone


def test_the_home_page_lays_its_notes_out_with_the_shelf_and_keeps_nothing_of_its_table(site):
    """One pattern says who a note is written for, in shelf.py. The home page lays its notes out with the shelf
    (a test of test_commercial.py checks that the page carries it) and has neither that pattern nor the table
    it showed before: no code and no rule is left behind for it."""
    source = Path(home.__file__).read_text(encoding="utf-8")
    assert not re.search(r"^READER\s*=", source, re.M) and "for the (CEO" not in source
    assert "shelf.shelf(" in source and "note_row" not in source and "INDEX_HEADS" not in source
    css = CSS_COMMENT.sub("", (site[0] / "home.css").read_text(encoding="utf-8"))
    assert not re.search(r"\.index\b|\.ix-", css)
    assert set(shelf.READERS) == set(re.findall(r"[A-Z]{3}", shelf.READER.pattern))


def pdf_of(folder: Path, slug: str, pages: int, size: tuple[float, float] = (810, 1012.5)) -> None:
    fitz = pytest.importorskip("fitz")
    with fitz.open() as doc:
        for _ in range(pages):
            doc.new_page(width=size[0], height=size[1])
        doc.save(folder / f"{slug}.pdf")


def test_the_covers_are_the_first_page_of_each_file(site, tmp_path):
    pytest.importorskip("fitz")
    pytest.importorskip("PIL")
    from PIL import Image
    _, pages = site
    papers, out = tmp_path / "papers", tmp_path / "covers"
    papers.mkdir()
    for note in build.notes_of(pages):
        pdf_of(papers, note.slug, note.pdf_pages)
    written = shelf.generate_covers(papers, out)
    assert sorted(path.name for path in written) == sorted(f"{note.slug}.webp" for note in build.notes_of(pages))
    for path in written:
        with Image.open(path) as image:
            assert image.size == shelf.COVER_SIZE and image.format == "WEBP", path.name


def test_a_file_that_is_not_the_one_the_note_states_writes_no_cover(site, tmp_path):
    """A PDF that is missing, or that does not have the pages the note states, stops the run before any cover
    is written: an old copy of a file must not give the page its picture."""
    pytest.importorskip("fitz")
    pytest.importorskip("PIL")
    _, pages = site
    notes = build.notes_of(pages)
    papers, out = tmp_path / "papers", tmp_path / "covers"
    papers.mkdir()
    for note in notes[1:]:
        pdf_of(papers, note.slug, note.pdf_pages)
    with pytest.raises(ValueError, match=rf"{notes[0].slug}: no {notes[0].slug}\.pdf"):
        shelf.generate_covers(papers, out)
    pdf_of(papers, notes[0].slug, notes[0].pdf_pages + 1)
    with pytest.raises(ValueError, match=rf"{notes[0].slug}: .* has {notes[0].pdf_pages + 1} pages and the note states {notes[0].pdf_pages}"):
        shelf.generate_covers(papers, out)
    pdf_of(papers, notes[0].slug, notes[0].pdf_pages, size=(800, 800))      # the right pages, on a square sheet
    with pytest.raises(ValueError, match=rf"{notes[0].slug}: the first page .* is not 4:5"):
        shelf.generate_covers(papers, out)
    assert not out.exists() or not list(out.iterdir())
