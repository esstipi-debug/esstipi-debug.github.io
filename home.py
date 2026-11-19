"""The home page of the site, laid out as a working drawing: the record is a white line, the floor a red one.

build.py owns the pages, the data (the figures, the steps of the method) and the helpers; drawings.py owns
the line drawings; this module only lays the home page out. It imports build, so build imports it late,
when it renders a page. No script anywhere: the situation is picked with radio buttons, what folds, folds
with <details>, and what moves, moves with CSS.

From top to bottom: the headline beside the sheet where the reader picks a situation (each one shows its
drawing, its figure and its door); who the reader is and where the work is; the four figures; the method;
the argument and the pillars, written in src/pages/index.md; the field notes and the short answers; and
the closing call. Three sentences come from other pages and are read from them, never retyped: who the
work fits best (engagements), the door for whoever is hiring (the author page) and the base of the claims
(the audit).
"""
from __future__ import annotations

import re

import build
import drawings
from build import Page, esc, href

DESK_ALT = ("Illustration: a desk at night by a window over a warehouse yard, with a field kit laid out on it: "
            "a passport and a boarding pass, a high-visibility vest and gloves, a steel tape, "
            "a knife, a chest camera and a two-piece recorder.")
DESK_CREDIT = "Illustration"  # under the picture: it is not a photograph, and the page says so
FIGURES_TITLE = "What you can check"
FIGURES_NOTE = ("Each number says where it comes from: a study, a company filing, my own analysis, "
                "or my own field work.")
DEPLOYMENT_LINE = "For technology teams, the same work runs in five steps, from the first audit to the handback."
DEPLOYMENT_LINK = "How a deployment runs"
METHOD_TITLE = "How the work goes"
ANSWER_LINK = "Full answer"
FIRST_SENTENCE = re.compile(r"(?<=[.!?])\s+")

# Each situation is shown with the figure that measures it and the drawing cut from that figure.
SITUATION_FIGURE = {
    "a-new-system-goes-live": "a-new-system-goes-live",
    "the-inventory-number-is-wrong": "why-inventory-records-do-not-match-the-shelf",
    "the-floor-works-around-the-system": "proof",
}
BEST_FIT = ("engagements", "Best fit")              # the page and the heading the sentence stands under
HIRING = (build.AUTHOR_SLUG, "If you are hiring")   # the same, for the door of whoever is hiring
AUDIT_SLUG = "not-received-but-delivered"
AUDIT_BASE = re.compile(r"Of [\d,]+ delivered orders with a review, [\d,]+ had a review saying the order had "
                        r"not arrived\.")
READER = re.compile(r"for the (CEO|COO|CFO)\b")     # a field note says who it is written for
COUNT_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
LATE_WORDS = "written on or before the delivery day"
AFTER_WORDS = "written after it"
INDEX_HEADS = ("Note", "For", "What it covers", "File")


# ---------------------------------------------------------------- what other pages already say

def paragraph_under(pages: list[Page], slug: str, heading: str) -> str:
    """The first paragraph under a heading of another page, as that page prints it."""
    page = build.find(pages, slug)
    found = re.search(rf"<h2[^>]*>{re.escape(heading)}</h2>\s*<p>(.*?)</p>", page.body_html, re.S)
    if not found:
        raise ValueError(f"{slug}: no paragraph under the heading {heading!r}, and the home page prints it")
    return found.group(1)


def audit_base(pages: list[Page]) -> str:
    """How many orders the claims were found in, in the audit's own sentence."""
    found = AUDIT_BASE.search(build.find(pages, AUDIT_SLUG).body_html)
    if not found:
        raise ValueError(f"{AUDIT_SLUG}: the sentence with the base of the claims is missing")
    return found.group(0)


def figure_of(slug: str) -> build.HomeFigure:
    for figure in build.HOME_FIGURES:
        if figure.slug == slug:
            return figure
    raise ValueError(f"no home figure points to the page {slug!r}")


