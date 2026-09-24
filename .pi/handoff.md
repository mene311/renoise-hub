# Renoise hub — handoff

## Mission
One landing page for every Renoise thing I've published on GitHub, generated from live
repository facts so the numbers don't rot.

Live: https://mene311.github.io/renoise-hub/  (repo `mene311/renoise-hub`, branch `master`, Pages from root)

## How it works
- `data.json` — copy, sections, links, tags. Hand-written; this is the part that needs taste.
- `build.py` — pulls last change / size / file counts from the GitHub API via `gh`, probes every
  linked site (HEAD, falling back to GET because some hosts reject HEAD), renders `index.html`.
- `facts.json` — cache of the last build, so `./build.py --offline` works without network.
- `./build.py --check` — renders, then HEADs every link in the page and fails on dead ones.
- `style.css` — the same tracker chrome as the wavetable tools pages (mono, sharp corners,
  one green accent). Tokens copied from `~/Projects/renoise/themes/public/css/style.css`.
- `.github/workflows/refresh.yml` — weekly rebuild + commit when numbers move.

## Adding something
Add an entry to `data.json` under `repos`, list its key in one of the section `items`, run
`./build.py`. Counts come from `facts` entries: `{"type": "tree_count", "ext": ".xrni",
"label": "instruments"}`. Entries that aren't their own repo (like the LFO presets, which live
inside the wavetable tools repo) need `"external": true`, a `static` list of chips, and no
`facts`.

## Verification used
Images aren't readable in this session (vision tool wants a session header), so the page was
checked by measuring: palette histogram is the chrome set, no element overflows the content
width, all four nav anchors resolve, and all 19 links on the deployed page return 200.

## Gotchas
- `gh api ... --jq '[..] | @tsv'` silently produced nothing in one shell; plain JSON + python worked.
- Topics API needs one `-f names[]=x` per topic, not a comma-joined string.
- Pages takes ~1 minute; a curl right after pushing returns the previous deploy, so check
  `gh api repos/mene311/renoise-hub/pages/builds/latest --jq .status` before believing a miss.
- `pkill -f "http.server 8099"` kills the calling shell too (the pattern matches its own command
  line). Use the listening pid or `[h]ttp.server`.

## Session changes beyond this repo
- Published 133 LFO presets + 133 modulation sets into `renoise-wavetable-tools/presets/`.
- Fixed the stale description and added topics on six repos; cross-linked the hub from the
  tools pages, tools README and instruments README.
