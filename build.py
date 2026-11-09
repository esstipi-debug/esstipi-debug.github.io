#!/usr/bin/env python3
"""Build the static site at the repository root from src/pages/*.md.

Usage:
    python build.py

Each page is a Markdown file that starts with a front matter block: "key: value"
lines between two "---" lines, where a repeated key ("cite", "offer") makes a
list. The build writes index.html, one folder per page, style.css, favicon.svg,
the files in src/files/, robots.txt, sitemap.xml, 404.html and .nojekyll.
Folders of pages that no longer exist are removed, using src/generated.json as
the record of what it wrote.

Page types: "question" and "note" are the field notes, "author" and "book" the
author page and the manuscript. "home" is the home page; "landing" the five
entry pages (three floors and two kinds of buyer, shown as doors on the home
page); "page" the other commercial pages (engagements, proof, working terms).
"""
from __future__ import annotations

import html
import json
import logging
import re
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import quote

import markdown

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PAGES_DIR = SRC / "pages"
FILES_DIR = SRC / "files"
MANIFEST = SRC / "generated.json"
ASSETS = ("style.css", "favicon.svg")

SITE_URL = "https://esstipi-debug.github.io"
AUTHOR = "Marcos Stipicich"
AUTHOR_ROLE = "Deployment Strategist · Supply Chain & Operations"
AUTHOR_SLUG = "marcos-stipicich"
BOOK_SLUG = "the-deployment-chasm"
LINKEDIN = "https://www.linkedin.com/in/marcos-stipicich"
GITHUB = "https://github.com/esstipi-debug"
EMAIL = "marcos.stipicic@gmail.com"
LOCATION = "Santiago, Chile"
KNOWS_ABOUT = (
    "Supply chain management",
    "Warehouse operations",
    "Warehouse management system cutovers",
    "Inventory record accuracy",
    "Retail planning",
    "Deployment strategy",
)
# Tokens from Google Search Console and Bing Webmaster Tools, printed on the home page once set.
GOOGLE_SITE_VERIFICATION = "yWgq7sziMlBmLplKNEser905TPbsTWBzZ840z-s1YfE"
BING_SITE_VERIFICATION = ""

SEARCH_BOTS = ("Googlebot", "Bingbot", "OAI-SearchBot", "Claude-SearchBot", "PerplexityBot")
TRAINING_BOTS = ("GPTBot", "ClaudeBot", "CCBot", "Google-Extended")
DISALLOWED_PATHS = ("/src/", "/tests/")

PAGE_TYPES = ("home", "question", "note", "author", "book", "landing", "page")
REQUIRED_KEYS = ("type", "order", "slug", "title", "description", "published", "updated")
KIND_KEYS = {"home": ("headline", "lede"), "landing": ("group", "door", "door_text")}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESERVED_SLUGS = frozenset({"files", "src", "tests"})  # folders the build or the repository already use
FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.S)
MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")

# Commercial pages. A target that starts with "#" is an anchor on the home page.
NAV = (
    ("Industries", "#industries"),
    ("Engagements", "engagements/"),
    ("Proof", "proof/"),
    ("Field notes", "#field-notes"),
    ("About", f"{AUTHOR_SLUG}/"),
    ("Contact", "contact/"),
)
DOOR_GROUPS = (("floor", "Where is the work?"), ("buyer", "Or what are you?"))
NEXT_LINKS = (("Engagements and fees", "engagements"), ("Proof", "proof"), ("Working terms", "working-terms"))
DEFAULT_CTA = "Tell me what's breaking"
OFFER_UNITS = ("project", "month", "hour", "day")
FROM_PRICE_UNITS = ("project", "month")  # quoted as "from"; hours and days are flat rates
AREA_SERVED = ("United States", "Australia", "Canada", "United Kingdom", "Europe")

log = logging.getLogger("build")


@dataclass(frozen=True)
class Citation:
    text: str
    url: str | None


@dataclass(frozen=True)
class Offer:
    """A priced service on the engagements page, for its structured data. The amount is in USD."""
    name: str
    amount: int
    unit: str

    @property
    def is_from_price(self) -> bool:
        return self.unit in FROM_PRICE_UNITS


