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
FORM_NAMES = re.compile(r"\b(?:B-1|W-8BEN(?:-E)?|10-K)\b")  # names with a digit in them, not figures
JSONLD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
CONTACT_BUTTON = re.compile(r'<a class="btn btn-contact" href="([^"]+)"')

# Every figure a commercial page may print, and where it comes from. A new number fails the test
# until it is added here with its source. HECHOS = cv dossier/HECHOS.md; plan = the approved site plan.
FIGURES = {
    "02:30": "the night shift, a time of day used as a scene, not a measurement",
    "12": "best fit: a system change in the last or next 12 months (plan C); 12 months of the returning-client "
          "rate (owner decision 2026-11-13, content plan §3 A)",
    "14": "14 November 2026, date of the engine count (HECHOS, kern)",
    "15": "15 planners (HECHOS, Trayectoria 2016-2017); 15 to 20 hours a week (plan B5)",
    "20": "team of 20 (HECHOS, AGCO row); 15 to 20 hours a week; 20 October 2026 (HECHOS, fdekit)",
    "20%": "order processing time down about 20%, by his estimate (HECHOS, AGCO row; book l.6921); returning "
           "clients pay 20% less (owner decision 2026-11-13, content plan §3 A)",
    "23": "23 operators trained on RF (HECHOS, AGCO row)",
    "25": "25 October 2026, date of the receiving-kit count (HECHOS, mellon)",
    "30": "30-60-90-day plan; measures that hold 30 days after go-live (plan B5)",
    "30%": "30% at the start and 30% after 30 days (plan B5)",
    "31": "31 integration tests on an embedded PostgreSQL in the weightlifting app (HECHOS, Holy Oly)",
    "40%": "40% at go-live (plan B5)",
    "50%": "50% at the start and 50% on delivery (plan B5); fewer than 50% of tau-bench tasks solved "
           "(Yao et al. 2024, abstract)",
    "57%": "Olist triage, published page not-received-but-delivered",
    "60": "30-60-90-day plan; 60-minute sessions (plan B5)",
    "65%": "DeHoratius and Raman 2008, published page why-inventory-records-do-not-match-the-shelf",
    "90": "the 90-day check, included after every audit and go-live (owner decision 2026-11-13, content plan "
          "§3 B); visa stays of up to 90 days; 30-60-90-day plan",
    "95%": "MIT NANDA 2025, The GenAI Divide (book appendix EV-MIT-01, industry report); at least 95% glue "
           "code (Sculley et al. 2015, NeurIPS, verified in the paper 2026-11-13)",
    "100": "about 100 people (HECHOS, Trayectoria 2018-2020)",
    "200": "more than 200 stores (HECHOS, Trayectoria 2016-2017)",
    "250": "advisory fee in USD per hour (plan C, option A)",
    "370,000": "DeHoratius and Raman 2008, published page why-inventory-records-do-not-match-the-shelf",
    "600": "Australian Visitor visa, subclass 600 (Home Affairs)",
    "1,079": "receiving-kit test count (HECHOS, mellon)",
    "1,187": "field-kit passing tests (HECHOS, fdekit)",
    "1,200": "on-site day fee in USD (plan C, option A)",
    "1,332": "about 1,332 unit test cases in the weightlifting app (HECHOS, Holy Oly)",
    "2013": "start of the first planning role, June 2013 (HECHOS, Trayectoria)",
    "2016": "end of the analyst role, February 2016, and start of the retail planning role, March 2016 "
            "(HECHOS, Trayectoria)",
    "2017": "end of the retail planning role, December 2017 (HECHOS, Trayectoria)",
    "2020": "end of the three-site role, April 2020, and start of the e-commerce role, May 2020 "
            "(HECHOS, Trayectoria)",
    "2022": "start of the Melbourne role, August 2022, and end of the e-commerce role, July 2022 "
            "(HECHOS, Trayectoria)",
    "2024": "end of the Melbourne role (HECHOS, AGCO row); year of tau-bench (Yao et al., arXiv 2406.12045)",
    "2015": "year of Sculley et al., Hidden Technical Debt in Machine Learning Systems (NeurIPS)",
    "2018": "year of the ERP launch (Revlon, Inc., Form 10-K for 2018, verified 2026-11-13); start of the "
            "three-site logistics role, January 2018 (HECHOS, Trayectoria)",
    "2025": "year of the MIT NANDA report",
    "2026": "year of the test counts (HECHOS, Sistemas construidos)",
    "6,000": "fractional lead fee in USD per month (plan C, option A)",
    "8,500": "field audit fee in USD (plan C, option A)",
    "9,966": "engine test count, CLM_TESTS_KERN_ACTUAL: collected at commit 7757fb1 on 14 November 2026 "
             "(HECHOS, kern)",
    "15,000": "cutover leadership fee in USD (plan C, option A)",
    "50,000": "50,000-SKU distribution centre (HECHOS, AGCO row)",
    "2M": "about USD 2M a year of savings identified (HECHOS, Trayectoria 2013-2014)",
    "64": "about USD 64 million of net sales not shipped after an ERP launch (Revlon 10-K for 2018)",
    "64M": "the same USD 64 million, on the home page (Revlon 10-K for 2018)",
    "53.6": "USD 53.6 million of incremental charges in 2018 (Revlon 10-K for 2018)",
    "5%": "at most 5% model code in a mature ML system (Sculley et al. 2015, NeurIPS)",
    "73": "claims at flagged sellers (Which Record Lies?, README results table, Olist)",
    "1,093": "claims with no clear cause (Which Record Lies?, README results table, Olist)",
    "1,542": "late orders: claims written on or before the delivery day (Which Record Lies?, Olist)",
    "2,708": "\"not received\" claims on delivered orders (Which Record Lies?, Olist)",
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
    assert "?subject=What%20we%27re%20seeing" in build.contact_button(build.find(pages, "contact"))


ASKS_FOR_THE_DIAGNOSIS = re.compile(r"\b(?:breaking|broken|wrong|failing|problem|root cause)\b", re.I)


def test_no_contact_button_asks_the_reader_for_the_diagnosis(site):
    """The reader reports what they see. Naming what is broken is the work, so no button asks for it."""
    root, pages = site
    label = re.compile(r'<a class="btn btn-contact" href="[^"]+">(.*?)</a>', re.S)
    assert not ASKS_FOR_THE_DIAGNOSIS.search(build.DEFAULT_CTA)
    seen = 0
    for path in root.rglob("*.html"):
        for text in label.findall(path.read_text(encoding="utf-8")):
            seen += 1
            assert not ASKS_FOR_THE_DIAGNOSIS.search(html.unescape(text)), (path.name, text)
    assert seen, "no contact button was found on the built site"


def test_home_says_the_cause_sits_outside_the_department_that_shows_it(site):
    """The line under the headline reads the operation as one chain, not department by department."""
    _, pages = site
    lede = build.find(pages, "index").lede or ""
    assert "one department" in lede and "whole chain" in lede


def test_removed_files_are_not_kept(tmp_path):
    stale = tmp_path / "files" / "old-plan.pdf"
    stale.parent.mkdir()
    stale.write_bytes(b"old")
    build.write_site(build.load_site(), tmp_path, tmp_path / "generated.json")
    assert not stale.exists()
    assert (tmp_path / "files" / "client-onboarding-plan.pdf").is_file()


# ---------------------------------------------------------------- the plates of the method section

# ---------------------------------------------------------------- the home page, from top to bottom

HOME_FIGURE = re.compile(r'<a class="fig[^"]*" href="([^"]+)">\s*<span class="fig-g">(.*?)</span>\s*'
                         r'<span class="fig-n">(.*?)</span>\s*<span class="fig-t">(.*?)</span>.*?'
                         r'<span class="fig-go">(.*?)</span>', re.S)
KIT_TILE = re.compile(r'<li><a class="tile" href="([^"]+)">(.*?)</a></li>', re.S)
MAKERS = re.compile(r"\b(?:Stanley|FatMax|Insta360|DJI|Ironclad)\b", re.I)  # who made the real objects
SCRIPT = re.compile(r'<script(?! type="application/ld\+json")')
HERO_WORDS = 20  # the line under the headline is read in one breath


def section_of(text: str, anchor: str) -> str:
    """The markup of the section that carries this id, up to where it closes."""
    return text.split(f'id="{anchor}"', 1)[1].split("</section>", 1)[0]


def desk_keys() -> list[str]:
    return [item.key for item in build.DESK]


def test_the_hero_fits_a_first_screen(site):
    """One headline, a short line under it, the contact button and one more link. Nothing else."""
    root, pages = site
    home = build.find(pages, "index")
    hero = section_of(read(root, home), "hero")
    assert hero.count("<h1") == 1
    lede = re.sub(r"<[^>]+>", " ", re.search(r'<p class="lede">(.*?)</p>', hero, re.S).group(1))
    assert 0 < len(lede.split()) <= HERO_WORDS, lede
    assert len(CONTACT_BUTTON.findall(hero)) == 1
    assert hero.count('class="btn btn-ghost"') == 1
    assert home.base_line and home.base_line[:24] not in html.unescape(hero)   # where I work goes at the foot


def test_home_names_the_symptoms_before_asking_which_one(site):
    root, pages = site
    home = build.find(pages, "index")
    block = section_of(read(root, home), "situations")
    statement = block.split('<p class="statement">', 1)[1].split("</p>", 1)[0]
    lines = [html.unescape(line) for line in re.findall(r"<span>(.*?)</span>", statement)]
    assert lines == list(home.symptoms) and len(lines) == 3
    assert all(line.endswith(".") for line in lines)
    assert block.index('class="statement"') < block.index('class="doors-q"')


def test_home_shows_four_figures_each_with_its_source_and_page(site):
    root, pages = site
    figures = HOME_FIGURE.findall(section_of(read(root, build.find(pages, "index")), "proof"))
    assert [number for _, _, number, _, _ in figures] == [figure.number for figure in build.HOME_FIGURES]
    assert len(figures) == 4
    assert [grade for _, grade, _, _, _ in figures] == list(build.FIGURE_GRADES)   # one of each, in order
    for link, grade, number, caption, label in figures:
        assert set(NUMBER.findall(number)) <= FIGURES.keys(), number
        assert (root / link / "index.html").is_file(), link
        assert caption.strip() and label.strip(), number


def test_a_public_dataset_is_not_called_my_data(site):
    """The 57% is read from a public marketplace dataset: the analysis is mine, the data is not, and the
    page says which of the two it is."""
    root, pages = site
    borrowed = [figure for figure in build.HOME_FIGURES if "public" in figure.caption]
    assert borrowed
    for figure in borrowed:
        assert "data" not in figure.grade.lower(), figure.grade
    section = html.unescape(section_of(read(root, build.find(pages, "index")), "proof")).lower()
    assert "my data" not in section and "my own data" not in section


def test_the_method_is_three_steps_that_need_no_picture(site):
    root, pages = site
    method = section_of(read(root, build.find(pages, "index")), "method")
    steps = re.findall(r"<h3>(.*?)</h3>\s*<p>(.*?)</p>", method, re.S)
    assert steps == [(build.esc(title), build.esc(text)) for title, text in build.METHOD_STEPS]
    assert len(steps) == 3
    assert "<svg" not in method and "<img" not in method


def test_short_answers_open_in_place(site):
    root, pages = site
    text = read(root, build.find(pages, "index"))
    library = text.split('<section id="library">', 1)[1].split("</section>", 1)[0]
    questions = [page for page in pages if page.kind == "question"]
    assert library.count("<details>") == len(questions) > 0
    for page in questions:
        assert f'href="{page.slug}/"' in library, page.slug
    for note in (page for page in pages if page.kind == "note"):
        assert f'href="{note.slug}/"' in library, note.slug


def test_home_ends_on_the_same_call_as_it_opens(site):
    root, pages = site
    home = build.find(pages, "index")
    text = read(root, home)
    closing = section_of(text, "contact")
    address = CONTACT_BUTTON.findall(text)[0]
    assert f'href="{address}"' in closing                        # the same address and subject
    assert build.esc(home.cta or build.DEFAULT_CTA) in closing   # and the same words
    assert home.base_line[:24] in html.unescape(closing)


def test_home_has_its_own_style_sheet_and_no_other_page_does(site):
    root, pages = site
    for page in pages:
        assert ('href="home.css"' in read(root, page)) == page.is_home, page.slug
    css = (root / "home.css").read_text(encoding="utf-8")
    assert "prefers-color-scheme" not in css      # dark only, like the rest of the site
    assert "prefers-reduced-motion" in css        # what moves stops for whoever asks


def test_fonts_are_served_by_the_site_itself(site):
    root, pages = site
    for page in pages:
        text = read(root, page)
        assert "fonts.googleapis.com" not in text and "fonts.gstatic.com" not in text, page.slug
    css = (root / "style.css").read_text(encoding="utf-8")
    assert len(build.FONT_FILES) == 2
    for name in build.FONT_FILES:
        assert (root / "files" / "fonts" / name).is_file(), name
        assert f'url("files/fonts/{name}")' in css, name
    assert css.count("font-display: swap") == len(build.FONT_FILES)


def test_no_page_runs_a_script(site):
    root, pages = site
    for page in pages:
        assert not SCRIPT.search(read(root, page)), page.slug


UNSTYLED = ("landing", "page")  # they name the kind of article; nothing is drawn differently for them yet


def test_every_class_a_page_carries_has_a_rule(site):
    """The markup and the two style sheets are written apart: a class one of them forgot shows up here."""
    root, pages = site
    css = (root / "style.css").read_text(encoding="utf-8") + (root / "home.css").read_text(encoding="utf-8")
    for page in pages:
        tokens = {token for value in re.findall(r'class="([^"]+)"', read(root, page)) for token in value.split()}
        orphans = sorted(token for token in tokens
                         if not token.startswith("kind-") and token not in UNSTYLED
                         and not re.search(rf"\.{re.escape(token)}(?![\w-])", css))
        assert not orphans, (page.slug, orphans)


# ---------------------------------------------------------------- the desk

def home_with_desk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: tuple[str, ...] = ()) -> tuple[Path, str]:
    """Builds the site as if desk.py had written the files of the desk in src/files/desk/, but for `missing`."""
    files = tmp_path / "files-src"
    (files / "desk").mkdir(parents=True)
    for name in build.desk_files():
        if name not in missing:
            (files / "desk" / name).write_bytes(b"RIFF")
    monkeypatch.setattr(build, "FILES_DIR", files)
    root = tmp_path / "out"
    build.write_site(build.load_site(), root, root / "generated.json")
    return root, (root / "index.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("missing", ["desk.webp", "desk-800.webp", "kit-tape.webp", "yard.webp"])
def test_home_shows_no_picture_of_the_desk_until_every_file_exists(tmp_path, monkeypatch, missing):
    assert missing in build.desk_files()
    _, text = home_with_desk(tmp_path, monkeypatch, missing=(missing,))
    assert 'class="hero-figure"' not in text
    assert 'id="kit"' not in text
    assert "files/desk/" not in text
    assert "has-desk" not in text
    assert len(CONTACT_BUTTON.findall(text)) == 1   # the page still stands without it


def test_the_desk_stands_beside_the_headline(tmp_path, monkeypatch):
    root, text = home_with_desk(tmp_path, monkeypatch)
    assert text.index("<h1") < text.index('class="hero-figure"') < text.index('id="situations"')
    figure = text.split('class="hero-figure"', 1)[1].split("</figure>", 1)[0]
    width, height = build.DESK_SIZE
    picture = re.search(r'<img src="files/desk/desk\.webp"[^>]*>', figure).group(0)
    assert f'files/desk/desk-{build.DESK_SMALL}.webp {build.DESK_SMALL}w' in picture
    assert f'width="{width}" height="{height}"' in picture
    assert re.search(r'alt="[^"]{60,}"', picture)   # the picture is described for whoever cannot see it
    assert 'loading="lazy"' not in picture           # it is in the first screen
    assert "<figcaption>Illustration</figcaption>" in figure   # it is not a photograph, and the page says so
    assert (root / "files" / "desk" / "desk.webp").is_file()
    assert 'class="kind-home has-desk"' in text


def test_every_object_on_the_desk_has_a_tile_that_leads_to_its_page(tmp_path, monkeypatch):
    root, text = home_with_desk(tmp_path, monkeypatch)
    tiles = KIT_TILE.findall(section_of(text, "kit"))
    assert [link for link, _ in tiles] == [f"{item.slug}/" for item in build.DESK]
    assert len(set(desk_keys())) == len(desk_keys()) == 9
    width, height = build.TILE_SIZE
    for (link, body), item in zip(tiles, build.DESK):
        key = item.key
        assert re.fullmatch(r"[a-z]+(?:-[a-z]+)*", key)   # a key is also part of a file name
        assert f'<img src="files/desk/{build.tile_name(key)}" width="{width}" height="{height}" alt=""' in body, key
        assert 'loading="lazy"' in body, key
        assert f"<h3>{build.esc(item.name)}</h3>" in body, key
        assert f"<p>{build.esc(item.text)}</p>" in body, key
        assert ('class="tile-limit"' in body) == bool(item.rule), key
        assert not item.rule or f'<p class="tile-limit">{build.esc(item.rule)}</p>' in body, key
        assert (root / link / "index.html").is_file(), link
        assert (root / "files" / "desk" / build.tile_name(key)).is_file(), key


def test_the_desk_follows_the_rules_of_the_commercial_pages(tmp_path, monkeypatch):
    _, text = home_with_desk(tmp_path, monkeypatch)
    visible = main_text(text)
    assert not BANNED.search(visible)
    assert not SPANISH.search(visible)
    assert not COMPANY_VOICE.search(visible)
    assert not MAKERS.search(text)   # no maker is named: not in the text, not in a file name
    assert not set(NUMBER.findall(FORM_NAMES.sub(" ", visible))) - FIGURES.keys()
    assert not SCRIPT.search(text)
    assert len(CONTACT_BUTTON.findall(text)) == 1


def write_marks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, marks: dict) -> Path:
    path = tmp_path / "desk.json"
    path.write_text(json.dumps(marks), encoding="utf-8")
    monkeypatch.setattr(build, "DESK_SPOTS", path)
    return path


