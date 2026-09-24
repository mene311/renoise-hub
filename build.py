#!/usr/bin/env python3
"""Build the Renoise hub page.

Reads data.json (the curated copy, links and grouping) and, unless --offline is
passed, refreshes facts.json from the GitHub API: repository metadata, file
counts inside each repo, and whether the Pages site answers.

    ./build.py              refresh facts, then render index.html
    ./build.py --offline    render from the cached facts.json (no network)
    ./build.py --check      also HEAD every link in the rendered page
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OWNER = "mene311"
FACTS = ROOT / "facts.json"


# ── GitHub access ────────────────────────────────────────────────────────────


def gh(path: str) -> dict:
    """Call the GitHub API through the gh CLI, which already holds a token."""
    out = subprocess.run(
        ["gh", "api", path], capture_output=True, text=True, check=False
    )
    if out.returncode != 0:
        raise RuntimeError(f"gh api {path} failed: {out.stderr.strip()[:200]}")
    return json.loads(out.stdout)


def tree_of(repo: str, branch: str) -> list[str]:
    data = gh(f"repos/{OWNER}/{repo}/git/trees/{branch}?recursive=1")
    return [node["path"] for node in data.get("tree", []) if node["type"] == "blob"]


def url_alive(url: str) -> bool:
    """HEAD first; some hosts reject HEAD, so fall back to a one-byte GET."""
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": "renoise-hub-build"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status < 400:
                    return True
        except (urllib.error.URLError, TimeoutError, ValueError):
            continue
    return False


def refresh(data: dict) -> dict:
    facts: dict[str, dict] = {}
    for repo in (r for section in data["sections"] for r in section["items"]):
        entry = data["repos"].get(repo)
        if entry is None:
            continue
        if entry.get("external"):
            continue
        meta = gh(f"repos/{OWNER}/{repo}")
        branch = meta["default_branch"]
        paths = tree_of(repo, branch)
        counts = {}
        for fact in entry.get("facts", []):
            if fact["type"] == "tree_count":
                ext = fact["ext"]
                counts[ext] = sum(1 for p in paths if p.endswith(ext))
        facts[repo] = {
            "pushed": meta["pushed_at"][:10],
            "created": meta["created_at"][:10],
            "size_mb": round(meta["size"] / 1024, 1),
            "stars": meta["stargazers_count"],
            "branch": branch,
            "license": (meta.get("license") or {}).get("spdx_id"),
            "counts": counts,
            "has_pages": meta["has_pages"],
        }
        print(f"  {repo}: {counts or '-'} pushed {facts[repo]['pushed']}")
    sites: dict[str, bool] = {}
    for entry in data["repos"].values():
        url = entry.get("links", {}).get("site")
        if url and url not in sites:
            sites[url] = url_alive(url)
    facts["_sites"] = sites
    facts["_built"] = time.strftime("%Y-%m-%d %H:%M")
    return facts


# ── rendering ────────────────────────────────────────────────────────────────


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def fact_chips(repo: str, entry: dict, facts: dict) -> str:
    live = facts.get(repo, {})
    chips: list[tuple[str, str]] = []
    for fact in entry.get("facts", []):
        if fact["type"] == "tree_count":
            n = (live.get("counts") or {}).get(fact["ext"])
            if n:
                chips.append((f"{n:,}", fact["label"]))
    if live.get("size_mb"):
        chips.append((f"{live['size_mb']:g} MB", "repository"))
    if live.get("pushed"):
        chips.append((live["pushed"], "last change"))
    for text in entry.get("static", []):
        chips.append((text, ""))
    if live.get("stars"):
        chips.append((str(live["stars"]), "star" + ("" if live["stars"] == 1 else "s")))
    out = []
    for value, label in chips:
        if label:
            out.append(
                f'<span class="fact"><b>{esc(value)}</b> {esc(label)}</span>'
            )
        else:
            out.append(f'<span class="fact">{esc(value)}</span>')
    return "".join(out)


def card(repo: str, entry: dict, facts: dict) -> str:
    live = facts.get(repo, {})
    links = []
    site = entry.get("links", {}).get("site")
    if site and facts.get("_sites", {}).get(site, True):
        links.append(("open", site))
    for key, label in (("tool", "Renoise tool"), ("zip", "download .zip")):
        if entry.get("links", {}).get(key):
            links.append((label, entry["links"][key]))
    links.append(("source", entry["links"]["repo"]))
    link_html = "".join(
        f'<a href="{esc(url)}">{esc(label)}</a>' for label, url in links
    )
    tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in entry.get("tags", []))
    return f"""      <article class="card">
        <h3>{esc(entry['name'])}</h3>
        <p>{entry['blurb']}</p>
        <div class="facts">{fact_chips(repo, entry, facts)}</div>
        <div class="links">{link_html}</div>
        <div class="tags">{tags}</div>
      </article>"""


def render(data: dict, facts: dict) -> str:
    sections = []
    for section in data["sections"]:
        cards = "\n".join(
            card(repo, data["repos"][repo], facts)
            for repo in section["items"]
            if repo in data["repos"]
        )
        sections.append(
            f"""  <section class="panel" id="{section['id']}">
    <div class="panel-head">
      <h2>{esc(section['title'])}</h2>
      <span class="hint">{esc(section['blurb'])}</span>
    </div>
    <div class="panel-body">
      <div class="cards">
{cards}
      </div>
    </div>
  </section>"""
        )

    built = facts.get("_built", "cached facts")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Renoise hub — instruments, themes and tools</title>
<meta name="description" content="Everything I've published for Renoise: wavetable instruments, colour themes, LFO shapes, and the tools that build them.">
<link rel="stylesheet" href="style.css">
</head>
<body>
<div class="site-header"><div class="header-inner">
<a class="logo" href="./"><span class="logo-text">renoise<strong>&#183;</strong>hub</span></a>
<nav class="site-nav">
<a href="#sound">Sound</a>
<a href="#tools">Tools</a>
<a href="#themes">Themes</a>
<a href="#archives">Archives</a>
<a href="https://github.com/{OWNER}">GitHub</a>
</nav>
</div></div>

<div class="hero"><div class="hero-inner">
<h1>{data['hero']['heading']}</h1>
<p>{data['hero']['lede']}</p>
</div></div>

<main>
{chr(10).join(sections)}
</main>

<footer>
  <span>{esc(data['footer']['line'])}</span>
  <span>facts refreshed {esc(built)}</span>
</footer>
</body>
</html>
"""