@dataclass(frozen=True)
class Page:
    kind: str
    order: int
    slug: str
    title: str
    description: str
    published: date
    updated: date
    body_html: str
    kicker: str | None = None
    origin: str | None = None
    origin_label: str | None = None
    origin_url: str | None = None
    pdf: str | None = None
    pdf_pages: int | None = None
    cites: tuple[Citation, ...] = ()
    headline: str | None = None
    lede: str | None = None
    base_line: str | None = None
    secondary: tuple[str, str] | None = None
    subject: str | None = None
    cta: str | None = None
    group: str | None = None
    door: str | None = None
    door_text: str | None = None
    offers: tuple[Offer, ...] = ()

    @property
    def is_home(self) -> bool:
        return self.kind == "home"

    @property
    def path(self) -> str:
        """URL path from the site root: '' for the home page, 'slug/' otherwise."""
        return "" if self.is_home else f"{self.slug}/"

    @property
    def url(self) -> str:
        return f"{SITE_URL}/{self.path}"


# ---------------------------------------------------------------- loading


def parse_front_matter(text: str, name: str) -> tuple[dict[str, list[str]], str]:
    match = FRONT_MATTER_RE.match(text.replace("\r\n", "\n"))
    if not match:
        raise ValueError(f"{name}: missing front matter")
    meta: dict[str, list[str]] = {}
    for line in match.group(1).splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"{name}: bad front matter line {line!r}")
        meta.setdefault(key.strip(), []).append(value.strip())
    return meta, match.group(2)


def render_markdown(text: str) -> str:
    return markdown.markdown(text, extensions=["extra", "smarty"], output_format="html")


def render_inline(text: str) -> str:
    """Markdown for one line (a title or a citation), without the wrapping <p>."""
    return re.sub(r"\A<p>(.*)</p>\Z", r"\1", render_markdown(text).strip(), flags=re.S)


def parse_citation(value: str) -> Citation:
    text, sep, url = value.partition(" | ")
    return Citation(text=text.strip(), url=url.strip() if sep and url.strip() else None)


def parse_offer(value: str) -> Offer:
    """'name | amount | unit', with the amount in USD and the unit one of OFFER_UNITS."""
    parts = [part.strip() for part in value.split("|")]
    if len(parts) != 3:
        raise ValueError(f"offer must be 'name | amount | unit': {value!r}")
    name, amount, unit = parts
    if unit not in OFFER_UNITS:
        raise ValueError(f"offer {name!r}: unknown unit {unit!r}, expected one of {OFFER_UNITS}")
    if not amount.isdigit():
        raise ValueError(f"offer {name!r}: the amount must be a whole number of USD, got {amount!r}")
    return Offer(name=name, amount=int(amount), unit=unit)


def parse_link(value: str) -> tuple[str, str]:
    """'label | slug': a link to another page of the site."""
    label, sep, slug = value.partition("|")
    label, slug = label.strip(), slug.strip()
    if not sep or not label or not SLUG_RE.match(slug):
        raise ValueError(f"link must be 'label | slug': {value!r}")
    return label, slug


def check_kind_keys(one: dict[str, str], name: str) -> None:
    missing = [key for key in KIND_KEYS.get(one["type"], ()) if key not in one]
    if missing:
        raise ValueError(f"{name}: missing {', '.join(missing)}")
    groups = [group for group, _ in DOOR_GROUPS]
    if one["type"] == "landing" and one["group"] not in groups:
        raise ValueError(f"{name}: unknown group {one['group']!r}, expected one of {groups}")


def commercial_fields(one: dict[str, str], meta: dict[str, list[str]]) -> dict:
    """Optional keys of the commercial pages; the other page types leave them empty."""
    return {
        "headline": one.get("headline"),
        "lede": one.get("lede"),
        "base_line": one.get("base_line"),
        "secondary": parse_link(one["secondary"]) if "secondary" in one else None,
        "subject": one.get("subject"),
        "cta": one.get("cta"),
        "group": one.get("group"),
        "door": one.get("door"),
        "door_text": one.get("door_text"),
        "offers": tuple(parse_offer(value) for value in meta.get("offer", [])),
    }