def test_an_object_left_unmarked_is_an_error(tmp_path, monkeypatch):
    first, second, *rest = desk_keys()
    write_marks(tmp_path, monkeypatch, {"spots": {key: [5, 40, 8, 20] for key in rest}})
    with pytest.raises(ValueError, match=rf"desk\.json: no mark for {first}, {second}$"):
        build.desk_spots()


def test_a_mark_for_an_unknown_object_is_an_error(tmp_path, monkeypatch):
    spots = {key: [5, 40, 8, 20] for key in desk_keys()} | {"hammer": [5, 5, 5, 5]}
    write_marks(tmp_path, monkeypatch, {"spots": spots})
    with pytest.raises(ValueError, match="unknown object 'hammer'"):
        build.desk_spots()


def test_no_marks_file_means_no_marks(tmp_path):
    assert build.load_spots(tmp_path / "desk.json") == {}
    assert build.load_details(tmp_path / "desk.json") == {}


def test_details_are_marked_like_objects(tmp_path, monkeypatch):
    spots = {key: [5, 40, 8, 20] for key in desk_keys()}
    path = write_marks(tmp_path, monkeypatch, {"spots": spots, "details": {"yard": [70, 30, 20, 25]}})
    assert build.load_details(path) == {"yard": (70, 30, 20, 25)}
    assert build.load_spots(path).keys() == set(desk_keys())
    path.write_text(json.dumps({"spots": spots, "details": {"window": [1, 1, 5, 5]}}), encoding="utf-8")
    with pytest.raises(ValueError, match=r"desk\.json: unknown detail 'window'"):
        build.load_details(path)
    path.write_text(json.dumps({"spots": spots, "details": {"yard": [90, 1, 20, 5]}}), encoding="utf-8")
    with pytest.raises(ValueError, match=r"desk\.json: yard lies outside the picture"):
        build.load_details(path)


