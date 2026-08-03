"""Build the Glasgow 2026 Commonwealth Games tartan dashboard."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from data_processing import MAP_DIR, Team, flag_url, load_data
from viz import MEDAL_COLOURS, REGION_COLOURS, build_figure

OUTPUT = MAP_DIR / "output" / "glasgow_2026_dashboard.html"
PREVIEW = MAP_DIR / "output" / "glasgow_2026_preview.png"

def _table_rows(teams: list[Team]) -> str:
    ranked = sorted(teams, key=lambda team: (-team.gold, -team.silver, -team.bronze, team.name))
    rows: list[str] = []
    medal_rank = 0
    for team in ranked:
        if team.total:
            medal_rank += 1
            rank = str(medal_rank)
        else:
            rank = "—"
        rows.append(
            f'<tr data-code="{team.code}" data-medallist="{int(bool(team.total))}" '
            f'data-search="{html.escape((team.name + " " + team.code + " " + team.city).lower())}">'
            f'<td class="rank">{rank}</td><td><img class="flag" src="{flag_url(team.code)}" alt="{html.escape(team.name)} flag" loading="lazy"><strong>{html.escape(team.name)}</strong>'
            f'<small>{team.code} · {html.escape(team.city)}</small></td>'
            f'<td class="medal gold">{team.gold}</td><td class="medal silver">{team.silver}</td>'
            f'<td class="medal bronze">{team.bronze}</td><td class="total">{team.total}</td></tr>'
        )
    return "".join(rows)


def build_html() -> str:
    raw, teams = load_data()
    figure, route_indices, marker_index = build_figure(raw, teams)
    plot = figure.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        config={"responsive": True, "scrollZoom": True, "displaylogo": False},
        div_id="glasgow-map",
    )
    data = [
        {"name": team.name, "code": team.code, "city": team.city, "flag": flag_url(team.code), "gold": team.gold,
         "silver": team.silver, "bronze": team.bronze, "total": team.total}
        for team in teams
    ]
    marker_codes = [
        team.code
        for team in sorted(teams, key=lambda team: team.name)
    ]
    medal_teams = sum(bool(team.total) for team in teams)
    total_medals = sum(team.total for team in teams)
    medal_legend = "".join(
        f'<span class="legend-item"><i style="background:{colour}"></i>{name.title()}</span>'
        for name, colour in MEDAL_COLOURS.items()
    )
    region_legend = "".join(
        f'<span class="legend-item"><i style="background:{colour}"></i>{html.escape(name)}</span>'
        for name, colour in REGION_COLOURS.items()
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Every Glasgow 2026 team and medal woven into one interactive Commonwealth tartan.">
<meta property="og:type" content="website">
<meta property="og:title" content="The Commonwealth Tartan · Glasgow 2026">
<meta property="og:description" content="Every Glasgow 2026 team and medal woven into one interactive Commonwealth tartan.">
<meta property="og:image" content="glasgow_2026_preview.png">
<meta property="og:image:alt" content="The Glasgow 2026 Commonwealth Tartan medal map">
<meta name="twitter:card" content="summary_large_image">
<title>The Commonwealth Tartan · Glasgow 2026</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap');
:root{{--ink:#16082e;--panel:#21103d;--panel2:#2b1450;--line:rgba(0,196,201,.28);--text:#fff7fc;--muted:#cbb9d4;--pink:#f259b0;--purple:#51129b;--indigo:#263cc8;--teal:#00c4c9;--gold:#f6c453;--silver:#d9e1e8;--bronze:#c77d4a}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--ink);color:var(--text);font-family:'DM Sans',system-ui,sans-serif}}
body:before{{content:"";position:fixed;inset:0;pointer-events:none;background:radial-gradient(circle at 12% 0%,rgba(242,89,176,.22),transparent 32%),radial-gradient(circle at 88% 4%,rgba(0,196,201,.17),transparent 30%),linear-gradient(145deg,transparent 52%,rgba(38,60,200,.11))}}
.shell{{position:relative;max-width:1600px;margin:auto;padding:26px 28px 34px}} header{{display:grid;grid-template-columns:1fr auto;gap:22px;align-items:end;margin-bottom:22px}}
.eyebrow{{font:700 12px 'Space Grotesk';letter-spacing:.18em;text-transform:uppercase;color:var(--teal);margin-bottom:8px}}
h1{{font:700 clamp(34px,5vw,68px)/.96 'Space Grotesk';letter-spacing:-.055em;margin:0;max-width:920px}} h1 span{{color:var(--pink)}}
.dek{{max-width:760px;color:var(--muted);font-size:15px;line-height:1.55;margin:16px 0 0}}
.stamp{{border:1px solid var(--pink);border-radius:999px;padding:9px 14px;color:var(--text);background:rgba(242,89,176,.12);font-size:12px;white-space:nowrap}}
.stats{{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px;margin-bottom:12px}} .stat{{position:relative;overflow:hidden;background:linear-gradient(135deg,rgba(43,20,80,.96),rgba(33,16,61,.92));border:1px solid var(--line);border-radius:13px;padding:14px 16px}} .stat:before{{content:"";position:absolute;inset:0 auto 0 0;width:3px;background:var(--pink)}} .stat:nth-child(2):before{{background:var(--purple)}} .stat:nth-child(3):before{{background:var(--teal)}} .stat:nth-child(4):before{{background:var(--indigo)}}
.stat b{{font:700 24px 'Space Grotesk';display:block}} .stat span{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.1em}}
.workspace{{display:grid;grid-template-columns:minmax(0,1fr) 390px;gap:12px;min-height:1250px}} .map-card,.side{{background:rgba(33,16,61,.92);border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 18px 60px rgba(7,0,24,.42)}}
.map-card{{position:relative}} #glasgow-map{{height:1120px}} .controls{{min-height:56px;padding:11px 14px;display:flex;align-items:center;gap:7px;flex-wrap:wrap;border-bottom:1px solid var(--line);background:var(--panel)}}
.chart-legends{{min-height:74px;padding:12px 16px;display:flex;align-items:center;justify-content:center;gap:24px;flex-wrap:wrap;border-top:1px solid var(--line);background:var(--panel)}} .legend-group{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}} .legend-group strong{{font:700 10px 'Space Grotesk';letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-right:2px}} .legend-item{{display:inline-flex;align-items:center;gap:5px;color:var(--text);font-size:11px;white-space:nowrap}} .legend-item i{{display:inline-block;width:22px;height:5px;border-radius:99px}}
button{{font:600 12px 'DM Sans';color:var(--text);background:rgba(22,8,46,.9);border:1px solid rgba(0,196,201,.4);border-radius:999px;padding:8px 12px;cursor:pointer;transition:background .15s,border-color .15s,transform .15s}} button:hover{{border-color:var(--teal);background:rgba(0,196,201,.12)}} button.active{{background:linear-gradient(110deg,var(--pink),#dd43a5);color:var(--ink);border-color:var(--pink)}} button:active{{transform:translateY(1px)}} button:focus-visible,input:focus-visible{{outline:2px solid var(--teal);outline-offset:2px}}
.side{{height:1250px;display:flex;flex-direction:column}} .side-head{{padding:16px;border-bottom:1px solid var(--line);background:linear-gradient(135deg,rgba(81,18,155,.2),transparent 70%)}} .side-head h2{{font:700 18px 'Space Grotesk';margin:0 0 6px}} .side-head p{{font-size:11px;color:var(--muted);line-height:1.45;margin:0 0 12px}} input{{width:100%;border:1px solid var(--line);border-radius:9px;background:var(--ink);color:var(--text);padding:10px 12px;outline:none}} input::placeholder{{color:#9f8bae}} input:focus{{border-color:var(--teal)}}
.table-wrap{{overflow:auto;flex:1}} table{{width:100%;border-collapse:collapse;font-size:12px}} thead{{position:sticky;top:0;z-index:2;background:var(--panel)}} th{{padding:10px 8px;text-align:right;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.08em;border-bottom:1px solid var(--line)}} th:nth-child(2){{text-align:left}} td{{padding:9px 8px;border-bottom:1px solid rgba(0,196,201,.12);text-align:right}} tr{{cursor:pointer}} tbody tr:hover{{background:rgba(0,196,201,.09)}} tbody tr.selected{{background:rgba(242,89,176,.18);box-shadow:inset 3px 0 var(--pink)}} td:nth-child(2){{text-align:left;max-width:190px}} td small{{display:block;color:var(--muted);margin:2px 0 0 29px}} .flag{{display:inline-block;width:20px;height:20px;margin-right:9px;vertical-align:-5px}} .imagelayer image{{pointer-events:none}} .rank{{color:#ad97ba;width:28px}} .medal{{font-weight:700}} .gold{{color:var(--gold)}} .silver{{color:var(--silver)}} .bronze{{color:var(--bronze)}} .total{{font-weight:700}} tr.hidden{{display:none}}
.note{{color:var(--muted);font-size:11px;line-height:1.5;margin:14px 2px 0}} .note a{{color:var(--teal)}}
@media(max-width:1000px){{header{{grid-template-columns:1fr}}.stamp{{justify-self:start}}.workspace{{grid-template-columns:1fr}}.side{{height:620px}}}}
@media(max-width:620px){{.shell{{padding:18px 12px}}.stats{{grid-template-columns:repeat(2,1fr)}}#glasgow-map{{height:1060px}}.workspace{{min-height:0}}.map-card{{min-height:1060px}}}}
</style></head><body><main class="shell">
<header><div><div class="eyebrow">Glasgow 2026 Commonwealth Games</div><h1>The Commonwealth <span>Tartan.</span></h1><p class="dek">Across a field of Glasgow pink, countries run alphabetically from top to bottom and are coloured by Commonwealth region. Flags form the left edge and team codes the right. Each sport carries three violin-shaped medal threads: zero passes beneath the country strand; a win resurfaces above it.</p></div><div class="stamp">Final results</div></header>
<section class="stats"><div class="stat"><b>{len(teams)}</b><span>Competing teams</span></div><div class="stat"><b>{medal_teams}</b><span>Teams with medals</span></div><div class="stat"><b>{total_medals}</b><span>Medals awarded</span></div><div class="stat"><b>216 · 215 · 243</b><span>Gold · silver · bronze</span></div></section>
<section class="workspace"><div class="map-card"><div class="controls"><button data-filter="all">All threads</button><button data-filter="medallists">Medallists</button><button data-filter="none" class="active">No medals</button><button id="clear">Clear selection</button></div>{plot}<div class="chart-legends"><div class="legend-group"><strong>Medal violins</strong>{medal_legend}</div><div class="legend-group"><strong>Country region</strong>{region_legend}</div></div></div>
<aside class="side"><div class="side-head"><h2>Final medal table</h2><p>Click a team—or any metallic stitch—to lift its strand from the cloth.</p><input id="search" type="search" placeholder="Search team, code or capital…" aria-label="Search teams"></div><div class="table-wrap"><table><thead><tr><th>#</th><th>Team</th><th class="gold">G</th><th class="silver">S</th><th class="bronze">B</th><th>Total</th></tr></thead><tbody>{_table_rows(teams)}</tbody></table></div></aside></section>
<p class="note">Sources: <a href="https://www.glasgow2026.com/teams">official Glasgow 2026 teams</a>, the <a href="https://www.glasgow2026.com/results/detailed/#/general-medals">final medal table</a>, and the official sport medal reports. Every country strand has equal weight and is coloured by region. Team-event medals count once in the medal table.</p>
</main><script>
const TEAMS={json.dumps(data, ensure_ascii=False)};
const TEAM_BY_CODE=Object.fromEntries(TEAMS.map(t=>[t.code,t]));
const MARKER_CODES={json.dumps(marker_codes)};
const ROUTES={json.dumps(route_indices)};
const MARKERS={marker_index};
const gd=document.getElementById('glasgow-map');
let mode='none', selected=null;
function allowed(t){{return mode==='all'||(mode==='medallists'&&t.total>0)||(mode==='none'&&t.total===0)}}
function refresh(){{
  const routeTraces=[], routeOpacity=[];
  TEAMS.forEach(t=>{{(ROUTES[t.code]||[]).forEach(i=>{{routeTraces.push(i);routeOpacity.push(!allowed(t)?.025:selected===null?(t.total?.76:.62):selected===t.code?1:.055);}});}});
  const anchorOpacity=MARKER_CODES.map(code=>allowed(TEAM_BY_CODE[code])?1:.12);
  const updates=[Plotly.restyle(gd,{{opacity:routeOpacity}},routeTraces),Plotly.restyle(gd,{{'marker.opacity':[anchorOpacity]}},[MARKERS])];
  gd.data.forEach((trace,index)=>{{if(trace.meta&&trace.meta.kind==='stitches'){{const values=trace.customdata.map(d=>!allowed(TEAM_BY_CODE[d[0]])?.02:selected===null?1:selected===d[0]?1:.06);updates.push(Plotly.restyle(gd,{{'marker.opacity':[values]}},[index]));}}}});
  document.querySelectorAll('tbody tr').forEach(r=>r.classList.toggle('selected',r.dataset.code===selected));
  return Promise.all(updates);
}}
document.querySelectorAll('[data-filter]').forEach(btn=>btn.onclick=()=>{{mode=btn.dataset.filter;selected=null;document.querySelectorAll('[data-filter]').forEach(b=>b.classList.toggle('active',b===btn));refresh();}});
function choose(code){{selected=selected===code?null:code;refresh();}}
document.querySelectorAll('tbody tr').forEach(row=>row.onclick=()=>choose(row.dataset.code));
gd.on('plotly_click',ev=>{{const p=ev.points[0];if(p.customdata&&(p.curveNumber===MARKERS||(p.data.meta&&p.data.meta.kind==='stitches')))choose(p.customdata[0]);}});
document.getElementById('clear').onclick=()=>{{selected=null;refresh();}};
function filterRows(){{const q=document.getElementById('search').value.trim().toLowerCase();document.querySelectorAll('tbody tr').forEach(r=>{{r.classList.toggle('hidden',!r.dataset.search.includes(q));}})}}
document.getElementById('search').addEventListener('input',filterRows);
filterRows();refresh();
</script></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_html(), encoding="utf-8")
    raw, teams = load_data()
    figure, _, _ = build_figure(raw, teams)
    # LinkedIn's large-image card is a wide 1200x630 canvas; keep the full
    # tartan visible inside that share-friendly frame.
    PREVIEW.write_bytes(figure.to_image(format="png", width=1200, height=630, scale=1))
    print(f"Wrote {args.output}")
    print(f"Wrote {PREVIEW}")
    print(f"{raw['event']}: {len(teams)} teams, {sum(team.total for team in teams)} medals")


if __name__ == "__main__":
    main()
