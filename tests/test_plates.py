"""Checks on plates.py, the script that turns a generated scene into a plate of the site."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("PIL")
from PIL import Image, ImageDraw  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build  # noqa: E402
import plates  # noqa: E402

GROUND = (16, 18, 23)   # the page background, #101217
INK = (227, 162, 126)   # the accent, #E3A27E
TOLERANCE = 6           # WebP is lossy


def near(pixel: tuple[int, ...], colour: tuple[int, int, int]) -> bool:
    return all(abs(a - b) <= TOLERANCE for a, b in zip(pixel[:3], colour))


def is_ground(pixel: tuple[int, ...]) -> bool:
    """Never lighter than the page, so the page's "lighten" blend hides it, and still close to it."""
    return all(page - 2 * plates.GROUND_UNDER - TOLERANCE <= channel <= page
               for channel, page in zip(pixel[:3], GROUND))


def drawing(path: Path, ground: int, ink: int) -> Path:
    """A 4:3 test image: thick strokes that run to every edge, on a ground that is not the page colour."""
    image = Image.new("RGB", (640, 480), (ground, ground, ground))
    pen = ImageDraw.Draw(image)
    for offset in range(0, 640, 40):
        pen.line((offset, 0, offset, 480), fill=(ink, ink, ink), width=6)
    pen.rectangle((240, 160, 400, 320), fill=(ink, ink, ink))
    image.save(path)
    return path


def test_a_scene_becomes_two_plates_in_the_page_colours(tmp_path):
    source = drawing(tmp_path / "escena-1.png", ground=30, ink=240)
    written = plates.convert(source, tmp_path / "out", number=1)
    assert [path.name for path in written] == [build.plate_name(1), build.plate_name(1, small=True)]
    large, small = (Image.open(path).convert("RGB") for path in written)
    assert large.size == build.PLATE_SIZE
    assert small.size == (build.PLATE_SMALL, build.PLATE_SMALL * build.PLATE_SIZE[1] // build.PLATE_SIZE[0])
    width, height = large.size
    for corner in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
        assert is_ground(large.getpixel(corner)), corner   # no hard edge: the border is the page itself
    assert near(large.getpixel((width // 2, height // 2)), INK)   # the strokes take the accent colour
    border = [large.getpixel((x, y)) for x in range(0, width, 16) for y in (0, 1, height - 2, height - 1)]
    border += [large.getpixel((x, y)) for y in range(0, height, 16) for x in (0, 1, width - 2, width - 1)]
    assert all(is_ground(pixel) for pixel in border)   # all the way round, not only at the corners


def test_a_dark_on_light_drawing_is_inverted(tmp_path):
    source = drawing(tmp_path / "escena-2.png", ground=235, ink=20)
    large = Image.open(plates.convert(source, tmp_path / "out", number=2)[0]).convert("RGB")
    assert near(large.getpixel((large.width // 2, large.height // 2)), INK)
    assert is_ground(large.getpixel((0, 0)))


def test_missing_scenes_are_reported(tmp_path, capsys):
    drawing(tmp_path / "escena-1.png", ground=30, ink=240)
    assert plates.main([str(tmp_path), "--out", str(tmp_path / "out")]) == 1
    assert "escena-2" in capsys.readouterr().out


def test_a_missing_folder_is_an_error(tmp_path, capsys):
    assert plates.main([str(tmp_path / "nowhere")]) == 2
    assert "not a folder" in capsys.readouterr().out