# ── link checking ────────────────────────────────────────────────────────────


def check_links(html: str) -> int:
    import re

    urls = sorted(set(re.findall(r'href="(https?://[^"]+)"', html)))
    bad = 0
    for url in urls:
        try:
            req = urllib.request.Request(
                url, method="HEAD", headers={"User-Agent": "renoise-hub-build"}
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                code = resp.status
        except urllib.error.HTTPError as exc:
            code = exc.code
        except (urllib.error.URLError, TimeoutError) as exc:
            code = str(exc)[:40]
        flag = "ok " if str(code).startswith("2") or str(code) == "301" else "BAD"
        if flag == "BAD":
            bad += 1
        print(f"  [{flag}] {code} {url}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use cached facts.json")
    ap.add_argument("--check", action="store_true", help="HEAD every link afterwards")
    args = ap.parse_args()

    data = json.loads((ROOT / "data.json").read_text())
    if args.offline:
        facts = json.loads(FACTS.read_text()) if FACTS.exists() else {}
        print("  using cached facts")
    else:
        print("refreshing facts from GitHub")
        try:
            facts = refresh(data)
        except Exception as exc:  # keep the page buildable without network
            print(f"  refresh failed ({exc}); falling back to cached facts")
            facts = json.loads(FACTS.read_text()) if FACTS.exists() else {}
        else:
            FACTS.write_text(json.dumps(facts, indent=2, sort_keys=True) + "\n")

    html = render(data, facts)
    (ROOT / "index.html").write_text(html)
    print(f"  wrote index.html ({len(html):,} bytes)")

    if args.check:
        print("checking links")
        bad = check_links(html)
        print(f"  {bad} bad link(s)")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
