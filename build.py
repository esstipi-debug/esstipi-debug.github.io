#!/usr/bin/env python3
"""Build the static site under landpage/ from src/pages/*.md.

Usage:
    python build.py

Each page is a Markdown file that starts with a front matter block: "key: value"
lines between two "---" lines, where a repeated key ("cite", "offer") makes a
list. The build writes the site inside landpage/ (index.html, one folder per
page, style.css, favicon.svg, the files in src/files/, and sitemap.xml) and
writes robots.txt, a neutral 404.html and .nojekyll at the repository root.
Folders of pages that no longer exist are removed, using src/generated.json as
the record of what it wrote.

Page types: "question" and "note" are the field notes, "author" and "book" the
author page and the manuscript. "home" is the home page; "landing" the eight
entry pages, shown as doors on the home page (three situations first, then
three floors and two kinds of buyer); "page" the other commercial pages
(engagements, proof, working terms).

The home page is laid out by home.py as a working drawing, with the line drawings of drawings.py.
The hero desk picture (desk.webp and desk-800.webp) and the yard detail (yard.webp) are prepared by
desk.py in src/files/desk/ and gated independently on the home page; the present design draws neither
the yard nor the plates of plates.py, and both tools stay for when pictures return.
"""
from __future__ import annotations

import html
import json
import logging
import math
import re
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import quote

import markdown

ROOT = Path(__file__).resolve().parent
SITE_DIR = "landpage"
OUT = ROOT / SITE_DIR
SRC = ROOT / "src"
PAGES_DIR = SRC / "pages"
FILES_DIR = SRC / "files"
MANIFEST = SRC / "generated.json"
ASSETS = ("style.css", "home.css", "favicon.svg")

SITE_URL = f"https://esstipi-debug.github.io/{SITE_DIR}"
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
# A note says, in two lines of its own, what it is about and what the reader takes away: a title alone does not.
KIND_KEYS = {"home": ("headline", "lede"), "landing": ("group", "door", "door_text"), "note": ("about", "takeaway")}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESERVED_SLUGS = frozenset({"files", "src", "tests"})  # folders the build or the repository already use
FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.S)
MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")

# Commercial pages. A target that starts with "#" is an anchor on the home page.
NAV = (
    ("Engagements", "engagements/"),
    ("Proof", "proof/"),
    ("About", f"{AUTHOR_SLUG}/"),
    ("Contact", "contact/"),
)
# The first choice on the home page is what is happening, not who the visitor is: the situation doors
# stand alone under the hero. The doors by floor and by kind of buyer sit lower, under "industries".
SITUATION_GROUP = ("situation", "Which one is yours?")
DOOR_GROUPS = (("buyer", "What are you?"), ("floor", "Or where is the work?"))
ALL_GROUPS = (SITUATION_GROUP, *DOOR_GROUPS)

# The method, in the tailor's three verbs. On the home page each step is a panel, and the panels stack.
METHOD_STEPS = (
    ("Measure", "Count what the floor holds against what the record says."),
    ("Cut", "Take out the loss the count exposes, at its cause."),
    ("Stitch", "Stay through go-live until the new way of working holds."),
)
# The desk hero picture and detail cuts: desk.py prepares them independently in src/files/desk/.
DESK_SIZE = (1600, 900)
DESK_SMALL = 800  # width of the second file, for narrow screens
DESK_SPOTS = SRC / "desk.json"  # detail marks in percent of the picture
SERVICES_SLUG = "engagements"
HERO_SIZES = "(min-width: 62rem) 56vw, 100vw"  # the width the picture of the desk takes beside the headline
DETAIL_SIZES = {"yard": (800, 668)}  # detail cut of the picture used behind the How I work pillar
DESK_DETAILS = tuple(DETAIL_SIZES)
# In src/files/fonts/: the sans, a variable file, and the mono. The folder also keeps the two files of the
# earlier design, which the radar page (atlas/) still loads by itself; no style sheet of the site names them.
FONT_FILES = ("ibm-plex-sans-latin-variable.woff2", "ibm-plex-mono-latin-400.woff2")
GROUND = "#0a1626"  # --ground in src/style.css: the browser bar and the 404 page take the page colour
NEXT_LINKS = (("Engagements and fees", SERVICES_SLUG), ("Proof", "proof"), ("Working terms", "working-terms"))
# The button asks for what the reader sees. Naming what is broken is my work, not theirs.
DEFAULT_CTA = "Tell me what you’re seeing"  # a typographic apostrophe: the closing call sets these words very large
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
    about: str | None = None     # a note: what it is about, in one sentence of its description
    takeaway: str | None = None  # a note: what the reader takes away, in the rest of that description
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
    symptoms: tuple[str, ...] = ()  # the home page: what is going wrong, one sentence each

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


