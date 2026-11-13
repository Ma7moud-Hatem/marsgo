"""Presentation helpers: CSS, badges, bars, checklists, and credits."""

from __future__ import annotations

import html

from .config import COLORS, GEOLOGY_COLORS

CSS = f"""
<style>
  :root {{
    --bg: {COLORS['bg']};
    --panel: {COLORS['panel']};
    --panel2: {COLORS['panel2']};
    --line: {COLORS['line']};
    --text: {COLORS['text']};
    --muted: {COLORS['muted']};
    --accent: {COLORS['accent']};
    --route: {COLORS['route']};
    --go: {COLORS['go']};
    --warn: {COLORS['warn']};
    --nogo: {COLORS['nogo']};
  }}
  html, body, [class*="css"] {{
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
  }}
  .stApp {{ background: var(--bg); color: var(--text); }}
  .block-container {{ padding-top: 0.9rem; padding-bottom: 1.2rem; max-width: 100%; }}
  section[data-testid="stSidebar"] {{
    background: #101418;
    border-right: 1px solid var(--line);
  }}
  section[data-testid="stSidebar"] .block-container {{ padding-top: 1rem; }}
  #MainMenu, footer {{ visibility: hidden; }}
  h1, h2, h3, h4 {{ color: #f3ede4; letter-spacing: -0.02em; }}
  p, li, label, span {{ color: var(--text); }}
  .stCaption, [data-testid="stCaptionContainer"] {{ color: var(--muted) !important; }}

  .mg-head {{
    display: flex; align-items: center; justify-content: space-between;
    gap: 18px; padding: 0 2px 10px 2px; flex-wrap: wrap;
  }}
  .mg-brand {{ display: flex; align-items: baseline; gap: 12px; }}
  .mg-brand .name {{
    font-size: 30px; font-weight: 800; letter-spacing: -0.04em;
    color: #f7f1e6;
  }}
  .mg-brand .name span {{ color: var(--accent); }}
  .mg-brand .tag {{
    font-size: 12px; text-transform: uppercase; letter-spacing: 0.16em;
    color: var(--muted);
  }}
  .mg-meta {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
  .chip {{
    display: inline-block; padding: 6px 11px; border-radius: 999px;
    border: 1px solid var(--line); background: var(--panel);
    color: var(--text); font-size: 12.5px; white-space: nowrap;
  }}
  .chip b {{ color: #fff; }}

  .verdict {{
    border-radius: 14px; padding: 16px 18px; border: 1px solid var(--line);
    background: linear-gradient(160deg, rgba(255,255,255,.04), rgba(255,255,255,0));
  }}
  .verdict .label {{
    font-size: 11px; letter-spacing: .18em; text-transform: uppercase;
    color: var(--muted); margin-bottom: 2px;
  }}
  .verdict .word {{
    font-size: 46px; line-height: 1; font-weight: 900; letter-spacing: -.03em;
  }}
  .verdict .why {{ margin-top: 8px; font-size: 13px; line-height: 1.45; color: #cfd6de; }}
  .verdict.go {{ border-color: rgba(46,204,113,.45); box-shadow: inset 0 0 40px rgba(46,204,113,.07); }}
  .verdict.go .word {{ color: var(--go); }}
  .verdict.nogo {{ border-color: rgba(231,76,60,.55); box-shadow: inset 0 0 40px rgba(231,76,60,.10); }}
  .verdict.nogo .word {{ color: var(--nogo); }}
  .verdict.warn .word {{ color: var(--warn); }}

  .grid {{ display: grid; gap: 8px; }}
  .card {{
    background: var(--panel); border: 1px solid var(--line); border-radius: 11px;
    padding: 10px 12px;
  }}
  .card .k {{
    font-size: 10.5px; letter-spacing: .14em; text-transform: uppercase;
    color: var(--muted); margin-bottom: 3px;
  }}
  .card .v {{ font-size: 22px; font-weight: 750; color: #fff; letter-spacing: -.02em; }}
  .card .s {{ font-size: 11.5px; color: var(--muted); margin-top: 2px; }}

  .sect {{
    font-size: 11px; letter-spacing: .17em; text-transform: uppercase;
    color: var(--muted); margin: 14px 0 7px 1px;
  }}

  .bar-row {{ margin: 9px 0 12px 0; }}
  .bar-head {{
    display: flex; justify-content: space-between; gap: 10px;
    font-size: 12.5px; margin-bottom: 4px;
  }}
  .bar-head .lbl {{ font-weight: 650; color: #fff; }}
  .bar-head .val {{ color: var(--muted); font-variant-numeric: tabular-nums; }}
  .bar {{
    position: relative; height: 9px; border-radius: 999px;
    background: #232a31; overflow: hidden;
  }}
  .bar .fill {{ height: 100%; border-radius: 999px; }}
  .bar .mark {{
    position: absolute; top: -2px; bottom: -2px; width: 2px;
    background: #ffffffaa;
  }}

  .check {{
    display: flex; gap: 10px; align-items: flex-start; padding: 8px 0;
    border-bottom: 1px solid #20262c;
  }}
  .check:last-child {{ border-bottom: 0; }}
  .check .ico {{ width: 19px; text-align: center; font-size: 14px; line-height: 1.3; }}
  .check .body {{ flex: 1; }}
  .check .top {{ display: flex; justify-content: space-between; gap: 8px; }}
  .check .nm {{ font-size: 13px; font-weight: 650; color: #fff; }}
  .check .vl {{ font-size: 12.5px; color: var(--muted); font-variant-numeric: tabular-nums; }}
  .check .dt {{ font-size: 11.5px; color: var(--muted); margin-top: 2px; line-height: 1.35; }}
  .pass .ico {{ color: var(--go); }}
  .warn .ico {{ color: var(--warn); }}
  .fail .ico {{ color: var(--nogo); }}

  .chips {{ display: flex; gap: 6px; flex-wrap: wrap; margin: 2px 0 8px 0; }}
  .lchip {{
    font-size: 10.5px; letter-spacing: .1em; text-transform: uppercase;
    border: 1px solid var(--line); border-radius: 999px; padding: 4px 8px;
    color: var(--muted); background: #101418;
  }}
  .lchip.on {{ color: #071014; background: var(--route); border-color: var(--route); font-weight: 700; }}

  .legend {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 6px; }}
  .legend .it {{ display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--muted); }}
  .legend .sw {{ width: 10px; height: 10px; border-radius: 3px; }}

  .station-head {{ display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }}
  .station-head .t {{ font-size: 17px; font-weight: 750; color: #fff; }}
  .station-head .sol {{ font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: var(--accent); }}
  .sci {{ font-size: 12.5px; line-height: 1.45; color: #cfd6de; }}
  .sci b {{ color: #fff; }}
  .unit-tag {{
    display: inline-block; padding: 2px 8px; border-radius: 5px; font-size: 11px;
    font-weight: 700; color: #101418; margin-right: 6px;
  }}

  .field-card {{
    border: 1px solid var(--route); border-radius: 16px; padding: 20px 24px;
    background: linear-gradient(150deg, rgba(56,225,255,.10), rgba(56,225,255,.02));
    margin-bottom: 10px;
  }}
  .field-card .k {{ font-size: 11px; letter-spacing: .2em; text-transform: uppercase; color: #9fe9ff; }}
  .field-card .big {{ font-size: 40px; font-weight: 850; color: #fff; line-height: 1.1; margin: 2px 0 2px; }}
  .field-card .sub {{ font-size: 15px; color: #cfe9f2; }}

  .foot {{
    margin-top: 14px; padding-top: 10px; border-top: 1px solid var(--line);
    font-size: 10.5px; line-height: 1.5; color: #78828c;
  }}
  .foot b {{ color: #aab3bc; }}

  details summary {{ cursor: pointer; color: var(--muted); font-size: 12px; }}
</style>
"""