@pytest.mark.parametrize("content, fault", [
    ("{not json", "is not valid JSON"),
    ('{"marks": {}}', 'needs a "spots" object'),
    ('{"spots": []}', 'needs a "spots" object'),
    ('{"spots": {"tape": 5}}', "tape needs four numbers: left, top, width and height"),
    ('{"spots": {"tape": [1, 2, 3]}}', "tape needs four numbers: left, top, width and height"),
    ('{"spots": {"tape": [1, 2, "3", 4]}}', "tape needs four numbers: left, top, width and height"),
    ('{"spots": {"tape": [true, 2, 3, 4]}}', "tape needs four numbers: left, top, width and height"),
    ('{"spots": {"tape": [NaN, 2, 3, 4]}}', "tape needs four numbers: left, top, width and height"),
    ('{"spots": {"tape": [10, 20, 0, 5]}}', "tape has no width or no height"),
    ('{"spots": {"tape": [10, 20, 5, -5]}}', "tape has no width or no height"),
    ('{"spots": {"tape": [96, 20, 5, 5]}}', "tape lies outside the picture"),
    ('{"spots": {"tape": [10, 90, 5, 20]}}', "tape lies outside the picture"),
    ('{"spots": {"tape": [-1, 20, 5, 5]}}', "tape lies outside the picture"),
])
def test_marks_that_cannot_be_used_name_the_file_and_the_fault(tmp_path, content, fault):
    path = tmp_path / "desk.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape(f"desk.json: {fault}")):
        build.load_spots(path)


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