@dataclass(frozen=True)
class HomeFigure:
    """A number the home page prints large: what it measures, where it comes from, and the page where it
    can be checked."""
    number: str
    caption: str
    label: str
    slug: str
    grade: str  # one of FIGURE_GRADES: what kind of source stands behind the number


# What stands behind a number, in the words the page shows: a study, a company filing, my own analysis
# (of public data, published and re-runnable) or my own field work (lived, as HECHOS records it).
# "My analysis", not "My data": the dataset is public, and only the reading of it is mine.
FIGURE_GRADES = ("Study", "Company filing", "My analysis", "My field work")

# The triage behind the 57%, as published in the demo's README (Which Record Lies?, Olist dataset):
# 2,708 "not received" claims on delivered orders, split by what the records say.
CLAIMS_TRIAGE = (
    ("late", "late orders", 1542),
    ("flag", "at flagged sellers", 73),
    ("open", "with no clear cause", 1093),
)

# A chain: the record is wrong, a go-live costs, what I measure, what I did.
HOME_FIGURES = (
    HomeFigure("65%", "of about 370,000 inventory records were inaccurate, in one retailer’s audit.",
               "Why records drift", "why-inventory-records-do-not-match-the-shelf", "Study"),
    HomeFigure("USD 64M", "of sales a US cosmetics maker could not ship in the year it switched on a new ERP, "
               "by its own estimate.", "Before your go-live", "a-new-system-goes-live", "Company filing"),
    HomeFigure("57%", "of “not received” reviews on delivered orders were written on or before the "
               "delivery day, in a public marketplace dataset.", "See the audit", "not-received-but-delivered",
               "My analysis"),
    HomeFigure("50,000", "SKU distribution centre, taken through its warehouse-system changeover. "
               "Order processing time fell about 20% once the floor workarounds were retired.", "Proof", "proof",
               "My field work"),
)


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
    groups = [group for group, _ in ALL_GROUPS]
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
        "symptoms": tuple(meta.get("symptom", [])),
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
        about=one.get("about"),
        takeaway=one.get("takeaway"),
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
    """A source as the page prints it. A page range takes a hyphen: the site prints no dash."""
    text = render_inline(citation.text.replace("–", "-"))
    if not citation.url:
        return text
    return f'{text} <a href="{esc(citation.url)}">{esc(link_label(citation.url))}</a>'


def pdf_link(note: Page, css_class: str = "") -> str:
    named = f' class="{esc(css_class)}"' if css_class else ""
    return f'<a{named} href="{esc(note.pdf or "")}">PDF, {note.pdf_pages} pages</a>'


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


def font_preload(prefix: str) -> str:
    """The display font is on every page, in the first screen: fetch it early. Nothing while the file is missing."""
    if not (FILES_DIR / "fonts" / FONT_FILES[0]).is_file():
        return ""
    return f'<link rel="preload" href="{prefix}files/fonts/{FONT_FILES[0]}" as="font" type="font/woff2" crossorigin>'


