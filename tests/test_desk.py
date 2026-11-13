"""Checks on desk.py, the script that prepares the picture of the desk for the home page."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("PIL")
from PIL import Image, ImageDraw  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build  # noqa: E402
import desk  # noqa: E402
import plates  # noqa: E402

GROUND = (16, 18, 23)    # the page background, #101217
LAMPLIT = (200, 150, 60)
TOLERANCE = 8            # WebP is lossy


def is_ground(pixel: tuple[int, ...]) -> bool:
    """Never lighter than the page, so the "lighten" blend of the page hides it, and still close to it."""
    return all(page - 2 * plates.GROUND_UNDER - TOLERANCE <= channel <= page
               for channel, page in zip(pixel[:3], GROUND))


def photo(path: Path) -> Path:
    """A 4:3 test picture: a brown desk that runs to every edge, with a lamplit patch in the middle."""
    image = Image.new("RGB", (1200, 900), (90, 70, 50))
    ImageDraw.Draw(image).rectangle((480, 360, 720, 540), fill=LAMPLIT)
    image.save(path)
    return path


def test_the_picture_becomes_two_files_that_fade_into_the_page(tmp_path):
    written = desk.convert(photo(tmp_path / "escritorio.png"), tmp_path / "out")
    assert [path.name for path in written] == [build.desk_name(), build.desk_name(small=True)]
    large, small = (Image.open(path).convert("RGB") for path in written)
    assert large.size == build.DESK_SIZE
    assert small.size == (build.DESK_SMALL, build.DESK_SMALL * build.DESK_SIZE[1] // build.DESK_SIZE[0])
    width, height = large.size
    border = [large.getpixel((x, y)) for x in range(0, width, 16) for y in (0, 1, height - 2, height - 1)]
    border += [large.getpixel((x, y)) for y in range(0, height, 16) for x in (0, 1, width - 2, width - 1)]
    assert all(is_ground(pixel) for pixel in border)   # no edge shows: the border is the page itself
    centre = large.getpixel((width // 2, height // 2))
    assert all(abs(a - b) <= TOLERANCE for a, b in zip(centre, LAMPLIT))   # the picture keeps its colours


def test_a_missing_picture_is_an_error(tmp_path, capsys):
    assert desk.main([str(tmp_path / "nowhere.png")]) == 2
    assert "not a file" in capsys.readouterr().out


def test_a_file_that_is_not_a_picture_is_an_error(tmp_path, capsys):
    notes = tmp_path / "notes.png"
    notes.write_text("not a picture", encoding="utf-8")
    assert desk.main([str(notes), "--out", str(tmp_path / "out")]) == 2
    assert "notes.png is not a picture" in capsys.readouterr().out


def all_spots() -> dict[str, tuple[float, ...]]:
    """Every object marked, side by side; the tape lies on the lamplit patch of the test picture."""
    spots = {item.key: (4.0 + 10 * index, 70.0, 8.0, 12.0) for index, item in enumerate(build.DESK)}
    return spots | {"tape": (42.0, 42.0, 16.0, 16.0)}


def test_every_marked_object_becomes_a_tile(tmp_path):
    written = desk.tiles(photo(tmp_path / "escritorio.png"), tmp_path / "out", all_spots())
    assert [path.name for path in written] == [build.tile_name(item.key) for item in build.DESK]
    for path in written:
        assert Image.open(path).size == build.TILE_SIZE
    tape = Image.open(tmp_path / "out" / build.tile_name("tape")).convert("RGB")
    centre = tape.getpixel((tape.width // 2, tape.height // 2))
    assert all(abs(a - b) <= TOLERANCE for a, b in zip(centre, LAMPLIT))   # the tile is cut around its object
    corner = tape.getpixel((4, 4))
    assert not all(abs(a - b) <= TOLERANCE for a, b in zip(corner, LAMPLIT))   # with some of the desk around it


def test_a_tile_near_the_edge_stays_inside_the_picture(tmp_path):
    spots = all_spots() | {"passport": (0.0, 90.0, 6.0, 10.0)}
    written = desk.tiles(photo(tmp_path / "escritorio.png"), tmp_path / "out", spots)
    assert Image.open(written[0]).size == build.TILE_SIZE


def test_details_are_cut_where_the_marks_say(tmp_path):
    marks = {"chart": (40.0, 40.0, 20.0, 20.0), "yard": (0.0, 0.0, 20.0, 30.0)}
    written = desk.details(photo(tmp_path / "escritorio.png"), tmp_path / "out", marks)
    assert [path.name for path in written] == [build.detail_name(name) for name in build.DESK_DETAILS]
    chart, yard = (Image.open(path).convert("RGB") for path in written)
    assert chart.size == build.DETAIL_SIZES["chart"] and yard.size == build.DETAIL_SIZES["yard"]
    centre = lambda image: image.getpixel((image.width // 2, image.height // 2))  # noqa: E731
    assert all(abs(a - b) <= TOLERANCE for a, b in zip(centre(chart), LAMPLIT))       # cut on the lamplit patch
    assert not all(abs(a - b) <= TOLERANCE for a, b in zip(centre(yard), LAMPLIT))    # cut away from it


def test_a_detail_left_unmarked_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="no mark for the detail yard"):
        desk.details(photo(tmp_path / "escritorio.png"), tmp_path / "out", {"chart": (40.0, 40.0, 20.0, 20.0)})


def test_the_script_writes_every_file_the_home_page_waits_for(tmp_path, monkeypatch, capsys):
    marks = tmp_path / "desk.json"
    marks.write_text(json.dumps({"spots": {key: list(box) for key, box in all_spots().items()},
                                 "details": {"chart": [40, 40, 20, 20], "yard": [0, 0, 20, 30]}}), encoding="utf-8")
    monkeypatch.setattr(build, "DESK_SPOTS", marks)
    out = tmp_path / "out"
    assert desk.main([str(photo(tmp_path / "escritorio.png")), "--out", str(out)]) == 0
    assert sorted(path.name for path in out.iterdir()) == sorted(build.desk_files())
    assert "wrote" in capsys.readouterr().out


def test_without_marks_the_script_writes_the_picture_and_says_what_is_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(build, "DESK_SPOTS", tmp_path / "desk.json")
    out = tmp_path / "out"
    assert desk.main([str(photo(tmp_path / "escritorio.png")), "--out", str(out)]) == 1
    assert sorted(path.name for path in out.iterdir()) == [build.desk_name(small=True), build.desk_name()]
    assert "mark where each object lies" in capsys.readouterr().out


def test_marks_are_checked_before_anything_is_written(tmp_path, monkeypatch, capsys):
    marks = tmp_path / "desk.json"
    marks.write_text('{"spots": {"hammer": [1, 2, 3, 4]}}', encoding="utf-8")
    monkeypatch.setattr(build, "DESK_SPOTS", marks)
    out = tmp_path / "out"
    assert desk.main([str(photo(tmp_path / "escritorio.png")), "--out", str(out)]) == 2
    assert not out.exists() or not list(out.iterdir())   # the picture on the site is not replaced
    assert "desk.json: unknown object 'hammer'" in capsys.readouterr().out


def test_a_new_picture_without_marks_takes_the_old_tiles_away(tmp_path, monkeypatch, capsys):
    """Tiles cut from an earlier picture must not be published beside a new one."""
    monkeypatch.setattr(build, "DESK_SPOTS", tmp_path / "desk.json")
    out = tmp_path / "out"
    out.mkdir()
    for name in build.desk_files():
        (out / name).write_bytes(b"old")
    assert desk.main([str(photo(tmp_path / "escritorio.png")), "--out", str(out)]) == 1
    assert sorted(path.name for path in out.iterdir()) == [build.desk_name(small=True), build.desk_name()]
    assert Image.open(out / build.desk_name()).size == build.DESK_SIZE   # and the picture is the new one
    assert "removed 11 files cut from an earlier picture" in capsys.readouterr().out


def test_a_failed_write_is_not_blamed_on_the_picture(tmp_path, monkeypatch, capsys):
    def full_disk(image, path):
        raise OSError("No space left on device")

    monkeypatch.setattr(build, "DESK_SPOTS", tmp_path / "desk.json")
    monkeypatch.setattr(desk, "save", full_disk)
    assert desk.main([str(photo(tmp_path / "escritorio.png")), "--out", str(tmp_path / "out")]) == 2
    said = capsys.readouterr().out
    assert "could not write the desk" in said and "No space left on device" in said
    assert "is not a picture" not in said
