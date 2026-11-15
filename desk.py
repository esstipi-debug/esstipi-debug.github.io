#!/usr/bin/env python3
"""Prepare the hero picture of the desk and the yard detail independently for the home page.

Usage:
    python desk.py <picture> [--out src/files/desk] [--only all|hero|details]

The hero picture is cut to 16:9 and written twice, as desk.webp and desk-800.webp, with its edges
faded into the page colour. Detail cuts (yard.webp) are read from "details" in src/desk.json as
left, top, width and height in percent of the 16:9 frame. Both slots activate independently on the
home page, and any stale kit-*.webp tiles in the output folder are removed.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps

import build
import plates

WEBP_QUALITY = 84
ONLY_MODES = ("all", "hero", "details")


def fitted(source: Path) -> Image.Image:
    """The picture cut to 16:9 at the hero size. Detail percentages refer to this frame."""
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
    """Writes the hero desk picture in both sizes and returns the two paths."""
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


def details(source: Path, out_dir: Path, marks: dict[str, tuple[float, ...]]) -> list[Path]:
    """Writes the detail cuts used by the home page, each cut where its mark says."""
    missing = [name for name in build.DESK_DETAILS if name not in marks]
    if missing:
        raise ValueError(f"no mark for the detail {', '.join(missing)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    picture = fitted(source)
    return [save(ImageOps.fit(picture.crop(percent_box(picture.size, marks[name])), build.DETAIL_SIZES[name],
                              Image.Resampling.LANCZOS), out_dir / build.detail_name(name))
            for name in build.DESK_DETAILS]


def clear_stale_tiles(out_dir: Path) -> int:
    """Removes legacy kit-*.webp object crops from the output folder."""
    if not out_dir.is_dir():
        return 0
    stale = sorted(out_dir.glob("kit-*.webp"))
    for path in stale:
        path.unlink()
    return len(stale)


def clear_details(out_dir: Path) -> int:
    """Removes detail cuts when marks are incomplete so stale details do not stay behind."""
    stale = [out_dir / name for name in build.detail_files() if (out_dir / name).is_file()]
    for path in stale:
        path.unlink()
    return len(stale)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare the desk hero picture and yard detail independently.")
    parser.add_argument("picture", type=Path)
    parser.add_argument("--out", type=Path, default=build.FILES_DIR / "desk")
    parser.add_argument("--only", choices=ONLY_MODES, default="all")
    args = parser.parse_args(argv)
    if not args.picture.is_file():
        print(f"{args.picture} is not a file")
        return 2
    marks: dict[str, tuple[float, ...]] = {}
    if args.only in ("all", "details"):
        try:  # validate marks before touching output files
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
    written: list[Path] = []
    removed_tiles = clear_stale_tiles(args.out)
    removed_details = 0
    try:
        if args.only in ("all", "hero"):
            written += convert(args.picture, args.out)
        if args.only in ("all", "details"):
            if unmarked:
                removed_details = clear_details(args.out)
            else:
                written += details(args.picture, args.out, marks)
    except OSError as error:
        print(f"could not write the desk to {args.out}: {error}")
        return 2
    for path in written:
        print(f"wrote {path}")
    if removed_tiles:
        print(f"removed {removed_tiles} stale kit tile(s)")
    if removed_details:
        print(f"removed {removed_details} stale detail file(s)")
    if args.only in ("all", "details") and unmarked:
        print(f"now mark the details in {build.DESK_SPOTS}: {', '.join(unmarked)}")
        return 1
    print("ready; now run: python build.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
