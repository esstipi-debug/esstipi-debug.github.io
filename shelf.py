#!/usr/bin/env python3
"""The field notes on the author page, as a shelf.

Usage (make the cover of every note again, from a folder that holds each PDF as <slug>.pdf):
    python shelf.py <folder>

A title alone does not say what a note is about. So each entry opens with it ("about" in the note's front
matter), says what the reader takes away ("takeaway"), and then gives the note's name, with the way to its
page, and its file. The entries stand under the reader the note is written for, and a filter leaves one reader:
radio buttons and the selectors of style.css, with no script. On a phone the list opens one note at a time and
a shut entry still says what the note is about; on a wide screen every entry stands open.

Nothing is printed twice: the line that says what a note is about is also the label of its radio button. The
cover is the first page of the note's PDF, kept small in src/files/covers/; build.py imports this module late,
inside author_main().
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import build
from build import Page, esc, href

READER = re.compile(r"for the (CEO|COO|CFO)\b")     # a field note says who it is written for
READERS = ("CEO", "CFO", "COO")                     # the order of the shelf; style.css has a rule for each
EVERYONE = "all"                                    # the pick that shows every note, and the group of a note that names no reader
COVERS_DIR_NAME = "covers"
COVER_SIZE = (216, 270)                             # a note's page is 4:5; the shelf shows it at about a third of this
COVER_OVERSAMPLE = 3                                # the page is drawn larger and brought down, so the small type stays clean
COVER_SHAPE_SLACK = 0.01                            # how far from 4:5 a first page may be before its cover would look stretched
WEBP_QUALITY = 80


def reader_of(note: Page) -> str | None:
    found = READER.search(note.description)
    return found.group(1) if found else None


def groups(notes: list[Page]) -> list[tuple[str, str, list[Page]]]:
    """(key, label, notes): a group for each reader, in the order of READERS, then the notes that name no reader,
    under the line each carries over its title. Inside a group the notes keep the order of the site."""
    named = [(reader.lower(), f"For the {reader}", [note for note in notes if reader_of(note) == reader])
             for reader in READERS]
    unnamed: dict[str, list[Page]] = {}
    for note in notes:
        if reader_of(note) is None:
            unnamed.setdefault(note.kicker or "Field notes", []).append(note)
    return [group for group in named if group[2]] + [(EVERYONE, label, theirs) for label, theirs in unnamed.items()]


def cover_path(note: Page) -> Path:
    return build.FILES_DIR / COVERS_DIR_NAME / f"{note.slug}.webp"


def cover(note: Page, depth: int, opens: bool) -> str:
    """The picture of the note's first page. It repeats the entry, so it carries no words of its own. The cover
    of the entry that opens the list comes with the page; the others wait until they are about to be seen.
    Nothing while the file is missing: a picture gates on its file, like the desk of the home page, and the
    tests say whether every note of the site has its cover."""
    if not cover_path(note).is_file():
        return ""
    width, height = COVER_SIZE
    return (f'<img class="shelf-cover" src="{href(f"files/{COVERS_DIR_NAME}/{note.slug}.webp", depth)}" alt="" '
            f'width="{width}" height="{height}" loading="{"eager" if opens else "lazy"}" decoding="async">')


def entry(note: Page, number: int, depth: int) -> str:
    """One note. The first opens the list on a phone; the line that says what the note is about opens the rest."""
    pick, opens = f"shelf-note-{number}", number == 1
    lines = (
        '<li class="shelf-note">',
        f'<input class="shelf-pick" type="radio" name="shelf-note" id="{pick}"{" checked" if opens else ""}>',
        cover(note, depth, opens),
        f'<label class="shelf-about" for="{pick}">{esc(note.about or "")}</label>',
        f'<p class="shelf-takeaway">{esc(note.takeaway or "")}</p>',
        f'<p class="shelf-links"><a class="shelf-name" href="{href(note.path, depth)}"><em>{esc(note.title)}</em></a>'
        f'{build.pdf_link(note, "shelf-file")}</p>',
        "</li>",
    )
    return "\n".join(line for line in lines if line)


def reader_filter(keys: list[str]) -> str:
    """The radio buttons that leave one reader, and their labels. The buttons stand before the groups, as their
    siblings, so that a selector can reach both. The label in view is short; the button says the whole of it."""
    picks = [(EVERYONE, "All", "All field notes")]
    picks += [(reader.lower(), reader, f"Field notes for the {reader}") for reader in READERS if reader.lower() in keys]
    buttons = "\n".join(f'<input class="shelf-pick" type="radio" name="shelf-for" id="shelf-{key}" '
                        f'aria-label="{said}"{" checked" if key == EVERYONE else ""}>' for key, _, said in picks)
    labels = "".join(f'<label for="shelf-{key}">{label}</label>' for key, label, _ in picks)
    return f'{buttons}\n<p class="shelf-filter">{labels}</p>'


def shelf(pages: list[Page], depth: int) -> str:
    """Every field note of the site, under its reader."""
    found = groups(build.notes_of(pages))
    sections, number = [], 0
    for key, label, theirs in found:
        entries = []
        for note in theirs:
            number += 1
            entries.append(entry(note, number, depth))
        items = "\n".join(entries)
        # A plain block, not a <section>: the reader groups are parts of one section of the page, Writing.
        sections.append(f'<div class="shelf-group" data-for="{key}">\n<h3 class="shelf-for">{esc(label)}</h3>\n'
                        f'<ul class="shelf-list">\n{items}\n</ul>\n</div>')
    body = "\n".join(sections)
    return (f'<div class="shelf">\n{reader_filter([key for key, _, _ in found])}\n'
            f'<div class="shelf-groups">\n{body}\n</div>\n</div>')


# ---------------------------------------------------------------- the covers


def generate_covers(pdf_dir: Path, out_dir: Path | None = None) -> list[Path]:
    """The first page of each note's PDF as a small WebP. A PDF that is missing, or that does not have the pages
    the note states, stops the run before any cover is written: an old copy must not give the page its picture."""
    import fitz
    from PIL import Image

    target = out_dir or (build.FILES_DIR / COVERS_DIR_NAME)
    drawn = []
    for note in build.notes_of(build.load_site()):
        source = pdf_dir / f"{note.slug}.pdf"
        if not source.is_file():
            raise ValueError(f"{note.slug}: no {source.name} in {pdf_dir}")
        with fitz.open(source) as doc:
            if doc.page_count != note.pdf_pages:
                raise ValueError(f"{note.slug}: {source.name} has {doc.page_count} pages and the note states {note.pdf_pages}")
            first = doc[0]
            if abs(first.rect.width / first.rect.height - COVER_SIZE[0] / COVER_SIZE[1]) > COVER_SHAPE_SLACK:
                raise ValueError(f"{note.slug}: the first page of {source.name} is not 4:5 "
                                 f"({first.rect.width:g} by {first.rect.height:g}): its cover would be stretched")
            scale = COVER_SIZE[0] * COVER_OVERSAMPLE / first.rect.width
            pix = first.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            page = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        drawn.append((note.slug, page.resize(COVER_SIZE, Image.LANCZOS)))
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for slug, image in drawn:
        dest = target / f"{slug}.webp"
        image.save(dest, "WEBP", quality=WEBP_QUALITY, method=6)
        written.append(dest)
    return written


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    paths = generate_covers(Path(sys.argv[1]))
    print(f"made {len(paths)} covers in {build.FILES_DIR / COVERS_DIR_NAME}")
