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


def cloud(x, y, s):
    return (f'<g transform="translate({F(x)},{F(y)}) scale({s})" opacity=".92"><g>'
            f'<animateTransform attributeName="transform" type="translate" values="0,0;14,0;0,0" dur="40s" repeatCount="indefinite"/>'
            '<ellipse cx="0" cy="0" rx="34" ry="11" fill="#FFFFFF"/><ellipse cx="-12" cy="-8" rx="16" ry="11" fill="#FFFFFF"/>'
            '<ellipse cx="10" cy="-11" rx="18" ry="13" fill="#FFFFFF"/><ellipse cx="0" cy="4" rx="30" ry="5" fill="#E0F2FE"/></g></g>')


def birds(x, y):
    o = []
    for i, (dx, dy, sc) in enumerate(((0, 0, 1), (22, -8, .8), (40, 6, .7), (-20, 10, .65))):
        up = "M-8,0 Q-4,-5 0,0 Q4,-5 8,0"
        dn = "M-8,0 Q-4,3 0,0 Q4,3 8,0"
        o.append(f'<path transform="translate({F(x+dx)},{F(y+dy)}) scale({sc})" d="{up}" stroke="#334155" stroke-width="1.6" stroke-linecap="round">'
                 f'<animate attributeName="d" values="{up};{dn};{up}" dur="{F(1+i*.15)}s" repeatCount="indefinite"/></path>')
    return "".join(o)


def kite(x, y):
    return (f'<g transform="translate({x},{y})"><g>'
            '<animateTransform attributeName="transform" type="rotate" values="-6;6;-6" dur="3s" repeatCount="indefinite"/>'
            '<path d="M0,-16 L12,0 L0,18 L-12,0 Z" fill="#EF4444" stroke="#7F1D1D" stroke-width=".8"/>'
            '<path d="M0,-16 L0,18 M-12,0 L12,0" stroke="#FDE047" stroke-width="1"/>'
            '<path d="M0,18 C-6,26 6,32 -2,40 C-8,46 4,52 -2,58" stroke="#F59E0B" stroke-width="1.2"/>'
            '<path d="M-3,27 l-4,-2 l1,4 Z M-1,41 l4,-3 l0,5 Z M-2,53 l-4,-1 l2,4 Z" fill="#FDE047"/></g></g>')


def kid(x, y):
    return (f'<g transform="translate({F(x)},{F(y)})">'
            '<ellipse cx="0" cy="1" rx="7" ry="1.5" fill="#3F2A14" opacity=".25"/>'
            '<path d="M-2,-8 L-3,0 M2,-8 L3,0" stroke="#1F2937" stroke-width="1.8" stroke-linecap="round"/>'
            '<path d="M-4,-17 L4,-17 L4.5,-8 L-4.5,-8 Z" fill="#DC2626"/>'
            '<path d="M3,-15 L6,-20" stroke="#E9B57F" stroke-width="1.6" stroke-linecap="round"/>'
            '<circle cx="0" cy="-20.5" r="3.6" fill="#1E293B"/><ellipse cx=".6" cy="-20" rx="2.8" ry="3" fill="#E9B57F"/></g>')


def scarecrow(x, y):
    return (f'<g transform="translate({F(x)},{F(y)})">'
            '<ellipse cx="0" cy="1" rx="9" ry="2" fill="#3F2A14" opacity=".25"/>'
            '<path d="M0,0 L0,-34 M-14,-24 L14,-24" stroke="#7A4E2D" stroke-width="2" stroke-linecap="round"/>'
            '<g><animateTransform attributeName="transform" type="rotate" values="-3 0 -30;3 0 -30;-3 0 -30" dur="4s" repeatCount="indefinite"/>'
            '<path d="M-8,-26 L8,-26 L10,-12 L-10,-12 Z" fill="#2563EB"/>'
            '<path d="M-14,-24 L-8,-25 M8,-25 L14,-24" stroke="#2563EB" stroke-width="3.5" stroke-linecap="round"/>'
            '<path d="M-15,-23 l-3,2 M15,-23 l3,2" stroke="#D6B98A" stroke-width="1.2"/>'
            '<circle cx="0" cy="-31" r="4.5" fill="#E7D2A6" stroke="#A47148" stroke-width=".6"/>'
            '<path d="M-2,-32 l1,0 M2,-32 l1,0 M-2,-29 Q0,-28 2,-29" stroke="#3F2A14" stroke-width=".8"/>'
            '<path d="M0,-44 L-11,-34 L11,-34 Z" fill="#FDE68A" stroke="#B4892A" stroke-width=".7"/>'
            '<path d="M-6,-12 L-7,-8 M6,-12 L7,-8" stroke="#D6B98A" stroke-width="1"/></g></g>')


