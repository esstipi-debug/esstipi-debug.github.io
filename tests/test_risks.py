"""Checks on the two evidence plates, drawn from src/risks.json.

The scope plate (engagements page) sets what a rollout role at a software vendor takes on beside my cutover
engagement. The backing plate (proof page) shows, for each risk, how far I went and how far a stranger can check
it without me. The fixture builds into a temporary folder, not the repository.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build  # noqa: E402
import risks  # noqa: E402

DATA = json.loads(risks.RISKS_FILE.read_text(encoding="utf-8"))
RISK_IDS = [risk["id"] for risk in DATA["risks"]]
PAYERS = ("Finance", "Operations", "The chief executive")   # the three readers each situation page answers
ROW = re.compile(r'<tr data-risk="([a-z]+)"[^>]*>(.*?)</tr>', re.S)
CELL_LEVEL = re.compile(r'<span class="risk-level" data-level="(\d)">')
TRACK = re.compile(r'<svg class="risk-track" data-reached="(\d)" data-checkable="(\d)"')
LEVEL_WORD = re.compile(r'<span class="risk-level-word">([^<]*)</span>')
GRADE = re.compile(r'<span class="risk-grade">([^<]*)</span>')
PAYS = re.compile(r'<span class="risk-pays">([^<]*)</span>')
COLOUR_ATTRIBUTE = re.compile(r'\s(?:fill|stroke)="(?!none")[^"]*"')


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[build.Page]]:
    root = tmp_path_factory.mktemp("site")
    pages = build.load_site()
    build.write_site(pages, root, root / "generated.json")
    return root, pages


def read(root: Path, slug: str, pages: list[build.Page]) -> str:
    return (root / build.find(pages, slug).path / "index.html").read_text(encoding="utf-8")


def plate(page_html: str, name: str) -> str:
    found = re.search(rf'<figure class="risk-map" id="{name}-plate">.*?</figure>', page_html, re.S)
    assert found, name
    return found.group(0)


def words_of(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def middle(values: list[int]) -> int:
    """The middle value of an odd number of levels."""
    return sorted(values)[len(values) // 2]


def reaching(level: int) -> list[int]:
    """For each risk, how many coded roles reach at least `level`."""
    roles = [role for kind in DATA["scope"]["kinds"] for role in kind["roles"]]
    return [sum(role["levels"][index] >= level for role in roles) for index in range(len(RISK_IDS))]


# ---------------------------------------------------------------- where the plates stand

def test_each_plate_stands_on_its_own_page_and_leaves_no_marker(site):
    root, pages = site
    for page in pages:
        text = (root / page.path / "index.html").read_text(encoding="utf-8")
        assert ('id="scope-plate"' in text) == (page.slug == "engagements"), page.slug
        assert ('id="backing-plate"' in text) == (page.slug == "proof"), page.slug
        assert "<!-- plate:" not in text, page.slug


# ---------------------------------------------------------------- the scope plate

def test_the_scope_plate_draws_the_middle_of_each_kind_and_my_engagement(site):
    root, pages = site
    rows = dict(ROW.findall(plate(read(root, "engagements", pages), "scope")))
    assert list(rows) == RISK_IDS
    for index, risk_id in enumerate(RISK_IDS):
        expected = [middle([role["levels"][index] for role in kind["roles"]]) for kind in DATA["scope"]["kinds"]]
        expected.append(DATA["scope"]["mine"]["levels"][index])
        assert [int(level) for level in CELL_LEVEL.findall(rows[risk_id])] == expected, risk_id


def test_the_scope_plate_codes_five_roles_of_each_kind():
    for kind in DATA["scope"]["kinds"]:
        assert len(kind["roles"]) == risks.ROLES_PER_KIND, kind["id"]
        for role in kind["roles"]:
            assert len(role["levels"]) == len(RISK_IDS) and all(0 <= level <= 3 for level in role["levels"])


def test_the_scope_lead_counts_the_roles_that_build_or_answer_for_each_risk(site):
    root, pages = site
    lead = words_of(re.search(r'<figcaption class="risk-lead">(.*?)</figcaption>',
                              plate(read(root, "engagements", pages), "scope"), re.S).group(1))
    counted = dict(zip(RISK_IDS, reaching(2)))
    total = sum(len(kind["roles"]) for kind in DATA["scope"]["kinds"])
    word = risks.NUMBER_WORDS
    assert lead.startswith(f"In {word[total]} rollout roles at software vendors, ")
    system = "always in scope" if counted["system"] == total else f"in scope in {word[counted['system']]}"
    assert f"the system is {system}" in lead
    assert f"adoption is in {word[counted['owner']]} of them." in lead
    assert f"Checking the record before it is used is in {word[counted['record']]}," in lead
    assert f"a test stage before the write is in {word[counted['write']]}," in lead
    assert lead.endswith(f"and the incentive is in {word[counted['incentive']]}.")


def test_the_scope_plate_names_no_company_and_states_its_sample(site):
    root, pages = site
    scope = plate(read(root, "engagements", pages), "scope")
    source = words_of(re.search(r'<p class="src">(.*?)</p>', scope, re.S).group(1))
    assert "startup.jobs" in source and "ten job postings" in source and "not a whole team" in source
    assert "<a " not in scope   # the coding table, with the names of the companies, stays out of the site


# ---------------------------------------------------------------- the backing plate

def test_the_backing_plate_draws_both_marks_for_each_risk(site):
    root, pages = site
    backing = plate(read(root, "proof", pages), "backing")
    drawn = [(int(reached), int(checkable)) for reached, checkable in TRACK.findall(backing)]
    assert drawn == [(entry["reached"], entry["checkable"]) for entry in DATA["backing"]]
    assert [entry["risk"] for entry in DATA["backing"]] == RISK_IDS


def test_the_backing_lead_counts_what_rests_on_my_word_and_what_you_can_rerun(site):
    root, pages = site
    lead = words_of(re.search(r'<figcaption class="risk-lead">(.*?)</figcaption>',
                              plate(read(root, "proof", pages), "backing"), re.S).group(1))
    answered = [entry for entry in DATA["backing"] if entry["reached"] == 3]
    rerun = sum(entry["checkable"] >= 2 for entry in DATA["backing"])
    word = risks.NUMBER_WORDS
    assert lead.startswith(f"I answered for {word[len(answered)]} of these {word[len(RISK_IDS)]} risks")
    assert lead.endswith(f"{word[rerun].capitalize()} you can re-run yourself.")
    # "You have my word for those" is true only while each of them is field work.
    assert all(entry["grade"] == build.FIGURE_GRADES[3] for entry in answered)


def test_the_backing_rows_open_in_place_without_a_script(site):
    root, pages = site
    backing = plate(read(root, "proof", pages), "backing")
    assert backing.count('<details class="risk-row">') == len(RISK_IDS)
    assert "<script" not in backing


def test_public_evidence_carries_a_link_and_the_rest_does_not():
    """A stranger can only check what is public: a link goes with it, and private or lived evidence has none."""
    for entry in DATA["backing"]:
        assert bool(entry["links"]) == (entry["checkable"] > 0), entry["risk"]
        for link in entry["links"]:
            assert link["href"] == build.GITHUB or re.fullmatch(r"[a-z0-9-]+/", link["href"]), link


# ---------------------------------------------------------------- one vocabulary, one look

def test_the_plates_speak_one_vocabulary(site):
    root, pages = site
    both = plate(read(root, "engagements", pages), "scope") + plate(read(root, "proof", pages), "backing")
    assert set(LEVEL_WORD.findall(both)) <= set(risks.LEVEL_WORDS)
    assert set(html.unescape(grade) for grade in GRADE.findall(both)) <= set(risks.GRADES)
    assert set(html.unescape(payer) for payer in PAYS.findall(both)) <= set(PAYERS)
    assert risks.GRADES[-1] == build.FIGURE_GRADES[3]   # the home page's own words for lived work
    assert [risk["pays"] for risk in DATA["risks"] if risk["pays"] not in PAYERS] == []


def test_the_plate_marks_take_their_colours_from_the_style_sheet(site):
    root, pages = site
    both = plate(read(root, "engagements", pages), "scope") + plate(read(root, "proof", pages), "backing")
    assert not COLOUR_ATTRIBUTE.search(both), COLOUR_ATTRIBUTE.search(both)
    css = (root / "style.css").read_text(encoding="utf-8")
    for name in ("risk-level-on", "risk-track-reached", "risk-track-check"):
        rule = re.search(rf"\.{name}\s*\{{([^}}]*)\}}", css)
        assert rule and "var(--" in rule.group(1), name


# ---------------------------------------------------------------- faults in the data file

@pytest.mark.parametrize("change, fault", [
    (lambda data: data["risks"].pop(), "seven risks"),
    (lambda data: data["scope"]["kinds"][0]["roles"].pop(), "five roles"),
    (lambda data: data["scope"]["mine"]["levels"].__setitem__(0, 4), "level"),
    (lambda data: data["backing"][0].__setitem__("grade", "Trust me"), "grade"),
    (lambda data: data["backing"][1].__setitem__("grade", "Tested, private repository"), "field work"),
    (lambda data: data["backing"][0].pop("links"), "links"),
    (lambda data: data["scope"]["kinds"][1].pop("short"), "short"),
    (lambda data: data["risks"][0].__setitem__("id", "platform"), "system, record"),
])
def test_faults_in_the_data_file_name_the_file_and_the_fault(tmp_path, change, fault):
    data = json.loads(risks.RISKS_FILE.read_text(encoding="utf-8"))
    change(data)
    bad = tmp_path / "risks.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=rf"risks\.json: .*{fault}"):
        risks.load(bad)


def test_a_data_file_that_is_not_an_object_names_the_file(tmp_path):
    bad = tmp_path / "risks.json"
    bad.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match=r"risks\.json: needs a JSON object"):
        risks.load(bad)


def test_an_unknown_plate_marker_stops_the_build():
    with pytest.raises(ValueError, match="unknown plate 'hexagon'"):
        risks.with_plates("<p>A</p>\n<!-- plate: hexagon -->\n", depth=1)


def test_engagements_links_to_the_atlas_outside_the_scope_plate(site):
    root, pages = site
    page_html = read(root, "engagements", pages)
    scope = plate(page_html, "scope")
    assert 'href="https://esstipi-debug.github.io/atlas/"' in page_html
    assert "atlas/" not in scope


def test_plates_and_nav_active_state_are_styled(site):
    root, pages = site
    css = (root / "style.css").read_text(encoding="utf-8")
    assert "article.page:has(.eng-deck, .risk-map)" in css
    assert ":not(.eng-deck, .risk-map, .card-demo)" in css
    assert 'a[aria-current="page"]' in css
    engagements = read(root, "engagements", pages)
    assert 'href="../engagements/" aria-current="page"' in engagements
    assert engagements.count('aria-current="page"') == 1
    assert 'aria-current="page"' not in read(root, "index", pages)
