"""CustomJS callbacks for client-side cross-filtering in standalone Bokeh HTML."""

from __future__ import annotations

import json

from bokeh.models import CustomJS

from wind_bokeh_charts import OWNER_COL, TOP_BAR_RANK
from wind_data import COL

# Map: IndexFilter on shared master. Charts: re-run pandas-style groupbys in JS.
_FILTER_UPDATE_JS = """
const d = master.data;
const n = d.capacity.length;
const f = filter_state.data;
const instF = (f.inst_filter[0] || "").trim();
const statusF = (f.status_filter[0] || "").trim();
const countryF = (f.country_filter[0] || "").trim();
const ownerF = (f.owner_filter[0] || "").trim();
const projectF = (f.project_filter[0] || "").trim();
const topSet = new Set(top_countries);
const filtered = !!(instF || statusF || countryF || ownerF || projectF);

function rowPasses(i) {
  if (instF && d.installation_type[i] !== instF) return false;
  if (statusF && d.status[i] !== statusF) return false;
  if (countryF) {
    if (countryF === "Other") {
      if (topSet.has(d.country[i])) return false;
    } else if (d.country[i] !== countryF) return false;
  }
  if (ownerF) {
    const o = (d.owner[i] || "").toLowerCase();
    if (!o.includes(ownerF.toLowerCase())) return false;
  }
  if (projectF && d.project[i] !== projectF) return false;
  return true;
}

const idx = [];
let totalCap = 0;
const countries = new Set();
for (let i = 0; i < n; i++) {
  if (rowPasses(i)) {
    idx.push(i);
    totalCap += d.capacity[i];
    countries.add(d.country[i]);
  }
}

index_filter.indices = idx;
index_filter.change.emit();
map_bg_renderer.visible = filtered;

function sumByKey(key) {
  const agg = {};
  for (const i of idx) {
    const k = d[key][i];
    agg[k] = (agg[k] || 0) + d.capacity[i];
  }
  const labels = Object.keys(agg).sort((a, b) => agg[b] - agg[a]);
  return { labels, values: labels.map(l => agg[l]) };
}

function sumCountries() {
  const agg = {};
  for (const i of idx) {
    let k = d.country[i];
    if (!topSet.has(k)) k = "Other";
    agg[k] = (agg[k] || 0) + d.capacity[i];
  }
  const sorted = Object.entries(agg).sort((a, b) => a[1] - b[1]);
  return { labels: sorted.map(s => s[0]), values: sorted.map(s => s[1]) };
}

function sumProjects() {
  const agg = {};
  for (const i of idx) {
    const proj = d.project[i];
    if (!agg[proj]) agg[proj] = { cap: 0, country: d.country[i] };
    agg[proj].cap += d.capacity[i];
  }
  const sorted = Object.entries(agg).sort((a, b) => b[1].cap - a[1].cap).slice(0, top_bar_rank);
  sorted.sort((a, b) => a[1].cap - b[1].cap);
  return {
    labels: sorted.map(s => s[0]),
    countries: sorted.map(s => s[1].country),
    values: sorted.map(s => s[1].cap),
  };
}

function sumOwners() {
  const agg = {};
  for (const i of idx) {
    let entries = [];
    try { entries = JSON.parse(d.owner_json[i] || "[]"); } catch(e) { entries = []; }
    for (const e of entries) {
      if (!e.name) continue;
      const share = (e.pct || 0) / 100.0;
      agg[e.name] = (agg[e.name] || 0) + d.capacity[i] * share;
    }
  }
  const sorted = Object.entries(agg).sort((a, b) => b[1] - a[1]).slice(0, top_bar_rank);
  sorted.sort((a, b) => a[1] - b[1]);
  return { labels: sorted.map(s => s[0]), values: sorted.map(s => s[1]) };
}

const inst = sumByKey("installation_type");
const instData = {};
instData[col_installation] = inst.labels;
instData[col_capacity] = inst.values;
inst_source.data = instData;
inst_source.change.emit();
inst_fig.x_range.factors = inst.labels;
inst_fig.x_range.change.emit();

const stat = sumByKey("status");
const statusData = {};
statusData[col_status] = stat.labels;
statusData[col_capacity] = stat.values;
status_source.data = statusData;
status_source.change.emit();
status_fig.x_range.factors = stat.labels;
status_fig.x_range.change.emit();

const ctry = sumCountries();
const countryData = {};
countryData[col_country] = ctry.labels;
countryData[col_capacity] = ctry.values;
country_source.data = countryData;
country_source.change.emit();
country_fig.y_range.factors = ctry.labels;
country_fig.y_range.change.emit();

const proj = sumProjects();
const projectData = {};
projectData[col_project] = proj.labels;
projectData[col_country] = proj.countries;
projectData[col_capacity] = proj.values;
projects_source.data = projectData;
projects_source.change.emit();
projects_fig.y_range.factors = proj.labels;
projects_fig.y_range.change.emit();

const own = sumOwners();
const ownerData = {};
ownerData[col_owner] = own.labels;
ownerData[col_capacity] = own.values;
owner_source.data = ownerData;
owner_source.change.emit();
owner_fig.y_range.factors = own.labels;
owner_fig.y_range.change.emit();

function escHtml(s) {
  return String(s ?? "")
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function updateTable() {
  const tbody = document.getElementById("assets-tbody");
  if (!tbody) return;
  const rows = idx.map(i => ({
    country: d.country[i], project: d.project[i], phase: d.phase[i],
    capacity: d.capacity[i], inst: d.installation_type[i], status: d.status[i],
    start: d.start_year[i], retired: d.retired_year[i],
    operator: d.operator[i], owner: d.owner[i],
    lat: d.lat[i], lon: d.lon[i], wiki: d.wiki[i],
  }));
  rows.sort((a, b) => b.capacity - a.capacity);
  const top = rows.slice(0, table_row_limit);
  tbody.innerHTML = top.map(r => {
    const wiki = (r.wiki || "").trim();
    const wikiCell = wiki.startsWith("http")
      ? `<a href="${escHtml(wiki)}">${escHtml(wiki)}</a>`
      : escHtml(wiki);
    const fmtInt = (v) => (typeof v === "number" && !isNaN(v))
      ? Math.round(v).toLocaleString("en-US", { maximumFractionDigits: 0 })
      : escHtml(v);
    const fmtCoord = (v) => (typeof v === "number" && !isNaN(v))
      ? Number(v).toFixed(4)
      : escHtml(v);
    return `<tr>
      <td>${escHtml(r.country)}</td><td>${escHtml(r.project)}</td><td>${escHtml(r.phase)}</td>
      <td>${fmtInt(r.capacity)}</td><td>${escHtml(r.inst)}</td><td>${escHtml(r.status)}</td>
      <td>${escHtml(r.start)}</td><td>${escHtml(r.retired)}</td>
      <td>${escHtml(r.operator)}</td><td>${escHtml(r.owner)}</td>
      <td>${fmtCoord(r.lat)}</td><td>${fmtCoord(r.lon)}</td><td>${wikiCell}</td>
    </tr>`;
  }).join("");
  const note = document.getElementById("table-note");
  if (note) {
    note.textContent = filtered
      ? `Top ${Math.min(table_row_limit, rows.length)} rows by capacity (filtered). Click a chart again to clear.`
      : `Top ${table_row_limit} rows by capacity (full dataset). Click a chart bar to cross-filter.`;
  }
}
updateTable();

const kc = document.getElementById('kpi-capacity');
if (kc) kc.textContent = Math.round(totalCap).toLocaleString("en-US", {maximumFractionDigits: 0});
const kr = document.getElementById('kpi-rows');
if (kr) kr.textContent = idx.length.toLocaleString("en-US", {maximumFractionDigits: 0});
const kcn = document.getElementById('kpi-countries');
if (kcn) kcn.textContent = countries.size.toLocaleString("en-US", {maximumFractionDigits: 0});
"""

