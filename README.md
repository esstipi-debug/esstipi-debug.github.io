# esstipi-debug.github.io

Short field notes by Marcos Stipicich: one question per page, each with one mechanism and one source.

The site is generated. Edit `src/pages/*.md`, then run:

```bash
pip install -r requirements.txt
python build.py
python -m pytest
```

`build.py` writes the HTML at the repository root, together with `robots.txt`, `sitemap.xml` and `404.html`. Folders of pages that were removed from `src/pages/` are deleted on the next build. Files in `src/files/` (the one-page plan) are copied to `files/`.

## Page types

| `type` | What it is | Keys beyond the required ones |
|---|---|---|
| `home` | The home page: hero, doors to the landing pages, the argument, then the field notes | `headline`, `lede`, optional `kicker`, `base_line`, `secondary: label \| slug`, `subject` |
| `landing` | An entry page for one situation, one floor or one kind of buyer, shown as a door on the home page | `group: situation`, `floor` or `buyer`, `door`, `door_text`, `kicker`, `subject` |
| `page` | Engagements, how I work, proof, working terms, contact | optional `headline`, `kicker`, `subject`, `cta`, repeated `offer: name \| amount in USD \| unit` |
| `question`, `note`, `author`, `book` | The field notes, the author page and the manuscript | see the existing pages |

Every landing page carries the same four sections: *What I check first*, *Where I have stood*, *What I don't claim* and *How we would start*. Every commercial page ends with one contact button, an email whose subject line is the page's `subject`.

The home page asks first what is happening, not who the visitor is: the three situation doors stand alone under the hero, and the doors by floor and by kind of buyer come lower. A situation page adds a fifth section, *What each of you will ask first*, with one question each from finance, operations and the chief executive, so the page can be forwarded.

The method section of the home page shows three drawn tools. Once four plates exist in `src/files/plates/` (`scene-1.webp` to `scene-4.webp`, each also as `-800.webp`), it shows them instead, as four scenes. `python plates.py <folder>` writes them from generated images named `escena-1.png` to `escena-4.png`: it maps each one onto the page's two colours, so the picture has no visible edge. Pillow is needed only by that script and its tests.

`tests/test_commercial.py` holds the rules for the commercial pages: prices only on the engagements page and only in USD, the employer named once and only on the proof page, no banned words, one voice (the site speaks as "I", never as a firm's "we"), the *Who to hire for what* table on the engagements page, and `FIGURES`, the list of every number a commercial page may print with its source. A new number fails the tests until it is added there.
