#!/usr/bin/env python3
"""Turn the generated scenes into the plates of the home page's method section.

Usage:
    python plates.py <folder with escena-1.png ... escena-4.png> [--out src/files/plates]

Each scene is cut to 16:9, read as brightness and mapped onto the page's two colours: the
ground becomes the page background and the strokes the accent. The file is lossy, so the
ground is written a few levels darker than the page and the page lifts it back with a
"lighten" blend (src/style.css): no edge of the picture can show. Every scene is written
twice, as scene-N.webp and scene-N-800.webp.
build.py shows the plates once all of them are there. Pillow is needed only by this script.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps

import build

GROUND = (16, 18, 23)  # --bg in src/style.css, #101217
INK = (227, 162, 126)  # --accent in src/style.css, #E3A27E
GROUND_UNDER = 6  # the plate's ground goes this many levels under the page colour (see the docstring)
SOURCE_STEM = "escena-{number}"
SOURCE_TYPES = (".png", ".jpg", ".jpeg", ".webp")
EDGE_FADE = 0.07  # share of the width that fades into the ground along each edge
GROUND_MARGIN = 14  # brightness levels above the ground that still count as ground
STROKE_SHARE = 0.005  # the brightest half percent of the pixels sets the white point
MASK_FLOOR = 16  # mask levels at or under this become zero, so the border is pure ground
WEBP_QUALITY = 82


def find_source(folder: Path, number: int) -> Path | None:
    for suffix in SOURCE_TYPES:
        candidate = folder / f"{SOURCE_STEM.format(number=number)}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def light_on_dark(gray: Image.Image) -> Image.Image:
    """Strokes light, ground dark: a drawing that came the other way round is inverted."""
    histogram = gray.histogram()
    return gray if sum(histogram[:128]) >= sum(histogram[128:]) else ImageOps.invert(gray)


def stretch(gray: Image.Image) -> Image.Image:
    """Ground to black and the brightest strokes to white. The ground is the most common dark level."""
    histogram = gray.histogram()
    ground = max(range(128), key=histogram.__getitem__)
    black = ground + GROUND_MARGIN
    white, seen, enough = 255, 0, sum(histogram) * STROKE_SHARE
    for level in range(255, black, -1):
        seen += histogram[level]
        if seen >= enough:
            white = level
            break
    span = max(white - black, 1)
    return gray.point([max(0, min(255, round((level - black) * 255 / span))) for level in range(256)])


def edge_fade(size: tuple[int, int]) -> Image.Image:
    """White in the middle and black along the four edges, with a soft ramp between them."""
    width, height = size
    margin = round(width * EDGE_FADE)
    mask = Image.new("L", size, 0)
    mask.paste(255, (margin, margin, width - margin, height - margin))
    mask = mask.filter(ImageFilter.GaussianBlur(margin / 2))
    return mask.point([max(0, (level - MASK_FLOOR) * 255 // (255 - MASK_FLOOR)) for level in range(256)])


def to_plate(source: Path) -> Image.Image:
    with Image.open(source) as image:
        gray = stretch(light_on_dark(image.convert("L")))
    gray = ImageOps.fit(gray, build.PLATE_SIZE, Image.Resampling.LANCZOS)
    gray = ImageChops.multiply(gray, edge_fade(gray.size))
    ground = tuple(max(0, channel - GROUND_UNDER) for channel in GROUND)
    return ImageOps.colorize(gray, black=ground, white=INK)


def convert(source: Path, out_dir: Path, number: int) -> list[Path]:
    """Writes the two sizes of plate `number` and returns their paths, the large one first."""
    plate = to_plate(source)
    out_dir.mkdir(parents=True, exist_ok=True)
    width, height = build.PLATE_SIZE
    small = plate.resize((build.PLATE_SMALL, build.PLATE_SMALL * height // width), Image.Resampling.LANCZOS)
    written = []
    for image, is_small in ((plate, False), (small, True)):
        path = out_dir / build.plate_name(number, is_small)
        image.save(path, "WEBP", quality=WEBP_QUALITY, method=6)
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Turn the generated scenes into the plates of the home page.")
    parser.add_argument("folder", type=Path, help="folder with escena-1.png ... escena-4.png")
    parser.add_argument("--out", type=Path, default=build.plates_dir(), help="where the plates are written")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        print(f"{args.folder} is not a folder")
        return 2
    missing = []
    for number in range(1, len(build.SCENES) + 1):
        source = find_source(args.folder, number)
        if source is None:
            missing.append(SOURCE_STEM.format(number=number))
            continue
        try:
            written = convert(source, args.out, number)
        except OSError as error:  # not an image, or it cannot be read
            print(f"{source.name}: {error}")
            return 2
        print(f"{source.name} -> " + ", ".join(f"{path.name} ({path.stat().st_size // 1024} KB)" for path in written))
    if missing:
        print(f"missing: {', '.join(missing)}. The home page keeps the three tools until all "
              f"{len(build.SCENES)} plates exist.")
        return 1
    print("all plates written; now run: python build.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
