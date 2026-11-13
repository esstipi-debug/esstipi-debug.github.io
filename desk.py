#!/usr/bin/env python3
"""Prepare the picture of the desk for the home page.

Usage:
    python desk.py <picture> [--out src/files/desk]

The picture is cut to 16:9 and written twice, as desk.webp and desk-800.webp, with its edges faded
into the page colour. Then, from the marks in src/desk.json, the script cuts a tile around each
object (kit-<object>.webp) and the two details the home page uses (chart.webp and yard.webp). A
mark is left, top, width and height, in percent of the picture:

    {"spots": {"passport": [4, 58, 9, 14], "boots": [14, 40, 12, 30]},
     "details": {"chart": [72, 28, 24, 29], "yard": [53, 1, 22, 32]}}

build.py shows the desk on the home page once every file exists. Run without marks, or with some
missing, the script writes the picture, removes the tiles and details cut from an earlier one and
says what to mark. Pillow is needed only by this script, plates.py and their tests.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps

import build
import plates

WEBP_QUALITY = 84
TILE_ROOM = 1.28  # how much of the desk a tile keeps around its object, as a multiple of the mark


def fitted(source: Path) -> Image.Image:
    """The picture cut to 16:9, at the size the page shows it. The marks are percentages of this."""
    with Image.open(source) as image:
        return ImageOps.fit(ImageOps.exif_transpose(image).convert("RGB"), build.DESK_SIZE,
                            Image.Resampling.LANCZOS)


def to_desk(source: Path) -> Image.Image:
    picture = fitted(source)
    ground = tuple(max(0, channel - plates.GROUND_UNDER) for channel in plates.GROUND)
    return Image.composite(picture, Image.new("RGB", picture.size, ground), plates.edge_fade(picture.size))


def save(image: Image.Image, path: Path) -> Path:
    image.save(path, "WEBP", quality=WEBP_QUALITY, method=6)
    return path


def convert(source: Path, out_dir: Path) -> list[Path]:
    """Writes the picture of the desk in both sizes and returns the two paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    large = to_desk(source)
    width, height = build.DESK_SIZE
    small = large.resize((build.DESK_SMALL, build.DESK_SMALL * height // width), Image.Resampling.LANCZOS)
    return [save(image, out_dir / build.desk_name(is_small)) for image, is_small in ((large, False), (small, True))]


def percent_box(size: tuple[int, int], mark: tuple[float, ...]) -> tuple[int, int, int, int]:
    width, height = size
    left, top, wide, high = mark
    return (round(width * left / 100), round(height * top / 100),
            round(width * (left + wide) / 100), round(height * (top + high) / 100))


def tile_box(size: tuple[int, int], mark: tuple[float, ...]) -> tuple[int, int, int, int]:
    """A box of the tile's proportions, centred on the object's mark with room around it, inside the picture."""
    width, height = size
    left, top, wide, high = (value / 100 for value in mark)
    ratio = build.TILE_SIZE[0] / build.TILE_SIZE[1]
    box_wide = min(max(wide * width, high * height * ratio) * TILE_ROOM, width, height * ratio)
    box_high = box_wide / ratio
    x = min(max((left + wide / 2) * width - box_wide / 2, 0), width - box_wide)
    y = min(max((top + high / 2) * height - box_high / 2, 0), height - box_high)
    return round(x), round(y), round(x + box_wide), round(y + box_high)


def tiles(source: Path, out_dir: Path, spots: dict[str, tuple[float, ...]]) -> list[Path]:
    """Writes a tile for each object on the desk, cut around its mark. Returns the paths in the desk's order."""
    missing = [item.key for item in build.DESK if item.key not in spots]
    if missing:
        raise ValueError(f"no mark for {', '.join(missing)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    picture = fitted(source)
    return [save(picture.crop(tile_box(picture.size, spots[item.key])).resize(build.TILE_SIZE, Image.Resampling.LANCZOS),
                 out_dir / build.tile_name(item.key)) for item in build.DESK]


def details(source: Path, out_dir: Path, marks: dict[str, tuple[float, ...]]) -> list[Path]:
    """Writes the details of the picture the home page uses, each cut where its mark says."""
    missing = [name for name in build.DESK_DETAILS if name not in marks]
    if missing:
        raise ValueError(f"no mark for the detail {', '.join(missing)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    picture = fitted(source)
    return [save(ImageOps.fit(picture.crop(percent_box(picture.size, marks[name])), build.DETAIL_SIZES[name],
                              Image.Resampling.LANCZOS), out_dir / build.detail_name(name))
            for name in build.DESK_DETAILS]


def clear_cuts(out_dir: Path) -> int:
    """Removes the tiles and details in the folder, so that none cut from an earlier picture stays beside a
    new one. Returns how many files went."""
    cuts = [out_dir / name for name in build.desk_files() if name not in (build.desk_name(), build.desk_name(small=True))]
    stale = [path for path in cuts if path.is_file()]
    for path in stale:
        path.unlink()
    return len(stale)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare the picture of the desk for the home page.")
    parser.add_argument("picture", type=Path)
    parser.add_argument("--out", type=Path, default=build.FILES_DIR / "desk")
    args = parser.parse_args(argv)
    if not args.picture.is_file():
        print(f"{args.picture} is not a file")
        return 2
    try:  # the marks first: a file that cannot be used must not cost the picture already on the site
        spots = build.desk_spots()
        marks = build.load_details(build.DESK_SPOTS)
    except ValueError as error:
        print(error)
        return 2
    try:
        fitted(args.picture)
    except (OSError, SyntaxError, Image.DecompressionBombError):
        print(f"{args.picture.name} is not a picture")
        return 2
    unmarked = [name for name in build.DESK_DETAILS if name not in marks]
    complete = bool(spots) and not unmarked
    try:
        written = convert(args.picture, args.out)
        removed = 0 if complete else clear_cuts(args.out)
        if complete:
            written += tiles(args.picture, args.out, spots) + details(args.picture, args.out, marks)
    except OSError as error:
        print(f"could not write the desk to {args.out}: {error}")
        return 2
    for path in written:
        print(f"wrote {path}")
    if complete:
        print("the desk is ready; now run: python build.py")
        return 0
    if removed:
        print(f"removed {removed} files cut from an earlier picture")
    if not spots:
        print(f"now mark where each object lies in {build.DESK_SPOTS}")
    else:
        print(f"now mark the details in {build.DESK_SPOTS}: {', '.join(unmarked)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
