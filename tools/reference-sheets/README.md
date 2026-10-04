# Reference sheets

Licensed architectural references from Wikimedia Commons, for authoring review only.
Images download into `out/reference/` (never committed); the credits document is
committed under `docs/design/references/`.

```text
python tools/reference-sheets/fetch_commons.py   # themed searches -> out/reference/raw + manifest.json
python tools/reference-sheets/make_sheet.py      # reviewed picks -> out/reference/st_maria_chapel_references.png
python tools/reference-sheets/make_doc.py        # credits -> docs/design/references/st-maria-chapel.md
```

`fetch_commons.py` keeps only files whose licence is CC0, public domain, CC BY or
CC BY-SA, and records author, licence and source page for each. Picks in
`make_sheet.py` index that manifest, so re-fetching can renumber them: review the
candidates before regenerating. Its requests identify the project, not a person.