# ---------------------------------------------------------------- the content of 2026-11-13
# The owner's decisions of 2026-11-13: show the deployment work, take more from the manuscript, and
# promise a 90-day check and a returning-client rate (content plan, C:/tolkien/docs/designs/).
DEPLOYMENT_STEPS = ("Discover on the floor.", "Tune.", "Orchestrate.", "Value case.", "Let go.")
SOURCE_LINE = re.compile(r'<p class="src">(.*?)</p>', re.S)


def test_the_home_bar_draws_the_published_triage(site):
    root, pages = site
    figures = section_of(read(root, build.find(pages, "index")), "proof")
    counts = [count for _, _, count in build.CLAIMS_TRIAGE]
    assert sum(counts) == 2708 and round(100 * counts[0] / sum(counts)) == 57   # the 57% it sits under
    assert figures.count("<rect ") == len(counts)
    for _, words, count in build.CLAIMS_TRIAGE:
        assert f"{count:,} {words}" in figures, words
    assert 'role="img"' in figures and "2,708 claims" in figures
    assert "How a deployment runs" in section_of(read(root, build.find(pages, "index")), "method")


def test_engagements_promise_what_happens_after_the_work(site):
    root, pages = site
    engagements = main_text(read(root, build.find(pages, "engagements")))
    assert "After the work" in engagements
    assert "The 90-day check is included." in engagements
    assert "putting it back is on me" in engagements
    assert "For 12 months after an engagement ends, advisory hours and on-site days cost 20% less." in engagements
    terms = main_text(read(root, build.find(pages, "working-terms")))
    assert "After the work." in terms and "This assumes the three things I ask for above" in terms


