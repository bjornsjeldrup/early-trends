#!/usr/bin/env python3
# Regenerate Trend lifecycle charts from trends/tracker.json.
#
# Usage (from the repo root):
#   python3 scripts/lifecycle.py
#   python3 scripts/lifecycle.py --self-test
#
# Reads each pick's lifecycle object and rewrites the block between
# <!-- lifecycle:start --> and <!-- lifecycle:end --> on that product page.
# Also refreshes the mini curve on product cards and the two groups on
# categories/our-misses.html. Safe to run again after editing tracker.json.
# The self-test fixture is rendered in memory only and is not a public page.

import math
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VW, VH = 1000.0, 385.0
PHASE_X = {
    "sleeper": (0.0, 260.0),
    "early": (260.0, 440.0),
    "rising": (440.0, 600.0),
    "mainstream": (600.0, 800.0),
    "peak": (800.0, 1000.0),
}
PHASE_ORDER = ["sleeper", "early", "rising", "mainstream", "peak"]
PHASE_LABEL = {
    "sleeper": "Sleeper",
    "early": "Early",
    "rising": "Rising",
    "mainstream": "Mainstream",
    "peak": "Peak / Plateau",
    "fizzled": "Fizzled",
}
MINI_LABEL = {
    "sleeper": "Sleeper",
    "early": "Early",
    "rising": "Rising",
    "mainstream": "Mainstream",
    "peak": "Peak",
    "fizzled": "Fizzled",
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS_LONG = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
# Fixed schematic from the approved curve. Markers move; this path does not.
CURVE_DATA = (
    "0.0,321.7 14.3,319.1 28.7,315.8 43.0,311.9 57.3,307.7 71.7,303.5 "
    "86.0,299.7 100.4,297.0 114.7,295.5 129.0,295.6 143.4,297.1 157.7,299.9 "
    "172.0,303.5 186.4,307.4 200.7,311.2 215.1,314.5 229.4,317.1 243.7,318.9 "
    "258.1,319.9 272.4,320.2 286.7,320.0 301.1,319.2 315.4,318.0 329.7,316.5 "
    "344.1,314.5 358.4,312.2 372.8,309.4 387.1,306.1 401.4,302.3 415.8,297.9 "
    "430.1,292.8 444.4,287.1 458.8,280.6 473.1,273.4 487.5,265.5 501.8,257.0 "
    "516.1,247.8 530.5,238.1 544.8,228.1 559.1,217.9 573.5,207.7 587.8,197.7 "
    "602.2,187.9 616.5,178.7 630.8,170.0 645.2,162.0 659.5,154.8 673.8,148.2 "
    "688.2,142.4 702.5,137.3 716.8,132.8 731.2,128.9 745.5,125.6 759.9,122.7 "
    "774.2,120.3 788.5,118.2 802.9,116.5 817.2,115.0 831.5,113.8 845.9,113.5 "
    "860.2,113.7 874.6,114.2 888.9,115.1 903.2,116.3 917.6,117.6 931.9,119.2 "
    "946.2,120.9 960.6,122.8 974.9,124.8 989.2,126.9 1000.0,128.6"
)
CURVE = [tuple(float(n) for n in pair.split(",")) for pair in CURVE_DATA.split()]
ARTICLE_RE = re.compile(r'<article class="trend-card"[^>]*>.*?</article>', re.S)
BLOCK_RE = re.compile(r"[ \t]*<!-- lifecycle:start -->.*?<!-- lifecycle:end -->\n?", re.S)
MINI_RE = re.compile(r"[ \t]*<!-- lifecycle-mini:start -->.*?<!-- lifecycle-mini:end -->\n?", re.S)
GROUPS_RE = re.compile(r"[ \t]*<!-- misses-groups:start -->.*?<!-- misses-groups:end -->", re.S)


def n(value):
    return f"{value:.1f}"


def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def parse_date(raw):
    if not raw or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(raw)):
        return None
    year, month, day = (int(part) for part in raw.split("-"))
    return date(year, month, day)


def signal_start(pick):
    """Full day when the repo has one, else the first of a YYYY-MM. Year-only stays unset."""
    raw = pick.get("first_clear_signal")
    parsed = parse_date(raw)
    if parsed:
        return parsed
    fs = (pick.get("lifecycle") or {}).get("first_signal") or ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", fs):
        return parse_date(fs)
    if re.fullmatch(r"\d{4}-\d{2}", fs):
        year, month = (int(part) for part in fs.split("-"))
        return date(year, month, 1)
    return None


