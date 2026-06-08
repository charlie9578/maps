"""Shared data model and chart helpers for the squad dashboard."""

from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date

import plotly.graph_objects as go

from club_confed import club_confederation, is_domestic, nation_confederation, normalize_country
from data_processing import Team
from viz import CONFED_COLORS, DEFAULT_COLOR

DASH_BG = "#0f172a"
PLOT_BG = "#1e293b"
GRID = "#334155"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"

# Tournament window for birthday detection (opening match → final).
WC_OPENING_DAY = date(2026, 6, 11)
WC_FINAL_DAY = date(2026, 7, 19)

CONFED_ORDER = ["UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC", "OTHER"]
POS_ORDER = ["GK", "DF", "MF", "FW"]
POS_COLORS = {
    "GK": "#f59e0b",
    "DF": "#2563eb",
    "MF": "#16a34a",
    "FW": "#dc2626",
}
AGE_BANDS = [(17, 21), (22, 25), (26, 29), (30, 33), (34, 50)]
AGE_BAND_LABELS = ["17–21", "22–25", "26–29", "30–33", "34+"]

CAPTAIN_RE = re.compile(r"\(\s*captain\s*\)", re.IGNORECASE)
CAPTAIN_LABEL = "Captains"
MATE_LABEL = "Squad mates"


@dataclass(frozen=True)
class PlayerRow:
    nation: str
    nation_confed: str
    name: str
    pos: str
    dob: str | None
    age: int | None
    caps: int | None
    goals: int | None
    club: str
    club_country: str
    club_confed: str
    domestic: bool
    distance_km: float | None
    is_captain: bool = False


@dataclass(frozen=True)
class CaptainProfile:
    name: str
    nation: str
    pos: str
    age: int | None
    caps: int | None
    goals: int | None
    club: str
    squad_avg_age: float | None
    squad_avg_caps: float | None
    age_vs_squad: float | None
    caps_vs_squad: float | None
    most_capped_on_team: bool
    top_scorer_on_team: bool
    plays_abroad: bool


@dataclass(frozen=True)
class AgeExtreme:
    name: str
    nation: str
    pos: str
    age: int | None
    dob: str | None
    club: str


@dataclass(frozen=True)
class TournamentBirthday:
    birthday: date
    name: str
    nation: str
    pos: str
    age_on_opening: int | None
    turns: int | None
    club: str


def parse_dob(iso: str | None) -> date | None:
    if not iso:
        return None
    try:
        return date.fromisoformat(iso)
    except ValueError:
        return None


def birthday_in_tournament_year(dob: date, *, year: int = WC_OPENING_DAY.year) -> date | None:
    """Map DOB to the same calendar day in ``year`` (Feb 29 → Feb 28 in non-leap years)."""
    day = dob.day
    if dob.month == 2 and dob.day == 29:
        day = 28
    try:
        return date(year, dob.month, day)
    except ValueError:
        return None


def age_on(dob: date, on: date) -> int:
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


def is_captain_name(name: str) -> bool:
    return bool(CAPTAIN_RE.search(name))


def clean_player_name(name: str) -> str:
    return CAPTAIN_RE.sub("", name).strip()


def captain_group(row: PlayerRow) -> str:
    return CAPTAIN_LABEL if row.is_captain else MATE_LABEL


def build_player_rows(teams: list[Team], clubs: dict[str, dict]) -> list[PlayerRow]:
    """Flatten squads into one row per player with club confederation metadata."""
    rows: list[PlayerRow] = []
    for team in teams:
        n_confed = nation_confederation(team.confederation)
        dist_by_club: dict[str, float] = {}
        for route in team.routes:
            for club_name in route.clubs:
                dist_by_club[club_name] = route.distance_km

        for _no, name, pos, dob, age, caps, goals, club in team.squad:
            club_meta = clubs.get(club, {})
            club_country = normalize_country(str(club_meta.get("country", "Unknown")))
            captain = is_captain_name(name)
            rows.append(
                PlayerRow(
                    nation=team.nation,
                    nation_confed=n_confed,
                    name=clean_player_name(name),
                    pos=pos or "—",
                    dob=dob,
                    age=age,
                    caps=caps,
                    goals=goals,
                    club=club,
                    club_country=club_country,
                    club_confed=club_confederation(club_country),
                    domestic=is_domestic(team.nation, club_country),
                    distance_km=dist_by_club.get(club),
                    is_captain=captain,
                )
            )
    return rows