def test_the_vendors_page_runs_a_deployment_in_five_steps(site):
    root, pages = site
    text = read(root, build.find(pages, "for-technology-vendors"))
    start = text.split('id="how-we-would-start"', 1)[1].split("<h2", 1)[0]
    steps = re.findall(r"<li><strong>(.*?)</strong>", start)
    assert steps == list(DEPLOYMENT_STEPS)
    assert start.count("<em>Out:") == len(DEPLOYMENT_STEPS)
    assert "data contract" in start and "files/client-onboarding-plan.pdf" in start


def test_the_hiring_door_and_the_engineering_handoff(site):
    root, pages = site
    author = read(root, build.find(pages, "marcos-stipicich"))
    assert "If you are hiring</h2>" in author and "for-technology-vendors/#how-we-would-start" in author
    assert "data contract" in main_text(read(root, build.find(pages, "how-i-work")))


def test_the_proof_page_draws_the_rule_as_a_flow(site):
    root, pages = site
    flow = read(root, build.find(pages, "proof")).split('<ol class="flow">', 1)[1].split("</ol>", 1)[0]
    assert flow.count("<li>") == 4
    assert '<span class="flow-stop">If a number fails, nothing is written' in flow


def test_figures_from_the_manuscript_name_their_source(site):
    root, pages = site
    golive = read(root, build.find(pages, "a-new-system-goes-live"))
    assert "USD 64 million" in golive and "USD 53.6 million" in golive
    assert "sec.gov/Archives/edgar/data/887921/" in SOURCE_LINE.search(golive).group(1)
    assert "Revlon" not in golive.split('<p class="src">', 1)[0]   # the company is named in the source only
    vendors = SOURCE_LINE.search(read(root, build.find(pages, "for-technology-vendors"))).group(1)
    assert "arxiv.org/abs/2406.12045" in vendors and "papers.nips.cc" in vendors
    for slug in ("a-new-system-goes-live", "proof", "marcos-stipicich"):
        assert "about 20%" in main_text(read(root, build.find(pages, slug))), slug   # as the manuscript states it