def home_links(page: Page, prefix: str) -> str:
    """What only the home page loads: its own style sheet and, once it exists, the picture of the desk."""
    if not page.is_home:
        return ""
    links = [f'<link rel="stylesheet" href="{prefix}home.css">']
    if hero_desk_ready():
        large, small = f"{prefix}files/desk/{desk_name()}", f"{prefix}files/desk/{desk_name(small=True)}"
        links.append(f'<link rel="preload" as="image" href="{large}" '
                     f'imagesrcset="{small} {DESK_SMALL}w, {large} {DESK_SIZE[0]}w" imagesizes="{HERO_SIZES}" '
                     f'fetchpriority="high">')
    return "\n" + "\n".join(links)


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
<meta name="theme-color" content="{GROUND}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(page.title)}">
<meta property="og:description" content="{esc(page.description)}">
<meta property="og:url" content="{page.url}">
<meta property="og:site_name" content="{AUTHOR}">
<meta name="twitter:card" content="summary">
{verification_tags(page)}
<link rel="icon" href="{prefix}favicon.svg" type="image/svg+xml">
{font_preload(prefix)}
<link rel="stylesheet" href="{prefix}style.css">{home_links(page, prefix)}
<script type="application/ld+json">{data}</script>
</head>"""


def site_header(depth: int, current: str = "") -> str:
    home = href("", depth)
    items = []
    for label, target in NAV:
        link = f"{home}{target}" if target.startswith("#") else href(target, depth)
        active = ' aria-current="page"' if current and target == current else ""
        items.append(f'<li><a href="{link}"{active}>{label}</a></li>')
    links = "\n".join(items)
    return f"""<header class="site-header"><div class="wrap">
<a class="name" href="{home}">{AUTHOR}</a>
<nav aria-label="Site"><ul>
{links}
</ul></nav>
</div>
<div class="tape" aria-hidden="true"><span></span></div>
</header>"""


def site_footer(depth: int) -> str:
    roles = "\n".join(f"<p>{esc(part)}</p>" for part in AUTHOR_ROLE.split(" · "))
    return f"""<footer class="site-footer"><div class="wrap">
<div>
<a class="name" href="{href(AUTHOR_SLUG + '/', depth)}">{AUTHOR}</a>
{roles}
</div>
<ul>
<li><a href="{LINKEDIN}">LinkedIn</a></li>
<li><a href="{GITHUB}">GitHub</a></li>
</ul>
</div></footer>"""


def byline(page: Page, depth: int) -> str:
    """The author and the dates: one middle dot at most, between the name and the dates."""
    author = f'By <a href="{href(AUTHOR_SLUG + "/", depth)}">{AUTHOR}</a>'
    dates = [f'<time datetime="{page.published.isoformat()}">{human_date(page.published)}</time>']
    if page.updated != page.published:
        dates.append(f'updated <time datetime="{page.updated.isoformat()}">{human_date(page.updated)}</time>')
    return f'<p class="byline">{author} · {", ".join(dates)}</p>'


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


def headline_group(headline: str, line: str = "") -> str:
    """The headline and, under it, the small line that names the page's section, in one heading group:
    the line labels the headline above it, never the section that follows (proof opens on a section head)."""
    if not line:
        return f"<h1>{headline}</h1>"
    return f'<hgroup>\n<h1>{headline}</h1>\n<p class="kicker">{line}</p>\n</hgroup>'


def contact_href(page: Page) -> str:
    """An email to the author with the page's subject line."""
    return f'mailto:{EMAIL}?subject={quote(page.subject or page.title, safe="")}'


def contact_button(page: Page) -> str:
    """The one call to action of a commercial page: an email with the page's subject line."""
    return f'<a class="btn btn-contact" href="{contact_href(page)}">{esc(page.cta or DEFAULT_CTA)}</a>'


def next_links(depth: int) -> str:
    links = ", ".join(f'<a href="{href(slug + "/", depth)}">{esc(label)}</a>' for label, slug in NEXT_LINKS)
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


def note_answers(page: Page, pages: list[Page], depth: int) -> str:
    """The short answers drawn from a field note. A note with none yet prints no heading and no empty list."""
    questions = questions_of(pages, page.slug)
    if not questions:
        return ""
    items = "\n".join(f'<li><a href="{href(question.path, depth)}">{render_inline(question.title)}</a></li>'
                      for question in questions)
    return f'\n<h2>Questions these field notes answer</h2>\n<ul class="links">\n{items}\n</ul>'


def note_main(page: Page, pages: list[Page], depth: int) -> str:
    return f"""<article>
{headline_group(esc(page.title), esc(page.kicker or "Field notes"))}
{byline(page, depth)}
{lead_with_answer(page.body_html)}
<p class="cta"><a href="{esc(page.pdf or "")}">Read the field notes</a> (PDF, {page.pdf_pages} pages)</p>\
{note_answers(page, pages, depth)}
</article>"""


