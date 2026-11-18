import json
import os
import random
import string
import sys
import urllib.request
from xml.sax.saxutils import escape

QUERY = """
query($login: String!) {
  user(login: $login) {
    pullRequests { totalCount }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}"""

COLOURS = ["#4D9DE0", "#F7C548", "#3BB273", "#FF7A45", "#A78BFA", "#2EC4B6"]
W, H = 495, 206
COLS, CW, CH, GAP, ROW_GAP = 20, 21, 26, 3, 5
LEFT, TOP = (W - (COLS * (CW + GAP) - GAP)) // 2, 44


def fetch(login):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}"},
    )
    user = json.load(urllib.request.urlopen(req))["data"]["user"]
    contribs = user["contributionsCollection"]
    calendar = contribs["contributionCalendar"]

    days = sorted((d for w in calendar["weeks"] for d in w["contributionDays"]), key=lambda d: d["date"])
    streak = best = 0
    for d in days:
        streak = streak + 1 if d["contributionCount"] else 0
        best = max(best, streak)

    sizes = {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            sizes[name] = sizes.get(name, 0) + edge["size"]
    total = sum(sizes.values()) or 1

    return {
        "commits": contribs["totalCommitContributions"],
        "prs": user["pullRequests"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in user["repositories"]["nodes"]),
        "streak": best,
        "contributions": calendar["totalContributions"],
        "languages": sorted(((n, s / total * 100) for n, s in sizes.items()), key=lambda x: -x[1]),
    }


def board(title, rows):
    rnd = random.Random(title)
    glyphs = string.ascii_uppercase + string.digits
    cells = []
    for r, (label, value, colour) in enumerate(rows):
        text = label.ljust(COLS - len(value))[:COLS - len(value)] + value
        for c, char in enumerate(text):
            lit = c >= COLS - len(value) and char != " "
            bg, fg = (colour, "#0b0d12") if lit else ("#1c1d24", "#8d8a84")
            strip = [rnd.choice(glyphs) for _ in range(6)] + [char]
            letters = "".join(
                f'<text x="{CW / 2}" y="{i * CH + CH * .72}" text-anchor="middle" fill="{fg}">{escape(g.strip())}</text>'
                for i, g in enumerate(strip))
            cells.append(
                f'<svg x="{LEFT + c * (CW + GAP)}" y="{TOP + r * (CH + ROW_GAP)}" width="{CW}" height="{CH}">'
                f'<rect width="{CW}" height="{CH}" rx="2.5" fill="{bg}"/>'
                f'<g class="flip" style="animation-delay:{r * .2 + c * .03:.2f}s">{letters}</g>'
                f'<rect y="{CH / 2 - .5}" width="{CW}" height="1" fill="#0b0d12" opacity=".55"/></svg>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<style>
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:15px;font-weight:700}}
.title{{font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;font-size:16px;fill:#FF69B4}}
.flip{{animation:flip 14s infinite}}
@keyframes flip{{0%{{transform:translateY(0);animation-timing-function:steps(6,end)}}4.5%,100%{{transform:translateY(-{6 * CH}px)}}}}
</style>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="6" fill="#111218" stroke="#30363d"/>
<text x="{LEFT}" y="30" class="title">{title}</text>
{"".join(cells)}
</svg>'''


def main(login, out_dir):
    s = fetch(login)
    stats = [
        ("COMMITS", str(s["commits"])),
        ("CONTRIBS", str(s["contributions"])),
        ("PULL REQS", str(s["prs"])),
        ("STARS", str(s["stars"])),
        ("BEST STREAK", f"{s['streak']}D"),
    ]
    langs = [(name.upper()[:11], f"{pct:.0f}%" if pct >= 1 else "<1%") for name, pct in s["languages"][:5]]

    with open(f"{out_dir}/stats.svg", "w") as f:
        f.write(board("GitHub Stats", [(l, v, COLOURS[i]) for i, (l, v) in enumerate(stats)]))
    with open(f"{out_dir}/languages.svg", "w") as f:
        f.write(board("Most Used Languages", [(l, v, COLOURS[i]) for i, (l, v) in enumerate(langs)]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
