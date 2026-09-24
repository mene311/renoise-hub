# Renoise hub

A landing page for everything I've published for Renoise: instrument libraries, colour
themes, LFO shapes, and the tools that build them. It's one static page, served by GitHub
Pages at https://mene311.github.io/renoise-hub/.

## How it's put together

`data.json` holds the words: the hero copy, the four sections, and one entry per thing
published. Descriptions, tags and links are written by hand, because that's the part a
script can't guess.

`build.py` holds the numbers. It asks the GitHub API for each repository's last change,
size and file counts, probes every linked site to see if it still answers, and renders
`index.html`. Facts land in `facts.json`, so the page can also be rebuilt without a network:

```sh
./build.py              # refresh facts from GitHub, then render
./build.py --offline    # render from the cached facts
./build.py --check      # render, then HEAD every link and report dead ones
```

`style.css` is the same tracker chrome the wavetable tools pages use: monospace, sharp
corners, one green accent on a mostly grey palette.

## Keeping it current

`.github/workflows/refresh.yml` runs the build weekly and commits when the numbers move, so
counts and dates don't rot. Add a repository by putting it in `data.json`; the numbers take
care of themselves.