def tournament_birthdays(rows: list[PlayerRow]) -> list[TournamentBirthday]:
    """Players whose birthday falls during the World Cup (11 Jun – 19 Jul 2026)."""
    hits: list[TournamentBirthday] = []
    for r in rows:
        dob = parse_dob(r.dob)
        if dob is None:
            continue
        bday = birthday_in_tournament_year(dob)
        if bday is None or not (WC_OPENING_DAY <= bday <= WC_FINAL_DAY):
            continue
        opening_age = age_on(dob, WC_OPENING_DAY)
        hits.append(
            TournamentBirthday(
                birthday=bday,
                name=r.name,
                nation=r.nation,
                pos=r.pos,
                age_on_opening=opening_age,
                turns=opening_age + 1,
                club=r.club,
            )
        )
    hits.sort(key=lambda x: (x.birthday, x.nation, x.name))
    return hits


def age_extremes(rows: list[PlayerRow]) -> tuple[list[AgeExtreme], list[AgeExtreme]]:
    """Return (youngest, oldest) player lists; ties broken by DOB then name."""
    ranked: list[tuple[tuple[int, date, str], PlayerRow]] = []
    for r in rows:
        if r.age is None:
            continue
        dob = parse_dob(r.dob)
        # Youngest first: higher DOB, lower age. Sort key uses inverted DOB via neg ordinal.
        dob_key = dob.toordinal() if dob else 0
        ranked.append(((r.age, dob_key, r.name), r))

    if not ranked:
        return [], []

    ranked.sort(key=lambda item: (item[0][0], -item[0][1], item[0][2]))
    min_age = ranked[0][0][0]
    youngest = [
        AgeExtreme(r.name, r.nation, r.pos, r.age, r.dob, r.club)
        for _, r in ranked
        if r.age == min_age
    ]

    ranked.sort(key=lambda item: (-item[0][0], item[0][1], item[0][2]))
    max_age = ranked[0][0][0]
    oldest = [
        AgeExtreme(r.name, r.nation, r.pos, r.age, r.dob, r.club)
        for _, r in ranked
        if r.age == max_age
    ]
    return youngest, oldest


def format_dob(iso: str | None) -> str:
    dob = parse_dob(iso)
    if dob is None:
        return "—"
    return dob.strftime("%d %b %Y").replace(" 0", " ")


def confed_color(confed: str) -> str:
    return CONFED_COLORS.get(confed, DEFAULT_COLOR)


def active_confeds(rows: list[PlayerRow]) -> list[str]:
    return [c for c in CONFED_ORDER if any(r.nation_confed == c for r in rows)]


def age_band(age: int | None) -> str | None:
    if age is None:
        return None
    for (lo, hi), label in zip(AGE_BANDS, AGE_BAND_LABELS, strict=True):
        if lo <= age <= hi:
            return label
    return None


