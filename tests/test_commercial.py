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
DOORS_PER_GROUP = {"situation": 3, "floor": 3, "buyer": 2}
# Situation pages carry one more section: the first question of each of the three people who will read it.
ROLE_SECTION = "What each of you will ask first"
ROLES_ASKING = ("Finance", "Operations", "The chief executive")
# The engagements page says who to hire for what: a large firm, an auditor, an integrator, or one operator.
WHO_TO_HIRE = ("Who", "Hire them when", "What they leave")
# The site speaks as one person ("I"), not as a firm ("we"): the owner's decision of 2026-11-12.
COMPANY_VOICE = re.compile(
    r"\b(?:our (?:team|firm|company|clients|consultants|experts|people|services)"
    r"|we (?:are|help|deliver|offer|provide|work with|believe|speciali[sz]e))\b",
    re.I,
)
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
    "2M": "about USD 2M a year of savings identified (HECHOS, Trayectoria 2013-2014)",
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
        expected = [*LANDING_SECTIONS, ROLE_SECTION] if page.group == "situation" else list(LANDING_SECTIONS)
        assert headings == expected, page.slug
        assert '<p class="scene">' in text, page.slug


def test_situation_pages_answer_each_role(site):
    root, pages = site
    for page in landings(pages, "situation"):
        section = read(root, page).split(f"{ROLE_SECTION}</h2>", 1)[1]
        asked = re.findall(r"<p><strong>([^:<]+):", section)
        assert sorted(asked) == sorted(ROLES_ASKING), page.slug


def test_home_opens_with_situations_not_job_titles(site):
    """The first choice is what is happening, not who you are (audience doors come second)."""
    root, pages = site
    text = read(root, build.find(pages, "index"))
    assert text.index('id="situations"') < text.index('id="method"') < text.index('id="industries"')
    first = text.split('id="situations"', 1)[1].split("</section>", 1)[0]
    labels = [html.unescape(label) for label in re.findall(r'<span class="door-t">(.*?)</span>', first)]
    assert len(labels) == DOORS_PER_GROUP["situation"]
    assert not [label for label in labels if label.startswith("I ")], labels


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


def test_commercial_pages_speak_as_one_person(site):
    root, pages = site
    for page in commercial(pages):
        text = main_text(read(root, page))
        assert not COMPANY_VOICE.search(text), (page.slug, COMPANY_VOICE.search(text).group(0))
        assert re.search(r"\bI\b", text), page.slug


def test_engagements_says_who_to_hire_for_what(site):
    root, pages = site
    text = read(root, build.find(pages, "engagements"))
    table = re.search(r"<table[^>]*>(.*?)</table>", text, re.S)
    assert table, "the comparison table is missing"
    headers = [html.unescape(header) for header in re.findall(r"<th[^>]*>(.*?)</th>", table.group(1))]
    assert headers == list(WHO_TO_HIRE)
    rows = re.findall(r"<tr>\s*<td[^>]*>(.*?)</td>", table.group(1), re.S)
    assert len(rows) == 4 and rows[-1].strip() == "Me", rows
    labels = set(re.findall(r'data-label="([^"]+)"', table.group(1)))
    assert labels == set(WHO_TO_HIRE[1:])  # each cell carries its column name for the stacked phone layout
    assert text.index("<table") < text.index("Best fit</h2>")


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


# ---------------------------------------------------------------- the plates of the method section

SCENE_FIGURE = re.compile(r'<figure class="scene">.*?</figure>', re.S)


def home_with_plates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, count: int) -> tuple[Path, str]:
    """Builds the site as if `count` plates, in both sizes, were in src/files/plates/."""
    files = tmp_path / "files-src"
    (files / "plates").mkdir(parents=True)
    for number in range(1, count + 1):
        for small in (False, True):
            (files / "plates" / build.plate_name(number, small)).write_bytes(b"RIFF")
    monkeypatch.setattr(build, "FILES_DIR", files)
    root = tmp_path / "out"
    build.write_site(build.load_site(), root, root / "generated.json")
    return root, (root / "index.html").read_text(encoding="utf-8")


def test_home_keeps_the_method_strip_until_every_plate_exists(tmp_path, monkeypatch):
    _, text = home_with_plates(tmp_path, monkeypatch, count=len(build.SCENES) - 1)
    assert '<ol class="steps">' in text
    assert 'class="scene"' not in text


def test_home_shows_the_four_scenes_once_the_plates_exist(tmp_path, monkeypatch):
    root, text = home_with_plates(tmp_path, monkeypatch, count=len(build.SCENES))
    figures = SCENE_FIGURE.findall(text)
    assert len(figures) == len(build.SCENES) == 4
    assert '<ol class="steps">' not in text
    assert text.count('id="method"') == 1
    width, height = build.PLATE_SIZE
    for number, figure in enumerate(figures, 1):
        assert f'src="files/plates/scene-{number}.webp"' in figure, number
        assert f'files/plates/scene-{number}-800.webp 800w' in figure, number
        assert f'width="{width}" height="{height}"' in figure, number
        assert re.search(r'alt="[^"]{40,}"', figure), number
        assert (root / "files" / "plates" / f"scene-{number}.webp").is_file(), number
    visible = main_text(text)
    assert not BANNED.search(visible)
    assert not SPANISH.search(visible)
    assert not COMPANY_VOICE.search(visible)
    assert not set(NUMBER.findall(FORM_NAMES.sub(" ", visible))) - FIGURES.keys()


