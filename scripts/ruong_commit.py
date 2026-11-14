#!/usr/bin/env python3
"""Ruộng commit — vẽ biểu đồ đóng góp GitHub thành cánh đồng lúa miền Tây.

Mỗi ô ruộng là một ngày: ruộng nước -> mạ non -> lúa xanh -> lúa trổ bông -> lúa chín.
Chỉ dùng thư viện chuẩn để chạy được trong GitHub Actions.

    GITHUB_TOKEN=... python3 scripts/ruong_commit.py --user Thien21112005 --out generated/ruong-commit.svg
"""
import argparse
import datetime as dt
import json
import math
import os
import random
import urllib.request

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalRepositoryContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
    byRepo: contributionsCollection {
      commitContributionsByRepository(maxRepositories: 100) {
        contributions { totalCount }
        repository { primaryLanguage { name color } }
      }
    }
  }
}
"""

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "ruong-commit"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]


def F(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def streaks(days):
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] > 0 else 0
        longest = max(longest, run)
    cur = 0
    seq = list(days)
    if seq and seq[-1]["contributionCount"] == 0:
        seq = seq[:-1]  # hôm nay chưa commit thì tính từ hôm qua
    for d in reversed(seq):
        if d["contributionCount"] > 0:
            cur += 1
        else:
            break
    return longest, cur


def languages(user):
    tot = {}
    for item in user["byRepo"]["commitContributionsByRepository"]:
        lang = (item.get("repository") or {}).get("primaryLanguage")
        if not lang:
            continue
        c = tot.setdefault(lang["name"], [0, lang["color"] or "#9CA3AF"])
        c[0] += item["contributions"]["totalCount"]
    items = sorted(tot.items(), key=lambda kv: -kv[1][0])
    total = sum(v[0] for _, v in items) or 1
    top = [(n, v[0] / total, v[1]) for n, v in items[:5]]
    rest = 1 - sum(p for _, p, _ in top)
    if rest > 0.005:
        top.append(("Khác", rest, "#9CA3AF"))
    return top


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def palm(x, y, h, lean, s, rnd, col_leaf="#2E8B3E", col_dark="#1F6B30"):
    top = (x + lean, y - h)
    ctrl = (x + lean * 0.1, y - h * 0.6)
    out = [f'<path d="M{F(x)},{F(y)} Q{F(ctrl[0])},{F(ctrl[1])} {F(top[0])},{F(top[1])}" stroke="#7A4E2D" stroke-width="{F(5*s)}" stroke-linecap="round"/>']
    rings = []
    for i in range(1, 12):
        t = i / 12
        px = (1 - t) ** 2 * x + 2 * (1 - t) * t * ctrl[0] + t * t * top[0]
        py = (1 - t) ** 2 * y + 2 * (1 - t) * t * ctrl[1] + t * t * top[1]
        rings.append(f"M{F(px-2.4*s)},{F(py)} l{F(4.8*s)},{F(1*s)}")
    out.append(f'<path d="{"".join(rings)}" stroke="#4A2C17" stroke-width="{F(.9*s)}" opacity=".6"/>')
    fr = []
    for k, ang in enumerate((-165, -140, -112, -80, -55, -28, -5, 172, 196, 25, 150)):
        a = math.radians(ang + rnd.uniform(-6, 6))
        L = h * rnd.uniform(.42, .55)
        dx, dy = math.cos(a) * L, math.sin(a) * L
        ex, ey = top[0] + dx, top[1] + dy + L * 0.45
        cx, cy = top[0] + dx * 0.55, top[1] + dy * 0.55 - L * 0.05
        col = col_dark if k < 6 else col_leaf
        # leaflets along the frond
        segs = []
        for i in range(1, 13):
            t = i / 13
            px = (1 - t) ** 2 * top[0] + 2 * (1 - t) * t * cx + t * t * ex
            py = (1 - t) ** 2 * top[1] + 2 * (1 - t) * t * cy + t * t * ey
            ll = L * 0.28 * math.sin(math.pi * min(1, t * 1.05)) ** 0.6 + 2
            tx = 2 * (1 - t) * (cx - top[0]) + 2 * t * (ex - cx)
            ty = 2 * (1 - t) * (cy - top[1]) + 2 * t * (ey - cy)
            n = math.hypot(tx, ty) or 1
            tx, ty = tx / n, ty / n
            for side in (-1, 1):
                b = math.radians(side * 50)
                lx = tx * math.cos(b) - ty * math.sin(b)
                ly = tx * math.sin(b) + ty * math.cos(b) + 0.35
                m = math.hypot(lx, ly)
                lx, ly = lx / m, ly / m
                nx, ny = -ly, lx
                w = 0.9 * s
                segs.append(f"M{F(px+nx*w)},{F(py+ny*w)}L{F(px+lx*ll)},{F(py+ly*ll)}L{F(px-nx*w)},{F(py-ny*w)}Z")
        fr.append(f'<path d="{"".join(segs)}" fill="{col}"/>')
        fr.append(f'<path d="M{F(top[0])},{F(top[1])} Q{F(cx)},{F(cy)} {F(ex)},{F(ey)}" stroke="#4D7C0F" stroke-width="{F(1.2*s)}"/>')
    nuts = "".join(f'<circle cx="{F(top[0]+dx*s)}" cy="{F(top[1]+dy*s)}" r="{F(4*s)}" fill="#4D7C0F" stroke="#365314" stroke-width=".6"/>'
                   for dx, dy in ((-4, 5), (4, 4), (0, 9)))
    tx, ty = F(top[0]), F(top[1])
    out.append(f'<g><animateTransform attributeName="transform" type="rotate" values="0 {tx} {ty};1.6 {tx} {ty};0 {tx} {ty};-1.2 {tx} {ty};0 {tx} {ty}" dur="7s" repeatCount="indefinite"/>'
               + "".join(fr) + nuts + "</g>")
    return "".join(out)


def egret(x, y, flip=False):
    sx = -1 if flip else 1
    return (f'<g transform="translate({F(x)},{F(y)}) scale({sx},1)">'
            f'<ellipse cx="0" cy="1" rx="7" ry="1.6" fill="#0F766E" opacity=".25"/>'
            f'<path d="M-1,-1 L-2,-9 M2,-1 L1.5,-9" stroke="#1F2937" stroke-width=".8"/>'
            f'<path d="M-7,-12 C-6,-17 2,-18 6,-14 C7,-12 4,-9 0,-9 C-4,-9 -7,-10 -7,-12 Z" fill="#FFFFFF" stroke="#CBD5E1" stroke-width=".5"/>'
            f'<path d="M4,-14 C7,-17 4,-20 7,-24" stroke="#FFFFFF" stroke-width="2.4" stroke-linecap="round" fill="none"/>'
            f'<g><animateTransform attributeName="transform" type="rotate" values="0 7 -24;0 7 -24;28 7 -24;0 7 -24" keyTimes="0;.7;.8;1" dur="5s" repeatCount="indefinite"/>'
            f'<circle cx="7.5" cy="-24.5" r="2.2" fill="#FFFFFF"/><path d="M9,-25 L15,-23.6 L9,-23.8 Z" fill="#EAB308"/>'
            f'<circle cx="8" cy="-25" r=".5" fill="#0F172A"/></g></g>')


def farmer(x, y):
    """Người gánh lúa, đội nón lá, đi trên bờ ruộng."""
    return (f'<g transform="translate({F(x)},{F(y)})"><g>'
            f'<animateTransform attributeName="transform" type="translate" values="0,0;0,-1.2;0,0" dur="1.1s" repeatCount="indefinite"/>'
            f'<ellipse cx="0" cy="1" rx="16" ry="2" fill="#3F2A14" opacity=".25"/>'
            f'<path d="M-2,-12 L-4,0 M2,-12 L4,0" stroke="#1F2937" stroke-width="2.2" stroke-linecap="round"/>'
            f'<path d="M-5,-25 L5,-25 L6,-11 L-6,-11 Z" fill="#5B3A1E"/>'
            f'<path d="M-24,-26 L24,-28" stroke="#A16207" stroke-width="1.6" stroke-linecap="round"/>'
            f'<path d="M-24,-26 L-27,-14 M-24,-26 L-21,-14 M24,-28 L21,-15 M24,-28 L27,-15" stroke="#78350F" stroke-width=".6"/>'
            f'<path d="M-30,-14 L-18,-14 L-20,-7 L-28,-7 Z M18,-15 L30,-15 L28,-8 L20,-8 Z" fill="#B45309"/>'
            f'<path d="M-30,-14 C-28,-19 -20,-19 -18,-14 Z M18,-15 C20,-20 28,-20 30,-15 Z" fill="#EAB308"/>'
            f'<circle cx="0" cy="-29" r="4.4" fill="#1E293B"/><ellipse cx="-1" cy="-28.6" rx="3.4" ry="3.8" fill="#E9B57F"/>'
            f'<path d="M0,-41 L-11,-31 L11,-31 Z" fill="#FDE68A" stroke="#B4892A" stroke-width=".8"/>'
            f'</g></g>')


def hut(x, y, s):
    return (f'<g transform="translate({F(x)},{F(y)}) scale({s})">'
            '<ellipse cx="50" cy="2" rx="60" ry="5" fill="#1A2E05" opacity=".2"/>'
            '<path d="M72,0 L94,-9 L94,-41 L72,-32 Z" fill="#6A4422"/>'
            '<path d="M72,-32 L94,-41 L84,-63 Z" fill="#9C7442"/>'
            '<path d="M0,0 L72,0 L72,-32 L0,-32 Z" fill="#8B5E34"/>'
            '<path d="M6,0V-32M12,0V-32M18,0V-32M24,0V-32M30,0V-32M36,0V-32M60,0V-32M66,0V-32" stroke="#5E3B1C" stroke-width=".8"/>'
            '<rect x="10" y="-23" width="17" height="11" fill="#24150A"/><rect x="42" y="-25" width="14" height="25" fill="#2A190B"/>'
            '<path d="M-8,-25 L81,-25 L88,-64 L7,-64 Z" fill="#B48A50"/>'
            '<path d="M10,-64L0,-25M22,-64L14,-25M34,-64L28,-25M46,-64L42,-25M58,-64L56,-25M70,-64L70,-25M82,-64L80,-25" stroke="#8C6232" stroke-width="1"/>'
            '<path d="M81,-25 L88,-64 L101,-38 L97,-35 Z" fill="#7A5428"/>'
            '<path d="M6,-64 L89,-64" stroke="#5E3F1E" stroke-width="3" stroke-linecap="round"/></g>')


# ---------------------------------------------------------------------------
def render(user):
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    longest, current = streaks(days)
    best = max(days, key=lambda d: d["contributionCount"])
    langs = languages(user)
    rnd = random.Random(11)

    W, H = 1200, 590
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none">',
         """<defs>
  <clipPath id="frame"><rect width="1200" height="590" rx="18"/></clipPath>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#7DD3FC"/><stop offset=".7" stop-color="#E0F2FE"/><stop offset="1" stop-color="#FEF9C3"/>
  </linearGradient>
  <linearGradient id="land" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#9BCB6B"/><stop offset="1" stop-color="#7DB04E"/>
  </linearGradient>
  <linearGradient id="board" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#B07A45"/><stop offset="1" stop-color="#8A5A2E"/>
  </linearGradient>
  <linearGradient id="water" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#BFEFE3"/><stop offset="1" stop-color="#8FD3C4"/>
  </linearGradient>
  <filter id="shade" x="-10%" y="-40%" width="120%" height="180%">
    <feDropShadow dx="0" dy="1" stdDeviation="1" flood-color="#3B2412" flood-opacity=".8"/>
  </filter>