def author_main(page: Page, pages: list[Page], depth: int) -> str:
    import shelf  # late: shelf.py lays the field notes out with this module's data and helpers
    return f"""<article>
<h1>{AUTHOR}</h1>
<p class="lede">{AUTHOR_ROLE}, {LOCATION}</p>
{page.body_html}
<h2 id="writing">Writing</h2>
{shelf.shelf(pages, depth)}
<p class="shelf-book"><a href="{href(BOOK_SLUG + "/", depth)}"><em>The Deployment Chasm</em></a>, a manuscript</p>
<h2>Contact</h2>
<p><a href="{LINKEDIN}">LinkedIn</a>, <a href="{GITHUB}">GitHub</a>, <a href="mailto:{EMAIL}">{EMAIL}</a></p>
</article>"""


def book_main(page: Page, pages: list[Page], depth: int) -> str:
    import book  # late: book.py renders the zero-JS leafable sample reader from src/files/book/
    return f"""<article class="book-page">
{headline_group(esc(page.title), esc(page.kicker or "Manuscript"))}
<p class="byline">By <a href="{href(AUTHOR_SLUG + '/', depth)}">{AUTHOR}</a></p>
{book.reader_html(depth)}
{page.body_html}
</article>"""


def list_item(page: Page, depth: int, extra: str = "") -> str:
    title = f"<em>{esc(page.title)}</em>" if page.kind == "note" else render_inline(page.title)
    return (f'<li><a href="{href(page.path, depth)}">{title}</a>'
            f'<span class="gist">{esc(page.description)}{extra}</span></li>')


def desk_dir() -> Path:
    return FILES_DIR / "desk"


def desk_name(small: bool = False) -> str:
    return f"desk{f'-{DESK_SMALL}' if small else ''}.webp"


def detail_name(name: str) -> str:
    return f"{name}.webp"


def hero_desk_files() -> tuple[str, ...]:
    """The hero desk image in both sizes."""
    return (desk_name(), desk_name(small=True))


def detail_files() -> tuple[str, ...]:
    """Detail cuts prepared from the desk picture."""
    return tuple(detail_name(name) for name in DESK_DETAILS)


def hero_desk_ready() -> bool:
    """True once both hero desk sizes exist in src/files/desk/."""
    folder = desk_dir()
    return all((folder / name).is_file() for name in hero_desk_files())


def detail_ready(name: str = "yard") -> bool:
    """True once the named detail cut exists in src/files/desk/."""
    return (desk_dir() / detail_name(name)).is_file()


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def read_marks(path: Path) -> object:
    """The marks of the desk as written, or None while the file does not exist."""
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path.name}: is not valid JSON ({error.msg}, line {error.lineno})") from error


def checked_box(file_name: str, key: str, box: object) -> tuple[float, ...]:
    """A mark is left, top, width and height, in percent of the picture, and lies inside it."""
    if not (isinstance(box, list) and len(box) == 4 and all(is_number(value) for value in box)):
        raise ValueError(f"{file_name}: {key} needs four numbers: left, top, width and height")
    left, top, wide, high = box
    if wide <= 0 or high <= 0:
        raise ValueError(f"{file_name}: {key} has no width or no height")
    if left < 0 or top < 0 or left + wide > 100 or top + high > 100:
        raise ValueError(f"{file_name}: {key} lies outside the picture")
    return (left, top, wide, high)


def load_details(path: Path) -> dict[str, tuple[float, ...]]:
    """Where the details lie on the picture: under "details" in desk.json, left, top, width and height in percent."""
    marks = read_marks(path)
    if marks is None:
        return {}
    if not isinstance(marks, dict):
        raise ValueError(f"{path.name}: needs a JSON object")
    raw = marks.get("details", {})
    if not isinstance(raw, dict):
        raise ValueError(f'{path.name}: "details" must be an object')
    details = {}
    for name, box in raw.items():
        if name not in DETAIL_SIZES:
            raise ValueError(f"{path.name}: unknown detail '{name}'")
        details[name] = checked_box(path.name, name, box)
    return details


def home_main(page: Page, pages: list[Page], depth: int) -> str:
    import home  # late: home.py lays the page out with this module's data and helpers
    return home.main(page, pages, depth)


