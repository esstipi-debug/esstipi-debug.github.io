"""The two evidence plates of the site, drawn from src/risks.json.

The scope plate (engagements page) sets what a rollout role at a software vendor takes on beside my cutover
engagement, one row per risk: one mark for each coded posting, then mine, then how many of the postings build
or answer for the risk. The backing plate (proof page) draws two lines for each risk on one scale: how far I
went, and under it how far a stranger can check it without me.

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
KINDS = 2               # the narrow layout of the scope plate sets two kinds of five roles in one line
NUMBER_WORDS = ("none", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
MARKER = re.compile(r"<!-- plate: ([a-z]+) -->")
BUILT = 2               # a role counts in the lead from "built and tested outside a live system" up
TRACK_VIEW = (300, 28)                # the backing track, in its own units; the style sheet stretches it
TRACK_X = (1, 100.33, 199.67, 299)    # where each level falls on it
WENT, CHECK = "How far I went", "What you can check without me"   # the two lines, and the two halves of a row
TRACK_LINES = (("reached", 9), ("check", 19))   # the class of each line and the height it runs at
TICK = 5                                         # half the height of the stroke that closes a line


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
    require(path, scope, ("source", "reading", "count_head"), "scope", lists=("kinds",))
    if len(scope["kinds"]) != KINDS:
        raise fault(path, f"the scope plate is laid out for two kinds of role, not {len(scope['kinds'])}")
    for kind in scope["kinds"]:
        require(path, kind, ("id", "label", "short", "group"), "scope kind", lists=("roles",))
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

def level_mark(level: int) -> str:
    """A level as three strokes filled from the bottom, with its words beside it: the shape carries the
    level, so it reads without colour, and the words say it to whoever does not see the mark."""
    strokes = "".join(f'<i class="risk-level-{"on" if 3 - step <= level else "off"}"></i>' for step in range(3))
    return (f'<span class="risk-level" data-level="{level}"><span class="risk-tally" aria-hidden="true">{strokes}</span>'
            f'<span class="risk-level-word">{LEVEL_WORDS[level]}</span></span>')


def counted(data: dict) -> dict[str, int]:
    """For each risk, how many of the coded roles build or answer for it."""
    roles = [role for kind in data["scope"]["kinds"] for role in kind["roles"]]
    return {risk["id"]: sum(role["levels"][index] >= BUILT for role in roles)
            for index, risk in enumerate(data["risks"])}


def scope_lead(data: dict) -> str:
    """The plate's sentence, counted from the coded roles: how many build or answer for each risk."""
    count = counted(data)
    word, total = NUMBER_WORDS, sum(len(kind["roles"]) for kind in data["scope"]["kinds"])
    system = "always in scope" if count["system"] == total else f"in scope in {word[count['system']]}"
    return (f"In {word[total]} rollout roles at software vendors, the system is {system} "
            f"and adoption is in {word[count['owner']]} of them. "
            f"Checking the record before it is used is in {word[count['record']]}, "
            f"a test stage before the write is in {word[count['write']]}, "
            f"and the incentive is in {word[count['incentive']]}.")


def scope_row(risk: dict, index: int, data: dict, count: int) -> str:
    """One risk: a mark for each coded role, with a gap where a new kind of role starts, then mine, then the count."""
    kinds, mine = data["scope"]["kinds"], data["scope"]["mine"]
    cells = []
    for kind_number, kind in enumerate(kinds):
        for role_number, role in enumerate(kind["roles"]):
            gap = ' class="risk-gap"' if kind_number and not role_number else ""
            cells.append(f'<td role="cell"{gap}>{level_mark(role["levels"][index])}</td>')
    total = sum(len(kind["roles"]) for kind in kinds)
    return (f'<tr data-risk="{risk["id"]}" role="row"><th scope="row" role="rowheader">{esc(risk["label"])}</th>'
            f'{"".join(cells)}<td role="cell" class="risk-mine risk-gap">{level_mark(mine["levels"][index])}</td>'
            f'<td role="cell" class="risk-count"><b>{count}</b> of {total}</td></tr>')


def scope_legend(mine: dict) -> str:
    levels = "".join(f"<li>{level_mark(level)}</li>" for level in range(len(LEVEL_WORDS)))
    strokes = '<i class="risk-level-on"></i>' * 3
    return (f'<ul class="risk-legend">{levels}<li class="risk-mine"><span class="risk-tally" aria-hidden="true">'
            f'{strokes}</span>{esc(mine["short"])}</li></ul>')


