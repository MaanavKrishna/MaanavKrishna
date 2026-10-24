#!/usr/bin/env python3
"""Draw the Activity card (stats.svg) from live GitHub data.

Runs in GitHub Actions (see .github/workflows/snake.yml) with GITHUB_TOKEN set:

    python3 scripts/build_stats.py dist

It replaces third-party stats services, which rate-limit and fail. The card uses
the same palette, fonts and helpers as build_assets.py.
"""
import json
import os
import sys
import urllib.request
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_assets as ba  # noqa: E402

LOGIN = os.environ.get("GITHUB_LOGIN", "MaanavKrishna")

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests(states: MERGED) { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount weekday } }
      }
    }
  }
}
"""


def fetch():
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]


def card(u):
    repos = u["repositories"]
    stars = sum(n["stargazerCount"] for n in repos["nodes"])
    langs = Counter()
    for n in repos["nodes"]:
        for e in n["languages"]["edges"]:
            langs[e["node"]["name"]] += e["size"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]

    INK, PAPER, HEAD, DIM = ba.INK, ba.PAPER, ba.HEAD, ba.DIM
    W, H = 1600, 600
    T, measure, fit = ba.T, ba.measure, ba.fit
    body = f'<rect width="{W}" height="{H}" rx="30" fill="{INK}"/>'
    body += T(52, 84, "Last 12 months,", "fx", 46, PAPER, ls=-1.8)
    body += T(52 + measure("Last 12 months,", "fx", 46, -1.8) + 14, 84, "straight from GitHub.", "fs", 50, DIM)
    body += T(W - 52, 80, "UPDATED DAILY", "fm", 12, DIM, "end", 2)

    stats = [(cal["totalContributions"], "CONTRIBUTIONS"), (repos["totalCount"], "PUBLIC REPOS"),
             (u["pullRequests"]["totalCount"], "PULL REQUESTS MERGED"), (stars, "STARS EARNED")]
    for i, (n, label) in enumerate(stats):
        x = 52 + i * 384
        body += f'<g class="fade" style="animation-delay:{0.1*i:.1f}s">'
        body += T(x - 3, 214, f"{n:,}", "fx", 96, PAPER, ls=-4)
        body += T(x, 252, label, "fm", 12, DIM, ls=2) + "</g>"
        if i:
            body += f'<line x1="{x-28}" y1="138" x2="{x-28}" y2="262" stroke="#2C2C2C"/>'
    body += f'<line x1="52" y1="292" x2="{W-52}" y2="292" stroke="#2C2C2C"/>'

    # contribution heatmap
    counts = sorted(d["contributionCount"] for w in weeks for d in w["contributionDays"] if d["contributionCount"] > 0)

    def level(c):
        if c == 0 or not counts:
            return 0
        q = [counts[int(len(counts) * f)] for f in (.25, .5, .75)]
        return 1 + sum(c > v for v in q)
    shades = ["#1E1E1E", "#1B2466", "#2236B3", "#3D5BFF", "#8C9CFF"]
    cell, gap = 13, 3
    hx, hy = 52, 336
    body += T(hx, 324, "CONTRIBUTION CALENDAR", "fm", 11, DIM, ls=2)
    for wi, w in enumerate(weeks[-53:]):
        for d in w["contributionDays"]:
            x = hx + wi * (cell + gap)
            y = hy + 10 + d["weekday"] * (cell + gap)
            body += (f'<rect class="cell" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{shades[level(d["contributionCount"])]}" '
                     f'style="animation-delay:{0.012*wi:.3f}s"/>')
    lx = hx + 53 * (cell + gap) - gap
    ly = hy + 10 + 7 * (cell + gap) + 24
    body += T(lx - 5 * 17 - 16, ly, "less", "fm", 11, DIM, "end")
    for k, s in enumerate(shades):
        body += f'<rect x="{lx - (5-k)*17}" y="{ly-11}" width="13" height="13" rx="3" fill="{s}"/>'
    body += T(lx + 8, ly, "more", "fm", 11, DIM)

    # languages
    total = sum(langs.values()) or 1
    top = langs.most_common(6)
    rx0 = 52 + 53 * (cell + gap) + 70
    rw = W - 52 - rx0
    body += T(rx0, 324, "LANGUAGES BY CODE SIZE", "fm", 11, DIM, ls=2)
    bar_shades = ["#5A72FF", "#8C9CFF", "#C6CEFF", PAPER, "#86827A", "#4A4A4A"]
    x = rx0
    for k, (name, size) in enumerate(top):
        w = rw * size / total
        body += f'<rect class="seg" x="{x:.1f}" y="346" width="{max(w-3, 2):.1f}" height="16" rx="3" fill="{bar_shades[k]}" style="animation-delay:{0.1*k:.1f}s"/>'
        x += w
    for k, (name, size) in enumerate(top):
        cx = rx0 + (k % 2) * (rw / 2)
        cy = 408 + (k // 2) * 40
        body += f'<rect x="{cx}" y="{cy-11}" width="12" height="12" rx="3" fill="{bar_shades[k]}"/>'
        body += T(cx + 22, cy, name, "fh", 19, PAPER, ls=-.2)
        body += T(cx + rw / 2 - 30, cy, f"{100*size/total:.1f}%", "fm", 13, DIM, "end")
    body += T(52, H - 40, f"{u['followers']['totalCount']} followers  /  github.com/{LOGIN}", "fm", 12, DIM, ls=1.5)
    css = (".cell{opacity:0;animation:fade .5s ease-out forwards}"
           ".seg{transform-box:fill-box;transform-origin:left;animation:seg 1s cubic-bezier(.65,0,.25,1) both}"
           "@keyframes seg{from{transform:scaleX(0)}to{transform:scaleX(1)}}")
    return ba.doc(W, H, body, css, f"GitHub activity: {cal['totalContributions']} contributions in the last year, "
                  f"{repos['totalCount']} public repos, {stars} stars. Top languages: {', '.join(n for n, _ in top)}.")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "dist"
    os.makedirs(out, exist_ok=True)
    ba.OUT = out
    ba.write("stats.svg", card(fetch()))
    print(f"wrote {out}/stats.svg")


if __name__ == "__main__":
    main()