def load_page(path: Path) -> Page:
    meta, body = parse_front_matter(path.read_text(encoding="utf-8"), path.name)
    missing = [key for key in REQUIRED_KEYS if key not in meta]
    if missing:
        raise ValueError(f"{path.name}: missing {', '.join(missing)}")
    one = {key: values[0] for key, values in meta.items()}
    if one["type"] not in PAGE_TYPES:
        raise ValueError(f"{path.name}: unknown type {one['type']!r}")
    if not SLUG_RE.match(one["slug"]) or one["slug"] in RESERVED_SLUGS:
        raise ValueError(f"{path.name}: bad or reserved slug {one['slug']!r}")
    check_kind_keys(one, path.name)
    try:
        extra = commercial_fields(one, meta)
    except ValueError as error:
        raise ValueError(f"{path.name}: {error}") from error
    return Page(
        kind=one["type"],
        order=int(one["order"]),
        slug=one["slug"],
        title=one["title"],
        description=one["description"],
        published=date.fromisoformat(one["published"]),
        updated=date.fromisoformat(one["updated"]),
        body_html=render_markdown(body),
        kicker=one.get("kicker"),
        origin=one.get("origin"),
        origin_label=one.get("origin_label"),
        origin_url=one.get("origin_url"),
        pdf=one.get("pdf"),
        pdf_pages=int(one["pdf_pages"]) if "pdf_pages" in one else None,
        cites=tuple(parse_citation(value) for value in meta.get("cite", [])),
        **extra,
    )


def load_site(pages_dir: Path = PAGES_DIR) -> list[Page]:
    pages = sorted(
        (load_page(path) for path in pages_dir.glob("*.md")),
        key=lambda page: (PAGE_TYPES.index(page.kind), page.order, page.slug),
    )
    slugs = [page.slug for page in pages]
    duplicated = sorted({slug for slug in slugs if slugs.count(slug) > 1})
    if duplicated:
        raise ValueError(f"duplicated slugs: {duplicated}")
    if [page.slug for page in pages if page.is_home] != ["index"]:
        raise ValueError("there must be exactly one home page, with slug 'index'")
    notes = {page.slug for page in pages if page.kind == "note"}
    for page in pages:
        if page.kind == "question" and page.origin not in notes and not page.origin_url:
            raise ValueError(f"{page.slug}: origin must be a field note or an origin_url")
        if page.secondary and page.secondary[1] not in slugs:
            raise ValueError(f"{page.slug}: link to an unknown page {page.secondary[1]!r}")
    return pages


# ---------------------------------------------------------------- helpers


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def human_date(day: date) -> str:
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


def href(path: str, depth: int) -> str:
    """Relative link from a page at `depth` folders below the root to a site path."""
    return f"{'../' * depth}{path}" or "./"


def notes_of(pages: list[Page]) -> list[Page]:
    return [page for page in pages if page.kind == "note"]


def questions_of(pages: list[Page], origin: str | None = None) -> list[Page]:
    return [page for page in pages
            if page.kind == "question" and (origin is None or page.origin == origin)]


def landings_of(pages: list[Page], group: str) -> list[Page]:
    return [page for page in pages if page.kind == "landing" and page.group == group]


def find(pages: list[Page], slug: str) -> Page:
    return next(page for page in pages if page.slug == slug)


def link_label(url: str) -> str:
    return url.removeprefix("https://").removeprefix("http://").removeprefix("www.")


def citation_html(citation: Citation) -> str:
    text = render_inline(citation.text)
    if not citation.url:
        return text
    return f'{text} <a href="{esc(citation.url)}">{esc(link_label(citation.url))}</a>'


def pdf_link(note: Page) -> str:
    return f'<a href="{esc(note.pdf or "")}">PDF, {note.pdf_pages} pages</a>'


# ---------------------------------------------------------------- structured data


def person_ref() -> dict:
    return {
        "@type": "Person",
        "@id": f"{SITE_URL}/{AUTHOR_SLUG}/#person",
        "name": AUTHOR,
        "url": f"{SITE_URL}/{AUTHOR_SLUG}/",
        "sameAs": [LINKEDIN, GITHUB],
    }


