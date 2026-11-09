"""Checks on the commercial pages: the home page, the five landing pages and the other pages.

The fixture builds into a temporary folder, not the repository.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build  # noqa: E402

COMMERCIAL_KINDS = ("home", "landing", "page")
LANDING_SECTIONS = ("What I check first", "Where I have stood", "What I don't claim", "How we would start")
DOORS_PER_GROUP = {"floor": 3, "buyer": 2}
PRICE_WORDS = re.compile(r"\bper (?:hour|day|month)\b|\bfrom USD\b", re.I)
FOREIGN_MONEY = re.compile(r"[$€£]|\b(?:AUD|CAD|GBP|EUR|CLP|UF)\b")
BANNED = re.compile(
    r"\b(?:SAP|Oracle|revolutionary|unprecedented|cutting[- ]edge|state[- ]of[- ]the[- ]art|game[- ]changer"
    r"|unicorns?|paradigm|world[- ]class|best[- ]in[- ]class|seamless(?:ly)?|unparalleled|guarantee[sd]?)\b",
    re.I,
)
SPANISH = re.compile(r"[¿¡ñÑ]|\b(?:que|para|los|las|del|una|por|con|también|más)\b", re.I)
# Stored as the sha256 of the lower-case name, as in linkedin_gate.py, so the rule does not write the name.
EMPLOYER_SHA256 = "317d710efc13fed0f8c4fc2b9a35d0106a560a632af7bdf38ec5a2747b8b4c7e"
WORD = re.compile(r"[^\W\d_]+")
NUMBER = re.compile(r"\d(?:[\d,.:]*\d)?(?:%|M\b)?")
FORM_NAMES = re.compile(r"\b(?:B-1|W-8BEN(?:-E)?)\b")  # names with a digit in them, not figures
JSONLD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
CONTACT_BUTTON = re.compile(r'<a class="btn btn-contact" href="([^"]+)"')

# Every figure a commercial page may print, and where it comes from. A new number fails the test
# until it is added here with its source. HECHOS = cv dossier/HECHOS.md; plan = the approved site plan.
FIGURES = {
    "02:30": "the night shift, a time of day used as a scene, not a measurement",
    "12": "best fit: a system change in the last or next 12 months (plan C)",
    "15": "15 planners (HECHOS, Trayectoria 2016-2017); 15 to 20 hours a week (plan B5)",
    "20": "team of 20 (HECHOS, AGCO row); 15 to 20 hours a week; 20 October 2026 (HECHOS, fdekit)",
    "20%": "order processing time down 20% (HECHOS, AGCO row)",
    "23": "23 operators trained on RF (HECHOS, AGCO row)",
    "25": "25 October 2026, date of the receiving-kit count (HECHOS, mellon)",
    "30": "30-60-90-day plan; measures that hold 30 days after go-live (plan B5)",
    "30%": "30% at the start and 30% after 30 days (plan B5)",
    "31": "31 October 2026, date of the engine count (HECHOS, kern)",
    "40%": "40% at go-live (plan B5)",
    "50%": "50% at the start and 50% on delivery (plan B5)",
    "57%": "Olist triage, published page not-received-but-delivered",
    "60": "30-60-90-day plan; 60-minute sessions (plan B5)",
    "65%": "DeHoratius and Raman 2008, published page why-inventory-records-do-not-match-the-shelf",
    "90": "the 90-day check; visa stays of up to 90 days; 30-60-90-day plan",
    "95%": "MIT NANDA 2025, The GenAI Divide (book appendix EV-MIT-01, industry report)",
    "100": "about 100 people (HECHOS, Trayectoria 2018-2020)",
    "200": "more than 200 stores (HECHOS, Trayectoria 2016-2017)",
    "250": "advisory fee in USD per hour (plan C, option A)",
    "370,000": "DeHoratius and Raman 2008, published page why-inventory-records-do-not-match-the-shelf",
    "600": "Australian Visitor visa, subclass 600 (Home Affairs)",
    "1,079": "receiving-kit test count (HECHOS, mellon)",
    "1,187": "field-kit passing tests (HECHOS, fdekit)",
    "1,200": "on-site day fee in USD (plan C, option A)",
    "2022": "start of the Melbourne role (HECHOS, AGCO row)",
    "2024": "end of the Melbourne role (HECHOS, AGCO row)",
    "2025": "year of the MIT NANDA report",
    "2026": "year of the test counts (HECHOS, Sistemas construidos)",
    "6,000": "fractional lead fee in USD per month (plan C, option A)",
    "8,500": "field audit fee in USD (plan C, option A)",
    "9,689": "engine test count, CLM_TESTS_KERN_ACTUAL (HECHOS, kern)",
    "15,000": "cutover leadership fee in USD (plan C, option A)",
    "50,000": "50,000-SKU distribution centre (HECHOS, AGCO row)",
    "5M": "about USD 5M of inventory freed (HECHOS, Trayectoria 2020-2022)",
    "10M": "best-fit revenue floor (plan C)",
    "15M": "USD 15M budget (HECHOS, Trayectoria 2018-2020)",
    "30M": "USD 30M P&L (HECHOS, Trayectoria 2020-2022)",
    "100M": "USD 100M inventory position (HECHOS, Trayectoria 2014-2016); best-fit revenue ceiling (plan C)",
}


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[build.Page]]:
    root = tmp_path_factory.mktemp("site")
    pages = build.load_site()
    build.write_site(pages, root, root / "generated.json")
    return root, pages


def read(root: Path, page: build.Page) -> str:
    return (root / page.path / "index.html").read_text(encoding="utf-8")


def commercial(pages: list[build.Page]) -> list[build.Page]:
    return [page for page in pages if page.kind in COMMERCIAL_KINDS]


def landings(pages: list[build.Page], group: str | None = None) -> list[build.Page]:
    return [page for page in pages if page.kind == "landing" and (group is None or page.group == group)]


def main_text(page_html: str) -> str:
    """Visible text of <main>, without scripts and without the home page's list of field notes."""
    body = page_html.split("<main", 1)[1].split("</main>", 1)[0]
    body = re.sub(r"<script.*?</script>", " ", body, flags=re.S)
    body = re.sub(r'<section id="library">.*?</section>', " ", body, flags=re.S)
    body = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", html.unescape(body)).strip()


