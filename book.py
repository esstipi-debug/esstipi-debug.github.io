#!/usr/bin/env python3
"""Render the interactive, zero-JS leafable book viewer for The Deployment Chasm sample.

Usage (regenerate page images from src/files/the-deployment-chasm-sample.pdf):
    python book.py

build.py imports this module lazily inside book_main() and embeds the viewer when all sample
page images exist in src/files/book/. On wide screens the viewer displays a physical two-page
book (cover, then spreads 2-3, 4-5, 6-7) with spine shadow, click-to-turn leaves and a full-screen
reading toggle. On narrow screens it steps page by page (1 to 7). Zero JavaScript.
"""
from __future__ import annotations

from pathlib import Path

import build
from build import esc, href

PDF_NAME = "the-deployment-chasm-sample.pdf"
BOOK_DIR_NAME = "book"
PAGE_SIZE = (1200, 1800)
DPI = 200
WEBP_QUALITY = 88

# Exact descriptions of the 7 sample pages, kept clean of dashes, arrows and product names.
SAMPLE_PAGES: tuple[tuple[int, str], ...] = (
    (1, "Cover of The Deployment Chasm by Marcos Stipicich"),
    (2, "Table of contents, frontmatter and chapters 1 to 11"),
    (3, "Table of contents continued, chapter 12 to appendices and bibliography"),
    (4, "Chapter 1 opening: The Forty-Year Arc, art curation record"),
    (5, "Chapter 1 excerpt: framing of enterprise deployment failure"),
    (6, "Chapter 1 excerpt: the three seams between system and floor"),
    (7, "Chapter 1 excerpt: operationalization and one-week intake measurement"),
)

# Desktop book spreads: (spread_index, label, (page_numbers...))
SPREADS: tuple[tuple[int, str, tuple[int, ...]], ...] = (
    (0, "Cover", (1,)),
    (1, "2-3", (2, 3)),
    (2, "4-5", (4, 5)),
    (3, "6-7", (6, 7)),
)


def book_dir() -> Path:
    return build.FILES_DIR / BOOK_DIR_NAME


def page_name(number: int) -> str:
    return f"page-{number:02d}.webp"


def ready() -> bool:
    """True once every sample page image exists in src/files/book/."""
    folder = book_dir()
    return all((folder / page_name(number)).is_file() for number, _ in SAMPLE_PAGES)


def _leaf_html(
    number: int,
    alt: str,
    depth: int,
    side: str,
    target: int | None,
    hit_label: str,
) -> str:
    src = href(f"files/{BOOK_DIR_NAME}/{page_name(number)}", depth)
    width, height = PAGE_SIZE
    loading = ' fetchpriority="high"' if number == 1 else ' loading="lazy"'
    hit = ""
    if target is not None:
        hit_cls = "book-hit-prev" if side == "left" else "book-hit-next"
        hit = (f'<label class="book-leaf-hit {hit_cls}" for="book-p{target}">'
               f'<span class="book-sr">{esc(hit_label)}</span></label>')
    gutter = f'<span class="book-gutter book-gutter-{side}" aria-hidden="true"></span>' if side in ("left", "right") else ""
    return (f'<div class="book-leaf book-leaf-{side}" data-page="{number}">'
            f'<img src="{src}" width="{width}" height="{height}" alt="{esc(alt)}"{loading}>'
            f'{gutter}{hit}</div>')


def _spreads_html(depth: int) -> str:
    alts = dict(SAMPLE_PAGES)
    blocks = []
    # Spread 0: Front cover centered; clicking opens spread 1 (pages 2-3).
    cover = _leaf_html(1, alts[1], depth, "cover", 2, "Open book to pages 2-3")
    blocks.append(f'<div class="book-spread book-spread-cover" data-spread="0">{cover}</div>')

    # Spreads 1..3: open two-page book spreads.
    nav_targets = {
        1: (1, 4, "Back to cover", "Turn to pages 4-5"),
        2: (2, 6, "Turn back to pages 2-3", "Turn to pages 6-7"),
        3: (4, None, "Turn back to pages 4-5", ""),
    }
    for index, _, pair in SPREADS[1:]:
        left_n, right_n = pair
        prev_target, next_target, prev_text, next_text = nav_targets[index]
        left = _leaf_html(left_n, alts[left_n], depth, "left", prev_target, prev_text)
        right = _leaf_html(right_n, alts[right_n], depth, "right", next_target, next_text)
        blocks.append(f'<div class="book-spread book-spread-open" data-spread="{index}">{left}{right}</div>')
    return "\n".join(blocks)


def _status_html() -> str:
    total = len(SAMPLE_PAGES)
    desk_items = [
        f'<span class="book-stat" data-s="0">Cover (1 of {total})</span>',
        f'<span class="book-stat" data-s="1">Pages 2-3 of {total}</span>',
        f'<span class="book-stat" data-s="2">Pages 4-5 of {total}</span>',
        f'<span class="book-stat" data-s="3">Pages 6-7 of {total}</span>',
    ]
    mob_items = [
        f'<span class="book-stat-m" data-p="{n}">Page {n} of {total}</span>'
        for n, _ in SAMPLE_PAGES
    ]
    return (f'<span class="book-status-desk">{"".join(desk_items)}</span>'
            f'<span class="book-status-mob">{"".join(mob_items)}</span>')