def person_full(page: Page) -> dict:
    return {
        **person_ref(),
        "jobTitle": "Deployment Strategist",
        "description": page.description,
        "email": f"mailto:{EMAIL}",
        "homeLocation": {"@type": "Place", "name": LOCATION},
        "knowsAbout": list(KNOWS_ABOUT),
    }


def article_data(page: Page, pages: list[Page]) -> dict:
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": page.title[:110],
        "description": page.description,
        "url": page.url,
        "mainEntityOfPage": page.url,
        "inLanguage": "en",
        "datePublished": page.published.isoformat(),
        "dateModified": page.updated.isoformat(),
        "author": person_ref(),
    }
    if page.kind == "note" and page.pdf:
        data["associatedMedia"] = {"@type": "MediaObject", "contentUrl": page.pdf,
                                   "encodingFormat": "application/pdf"}
    if page.kind == "question":
        data["isBasedOn"] = find(pages, page.origin).pdf if page.origin else page.origin_url
        data["citation"] = [
            {"@type": "CreativeWork", "name": citation.text.replace("*", ""),
             **({"url": citation.url} if citation.url else {})}
            for citation in page.cites
        ]
    return data


def service_data(offer: Offer) -> dict:
    price_key = "minPrice" if offer.is_from_price else "price"
    return {
        "@type": "Service",
        "name": offer.name,
        "provider": person_ref(),
        "areaServed": list(AREA_SERVED),
        "offers": {
            "@type": "Offer",
            "priceSpecification": {"@type": "UnitPriceSpecification", "priceCurrency": "USD",
                                   price_key: offer.amount, "unitText": offer.unit},
        },
    }


def webpage_data(page: Page) -> dict:
    data = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": page.title,
        "description": page.description,
        "url": page.url,
        "inLanguage": "en",
        "dateModified": page.updated.isoformat(),
        "isPartOf": {"@type": "WebSite", "url": f"{SITE_URL}/"},
        "author": person_ref(),
    }
    if page.offers:
        data["mainEntity"] = [service_data(offer) for offer in page.offers]
    return data


def structured_data(page: Page, pages: list[Page]) -> dict:
    base = {"@context": "https://schema.org"}
    if page.kind == "home":
        return {**base, "@type": "WebSite", "name": AUTHOR, "url": page.url, "inLanguage": "en",
                "description": page.description, "author": person_ref()}
    if page.kind == "author":
        return {**base, "@type": "ProfilePage", "url": page.url,
                "dateModified": page.updated.isoformat(), "mainEntity": person_full(page)}
    if page.kind == "book":
        return {**base, "@type": "Book", "name": page.title, "url": page.url, "inLanguage": "en",
                "description": page.description, "creativeWorkStatus": "Manuscript",
                "author": person_ref()}
    if page.kind in ("landing", "page"):
        return webpage_data(page)
    return article_data(page, pages)


# ---------------------------------------------------------------- page parts


def document_title(page: Page) -> str:
    titles = {
        "home": page.title,
        "author": f"{AUTHOR} · Deployment Strategist, Supply Chain & Operations",
        "book": f"{page.title} · a manuscript by {AUTHOR}",
        "note": f"{page.title} · field notes by {AUTHOR}",
    }
    return titles.get(page.kind, f"{page.title} · {AUTHOR}")


def verification_tags(page: Page) -> str:
    if not page.is_home:
        return ""
    tags = []
    if GOOGLE_SITE_VERIFICATION:
        tags.append(f'<meta name="google-site-verification" content="{esc(GOOGLE_SITE_VERIFICATION)}">')
    if BING_SITE_VERIFICATION:
        tags.append(f'<meta name="msvalidate.01" content="{esc(BING_SITE_VERIFICATION)}">')
    return "\n".join(tags)


def head(page: Page, pages: list[Page], depth: int) -> str:
    og_types = {"home": "website", "author": "profile", "book": "book", "landing": "website", "page": "website"}
    og_type = og_types.get(page.kind, "article")
    data = json.dumps(structured_data(page, pages), ensure_ascii=False).replace("</", "<\\/")
    prefix = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(document_title(page))}</title>
