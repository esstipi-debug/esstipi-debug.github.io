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
| `landing` | An entry page for one floor or one kind of buyer, shown as a door on the home page | `group: floor` or `buyer`, `door`, `door_text`, `kicker`, `subject` |
| `page` | Engagements, how I work, proof, working terms, contact | optional `headline`, `kicker`, `subject`, `cta`, repeated `offer: name \| amount in USD \| unit` |
| `question`, `note`, `author`, `book` | The field notes, the author page and the manuscript | see the existing pages |

Every landing page carries the same four sections: *What I check first*, *Where I have stood*, *What I don't claim* and *How we would start*. Every commercial page ends with one contact button, an email whose subject line is the page's `subject`.

`tests/test_commercial.py` holds the rules for the commercial pages: prices only on the engagements page and only in USD, the employer named once and only on the proof page, no banned words, and `FIGURES`, the list of every number a commercial page may print with its source. A new number fails the tests until it is added there.
