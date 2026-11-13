"""The home page of the site: its sections, from the headline down to the closing call.

build.py owns the pages, the data (the desk's objects, the figures, the steps of the method) and the
helpers; this module only lays the home page out. It imports build, so build imports it late, when it
renders a page. No script anywhere: what opens, opens with <details>; what moves, moves with CSS.
"""
from __future__ import annotations

import re

import build
from build import DeskObject, Page, esc, href

DESK_ALT = ("Illustration: a desk at night by a window over a warehouse yard, with a field kit laid out on it: "
            "a passport and a boarding pass, safety boots, a high-visibility vest and gloves, a steel tape, "
            "a knife, a chest camera, a recorder, a notebook of tally marks and a laptop.")
DESK_CREDIT = "Illustration"  # under the picture: it is not a photograph, and the page says so
FIGURES_TITLE = "What you can check"
METHOD_TITLE = "How the work goes"
KIT_TITLE = "The desk the night before a visit"
KIT_NOTE = "Every object says one thing about how I work: pick one."
KIT_CREDIT = "The desk is an illustration."
ANSWER_LINK = "Full answer"
FIRST_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def headline(page: Page) -> str:
    """The headline as two lines when it has two sentences: what is wrong, then what I do about it."""
    parts = FIRST_SENTENCE.split((page.headline or page.title).strip(), maxsplit=1)
    classes = ("h1-a", "h1-b")
    return " ".join(f'<span class="{css}">{build.render_inline(part)}</span>' for css, part in zip(classes, parts))


def desk_picture(depth: int) -> str:
    """The desk beside the headline. Empty until desk.py has written every file of the desk."""
    if not build.desk_ready():
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
    """The first screen: the headline, one line under it, the contact button and one more link."""
    secondary = ""
    if page.secondary:
        label, slug = page.secondary
        secondary = f'\n<a class="btn btn-ghost" href="{href(slug + "/", depth)}">{esc(label)}</a>'
    return f"""<section id="hero" class="hero">
<div class="wrap hero-in">
<p class="kicker">{esc(page.kicker or build.AUTHOR_ROLE)}</p>
<h1>{headline(page)}</h1>
<div class="hero-body">
<div class="hero-copy">
<p class="lede">{build.render_inline(page.lede or "")}</p>
<p class="actions">{build.contact_button(page)}{secondary}</p>
</div>
{desk_picture(depth)}
</div>
</div>
</section>"""


def door_item(page: Page, depth: int) -> str:
    return (f'<li><a class="door" href="{href(page.path, depth)}">'
            f'<span class="door-t">{esc(page.door or page.title)}</span>'
            f'<span class="door-d">{esc(page.door_text or "")}</span></a></li>')


def door_group(pages: list[Page], depth: int, group: str, question: str) -> str:
    items = "\n".join(door_item(page, depth) for page in build.landings_of(pages, group))
    return f'<h2 class="doors-q">{esc(question)}</h2>\n<ul class="doors">\n{items}\n</ul>'


def situations(page: Page, pages: list[Page], depth: int) -> str:
    """What is going wrong, in the reader's words, and then the three doors: which one is yours?"""
    lines = " ".join(f"<span>{esc(line)}</span>" for line in page.symptoms)
    statement = f'<p class="statement">{lines}</p>\n' if lines else ""
    return f"""<section id="situations" class="situations">
<div class="wrap">
{statement}{door_group(pages, depth, *build.SITUATION_GROUP)}
</div>
</section>"""


def figure_item(figure: build.HomeFigure, pages: list[Page], depth: int, lead: bool) -> str:
    art = ""
    if lead and build.desk_ready():
        width, height = build.DETAIL_SIZES["chart"]
        source = href(f"files/desk/{build.detail_name('chart')}", depth)
        art = (f'\n<img class="fig-art" src="{source}" width="{width}" height="{height}" alt="" '
               f'loading="lazy" decoding="async">')
    return f"""<a class="fig{' fig-lead' if lead else ''}" href="{href(build.find(pages, figure.slug).path, depth)}">
<span class="fig-n">{esc(figure.number)}</span>
<span class="fig-t">{esc(figure.caption)}</span>
<span class="fig-go">{esc(figure.label)}</span>{art}
</a>"""


def figures(pages: list[Page], depth: int) -> str:
    """Three numbers, large, each with what it measures and the page where it can be checked."""
    items = "\n".join(figure_item(figure, pages, depth, lead=index == 0)
                      for index, figure in enumerate(build.HOME_FIGURES))
    return f"""<section id="proof" class="figures">
<div class="wrap">
<h2>{FIGURES_TITLE}</h2>
<div class="fig-grid">
{items}
</div>
</div>
</section>"""


