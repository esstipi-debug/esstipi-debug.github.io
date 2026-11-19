"""The line drawings of the home page: the record as a white plan line, the floor as a red one.

Plain SVG, no script, and every colour comes from the style sheets. A drawing that is a schematic says
"not to scale"; the one cut from a published share says its lengths are to scale, and where the floor leaves
the record is worked out from that share. The three drawings of the method carry no words: the step's own
heading and sentence stand under each of them, and each says what it shows in its label.
"""
from __future__ import annotations

from html import escape

VIEW = (560, 230)        # the drawing's own units; the style sheets size its lines and letters by screen width
RECORD_SPAN = (30, 530)  # where the record line starts and ends
NOT_TO_SCALE = "not to scale"
TO_SCALE = "lengths to scale"
# Where the floor steps, as shares of the stretch that left the record: uneven on purpose, like a count sheet.
STEP_SHARES = (.175, .385, .615, .815)
STEP_DEPTHS = (135, 112, 150, 122, 140)


def frame(label: str, body: str, note: str, note_left: bool = False) -> str:
    """One drawing: what it shows in words, its lines, and the note that says whether it is to scale."""
    width, height = VIEW
    place = f'x="{RECORD_SPAN[0]}" text-anchor="start"' if note_left else f'x="{RECORD_SPAN[1]}" text-anchor="end"'
    return (f'<svg class="dwg" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label, quote=True)}">'
            f'{body}<text class="note" {place} y="{height - 8}">{note}</text></svg>')


def gap() -> str:
    """Before a situation is picked: the record runs straight, the floor drops away, and the distance is the gap."""
    return frame(
        "The record runs straight; the floor drops away from it and comes back. The distance between them is the gap.",
        '<path class="d-plan" d="M30 80H530"/>'
        '<path class="d-floor" pathLength="1" d="M30 80H150C185 80 185 160 220 160H330C365 160 365 80 400 80H530"/>'
        '<path class="d-dim" d="M275 80V160M268 80H282M268 160H282"/>'
        '<text x="30" y="62">the record</text><text x="232" y="190">the floor</text>'
        '<text class="d-big" x="290" y="127">the gap</text>', NOT_TO_SCALE)


def go_live(amount: str) -> str:
    """A new system goes live: the plan runs straight through it, the floor drops and takes time to come back."""
    return frame(
        "The plan runs straight through go-live; the floor drops at go-live and takes the rest of the year to come back.",
        '<path class="d-plan" d="M30 80H530"/><path class="d-dim" d="M190 40V190"/>'
        '<path class="d-floor" pathLength="1" d="M30 80H190L210 165C300 165 400 130 500 80H530"/>'
        '<path class="d-dim" d="M250 80V163M243 80H257M243 163H257"/>'
        '<text x="30" y="62">the plan</text><text x="198" y="56">go-live</text>'
        f'<text x="310" y="196">the floor</text><text class="d-big" x="264" y="128">{escape(amount)}</text>',
        NOT_TO_SCALE)


def leaves_the_record_at(share_off: float) -> int:
    """Where along the record line the floor leaves it, when that share of the records does not match."""
    left, right = RECORD_SPAN
    return left + round((1 - share_off) * (right - left))


def inventory(share_off: float, whole: str = "", share: str = "") -> str:
    """The inventory number is wrong: the floor follows the record, then leaves it for the share that is off."""
    left, right = RECORD_SPAN
    cut = leaves_the_record_at(share_off)
    turns = [cut + round(step * (right - cut)) for step in STEP_SHARES] + [right]
    steps = "".join(f"V{depth}H{x}" for depth, x in zip(STEP_DEPTHS, turns))
    middle = (cut + right) // 2
    on, off = round(100 * (1 - share_off)), round(100 * share_off)
    return frame(
        f"The floor follows the record for {on}% of its length and leaves it for the other {off}%.",
        f'<path class="d-dim" d="M{left} 44H{right}M{left} 38V50M{right} 38V50"/><path class="d-plan" d="M{left} 90H{right}"/>'
        f'<path class="d-floor" pathLength="1" d="M{left} 90H{cut}{steps}"/>'
        f'<path class="d-dim" d="M{cut} 182H{right}M{cut} 176V188M{right} 176V188"/>'
        f'<text x="280" y="32" text-anchor="middle">{escape(whole)}</text><text x="{left}" y="78">the record</text>'
        f'<text x="{left}" y="132">the floor</text>'
        f'<text class="d-big" x="{middle}" y="208" text-anchor="middle">{escape(share)}</text>',
        TO_SCALE, note_left=True)


def workaround(share: str) -> str:
    """The floor works around the system: the plan runs through it, the floor goes over it and comes back."""
    return frame(
        "The plan runs straight through the system; the floor goes around it and comes back to the line.",
        '<rect class="d-box" x="208" y="78" width="144" height="64"/><path class="d-plan" d="M40 110H208M352 110H520"/>'
        '<path class="d-floor" pathLength="1" d="M40 110H146C176 110 171 46 201 46H359C389 46 384 110 414 110H520"/>'
        '<text x="40" y="98">the plan</text><text x="280" y="117" text-anchor="middle">the system</text>'
        f'<text x="420" y="142">the floor</text><text class="d-big" x="280" y="34" text-anchor="middle">{escape(share)}</text>',
        NOT_TO_SCALE)


# The method: the same line in three states. No words inside; the label says what each one shows.
METHOD = (
    ("The floor line drops away from the record, and the drop is measured.",
     '<path class="d-plan" d="M10 40H230"/>'
     '<path class="d-floor" d="M10 40H70C88 40 88 86 106 86H140C158 86 158 40 176 40H230"/>'
     '<path class="d-dim" d="M123 40V86M116 40H130M116 86H130"/>'),
    ("The part of the floor line that dropped is cut out at both ends.",
     '<path class="d-plan" d="M10 40H230"/><path class="d-floor" d="M10 40H70M176 40H230"/>'
     '<path class="d-ghost" d="M70 58C88 58 88 104 106 104H140C158 104 158 58 176 58"/>'
     '<path class="d-cut" d="M63 28L77 52M169 28L183 52"/>'),
    ("The floor line runs along the record again, stitched across the cut.",
     '<path class="d-plan" d="M10 37H230"/><path class="d-floor" d="M10 43H230"/>'
     '<path class="d-stitch" d="M76 31V49M90 31V49M104 31V49M118 31V49M132 31V49M146 31V49M160 31V49M174 31V49"/>'),
)


def method_step(index: int) -> str:
    label, body = METHOD[index]
    return f'<svg class="dwg dwg-step" viewBox="0 0 240 112" role="img" aria-label="{escape(label, quote=True)}">{body}</svg>'
