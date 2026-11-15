"""The two evidence plates of the site, drawn from src/risks.json.

The scope plate (engagements page) sets what a rollout role at a software vendor takes on beside my cutover
engagement, one row per risk: each cell is the middle level of five coded roles. The backing plate (proof page)
shows, for each risk, how far I went and how far a stranger can check it without me.

A page asks for a plate with a marker on a line of its own, <!-- plate: scope --> or <!-- plate: backing -->.
Both plates are plain HTML and inline SVG: no script, and every colour comes from the style sheet. The coding
table, with the names of the companies and the links to their postings, stays out of this public repository;
C:/tolkien keeps it, and a test there checks that the two copies agree.

It imports build, so build imports it late, when it renders a page.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

import build
from build import esc, href

RISKS_FILE = build.SRC / "risks.json"
LEVEL_WORDS = ("Not in scope", "Described", "Built and tested outside a live system",
               "Answered for it in a live operation")
FIELD_WORK = build.FIGURE_GRADES[3]   # the home page's own words for lived work
PUBLIC = "Public and re-runnable"
GRADES = (PUBLIC, "Tested, private repository", FIELD_WORK)
PAYERS = ("Finance", "Operations", "The chief executive")   # the three readers each situation page answers
RISK_IDS = ("system", "record", "floor", "incentive", "write", "owner", "cash")   # the leads name five of them
RISK_COUNT = len(RISK_IDS)
ROLES_PER_KIND = 5
NUMBER_WORDS = ("none", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
MARKER = re.compile(r"<!-- plate: ([a-z]+) -->")
BUILT = 2               # a role counts in the lead from "built and tested outside a live system" up
TRACK_X = (8, 40, 72, 104)   # where each level sits on the backing track, in SVG units


# ---------------------------------------------------------------- the data file

def fault(path: Path, message: str) -> ValueError:
    return ValueError(f"{path.name}: {message}")


def require(path: Path, item: object, texts: tuple[str, ...], where: str, lists: tuple[str, ...] = ()) -> None:
    """The keys a plate reads, present and of the right kind, so a fault names the file and not a line of code."""
    if not isinstance(item, dict):
        raise fault(path, f"{where}: needs a JSON object")
    for key in texts:
        if not isinstance(item.get(key), str) or not item[key].strip():
            raise fault(path, f"{where}: needs the text '{key}'")
    for key in lists:
        if not isinstance(item.get(key), list):
            raise fault(path, f"{where}: needs the list '{key}'")


def check_level(path: Path, value: object, where: str) -> None:
    if not (isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 3):
        raise fault(path, f"{where}: a level must be a whole number from 0 to 3, not {value!r}")


def check_levels(path: Path, levels: object, where: str) -> None:
    if not (isinstance(levels, list) and len(levels) == RISK_COUNT):
        raise fault(path, f"{where}: needs one level for each of the seven risks")
    for value in levels:
        check_level(path, value, where)


def check_scope(path: Path, scope: object) -> None:
    require(path, scope, ("source",), "scope", lists=("kinds",))
    for kind in scope["kinds"]:
        require(path, kind, ("id", "label", "short"), "scope kind", lists=("roles",))
        if len(kind["roles"]) != ROLES_PER_KIND:
            raise fault(path, f"kind '{kind['id']}' needs five roles, has {len(kind['roles'])}")
        for number, role in enumerate(kind["roles"], 1):
            require(path, role, ("posted",), f"{kind['id']} role {number}")
            check_levels(path, role.get("levels"), f"{kind['id']} role {number}")
    require(path, scope.get("mine"), ("label", "short"), "my engagement")
    check_levels(path, scope["mine"].get("levels"), "my engagement")


def check_backing(path: Path, backing: object) -> None:
    if not isinstance(backing, list):
        raise fault(path, "needs the list 'backing'")
    for entry in backing:
        require(path, entry, ("risk", "grade", "reached_text", "checkable_text"), "backing", lists=("links",))
        for link in entry["links"]:
            require(path, link, ("label", "href"), f"{entry['risk']} link")
    if [entry["risk"] for entry in backing] != list(RISK_IDS):
        raise fault(path, "the backing must follow the seven risks, in their order")
    for entry in backing:
        check_level(path, entry["reached"], entry["risk"])
        check_level(path, entry["checkable"], entry["risk"])
        if entry["grade"] not in GRADES:
            raise fault(path, f"{entry['risk']}: unknown grade '{entry['grade']}'")
        if entry["reached"] == 3 and entry["grade"] != FIELD_WORK:
            raise fault(path, f"{entry['risk']}: the lead says what I answered for rests on my word; "
                              "with any grade but field work it stops being true")
        if bool(entry["links"]) != (entry["checkable"] > 0):
            raise fault(path, f"{entry['risk']}: a link goes with what a stranger can check, and only with it")


def load(path: Path = RISKS_FILE) -> dict:
    """The plates' data, checked: a fault names the file and what is wrong."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise fault(path, "is missing") from error
    except json.JSONDecodeError as error:
        raise fault(path, f"is not valid JSON ({error.msg}, line {error.lineno})") from error
    if not isinstance(data, dict):
        raise fault(path, "needs a JSON object at the top")
    risks = data.get("risks")
    if not (isinstance(risks, list) and len(risks) == RISK_COUNT):
        raise fault(path, "needs seven risks")
    for risk in risks:
        require(path, risk, ("id", "label", "pays"), "risk")
        if risk["pays"] not in PAYERS:
            raise fault(path, f"{risk['id']}: who pays must be one of {', '.join(PAYERS)}")
    if [risk["id"] for risk in risks] != list(RISK_IDS):
        raise fault(path, f"the seven risks must be {', '.join(RISK_IDS)}, in that order")
    require(path, data, ("backing_key", "backing_limit"), "top")
    check_scope(path, data.get("scope"))
    check_backing(path, data.get("backing"))
    return data


