# esstipi-debug.github.io

Short field notes by Marcos Stipicich: one question per page, each with one mechanism and one source.

The site is generated. Edit `src/pages/*.md`, then run:

```bash
pip install -r requirements.txt
python build.py
python -m pytest
```

`build.py` writes the HTML at the repository root, together with `robots.txt`, `sitemap.xml` and `404.html`. Folders of pages that were removed from `src/pages/` are deleted on the next build.