_TAP_JS = """
const inds = cb_obj.indices;
if (!inds || inds.length === 0) return;
const idx = inds[0];
const src = tap_source.data;
const value = (src[tap_column] && src[tap_column][idx] != null) ? String(src[tap_column][idx]) : null;
if (!value) return;
const key = dimension + "_filter";
const cur = (filter_state.data[key][0] || "").trim();
const clearing = cur === value;

if (clearing) {
  filter_state.data[key] = [""];
  tap_source.selected.indices = [];
} else {
  filter_state.data[key] = [value];
  for (const s of tap_sources) {
    if (s !== tap_source) s.selected.indices = [];
  }
}
filter_state.change.emit();
update_cb.execute();
"""


def wire_cross_filter(
    *,
    master,
    index_filter,
    map_bg_renderer,
    inst_source,
    status_source,
    country_source,
    projects_source,
    owner_source,
    filter_state,
    inst_renderer,
    status_renderer,
    country_renderer,
    projects_renderer,
    owner_renderer,
    inst_fig,
    status_fig,
    country_fig,
    projects_fig,
    owner_fig,
    top_countries: list[str],
    row_count: int,
    inst_tap_col: str,
    status_tap_col: str,
    country_tap_col: str,
    project_tap_col: str,
    owner_tap_col: str,
) -> None:
    """Wire TapTool selection to IndexFilter on the shared master source."""
    all_tap_sources = [
        inst_renderer.data_source,
        status_renderer.data_source,
        country_renderer.data_source,
        projects_renderer.data_source,
        owner_renderer.data_source,
    ]

    update_cb = CustomJS(
        args=dict(
            master=master,
            index_filter=index_filter,
            map_bg_renderer=map_bg_renderer,
            inst_source=inst_source,
            status_source=status_source,
            country_source=country_source,
            projects_source=projects_source,
            owner_source=owner_source,
            filter_state=filter_state,
            inst_fig=inst_fig,
            status_fig=status_fig,
            country_fig=country_fig,
            projects_fig=projects_fig,
            owner_fig=owner_fig,
            top_countries=top_countries,
            top_bar_rank=TOP_BAR_RANK,
            table_row_limit=100,
            row_count=row_count,
            col_installation=COL.installation_type,
            col_status=COL.status,
            col_country=COL.country,
            col_project=COL.project,
            col_owner=OWNER_COL,
            col_capacity=COL.capacity_mw,
        ),
        code=_FILTER_UPDATE_JS,
    )

    for dim, renderer, tap_col in [
        ("inst", inst_renderer, inst_tap_col),
        ("status", status_renderer, status_tap_col),
        ("country", country_renderer, country_tap_col),
        ("project", projects_renderer, project_tap_col),
        ("owner", owner_renderer, owner_tap_col),
    ]:
        tap_cb = CustomJS(
            args=dict(
                filter_state=filter_state,
                update_cb=update_cb,
                dimension=dim,
                tap_source=renderer.data_source,
                tap_sources=all_tap_sources,
                tap_column=tap_col,
            ),
            code=_TAP_JS,
        )
        renderer.data_source.selected.js_on_change("indices", tap_cb)


def owner_json_entries(owner: object) -> str:
    """Serialize pre-parsed owner shares for CustomJS re-aggregation."""
    from wind_bokeh_charts import _parse_owner_shares

    entries = [{"name": n, "pct": p} for n, p in _parse_owner_shares(owner)]
    return json.dumps(entries)