def age_months(start, end):
    return (end.year - start.year) * 12 + (end.month - start.month) + (end.day - start.day) / 30.437


def phase_from_age(start, when):
    if not start or not when:
        return None
    age = age_months(start, when)
    if age < 3:
        return "early"
    if age <= 6:
        return "rising"
    return "mainstream"


def curve_y(x):
    x = max(0.0, min(VW, x))
    for (x0, y0), (x1, y1) in zip(CURVE, CURVE[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return y0
            t = (x - x0) / (x1 - x0)
            return y0 + (y1 - y0) * t
    return CURVE[-1][1]


def x_in(phase, frac):
    start, end = PHASE_X[phase]
    return start + (end - start) * frac


def fizzled_y(x, ring_x):
    if x <= ring_x:
        return curve_y(x)
    span = 220.0
    t = min(1.0, (x - ring_x) / span)
    base = curve_y(ring_x)
    if t < 0.45:
        return base - math.sin((t / 0.45) * math.pi) * 16.0
    flat = min(328.0, base + 6.0)
    u = min(1.0, (t - 0.45) / 0.55)
    return base + (flat - base) * u


def sample_x(x0, x1, step=8.0):
    xs = []
    x = float(x0)
    while x < x1 - 0.01:
        xs.append(x)
        x += step
    xs.append(float(x1))
    return xs


def path_d(points, close=False):
    head = f"M{n(points[0][0])},{n(points[0][1])}"
    rest = "".join(f"L{n(x)},{n(y)}" for x, y in points[1:])
    if close:
        rest += f"L{n(points[-1][0])},{n(VH)}L0,{n(VH)}Z"
    return head + rest


def month_year(value, long=False):
    names = MONTHS_LONG if long else MONTHS
    if re.fullmatch(r"\d{4}", value or ""):
        return value
    if re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", value or ""):
        year, month = value.split("-")[:2]
        return f"{names[int(month) - 1]} {year}"
    return value or ""


def spotted_text(iso, long=False):
    names = MONTHS_LONG if long else MONTHS
    year, month, day = iso.split("-")
    return f"{int(day)} {names[int(month) - 1]} {year}"


def aria_label(pick):
    phase = pick["lifecycle"]["phase"]
    spotted = spotted_text(pick["lifecycle"]["spotted"])
    if phase == "fizzled":
        return f"Lifecycle: Fizzled, spotted {spotted}"
    return f"Lifecycle: {PHASE_LABEL[phase]} phase, spotted {spotted}"


def layout(pick):
    lc = pick["lifecycle"]
    phase = lc["phase"]
    verdict = lc["verdict"]
    start = signal_start(pick)
    spotted = parse_date(lc.get("spotted"))
    first_x = 60.0 if lc.get("first_signal") else None
    if verdict == "fizzled":
        ring_phase = phase_from_age(start, spotted) or "early"
        if ring_phase not in PHASE_X:
            ring_phase = "early"
        ring_x = x_in(ring_phase, 0.58)
        return {
            "verdict": verdict,
            "phase": phase,
            "first_x": first_x,
            "ring_x": ring_x,
            "here_x": None,
            "end_x": 760.0,
        }
    if verdict == "late_miss":
        col = phase if phase in PHASE_X else "mainstream"
        return {
            "verdict": verdict,
            "phase": col,
            "first_x": first_x,
            "ring_x": x_in(col, 0.56),
            "here_x": x_in(col, 0.84),
            "end_x": None,
        }
    current = phase if phase in PHASE_X else "early"
    spotted_phase = phase_from_age(start, spotted) or current
    if spotted_phase not in PHASE_X:
        spotted_phase = current
    if PHASE_ORDER.index(spotted_phase) > PHASE_ORDER.index(current):
        spotted_phase = current
    if spotted_phase == current:
        ring_x = x_in(current, 0.30)
        here_x = x_in(current, 0.52)
    else:
        ring_x = x_in(spotted_phase, 0.70)
        here_x = x_in(current, 0.40)
    return {
        "verdict": verdict,
        "phase": current,
        "first_x": first_x,
        "ring_x": ring_x,
        "here_x": here_x,
        "end_x": None,
    }


def point_on(x, kind, ring_x):
    if kind == "fizzled":
        return fizzled_y(x, ring_x)
    return curve_y(x)


def desc_text(pick, lay):
    lc = pick["lifecycle"]
    name = pick["product_name"]
    bits = ["Schematic phase view, not a measured chart."]
    if lay["verdict"] == "fizzled":
        when = month_year(lc.get("fizzled_on") or lc["spotted"][:7], long=True)
        bits.append(
            f"{name} fizzled in {when} – no breakout after 6 months."
        )
    elif lay["verdict"] == "late_miss":
        bits.append(f"{name} was spotted late, in the {PHASE_LABEL[lay['phase']]} phase.")
    else:
        bits.append(f"{name} is in the {PHASE_LABEL[lay['phase']]} phase.")
    if lc.get("first_signal"):
        bits.append(f"First signal in {month_year(lc['first_signal'], long=True)}.")
    bits.append(f"Spotted on {spotted_text(lc['spotted'], long=True)}.")
    if lay["here_x"] is not None:
        bits.append("The current point is marked You are here.")
    return " ".join(bits)


def svg_title(pick, lay):
    if lay["verdict"] == "late_miss":
        return "Spotted late"
    if lay["verdict"] == "fizzled":
        return "Didn't take off"
    return f"Trend lifecycle for {pick['product_name']}"


def edge(x, y, tx, ty, radius):
    dx, dy = tx - x, ty - y
    dist = math.hypot(dx, dy) or 1.0
    return x + dx / dist * radius, y + dy / dist * radius


def annotations(pick, lay):
    lc = pick["lifecycle"]
    html = []
    leaders = []
    ring_y = point_on(lay["ring_x"], "fizzled" if lay["verdict"] == "fizzled" else "standard", lay["ring_x"])
    if lay["first_x"] is not None:
        html.append(
            f'<div class="lc-anno lc-anno-first" style="left:3.5%;top:50%">{esc("First signal")}<br>{esc(month_year(lc["first_signal"]))}</div>'
        )
    if lay["verdict"] == "late_miss":
        spot_left, spot_top = 46.0, 9.0
        spot_lines = ("Spotted late", spotted_text(lc["spotted"]))
    elif lay["verdict"] == "fizzled":
        spot_left, spot_top = 3.5, 5.0
        spot_lines = ("Spotted", spotted_text(lc["spotted"]))
    else:
        spot_left, spot_top = 3.5, 4.0
        spot_lines = ("Spotted by Early Trends", spotted_text(lc["spotted"]))
    html.append(
        f'<div class="lc-anno lc-anno-spotted" style="left:{n(spot_left)}%;top:{n(spot_top)}%">'
        + "<br>".join(esc(line) for line in spot_lines)
        + "</div>"
    )
    end_x = (spot_left + 10) / 100.0 * VW
    end_y = (spot_top + 16) / 100.0 * VH
    x1, y1 = edge(lay["ring_x"], ring_y, end_x, end_y, 12)
    leaders.append(
        f'<line class="lc-leader" x1="{n(x1)}" y1="{n(y1)}" x2="{n(end_x)}" y2="{n(end_y)}" stroke="#e6ecff" stroke-opacity="0.55" stroke-width="1.2"/>'
    )
    if lay["here_x"] is not None:
        here_y = curve_y(lay["here_x"])
        here_pct = lay["here_x"] / VW * 100.0
        here_top_pct = here_y / VH * 100.0
        if here_y < 180:
            # Crest sits high. Keep the label just under the dot so it stays
            # in the same phase column on both wide and narrow screens.
            here_left = min(70.0, max(4.0, here_pct - 11.0))
            here_top = min(82.0, here_top_pct + 12.0)
            target_x = (here_left + 6.0) / 100.0 * VW
            target_y = here_top / 100.0 * VH
            lx, ly = edge(lay["here_x"], here_y, target_x, target_y, 16)
            lx2, ly2 = target_x, target_y
        else:
            here_left = here_pct + 2.6
            here_top = max(8.0, here_top_pct - 3.0)
            lx, ly = lay["here_x"] + 14, here_y
            lx2, ly2 = lay["here_x"] + 36, here_y
        html.append(
            f'<div class="lc-anno lc-anno-here" style="left:{n(here_left)}%;top:{n(here_top)}%">You are here</div>'
        )
        leaders.append(
            f'<line class="lc-leader" x1="{n(lx)}" y1="{n(ly)}" x2="{n(lx2)}" y2="{n(ly2)}" stroke="#ff5ea8" stroke-opacity="0.8" stroke-width="1.4"/>'
        )
    if lay["verdict"] == "fizzled":
        when = month_year(lc.get("fizzled_on") or lc["spotted"][:7])
        html.append(
            '<div class="lc-anno lc-anno-fizzled" style="left:54%;top:52%">'
            f'{esc("Fizzled · " + when)}<br>{esc("No breakout after 6 months")}</div>'
        )
        end_y = fizzled_y(lay["end_x"], lay["ring_x"])
        x1, y1 = edge(lay["end_x"], end_y, 620, 230, 10)
        leaders.append(
            f'<line class="lc-leader" x1="{n(x1)}" y1="{n(y1)}" x2="620" y2="230" stroke="#ff5ea8" stroke-opacity="0.75" stroke-width="1.3"/>'
        )
        mid_x = lay["ring_x"] + (VW - lay["ring_x"]) * 0.42
        label_y = max(36.0, curve_y(mid_x) - 34)
        html.append(
            f'<div class="lc-anno lc-anno-expected" style="left:{n(mid_x / VW * 100 - 6)}%;top:{n(label_y / VH * 100)}%">Expected path</div>'
        )
    return html, leaders, ring_y


def render_svg(pick, uid):
    lay = layout(pick)
    lc = pick["lifecycle"]
    title_id = f"lc-title-{uid}"
    desc_id = f"lc-desc-{uid}"
    label = aria_label(pick)
    annos, leaders, ring_y = annotations(pick, lay)
    parts = []
    if lay["verdict"] == "fizzled":
        actual = [(x, fizzled_y(x, lay["ring_x"])) for x in sample_x(0, lay["end_x"])]
        expected = [(x, curve_y(x)) for x in sample_x(lay["ring_x"], VW)]
        parts.append(f'<path d="{path_d(actual, close=True)}" fill="url(#lc-fill-{uid})" fill-opacity="0.85"/>')
        parts.append(
            f'<path d="{path_d(actual)}" fill="none" stroke="url(#lc-stroke-{uid})" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>'
        )
        parts.append(
            f'<path d="{path_d(expected)}" fill="none" stroke="#7d8bb5" stroke-width="2.4" stroke-dasharray="7 7" stroke-linecap="round"/>'
        )
    else:
        parts.append(f'<path d="{path_d(CURVE, close=True)}" fill="url(#lc-fill-{uid})"/>')
        parts.append(
            f'<path d="{path_d(CURVE)}" fill="none" stroke="url(#lc-stroke-{uid})" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>'
        )
    if lay["first_x"] is not None:
        fy = curve_y(lay["first_x"]) if lay["verdict"] != "fizzled" else fizzled_y(lay["first_x"], lay["ring_x"])
        parts.append(f'<circle class="lc-first" cx="{n(lay["first_x"])}" cy="{n(fy)}" r="5" fill="#7d8bb5"/>')
    parts.extend(leaders)
    ring_stroke = "#ff5ea8" if lay["verdict"] == "late_miss" else "#f4fffb"
    parts.append(
        f'<circle class="lc-ring" cx="{n(lay["ring_x"])}" cy="{n(ring_y)}" r="9" fill="#0b1020" stroke="{ring_stroke}" stroke-width="2.6"/>'
    )
    if lay["here_x"] is not None:
        hy = curve_y(lay["here_x"])
        parts.append(
            f'<g transform="translate({n(lay["here_x"])},{n(hy)})">'
            '<circle r="16" fill="#ff5ea8" fill-opacity="0.28"/>'
            '<circle class="lc-pulse" r="11" fill="#ff5ea8"/>'
            '<circle r="7.5" fill="#ff5ea8"/>'
            "</g>"
        )
    if lay["end_x"] is not None:
        ey = fizzled_y(lay["end_x"], lay["ring_x"])
        parts.append(f'<circle class="lc-end" cx="{n(lay["end_x"])}" cy="{n(ey)}" r="6" fill="#7d8bb5"/>')
    cols = []
    phases = []
    for key in PHASE_ORDER:
        on = lay["verdict"] != "fizzled" and key == lay["phase"]
        cls = ' class="is-current"' if on else ""
        cols.append(f"<span{cls}></span>")
        text = "Peak /<wbr>Plateau" if key == "peak" else esc(PHASE_LABEL[key])
        phases.append(f"<li{cls}>{text}</li>")
    variant = {"late_miss": "is-late", "fizzled": "is-fizzled"}.get(lay["verdict"], "is-early")
    svg = (
        f'<svg viewBox="0 0 1000 385" width="100%" role="img" aria-label="{esc(label)}" aria-describedby="{desc_id}" preserveAspectRatio="xMidYMid meet">'
        f'<title id="{title_id}">{esc(svg_title(pick, lay))}</title>'
        f'<desc id="{desc_id}">{esc(desc_text(pick, lay))}</desc>'
        "<defs>"
        f'<linearGradient id="lc-stroke-{uid}" x1="0" y1="0" x2="1000" y2="0" gradientUnits="userSpaceOnUse">'
        '<stop offset="0%" stop-color="#38e1ff"/>'
        '<stop offset="55%" stop-color="#8a7dff"/>'
        '<stop offset="100%" stop-color="#ff5ea8"/>'
        "</linearGradient>"
        f'<linearGradient id="lc-fill-{uid}" x1="0" y1="0" x2="1000" y2="0" gradientUnits="userSpaceOnUse">'
        '<stop offset="0%" stop-color="#38e1ff" stop-opacity="0.22"/>'
        '<stop offset="55%" stop-color="#8a7dff" stop-opacity="0.16"/>'
        '<stop offset="100%" stop-color="#ff5ea8" stop-opacity="0.14"/>'
        "</linearGradient>"
        "</defs>"
        + "".join(parts)
        + "</svg>"
    )
    ann = "".join(annos)
    return (
        f'<div class="lifecycle-chart {variant}">'
        f'<div class="lifecycle-cols" aria-hidden="true">{"".join(cols)}</div>'
        f'<ul class="lifecycle-phases">{"".join(phases)}</ul>'
        '<div class="lifecycle-plot"><div class="lifecycle-plot-inner">'
        f"{svg}<div class=\"lc-annos\">{ann}</div>"
        "</div></div></div>"
    )


def render_product_block(pick):
    uid = pick["slug"]
    label = aria_label(pick)
    chart = render_svg(pick, uid)
    return (
        "  <!-- lifecycle:start -->\n"
        f'  <section class="lifecycle-section" aria-label="{esc(label)}">\n'
        '    <div class="wrap">\n'
        f'      <h2 id="lifecycle-{uid}">Trend lifecycle</h2>\n'
        '      <p class="lifecycle-explainer">Where this product sits in its hype cycle right now.</p>\n'
        f"      {chart}\n"
        '      <p class="lifecycle-caption">Schematic phase view, not a measured chart.</p>\n'
        "    </div>\n"
        "  </section>\n"
        "  <!-- lifecycle:end -->"
    )


def spark_xy(x, y):
    sx = x / VW * 120.0
    sy = 3.0 + (y - 110.0) / (330.0 - 110.0) * 22.0
    return sx, max(2.4, min(25.6, sy))


def render_mini(pick, uid):
    lay = layout(pick)
    phase = pick["lifecycle"]["phase"]
    variant = {"late_miss": "is-late", "fizzled": "is-fizzled"}.get(lay["verdict"], "is-early")
    if lay["verdict"] == "fizzled":
        pts = [(x, fizzled_y(x, lay["ring_x"])) for x in sample_x(0, lay["end_x"], 16)]
        dot_x, dot_y = lay["end_x"], fizzled_y(lay["end_x"], lay["ring_x"])
        dot = "#7d8bb5"
    else:
        pts = CURVE
        dot_x, dot_y = lay["here_x"], curve_y(lay["here_x"])
        dot = "#ff5ea8"
    spark = [spark_xy(x, y) for x, y in pts]
    dx, dy = spark_xy(dot_x, dot_y)
    label = f"Lifecycle: {MINI_LABEL[phase]} phase" if phase != "fizzled" else "Lifecycle: Fizzled"
    svg = (
        f'<svg viewBox="0 0 120 28" width="120" height="28" aria-hidden="true" focusable="false" preserveAspectRatio="xMidYMid meet">'
        "<defs>"
        f'<linearGradient id="lc-mini-{uid}" x1="0" y1="0" x2="120" y2="0" gradientUnits="userSpaceOnUse">'
        '<stop offset="0%" stop-color="#38e1ff"/><stop offset="100%" stop-color="#ff5ea8"/>'
        "</linearGradient></defs>"
        f'<polyline points="{" ".join(n(x) + "," + n(y) for x, y in spark)}" fill="none" stroke="url(#lc-mini-{uid})" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{n(dx)}" cy="{n(dy)}" r="2.4" fill="{dot}"/>'
        "</svg>"
    )
    return (
        "<!-- lifecycle-mini:start -->"
        f'<p class="lifecycle-mini {variant}" aria-label="{esc(label)}">{svg}'
        f'<span aria-hidden="true">{esc(MINI_LABEL[phase])}</span></p>'
        "<!-- lifecycle-mini:end -->"
    )


def upsert_product(html, block):
    if "<!-- lifecycle:start -->" in html:
        return BLOCK_RE.sub(lambda _match: block + "\n", html, count=1)
    match = re.search(r'\n[ \t]*<article class="section">', html)
    if not match:
        raise SystemExit("product page has no article section to insert before")
    return html[: match.start()] + "\n\n" + block + "\n" + html[match.start() :]


def upsert_mini(card, mini):
    line = mini.strip()
    if "<!-- lifecycle-mini:start -->" in card:
        found = re.search(r"^([ \t]*)<!-- lifecycle-mini:start -->", card, re.M)
        indent = found.group(1) if found else "    "
        return MINI_RE.sub(indent + line + "\n", card, count=1)
    match = re.search(r'\n([ \t]*)<div class="card-meta">', card)
    if not match:
        match = re.search(r'\n([ \t]*)<p class="where-to-buy">', card)
    if not match:
        return card
    indent = match.group(1)
    return card[: match.start()] + "\n" + indent + line + card[match.start() :]


def card_slug(card, known):
    match = re.search(r'<h3>\s*<a href="([^"]+)"', card)
    if not match:
        return None
    name = match.group(1).split("?")[0].rstrip("/").split("/")[-1]
    if name.endswith(".html"):
        name = name[: -len(".html")]
    return name if name in known else None


def update_cards(html, picks):
    out = []
    last = 0
    count = 0
    seen = {}
    for match in ARTICLE_RE.finditer(html):
        out.append(html[last : match.start()])
        card = match.group(0)
        slug = card_slug(card, picks)
        if slug:
            seen[slug] = seen.get(slug, 0) + 1
            card = upsert_mini(card, render_mini(picks[slug], f"{slug}-mini-{seen[slug]}"))
            count += 1
        out.append(card)
        last = match.end()
    out.append(html[last:])
    return "".join(out), count


def html_files():
    found = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        for name in filenames:
            if name.endswith(".html"):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def load_picks():
    import json

    with open(os.path.join(ROOT, "trends", "tracker.json"), encoding="utf-8") as handle:
        data = json.load(handle)
    picks = {}
    for pick in data["picks"]:
        lc = pick.get("lifecycle") or {}
        if lc.get("phase") not in PHASE_LABEL or lc.get("verdict") not in ("early_pick", "late_miss", "fizzled"):
            raise SystemExit(f"{pick['id']} is missing a lifecycle phase or verdict")
        if not lc.get("spotted"):
            raise SystemExit(f"{pick['id']} is missing lifecycle.spotted")
        picks[pick["slug"]] = pick
    return picks, data["picks"]


def dedent(card):
    lines = card.split("\n")
    indents = [len(line) - len(line.lstrip(" ")) for line in lines if line.strip()]
    cut = min(indents) if indents else 0
    return "\n".join(line[cut:] if line.startswith(" " * cut) else line for line in lines).strip() + "\n"


def rewrite_urls(card, src_file, dest_file):
    src_dir = os.path.dirname(src_file)
    dest_dir = os.path.dirname(dest_file)

    def repl(attr):
        def inner(match):
            url = match.group(1)
            if re.match(r"^[a-z]+:", url) or url.startswith("#"):
                return match.group(0)
            target = os.path.normpath(os.path.join(src_dir, url))
            return f'{attr}="{os.path.relpath(target, dest_dir)}"'

        return inner

    card = re.sub(r'href="([^"]+)"', repl("href"), card)
    card = re.sub(r'src="([^"]+)"', repl("src"), card)
    return card


def best_cards(picks):
    best = {}
    for path in html_files():
        html = read(path)
        rank = 2 if path.endswith(os.path.join("categories", "our-misses.html")) else 1
        for match in ARTICLE_RE.finditer(html):
            card = match.group(0)
            slug = card_slug(card, picks)
            if not slug:
                continue
            if slug not in best or rank > best[slug][0]:
                best[slug] = (rank, path, card)
    return best


def render_miss_entry(pick, card_html):
    uid = pick["slug"] + "-miss"
    return (
        '<article class="miss-entry">\n'
        '<div class="card-grid miss-card-grid">\n'
        f"{card_html.strip()}\n"
        "</div>\n"
        '<div class="miss-curve">\n'
        "<h3>Trend lifecycle</h3>\n"
        '<p class="lifecycle-explainer">Where this product sits in its hype cycle right now.</p>\n'
        f"{render_svg(pick, uid)}\n"
        '<p class="lifecycle-caption">Schematic phase view, not a measured chart.</p>\n'
        "</div>\n"
        "</article>\n"
    )


def render_groups(ordered, picks, cards, dest):
    late = []
    fizzled = []
    for pick in ordered:
        verdict = pick["lifecycle"]["verdict"]
        if verdict == "fizzled":
            fizzled.append(pick)
        elif verdict == "late_miss" and pick.get("shelf") == "our-misses":
            late.append(pick)
    chunks = ['<h2 id="spotted-too-late">Spotted too late</h2>\n']
    if not late:
        chunks.append('<p class="miss-empty">No late picks on this shelf right now.</p>\n')
    for pick in late:
        _rank, src, card = cards[pick["slug"]]
        card = rewrite_urls(dedent(card), src, dest)
        chunks.append(render_miss_entry(pick, card))
    chunks.append('<h2 id="didnt-take-off">Didn&rsquo;t take off</h2>\n')
    if not fizzled:
        chunks.append('<p class="miss-empty">Fizzles are reported after 6 months.</p>\n')
    for pick in fizzled:
        if pick["slug"] in cards:
            _rank, src, card = cards[pick["slug"]]
            card = rewrite_urls(dedent(card), src, dest)
        else:
            card = ""
        if card:
            chunks.append(render_miss_entry(pick, card))
    return "".join(chunks)


def update_misses(ordered, picks):
    dest = os.path.join(ROOT, "categories", "our-misses.html")
    html = read(dest)
    if "grouped under spotted too late" not in html:
        html = html.replace(
            "is the early pick in Tech &amp; Gadgets.</p>",
            "is the early pick in Tech &amp; Gadgets. Misses on this shelf are grouped under spotted too late and didn&rsquo;t take off.</p>",
            1,
        )
    generated = render_groups(ordered, picks, best_cards(picks), dest)
    block = "      <!-- misses-groups:start -->\n" + generated + "      <!-- misses-groups:end -->"
    if "<!-- misses-groups:start -->" in html:
        html = GROUPS_RE.sub(lambda _match: block, html, count=1)
    else:
        examples = html.find('id="examples"')
        head = html.find('<div class="section-head">', examples)
        head = html.rfind("\n", 0, head) + 1
        head_end = html.find("</div>", head) + len("</div>")
        grid = html.find('<div class="card-grid">', head_end)
        affiliate = html.find("<!-- AFFILIATE SLOT: category-our-misses-picks")
        if min(head, grid, affiliate) < 0:
            raise SystemExit("could not find the misses card block")
        notices = html[head_end:grid]
        new_head = (
            '      <div class="section-head">\n'
            "        <h2>Our misses</h2>\n"
            '        <a href="../trends/index.html">All trends &rarr;</a>\n'
            "      </div>"
        )
        html = html[:head] + new_head + "\n" + notices + block + "\n      " + html[affiliate:]
    write(dest, html)


def update_all(picks, ordered):
    pages = 0
    for slug, pick in picks.items():
        path = os.path.join(ROOT, "trends", slug + ".html")
        if not os.path.isfile(path):
            raise SystemExit("missing product page " + path)
        html = read(path)
        updated = upsert_product(html, render_product_block(pick))
        if updated != html:
            write(path, updated)
        pages += 1
    cards = 0
    for path in html_files():
        html = read(path)
        updated, count = update_cards(html, picks)
        cards += count
        if updated != html:
            write(path, updated)
    update_misses(ordered, picks)
    return pages, cards


def circle_attr(html, cls, attr):
    match = re.search(rf'<circle class="{cls}"[^>]*{attr}="([^"]+)"', html)
    if not match:
        raise AssertionError(f"missing {cls} {attr}")
    return match.group(1)


def run_self_test():
    early = {
        "slug": "fixture-early",
        "product_name": "Fixture Early",
        "first_clear_signal": "2026-08-18",
        "lifecycle": {
            "first_signal": "2026-08",
            "spotted": "2026-11-10",
            "phase": "early",
            "verdict": "early_pick",
        },
    }
    rising = {
        "slug": "fixture-rising",
        "product_name": "Fixture Rising",
        "first_clear_signal": "2026-06-01",
        "lifecycle": {
            "first_signal": "2026-06",
            "spotted": "2026-08-15",
            "phase": "rising",
            "verdict": "early_pick",
        },
    }
    late = {
        "slug": "fixture-late",
        "product_name": "Fixture Late",
        "first_clear_signal": "2024-07-18",
        "lifecycle": {
            "first_signal": "2024-07",
            "spotted": "2026-10-28",
            "phase": "mainstream",
            "verdict": "late_miss",
        },
    }
    fizzled = {
        "slug": "fixture-fizzled",
        "product_name": "Fixture Fizzled",
        "first_clear_signal": "2026-05-01",
        "lifecycle": {
            "first_signal": "2026-05",
            "spotted": "2026-05-20",
            "phase": "fizzled",
            "verdict": "fizzled",
            "fizzled_on": "2026-11",
        },
    }
    early_html = render_product_block(early)
    assert early_html == render_product_block(early)
    assert 'preserveAspectRatio="xMidYMid meet"' in early_html
    assert "preserveAspectRatio=\"none\"" not in early_html
    assert 'width="100%"' in early_html
    assert "Lifecycle: Early phase, spotted 10 Nov 2026" in early_html
    assert "<title" in early_html and "<desc" in early_html
    ring_x = float(circle_attr(early_html, "lc-ring", "cx"))
    assert 260 < ring_x < 440
    assert circle_attr(early_html, "lc-ring", "stroke") == "#f4fffb"
    assert 'class="is-current">Early' in early_html or 'class="is-current">Early</li>' in early_html
    assert "YOU ARE HERE" not in early_html  # CSS uppercases the visible words
    assert "You are here" in early_html

    rising_html = render_svg(rising, "fixture-rising")
    assert float(circle_attr(rising_html, "lc-ring", "cx")) < 440
    here = re.search(r'translate\(([0-9.]+),', rising_html)
    assert here and 440 < float(here.group(1)) < 600
    assert 'class="is-current">Rising' in rising_html
    assert 'class="is-current">Early' not in rising_html

    late_html = render_svg(late, "fixture-late")
    assert circle_attr(late_html, "lc-ring", "stroke") == "#ff5ea8"
    assert 600 < float(circle_attr(late_html, "lc-ring", "cx")) < 800
    assert "<title id=\"lc-title-fixture-late\">Spotted late</title>" in late_html
    assert "Spotted late" in late_html
    assert 'class="is-current">Mainstream' in late_html

    fizz = render_svg(fizzled, "fixture-fizzled")
    assert "Expected path" in fizz
    assert 'stroke-dasharray="7 7"' in fizz
    assert "is-current" not in fizz
    assert "You are here" not in fizz
    assert "No breakout after 6 months" in fizz
    assert "Fizzled · Nov 2026" in fizz
    assert circle_attr(fizz, "lc-end", "fill") == "#7d8bb5"
    ring = float(circle_attr(fizz, "lc-ring", "cx"))
    end = float(circle_attr(fizz, "lc-end", "cx"))
    assert curve_y(end) < fizzled_y(end, ring) - 40
    assert "preserveAspectRatio=\"none\"" not in fizz

    bare = "<main>\n  </section>\n  <article class=\"section\">\n  </article>\n</main>\n"
    once = upsert_product(bare, early_html)
    twice = upsert_product(once, early_html)
    assert once == twice
    assert once.count("lifecycle:start") == 1
    card = '<article class="trend-card">\n  <div class="body">\n    <h3><a href="trends/fixture-early.html">Fixture Early</a></h3>\n    <div class="card-meta"></div>\n  </div>\n</article>'
    mini = render_mini(early, "fixture-early-mini-1")
    c1 = upsert_mini(card, mini)
    c2 = upsert_mini(c1, mini)
    assert c1 == c2
    assert c1.count("lifecycle-mini:start") == 1
    assert 'viewBox="0 0 120 28"' in c1
    assert "preserveAspectRatio=\"none\"" not in c1

    page = os.path.join(ROOT, "trends", "fixture-fizzled.html")
    if os.path.exists(page):
        raise AssertionError("fizzled fixture must not be a public page")
    print("self-test ok")


def main(argv):
    if "--self-test" in argv:
        run_self_test()
        return
    run_self_test()
    picks, ordered = load_picks()
    pages, cards = update_all(picks, ordered)
    fixture = os.path.join(ROOT, "trends", "fixture-fizzled.html")
    if os.path.exists(fixture):
        raise SystemExit("refusing to leave a public fizzled fixture page")
    print(f"product pages: {pages}")
    print(f"cards: {cards}")


if __name__ == "__main__":
    main(sys.argv[1:])
