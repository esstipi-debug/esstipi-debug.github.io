#!/usr/bin/env python3
"""Turn photographs of the objects of the kit into the figures of the home page plate.

Usage:
    python kit.py <manifest.json> [--out src/files/kit]

The manifest sits beside the photographs. For each one it names the figures it shows, from
left to right, and the marks to smooth away (the name or logo of a maker), each as x, y and
radius in the pixels of that photograph:

    {"photos": [{"file": "knife-and-tape.jpg", "figures": ["blade", "tape"],
                 "blank": [[1108, 790, 165]]}]}

Every object has to lie whole inside one plain sheet of a colour that is not its own,
photographed from above and out of direct sun. The sheet is the largest plain area of the
photograph. Its limit is any sharp edge: a shadow has a soft one, so it stays with the sheet.
What is left is cut out, hatched in the accent colour of the page (the lighter the object, the
more lines, as in a white-line engraving) and written twice, as <figure>.webp and
<figure>-360.webp, on a transparent ground. build.py shows a figure once both files exist.
numpy, OpenCV and Pillow are needed only by this script and its tests.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

import build

INK = (227, 162, 126)   # --accent in src/style.css, #E3A27E
PHOTO_SIDE = 2000       # photographs are read at this long side, so one threshold means the same in all of them
EDGE = 15.0             # change of colour between neighbours that counts as a sharp edge
PAPER_NEAR = 8.0        # distance from the colour of the sheet that still counts as the sheet. Kept tight:
                        # a filled ring reads well, a light part punched out of an object does not
PAPER_SHARE = 0.002     # a plain patch smaller than this share of the photograph is a glint, not the sheet
OBJECT_SHARE = 0.002    # anything smaller than this share of the photograph is a speck
LIGHT_REACH = 80.0      # how far the colour of the sheet is carried over what covers it, in pixels
WORK = 2 * build.KIT_SIZE   # a figure is drawn at twice its size and reduced, which smooths the lines
MARGIN = 0.06           # empty border of a figure, as a share of its side
PERIOD = 18.0           # distance between two hatching lines, in pixels of the working size
SOFT = 2.4 / PERIOD     # width of the soft edge of a line, as a share of the period
SQUARE = np.ones((3, 3), np.uint8)
ROUND = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))


# ---------------------------------------------------------------- finding the objects


def sharp_edges(lab: np.ndarray) -> np.ndarray:
    """1 where the colour changes sharply from one pixel to the next, 0 elsewhere."""
    strength = np.zeros(lab.shape[:2], np.float32)
    for channel in cv2.split(lab):
        across = cv2.Sobel(channel, cv2.CV_32F, 1, 0)
        down = cv2.Sobel(channel, cv2.CV_32F, 0, 1)
        strength = np.maximum(strength, cv2.magnitude(across, down))
    return cv2.dilate((strength > EDGE).astype(np.uint8), SQUARE)


def sheet_and_holes(lab: np.ndarray, wall: np.ndarray) -> np.ndarray:
    """True on the sheet: its largest plain area, plus any plain area of its colour (the hole of a ring)."""
    count, labels, stats, _ = cv2.connectedComponentsWithStats((wall == 0).astype(np.uint8), connectivity=4)
    if count < 2:
        return np.zeros(wall.shape, bool)
    areas = stats[:, cv2.CC_STAT_AREA].copy()
    areas[0] = 0   # label 0 is the walls
    largest = int(areas.argmax())
    sheet = labels == largest
    weight = sheet.astype(np.float32)
    reach = cv2.GaussianBlur(weight, (0, 0), LIGHT_REACH)
    carried = cv2.GaussianBlur(lab * weight[..., None], (0, 0), LIGHT_REACH) / np.maximum(reach, 1e-3)[..., None]
    overall = np.median(lab[sheet], axis=0)
    light = np.where(reach[..., None] > 0.02, carried, overall)   # the colour of the sheet near each pixel
    smallest = PAPER_SHARE * wall.size
    for label in np.flatnonzero(areas >= smallest):
        if label == largest:
            continue
        patch = labels == label
        if np.linalg.norm(np.median(lab[patch], axis=0) - np.median(light[patch], axis=0)) < PAPER_NEAR:
            sheet |= patch
    return sheet


def find_objects(photo: np.ndarray) -> list[np.ndarray]:
    """One mask per object lying whole inside the sheet, from left to right, each the size of the photograph."""
    height, width = photo.shape[:2]
    scale = PHOTO_SIDE / max(height, width)
    size = (round(width * scale), round(height * scale))
    small = cv2.resize(photo, size, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    lab = cv2.cvtColor(cv2.GaussianBlur(small, (0, 0), 1.3), cv2.COLOR_BGR2LAB).astype(np.float32)
    solid = (~sheet_and_holes(lab, sharp_edges(lab))).astype(np.uint8)
    solid = cv2.morphologyEx(solid, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    count, labels, stats, centres = cv2.connectedComponentsWithStats(solid)
    found = []
    for label in range(1, count):
        left, top, wide, high, area = stats[label]
        off_the_sheet = left == 0 or top == 0 or left + wide == size[0] or top + high == size[1]
        if area >= OBJECT_SHARE * solid.size and not off_the_sheet:
            found.append((centres[label][0], label))
    return [cv2.resize((labels == label).astype(np.uint8), (width, height), interpolation=cv2.INTER_NEAREST) > 0
            for _, label in sorted(found)]


# ---------------------------------------------------------------- drawing a figure


def without_marks(photo: np.ndarray, discs) -> np.ndarray:
    """The photograph with each disc (x, y, radius) smoothed flat, so that no name or logo is drawn."""
    clean = photo.copy()
    height, width = photo.shape[:2]
    for x, y, radius in discs:
        x, y, radius = round(x), round(y), round(radius)
        reach = 2 * radius   # the blur needs room around the disc
        top, bottom = max(y - reach, 0), min(y + reach + 1, height)
        left, right = max(x - reach, 0), min(x + reach + 1, width)
        inside = np.zeros((bottom - top, right - left), np.uint8)
        cv2.circle(inside, (x - left, y - top), radius, 1, -1)
        smooth = cv2.GaussianBlur(photo[top:bottom, left:right], (0, 0), max(radius / 2.2, 1.0))
        clean[top:bottom, left:right][inside > 0] = smooth[inside > 0]
    return clean


def screen(shape: tuple[int, int], angle: float, shift) -> np.ndarray:
    """Parallel lines at an angle, as a wave: 0 on the middle of a line, 1 halfway to the next one."""
    rows, columns = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)
    turn = np.deg2rad(angle)
    along = (columns * np.cos(turn) + rows * np.sin(turn)) / PERIOD + shift
    return np.abs(2 * (along - np.floor(along)) - 1)


def lines(wave: np.ndarray, width: np.ndarray) -> np.ndarray:
    """Ink of a set of lines whose width, as a share of the period, changes from place to place."""
    return np.clip((width - wave) / SOFT + 0.5, 0, 1) * (width > 0.02)


def engrave(gray: np.ndarray, shape: np.ndarray) -> np.ndarray:
    """Line work for one object, from 0 (ground) to 1 (ink): hatching that widens with the light,
    crossed where the object is lightest, and its contours."""
    inside = shape > 0
    flat = gray.copy()
    flat[~inside] = np.median(gray[inside])   # the sheet around the object must not set its contrast
    tone = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8)).apply(flat).astype(np.float32) / 255
    low, high = np.percentile(tone[inside], (2, 98))
    tone = np.clip((tone - low) / max(high - low, 1e-3), 0, 1)
    lean = cv2.GaussianBlur(tone, (0, 0), 2 * PERIOD) * 1.3   # lines lean with the light, as a cut line does
    ink = lines(screen(tone.shape, 24, lean), np.clip((tone - 0.10) / 0.55, 0, 1) * 0.72)
    ink = np.maximum(ink, lines(screen(tone.shape, 88, lean * 0.7), np.clip((tone - 0.52) / 0.42, 0, 1) * 0.6))
    ink = np.maximum(ink, lines(screen(tone.shape, -38, 0.0), np.clip((tone - 0.82) / 0.18, 0, 1) * 0.5))
    edges = cv2.Canny(cv2.GaussianBlur(flat, (0, 0), PERIOD / 5), 18, 50)
    outline = cv2.morphologyEx(shape, cv2.MORPH_GRADIENT, SQUARE) * 255
    contour = cv2.dilate(np.maximum(edges, outline), ROUND).astype(np.float32) / 255
    contour = cv2.GaussianBlur(contour, (0, 0), 0.8)
    body = cv2.GaussianBlur(cv2.dilate(shape, ROUND).astype(np.float32), (0, 0), 1.2)
    return np.clip(np.maximum(ink, contour), 0, 1) * np.clip(body, 0, 1)


def picture(alpha: np.ndarray) -> Image.Image:
    """A picture in one ink: the drawing is its transparency, so it sits on any ground."""
    ink = np.empty((*alpha.shape, 4), np.uint8)
    ink[..., :3] = INK
    ink[..., 3] = alpha
    return Image.fromarray(ink, "RGBA")


def figure(photo: np.ndarray, mask: np.ndarray, blank=()) -> Image.Image:
    """The object under `mask` as a square figure of the plate."""
    photo = without_marks(photo, blank)
    rows, columns = np.nonzero(mask)
    top, bottom, left, right = rows.min(), rows.max() + 1, columns.min(), columns.max() + 1
    scale = WORK * (1 - 2 * MARGIN) / max(bottom - top, right - left)
    size = (max(round((right - left) * scale), 1), max(round((bottom - top) * scale), 1))
    gray = cv2.cvtColor(photo[top:bottom, left:right], cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, size, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    shape = cv2.resize(mask[top:bottom, left:right].astype(np.float32), size, interpolation=cv2.INTER_LINEAR)
    drawn = engrave(gray, (shape > 0.5).astype(np.uint8))
    canvas = np.zeros((WORK, WORK), np.float32)
    row, column = (WORK - size[1]) // 2, (WORK - size[0]) // 2
    canvas[row:row + size[1], column:column + size[0]] = drawn
    alpha = cv2.resize(canvas, (build.KIT_SIZE, build.KIT_SIZE), interpolation=cv2.INTER_AREA)
    return picture(np.clip(alpha * 255, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- files


def read_photo(source: Path) -> np.ndarray:
    with Image.open(source) as image:
        upright = ImageOps.exif_transpose(image).convert("RGB")
    return cv2.cvtColor(np.asarray(upright), cv2.COLOR_RGB2BGR)


def convert(source: Path, names: list[str], out_dir: Path, blank=()) -> list[Path]:
    """Writes the figures of one photograph, named from left to right, in both sizes."""
    known = {entry.key for entry in build.KIT}
    for name in names:
        if name not in known:
            raise ValueError(f"{source.name}: unknown figure '{name}'")
    photo = read_photo(source)
    masks = find_objects(photo)
    if len(masks) != len(names):
        raise ValueError(f"{source.name}: {len(masks)} objects found, {len(names)} figures named")
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, mask in zip(names, masks):
        large = figure(photo, mask, blank)
        alpha = np.asarray(large)[..., 3]
        small = picture(cv2.resize(alpha, (build.KIT_SMALL, build.KIT_SMALL), interpolation=cv2.INTER_AREA))
        for image, is_small in ((large, False), (small, True)):
            path = out_dir / build.figure_name(name, is_small)
            image.save(path, "WEBP", lossless=True, method=6)
            written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Turn photographs of the kit into the figures of the plate.")
    parser.add_argument("manifest", type=Path, help="JSON file beside the photographs")
    parser.add_argument("--out", type=Path, default=build.FILES_DIR / "kit")
    args = parser.parse_args(argv)
    if not args.manifest.is_file():
        print(f"{args.manifest} is not a file")
        return 2
    failed = False
    for entry in json.loads(args.manifest.read_text(encoding="utf-8"))["photos"]:
        source = args.manifest.parent / entry["file"]
        try:
            written = convert(source, entry["figures"], args.out, [tuple(disc) for disc in entry.get("blank", [])])
        except (OSError, ValueError) as error:
            print(f"{source.name}: {error}")
            failed = True
            continue
        for path in written:
            print(f"wrote {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