# ---------------------------------------------------------------- the scope plate

def middle(values: list[int]) -> int:
    """The middle value of an odd number of levels."""
    return sorted(values)[len(values) // 2]


def level_cell(level: int) -> str:
    """A level in words, after a mark of three squares filled up to it. The words carry the meaning."""
    squares = "".join(f'<rect class="risk-level-{"on" if step < level else "off"}" x="{1 + step * 10}" y="1" '
                      'width="6" height="6"/>' for step in range(3))
    mark = f'<svg class="risk-level-mark" viewBox="0 0 28 8" aria-hidden="true" focusable="false">{squares}</svg>'
    return (f'<span class="risk-level" data-level="{level}">{mark}'
            f'<span class="risk-level-word">{LEVEL_WORDS[level]}</span></span>')


def scope_lead(data: dict) -> str:
    """The plate's sentence, counted from the coded roles: how many build or answer for each risk."""
    roles = [role for kind in data["scope"]["kinds"] for role in kind["roles"]]
    ids = [risk["id"] for risk in data["risks"]]
    count = {risk_id: sum(role["levels"][index] >= BUILT for role in roles) for index, risk_id in enumerate(ids)}
    word, total = NUMBER_WORDS, len(roles)
    system = "always in scope" if count["system"] == total else f"in scope in {word[count['system']]}"
    return (f"In {word[total]} rollout roles at software vendors, the system is {system} "
            f"and adoption is in {word[count['owner']]} of them. "
            f"Checking the record before it is used is in {word[count['record']]}, "
            f"a test stage before the write is in {word[count['write']]}, "
            f"and the incentive is in {word[count['incentive']]}.")


def scope_plate(data: dict, depth: int) -> str:
    kinds, mine = data["scope"]["kinds"], data["scope"]["mine"]
    # The roles are explicit because the narrow layout sets the table to blocks, and some screen readers then
    # stop reading it as a table; the header row is hidden from sight there, never from them.
    heads = "".join(f'<th scope="col" role="columnheader">{esc(column["label"])}</th>' for column in (*kinds, mine))
    labels = [column["short"] for column in (*kinds, mine)]
    rows = []
    for index, risk in enumerate(data["risks"]):
        levels = [middle([role["levels"][index] for role in kind["roles"]]) for kind in kinds]
        levels.append(mine["levels"][index])
        cells = "".join(f'<td role="cell" data-label="{esc(label)}">{level_cell(level)}</td>'
                        for label, level in zip(labels, levels))
        rows.append(f'<tr data-risk="{risk["id"]}" role="row"><th scope="row" role="rowheader">'
                    f'{esc(risk["label"])}</th>{cells}</tr>')
    body = "\n".join(rows)
    return f"""<figure class="risk-map" id="scope-plate">
<figcaption class="risk-lead">{esc(scope_lead(data))}</figcaption>
<table class="risk-table" role="table">
<thead role="rowgroup"><tr role="row"><th scope="col" role="columnheader">The risk</th>{heads}</tr></thead>
<tbody role="rowgroup">
{body}
</tbody>
</table>
<p class="src">{esc(data["scope"]["source"])}</p>
</figure>"""


# ---------------------------------------------------------------- the backing plate

def track(reached: int, checkable: int) -> str:
    """Both marks on one track of four levels: a dot for how far I went, a ring for what a stranger can check."""
    label = (f"How far I went: {LEVEL_WORDS[reached].lower()}. "
             f"What you can check without me: {LEVEL_WORDS[checkable].lower()}.")
    ticks = "".join(f'<circle class="risk-track-tick" cx="{x}" cy="9" r="1.6"/>' for x in TRACK_X)
    return (f'<svg class="risk-track" data-reached="{reached}" data-checkable="{checkable}" viewBox="0 0 112 18" '
            f'role="img" aria-label="{esc(label)}">'
            f'<line class="risk-track-line" x1="{TRACK_X[0]}" y1="9" x2="{TRACK_X[-1]}" y2="9"/>{ticks}'
            f'<circle class="risk-track-check" cx="{TRACK_X[checkable]}" cy="9" r="6.5"/>'
            f'<circle class="risk-track-reached" cx="{TRACK_X[reached]}" cy="9" r="4"/></svg>')


def links_html(links: list[dict], depth: int) -> str:
    anchors = [f'<a href="{esc(link["href"] if link["href"].startswith("https://") else href(link["href"], depth))}">'
               f'{esc(link["label"])}</a>' for link in links]
    return f" See {' and '.join(anchors)}." if anchors else ""


def backing_row(risk: dict, entry: dict, depth: int) -> str:
    went = (f'<span class="risk-level-word">{LEVEL_WORDS[entry["reached"]]}</span> '
            f'(<span class="risk-grade">{esc(entry["grade"])}</span>). {esc(entry["reached_text"])}')
    check = esc(entry["checkable_text"])
    if entry["checkable"]:
        check = (f'<span class="risk-level-word">{LEVEL_WORDS[entry["checkable"]]}</span> '
                 f'(<span class="risk-grade">{PUBLIC}</span>). {check}{links_html(entry["links"], depth)}')
    return f"""<li><details class="risk-row">
<summary><span class="risk-name">{esc(risk["label"])}</span><span class="risk-pays">{esc(risk["pays"])}</span>{track(entry["reached"], entry["checkable"])}</summary>
<div class="risk-evidence">
<p><strong>How far I went:</strong> {went}</p>
<p><strong>What you can check without me:</strong> {check}</p>
</div>
</details></li>"""


def backing_lead(data: dict) -> str:
    """The plate's sentence, counted from the backing: what rests on my word and what a stranger can re-run."""
    answered = sum(entry["reached"] == 3 for entry in data["backing"])
    rerun = sum(entry["checkable"] >= BUILT for entry in data["backing"])
    word = NUMBER_WORDS
    return (f"I answered for {word[answered]} of these {word[len(data['risks'])]} risks in live operations, "
            f"and you have my word for those. {word[rerun].capitalize()} you can re-run yourself.")


def backing_plate(data: dict, depth: int) -> str:
    rows = "\n".join(backing_row(risk, entry, depth) for risk, entry in zip(data["risks"], data["backing"]))
    return f"""<figure class="risk-map" id="backing-plate">
<figcaption class="risk-lead">{esc(backing_lead(data))}</figcaption>
<p class="risk-key">{esc(data["backing_key"])}</p>
<ul class="risk-rows">
{rows}
</ul>
<p class="risk-limit">{esc(data["backing_limit"])}</p>
</figure>"""


# ---------------------------------------------------------------- the markers

PLATES: dict[str, Callable[[dict, int], str]] = {"scope": scope_plate, "backing": backing_plate}


def with_plates(body_html: str, depth: int, path: Path = RISKS_FILE) -> str:
    """The page body with each plate marker replaced by its plate. An unknown marker stops the build."""
    names = MARKER.findall(body_html)
    if not names:
        return body_html
    unknown = [name for name in names if name not in PLATES]
    if unknown:
        raise ValueError(f"unknown plate '{unknown[0]}'")
    data = load(path)
    return MARKER.sub(lambda found: PLATES[found.group(1)](data, depth), body_html)