def said_in(figure: build.HomeFigure, pattern: str) -> str:
    """A phrase of a figure's caption, for a drawing to print in the caption's own words."""
    found = re.search(pattern, figure.caption)
    if not found:
        raise ValueError(f"the caption of {figure.number} no longer says what its drawing prints ({pattern})")
    return found.group(0)


# ---------------------------------------------------------------- the headline and the sheet of situations

def headline(page: Page) -> str:
    """The headline as two lines when it has two sentences: what is wrong, then what I do about it."""
    parts = FIRST_SENTENCE.split((page.headline or page.title).strip(), maxsplit=1)
    classes = ("h1-a", "h1-b")
    return " ".join(f'<span class="{css}">{build.render_inline(part)}</span>' for css, part in zip(classes, parts))


def desk_picture(depth: int) -> str:
    """The desk beside the headline. Empty until hero_desk_ready() is True."""
    if not build.hero_desk_ready():
        return ""
    large = href(f"files/desk/{build.desk_name()}", depth)
    small = href(f"files/desk/{build.desk_name(small=True)}", depth)
    width, height = build.DESK_SIZE
    return f"""<figure class="hero-figure">
<img src="{large}" srcset="{small} {build.DESK_SMALL}w, {large} {width}w" sizes="{build.HERO_SIZES}"
 width="{width}" height="{height}" alt="{esc(DESK_ALT)}" fetchpriority="high">
<figcaption>{DESK_CREDIT}</figcaption>
</figure>"""


def hero(page: Page, depth: int) -> str:
    """The first screen: the headline, one line under it, the contact button and one more link. Nothing
    small stands above the headline to announce it: the role signs the block, under the two actions."""
    secondary = ""
    if page.secondary:
        label, slug = page.secondary
        secondary = f'\n<a class="btn btn-ghost" href="{href(slug + "/", depth)}">{esc(label)}</a>'
    picture = desk_picture(depth)
    body_class = "hero-body hero-with-figure" if picture else "hero-body"
    figure_html = f"\n{picture}" if picture else ""
    return f"""<section id="hero" class="hero">
<h1>{headline(page)}</h1>
<div class="{body_class}">
<div class="hero-copy">
<p class="lede">{build.render_inline(page.lede or "")}</p>
<p class="actions">{build.contact_button(page)}{secondary}</p>
<p class="hero-role">{esc(page.kicker or build.AUTHOR_ROLE)}</p>
</div>{figure_html}
</div>
</section>"""


def door_item(page: Page, depth: int) -> str:
    return (f'<li><a class="door" href="{href(page.path, depth)}">'
            f'<span class="door-t">{esc(page.door or page.title)}</span>'
            f'<span class="door-d">{esc(page.door_text or "")}</span></a></li>')


def situation_drawing(slug: str, figure: build.HomeFigure) -> str:
    """The drawing of a situation, with the words and the cut taken from the figure that measures it."""
    if slug == "a-new-system-goes-live":
        return drawings.go_live(figure.number)
    if slug == "the-inventory-number-is-wrong":
        whole = said_in(figure, r"about [\d,]+") + " records"
        return drawings.inventory(float(figure.number.rstrip("%")) / 100, whole, figure.number)
    if slug == "the-floor-works-around-the-system":
        return drawings.workaround(said_in(figure, r"about \d+%"))
    raise ValueError(f"the situation {slug!r} has no drawing yet (drawings.py)")


def state(number: int, door: Page, pages: list[Page], depth: int) -> str:
    """What a picked situation shows: its drawing, the figure that measures it and its door."""
    if door.slug not in SITUATION_FIGURE:
        raise ValueError(f"the situation {door.slug!r} has no figure yet (home.SITUATION_FIGURE)")
    figure = figure_of(SITUATION_FIGURE[door.slug])
    link = href(build.find(pages, figure.slug).path, depth)
    return f"""<div class="state state-{number}">
<div class="dwg-box">{situation_drawing(door.slug, figure)}</div>
<p class="state-fig"><span class="tag">{esc(figure.grade)}</span> <b class="state-n">{esc(figure.number)}</b> \
{esc(figure.caption)} <a href="{link}">{esc(figure.label)}</a></p>
<ul class="doors">
{door_item(door, depth)}
</ul>
</div>"""