def employer_mentions(text: str) -> int:
    return sum(hashlib.sha256(word.lower().encode()).hexdigest() == EMPLOYER_SHA256
               for word in WORD.findall(text))


def test_landing_pages_follow_one_skeleton(site):
    root, pages = site
    assert len(landings(pages)) == sum(DOORS_PER_GROUP.values())
    for page in landings(pages):
        text = read(root, page)
        headings = [html.unescape(h).replace("’", "'") for h in re.findall(r"<h2[^>]*>(.*?)</h2>", text)]
        assert headings == list(LANDING_SECTIONS), page.slug
        assert '<p class="scene">' in text, page.slug


def test_home_has_a_door_to_every_landing_page(site):
    root, pages = site
    text = read(root, build.find(pages, "index"))
    for group, count in DOORS_PER_GROUP.items():
        assert len(landings(pages, group)) == count, group
        for page in landings(pages, group):
            assert f'<a class="door" href="{page.slug}/">' in text, page.slug
    for anchor in ("industries", "questions", "field-notes"):
        assert f'id="{anchor}"' in text, anchor


def test_one_contact_button_per_commercial_page(site):
    root, pages = site
    for page in commercial(pages):
        buttons = CONTACT_BUTTON.findall(read(root, page))
        assert len(buttons) == 1, page.slug
        assert buttons[0].startswith(f"mailto:{build.EMAIL}?subject="), page.slug
        assert unquote(buttons[0].split("subject=", 1)[1]).strip(), page.slug


def test_prices_only_on_the_engagements_page_and_only_in_usd(site):
    root, pages = site
    for page in commercial(pages):
        text = main_text(read(root, page))
        assert not FOREIGN_MONEY.search(text), page.slug
        if page.slug != "engagements":
            assert not PRICE_WORDS.search(text), (page.slug, PRICE_WORDS.search(text).group(0))
    engagements = build.find(pages, "engagements")
    text = main_text(read(root, engagements))
    assert engagements.offers
    for offer in engagements.offers:
        assert f"USD {offer.amount:,}" in text, offer.name


def test_services_carry_usd_prices_in_structured_data(site):
    root, pages = site
    engagements = build.find(pages, "engagements")
    data = json.loads(JSONLD.search(read(root, engagements)).group(1))
    services = data["mainEntity"]
    assert [service["name"] for service in services] == [offer.name for offer in engagements.offers]
    for service, offer in zip(services, engagements.offers):
        assert service["@type"] == "Service"
        assert service["provider"]["name"] == build.AUTHOR
        spec = service["offers"]["priceSpecification"]
        assert spec["priceCurrency"] == "USD"
        assert spec["unitText"] == offer.unit
        # Projects and months are quoted "from"; hours and days are flat rates.
        assert spec["minPrice" if offer.unit in ("project", "month") else "price"] == offer.amount, offer.name