def haystack(x, y, s):
    return (f'<g transform="translate({F(x)},{F(y)}) scale({s})">'
            '<ellipse cx="0" cy="2" rx="22" ry="3" fill="#3F2A14" opacity=".2"/>'
            '<path d="M-20,0 C-20,-20 -8,-34 0,-36 C8,-34 20,-20 20,0 Z" fill="#E2B85A"/>'
            '<path d="M-14,-6 Q-6,-10 2,-8 M-16,-14 Q-4,-18 8,-15 M-10,-24 Q0,-27 10,-23 M4,-4 Q12,-6 17,-4" stroke="#B4892A" stroke-width="1"/>'
            '<path d="M0,-36 L0,-44" stroke="#7A4E2D" stroke-width="2" stroke-linecap="round"/></g>')


def banana(x, y, s, rnd):
    leaves = []
    for ang in (-150, -115, -80, -50, -20, 170):
        a = math.radians(ang + rnd.uniform(-8, 8))
        L = 24 * s
        ex, ey = x + math.cos(a) * L, y - 30 * s + math.sin(a) * L + L * .3
        cx, cy = x + math.cos(a) * L * .5, y - 30 * s + math.sin(a) * L * .5 - 4 * s
        nx, ny = -math.sin(a) * 5 * s, math.cos(a) * 5 * s
        leaves.append(f'<path d="M{F(x)},{F(y-30*s)} Q{F(cx+nx)},{F(cy+ny)} {F(ex)},{F(ey)} Q{F(cx-nx)},{F(cy-ny)} {F(x)},{F(y-30*s)} Z" '
                      f'fill="{rnd.choice(["#65A30D", "#4D7C0F", "#84CC16"])}" stroke="#3F6212" stroke-width=".6"/>')
    return (f'<path d="M{F(x)},{F(y)} L{F(x)},{F(y-30*s)}" stroke="#7DA34A" stroke-width="{F(4*s)}" stroke-linecap="round"/>'
            + "".join(leaves))


def dyke_ducks(x, y):
    o = []
    for i in range(6):
        dx = x + i * 15
        col, wing = (("#F8FAFC", "#CBD5E1") if i % 3 == 1 else ("#B07D4F", "#6B4226"))
        o.append(f'<g transform="translate({F(dx)},{F(y)})"><g>'
                 f'<animateTransform attributeName="transform" type="translate" values="0,0;0,-1;0,0" dur=".5s" begin="{F(i*.08)}s" repeatCount="indefinite"/>'
                 '<path d="M-1,-3 L-1.5,0 M2,-3 L2.5,0" stroke="#F59E0B" stroke-width=".8"/>'
                 f'<ellipse cx="1" cy="-6" rx="6" ry="3.6" fill="{col}"/>'
                 f'<path d="M-1,-6.5 Q2,-8 5,-6.5" stroke="{wing}" stroke-width="1.4"/>'
                 f'<path d="M-4,-7 L-5,-12" stroke="{col}" stroke-width="2.4" stroke-linecap="round"/>'
                 f'<circle cx="-5" cy="-12.5" r="2.4" fill="{"#5C4033" if i % 3 != 1 else "#F8FAFC"}"/>'
                 '<path d="M-7,-12.8 L-9.5,-12 L-7,-11.4 Z" fill="#F59E0B"/></g></g>')
    return "".join(o)


