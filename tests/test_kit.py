"""Checks on kit.py, the script that turns a photograph of an object into a figure of the kit plate."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
cv2 = pytest.importorskip("cv2")
pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build  # noqa: E402
import kit  # noqa: E402

PAPER = (236, 232, 226)   # a white sheet under window light, as OpenCV reads it (blue, green, red)
GREY = (105, 100, 95)     # an object
SIDE = 1200


def sheet() -> np.ndarray:
    return np.full((SIDE, SIDE, 3), PAPER, np.uint8)


def with_shadow(photo: np.ndarray, centre: tuple[int, int], radius: int, depth: int = 70) -> np.ndarray:
    """Darkens the sheet under a soft-edged blot, the way an object's shadow does."""
    blot = np.zeros(photo.shape[:2], np.float32)
    cv2.circle(blot, centre, radius, 1.0, -1)
    blot = cv2.GaussianBlur(blot, (0, 0), radius / 2.5)
    return np.clip(photo.astype(np.float32) - depth * blot[..., None], 0, 255).astype(np.uint8)


def photo_of_two(path: Path) -> Path:
    photo = sheet()
    cv2.circle(photo, (350, 600), 150, (160, 155, 150), -1)
    cv2.circle(photo, (310, 560), 60, (220, 218, 215), -1)   # a lit patch, so there is something to hatch
    cv2.rectangle(photo, (760, 380), (980, 860), GREY, -1)
    cv2.imwrite(str(path), photo)
    return path


def test_the_ink_is_the_accent_of_the_page():
    css = (build.SRC / "style.css").read_text(encoding="utf-8")
    accent = re.search(r"--accent:\s*#([0-9A-Fa-f]{6})", css).group(1)
    assert kit.INK == tuple(int(accent[index:index + 2], 16) for index in (0, 2, 4))


def test_an_object_is_found_and_its_shadow_stays_on_the_paper():
    photo = with_shadow(sheet(), (520, 520), 170)
    cv2.circle(photo, (640, 640), 120, GREY, -1)   # sharp-edged, and it covers part of its own shadow
    masks = kit.find_objects(photo)
    assert len(masks) == 1
    mask = masks[0]
    assert mask.shape == photo.shape[:2]
    assert mask[640, 640] and not mask[430, 430]   # the object, and the shadow beside it
    assert 0.9 < mask.sum() / (np.pi * 120 ** 2) < 1.15


def test_what_runs_off_the_sheet_is_not_an_object():
    photo = sheet()
    photo[:180] = (20, 30, 55)   # the dark table above the sheet
    cv2.circle(photo, (600, 700), 110, GREY, -1)
    masks = kit.find_objects(photo)
    assert len(masks) == 1
    assert masks[0][700, 600] and not masks[0][:180].any()


def test_objects_come_from_left_to_right():
    photo = sheet()
    cv2.circle(photo, (850, 400), 140, GREY, -1)   # the larger one is on the right
    cv2.rectangle(photo, (200, 700), (380, 900), (60, 60, 60), -1)
    left, right = kit.find_objects(photo)
    assert left[800, 290] and right[400, 850]


def test_a_ring_keeps_its_hole():
    photo = sheet()
    cv2.circle(photo, (600, 600), 170, (70, 70, 70), 46)
    (mask,) = kit.find_objects(photo)
    assert mask[600, 770] and not mask[600, 600]


def test_a_light_part_of_an_object_is_not_taken_for_a_hole():
    photo = sheet()
    cv2.circle(photo, (600, 600), 200, GREY, -1)
    cv2.circle(photo, (600, 600), 90, (222, 219, 214), -1)   # polished metal: nearly as light as the sheet
    (mask,) = kit.find_objects(photo)
    assert mask[600, 600]


def test_a_speck_on_the_sheet_is_not_an_object():
    photo = sheet()
    cv2.circle(photo, (600, 600), 120, GREY, -1)
    cv2.circle(photo, (200, 200), 6, (40, 40, 40), -1)
    assert len(kit.find_objects(photo)) == 1