def _desk_nav_html() -> str:
    prev_map = {0: None, 1: 1, 2: 2, 3: 4}
    next_map = {0: 2, 1: 4, 2: 6, 3: None}
    prev_controls = []
    next_controls = []
    for index, _, _ in SPREADS:
        p_target = prev_map[index]
        n_target = next_map[index]
        if p_target is None:
            prev_controls.append(f'<span class="book-step book-step-off" data-s="{index}" aria-disabled="true">Previous</span>')
        else:
            prev_controls.append(f'<label class="book-step" data-s="{index}" for="book-p{p_target}">Previous</label>')
        if n_target is None:
            next_controls.append(f'<span class="book-step book-step-off" data-s="{index}" aria-disabled="true">Next</span>')
        else:
            next_controls.append(f'<label class="book-step" data-s="{index}" for="book-p{n_target}">Next</label>')
    pills = "".join(
        f'<label class="book-pill" data-s="{index}" for="book-p{pair[0]}">{esc(label)}</label>'
        for index, label, pair in SPREADS
    )
    return (f'<div class="book-nav-desk">'
            f'<span class="book-steps">{"".join(prev_controls)}</span>'
            f'<span class="book-pills">{pills}</span>'
            f'<span class="book-steps">{"".join(next_controls)}</span>'
            f'</div>')


def _mob_nav_html() -> str:
    total = len(SAMPLE_PAGES)
    prev_controls = []
    next_controls = []
    pills = []
    for n, _ in SAMPLE_PAGES:
        if n == 1:
            prev_controls.append(f'<span class="book-step-m book-step-off" data-p="{n}" aria-disabled="true">Previous</span>')
        else:
            prev_controls.append(f'<label class="book-step-m" data-p="{n}" for="book-p{n - 1}">Previous</label>')
        if n == total:
            next_controls.append(f'<span class="book-step-m book-step-off" data-p="{n}" aria-disabled="true">Next</span>')
        else:
            next_controls.append(f'<label class="book-step-m" data-p="{n}" for="book-p{n + 1}">Next</label>')
        pills.append(f'<label class="book-pill-m" data-p="{n}" for="book-p{n}">{n}</label>')
    return (f'<div class="book-nav-mob">'
            f'<span class="book-steps">{"".join(prev_controls)}</span>'
            f'<span class="book-pills">{"".join(pills)}</span>'
            f'<span class="book-steps">{"".join(next_controls)}</span>'
            f'</div>')


def reader_html(depth: int) -> str:
    """The complete zero-JS leafable book widget, or empty string if sample page images are absent."""
    if not ready():
        return ""
    radios = "\n".join(
        f'<input class="book-pick" type="radio" name="book-page" id="book-p{n}"{" checked" if n == 1 else ""}>'
        for n, _ in SAMPLE_PAGES
    )
    pdf_url = href(f"files/{PDF_NAME}", depth)
    return f"""<section class="book-reader" id="sample-reader" aria-label="Sample pages of The Deployment Chasm">
{radios}
<input class="book-pick" type="checkbox" id="book-fs">
<div class="book-stage">
<div class="book-bar">
<div class="book-bar-meta">
<span class="book-bar-title">Sample reader</span>
{_status_html()}
</div>
<div class="book-bar-actions">
<a class="book-pdf" href="{pdf_url}" target="_blank" rel="noopener">Open PDF</a>
<label class="book-fs-btn" for="book-fs"><span class="book-fs-enter">Full screen</span><span class="book-fs-exit">Exit full screen</span></label>
</div>
</div>
<div class="book-viewport">
{_spreads_html(depth)}
</div>
<div class="book-nav">
{_desk_nav_html()}
{_mob_nav_html()}
<p class="book-hint">Click the right or left page to turn, or use full screen for close reading.</p>
</div>
</div>
</section>"""


def generate_images(pdf_path: Path | None = None, out_dir: Path | None = None) -> list[Path]:
    """Render each page of the PDF sample to crisp 1200x1800 WebP images."""
    import fitz
    from PIL import Image

    source = pdf_path or (build.FILES_DIR / PDF_NAME)
    target = out_dir or book_dir()
    target.mkdir(parents=True, exist_ok=True)
    written = []
    with fitz.open(source) as doc:
        for index, page in enumerate(doc, 1):
            pix = page.get_pixmap(dpi=DPI, alpha=False)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            dest = target / page_name(index)
            image.save(dest, "WEBP", quality=WEBP_QUALITY, method=6)
            written.append(dest)
    return written


if __name__ == "__main__":
    paths = generate_images()
    print(f"rendered {len(paths)} pages into {book_dir()}")
