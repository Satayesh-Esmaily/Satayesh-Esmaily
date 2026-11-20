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
 repositories(ownerAffiliations:OWNER,isFork:false,first:100,privacy:PUBLIC){totalCount nodes{stargazerCount languages(first:8,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}
 contributionsCollection{totalCommitContributions totalIssueContributions totalPullRequestContributions totalPullRequestReviewContributions
  contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""

def _langs(nodes):
    tot = {}
    for n in nodes:
        for e in n["languages"]["edges"]:
            tot[e["node"]["name"]] = tot.get(e["node"]["name"], 0) + e["size"]
    return sorted(tot.items(), key=lambda kv: -kv[1])

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
        followers=u["followers"]["totalCount"], langs=_langs(u["repositories"]["nodes"]), live=True)

def empty():
    return dict(weeks=[], total=0, commits=0, prs=0, issues=0, reviews=0, repos=0, stars=0, followers=0, langs=[], live=False)

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


def _shade(hexc, f):
    r, g, b = (int(hexc[i:i+2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % (int(r*f), int(g*f), int(b*f))

def skyline_svg(d):
    """Isometric neon 'city' where every day of the last year is a building."""
    W, H = 840, 400
    ux, uy, vx, vy = 14, 4, -9, 4.5       # week step, day step
    ox, oy, mg_ = 70, 130, 0.1
    tops = ["#141A33", "#0A5F7A", "#00A6C8", "#00E5FF", "#FF3DCB"]
    weeks = d["weeks"]
    cells = [(w, k, c) for w, wk in enumerate(weeks) for k, (_, c) in enumerate(wk)]
    mx = max([c for _, _, c in cells] + [1])
    cells.sort(key=lambda t: (t[0] + t[1], t[0]))
    def lvl(c):
        if c == 0: return 0
        r = c / mx
        return 1 if r <= .25 else 2 if r <= .5 else 3 if r <= .75 else 4
    def P(w, k, a, b, h):                 # corner at fractions a (week axis), b (day axis)
        return (ox + (w + a) * ux + (k + b) * vx, oy + (w + a) * uy + (k + b) * vy - h)
    def poly(pts, fill, op=1):
        return '<polygon points="%s" fill="%s"%s/>' % (" ".join("%.1f,%.1f" % q for q in pts), fill, "" if op == 1 else f' fill-opacity="{op}"')
    body, hot = "", ""
    for w, k, c in cells:
        L = lvl(c); h = 1.6 if c == 0 else 6 + 104 * (c / mx) ** 0.7
        c0, c1, c2, c3 = P(w, k, mg_, mg_, h), P(w, k, 1-mg_, mg_, h), P(w, k, 1-mg_, 1-mg_, h), P(w, k, mg_, 1-mg_, h)
        top = tops[L]; g = ""
        if c > 0:
            b2, b3, b1 = P(w, k, 1-mg_, 1-mg_, 0), P(w, k, mg_, 1-mg_, 0), P(w, k, 1-mg_, mg_, 0)
            g += poly([c3, c2, b2, b3], _shade(top, .62)) + poly([c1, c2, b2, b1], _shade(top, .4))
        g += poly([c0, c1, c2, c3], top, 0.55 if c == 0 else 1)
        if L == 4: hot += g
        else: body += g
    days = [c for _, _, c in cells]
    best, active = (max(days) if days else 0), sum(1 for c in days if c > 0)
    leg = "".join(f'<rect x="{262+i*16}" y="376" width="11" height="11" rx="3" fill="{t}"/>' for i, t in enumerate(tops))
    note = "last 12 months" if d["live"] else "updates after the first workflow run"
    stat = lambda x, lab, val, c: (f'<text x="{x}" y="318" font-family="{MONO}" font-size="10" letter-spacing="1.5" fill="{MUT}">{lab}</text>'
                                   f'<text x="{x}" y="344" font-family="{SANS}" font-size="24" font-weight="800" fill="{c}" filter="url(#glow)">{val}</text>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none">
<defs>{GLOW}<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="60"/></filter>
<linearGradient id="n" x1="28" x2="250" gradientUnits="userSpaceOnUse"><stop stop-color="{CY}"/><stop offset="1" stop-color="{MG}"/></linearGradient>
<clipPath id="c"><rect width="{W}" height="{H}" rx="18"/></clipPath></defs>
<g clip-path="url(#c)"><rect width="{W}" height="{H}" fill="{BG2}"/>
<g filter="url(#blur)"><circle cx="720" cy="40" r="110" fill="{MG}" fill-opacity="0.22"/><circle cx="120" cy="380" r="120" fill="{CY}" fill-opacity="0.20"/></g>
{body}<g filter="url(#glow)">{hot}</g>
<text x="28" y="292" font-family="{MONO}" font-size="11" letter-spacing="2.5" fill="{MG}">CONTRIBUTION SKYLINE</text>
<text x="28" y="344" font-family="{SANS}" font-size="44" font-weight="800" fill="url(#n)" filter="url(#glow)">{d["total"]}</text>
<text x="28" y="368" font-family="{MONO}" font-size="11.5" fill="{MUT}">contributions · {note}</text>
{stat(262, "BEST DAY", best, CY)}{stat(372, "ACTIVE DAYS", active, GR)}{leg}</g>
<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="17.5" stroke="{LINE}"/></svg>"""

def _fmt(ds):
    return f"{MONTHS[int(ds[5:7])-1]} {int(ds[8:10])}"

def streaks(d):
    days = [(dt, c) for w in d["weeks"] for dt, c in w]
    cur, cs, ce = 0, None, None
    i = len(days) - 1
    if i >= 0 and days[i][1] == 0: i -= 1
    if i >= 0 and days[i][1] > 0: ce = days[i][0]
    while i >= 0 and days[i][1] > 0:
        cur += 1; cs = days[i][0]; i -= 1
    best, run, bs, be, rs = 0, 0, None, None, None
    for dt, c in days:
        if c > 0:
            run += 1; rs = rs if run > 1 else dt
            if run > best: best, bs, be = run, rs, dt
        else: run = 0
    rng = lambda a, b: f"{_fmt(a)} – {_fmt(b)}" if a and b else "—"
    return cur, rng(cs, ce), best, rng(bs, be)

def stats_svg(d):
    import math
    W, H, CW, GAP = 840, 270, 270, 15
    cards = ""
    def card(x, label, c, inner):
        return (f'<g transform="translate({x} 0)"><rect x="0.5" y="0.5" width="{CW-1}" height="{H-1}" rx="18" fill="{BG2}" stroke="{LINE}"/>'
                f'<circle cx="26" cy="28" r="3.5" fill="{c}" filter="url(#glow)"/>'
                f'<text x="38" y="32" font-family="{MONO}" font-size="11" letter-spacing="2" fill="{c}">{label}</text>{inner}</g>')
    # --- contributions
    items = [("COMMITS", d["commits"], CY), ("PULL REQUESTS", d["prs"], MG), ("ISSUES", d["issues"], VI), ("CODE REVIEWS", d["reviews"], GR)]
    mx = max([v for _, v, _ in items] + [1])
    inner = (f'<text x="26" y="86" font-family="{SANS}" font-size="46" font-weight="800" fill="url(#n)" filter="url(#glow)">{d["total"]}</text>'
             f'<text x="26" y="108" font-family="{MONO}" font-size="11" fill="{MUT}">contributions · last 12 months</text>')
    for i, (lab, v, c) in enumerate(items):
        y = 140 + i * 31
        inner += (f'<text x="26" y="{y}" font-family="{MONO}" font-size="10" letter-spacing="1.5" fill="{MUT}">{lab}</text>'
                  f'<text x="{CW-26}" y="{y}" text-anchor="end" font-family="{SANS}" font-size="13" font-weight="700" fill="{TXT}">{v}</text>'
                  f'<rect x="26" y="{y+7}" width="{CW-52}" height="5" rx="2.5" fill="{LINE}"/>'
                  f'<rect x="26" y="{y+7}" width="{max((CW-52)*v/mx, 5 if v else 0):.1f}" height="5" rx="2.5" fill="{c}" filter="url(#glow)"/>')
    cards += card(0, "CONTRIBUTIONS", CY, inner)
    # --- streak
    cur, crng, best, brng = streaks(d)
    r = 48; C = 2 * math.pi * r
    prog = min(cur / max(best, 1), 1) * C
    inner = (f'<circle cx="135" cy="112" r="{r}" stroke="{LINE}" stroke-width="9"/>'
             f'<circle cx="135" cy="112" r="{r}" stroke="{CY}" stroke-width="9" stroke-linecap="round" stroke-dasharray="{prog:.1f} {C:.1f}" transform="rotate(-90 135 112)" filter="url(#glow)"/>'
             f'<path d="M135 56 C141 62 143 66 140 72 C138 76 132 76 130 72 C127 66 133 62 135 56Z" fill="{MG}" filter="url(#glow)"/>'
             f'<text x="135" y="125" text-anchor="middle" font-family="{SANS}" font-size="40" font-weight="800" fill="{TXT}">{cur}</text>'
             f'<text x="135" y="186" text-anchor="middle" font-family="{MONO}" font-size="11" letter-spacing="2" fill="{CY}">CURRENT STREAK</text>'
             f'<text x="135" y="203" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{MUT}">{crng}</text>'
             f'<line x1="26" y1="216" x2="{CW-26}" y2="216" stroke="{LINE}"/>'
             f'<text x="135" y="239" text-anchor="middle" font-family="{SANS}" font-size="13.5" font-weight="700" fill="{TXT}">Longest · {best} days</text>'
             f'<text x="135" y="256" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{MUT}">{brng}</text>')
    cards += card(CW + GAP, "STREAK", MG, inner)
    # --- languages
    langs = d.get("langs") or []
    total = sum(b for _, b in langs)
    cols = [CY, MG, VI, GR, YE, OR]
    top = [(n, b) for n, b in langs[:5]]
    rest = total - sum(b for _, b in top)
    if rest > 0: top.append(("Other", rest))
    r = 52; C = 2 * math.pi * r
    inner = f'<circle cx="80" cy="150" r="{r}" stroke="{LINE}" stroke-width="16"/>'
    off, leg = 0.0, ""
    for i, (n, b) in enumerate(top):
        c = cols[i] if n != "Other" else MUT
        seg = C * b / total
        inner += (f'<circle cx="80" cy="150" r="{r}" stroke="{c}" stroke-width="16" stroke-dasharray="{max(seg-2, 0.5):.1f} {C:.1f}" stroke-dashoffset="{-off:.1f}" transform="rotate(-90 80 150)" filter="url(#glow)"/>')
        off += seg
        y = 100 + i * 28
        leg += (f'<circle cx="162" cy="{y-4}" r="4" fill="{c}"/>'
                f'<text x="174" y="{y}" font-family="{SANS}" font-size="12.5" fill="{TXT}">{html.escape(n[:11])}</text>'
                f'<text x="{CW-22}" y="{y}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUT}">{100*b/total:.1f}%</text>')
    if total:
        inner += (f'<text x="80" y="156" text-anchor="middle" font-family="{SANS}" font-size="18" font-weight="800" fill="{TXT}">{100*top[0][1]/total:.0f}%</text>'
                  f'<text x="80" y="172" text-anchor="middle" font-family="{MONO}" font-size="9.5" fill="{MUT}">{html.escape(top[0][0][:10])}</text>' + leg)
    else:
        inner += f'<text x="80" y="154" text-anchor="middle" font-family="{MONO}" font-size="10" fill="{MUT}">no data yet</text>'
    cards += card(2 * (CW + GAP), "TOP LANGUAGES", VI, inner)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none">
<defs>{GLOW}<linearGradient id="n" x1="26" x2="200" gradientUnits="userSpaceOnUse"><stop stop-color="{CY}"/><stop offset="1" stop-color="{MG}"/></linearGradient></defs>{cards}</svg>"""

def write(d):
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "activity.svg"), "w", encoding="utf-8").write(activity_svg(d))
    open(os.path.join(OUT, "trophies.svg"), "w", encoding="utf-8").write(trophies_svg(d))
    open(os.path.join(OUT, "stats.svg"), "w", encoding="utf-8").write(stats_svg(d))
    open(os.path.join(OUT, "skyline.svg"), "w", encoding="utf-8").write(skyline_svg(d))

if __name__ == "__main__":
    if "--offline" in sys.argv:
        write(empty())
    else:
        login = os.environ.get("GH_LOGIN") or os.environ["GITHUB_REPOSITORY_OWNER"]
        data = fetch(login, os.environ["GITHUB_TOKEN"])
        print(f"{login}: {data['total']} contributions, {data['commits']} commits, {data['prs']} PRs, "
              f"{data['repos']} repos, {len(data['langs'])} languages, {len(data['weeks'])} weeks")
        if not data["weeks"]:
            raise SystemExit("No contribution data returned; not overwriting the existing images.")
        write(data)
    print("done")