# ---------------------------------------------------------------- the kit

KIT_FIGURE = re.compile(r'<li><a class="fig" href="([^"]+)">(.*?)</a></li>', re.S)
KIT_PICTURE = re.compile(r'src="files/kit/([a-z-]+)\.webp"')
KIT_MAKERS = re.compile(r"\b(?:Stanley|FatMax|Insta360|DJI|Ironclad)\b", re.I)  # who made the real objects


def home_with_kit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, keys: list[str]) -> tuple[Path, str]:
    """Builds the site as if the pictures of these figures, in both sizes, were in src/files/kit/."""
    files = tmp_path / "files-src"
    (files / "kit").mkdir(parents=True)
    for key in keys:
        for small in (False, True):
            (files / "kit" / build.figure_name(key, small)).write_bytes(b"RIFF")
    monkeypatch.setattr(build, "FILES_DIR", files)
    root = tmp_path / "out"
    build.write_site(build.load_site(), root, root / "generated.json")
    return root, (root / "index.html").read_text(encoding="utf-8")


def kit_keys() -> list[str]:
    return [figure.key for figure in build.KIT]


def test_home_has_no_kit_until_two_figures_exist(tmp_path, monkeypatch):
    _, text = home_with_kit(tmp_path, monkeypatch, kit_keys()[:build.KIT_MIN - 1])
    assert 'id="kit"' not in text


def test_a_figure_needs_its_picture_in_both_sizes(tmp_path, monkeypatch):
    key = kit_keys()[0]
    (tmp_path / "kit").mkdir()
    (tmp_path / "kit" / build.figure_name(key)).write_bytes(b"RIFF")
    monkeypatch.setattr(build, "FILES_DIR", tmp_path)
    assert build.kit_ready() == []
    (tmp_path / "kit" / build.figure_name(key, small=True)).write_bytes(b"RIFF")
    assert [figure.key for figure in build.kit_ready()] == [key]


def test_home_shows_the_figures_that_exist_in_the_order_of_the_plate(tmp_path, monkeypatch):
    keys = kit_keys()
    root, text = home_with_kit(tmp_path, monkeypatch, [keys[2], keys[0]])  # written out of order, and not all
    figures = KIT_FIGURE.findall(text)
    assert [KIT_PICTURE.search(body).group(1) for _, body in figures] == [keys[0], keys[2]]
    assert text.count('id="kit"') == 1
    assert text.index('id="method"') < text.index('id="kit"') < text.index('class="home-body"')
    for _, body in figures:
        key = KIT_PICTURE.search(body).group(1)
        assert f'files/kit/{key}-{build.KIT_SMALL}.webp {build.KIT_SMALL}w' in body, key
        assert f'width="{build.KIT_SIZE}" height="{build.KIT_SIZE}"' in body, key
        assert 'alt=""' in body and 'loading="lazy"' in body, key  # the name beside the picture says what it is
        assert (root / "files" / "kit" / f"{key}.webp").is_file(), key


def test_every_figure_of_the_kit_opens_a_page_of_its_own(tmp_path, monkeypatch):
    keys = kit_keys()
    assert len(set(keys)) == len(keys) >= build.KIT_MIN
    assert all(re.fullmatch(r"[a-z]+(?:-[a-z]+)*", key) for key in keys)  # a key is also a file name
    root, text = home_with_kit(tmp_path, monkeypatch, keys)
    figures = KIT_FIGURE.findall(text)
    assert len(figures) == len(build.KIT)
    assert len({door for door, _ in figures}) == len(figures)  # no two figures open the same page
    for (door, body), figure in zip(figures, build.KIT):
        assert door == f"{figure.slug}/"
        assert (root / door / "index.html").is_file(), door
        assert f'<span class="fig-t">{build.esc(figure.name)}</span>' in body, figure.key
        assert f'<span class="fig-d">{build.esc(figure.line)}</span>' in body, figure.key
        assert ('class="fig-r"' in body) == bool(figure.rule), figure.key
        assert not figure.rule or f'<span class="fig-r">{build.esc(figure.rule)}</span>' in body, figure.key


def test_the_kit_follows_the_rules_of_the_commercial_pages(tmp_path, monkeypatch):
    _, text = home_with_kit(tmp_path, monkeypatch, kit_keys())
    visible = main_text(text)
    assert not BANNED.search(visible)
    assert not SPANISH.search(visible)
    assert not COMPANY_VOICE.search(visible)
    assert not KIT_MAKERS.search(text)  # no maker is named: not in the text, not in a file name
    # "Fig. 1" is written by the style sheet, so the page prints no figure that lacks a source
    assert not set(NUMBER.findall(FORM_NAMES.sub(" ", visible))) - FIGURES.keys()


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