</defs>""",
         '<g clip-path="url(#frame)">',
         '<rect width="1200" height="590" fill="url(#land)"/>',
         '<rect width="1200" height="185" fill="url(#sky)"/>',
         '<circle cx="640" cy="70" r="34" fill="#FEF3C7" opacity=".9"/>']
    # far tree line
    sil = []
    x = -10
    while x < 1210:
        hh = rnd.uniform(16, 30)
        lean = rnd.uniform(-4, 4)
        tx, ty = x + lean, 178 - hh
        fr = "".join(
            f"M{F(tx)},{F(ty)}Q{F(tx+math.cos(math.radians(a))*hh*.25)},{F(ty+math.sin(math.radians(a))*hh*.25-2)} "
            f"{F(tx+math.cos(math.radians(a))*hh*.42)},{F(ty+math.sin(math.radians(a))*hh*.42+hh*.18)}"
            for a in (-160, -125, -90, -55, -20, 160, 20))
        sil.append(f'<path d="M{F(x)},178Q{F(x+lean*.2)},{F(178-hh*.6)} {F(tx)},{F(ty)}" stroke="#3F7D3A" stroke-width="1.6"/>'
                   f'<path d="{fr}" stroke="#3F7D3A" stroke-width="2"/>')
        x += rnd.uniform(14, 28)
    o.append('<g stroke-linecap="round" opacity=".85">' + "".join(sil) + "</g>")
    o.append('<path d="M0,176 C300,170 900,172 1200,176 L1200,190 L0,190 Z" fill="#5E9F45"/>')

    # title
    o.append('<text x="40" y="58" font-family="\'Times New Roman\', Georgia, serif" font-size="30" font-weight="bold" fill="#14532D" '
             'filter="url(#shade)" style="paint-order:stroke" stroke="#F0FDF4" stroke-width="3">Ruộng commit một năm qua</text>')
    o.append('<text x="42" y="86" font-family="Arial, sans-serif" font-size="14" font-style="italic" fill="#1F4D2B">'
             'Mỗi ô ruộng là một ngày — commit càng siêng, lúa càng chín vàng</text>')

    # wooden signboard with the numbers
    bx, by = 812, 16
    o.append(f'<path d="M{bx+40},{by+150} L{bx+46},{by+178} M{bx+330},{by+150} L{bx+324},{by+178}" stroke="#5B3A1E" stroke-width="6" stroke-linecap="round"/>')
    o.append(f'<rect x="{bx}" y="{by}" width="370" height="152" rx="8" fill="url(#board)" stroke="#5B3A1E" stroke-width="3"/>')
    o.append(f'<path d="M{bx+8},{by+50}H{bx+362}M{bx+8},{by+100}H{bx+362}" stroke="#7A4E2D" stroke-width="1" opacity=".6"/>')
    lines = [
        ("Bảng ghi mùa vụ", 17, True),
        (f"{cal['totalContributions']:,} lần gieo hạt trong năm".replace(",", "."), 15, True),
        (f"Commit {cc['totalCommitContributions']}  ·  PR {cc['totalPullRequestContributions']}  ·  "
         f"Issue {cc['totalIssueContributions']}  ·  Review {cc['totalPullRequestReviewContributions']}", 12.5, False),
        (f"Mùa dài nhất: {longest} ngày liền tay", 13.5, False),
        (f"Đang chăm ruộng: {current} ngày", 13.5, False),
        (f"Ngày bội thu: {dt.date.fromisoformat(best['date']).strftime('%d/%m/%Y')} ({best['contributionCount']} lần)", 13.5, False),
    ]
    yy = by + 26
    for t, fs, bold in lines:
        fw = 'font-weight="bold" ' if bold else ""
        o.append(f'<text x="{bx+185}" y="{yy}" text-anchor="middle" font-family="Arial, sans-serif" font-size="{fs}" '
                 f'{fw}fill="#FFF7ED" filter="url(#shade)">{esc(t)}</text>')
        yy += 23 if fs > 14 else 21

    # palms + hut beside the field
    o.append(hut(1050, 196, .55))
    o.append(palm(30, 400, 150, 22, 1.0, rnd))
    o.append(palm(1170, 404, 140, -20, 1.0, rnd))

    # ---- the paddy field: 53 weeks x 7 days, oblique perspective ----
    cw, rh, sk = 20, 25, 9
    x0, y0 = 70, 214
    o.append(f'<path d="M{x0-10+7*sk},{y0-6} L{x0+len(weeks)*cw+7*sk+6},{y0-6} L{x0+len(weeks)*cw+8},{y0+7*rh+6} L{x0-16},{y0+7*rh+6} Z" fill="#8A6A3A"/>')
    tiles = {0: [], 1: [], 2: [], 3: [], 4: []}
    tufts = [[] for _ in range(7)]
    heads = [[] for _ in range(7)]
    water_cells = []
    TUFT = {1: (2, 5, "#7CC046"), 2: (3, 8, "#4E9A2E"), 3: (3, 11, "#3F8A2C"), 4: (4, 12, "#B58A1E")}
    for wi, w in enumerate(weeks):
        for d in w["contributionDays"]:
            di = dt.date.fromisoformat(d["date"]).isoweekday() % 7  # Sunday=0
            lv = LEVELS.get(d["contributionLevel"], 0)
            xl = x0 + wi * cw + (7 - di) * sk
            yt = y0 + di * rh
            g = 2.2
            pts = [(xl + g, yt + g), (xl + cw - g, yt + g), (xl + cw - g - sk, yt + rh - g), (xl + g - sk, yt + rh - g)]
            tiles[lv].append("M" + "L".join(f"{F(a)},{F(b)}" for a, b in pts) + "Z")
            if lv == 0:
                water_cells.append((wi, di, xl, yt))
                continue
            n, h, col = TUFT[lv]
            for k in range(n):
                cx = xl + cw * (k + 1) / (n + 1) - sk * 0.55 + rnd.uniform(-1, 1)
                cy = yt + rh * 0.72 + rnd.uniform(-2, 2)
                hh = h * rnd.uniform(.85, 1.1)
                tufts[di].append((col, f"M{F(cx)},{F(cy)}Q{F(cx-2)},{F(cy-hh*.6)} {F(cx-3.6)},{F(cy-hh)}"
                                       f"M{F(cx)},{F(cy)}L{F(cx+.3)},{F(cy-hh-1)}"
                                       f"M{F(cx)},{F(cy)}Q{F(cx+2)},{F(cy-hh*.6)} {F(cx+3.6)},{F(cy-hh)}"))
                if lv >= 3:
                    hc = "#E9C24A" if lv == 4 else "#C9D86B"
                    heads[di].append((hc, f"M{F(cx+.3)},{F(cy-hh-1)}Q{F(cx+3)},{F(cy-hh-1)} {F(cx+3.5)},{F(cy-hh+3)}"
                                          f"M{F(cx-3.6)},{F(cy-hh)}Q{F(cx-5.5)},{F(cy-hh)} {F(cx-5.8)},{F(cy-hh+3)}"))
    fills = {0: "url(#water)", 1: "#B5D98C", 2: "#93C76A", 3: "#78B552", 4: "#D8C060"}
    for lv in range(5):
        if tiles[lv]:
            o.append(f'<path d="{"".join(tiles[lv])}" fill="{fills[lv]}"/>')
    # sky glints on the flooded plots
    gl = []
    for (wi, di, xl, yt) in water_cells[::3]:
        gl.append(f"M{F(xl+3)},{F(yt+8)}l7,0")
    if gl:
        o.append(f'<path d="{"".join(gl)}" stroke="#FFFFFF" stroke-width="1.2" stroke-linecap="round" opacity=".7">'
                 f'<animate attributeName="opacity" values=".7;.2;.7" dur="3s" repeatCount="indefinite"/></path>')
    # rice, row by row (back to front) with a gentle breeze
    for di in range(7):
        if not tufts[di]:
            continue
        base = y0 + di * rh + rh * 0.72
        by_col = {}
        for col, d in tufts[di]:
            by_col.setdefault(col, []).append(d)
        hb = {}
        for col, d in heads[di]:
            hb.setdefault(col, []).append(d)
        body = "".join(f'<path d="{"".join(v)}" stroke="{c}" stroke-width="1.3" stroke-linecap="round"/>' for c, v in by_col.items())
        body += "".join(f'<path d="{"".join(v)}" stroke="{c}" stroke-width="2" stroke-linecap="round"/>' for c, v in hb.items())
        o.append(f'<g transform="translate(0,{F(base)})"><g><animateTransform attributeName="transform" type="skewX" '
                 f'values="0;-5;0;3;0" dur="{F(5+di*.25)}s" repeatCount="indefinite"/>'
                 f'<g transform="translate(0,{F(-base)})">{body}</g></g></g>')
    # egrets in flooded plots
    picks = [c for c in water_cells if 1 <= c[1] <= 5]
    rnd.shuffle(picks)
    for (wi, di, xl, yt) in sorted(picks[:3], key=lambda c: c[1]):
        o.append(egret(xl + cw * 0.4 - sk * .5, yt + rh * 0.75, flip=rnd.random() < .5))

    # front dyke with the farmer, month labels
    fy = y0 + 7 * rh + 6
    o.append(f'<path d="M{x0-20},{fy} L{x0+len(weeks)*cw+12},{fy} L{x0+len(weeks)*cw+12},{fy+10} L{x0-20},{fy+10} Z" fill="#A27B48"/>')
    o.append(f'<path d="M{x0-20},{fy+1} L{x0+len(weeks)*cw+12},{fy+1}" stroke="#6E9C34" stroke-width="2.5"/>')
    o.append(farmer(x0 + len(weeks) * cw * 0.62, fy + 2))
    seen = None
    for wi, w in enumerate(weeks):
        m = dt.date.fromisoformat(w["contributionDays"][0]["date"]).month
        if m != seen:
            seen = m
            if wi < len(weeks) - 2:
                o.append(f'<text x="{F(x0 + wi*cw)}" y="{fy+28}" font-family="Arial, sans-serif" font-size="12" fill="#1F4D2B" font-weight="bold">Th{m}</text>')

    # legend
    ly = fy + 50
    o.append(f'<text x="70" y="{ly+14}" font-family="Arial, sans-serif" font-size="13" fill="#1F4D2B" font-weight="bold">Ít</text>')
    names = ["Ruộng nước", "Mạ non", "Lúa xanh", "Trổ bông", "Lúa chín"]
    lx = 92
    for lv in range(5):
        o.append(f'<path d="M{lx+sk},{ly} L{lx+cw+sk},{ly} L{lx+cw},{ly+18} L{lx},{ly+18} Z" fill="{fills[lv]}" stroke="#8A6A3A" stroke-width="1.5"/>')
        o.append(f'<text x="{lx+cw+sk+6}" y="{ly+14}" font-family="Arial, sans-serif" font-size="12" fill="#1F2937">{names[lv]}</text>')
        lx += 112
    o.append(f'<text x="{lx}" y="{ly+14}" font-family="Arial, sans-serif" font-size="13" fill="#1F4D2B" font-weight="bold">Nhiều</text>')

    # language harvest: rice sacks
    o.append(f'<text x="70" y="{ly+58}" font-family="Arial, sans-serif" font-size="12" font-style="italic" fill="#1F4D2B">'
             f'Cò trắng đứng chỗ ruộng còn nước, người gánh lúa đi dọc bờ ruộng mỗi ngày.</text>')
    sy = fy + 44
    o.append(f'<text x="1175" y="{sy+12}" text-anchor="end" font-family="\'Times New Roman\', Georgia, serif" font-size="19" font-weight="bold" fill="#14532D">Lúa về đầy bao — ngôn ngữ hay dùng</text>')
    sx = 1180 - 78 * len(langs)
    for name, p, color in langs:
        hgt = 26 + 44 * p / max(l[1] for l in langs)
        top = sy + 100 - hgt
        o.append(f'<g transform="translate({sx},0)">'
                 f'<ellipse cx="38" cy="{sy+101}" rx="34" ry="4" fill="#3F2A14" opacity=".25"/>'
                 f'<path d="M8,{F(sy+100)} C4,{F(top+20)} 10,{F(top+6)} 24,{F(top)} L52,{F(top)} C66,{F(top+6)} 72,{F(top+20)} 68,{F(sy+100)} Z" fill="#E7D2A6" stroke="#8A6A3A" stroke-width="1.5"/>'
                 f'<path d="M24,{F(top)} C30,{F(top-8)} 46,{F(top-8)} 52,{F(top)}" fill="#D9BE86" stroke="#8A6A3A" stroke-width="1.2"/>'
                 f'<path d="M22,{F(top+3)} L54,{F(top+3)}" stroke="#7A4E2D" stroke-width="2.2"/>'
                 f'<rect x="14" y="{F(top+14)}" width="48" height="{F(max(8, hgt-22))}" rx="3" fill="{color}" opacity=".85"/>'
                 f'<text x="38" y="{F(sy+118)}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="bold" fill="#1F2937">{esc(name)}</text>'
                 f'<text x="38" y="{F(top+14+max(8,hgt-22)/2+4)}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" font-weight="bold" fill="#FFFFFF" '
                 f'style="paint-order:stroke" stroke="#1F2937" stroke-width="2">{p*100:.0f}%</text></g>')
        sx += 78
    o.append('</g></svg>')
    return "\n".join(o) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", help="read data from a saved GraphQL response instead of calling the API")
    a = ap.parse_args()
    if a.json:
        user = json.load(open(a.json, encoding="utf-8"))["data"]["user"]
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("GITHUB_TOKEN is required")
        user = fetch(a.user, token)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(render(user))


if __name__ == "__main__":
    main()