# ---------------------------------------------------------------- the look, as rules the build keeps
# From the polish of 2026-11-14 (Hallmark, sloplint): what the linter named on the home page and the two
# style sheets, kept here so that a later edit cannot bring it back unnoticed.

STYLE_SHEETS = ("style.css", "home.css")
CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
TOKEN_BLOCK = re.compile(r":root\s*\{[^{}]*\}")
DECLARATIONS = re.compile(r"\{([^{}]*)\}")
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")   # a selector list and its declarations, inside @media or not
COLOUR_LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgb|hsl|hwb|lab|lch|oklab|oklch)a?\(")
LETTER_SPACING = re.compile(r"letter-spacing:\s*([^;}]+)")
CSS_URL = re.compile(r"""url\(\s*["']?([^"')\s]+)""")
MAIL_LINK = re.compile(r'href="mailto:([^"?]+)')
LINK_LABEL = re.compile(r"<a\b[^>]*>(.*?)</a>", re.S)
ARROWS = frozenset("→↗↘›»")
MAX_TRACKING = 0.03   # in em: past this a small label reads as set by a template


def style_sheets(root: Path) -> dict[str, str]:
    """The two style sheets as built, without their comments."""
    return {name: CSS_COMMENT.sub("", (root / name).read_text(encoding="utf-8")) for name in STYLE_SHEETS}


def test_every_colour_is_a_token(site):
    """A colour is written once, in :root, and used by name: nothing below the token block spells one out."""
    root, _ = site
    for name, css in style_sheets(root).items():
        rules = TOKEN_BLOCK.sub("", css)
        for block in DECLARATIONS.findall(rules):
            literal = COLOUR_LITERAL.search(block)
            assert not literal, (name, literal.group(0), block.strip()[:80])
    assert TOKEN_BLOCK.search(style_sheets(root)["style.css"])


def test_no_label_is_set_in_tracked_capitals(site):
    """Labels are the body face in sentence case: no rule turns text to capitals or spreads its letters."""
    root, _ = site
    for name, css in style_sheets(root).items():
        assert "uppercase" not in css and "small-caps" not in css, name
        for value in (found.strip() for found in LETTER_SPACING.findall(css)):
            if value in ("normal", "0"):
                continue
            # Written in em, so that it can be read against the limit whatever the size of the type.
            assert re.fullmatch(r"-?\d*\.?\d+em", value), (name, value)
            assert float(value[:-2]) <= MAX_TRACKING, (name, value)


def test_the_page_clips_sideways_overflow_without_a_scroll_box(site):
    """On html and on body: clip, never hidden. Hidden makes a scroll box, and the sticky parts stop sticking."""
    root, _ = site
    set_on = {"html": "", "body": ""}
    for selector, block in RULE.findall(style_sheets(root)["style.css"]):
        for name in (part.strip() for part in selector.split(",")):
            if name in set_on:
                set_on[name] += block
    for element, declarations in set_on.items():
        assert "overflow-x: clip" in declarations, element
        assert "overflow-x: hidden" not in declarations and "overflow: hidden" not in declarations, element


def test_every_file_a_style_sheet_points_to_exists(site):
    root, _ = site
    seen = 0
    for name, css in style_sheets(root).items():
        for target in CSS_URL.findall(css):
            if target.startswith("data:"):
                continue
            seen += 1
            assert (root / target).is_file(), (name, target)
    assert seen >= len(build.FONT_FILES)


def test_every_engagement_card_reads_unless_another_is_picked(site):
    """The cards open and close with radio buttons and CSS alone. The text of a card is never hidden at
    rest: the only rule that hides it names the pick of another card, and every card has its rules."""
    root, pages = site
    page_html = read(root, build.find(pages, "engagements"))
    cards = re.findall(r'<article class="eng-card" data-card="(\d+)">', page_html)
    picks = re.findall(r'<input class="eng-pick" type="radio" name="eng-deck" id="eng-(\d+)"', page_html)
    assert cards == picks and len(cards) >= 2
    assert len(re.findall(r'<input class="eng-pick"[^>]*\schecked>', page_html)) == 1   # one card opens the page
    css = style_sheets(root)["style.css"]
    for number in cards:
        opens = f':where(#eng-{number}:checked) ~ .eng-cards .eng-card[data-card="{number}"] .eng-body'
        gives_way = f':where(#eng-{number}:checked) ~ .eng-cards .eng-card:not([data-card="{number}"]) .eng-body'
        assert opens in css, number        # narrow screens: the picked card shows its text
        assert gives_way in css, number    # wide screens: the other cards give way to it
    at_rest = [block for selector, block in RULE.findall(css)
               if ".eng-body" in (part.strip() for part in selector.split(","))]
    assert at_rest
    for block in at_rest:
        assert "opacity: 0" not in block and "visibility: hidden" not in block, block.strip()


def test_every_mail_link_goes_to_the_site_address(site):
    """One address, the one in build.py. A card written by hand in a page must not carry another."""
    root, _ = site
    seen = 0
    for path in root.rglob("*.html"):
        for address in MAIL_LINK.findall(path.read_text(encoding="utf-8")):
            seen += 1
            assert address == build.EMAIL, (path.relative_to(root).as_posix(), address)
    assert seen


def test_no_link_carries_an_arrow(site):
    """A link says where it goes in words. An arrow glued to the label adds nothing a link does not say."""
    root, pages = site
    for page in pages:
        for label in LINK_LABEL.findall(read(root, page)):
            text = html.unescape(re.sub(r"<[^>]+>", "", label))
            assert not ARROWS & set(text), (page.slug, " ".join(text.split()))


def test_the_hero_opens_with_the_headline_and_signs_with_the_role(site):
    """Nothing small announces the headline. The role is said once in the hero, under the two actions."""
    root, pages = site
    home = build.find(pages, "index")
    hero = section_of(read(root, home), "hero")
    assert 'class="kicker"' not in hero
    assert "<p" not in hero.split("<h1", 1)[0]
    role = re.search(r'<p class="hero-role">(.*?)</p>', hero, re.S)
    assert role and html.unescape(role.group(1)) == (home.kicker or build.AUTHOR_ROLE)
    assert hero.index('class="actions"') < hero.index('class="hero-role"')
    assert hero.index('class="hero-role"') < hero.index("</div>", hero.index('class="actions"'))   # in the same block


def test_no_page_says_its_headline_twice(site):
    """The small line under a headline names the section. Where it would only repeat the headline, it is left out."""
    root, pages = site
    under_headline = re.compile(r'<h1[^>]*>(.*?)</h1>\s*<p class="kicker">(.*?)</p>', re.S)
    seen = 0
    for page in pages:
        match = under_headline.search(read(root, page))
        if match:
            seen += 1
            headline, line = (html.unescape(re.sub(r"<[^>]+>", "", part)).strip().lower() for part in match.groups())
            assert line != headline, page.slug
    assert seen   # the pages that name their section still do


def test_the_home_page_prints_typographic_quotes(site):
    """Front matter is plain text and is printed as typed: an apostrophe typed straight shows straight.
    On the home page, where a door or a description is set large, every quote is a typographic one."""
    root, pages = site
    body = read(root, build.find(pages, "index")).split("<main", 1)[1].split("</main>", 1)[0]
    text = html.unescape(re.sub(r"<[^>]+>", " ", body.split(">", 1)[1]))   # after the opening tag of <main>
    straight = [" ".join(text[max(0, found.start() - 24): found.start() + 12].split())
                for found in re.finditer(r"['\"]", text)]
    assert not straight, straight


# ---------------------------------------------------------------- every page, as the linter reads it
# Plan Maestro v2.0 of 2026-11-14: what the home page already keeps, now kept on every page the build writes.

TEXT_ELEMENT = re.compile(r"<(p|li|span|a|h[1-6]|td|th|figcaption|div)\b[^>]*>(.*?)</\1>", re.S)
BLOCK_INSIDE = re.compile(r"<(?:p|div|ul|ol|li|h[1-6]|table|section|article|hgroup)\b")
DASHES = re.compile("[–—]")   # an en dash or an em dash


def visible_text(page_html: str) -> str:
    """Every word a reader can see, the head's title included; scripts and styles left out."""
    without_code = re.sub(r"<(script|style)\b.*?</\1>", " ", page_html, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", without_code))


def test_no_page_opens_its_headline_with_a_small_line(site):
    """Nothing small stands above a headline to announce it: the line that names the section goes under it."""
    root, pages = site
    for page in pages:
        text = read(root, page)
        if "<h1" in text:
            assert 'class="kicker"' not in text.split("<h1", 1)[0], page.slug


def test_no_headline_sets_part_of_itself_in_italics(site):
    root, pages = site
    for page in pages:
        for headline in re.findall(r"<h1[^>]*>(.*?)</h1>", read(root, page), re.S):
            assert not re.search(r"<(?:em|i)\b", headline), (page.slug, headline)


def test_no_line_joins_three_items_with_middle_dots(site):
    """One middle dot can join two things, a name and a date. Three things in a row of dots read as a template."""
    root, pages = site
    for page in pages:
        for _, inner in TEXT_ELEMENT.findall(read(root, page)):
            if BLOCK_INSIDE.search(inner):
                continue
            text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", inner)).split())
            assert text.count("·") < 2, (page.slug, text[:90])


def test_no_page_prints_a_dash(site):
    """A comma, a colon, a full stop or parentheses do a dash's work; a page range takes a hyphen."""
    root, pages = site
    for page in pages:
        found = DASHES.search(visible_text(read(root, page)))
        assert not found, (page.slug, visible_text(read(root, page))[max(0, found.start() - 40): found.start() + 20])


def test_disabled_controls_have_a_style(site):
    """The engagements page has radio buttons: a control that can be disabled shows it, and not by fading alone."""
    root, _ = site
    rule = re.search(r"([^{}]*:disabled[^{}]*)\{([^{}]*)\}", style_sheets(root)["style.css"])
    assert rule and "cursor: not-allowed" in rule.group(2)

