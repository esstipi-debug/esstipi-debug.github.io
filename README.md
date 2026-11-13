# esstipi-debug.github.io

Short field notes by Marcos Stipicich: one question per page, each with one mechanism and one source.

The site is generated. Edit `src/pages/*.md`, then run:

```bash
pip install -r requirements.txt
python build.py
python -m pytest
```

`build.py` writes the HTML at the repository root, together with `robots.txt`, `sitemap.xml` and `404.html`. Folders of pages that were removed from `src/pages/` are deleted on the next build. Files in `src/files/` (the one-page plan, the two fonts and the pictures of the desk) are copied to `files/`.

## Page types

| `type` | What it is | Keys beyond the required ones |
|---|---|---|
| `home` | The home page: the headline with the desk beside it, the symptoms and the three situations, three figures, the method, the nine objects of the desk, the argument, the doors, then the field notes | `headline`, `lede` (twenty words at most), repeated `symptom`, optional `kicker`, `base_line`, `secondary: label \| slug`, `subject` |
| `landing` | An entry page for one situation, one floor or one kind of buyer, shown as a door on the home page | `group: situation`, `floor` or `buyer`, `door`, `door_text`, `kicker`, `subject` |
| `page` | Engagements, how I work, proof, working terms, contact | optional `headline`, `kicker`, `subject`, `cta`, repeated `offer: name \| amount in USD \| unit` |
| `question`, `note`, `author`, `book` | The field notes, the author page and the manuscript | see the existing pages |

Every landing page carries the same four sections: *What I check first*, *Where I have stood*, *What I don't claim* and *How we would start*. Every commercial page ends with one contact button, an email whose subject line is the page's `subject`.

The home page asks first what is happening, not who the visitor is: under the hero it names the symptoms (`symptom` in the front matter, one sentence each) and then the three situation doors; the doors by floor and by kind of buyer come lower. A situation page adds a fifth section, *What each of you will ask first*, with one question each from finance, operations and the chief executive, so the page can be forwarded.

The desk is a picture of the kit laid out the night before a visit, with nine objects that describe the work. The home page shows it beside the headline, with a line under it that says it is an illustration, and lower down shows the nine objects as a strip of tiles: each one says what it means for the work, the limit it works under on a client's site, and leads to its page. `python desk.py <picture>` cuts the picture to 16:9, fades its edges into the page and writes it twice to `src/files/desk/`; then, from the marks in `src/desk.json`, it cuts a tile around each object and the two details the page uses (`chart.webp` and `yard.webp`). A mark is left, top, width and height in percent, under `spots` for the objects and `details` for the two details. The objects and their texts are `DESK` in `build.py`. Until every file exists, the home page shows no picture and no strip, and still stands.

The method section of the home page is three panels, *Measure*, *Cut* and *Stitch* (`METHOD_STEPS` in `build.py`), that stack as the page is read. It needs no picture. `plates.py` still turns generated scenes into two-colour plates (`python plates.py <folder>`, from images named `escena-1.png` to `escena-4.png`), but the home page does not show them at present. Pillow is needed only by `plates.py`, `desk.py` and their tests.

`build.py` holds the pages, the data and the helpers; `home.py` lays the home page out. `src/style.css` is the whole site and `src/home.css` only the home page. Both are dark only, with one accent and no rounded corners; what moves does so with CSS and stops under `prefers-reduced-motion`. The two typefaces, Archivo and JetBrains Mono (both under the SIL Open Font License), are in `src/files/fonts/`: no page asks another host for a font.

`tests/test_commercial.py` holds the rules for the commercial pages: prices only on the engagements page and only in USD, the employer named once and only on the proof page, no banned words, one voice (the site speaks as "I", never as a firm's "we"), the *Who to hire for what* table on the engagements page, the home page from top to bottom (a hero that fits a first screen, three figures each with its page, the desk: every object has a tile that leads to its page, no maker is named), no script on any page, fonts served by the site itself, and `FIGURES`, the list of every number a commercial page may print with its source. A new number fails the tests until it is added there.