<meta name="description" content="{esc(page.description)}">
<meta name="author" content="{AUTHOR}">
<link rel="canonical" href="{page.url}">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#101217">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(page.title)}">
<meta property="og:description" content="{esc(page.description)}">
<meta property="og:url" content="{page.url}">
<meta property="og:site_name" content="{AUTHOR}">
<meta name="twitter:card" content="summary">
{verification_tags(page)}
<link rel="icon" href="{prefix}favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{prefix}style.css">
<script type="application/ld+json">{data}</script>
</head>"""


def site_header(depth: int) -> str:
    home = href("", depth)
    items = []
    for label, target in NAV:
        link = f"{home}{target}" if target.startswith("#") else href(target, depth)
        css = ' class="nav-contact"' if target == "contact/" else ""
        items.append(f'<li><a{css} href="{link}">{label}</a></li>')
    links = "\n".join(items)
    return f"""<header class="site-header"><div class="wrap">
<a class="name" href="{home}">{AUTHOR}</a>
<nav aria-label="Site"><ul>
{links}
</ul></nav>
</div></header>"""


def site_footer(depth: int) -> str:
    return f"""<footer class="site-footer"><div class="wrap">
<p><a href="{href(AUTHOR_SLUG + '/', depth)}">{AUTHOR}</a> · {AUTHOR_ROLE}</p>
<p><a href="{LINKEDIN}">LinkedIn</a> · <a href="{GITHUB}">GitHub</a></p>
</div></footer>"""


def byline(page: Page, depth: int) -> str:
    parts = [
        f'By <a href="{href(AUTHOR_SLUG + "/", depth)}">{AUTHOR}</a>',
        f'<time datetime="{page.published.isoformat()}">{human_date(page.published)}</time>',
    ]
    if page.updated != page.published:
        parts.append(f'updated <time datetime="{page.updated.isoformat()}">{human_date(page.updated)}</time>')
    return f'<p class="byline">{" · ".join(parts)}</p>'


def mark_first_paragraph(body_html: str, css_class: str) -> str:
    return body_html.replace("<p>", f'<p class="{css_class}">', 1)


def lead_with_answer(body_html: str) -> str:
    return mark_first_paragraph(body_html, "answer")


def origin_line(page: Page, pages: list[Page], depth: int) -> str:
    if page.origin:
        note = find(pages, page.origin)
        return (f'<p class="origin">From the field notes <a href="{href(note.path, depth)}">'
                f'<em>{esc(note.title)}</em></a> · {pdf_link(note)}</p>')
    return f'<p class="origin">From <a href="{esc(page.origin_url or "")}">{esc(page.origin_label or "")}</a></p>'


def heading(page: Page) -> str:
    return render_inline(page.headline or page.title)


def contact_button(page: Page) -> str:
    """The one call to action of a commercial page: an email with the page's subject line."""
    subject = quote(page.subject or page.title, safe="")
    label = esc(page.cta or DEFAULT_CTA)
    return f'<a class="btn btn-contact" href="mailto:{EMAIL}?subject={subject}">{label}</a>'


def next_links(depth: int) -> str:
    links = " · ".join(f'<a href="{href(slug + "/", depth)}">{esc(label)}</a>' for label, slug in NEXT_LINKS)
    return f'<p class="next">{links}</p>'


# ---------------------------------------------------------------- page bodies


def question_main(page: Page, pages: list[Page], depth: int) -> str:
    sources = "\n".join(f"<li>{citation_html(citation)}</li>" for citation in page.cites)
    return f"""<article>
<h1>{render_inline(page.title)}</h1>
{byline(page, depth)}
{lead_with_answer(page.body_html)}
<h2>Sources</h2>
<ul class="sources">
{sources}
</ul>
{origin_line(page, pages, depth)}
</article>"""