def inject_css(st) -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def fmt_duration(hours: float) -> str:
    total = max(0, int(round(hours * 60)))
    return f"{total // 60} h {total % 60:02d} m"


def status_icon(status: str) -> str:
    return {"pass": "●", "warn": "▲", "fail": "✕"}.get(status, "•")


def verdict_badge(verdict: str, reason: str) -> str:
    cls = "go" if verdict == "GO" else "nogo"
    return (
        f'<div class="verdict {cls}">'
        f'<div class="label">EVA verdict</div>'
        f'<div class="word">{verdict}</div>'
        f'<div class="why">{html.escape(reason)}</div>'
        f"</div>"
    )


def metric_grid(items: list[tuple[str, str, str]], cols: int = 3) -> str:
    cells = "".join(
        f'<div class="card"><div class="k">{html.escape(k)}</div>'
        f'<div class="v">{html.escape(v)}</div>'
        f'<div class="s">{html.escape(s)}</div></div>'
        for k, v, s in items
    )
    return f'<div class="grid" style="grid-template-columns:repeat({cols},1fr)">{cells}</div>'


def _bar_color(frac: float) -> str:
    if frac >= 0.90:
        return COLORS["nogo"]
    if frac >= 0.75:
        return COLORS["warn"]
    return COLORS["go"]