def test_a_figure_is_one_ink_on_nothing():
    photo = sheet()
    cv2.circle(photo, (600, 600), 200, (160, 155, 150), -1)
    cv2.circle(photo, (540, 540), 90, (220, 218, 215), -1)   # a lit patch, so there is something to hatch
    (mask,) = kit.find_objects(photo)
    figure = kit.figure(photo, mask)
    assert figure.mode == "RGBA" and figure.size == (build.KIT_SIZE, build.KIT_SIZE)
    pixels = np.asarray(figure)
    assert (pixels[..., :3] == kit.INK).all()   # one ink: the drawing is its transparency
    alpha = pixels[..., 3]
    edge = build.KIT_SIZE // 40
    assert not (alpha[:edge].any() or alpha[-edge:].any() or alpha[:, :edge].any() or alpha[:, -edge:].any())
    assert alpha.max() > 200
    quarter = build.KIT_SIZE // 4
    middle = alpha[quarter:-quarter, quarter:-quarter]
    assert 0.1 < (middle > 128).mean() < 0.9   # hatched: neither empty nor one solid patch


def test_a_blanked_mark_is_smoothed_away_and_the_rest_is_kept():
    photo = np.full((400, 400, 3), 160, np.uint8)
    cv2.putText(photo, "MARK", (120, 215), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (20, 20, 20), 4)
    photo[10:30, 10:30] = 40   # something away from the mark
    clean = kit.without_marks(photo, [(200, 200, 110)])
    assert clean[150:250, 110:290].std() < photo[150:250, 110:290].std() / 4
    assert (clean[:60, :60] == photo[:60, :60]).all()


def test_a_photo_becomes_one_figure_per_object_in_two_sizes(tmp_path):
    first, second = (figure.key for figure in build.KIT[:2])
    written = kit.convert(photo_of_two(tmp_path / "photo.png"), [first, second], tmp_path / "out")
    assert [path.name for path in written] == [
        build.figure_name(first), build.figure_name(first, small=True),
        build.figure_name(second), build.figure_name(second, small=True)]
    for path, side in zip(written, (build.KIT_SIZE, build.KIT_SMALL) * 2):
        with Image.open(path) as image:
            assert image.size == (side, side) and image.mode == "RGBA", path.name
            alpha = np.asarray(image)[..., 3]
        assert alpha.max() > 200 and not alpha[0].any(), path.name


def test_a_photo_with_fewer_objects_than_names_is_an_error(tmp_path):
    names = [figure.key for figure in build.KIT[:3]]
    with pytest.raises(ValueError, match=r"photo\.png: 2 objects found, 3 figures named"):
        kit.convert(photo_of_two(tmp_path / "photo.png"), names, tmp_path / "out")


def test_a_figure_the_site_does_not_know_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="unknown figure 'hammer'"):
        kit.convert(photo_of_two(tmp_path / "photo.png"), [build.KIT[0].key, "hammer"], tmp_path / "out")


def manifest_for(folder: Path, photos: list[dict]) -> Path:
    path = folder / "objetos.json"
    path.write_text(json.dumps({"photos": photos}), encoding="utf-8")
    return path


def test_the_manifest_names_each_photo_and_its_figures(tmp_path, capsys):
    photo_of_two(tmp_path / "photo.png")
    first, second = (figure.key for figure in build.KIT[:2])
    manifest = manifest_for(tmp_path, [{"file": "photo.png", "figures": [first, second], "blank": [[350, 600, 40]]}])
    assert kit.main([str(manifest), "--out", str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / build.figure_name(second, small=True)).is_file()
    assert build.figure_name(first) in capsys.readouterr().out


def test_a_photo_that_fails_is_reported_and_the_others_still_run(tmp_path, capsys):
    photo_of_two(tmp_path / "photo.png")
    first, second, third = (figure.key for figure in build.KIT[:3])
    manifest = manifest_for(tmp_path, [{"file": "gone.png", "figures": [third]},
                                       {"file": "photo.png", "figures": [first, second]}])
    assert kit.main([str(manifest), "--out", str(tmp_path / "out")]) == 1
    assert "gone.png" in capsys.readouterr().out
    assert (tmp_path / "out" / build.figure_name(first)).is_file()


def test_a_missing_manifest_is_an_error(tmp_path, capsys):
    assert kit.main([str(tmp_path / "nowhere.json")]) == 2
    assert "not a file" in capsys.readouterr().out