def note_main(page: Page, pages: list[Page], depth: int) -> str:
    items = "\n".join(f'<li><a href="{href(question.path, depth)}">{render_inline(question.title)}</a></li>'
                      for question in questions_of(pages, page.slug))
    return f"""<article>
<p class="kicker">{esc(page.kicker or "Field notes")}</p>
<h1>{esc(page.title)}</h1>
{byline(page, depth)}
{lead_with_answer(page.body_html)}
<p class="cta"><a href="{esc(page.pdf or "")}">Read the field notes</a> (PDF, {page.pdf_pages} pages)</p>
<h2>Questions these field notes answer</h2>
<ul>
{items}
</ul>
</article>"""


def author_main(page: Page, pages: list[Page], depth: int) -> str:
    writing = [f'<li><a href="{href(note.path, depth)}"><em>{esc(note.title)}</em></a> · {pdf_link(note)}</li>'
               for note in notes_of(pages)]
    writing.append(f'<li><a href="{href(BOOK_SLUG + "/", depth)}"><em>The Deployment Chasm</em></a>, '
                   'a manuscript</li>')
    items = "\n".join(writing)
    return f"""<article>
<h1>{AUTHOR}</h1>
<p class="lede">{AUTHOR_ROLE} · {LOCATION}</p>
{page.body_html}
<h2>Writing</h2>
<ul>
{items}
</ul>
<h2>Contact</h2>
<p><a href="{LINKEDIN}">LinkedIn</a> · <a href="{GITHUB}">GitHub</a> · <a href="mailto:{EMAIL}">{EMAIL}</a></p>
</article>"""


def book_main(page: Page, pages: list[Page], depth: int) -> str:
    return f"""<article>
<p class="kicker">{esc(page.kicker or "Manuscript")}</p>
<h1><em>{esc(page.title)}</em></h1>
<p class="byline">By <a href="{href(AUTHOR_SLUG + '/', depth)}">{AUTHOR}</a></p>
{page.body_html}
</article>"""


def list_item(page: Page, depth: int, extra: str = "") -> str:
    title = f"<em>{esc(page.title)}</em>" if page.kind == "note" else render_inline(page.title)
    return (f'<li><a href="{href(page.path, depth)}">{title}</a>'
            f'<span class="gist">{esc(page.description)}{extra}</span></li>')


def hero(page: Page, depth: int) -> str:
    secondary = ""
    if page.secondary:
        label, slug = page.secondary
        secondary = f'\n<a class="btn btn-ghost" href="{href(slug + "/", depth)}">{esc(label)}</a>'
    base = f'\n<p class="base">{render_inline(page.base_line)}</p>' if page.base_line else ""
    return f"""<section class="hero">
<p class="kicker">{esc(page.kicker or AUTHOR_ROLE)}</p>
<h1>{heading(page)}</h1>
<p class="lede">{render_inline(page.lede or "")}</p>
<p class="actions">{contact_button(page)}{secondary}</p>{base}
</section>"""


def door_item(page: Page, depth: int) -> str:
    return (f'<li><a class="door" href="{href(page.path, depth)}">'
            f'<span class="door-t">{esc(page.door or page.title)}</span>'
            f'<span class="door-d">{esc(page.door_text or "")}</span></a></li>')


def doors(pages: list[Page], depth: int) -> str:
    groups = []
    for group, question in DOOR_GROUPS:
        items = "\n".join(door_item(page, depth) for page in landings_of(pages, group))
        groups.append(f'<h2 class="doors-q">{esc(question)}</h2>\n<ul class="doors">\n{items}\n</ul>')
    joined = "\n".join(groups)
    return f'<section id="industries" class="doors-block">\n{joined}\n</section>'


def library(pages: list[Page], depth: int) -> str:
    """The field notes and the short answers, at the foot of the home page."""
    notes = "\n".join(list_item(note, depth, f" · {pdf_link(note)}") for note in notes_of(pages))
    questions = "\n".join(list_item(question, depth) for question in questions_of(pages))
    return f"""<section id="library">
<h2 id="field-notes">Field notes</h2>
<ul class="list">
{notes}
</ul>
<h2 id="questions">Short answers</h2>
<ul class="list">
{questions}
</ul>
<p class="next"><a href="{href(AUTHOR_SLUG + '/', depth)}">About the author</a> · \
<a href="{href(BOOK_SLUG + '/', depth)}"><em>The Deployment Chasm</em></a>, a manuscript</p>
</section>"""