def landing_main(page: Page, pages: list[Page], depth: int) -> str:
    return f"""<article class="landing">
{headline_group(heading(page), esc(page.kicker or "Industry"))}
{mark_first_paragraph(page.body_html, "scene")}
<p class="actions">{contact_button(page)}</p>
{next_links(depth)}
</article>"""


def section_line(page: Page) -> str:
    """The small line under a page's headline, naming its section. Empty where it would only say the
    headline again (a page with no headline of its own, such as the working terms)."""
    line = page.kicker or page.title
    if line.strip().lower() == (page.headline or page.title).strip().lower():
        return ""
    return esc(line)


def contact_link(page: Page) -> str:
    """The contact call as a link: the words and the address of the button, for a page that already showed it."""
    return f'<a class="page-close-link" href="{contact_href(page)}">{esc(page.cta or DEFAULT_CTA)}</a>'


def page_main(page: Page, pages: list[Page], depth: int) -> str:
    """A page in its own words, with what it asks for put in: the plates, the drawings and the rows. The
    contact button closes the page, unless the page marks a place for it under the headline; then the page
    closes with the same call as a link, so that there is still one button and the last word is still the call."""
    import page_parts  # late: both draw with this module's data and helpers
    import risks
    body = page_parts.fold_rows(page_parts.with_drawings(risks.with_plates(page.body_html, depth), pages))
    button = f'<p class="actions">{contact_button(page)}</p>'
    if page_parts.CONTACT in body:
        body, ending = body.replace(page_parts.CONTACT, button, 1), f'<p class="page-close">{contact_link(page)}</p>'
    else:
        ending = button
    return f"""<article class="page">
{headline_group(heading(page), section_line(page))}
{body}
{ending}
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
    body_class = f"kind-{page.kind}{' has-yard' if page.is_home and detail_ready('yard') else ''}"
    main_class = "" if page.is_home else ' class="wrap"'  # the home page lays out its own full-width sections
    return f"""{head(page, pages, depth)}
<body class="{body_class}">
<a class="skip" href="#main">Skip to content</a>
{site_header(depth, page.path)}
<main id="main"{main_class}>
{main}
</main>
{site_footer(depth)}
</body>
</html>
"""


def not_found_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>404 · Page not found</title>
<meta name="robots" content="noindex">
<meta name="color-scheme" content="dark">
<style>
body{margin:0;background:GROUND;color:#e8eef8;font:16px/1.6 system-ui,-apple-system,sans-serif}
main{max-width:34rem;margin:18vh auto 0;padding:0 1.25rem}
h1{font-size:1.25rem;font-weight:600;margin:0 0 .5rem}
p{color:#aebdd2;margin:0}
</style>
</head>
<body>
<main class="wrap">
<h1>Page not found</h1>
<p>There is nothing at this address.</p>
</main>
</body>
</html>
""".replace("GROUND", GROUND)


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


def write_site(
    pages: list[Page],
    root: Path = OUT,
    manifest: Path = MANIFEST,
    host_root: Path | None = None,
) -> None:
    site_host = root if host_root is None else host_root
    remove_stale(pages, root, manifest)
    for page in pages:
        write_text(root / page.path / "index.html", render_page(page, pages))
    for asset in ASSETS:
        shutil.copyfile(SRC / asset, root / asset)
    shutil.rmtree(root / "files", ignore_errors=True)  # files/ is generated: a file removed from src/files/ goes too
    if FILES_DIR.is_dir():
        shutil.copytree(FILES_DIR, root / "files")
    write_text(root / "sitemap.xml", sitemap_xml(pages))
    write_text(site_host / "robots.txt", robots_txt())
    write_text(site_host / "404.html", not_found_html())
    write_text(site_host / ".nojekyll", "")
    current = sorted(page.slug for page in pages if not page.is_home)
    write_text(manifest, json.dumps(current, indent=2) + "\n")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    pages = load_site()
    write_site(pages, OUT, MANIFEST, host_root=ROOT)
    log.info("built %d pages at %s", len(pages), OUT)
    return 0


if __name__ == "__main__":
    import build  # run as the module the other files import, so its data exists once

    raise SystemExit(build.main())