def situations(page: Page, pages: list[Page], depth: int) -> str:
    """What is going wrong, in the reader's words, and then: which one is yours? Three radio buttons pick
    it. Until one is picked the sheet shows the drawing of the gap; then it shows that situation's own."""
    doors = build.landings_of(pages, build.SITUATION_GROUP[0])
    numbered = list(enumerate(doors, 1))
    lines = " ".join(f"<span>{esc(line)}</span>" for line in page.symptoms)
    statement = f'<p class="statement">{lines}</p>\n' if lines else ""
    picks = "\n".join(f'<input class="pick" type="radio" name="situation" id="pick-{n}" aria-labelledby="pick-l{n}">'
                      for n, _ in numbered)
    labels = "\n".join(f'<label id="pick-l{n}" for="pick-{n}">{esc(door.door or door.title)}</label>'
                       for n, door in numbered)
    states = "\n".join(state(n, door, pages, depth) for n, door in numbered)
    return f"""<section id="situations" class="situations">
{statement}{picks}
<div class="picks" role="group" aria-labelledby="pick-q">
<h2 class="doors-q" id="pick-q">{esc(build.SITUATION_GROUP[1])}</h2>
{labels}
</div>
<div class="states">
<div class="state state-0"><div class="dwg-box">{drawings.gap()}</div></div>
{states}
</div>
</section>"""


def top(page: Page, pages: list[Page], depth: int) -> str:
    """The headline and, beside it on a wide screen, the sheet of situations."""
    return f"""<div class="wrap top">
{hero(page, depth)}
{situations(page, pages, depth)}
</div>"""


# ---------------------------------------------------------------- who the reader is

def hiring_door(pages: list[Page], depth: int) -> str:
    """The door for whoever is hiring, in the author page's own heading and sentence."""
    slug, heading = HIRING
    line = paragraph_under(pages, slug, heading).rstrip(":") + "."
    return (f'<li><a class="door" href="{href(slug + "/", depth)}#if-you-are-hiring">'
            f'<span class="door-t">{esc(heading)}</span><span class="door-d">{line}</span></a></li>')


def readers(pages: list[Page], depth: int) -> str:
    """Who the reader is and where the work is, right under the situations, and who the work fits best."""
    groups = []
    for group, question in build.DOOR_GROUPS:
        items = [door_item(page, depth) for page in build.landings_of(pages, group)]
        if group == "buyer":
            items.append(hiring_door(pages, depth))
        body = "\n".join(items)
        groups.append(f'<div class="readers-{group}">\n<h2 class="doors-q">{esc(question)}</h2>\n'
                      f'<ul class="doors">\n{body}\n</ul>\n</div>')
    slug, heading = BEST_FIT
    return f"""<section id="industries" class="readers">
<div class="wrap readers-in">
{chr(10).join(groups)}
<p class="fit"><span class="tag">{esc(heading)}</span> {paragraph_under(pages, slug, heading)}</p>
</div>
</section>"""


# ---------------------------------------------------------------- the four figures

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


def figure_item(figure: build.HomeFigure, pages: list[Page], depth: int) -> str:
    drawn = figure.slug == AUDIT_SLUG
    chart = f"\n{claims_drawing(pages)}" if drawn else ""
    return f"""<a class="fig{' fig-drawn' if drawn else ''}" href="{href(build.find(pages, figure.slug).path, depth)}">
<span class="fig-g">{esc(figure.grade)}</span>
<span class="fig-n">{esc(figure.number)}</span>
<span class="fig-t">{esc(figure.caption)}</span>{chart}
<span class="fig-go">{esc(figure.label)}</span>
</a>"""


def figures(pages: list[Page], depth: int) -> str:
    """Four numbers in a chain, each with what it measures, where it comes from and the page where it can be
    checked. The third carries its drawing."""
    items = "\n".join(figure_item(figure, pages, depth) for figure in build.HOME_FIGURES)
    return f"""<section id="proof" class="figures">
<div class="wrap">
<h2>{FIGURES_TITLE}</h2>
<p class="fig-note">{esc(FIGURES_NOTE)}</p>
<div class="fig-list">
{items}
</div>
</div>
</section>"""


