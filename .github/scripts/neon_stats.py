#!/usr/bin/env python3
"""Generates neon SVGs (commit activity chart + trophies) from your GitHub data.
Runs inside GitHub Actions with the built-in GITHUB_TOKEN; no external services needed.
Usage: python neon_stats.py            -> fetch real data
       python neon_stats.py --offline  -> write placeholders (no network)"""
import json, os, sys, urllib.request, html
from datetime import date

BG2, LINE = "#0A0C1C", "#1A1F3D"
CY, MG, VI, GR, YE, OR = "#00E5FF", "#FF3DCB", "#9D5CFF", "#39FF88", "#FFD60A", "#FF9F1C"
TXT, MUT = "#E6E9FF", "#8A93C2"
SANS = "Inter,'Segoe UI',-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif"
MONO = "'JetBrains Mono','SF Mono',SFMono-Regular,Consolas,'Liberation Mono',monospace"
GLOW = '<filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "generated")

QUERY = """query($login:String!){user(login:$login){
 followers{totalCount}
 repositories(ownerAffiliations:OWNER,isFork:false,first:100,privacy:PUBLIC){totalCount nodes{stargazerCount}}
 contributionsCollection{totalCommitContributions totalIssueContributions totalPullRequestContributions totalPullRequestReviewContributions
  contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""

def fetch(login, token):
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "neon-stats"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    if "errors" in d or not d.get("data", {}).get("user"):
        raise SystemExit(f"GraphQL error: {d.get('errors')}")
    u = d["data"]["user"]; cc = u["contributionsCollection"]; cal = cc["contributionCalendar"]
    return dict(
        weeks=[[(x["date"], x["contributionCount"]) for x in w["contributionDays"]] for w in cal["weeks"]],
        total=cal["totalContributions"], commits=cc["totalCommitContributions"], prs=cc["totalPullRequestContributions"],
        issues=cc["totalIssueContributions"], reviews=cc["totalPullRequestReviewContributions"],
        repos=u["repositories"]["totalCount"], stars=sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        followers=u["followers"]["totalCount"], live=True)

def empty():
    return dict(weeks=[], total=0, commits=0, prs=0, issues=0, reviews=0, repos=0, stars=0, followers=0, live=False)

def activity_svg(d):
    W, H = 840, 320
    x0, x1, yb, yt = 48, 800, 262, 100
    weeks = d["weeks"]
    sums = [sum(c for _, c in w) for w in weeks] or [0] * 52
    mx = max(max(sums), 1)
    n = len(sums)
    pts = [(x0 + (x1 - x0) * i / max(n - 1, 1), yb - (yb - yt) * s / mx) for i, s in enumerate(sums)]
    path = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for (xa, ya), (xb, yb2) in zip(pts, pts[1:]):
        dx = (xb - xa) / 2
        path += f" C{xa+dx:.1f} {ya:.1f} {xb-dx:.1f} {yb2:.1f} {xb:.1f} {yb2:.1f}"
    area = path + f" L{pts[-1][0]:.1f} {yb} L{pts[0][0]:.1f} {yb} Z"
    peak = max(range(n), key=lambda i: sums[i]); px, py = pts[peak]
    days = [c for w in weeks for _, c in w]
    best = max(days) if days else 0
    active = sum(1 for c in days if c > 0)
    avg = (sum(sums) / n) if n else 0
    grid = ""
    for k in range(4):
        y = yt + (yb - yt) * k / 3
        grid += f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="{LINE}"/>'
        grid += f'<text x="{x0-8}" y="{y+4:.1f}" text-anchor="end" font-family="{MONO}" font-size="10" fill="{MUT}">{round(mx*(1-k/3))}</text>'
    labels, last = "", None
    for i, w in enumerate(weeks):
        m = int(w[0][0][5:7])
        if m != last and (i == 0 or i < n - 2):
            labels += f'<text x="{pts[i][0]:.1f}" y="284" font-family="{MONO}" font-size="10" fill="{MUT}">{MONTHS[m-1]}</text>'
        last = m
    sub = f"Last 12 months  ·  {d['total']} contributions" if d["live"] else "Updates automatically with GitHub Actions"
    stat = lambda x, lab, val, c: (f'<text x="{x}" y="38" font-family="{MONO}" font-size="10" letter-spacing="1.5" fill="{MUT}">{lab}</text>'
                                    f'<text x="{x}" y="62" font-family="{SANS}" font-size="22" font-weight="800" fill="{c}" filter="url(#glow)">{val}</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none">
<defs>{GLOW}<linearGradient id="a" x1="0" y1="{yt}" x2="0" y2="{yb}" gradientUnits="userSpaceOnUse"><stop stop-color="{CY}" stop-opacity="0.38"/><stop offset="1" stop-color="{CY}" stop-opacity="0"/></linearGradient>
<linearGradient id="l" x1="{x0}" x2="{x1}" gradientUnits="userSpaceOnUse"><stop stop-color="{CY}"/><stop offset="1" stop-color="{MG}"/></linearGradient></defs>
<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="18" fill="{BG2}" stroke="{LINE}"/>
<text x="28" y="40" font-family="{SANS}" font-size="18" font-weight="700" fill="{TXT}">Commits &amp; Contributions</text>
<text x="28" y="62" font-family="{MONO}" font-size="11.5" fill="{MUT}">{html.escape(sub)}</text>
{stat(480, "BEST DAY", best, CY)}{stat(590, "AVG / WEEK", f"{avg:.1f}", MG)}{stat(710, "ACTIVE DAYS", active, GR)}
{grid}<path d="{area}" fill="url(#a)"/>
<path d="{path}" stroke="url(#l)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)"/>
<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{MG}" filter="url(#glow)"/>{labels}</svg>'''

def rank(v, th):
    r = "-"
    for letter, t in zip("CBAS", th):
        if v >= t: r = letter
    return r

def trophies_svg(d):
    items = [("COMMITS", d["commits"], (10, 50, 200, 500), CY), ("PULL REQ", d["prs"], (1, 10, 30, 100), MG),
             ("ISSUES", d["issues"], (1, 5, 20, 50), VI), ("REVIEWS", d["reviews"], (1, 5, 20, 50), GR),
             ("REPOS", d["repos"], (3, 10, 25, 50), YE), ("STARS", d["stars"], (1, 10, 50, 200), OR),
             ("FOLLOWERS", d["followers"], (1, 10, 50, 100), CY)]
    import math
    body = ""
    for i, (lab, v, th, c) in enumerate(items):
        cx, cy, r = 62 + i * 119, 54, 30
        hexp = " ".join(f"{cx + r*math.cos(math.radians(-90+60*k)):.1f},{cy + r*math.sin(math.radians(-90+60*k)):.1f}" for k in range(6))
        rk = rank(v, th)
        body += (f'<polygon points="{hexp}" fill="{c}" fill-opacity="0.08" stroke="{c}" stroke-width="2" stroke-linejoin="round" filter="url(#glow)"/>'
                 f'<text x="{cx}" y="{cy+9}" text-anchor="middle" font-family="{SANS}" font-size="26" font-weight="800" fill="{c}" filter="url(#glow)">{rk}</text>'
                 f'<text x="{cx}" y="108" text-anchor="middle" font-family="{SANS}" font-size="18" font-weight="800" fill="{TXT}">{v}</text>'
                 f'<text x="{cx}" y="128" text-anchor="middle" font-family="{MONO}" font-size="10" letter-spacing="1.5" fill="{MUT}">{lab}</text>')
        if i: body += f'<line x1="{cx-59.5}" y1="26" x2="{cx-59.5}" y2="124" stroke="{LINE}"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="840" height="150" viewBox="0 0 840 150" fill="none"><defs>{GLOW}</defs>
<rect x="0.5" y="0.5" width="839" height="149" rx="18" fill="{BG2}" stroke="{LINE}"/>{body}</svg>'''

def write(d):
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "activity.svg"), "w", encoding="utf-8").write(activity_svg(d))
    open(os.path.join(OUT, "trophies.svg"), "w", encoding="utf-8").write(trophies_svg(d))

if __name__ == "__main__":
    if "--offline" in sys.argv:
        write(empty())
    else:
        login = os.environ.get("GH_LOGIN") or os.environ["GITHUB_REPOSITORY_OWNER"]
        write(fetch(login, os.environ["GITHUB_TOKEN"]))
    print("done")