def band_color(index: int, *, alpha: float = 1.0) -> str:
    palette = ["#38bdf8", "#34d399", "#fbbf24", "#fb7185", "#a78bfa"]
    hex_c = palette[index % len(palette)]
    r, g, b = int(hex_c[1:3], 16), int(hex_c[3:5], 16), int(hex_c[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"


VETERAN_CAPS = 100

# Horizontal legend below the plot area (avoids clashing with subplot titles).
LEGEND_BELOW = {"orientation": "h", "yanchor": "top", "y": -0.12, "x": 0, "xanchor": "left"}


def dark_layout(
    fig: go.Figure,
    title: str,
    *,
    height: int = 420,
    showlegend: bool = False,
    legend_below: bool = False,
) -> None:
    top = 72 if "<" in title else 60
    bottom = 72 if legend_below else 48
    layout: dict = {
        "title": {"text": title, "x": 0.01, "xanchor": "left", "font": {"size": 15, "color": TEXT}},
        "template": "plotly_dark",
        "paper_bgcolor": DASH_BG,
        "plot_bgcolor": PLOT_BG,
        "font": {"color": TEXT, "family": "system-ui, Segoe UI, Roboto, sans-serif", "size": 12},
        "height": height,
        "margin": {"l": 48, "r": 24, "t": top, "b": bottom},
        "showlegend": showlegend,
    }
    if legend_below and showlegend:
        layout["legend"] = LEGEND_BELOW
    fig.update_layout(**layout)
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)


def style_subplot_titles(fig: go.Figure, *, font_size: int = 12) -> None:
    """Style make_subplots titles without moving them (resetting x causes side-by-side overlap)."""
    for ann in fig.layout.annotations or []:
        if ann.text and not ann.showarrow:
            ann.font = {"size": font_size, "color": TEXT}
            ann.xanchor = "left"


def add_violin_box(
    fig: go.Figure,
    rows: list[PlayerRow],
    *,
    category_key,
    categories: list[str],
    y_key,
    colors: dict[str, str] | None,
    row: int,
    col: int,
    y_title: str,
) -> None:
    """Overlay semi-transparent violins with box plots for one numeric metric."""
    for cat in categories:
        vals = [y_key(r) for r in rows if category_key(r) == cat and y_key(r) is not None]
        if not vals:
            continue
        color = (colors or {}).get(cat, "#64748b")
        fig.add_trace(
            go.Violin(
                x=[cat] * len(vals),
                y=vals,
                name=cat,
                legendgroup=cat,
                scalegroup=cat,
                line_color=color,
                fillcolor=f"rgba({int(color[1:3], 16)},{int(color[3:5], 16)},{int(color[5:7], 16)},0.25)",
                opacity=0.85,
                points=False,
                box_visible=False,
                meanline_visible=False,
                showlegend=False,
                hovertemplate=f"{cat}<br>%{{y}}<extra></extra>",
            ),
            row=row,
            col=col,
        )
        fig.add_trace(
            go.Box(
                x=[cat] * len(vals),
                y=vals,
                name=cat,
                legendgroup=cat,
                marker={"color": color},
                line={"color": color, "width": 1.5},
                fillcolor="rgba(15, 23, 42, 0.55)",
                boxpoints="outliers",
                jitter=0.25,
                pointpos=0,
                whiskerwidth=0.5,
                showlegend=False,
                hovertemplate=f"{cat}<br>%{{y}}<extra></extra>",
            ),
            row=row,
            col=col,
        )
    fig.update_yaxes(title_text=y_title, row=row, col=col)


def abroad_nations_table_html(rows: list[PlayerRow]) -> str:
    """Scrollable table of every nation ranked by share of squad playing abroad."""
    by_nation: dict[str, list[PlayerRow]] = defaultdict(list)
    for r in rows:
        by_nation[r.nation].append(r)

    ranked: list[tuple[str, float, int, int, str]] = []
    for nation, players in by_nation.items():
        abroad = sum(1 for p in players if not p.domestic)
        ranked.append(
            (nation, 100 * abroad / len(players), abroad, len(players), players[0].nation_confed)
        )
    ranked.sort(key=lambda x: (-x[1], x[0]))

    rows_html = "\n".join(
        "      <tr>"
        f"<td class=\"rank\">{i}</td>"
        f"<td>{_esc(nation)}</td>"
        f"<td>{pct:.0f}%</td>"
        f"<td>{abroad}/{total}</td>"
        f"<td>{_esc(confed)}</td>"
        "</tr>"
        for i, (nation, pct, abroad, total, confed) in enumerate(ranked, start=1)
    )
    all_abroad = sum(x[2] for x in ranked)
    all_players = sum(x[3] for x in ranked)
    overall = 100 * all_abroad / max(1, all_players)
    return f"""<div class="table-wrap">
  <p class="table-note">{len(ranked)} nations · <strong>{overall:.0f}%</strong> of all squad players
  play club football outside their national federation.</p>
  <table class="data-table">
    <thead>
      <tr><th>#</th><th>Nation</th><th>% abroad</th><th>Abroad / squad</th><th>Confed</th></tr>
    </thead>
    <tbody>
{rows_html}
    </tbody>
  </table>
</div>"""


def debutants_table_html(players: list[PlayerRow]) -> str:
    """Table of players with zero international caps before the tournament."""
    html = leaderboard_table_html(
        players,
        title="International debutants (0 caps)",
        metric="caps",
        columns=("Player", "Nation", "Pos", "Age", "Club"),
    )
    return html.replace('class="table-wrap"', 'class="table-wrap table-wide"', 1)


def birthday_table_html(birthdays: list[TournamentBirthday]) -> str:
    """Scrollable HTML table of players with birthdays during the tournament."""
    if not birthdays:
        return (
            '<p class="table-note">No squad player has a birthday between '
            f"{WC_OPENING_DAY.strftime('%d %b')} and {WC_FINAL_DAY.strftime('%d %b %Y')}.</p>"
        )
    opening = WC_OPENING_DAY.strftime("%d %b")
    rows_html = "\n".join(
        "      <tr"
        + (' class="row-opening"' if b.birthday == WC_OPENING_DAY else "")
        + ">"
        f"<td>{b.birthday.strftime('%a %d %b')}</td>"
        f"<td>{_esc(b.name)}</td>"
        f"<td>{_esc(b.nation)}</td>"
        f"<td>{_esc(b.pos)}</td>"
        f"<td>{b.turns if b.turns is not None else '—'}</td>"
        f"<td>{_esc(b.club)}</td>"
        "</tr>"
        for b in birthdays
    )
    return f"""<div class="table-wrap">
  <p class="table-note">{len(birthdays)} players have a birthday during the tournament
  (11 Jun – 19 Jul 2026). Rows on <strong>{opening}</strong> share opening day.
  <em>Turns</em> is their age on their birthday.</p>
  <table class="data-table">
    <thead>
      <tr><th>Date</th><th>Player</th><th>Nation</th><th>Pos</th><th>Turns</th><th>Club</th></tr>
    </thead>
    <tbody>
{rows_html}
    </tbody>
  </table>
</div>"""


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@dataclass(frozen=True)
class PositionSummary:
    pos: str
    count: int
    avg_age: float | None
    median_age: float | None
    avg_caps: float | None
    median_caps: float | None
    total_goals: int
    top_scorer: str
    top_scorer_goals: int
    most_caps: str
    most_caps_value: int


def _metric_value(row: PlayerRow, metric: str) -> int:
    if metric == "goals":
        return row.goals or 0
    if metric == "caps":
        return row.caps or 0
    raise ValueError(metric)


def top_players(rows: list[PlayerRow], metric: str, *, limit: int = 20) -> list[PlayerRow]:
    """Return players ranked by goals or caps, including ties at the cutoff."""
    ranked = sorted(rows, key=lambda r: (-_metric_value(r, metric), r.name))
    if len(ranked) <= limit:
        return ranked
    cutoff = _metric_value(ranked[limit - 1], metric)
    return [r for r in ranked if _metric_value(r, metric) >= cutoff]


def player_chart_label(row: PlayerRow) -> str:
    return f"{row.name} ({row.nation})"


def position_summaries(rows: list[PlayerRow]) -> list[PositionSummary]:
    """Aggregate age, caps, and goals by outfield/GK position."""
    out: list[PositionSummary] = []
    for pos in POS_ORDER:
        group = [r for r in rows if r.pos == pos]
        if not group:
            continue
        ages = [r.age for r in group if r.age is not None]
        caps = [r.caps for r in group if r.caps is not None]
        top_s = max(group, key=lambda r: r.goals or 0)
        top_c = max(group, key=lambda r: r.caps or 0)
        out.append(
            PositionSummary(
                pos=pos,
                count=len(group),
                avg_age=statistics.mean(ages) if ages else None,
                median_age=statistics.median(ages) if ages else None,
                avg_caps=statistics.mean(caps) if caps else None,
                median_caps=statistics.median(caps) if caps else None,
                total_goals=sum(r.goals or 0 for r in group),
                top_scorer=top_s.name,
                top_scorer_goals=top_s.goals or 0,
                most_caps=top_c.name,
                most_caps_value=top_c.caps or 0,
            )
        )
    return out


@dataclass(frozen=True)
class NationCapsSummary:
    nation: str
    nation_confed: str
    squad_size: int
    avg_caps: float
    median_caps: float
    total_caps: int
    most_capped: str
    most_capped_value: int


def nation_caps_summaries(rows: list[PlayerRow]) -> list[NationCapsSummary]:
    """Per-nation squad experience from international caps (mean, median, total)."""
    by_nation: dict[str, list[PlayerRow]] = {}
    for row in rows:
        by_nation.setdefault(row.nation, []).append(row)

    out: list[NationCapsSummary] = []
    for nation, squad in by_nation.items():
        caps = [r.caps for r in squad if r.caps is not None]
        if not caps:
            continue
        leader = max(squad, key=lambda r: r.caps or 0)
        out.append(
            NationCapsSummary(
                nation=nation,
                nation_confed=squad[0].nation_confed,
                squad_size=len(squad),
                avg_caps=statistics.mean(caps),
                median_caps=statistics.median(caps),
                total_caps=sum(caps),
                most_capped=leader.name,
                most_capped_value=leader.caps or 0,
            )
        )
    return sorted(out, key=lambda s: (-s.avg_caps, s.nation))


def veterans(rows: list[PlayerRow], min_caps: int = 100) -> list[PlayerRow]:
    return sorted(
        [r for r in rows if (r.caps or 0) >= min_caps],
        key=lambda r: (-(r.caps or 0), r.name),
    )


def debutants(rows: list[PlayerRow]) -> list[PlayerRow]:
    return sorted([r for r in rows if r.caps == 0], key=lambda r: (r.nation, r.name))


def _avg(values: list[int | float]) -> float | None:
    return statistics.mean(values) if values else None


def captain_profiles(rows: list[PlayerRow]) -> list[CaptainProfile]:
    """One profile per nation comparing the captain to the rest of the squad."""
    by_nation: dict[str, list[PlayerRow]] = {}
    for row in rows:
        by_nation.setdefault(row.nation, []).append(row)

    profiles: list[CaptainProfile] = []
    for nation, squad in sorted(by_nation.items()):
        captain = next((r for r in squad if r.is_captain), None)
        if captain is None:
            continue
        mates = [r for r in squad if not r.is_captain]
        mate_ages = [r.age for r in mates if r.age is not None]
        mate_caps = [r.caps for r in mates if r.caps is not None]
        squad_avg_age = _avg(mate_ages)
        squad_avg_caps = _avg(mate_caps)
        max_caps = max((r.caps or 0 for r in squad), default=0)
        max_goals = max((r.goals or 0 for r in squad), default=0)
        profiles.append(
            CaptainProfile(
                name=captain.name,
                nation=nation,
                pos=captain.pos,
                age=captain.age,
                caps=captain.caps,
                goals=captain.goals,
                club=captain.club,
                squad_avg_age=squad_avg_age,
                squad_avg_caps=squad_avg_caps,
                age_vs_squad=(captain.age - squad_avg_age) if captain.age is not None and squad_avg_age else None,
                caps_vs_squad=(captain.caps - squad_avg_caps)
                if captain.caps is not None and squad_avg_caps is not None
                else None,
                most_capped_on_team=(captain.caps or 0) >= max_caps,
                top_scorer_on_team=(captain.goals or 0) >= max_goals and max_goals > 0,
                plays_abroad=not captain.domestic,
            )
        )
    return profiles


def captains_table_html(profiles: list[CaptainProfile]) -> str:
    """Scrollable HTML table of every captain vs their squad averages."""
    if not profiles:
        return '<p class="table-note">No captains found in squad data.</p>'

    def fmt_delta(val: float | None, *, digits: int = 1) -> str:
        if val is None:
            return "—"
        sign = "+" if val > 0 else ""
        return f"{sign}{val:.{digits}f}"

    def delta_class(val: float | None) -> str:
        if val is None or val == 0:
            return ""
        return "delta-pos" if val > 0 else "delta-neg"

    rows_html = "\n".join(
        "      <tr"
        + (" class=\"row-highlight\"" if p.most_capped_on_team or p.top_scorer_on_team else "")
        + ">"
        f"<td>{_esc(p.name)}</td>"
        f"<td>{_esc(p.nation)}</td>"
        f"<td>{_esc(p.pos)}</td>"
        f"<td>{p.age if p.age is not None else '—'}</td>"
        f'<td class="{delta_class(p.age_vs_squad)}">{fmt_delta(p.age_vs_squad)}</td>'
        f"<td>{p.caps if p.caps is not None else '—'}</td>"
        f'<td class="{delta_class(p.caps_vs_squad)}">{fmt_delta(p.caps_vs_squad, digits=0)}</td>'
        f"<td>{p.goals if p.goals is not None else '—'}</td>"
        f"<td>{'★' if p.most_capped_on_team else '—'}</td>"
        f"<td>{'Yes' if p.plays_abroad else 'No'}</td>"
        f"<td>{_esc(p.club)}</td>"
        "</tr>"
        for p in profiles
    )
    most_capped_n = sum(1 for p in profiles if p.most_capped_on_team)
    return f"""<div class="table-wrap">
  <p class="table-note">{len(profiles)} captains · {most_capped_n} are their team's most-capped player (★)
  · Δ age / Δ caps vs squad average (excluding captain). Highlighted rows: most-capped or top scorer on team.</p>
  <table class="data-table">
    <thead>
      <tr>
        <th>Captain</th><th>Nation</th><th>Pos</th><th>Age</th><th>Δ age</th>
        <th>Caps</th><th>Δ caps</th><th>Goals</th><th>★</th><th>Abroad?</th><th>Club</th>
      </tr>
    </thead>
    <tbody>
{rows_html}
    </tbody>
  </table>
</div>"""


def caps_leaderboard_table_html(
    rows: list[PlayerRow],
    *,
    limit: int = 40,
    veteran_min: int = VETERAN_CAPS,
) -> str:
    """Caps leaders with 100+ cap veterans highlighted in one table."""
    leaders = top_players(rows, "caps", limit=limit)
    vet_total = len(veterans(rows, min_caps=veteran_min))
    if not leaders:
        return '<p class="table-note">No caps data.</p>'

    columns = ("Player", "Nation", "Pos", "Caps", "Goals", "Age", "Club")

    def cell(row: PlayerRow, col: str) -> str:
        mapping = {
            "Player": row.name,
            "Nation": row.nation,
            "Pos": row.pos,
            "Caps": str(row.caps if row.caps is not None else "—"),
            "Goals": str(row.goals if row.goals is not None else "—"),
            "Age": str(row.age if row.age is not None else "—"),
            "Club": row.club,
        }
        return _esc(mapping[col])

    header = (
        '<th class="rank">#</th>'
        + "".join(f"<th>{_esc(c)}</th>" for c in columns)
        + f'<th title="{veteran_min}+ caps">★</th>'
    )
    body = "\n".join(
        "      <tr"
        + (' class="row-highlight"' if (r.caps or 0) >= veteran_min else "")
        + ">"
        + f'<td class="rank">{i}</td>'
        + "".join(f"<td>{cell(r, c)}</td>" for c in columns)
        + f'<td>{"★" if (r.caps or 0) >= veteran_min else "—"}</td>'
        + "</tr>"
        for i, r in enumerate(leaders, start=1)
    )
    below = max(0, vet_total - sum(1 for r in leaders if (r.caps or 0) >= veteran_min))
    extra = (
        f" · {below} more with {veteran_min}+ caps below rank {len(leaders)}"
        if below
        else ""
    )
    return f"""<div class="table-wrap">
  <p class="table-note">Top {len(leaders)} by international caps · {vet_total} players have
  {veteran_min}+ caps (★){extra}.</p>
  <table class="data-table">
    <thead><tr>{header}</tr></thead>
    <tbody>
{body}
    </tbody>
  </table>
</div>"""


def leaderboard_table_html(
    players: list[PlayerRow],
    *,
    title: str,
    metric: str,
    columns: tuple[str, ...] = ("Player", "Nation", "Pos", "Goals", "Caps", "Age", "Club"),
) -> str:
    """Scrollable HTML table for a ranked player list."""
    if not players:
        return f'<p class="table-note">{_esc(title)}: no data.</p>'

    def cell(row: PlayerRow, col: str) -> str:
        mapping = {
            "Player": row.name,
            "Nation": row.nation,
            "Pos": row.pos,
            "Goals": str(row.goals if row.goals is not None else "—"),
            "Caps": str(row.caps if row.caps is not None else "—"),
            "Age": str(row.age if row.age is not None else "—"),
            "Club": row.club,
        }
        return _esc(mapping[col])

    header = "<th class=\"rank\">#</th>" + "".join(f"<th>{_esc(c)}</th>" for c in columns)
    body = "\n".join(
        "      <tr>"
        + f'<td class="rank">{i}</td>'
        + "".join(f"<td>{cell(r, c)}</td>" for c in columns)
        + "</tr>"
        for i, r in enumerate(players, start=1)
    )
    metric_note = "international goals" if metric == "goals" else "international caps"
    return f"""<div class="table-wrap">
  <p class="table-note">{_esc(title)} — {len(players)} players ({metric_note}, pre-tournament).</p>
  <table class="data-table">
    <thead><tr>{header}</tr></thead>
    <tbody>
{body}
    </tbody>
  </table>
</div>"""


def club_country_counts(rows: list[PlayerRow]) -> Counter[str]:
    return Counter(r.club_country for r in rows if r.club_country != "Unknown")
