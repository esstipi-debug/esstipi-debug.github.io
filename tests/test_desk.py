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


def test_details_are_cut_where_the_marks_say(tmp_path):
    centre = lambda image: image.getpixel((image.width // 2, image.height // 2))  # noqa: E731
    for box, lamplit in (((40.0, 40.0, 20.0, 20.0), True), ((0.0, 0.0, 20.0, 30.0), False)):
        written = desk.details(photo(tmp_path / "escritorio.png"), tmp_path / "out", {"yard": box})
        assert [path.name for path in written] == [build.detail_name(name) for name in build.DESK_DETAILS]
        yard = Image.open(written[0]).convert("RGB")
        assert yard.size == build.DETAIL_SIZES["yard"]
        on_patch = all(abs(a - b) <= TOLERANCE for a, b in zip(centre(yard), LAMPLIT))
        assert on_patch == lamplit   # cut where the mark says, on the lamplit patch or away from it


def test_a_detail_left_unmarked_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="no mark for the detail yard"):
        desk.details(photo(tmp_path / "escritorio.png"), tmp_path / "out", {})


def test_the_script_writes_every_desk_and_detail_file_and_clears_stale_tiles(tmp_path, monkeypatch, capsys):
    marks = tmp_path / "desk.json"
    marks.write_text(json.dumps({"details": {"yard": [0, 0, 20, 30]}}), encoding="utf-8")
    monkeypatch.setattr(build, "DESK_SPOTS", marks)
    out = tmp_path / "out"
    out.mkdir()
    (out / "kit-tape.webp").write_bytes(b"stale")
    (out / "kit-boots.webp").write_bytes(b"stale")
    assert desk.main([str(photo(tmp_path / "escritorio.png")), "--out", str(out)]) == 0
    expected = build.hero_desk_files() + build.detail_files()
    assert sorted(path.name for path in out.iterdir()) == sorted(expected)
    said = capsys.readouterr().out
    assert "wrote" in said
    assert "removed 2 stale kit tile(s)" in said


def test_only_details_writes_yard_without_creating_hero_desk(tmp_path, monkeypatch, capsys):
    marks = tmp_path / "desk.json"
    marks.write_text(json.dumps({"details": {"yard": [40, 40, 20, 20]}}), encoding="utf-8")
    monkeypatch.setattr(build, "DESK_SPOTS", marks)
    out = tmp_path / "out"
    out.mkdir()
    (out / "kit-camera.webp").write_bytes(b"stale")
    assert desk.main([str(photo(tmp_path / "escritorio.png")), "--out", str(out), "--only", "details"]) == 0
    assert sorted(path.name for path in out.iterdir()) == sorted(build.detail_files())
    said = capsys.readouterr().out
    assert "yard.webp" in said
    assert "removed 1 stale kit tile(s)" in said


def test_only_hero_works_without_detail_marks(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(build, "DESK_SPOTS", tmp_path / "desk.json")
    out = tmp_path / "out"
    assert desk.main([str(photo(tmp_path / "escritorio.png")), "--out", str(out), "--only", "hero"]) == 0
    assert sorted(path.name for path in out.iterdir()) == sorted(build.hero_desk_files())
    assert "ready; now run: python build.py" in capsys.readouterr().out


def test_without_marks_the_script_writes_hero_and_clears_stale_details(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(build, "DESK_SPOTS", tmp_path / "desk.json")
    out = tmp_path / "out"
    out.mkdir()
    (out / "yard.webp").write_bytes(b"old")
    (out / "kit-passport.webp").write_bytes(b"old")
    assert desk.main([str(photo(tmp_path / "escritorio.png")), "--out", str(out)]) == 1
    assert sorted(path.name for path in out.iterdir()) == sorted(build.hero_desk_files())
    assert Image.open(out / build.desk_name()).size == build.DESK_SIZE
    said = capsys.readouterr().out
    assert "removed 1 stale kit tile(s)" in said
    assert "removed 1 stale detail file(s)" in said
    assert "now mark the details" in said


def test_marks_are_checked_before_anything_is_written(tmp_path, monkeypatch, capsys):
    marks = tmp_path / "desk.json"
    marks.write_text('{"details": {"window": [1, 2, 3, 4]}}', encoding="utf-8")
    monkeypatch.setattr(build, "DESK_SPOTS", marks)
    out = tmp_path / "out"
    assert desk.main([str(photo(tmp_path / "escritorio.png")), "--out", str(out)]) == 2
    assert not out.exists() or not list(out.iterdir())   # existing site assets stay untouched
    assert "desk.json: unknown detail 'window'" in capsys.readouterr().out


def test_a_failed_write_is_not_blamed_on_the_picture(tmp_path, monkeypatch, capsys):
    def full_disk(image, path):
        raise OSError("No space left on device")

    monkeypatch.setattr(build, "DESK_SPOTS", tmp_path / "desk.json")
    monkeypatch.setattr(desk, "save", full_disk)
    assert desk.main([str(photo(tmp_path / "escritorio.png")), "--out", str(tmp_path / "out")]) == 2
    said = capsys.readouterr().out
    assert "could not write the desk" in said and "No space left on device" in said
    assert "is not a picture" not in said