# ---------------------------------------------------------------- the method, the library and the closing call

def method(pages: list[Page], depth: int) -> str:
    """The three steps of the work, each over the same line in a new state, and where the five steps of a
    deployment are written out."""
    steps = "\n".join(f"<li>{drawings.method_step(index)}\n<h3>{esc(title)}</h3>\n<p>{esc(text)}</p></li>"
                      for index, (title, text) in enumerate(build.METHOD_STEPS))
    deployment = href(build.find(pages, "for-technology-vendors").path, depth) + "#how-we-would-start"
    return f"""<section id="method" class="method">
<div class="wrap">
<h2>{METHOD_TITLE}</h2>
<ol class="stages">
{steps}
</ol>
<p class="method-more">{esc(DEPLOYMENT_LINE)} <a href="{deployment}">{esc(DEPLOYMENT_LINK)}</a></p>
</div>
</section>"""


def note_row(note: Page, depth: int) -> str:
    """One field note in the index: its title, who it is written for, what it covers and its file."""
    reader = READER.search(note.description)
    return f"""<tr><th scope="row"><a href="{href(note.path, depth)}">{esc(note.title)}</a></th>
<td class="ix-for">{reader.group(1) if reader else ""}</td>
<td class="ix-what">{esc(note.description)}</td>
<td class="ix-file">{build.pdf_link(note)}</td></tr>"""


def answer_item(question: Page, depth: int) -> str:
    return (f"<details><summary>{build.render_inline(question.title)}</summary>\n"
            f'<p class="short">{esc(question.description)} '
            f'<a href="{href(question.path, depth)}">{ANSWER_LINK}</a></p></details>')


def library(pages: list[Page], depth: int) -> str:
    """The field notes as an index and the short answers, at the foot of the home page. The answers open in
    place; on a phone the second half of them waits behind one line."""
    rows = "\n".join(note_row(note, depth) for note in build.notes_of(pages))
    heads = "".join(f'<th scope="col">{head}</th>' for head in INDEX_HEADS)
    questions = build.questions_of(pages)
    half = (len(questions) + 1) // 2
    first = "\n".join(answer_item(question, depth) for question in questions[:half])
    rest = "\n".join(answer_item(question, depth) for question in questions[half:])
    folded = (f'\n<details class="fold fold-quiet">\n<summary>{COUNT_WORDS[len(questions) - half].capitalize()} '
              f"more short answers</summary>\n{rest}\n</details>") if rest else ""
    return f"""<section id="library">
<div class="wrap">
<h2 id="field-notes">Field notes</h2>
<table class="index">
<thead><tr>{heads}</tr></thead>
<tbody>
{rows}
</tbody>
</table>
<h2 id="questions">Short answers</h2>
<div class="qa">
<div>
{first}
</div>{folded}
</div>
<p class="next"><a href="{href(build.AUTHOR_SLUG + '/', depth)}">About the author</a> · \
<a href="{href(build.BOOK_SLUG + '/', depth)}"><em>The Deployment Chasm</em></a>, a manuscript</p>
</div>
</section>"""


def closing(page: Page) -> str:
    """The page ends on the call it opened with: the same words, the same address, and where I work.
    The words are the link: no arrow follows them."""
    base = f"\n<p>{build.render_inline(page.base_line)}</p>" if page.base_line else ""
    label = esc(page.cta or build.DEFAULT_CTA)
    return f"""<section id="contact" class="close">
<div class="wrap">
<a class="close-link" href="{build.contact_href(page)}">{label}</a>{base}
</div>
</section>"""


def main(page: Page, pages: list[Page], depth: int) -> str:
    parts = (
        top(page, pages, depth),
        readers(pages, depth),
        figures(pages, depth),
        method(pages, depth),
        page.body_html,
        library(pages, depth),
        closing(page),
    )
    return "\n".join(part for part in parts if part)
