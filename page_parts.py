"""The pieces an inner page asks for in its own text.

A page is written in Markdown, and three things it cannot write by itself are asked for with a mark that this
module answers when the page is rendered:

- <!-- contact --> on a line of its own puts the page's one contact button there, under the headline; the page
  then closes with the same call as a link (build.py does both);
- <!-- drawing: claims --> puts the drawing of the audit's claims, the same one the home page shows;
- a list inside <div class="rows"> becomes rows that fold on a phone and stand open on a wide screen: each item
  starts with its title in bold, and the first row opens the list.

No script: a row is a <details>, and the style sheet does the rest. It imports build, so build imports it late,
when it renders a page.
"""
from __future__ import annotations

import re
from collections.abc import Callable

import build
from build import Page, esc

CONTACT = "<!-- contact -->"
DRAWING = re.compile(r"<!-- drawing: ([a-z]+) -->")
ROWS = re.compile(r'<div class="rows">\s*<ul>(.*?)</ul>\s*</div>', re.S)
ITEM = re.compile(r"<li>(.*?)</li>", re.S)
TITLED = re.compile(r"\A<strong>(.*?)</strong>(.*)\Z", re.S)
AUDIT_SLUG = "not-received-but-delivered"
AUDIT_BASE = re.compile(r"Of [\d,]+ delivered orders with a review, [\d,]+ had a review saying the order had "
                        r"not arrived\.")
LATE_WORDS = "written on or before the delivery day"
AFTER_WORDS = "written after it"


# ---------------------------------------------------------------- the claims of the audit, drawn

def audit_base(pages: list[Page]) -> str:
    """How many orders the claims were found in, in the audit's own sentence."""
    found = AUDIT_BASE.search(build.find(pages, AUDIT_SLUG).body_html)
    if not found:
        raise ValueError(f"{AUDIT_SLUG}: the sentence with the base of the claims is missing")
    return found.group(0)


def claims_drawing(pages: list[Page]) -> str:
    """The audit's claims on both sides of the delivery day, one unit of width for each claim: those written
    on or before it, and those written after it, split in two. Drawn from the published counts."""
    (_, _, late), (_, flag_words, flag), (_, rest_words, rest) = build.CLAIMS_TRIAGE
    total, after = late + flag + rest, flag + rest
    x, rects = 0, []
    for key, _, count in build.CLAIMS_TRIAGE:
        rects.append(f'<rect class="seg-{key}" x="{x}" y="0" width="{count}" height="10"/>')
        x += count
    summary = "; ".join(f"{count:,} {words}" for _, words, count in build.CLAIMS_TRIAGE)
    columns = f"{late}fr {flag}fr {rest}fr"
    return f"""<span class="claims" role="img" aria-label="{total:,} claims: {esc(summary)}" style="grid-template-columns: {columns}">
<span class="cota cota-late"><span><b>{late:,}</b> {LATE_WORDS}</span></span>
<span class="cota cota-after"><span><b>{after:,}</b> {AFTER_WORDS}</span></span>
<svg class="claims-bar" viewBox="0 0 {total} 10" preserveAspectRatio="none" aria-hidden="true">{"".join(rects)}</svg>
<span class="datum"><span>delivery day</span></span>
<span class="sub sub-flag" style="--half: {50 * flag / (late + flag):.2f}%"><span><b>{flag:,}</b> {esc(flag_words)}</span></span>
<span class="cota cota-rest"><span><b>{rest:,}</b> {esc(rest_words)}</span></span>
</span>
<span class="claims-base">{audit_base(pages)} <span class="note">Lengths to scale.</span></span>"""


DRAWINGS: dict[str, Callable[[list[Page]], str]] = {"claims": claims_drawing}


def with_drawings(body_html: str, pages: list[Page]) -> str:
    """The page body with each drawing mark replaced by its drawing. An unknown mark stops the build."""
    unknown = [name for name in DRAWING.findall(body_html) if name not in DRAWINGS]
    if unknown:
        raise ValueError(f"unknown drawing '{unknown[0]}'")
    return DRAWING.sub(lambda found: f'<div class="drawing">{DRAWINGS[found.group(1)](pages)}</div>', body_html)


# ---------------------------------------------------------------- lists that fold into rows

def row(number: int, item: str) -> str:
    titled = TITLED.match(item.strip())
    if not titled:
        raise ValueError(f"a row needs a title in bold: {item.strip()[:60]!r}")
    title, text = titled.groups()
    return (f'<li><details class="row"{" open" if number == 0 else ""}><summary><strong>{title}</strong></summary>'
            f"<p>{text.strip()}</p></details></li>")


def fold_rows(body_html: str) -> str:
    """Each list marked as rows, turned into rows: the bold title is what shows when a row is shut."""
    def rows(found: re.Match) -> str:
        made = "\n".join(row(number, item) for number, item in enumerate(ITEM.findall(found.group(1))))
        return f'<ul class="rows">\n{made}\n</ul>'
    return ROWS.sub(rows, body_html)