def method() -> str:
    """The three steps of the work, as panels that stack while the page is read."""
    steps = "\n".join(f'<li><div class="wrap step"><div class="step-rule" aria-hidden="true"></div>'
                      f'<div class="step-body"><h3>{esc(title)}</h3>\n<p>{esc(text)}</p></div></div></li>'
                      for title, text in build.METHOD_STEPS)
    return f"""<section id="method" class="method">
<div class="wrap"><h2>{METHOD_TITLE}</h2></div>
<ol class="stack">
{steps}
</ol>
</section>"""


def tile(item: DeskObject, pages: list[Page], depth: int) -> str:
    width, height = build.TILE_SIZE
    picture = href(f"files/desk/{build.tile_name(item.key)}", depth)
    limit = f'\n<p class="tile-limit">{esc(item.rule)}</p>' if item.rule else ""
    return f"""<li><a class="tile" href="{href(build.find(pages, item.slug).path, depth)}">\
<span class="tile-frame"><img src="{picture}" width="{width}" height="{height}" alt="" loading="lazy" decoding="async"></span>
<h3>{esc(item.name)}</h3>
<p>{esc(item.text)}</p>{limit}</a></li>"""


def kit(pages: list[Page], depth: int) -> str:
    """The nine objects on the desk, each with what it says about the work and the page it leads to.
    From the objects, on to the services. Empty until desk.py has written every file of the desk."""
    if not build.desk_ready():
        return ""
    tiles = "\n".join(tile(item, pages, depth) for item in build.DESK)
    return f"""<section id="kit" class="kit">
<div class="wrap">
<h2>{KIT_TITLE}</h2>
<p class="kit-note">{KIT_NOTE}</p>
</div>
<ul class="strip">
{tiles}
</ul>
<div class="wrap kit-foot">
<p class="kit-credit">{KIT_CREDIT}</p>
<a class="text-link" href="{href(build.find(pages, build.SERVICES_SLUG).path, depth)}">{esc(build.NEXT_LINKS[0][0])}</a>
</div>
</section>"""


def doors(pages: list[Page], depth: int) -> str:
    """The doors by floor and by kind of buyer, lower on the page than the three situations."""
    groups = "\n".join(f"<div>\n{door_group(pages, depth, group, question)}\n</div>"
                       for group, question in build.DOOR_GROUPS)
    return f"""<section id="industries" class="index">
<div class="wrap index-grid">
{groups}
</div>
</section>"""


def note_item(note: Page, depth: int) -> str:
    return f"""<article class="note-item">
<h3><a href="{href(note.path, depth)}">{esc(note.title)}</a></h3>
<p>{esc(note.description)}</p>
<p class="meta">{build.pdf_link(note)}</p>
</article>"""


def answer_item(question: Page, depth: int) -> str:
    return (f"<details><summary>{build.render_inline(question.title)}</summary>\n"
            f'<p class="short">{esc(question.description)} '
            f'<a href="{href(question.path, depth)}">{ANSWER_LINK}</a></p></details>')


def library(pages: list[Page], depth: int) -> str:
    """The field notes and the short answers, at the foot of the home page. The answers open in place."""
    notes = "\n".join(note_item(note, depth) for note in build.notes_of(pages))
    questions = build.questions_of(pages)
    half = (len(questions) + 1) // 2
    columns = "\n".join("<div>\n" + "\n".join(answer_item(question, depth) for question in column) + "\n</div>"
                        for column in (questions[:half], questions[half:]) if column)
    return f"""<section id="library">
<div class="wrap">
<h2 id="field-notes">Field notes</h2>
<div class="notes">
{notes}
</div>
<h2 id="questions">Short answers</h2>
<div class="qa">
{columns}
</div>
<p class="next"><a href="{href(build.AUTHOR_SLUG + '/', depth)}">About the author</a> · \
<a href="{href(build.BOOK_SLUG + '/', depth)}"><em>The Deployment Chasm</em></a>, a manuscript</p>
</div>
</section>"""


def closing(page: Page) -> str:
    """The page ends on the call it opened with: the same words, the same address, and where I work."""
    base = f"\n<p>{build.render_inline(page.base_line)}</p>" if page.base_line else ""
    label = esc(page.cta or build.DEFAULT_CTA)
    return f"""<section id="contact" class="close">
<div class="wrap">
<a class="close-link" href="{build.contact_href(page)}">{label} <span aria-hidden="true">→</span></a>{base}
</div>
</section>"""


def main(page: Page, pages: list[Page], depth: int) -> str:
    parts = (
        hero(page, depth),
        situations(page, pages, depth),
        figures(pages, depth),
        method(),
        kit(pages, depth),
        page.body_html,
        doors(pages, depth),
        library(pages, depth),
        closing(page),
    )
    return "\n".join(part for part in parts if part)