def icon_rice(x, y):
    return (f'<g transform="translate({F(x)},{F(y)})"><path d="M0,10 Q1,0 6,-8" stroke="#A3E635" stroke-width="1.6" fill="none"/>'
            + "".join(f'<ellipse cx="{F(2+k*1.2)}" cy="{F(2-k*3)}" rx="1.6" ry="2.6" fill="#FDE047" transform="rotate(35 {F(2+k*1.2)} {F(2-k*3)})"/>' for k in range(4))
            + '<path d="M0,10 Q-4,2 -8,0" stroke="#84CC16" stroke-width="1.4" fill="none"/></g>')


def icon_sprout(x, y):
    return (f'<g transform="translate({F(x)},{F(y)})"><path d="M0,10 L0,-2" stroke="#86EFAC" stroke-width="1.8"/>'
            '<path d="M0,0 C-8,-2 -9,-9 -2,-9 C-1,-6 0,-3 0,0 Z" fill="#4ADE80"/>'
            '<path d="M0,-2 C8,-4 9,-11 2,-11 C1,-8 0,-5 0,-2 Z" fill="#22C55E"/>'
            '<path d="M-6,10 L6,10" stroke="#A47148" stroke-width="2" stroke-linecap="round"/></g>')


def icon_sun(x, y):
    rays = "".join(f"M{F(math.cos(math.radians(a))*7)},{F(math.sin(math.radians(a))*7)}L{F(math.cos(math.radians(a))*10)},{F(math.sin(math.radians(a))*10)}"
                   for a in range(0, 360, 45))
    return (f'<g transform="translate({F(x)},{F(y)})"><path d="{rays}" stroke="#FDE047" stroke-width="1.6" stroke-linecap="round"/>'
            '<circle r="5" fill="#FACC15"/></g>')