def scope_plate(data: dict, depth: int) -> str:
    scope = data["scope"]
    kinds, mine, count = scope["kinds"], scope["mine"], counted(data)
    # The roles are explicit because the narrow layout sets the table to a grid, and some screen readers then
    # stop reading it as a table; the header row is hidden from sight there, never from them.
    groups = "".join(f'<th scope="colgroup" colspan="{len(kind["roles"])}" role="columnheader">{esc(kind["group"])}</th>'
                     for kind in kinds)
    # The first column of each kind after the first is wider: it carries the gap that sets the kinds apart.
    columns = "<col>" + "".join(
        f'<col class="risk-c-lv" span="{len(kind["roles"])}">' if not number
        else f'<col class="risk-c-gap"><col class="risk-c-lv" span="{len(kind["roles"]) - 1}">'
        for number, kind in enumerate(kinds))
    rows = "\n".join(scope_row(risk, index, data, count[risk["id"]]) for index, risk in enumerate(data["risks"]))
    return f"""<figure class="risk-map" id="scope-plate">
<figcaption class="risk-lead">{esc(scope_lead(data))}</figcaption>
{scope_legend(mine)}
<p class="risk-read">{esc(scope["reading"])}</p>
<table class="risk-matrix" role="table">
<colgroup>{columns}<col class="risk-c-mine"><col class="risk-c-count"></colgroup>
<thead role="rowgroup"><tr role="row"><th scope="col" role="columnheader">The risk</th>{groups}<th scope="col" role="columnheader" class="risk-gap">{esc(mine["short"])}</th><th scope="col" role="columnheader" class="risk-gap">{esc(scope["count_head"])}</th></tr></thead>
<tbody role="rowgroup">
{rows}
</tbody>
</table>
<p class="src">{esc(scope["source"])}</p>
</figure>"""


# ---------------------------------------------------------------- the backing plate

def track_line(level: int, y: int) -> str:
    """A line from the start of the scale to a level, closed by a short stroke. A level of nothing is the
    stroke alone, at the start: the mark is never missing, it has no length."""
    start, end = TRACK_X[0], TRACK_X[level]
    if not level:
        return f"M{start:g} {y - TICK}V{y + TICK}"
    return f"M{start:g} {y}H{end:g}M{end:g} {y - TICK}V{y + TICK}"


def track(reached: int, checkable: int) -> str:
    """Two lines on one scale of four levels: above, how far I went; below, what a stranger can check."""
    label = f"{WENT}: {LEVEL_WORDS[reached].lower()}. {CHECK}: {LEVEL_WORDS[checkable].lower()}."
    width, height = TRACK_VIEW
    ticks = "".join(f'<path class="risk-track-tick" d="M{x:g} 2V{height - 2}"/>' for x in TRACK_X)
    lines = "".join(f'<path class="risk-track-{name}" d="{track_line(level, y)}"/>'
                    for (name, y), level in zip(TRACK_LINES, (reached, checkable)))
    return (f'<svg class="risk-track" data-reached="{reached}" data-checkable="{checkable}" viewBox="0 0 {width} {height}" '
            f'preserveAspectRatio="none" role="img" aria-label="{esc(label)}">{ticks}{lines}</svg>')


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
<summary><span class="risk-name">{esc(risk["label"])} <span class="risk-pays">{esc(risk["pays"])}</span></span>{track(entry["reached"], entry["checkable"])}</summary>
<div class="risk-evidence">
<p><strong>{WENT}:</strong> {went}</p>
<p><strong>{CHECK}:</strong> {check}</p>
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
    lines = "".join(f'<span><i class="risk-swatch risk-swatch-{name}" aria-hidden="true"></i>{words}</span>'
                    for (name, _), words in zip(TRACK_LINES, (WENT, CHECK)))
    scale = "".join(f"<span>{word}</span>" for word in LEVEL_WORDS)
    return f"""<figure class="risk-map" id="backing-plate">
<figcaption class="risk-lead">{esc(backing_lead(data))}</figcaption>
<p class="risk-lines">{lines}</p>
<p class="risk-key">{esc(data["backing_key"])}</p>
<div class="risk-scale" aria-hidden="true">{scale}</div>
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