def test_employer_is_named_once_and_only_on_the_proof_page(site):
    root, pages = site
    hits = {}
    for path in root.rglob("*.html"):
        count = employer_mentions(path.read_text(encoding="utf-8"))
        if count:
            hits[path.relative_to(root).as_posix()] = count
    assert hits == {"proof/index.html": 1}
    assert employer_mentions(main_text(read(root, build.find(pages, "proof")))) == 1


def test_commercial_pages_avoid_banned_words_and_spanish(site):
    root, pages = site
    for page in commercial(pages):
        page_html = read(root, page)
        title = re.search(r"<title>(.*?)</title>", page_html).group(1)
        text = " ".join((main_text(page_html), html.unescape(title), page.description))
        assert not BANNED.search(text), (page.slug, BANNED.search(text).group(0))
        assert not SPANISH.search(text), (page.slug, SPANISH.search(text).group(0))


def test_every_figure_has_a_source(site):
    root, pages = site
    for page in commercial(pages):
        figures = set(NUMBER.findall(FORM_NAMES.sub(" ", main_text(read(root, page)))))
        assert not sorted(figures - FIGURES.keys()), (page.slug, sorted(figures - FIGURES.keys()))


def test_contact_subject_is_url_encoded(site):
    _, pages = site
    assert "?subject=What%27s%20breaking" in build.contact_button(build.find(pages, "contact"))


def test_removed_files_are_not_kept(tmp_path):
    stale = tmp_path / "files" / "old-plan.pdf"
    stale.parent.mkdir()
    stale.write_bytes(b"old")
    build.write_site(build.load_site(), tmp_path, tmp_path / "generated.json")
    assert not stale.exists()
    assert (tmp_path / "files" / "client-onboarding-plan.pdf").is_file()


# ---------------------------------------------------------------- front matter errors

LANDING_FRONT = {"type": "landing", "slug": "bad", "title": "Bad", "group": "floor",
                 "door": "Bad", "door_text": "A door."}


def write_page(folder: Path, name: str, **front: str) -> Path:
    keys = {"order": "1", "published": "2026-11-09", "updated": "2026-11-09",
            "description": "A test page with enough words in its description.", **front}
    path = folder / f"{name}.md"
    lines = "\n".join(f"{key}: {value}" for key, value in keys.items())
    path.write_text(f"---\n{lines}\n---\nBody.\n", encoding="utf-8")
    return path


def test_offers_need_a_known_unit():
    with pytest.raises(ValueError, match="unit"):
        build.parse_offer("Audit | 8500 | fortnight")


def test_offer_amounts_are_whole_usd():
    with pytest.raises(ValueError, match="whole number"):
        build.parse_offer("Audit | 8,500 | project")


def test_parse_errors_name_the_file(tmp_path):
    path = write_page(tmp_path, "engagements", type="page", slug="engagements", title="Engagements",
                      offer="Audit | 8500 | fortnight")
    with pytest.raises(ValueError, match="engagements.md: offer"):
        build.load_page(path)


def test_landing_pages_need_a_door(tmp_path):
    front = {key: value for key, value in LANDING_FRONT.items() if key != "door"}
    with pytest.raises(ValueError, match="missing door$"):
        build.load_page(write_page(tmp_path, "bad", **front))


def test_landing_pages_need_a_known_group(tmp_path):
    with pytest.raises(ValueError, match="unknown group"):
        build.load_page(write_page(tmp_path, "bad", **{**LANDING_FRONT, "group": "sky"}))


def test_home_needs_a_headline(tmp_path):
    with pytest.raises(ValueError, match="missing headline"):
        build.load_page(write_page(tmp_path, "index", type="home", slug="index", title="Home", lede="Lede."))


def test_reserved_slugs_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="reserved"):
        build.load_page(write_page(tmp_path, "files", **{**LANDING_FRONT, "slug": "files"}))


def test_links_must_point_to_an_existing_page(tmp_path):
    write_page(tmp_path, "index", type="home", slug="index", title="Home", headline="Headline.",
               lede="Lede.", secondary="See it | missing-page")
    with pytest.raises(ValueError, match="unknown page"):
        build.load_site(tmp_path)