def home_main(page: Page, pages: list[Page], depth: int) -> str:
    return f"""{hero(page, depth)}
{doors(pages, depth)}
<div class="home-body">
{page.body_html}
</div>
{library(pages, depth)}"""


def landing_main(page: Page, pages: list[Page], depth: int) -> str:
    return f"""<article class="landing">
<p class="kicker">{esc(page.kicker or "Industry")}</p>
<h1>{heading(page)}</h1>
{mark_first_paragraph(page.body_html, "scene")}
<p class="actions">{contact_button(page)}</p>
{next_links(depth)}
</article>"""


def page_main(page: Page, pages: list[Page], depth: int) -> str:
    return f"""<article class="page">
<p class="kicker">{esc(page.kicker or page.title)}</p>
<h1>{heading(page)}</h1>
{page.body_html}
<p class="actions">{contact_button(page)}</p>
</article>"""


MAIN_BUILDERS = {
    "home": home_main,
    "question": question_main,
    "note": note_main,
    "author": author_main,
    "book": book_main,
    "landing": landing_main,
    "page": page_main,
}


def render_page(page: Page, pages: list[Page]) -> str:
    depth = 0 if page.is_home else 1
    main = MAIN_BUILDERS[page.kind](page, pages, depth)
    return f"""{head(page, pages, depth)}
<body>
{site_header(depth)}
<main class="wrap">
{main}
</main>
{site_footer(depth)}
</body>
</html>
"""


def not_found_html() -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found · {AUTHOR}</title>
<meta name="robots" content="noindex">
<meta name="color-scheme" content="dark">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<main class="wrap">
<h1>Page not found</h1>
<p>The page you asked for is not here. <a href="/">Go to the home page</a>.</p>
</main>
</body>
</html>
"""


# ---------------------------------------------------------------- site files


def robots_txt() -> str:
    agents = "".join(f"User-agent: {bot}\n" for bot in (*SEARCH_BOTS, *TRAINING_BOTS, "*"))
    rules = "Allow: /\n" + "".join(f"Disallow: {path}\n" for path in DISALLOWED_PATHS)
    return ("# Search engines, AI search and AI training crawlers may read this site.\n"
            "# Google-Extended covers Gemini training and grounding in the Gemini app.\n"
            f"{agents}{rules}\nSitemap: {SITE_URL}/sitemap.xml\n")


def sitemap_xml(pages: list[Page]) -> str:
    urls = "".join(f"  <url>\n    <loc>{page.url}</loc>\n    <lastmod>{page.updated.isoformat()}</lastmod>\n"
                   "  </url>\n" for page in pages)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')


def remove_stale(pages: list[Page], root: Path, manifest: Path) -> None:
    """Delete folders written by an earlier build for pages that no longer exist."""
    previous = set(json.loads(manifest.read_text(encoding="utf-8"))) if manifest.exists() else set()
    current = {page.slug for page in pages if not page.is_home}
    for slug in sorted(previous - current):
        folder = root / slug
        if SLUG_RE.match(slug) and (folder / "index.html").is_file():
            shutil.rmtree(folder)
            log.info("removed %s/", slug)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_site(pages: list[Page], root: Path = ROOT, manifest: Path = MANIFEST) -> None:
    remove_stale(pages, root, manifest)
    for page in pages:
        write_text(root / page.path / "index.html", render_page(page, pages))
    for asset in ASSETS:
        shutil.copyfile(SRC / asset, root / asset)
    shutil.rmtree(root / "files", ignore_errors=True)  # files/ is generated: a file removed from src/files/ goes too
    if FILES_DIR.is_dir():
        shutil.copytree(FILES_DIR, root / "files")
    write_text(root / "robots.txt", robots_txt())
    write_text(root / "sitemap.xml", sitemap_xml(pages))
    write_text(root / "404.html", not_found_html())
    write_text(root / ".nojekyll", "")
    current = sorted(page.slug for page in pages if not page.is_home)
    write_text(manifest, json.dumps(current, indent=2) + "\n")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    pages = load_site()
    write_site(pages)
    log.info("built %d pages at %s", len(pages), ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