def suit_bars(consumables: list[dict], reserve_frac: float) -> str:
    out = []
    for r in consumables:
        frac = min(1.0, max(0.0, r["frac"]))
        pct = frac * 100
        reserve_mark = (1.0 - reserve_frac) * 100
        unit = r["unit"]
        dec = r["decimals"]
        reserve_left = max(0.0, 1.0 - frac) * 100
        out.append(
            f'<div class="bar-row">'
            f'<div class="bar-head"><span class="lbl">{html.escape(r["label"])}</span>'
            f'<span class="val">{r["used"]:.{dec}f} / {r["capacity"]:.{dec}f} {unit}'
            f' · {reserve_left:.0f}% left</span></div>'
            f'<div class="bar"><div class="fill" style="width:{pct:.1f}%;'
            f'background:{_bar_color(frac)}"></div>'
            f'<div class="mark" style="left:{reserve_mark:.1f}%"></div></div>'
            f"</div>"
        )
    out.append(
        '<div style="font-size:10.5px;color:#78828c;margin-top:-2px">'
        "White marker = walk-back reserve threshold. Bars show use vs. capacity.</div>"
    )
    return "".join(out)


def checklist(constraints: list[dict]) -> str:
    rows = []
    for c in constraints:
        rows.append(
            f'<div class="check {c["status"]}">'
            f'<div class="ico">{status_icon(c["status"])}</div>'
            f'<div class="body"><div class="top"><span class="nm">{html.escape(c["label"])}</span>'
            f'<span class="vl">{html.escape(str(c["value"]))}</span></div>'
            f'<div class="dt">{html.escape(c["detail"])}</div></div></div>'
        )
    return "".join(rows)


def layer_chips(names: list[str]) -> str:
    return '<div class="chips">' + "".join(
        f'<span class="lchip on">{html.escape(n)}</span>' for n in names
    ) + "</div>"


def geology_legend(present_symbols: set[str]) -> str:
    items = []
    for symbol, color in GEOLOGY_COLORS.items():
        if present_symbols and symbol not in present_symbols:
            continue
        items.append(
            f'<div class="it"><span class="sw" style="background:{color}"></span>{symbol}</div>'
        )
    return '<div class="legend">' + "".join(items) + "</div>"


def station_header(station: dict) -> str:
    return (
        f'<div class="station-head">'
        f'<span class="t">{html.escape(station["name"])}</span>'
        f'<span class="sol">Sol {station["sol"]}</span>'
        f"</div>"
    )


def unit_tag(symbol: str, name: str) -> str:
    color = GEOLOGY_COLORS.get(symbol, "#9aa3ad")
    return (
        f'<span class="unit-tag" style="background:{color}">{html.escape(symbol)}</span>'
        f'<b>{html.escape(name)}</b>'
    )


def footer() -> str:
    return (
        '<div class="foot">'
        "<b>MarsGo</b> · Mango's Gravity · NASA Space Apps Challenge 2026. "
        "<b>Data:</b> NASA/JPL Mars Trek (MOLA/HRSC DEM, Perseverance traverse, "
        "OMEGA/CRISM, THEMIS), Esri Astro CTX and HiRISE mosaics, USGS Astrogeology "
        "Jezero geologic map, NASA Mars 2020 raw images, NASA MSL REMS. "
        "<b>Limits:</b> public DEM is 200 m/px; human-scale hazard comes from a "
        "CTX-texture roughness proxy. Weather is a Gale Crater analog. "
        "Suit numbers are planning assumptions, not flight rules. All data cached "
        "locally for offline use."
        "</div>"
    )