def signboard(bx, by, cal, cc, longest, current, best):
    w, h = 398, 150
    t = by + 18  # board top
    o = []
    # posts
    o.append(f'<path d="M{bx+30},{t} L{bx+32},{by+186} M{bx+w-30},{t} L{bx+w-32},{by+186}" stroke="#5B3A1E" stroke-width="7" stroke-linecap="round"/>')
    # board planks
    o.append(f'<rect x="{bx}" y="{t}" width="{w}" height="{h}" rx="6" fill="url(#board)" stroke="#4A2E14" stroke-width="3"/>')
    o.append(f'<path d="M{bx+4},{t+50}H{bx+w-4}M{bx+4},{t+100}H{bx+w-4}" stroke="#5E3B1C" stroke-width="1.6" opacity=".7"/>')
    grain = []
    for k in range(9):
        gy = t + 10 + k * 16
        grain.append(f"M{bx+12},{gy} C{bx+90},{gy-3} {bx+180},{gy+3} {bx+260},{gy-1} S{bx+350},{gy+2} {bx+w-12},{gy}")
    o.append(f'<path d="{"".join(grain)}" stroke="#C99A68" stroke-width=".7" opacity=".35"/>')
    for (nx, ny) in ((bx + 10, t + 10), (bx + w - 10, t + 10), (bx + 10, t + h - 10), (bx + w - 10, t + h - 10)):
        o.append(f'<circle cx="{nx}" cy="{ny}" r="2.4" fill="#3B2412"/><circle cx="{nx-.6}" cy="{ny-.6}" r=".8" fill="#D6B98A"/>')
    # thatched cap
    o.append(f'<path d="M{bx-16},{t+4} L{bx+20},{by-6} L{bx+w-20},{by-6} L{bx+w+16},{t+4} Z" fill="#B48A50"/>')
    th = "".join(f"M{bx-10+k*12.6},{t+4} L{bx+22+k*10.8},{by-6}" for k in range(33))
    o.append(f'<path d="{th}" stroke="#8C6232" stroke-width=".9" opacity=".8"/>')
    fr = "".join(f"L{bx-16+k*6.65+3},{t+9+(k%3)} L{bx-16+(k+1)*6.65},{t+4}" for k in range(63))
    o.append(f'<path d="M{bx-16},{t+4}{fr}Z" fill="#8C6232"/>')
    o.append(f'<path d="M{bx+18},{by-7} L{bx+w-18},{by-7}" stroke="#5E3F1E" stroke-width="3" stroke-linecap="round"/>')
    # red cloth ribbon with the title
    cx = bx + w / 2
    ry = t + 18
    o.append(f'<path d="M{F(cx-120)},{ry-11} L{F(cx-132)},{ry} L{F(cx-120)},{ry+11} Z M{F(cx+120)},{ry-11} L{F(cx+132)},{ry} L{F(cx+120)},{ry+11} Z" fill="#991B1B"/>')
    o.append(f'<rect x="{F(cx-112)}" y="{ry-13}" width="224" height="26" rx="3" fill="#DC2626" stroke="#7F1D1D" stroke-width="1.2"/>')
    o.append(f'<text x="{F(cx)}" y="{ry+5}" text-anchor="middle" font-family="\'Times New Roman\', Georgia, serif" font-size="15" font-weight="bold" letter-spacing="2.5" fill="#FDE047">BẢNG GHI MÙA VỤ</text>')
    # big total
    total = f"{cal['totalContributions']:,}".replace(",", ".")
    o.append(icon_rice(bx + 22, t + 70))
    o.append(f'<text x="{bx+90}" y="{t+78}" text-anchor="middle" font-family="Georgia, serif" font-size="32" font-weight="bold" fill="#FEF3C7" filter="url(#shade)">{total}</text>')
    o.append(f'<text x="{bx+90}" y="{t+94}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11.5" fill="#FDE68A">lần gieo hạt trong năm</text>')
    # 2x2 chips
    chips = [("Commit", cc["totalCommitContributions"]), ("PR", cc["totalPullRequestContributions"]),
             ("Issue", cc["totalIssueContributions"]), ("Review", cc["totalPullRequestReviewContributions"])]
    for i, (lab, val) in enumerate(chips):
        chx = bx + 160 + (i % 2) * 110
        chy = t + 40 + (i // 2) * 28
        o.append(f'<rect x="{chx}" y="{chy}" width="102" height="22" rx="11" fill="#5B3A1E" stroke="#C99A68" stroke-width=".8"/>'
                 f'<text x="{chx+12}" y="{chy+15}" font-family="Arial, sans-serif" font-size="11.5" fill="#FDE68A">{lab}</text>'
                 f'<text x="{chx+92}" y="{chy+15.5}" text-anchor="end" font-family="Arial, sans-serif" font-size="13" font-weight="bold" fill="#FFF7ED">{val}</text>')
    # bottom row with icons
    bdate = dt.date.fromisoformat(best["date"]).strftime("%d/%m/%Y")
    cols = [(icon_rice, f"{longest} ngày liền", "Mùa dài nhất"),
            (icon_sprout, f"{current} ngày", "Đang chăm ruộng"),
            (icon_sun, bdate, f"Bội thu: {best['contributionCount']} lần")]
    for i, (ic, val, lab) in enumerate(cols):
        cx0 = bx + 14 + i * 128
        o.append(ic(cx0 + 8, t + 122))
        o.append(f'<text x="{cx0+24}" y="{t+120}" font-family="Arial, sans-serif" font-size="13.5" font-weight="bold" fill="#FFF7ED" filter="url(#shade)">{esc(val)}</text>'
                 f'<text x="{cx0+24}" y="{t+136}" font-family="Arial, sans-serif" font-size="10.5" fill="#FDE68A">{esc(lab)}</text>')
    return "".join(o)


def buffalo(x, y):
    """Con trâu gặm cỏ."""
    return (f'<g transform="translate({F(x)},{F(y)})">'
            '<ellipse cx="0" cy="2" rx="26" ry="3" fill="#3F2A14" opacity=".25"/>'
            '<path d="M-12,-10 L-13,0 M-6,-10 L-6,0 M10,-10 L10,0 M15,-10 L16,0" stroke="#334155" stroke-width="3.4" stroke-linecap="round"/>'
            '<path d="M-17,-14 C-18,-24 -6,-28 8,-27 C18,-26 22,-20 20,-12 C18,-7 -14,-6 -17,-14 Z" fill="#475569"/>'
            '<path d="M-6,-24 C0,-26 10,-26 16,-23" stroke="#64748B" stroke-width="1.4" opacity=".8"/>'
            '<path d="M20,-20 Q26,-16 24,-6" stroke="#475569" stroke-width="1.6" fill="none"/><path d="M23,-7 l2,3 l-3,0 Z" fill="#1F2937"/>'
            '<g><animateTransform attributeName="transform" type="rotate" values="0 -16 -18;6 -16 -18;0 -16 -18" dur="3s" repeatCount="indefinite"/>'
            '<path d="M-16,-20 C-22,-18 -26,-10 -27,-4 C-25,-1 -21,-1 -19,-4 C-17,-10 -13,-14 -12,-17 Z" fill="#475569"/>'
            '<ellipse cx="-24" cy="-3" rx="3.4" ry="2.4" fill="#334155"/>'
            '<path d="M-17,-19 C-24,-26 -30,-22 -26,-17 M-15,-19 C-10,-27 -4,-24 -8,-19" stroke="#E7E5E4" stroke-width="2" stroke-linecap="round" fill="none"/>'
            '<circle cx="-19" cy="-13" r=".9" fill="#0F172A"/></g>'
            '<path d="M-30,-1 l-2,-5 M-28,0 l0,-6 M-26,-1 l2,-5" stroke="#4D7C0F" stroke-width="1" stroke-linecap="round"/></g>')


def canal(y, x1, rnd):
    """Con mương nhỏ: xuồng ba lá, vịt bơi, lục bình, cây dừa trên bờ."""
    o = [f'<path d="M0,{y-16} C150,{y-22} 420,{y-12} {x1},{y-18} L{x1},{y+20} C420,{y+26} 150,{y+16} 0,{y+22} Z" fill="#D9BB7E"/>',
         f'<path d="M0,{y-11} C150,{y-17} 420,{y-7} {x1},{y-13} L{x1},{y+15} C420,{y+21} 150,{y+11} 0,{y+17} Z" fill="url(#water)"/>',
         f'<path d="M60,{y} l26,0 M240,{y+6} l30,0 M430,{y-2} l22,0 M600,{y+5} l26,0" stroke="#FFFFFF" stroke-width="1.3" stroke-linecap="round" opacity=".8">'
         '<animate attributeName="opacity" values=".8;.25;.8" dur="3s" repeatCount="indefinite"/></path>']
    # lục bình clumps
    for (lx, ly) in ((150, y + 4), (166, y + 8), (520, y + 2), (536, y + 7)):
        o.append(f'<g transform="translate({lx},{ly})"><ellipse cx="0" cy="1" rx="9" ry="2.4" fill="#14532D"/>'
                 '<ellipse cx="-4" cy="-3" rx="4" ry="3.4" fill="#16A34A"/><ellipse cx="3" cy="-4" rx="4" ry="3.6" fill="#22A447"/>'
                 '<path d="M0,-4 L0,-14" stroke="#4D7C0F" stroke-width="1"/>'
                 '<circle cx="-1" cy="-11" r="2" fill="#B794F6"/><circle cx="1" cy="-13.5" r="1.8" fill="#C4B5FD"/><circle cx="0" cy="-15.5" r="1.4" fill="#A78BFA"/></g>')
    # xuồng ba lá
    o.append(f'<g transform="translate(330,{y+4})"><g>'
             '<animateTransform attributeName="transform" type="translate" values="0,0;14,-.5;0,0" dur="10s" repeatCount="indefinite"/>'
             '<path d="M-30,-4 C-12,4 18,4 32,-5 L27,0 C14,6 -12,6 -25,0 Z" fill="#6B3D12"/>'
             '<path d="M-31,-5 C-12,3 18,3 33,-6" stroke="#E0B54A" stroke-width="1.6" stroke-linecap="round"/>'
             '<circle cx="-18" cy="-5" r="3" fill="#4D7C0F"/><circle cx="-13" cy="-6" r="2.8" fill="#65A30D"/>'
             '<path d="M6,-4 L5,-14 L13,-14 L12,-4 Z" fill="#7C4A21"/>'
             '<circle cx="9" cy="-16" r="3.4" fill="#1E293B"/><ellipse cx="8.2" cy="-15.6" rx="2.6" ry="2.9" fill="#E9B57F"/>'
             '<path d="M9,-25 L1,-18 L17,-18 Z" fill="#FDE68A" stroke="#B4892A" stroke-width=".7"/>'
             '<path d="M12,-11 L-2,6" stroke="#7C4A21" stroke-width="1.6" stroke-linecap="round"/>'
             '<ellipse cx="2" cy="4" rx="34" ry="3" stroke="#CCFBF1" stroke-width="1" opacity=".7"/></g></g>')
    # ducks swimming
    for i, (dx, col) in enumerate(((440, "#B07D4F"), (458, "#F8FAFC"), (474, "#B07D4F"))):
        o.append(f'<g transform="translate({dx},{y+3 + (i % 2) * 3})"><g>'
                 f'<animateTransform attributeName="transform" type="translate" values="0,0;0,-1;0,0" dur="{F(2+i*.3)}s" repeatCount="indefinite"/>'
                 '<path d="M8,1 L18,-1 M8,2 L18,4" stroke="#CCFBF1" stroke-width=".7" opacity=".7"/>'
                 f'<path d="M-6,0 C-7,-4 -2,-6 3,-5 C6,-5 8,-4 9,-7 C9.5,-3 8.5,-1 6,0 Z" fill="{col}"/>'
                 f'<path d="M-6.5,-2 L-6,-7" stroke="{col}" stroke-width="2.2" stroke-linecap="round"/>'
                 f'<circle cx="-5.6" cy="-8" r="2.4" fill="{"#5C4033" if col != "#F8FAFC" else "#F8FAFC"}"/>'
                 '<path d="M-7.6,-8.4 L-10,-7.6 L-7.6,-7 Z" fill="#F59E0B"/></g></g>')
    # a coconut palm on the far bank and grass along the near bank
    o.append(palm(650, y - 14, 56, -10, .62, rnd))
    tf = "".join(f"M{F(gx)},{F(y+20)}l-2,-6M{F(gx)},{F(y+20)}l0,-7M{F(gx)},{F(y+20)}l2,-6" for gx in range(12, x1, 26))
    o.append(f'<path d="{tf}" stroke="#4D7C0F" stroke-width="1" stroke-linecap="round"/>')
    return "".join(o)


BLADE_COLS = {1: ["#5FAE3A", "#4E9A2E", "#6CBB45"],
              2: ["#4E9A2E", "#3F8A2C", "#62B03C", "#57A534"],
              3: ["#3F8A2C", "#2F7A24", "#5AA83A", "#4B9530"],
              4: ["#C9A23A", "#B58A1E", "#D9B84E", "#A8902E"]}
BLADE_H = {1: 8, 2: 12, 3: 14, 4: 14}
GRAIN_COL = {3: ["#C8D86A", "#B5CC55"], 4: ["#F2C744", "#E5B12E", "#F7D865"]}


def rice_clump(bx, by, lv, rnd, blades, stems, grains, shadows):
    """Một bụi lúa: lá thon nhọn cong ra, bông lúa rủ hạt khi trổ/chín."""
    shadows.append(f"M{F(bx-3.4)},{F(by)}a3.4,1.1 0 1,0 6.8,0a3.4,1.1 0 1,0 -6.8,0Z")
    nb = {1: 3, 2: 5, 3: 6, 4: 6}[lv]
    H = BLADE_H[lv]
    for j in range(nb):
        u = j / (nb - 1) - 0.5
        a = math.radians(u * 78 + rnd.uniform(-7, 7))
        L = H * rnd.uniform(.78, 1.08) * (1 - 0.22 * abs(u) * 2)
        sx, cx = math.sin(a), math.cos(a)
        tipx = bx + sx * L * 1.15
        tipy = by - cx * L + abs(sx) * L * 0.35
        cxl = bx + sx * L * 0.45
        cyl = by - cx * L * 0.75
        w = 1.1 if lv > 1 else 0.9
        path = (f"M{F(bx-w)},{F(by)}Q{F(cxl-w*.6)},{F(cyl)} {F(tipx)},{F(tipy)}"
                f"Q{F(cxl+w*.6)},{F(cyl)} {F(bx+w)},{F(by)}Z")
        blades.setdefault(rnd.choice(BLADE_COLS[lv]), []).append(path)
    if lv >= 3:
        for k in range(1 if lv == 3 else 2):
            side = rnd.choice([-1, 1])
            tx = bx + side * rnd.uniform(.5, 2)
            ty = by - H * rnd.uniform(1.0, 1.12)
            droop = 5.5 if lv == 4 else 3.2
            p1 = (tx + side * 3.5, ty - 1.2)
            p2 = (tx + side * 6.5, ty + droop)
            stems.append(f"M{F(bx)},{F(by)}Q{F(bx)},{F(ty+3)} {F(tx)},{F(ty)}Q{F(p1[0])},{F(p1[1])} {F(p2[0])},{F(p2[1])}")
            for i in range(6):
                t = 0.15 + i * 0.16
                gx = (1 - t) ** 2 * tx + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
                gy = (1 - t) ** 2 * ty + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
                dx = 2 * (1 - t) * (p1[0] - tx) + 2 * t * (p2[0] - p1[0])
                dy = 2 * (1 - t) * (p1[1] - ty) + 2 * t * (p2[1] - p1[1])
                m = math.hypot(dx, dy) or 1
                dx, dy = dx / m, dy / m
                off = 0.9 if i % 2 else -0.9
                gx += -dy * off
                gy += dx * off
                rx, ry = 1.25, 0.72
                deg = math.degrees(math.atan2(dy, dx))
                grains.setdefault(rnd.choice(GRAIN_COL[lv]), []).append(
                    f"M{F(gx-dx*rx)},{F(gy-dy*rx)}a{rx},{ry} {F(deg)} 1,0 {F(2*dx*rx)},{F(2*dy*rx)}"
                    f"a{rx},{ry} {F(deg)} 1,0 {F(-2*dx*rx)},{F(-2*dy*rx)}Z")


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

    # sky details: clouds, birds, kite
    o.append(cloud(470, 128, 1.0) + cloud(730, 40, .7) + cloud(250, 150, .6))
    o.append(birds(560, 40))
    kite_x, kite_y = 470, 138

    # village notice board with a thatched cap
    o.append(signboard(790, 16, cal, cc, longest, current, best))

    # hut, haystack, banana trees beside the field
    o.append(banana(560, 200, .9, rnd) + banana(700, 203, 1.0, rnd))
    o.append(hut(600, 200, .55))
    o.append(haystack(682, 206, .8))
    o.append(palm(756, 200, 120, -26, .95, rnd))

    # ---- the paddy field: 53 weeks x 7 days, oblique perspective ----
    cw, rh, sk = 20, 25, 9
    x0, y0 = 70, 214
    o.append(f'<path d="M{x0-10+7*sk},{y0-6} L{x0+len(weeks)*cw+7*sk+6},{y0-6} L{x0+len(weeks)*cw+8},{y0+7*rh+6} L{x0-16},{y0+7*rh+6} Z" fill="#8A6A3A"/>')
    tiles = {0: [], 1: [], 2: [], 3: [], 4: []}
    water_cells = []
    blades = [dict() for _ in range(7)]   # fill colour -> [paths]
    stems = [[] for _ in range(7)]
    grains = [dict() for _ in range(7)]
    shadows = [[] for _ in range(7)]
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
            n = 2 if lv == 1 else 3
            for k in range(n):
                cx = xl + cw * (k + 1) / (n + 1) - sk * 0.55 + rnd.uniform(-1, 1)
                cy = yt + rh * 0.74 + rnd.uniform(-1.5, 1.5)
                rice_clump(cx, cy, lv, rnd, blades[di], stems[di], grains[di], shadows[di])
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
        if not blades[di]:
            continue
        base = y0 + di * rh + rh * 0.74
        body = f'<path d="{"".join(shadows[di])}" fill="#1F4D2B" opacity=".22"/>'
        body += "".join(f'<path d="{"".join(v)}" fill="{c}"/>' for c, v in blades[di].items())
        if stems[di]:
            body += f'<path d="{"".join(stems[di])}" stroke="#8A7A2A" stroke-width=".7" stroke-linecap="round"/>'
        body += "".join(f'<path d="{"".join(v)}" fill="{c}"/>' for c, v in grains[di].items())
        o.append(f'<g transform="translate(0,{F(base)})"><g><animateTransform attributeName="transform" type="skewX" '
                 f'values="0;-5;0;3;0" dur="{F(5+di*.25)}s" repeatCount="indefinite"/>'
                 f'<g transform="translate(0,{F(-base)})">{body}</g></g></g>')
    # egrets in flooded plots
    picks = [c for c in water_cells if 1 <= c[1] <= 5]
    rnd.shuffle(picks)
    for (wi, di, xl, yt) in sorted(picks[:3], key=lambda c: c[1]):
        o.append(egret(xl + cw * 0.4 - sk * .5, yt + rh * 0.75, flip=rnd.random() < .5))

    # scarecrow standing in the middle of the paddies
    o.append(scarecrow(x0 + 31 * cw + 3 * sk, y0 + 2 * rh + rh * 0.8))
    # beside the field: a grazing buffalo on the left, a banana tree on the right
    o.append(buffalo(40, 382))
    o.append(banana(1172, 404, .8, rnd))

    # front dyke with the farmer, month labels
    fy = y0 + 7 * rh + 6
    o.append(f'<path d="M{x0-20},{fy} L{x0+len(weeks)*cw+12},{fy} L{x0+len(weeks)*cw+12},{fy+10} L{x0-20},{fy+10} Z" fill="#A27B48"/>')
    o.append(f'<path d="M{x0-20},{fy+1} L{x0+len(weeks)*cw+12},{fy+1}" stroke="#6E9C34" stroke-width="2.5"/>')
    o.append(farmer(x0 + len(weeks) * cw * 0.62, fy + 2))
    # ducks running along the dyke + a kid flying a kite
    o.append(dyke_ducks(x0 + 120, fy + 3))
    kid_x = x0 + len(weeks) * cw * 0.42
    o.append(f'<path d="M{F(kid_x+4)},{F(fy-14)} Q{F((kid_x+kite_x)/2)},{F(fy-60)} {kite_x},{kite_y+18}" stroke="#F8FAFC" stroke-width=".8" opacity=".9"/>')
    o.append(kid(kid_x, fy + 2))
    o.append(kite(kite_x, kite_y))
    # grass tufts & wild flowers along the dyke
    tf = []
    fl = []
    for i in range(70):
        gx = x0 - 16 + rnd.uniform(0, len(weeks) * cw + 26)
        tf.append(f"M{F(gx)},{F(fy+1)}l-2,-5M{F(gx)},{F(fy+1)}l0,-6M{F(gx)},{F(fy+1)}l2,-5")
        if i % 4 == 0:
            fl.append(f'<circle cx="{F(gx+3)}" cy="{F(fy-3)}" r="1.6" fill="{rnd.choice(["#FDE047", "#F9A8D4", "#FFFFFF"])}"/>')
    o.append(f'<path d="{"".join(tf)}" stroke="#4D7C0F" stroke-width="1" stroke-linecap="round"/>' + "".join(fl))
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
    o.append(canal(fy + 150, 690, rnd))
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
