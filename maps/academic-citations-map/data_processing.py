"""OpenAlex search and citation-network expansion."""

from __future__ import annotations

import math
import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Literal

TrimMode = Literal["smart", "simple", "connections"]

import requests

from lib.env import env, load_repo_env

OPENALEX_BASE = "https://api.openalex.org"
USER_AGENT = "maps-repo/1.0 (academic-citations-map; educational)"
WORK_SELECT = (
    "id,display_name,publication_year,cited_by_count,referenced_works_count,doi"
)

_OPENALEX_ID_RE = re.compile(r"W\d+")


def normalize_doi(doi: str | None) -> str | None:
    """Lowercase bare DOI for duplicate matching."""
    if not doi:
        return None
    text = str(doi).strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    return text.rstrip("/") or None


def normalize_title_key(title: str) -> str:
    """Collapse punctuation/case for title-based duplicate checks."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", title.lower())).strip()


def normalize_openalex_id(work_id: str) -> str:
    """Return bare OpenAlex work id (e.g. W4393687471)."""
    text = work_id.strip()
    match = _OPENALEX_ID_RE.search(text)
    if not match:
        msg = f"Not a valid OpenAlex work id: {work_id!r}"
        raise ValueError(msg)
    return match.group(0)


def _session() -> requests.Session:
    load_repo_env()
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    api_key = env("OPENALEX_API_KEY")
    if api_key:
        session.params = {"api_key": api_key}
    return session


def _get_json(session: requests.Session, url: str, *, params: dict[str, Any] | None = None) -> dict:
    response = session.get(url, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


@dataclass(frozen=True)
class WorkSummary:
    """Minimal work metadata for nodes and search results."""

    id: str
    display_name: str
    publication_year: int | None
    cited_by_count: int
    doi: str | None = None

    @classmethod
    def from_api(cls, record: dict[str, Any]) -> WorkSummary:
        return cls(
            id=normalize_openalex_id(record["id"]),
            display_name=(record.get("display_name") or "Untitled").strip(),
            publication_year=record.get("publication_year"),
            cited_by_count=int(record.get("cited_by_count") or 0),
            doi=normalize_doi(record.get("doi")),
        )

    def with_id(self, work_id: str) -> WorkSummary:
        return WorkSummary(
            id=normalize_openalex_id(work_id),
            display_name=self.display_name,
            publication_year=self.publication_year,
            cited_by_count=self.cited_by_count,
            doi=self.doi,
        )

    def label(self) -> str:
        year = f" ({self.publication_year})" if self.publication_year else ""
        cites = f", cited {self.cited_by_count}×" if self.cited_by_count else ""
        name = self.display_name if len(self.display_name) <= 80 else self.display_name[:77] + "…"
        return f"{name}{year}{cites}"


@dataclass
class DedupeReport:
    """Duplicate OpenAlex records merged into one canonical node."""

    merges: list[tuple[str, str, str]] = field(default_factory=list)  # alias, canonical, reason

    @property
    def merge_count(self) -> int:
        return len(self.merges)

    def groups(self) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for alias, canonical, _reason in self.merges:
            grouped.setdefault(canonical, []).append(alias)
        return grouped


class WorkDeduplicator:
    """Map duplicate OpenAlex work ids onto a single canonical id."""

    def __init__(self, seed_id: str, *, match_title_year: bool = True) -> None:
        self.seed_id = normalize_openalex_id(seed_id)
        self.match_title_year = match_title_year
        self.report = DedupeReport()
        self._canonical: dict[str, str] = {}
        self._by_doi: dict[str, str] = {}
        self._by_title_year: dict[tuple[str, int | None], str] = {}
        self._nodes: dict[str, WorkSummary] = {}

    def resolve_id(self, work_id: str) -> str:
        wid = normalize_openalex_id(work_id)
        while wid in self._canonical and self._canonical[wid] != wid:
            wid = self._canonical[wid]
        return wid

    def _pick_canonical(self, existing_id: str, new_id: str) -> str:
        existing_id = self.resolve_id(existing_id)
        new_id = self.resolve_id(new_id)
        if existing_id == new_id:
            return existing_id
        if existing_id == self.seed_id or new_id == self.seed_id:
            return self.seed_id
        a = self._nodes.get(existing_id)
        b = self._nodes.get(new_id)
        score_a = (a.cited_by_count if a else 0, a.publication_year or 0 if a else 0)
        score_b = (b.cited_by_count if b else 0, b.publication_year or 0 if b else 0)
        return existing_id if score_a >= score_b else new_id

    def _link_alias(self, alias_id: str, canonical_id: str, reason: str) -> str:
        alias_id = normalize_openalex_id(alias_id)
        canonical_id = self.resolve_id(canonical_id)
        if alias_id == canonical_id:
            return canonical_id
        prev = self.resolve_id(alias_id)
        if prev != alias_id:
            canonical_id = self._pick_canonical(prev, canonical_id)
        self._canonical[alias_id] = canonical_id
        if alias_id in self._nodes:
            merged = self._merge_metadata(canonical_id, self._nodes.pop(alias_id))
            self._nodes[canonical_id] = merged
        if any(m[0] == alias_id for m in self.report.merges):
            return canonical_id
        self.report.merges.append((alias_id, canonical_id, reason))
        return canonical_id

    def _merge_metadata(self, canonical_id: str, incoming: WorkSummary) -> WorkSummary:
        canonical_id = self.resolve_id(canonical_id)
        existing = self._nodes.get(canonical_id)
        if existing is None:
            return incoming.with_id(canonical_id)
        if incoming.cited_by_count > existing.cited_by_count:
            return incoming.with_id(canonical_id)
        if incoming.cited_by_count == existing.cited_by_count and len(incoming.display_name) > len(
            existing.display_name
        ):
            return incoming.with_id(canonical_id)
        return existing

    def register(self, work: WorkSummary) -> WorkSummary:
        """Return the work under its canonical id; record merges when duplicates are found."""
        work_id = normalize_openalex_id(work.id)
        self._nodes[work_id] = work
        canonical_id = work_id

        doi = work.doi
        if doi:
            other = self._by_doi.get(doi)
            if other is None:
                self._by_doi[doi] = work_id
            else:
                canonical_id = self._pick_canonical(other, work_id)
                self._by_doi[doi] = canonical_id
                if work_id != canonical_id:
                    canonical_id = self._link_alias(work_id, canonical_id, "doi")
                else:
                    canonical_id = self._link_alias(other, canonical_id, "doi")
                    self._by_doi[doi] = canonical_id

        if self.match_title_year and canonical_id == work_id:
            title_key = (normalize_title_key(work.display_name), work.publication_year)
            if title_key[0]:
                other = self._by_title_year.get(title_key)
                if other is None:
                    self._by_title_year[title_key] = work_id
                else:
                    canonical_id = self._pick_canonical(other, work_id)
                    self._by_title_year[title_key] = canonical_id
                    if work_id != canonical_id:
                        canonical_id = self._link_alias(work_id, canonical_id, "title+year")
                    else:
                        canonical_id = self._link_alias(other, canonical_id, "title+year")
                        self._by_title_year[title_key] = canonical_id

        canonical_id = self.resolve_id(work_id)
        merged = self._merge_metadata(canonical_id, work)
        self._nodes[canonical_id] = merged
        return merged.with_id(canonical_id)


def dedupe_work_list(works: list[WorkSummary], *, seed_id: str | None = None) -> list[WorkSummary]:
    """Collapse duplicate search hits (same DOI or normalized title+year)."""
    if not works:
        return []
    deduper = WorkDeduplicator(seed_id or works[0].id)
    out: list[WorkSummary] = []
    seen_canonical: set[str] = set()
    for work in works:
        canonical = deduper.register(work)
        if canonical.id not in seen_canonical:
            seen_canonical.add(canonical.id)
            out.append(canonical)
    return out


@dataclass(frozen=True)
class SmartTrimConfig:
    """Heuristic pruning for deeper hops (beyond bare degree >= 2)."""

    smart_from_hop: int = 2
    min_connections_hop1: int = 2
    min_connections_deep: int = 3
    min_cited_for_low_degree: int = 5
    drop_bottom_fraction: float = 0.35
    protect_first_ring: bool = True


@dataclass
class TrimReport:
    """Trimming activity per expansion hop."""

    steps: list[str] = field(default_factory=list)

    def log(self, message: str) -> None:
        self.steps.append(message)


@dataclass
class CitationNetwork:
    """Directed citation graph: edge A → B means A cites B."""

    seed_id: str
    nodes: dict[str, WorkSummary] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)
    dedupe_report: DedupeReport = field(default_factory=DedupeReport)
    trim_report: TrimReport = field(default_factory=TrimReport)

    def add_edge(self, source_id: str, target_id: str) -> None:
        sid, tid = normalize_openalex_id(source_id), normalize_openalex_id(target_id)
        if sid == tid:
            return
        pair = (sid, tid)
        if pair not in self.edges:
            self.edges.append(pair)

    def upsert_node(self, work: WorkSummary) -> None:
        """Insert or update a node under its canonical id."""
        existing = self.nodes.get(work.id)
        if existing is None or work.cited_by_count >= existing.cited_by_count:
            self.nodes[work.id] = work

    def merge_node_ids(self, alias_id: str, canonical_id: str) -> None:
        """Rewire edges and drop a duplicate node id."""
        alias_id, canonical_id = normalize_openalex_id(alias_id), normalize_openalex_id(canonical_id)
        if alias_id == canonical_id or alias_id not in self.nodes:
            return
        alias_work = self.nodes.pop(alias_id)
        existing = self.nodes.get(canonical_id)
        if existing is None or alias_work.cited_by_count > existing.cited_by_count:
            self.nodes[canonical_id] = alias_work.with_id(canonical_id)
        self.edges = [
            (
                canonical_id if source == alias_id else source,
                canonical_id if target == alias_id else target,
            )
            for source, target in self.edges
        ]
        self.dedupe_edges()

    def dedupe_edges(self) -> None:
        """Remove duplicate and self-loop edges after id remapping."""
        seen: set[tuple[str, str]] = set()
        unique: list[tuple[str, str]] = []
        for source, target in self.edges:
            if source == target or (source, target) in seen:
                continue
            seen.add((source, target))
            unique.append((source, target))
        self.edges = unique

    def degree(self) -> dict[str, int]:
        """Undirected incident-edge count per node (in + out)."""
        counts: dict[str, int] = dict.fromkeys(self.nodes, 0)
        for source, target in self.edges:
            if source in counts:
                counts[source] += 1
            if target in counts:
                counts[target] += 1
        return counts


def prune_low_connection_nodes(
    network: CitationNetwork,
    *,
    min_connections: int = 2,
    keep_ids: frozenset[str] | None = None,
    candidate_ids: frozenset[str] | None = None,
) -> int:
    """
    Drop nodes with fewer than ``min_connections`` incident edges.

    When ``candidate_ids`` is set, only those nodes may be removed (e.g. papers
    added on the latest hop). Repeats until stable among candidates. The seed is
    always kept. Returns the number of nodes removed.
    """
    if min_connections < 1:
        msg = "min_connections must be >= 1"
        raise ValueError(msg)

    keep = keep_ids if keep_ids is not None else frozenset({network.seed_id})
    removed_total = 0

    while True:
        degrees = network.degree()
        to_remove = [
            node_id
            for node_id, count in degrees.items()
            if node_id not in keep
            and count < min_connections
            and (candidate_ids is None or node_id in candidate_ids)
        ]
        if not to_remove:
            break
        for node_id in to_remove:
            network.nodes.pop(node_id, None)
        remove_set = set(to_remove)
        network.edges = [
            edge
            for edge in network.edges
            if edge[0] not in remove_set and edge[1] not in remove_set
        ]
        removed_total += len(to_remove)

    return removed_total


def _undirected_adjacency(network: CitationNetwork) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {node_id: set() for node_id in network.nodes}
    for source, target in network.edges:
        if source in adj and target in adj:
            adj[source].add(target)
            adj[target].add(source)
    return adj


def _distance_from_seed(network: CitationNetwork) -> dict[str, int]:
    seed = network.seed_id
    dist: dict[str, int] = {seed: 0}
    queue: deque[str] = deque([seed])
    adj = _undirected_adjacency(network)
    while queue:
        node_id = queue.popleft()
        for neighbor in adj.get(node_id, ()):
            if neighbor not in dist:
                dist[neighbor] = dist[node_id] + 1
                queue.append(neighbor)
    return dist


def _importance_score(work: WorkSummary, degree: int, dist_from_seed: int) -> float:
    """Higher = more worth keeping in the visualization."""
    if dist_from_seed <= 1:
        proximity = 3.0
    else:
        proximity = 1.5 / (1 + dist_from_seed)
    return math.log1p(work.cited_by_count) * 2.0 + max(0, degree - 2) * 1.25 + proximity


def _score_percentile_cutoff(scores: list[float], drop_bottom_fraction: float) -> float:
    if not scores:
        return 0.0
    ordered = sorted(scores)
    idx = min(int(len(ordered) * drop_bottom_fraction), len(ordered) - 1)
    return ordered[idx]


def _remove_nodes(network: CitationNetwork, to_remove: set[str]) -> int:
    if not to_remove:
        return 0
    for node_id in to_remove:
        network.nodes.pop(node_id, None)
    network.edges = [
        edge
        for edge in network.edges
        if edge[0] not in to_remove and edge[1] not in to_remove
    ]
    return len(to_remove)


def prune_smart_nodes(
    network: CitationNetwork,
    *,
    hop: int,
    candidate_ids: frozenset[str],
    first_ring: frozenset[str],
    config: SmartTrimConfig,
    report: TrimReport | None = None,
) -> int:
    """
    Trim papers added on this hop.

    Hop 1: drop nodes with fewer than two connections (same as simple trim).
    Hop 2+: also require stronger local role or citation impact; peel low-score
    degree-2 chain nodes that survive the degree floor.
    """
    if not candidate_ids:
        return 0

    keep = {network.seed_id}
    if config.protect_first_ring:
        keep |= set(first_ring)

    removed_total = 0
    min_conn = config.min_connections_hop1 if hop == 1 else config.min_connections_deep
    removed_total += prune_low_connection_nodes(
        network,
        min_connections=min_conn,
        keep_ids=frozenset(keep),
        candidate_ids=candidate_ids,
    )
    if report is not None and removed_total:
        report.log(f"hop {hop}: removed {removed_total} with <{min_conn} connection(s)")

    if hop < config.smart_from_hop:
        return removed_total

    degrees = network.degree()
    dist = _distance_from_seed(network)
    candidates = [
        node_id
        for node_id in candidate_ids
        if node_id in network.nodes and node_id not in keep
    ]
    if not candidates:
        return removed_total

    scores = {
        node_id: _importance_score(network.nodes[node_id], degrees.get(node_id, 0), dist.get(node_id, 99))
        for node_id in candidates
    }
    cutoff = _score_percentile_cutoff(list(scores.values()), config.drop_bottom_fraction)

    to_remove: set[str] = set()
    for node_id in candidates:
        work = network.nodes[node_id]
        degree = degrees.get(node_id, 0)
        score = scores[node_id]
        low_degree = degree < config.min_connections_deep
        weak_chain = (
            degree <= 2
            and work.cited_by_count < config.min_cited_for_low_degree
            and score <= cutoff
        )
        if low_degree or weak_chain:
            to_remove.add(node_id)

    removed_smart = _remove_nodes(network, to_remove)
    if report is not None and removed_smart:
        report.log(
            f"hop {hop}: smart-trim removed {removed_smart} "
            f"(low degree or weak chain, score cutoff {cutoff:.2f})"
        )
    return removed_total + removed_smart


def cap_network_by_connections(
    network: CitationNetwork,
    max_works: int,
    *,
    report: TrimReport | None = None,
) -> int:
    """
    Drop the least-connected papers until at most ``max_works`` nodes remain.

    Each pass removes every non-seed paper tied for the fewest incident edges in
    the current graph, then repeats until the pool is small enough.
    """
    if max_works < 1:
        msg = "max_works must be >= 1"
        raise ValueError(msg)

    seed = network.seed_id
    if len(network.nodes) <= max_works:
        return 0

    removed_total = 0
    while len(network.nodes) > max_works:
        degrees = network.degree()
        removable = [node_id for node_id in network.nodes if node_id != seed]
        if not removable:
            break
        min_degree = min(degrees.get(node_id, 0) for node_id in removable)
        to_remove = {
            node_id for node_id in removable if degrees.get(node_id, 0) == min_degree
        }
        if not to_remove:
            break
        removed_total += _remove_nodes(network, to_remove)

    if report is not None and removed_total:
        report.log(
            f"connection cap: {len(network.nodes)} works kept "
            f"(max {max_works}, removed {removed_total} in min-degree batches)"
        )
    return removed_total


def prune_after_hop(
    network: CitationNetwork,
    *,
    hop: int,
    candidate_ids: frozenset[str],
    first_ring: frozenset[str],
    trim_mode: TrimMode,
    min_connections: int,
    smart_config: SmartTrimConfig | None,
    report: TrimReport | None = None,
) -> int:
    if trim_mode == "connections":
        return 0
    if trim_mode == "simple":
        removed = prune_low_connection_nodes(
            network,
            min_connections=min_connections,
            candidate_ids=candidate_ids,
        )
        if report is not None and removed:
            report.log(f"hop {hop}: removed {removed} with <{min_connections} connection(s)")
        return removed
    config = smart_config or SmartTrimConfig()
    if hop == 1 and min_connections != config.min_connections_hop1:
        config = SmartTrimConfig(
            smart_from_hop=config.smart_from_hop,
            min_connections_hop1=min_connections,
            min_connections_deep=config.min_connections_deep,
            min_cited_for_low_degree=config.min_cited_for_low_degree,
            drop_bottom_fraction=config.drop_bottom_fraction,
            protect_first_ring=config.protect_first_ring,
        )
    return prune_smart_nodes(
        network,
        hop=hop,
        candidate_ids=candidate_ids,
        first_ring=first_ring,
        config=config,
        report=report,
    )


def search_works(
    query: str,
    *,
    per_page: int = 25,
    session: requests.Session | None = None,
) -> list[WorkSummary]:
    """Full-text search for works (OpenAlex Search endpoint)."""
    session = session or _session()
    payload = _get_json(
        session,
        f"{OPENALEX_BASE}/works",
        params={
            "search": query.strip(),
            "per_page": min(per_page, 100),
            "select": WORK_SELECT,
        },
    )
    works = [WorkSummary.from_api(row) for row in payload.get("results", [])]
    return dedupe_work_list(works)


def fetch_work(work_id: str, *, session: requests.Session | None = None) -> WorkSummary:
    session = session or _session()
    wid = normalize_openalex_id(work_id)
    payload = _get_json(
        session,
        f"{OPENALEX_BASE}/works/{wid}",
        params={"select": WORK_SELECT},
    )
    return WorkSummary.from_api(payload)


def _title_match_score(query: str, display_name: str) -> int:
    """Higher = better match to the search query (title relevance, not citations)."""
    q = query.strip().lower()
    title = display_name.strip().lower()
    if not q or not title:
        return 0
    if q == title:
        return 100
    if q in title or title in q:
        return 80
    q_tokens = [t for t in re.split(r"\W+", q) if len(t) > 2]
    if not q_tokens:
        return 0
    overlap = sum(1 for t in q_tokens if t in title)
    return int(60 * overlap / len(q_tokens))


def pick_work(
    results: list[WorkSummary],
    *,
    pick_index: int | None = None,
    prefer_id: str | None = None,
    query: str | None = None,
) -> WorkSummary:
    if not results:
        msg = "No works matched the search query."
        raise ValueError(msg)
    if prefer_id:
        pid = normalize_openalex_id(prefer_id)
        for work in results:
            if work.id == pid:
                return work
    if pick_index is not None:
        if pick_index < 0 or pick_index >= len(results):
            msg = f"pick_index {pick_index} out of range (0–{len(results) - 1})"
            raise ValueError(msg)
        return results[pick_index]
    if len(results) == 1:
        return results[0]
    if query:
        scored = [(w, _title_match_score(query, w.display_name)) for w in results]
        best_title_score = max(s for _, s in scored)
        if best_title_score > 0:
            candidates = [w for w, s in scored if s == best_title_score]
            return max(candidates, key=lambda w: (w.cited_by_count, w.publication_year or 0))
    return max(results, key=lambda w: (w.cited_by_count, w.publication_year or 0))


def _paginate_works(
    session: requests.Session,
    *,
    filter_expr: str,
    max_results: int | None = None,
) -> list[WorkSummary]:
    """List+filter with pagination (per_page=100)."""
    out: list[WorkSummary] = []
    page = 1
    while True:
        payload = _get_json(
            session,
            f"{OPENALEX_BASE}/works",
            params={
                "filter": filter_expr,
                "per_page": 100,
                "page": page,
                "select": WORK_SELECT,
            },
        )
        batch = [WorkSummary.from_api(row) for row in payload.get("results", [])]
        if not batch:
            break
        out.extend(batch)
        if max_results is not None and len(out) >= max_results:
            return out[:max_results]
        meta = payload.get("meta") or {}
        if page >= int(meta.get("page_count") or 1):
            break
        page += 1
        time.sleep(0.11)
    return out


def _neighbor_ids_via_filters(
    session: requests.Session,
    work_id: str,
    *,
    max_per_direction: int | None,
) -> tuple[list[WorkSummary], list[WorkSummary]]:
    """
    Return (outgoing_refs, incoming_citers) for a work.

    OpenAlex filters: cited_by = works this paper cites; cites = works citing this paper.
    """
    wid = normalize_openalex_id(work_id)
    refs = _paginate_works(
        session,
        filter_expr=f"cited_by:{wid}",
        max_results=max_per_direction,
    )
    citers = _paginate_works(
        session,
        filter_expr=f"cites:{wid}",
        max_results=max_per_direction,
    )
    return refs, citers


def _integrate_work(
    network: CitationNetwork,
    deduper: WorkDeduplicator,
    work: WorkSummary,
) -> WorkSummary:
    """Register work for deduplication and ensure a single canonical node exists."""
    raw_id = work.id
    canonical = deduper.register(work)
    if raw_id != canonical.id and raw_id in network.nodes:
        network.merge_node_ids(raw_id, canonical.id)
    network.upsert_node(canonical)
    return canonical


def _finalize_network_nodes(network: CitationNetwork, deduper: WorkDeduplicator) -> None:
    """Merge any remaining alias node ids and drop stale entries."""
    for node_id in list(network.nodes):
        canonical_id = deduper.resolve_id(node_id)
        if canonical_id != node_id:
            network.merge_node_ids(node_id, canonical_id)
    stale = [node_id for node_id in network.nodes if deduper.resolve_id(node_id) != node_id]
    for node_id in stale:
        network.nodes.pop(node_id, None)
    network.dedupe_edges()


def expand_citation_network(
    seed_id: str,
    *,
    depth: int = 1,
    max_per_direction: int | None = 200,
    trim_after_each_hop: bool = True,
    trim_mode: TrimMode = "connections",
    min_connections: int = 2,
    smart_trim: SmartTrimConfig | None = None,
    max_works: int | None = 100,
    dedupe: bool = True,
    dedupe_title_year: bool = True,
    session: requests.Session | None = None,
) -> CitationNetwork:
    """
    BFS expansion of citation links around a seed work.

    depth=0: seed plus its direct references and citing works.
    depth=1: also expand those neighbors one hop (and so on).

    When ``trim_after_each_hop`` is true (default), nodes are pruned after expansion.
    ``trim_mode='connections'`` (default) keeps the seed and repeatedly drops the
    least-connected paper until ``max_works`` nodes remain. ``'smart'`` / ``'simple'``
    use per-hop rules, then apply the same cap when ``max_works`` is set.
    """
    if depth < 0:
        msg = "depth must be >= 0"
        raise ValueError(msg)

    session = session or _session()
    seed = normalize_openalex_id(seed_id)
    deduper = WorkDeduplicator(seed, match_title_year=dedupe_title_year) if dedupe else None
    seed_work = fetch_work(seed, session=session)
    if deduper:
        seed_work = deduper.register(seed_work)
    network = CitationNetwork(seed_id=seed_work.id)
    network.upsert_node(seed_work)

    frontier = {seed_work.id}
    seen = {seed_work.id}
    first_ring: set[str] = set()

    for hop in range(depth + 1):
        added_this_hop: set[str] = set()
        next_frontier: set[str] = set()
        for wid in frontier:
            refs, citers = _neighbor_ids_via_filters(
                session,
                wid,
                max_per_direction=max_per_direction,
            )
            source = deduper.resolve_id(wid) if deduper else wid
            for ref in refs:
                if deduper:
                    ref = _integrate_work(network, deduper, ref)
                else:
                    network.upsert_node(ref)
                network.add_edge(source, ref.id)
            for citer in citers:
                if deduper:
                    citer = _integrate_work(network, deduper, citer)
                else:
                    network.upsert_node(citer)
                network.add_edge(citer.id, source)

            for neighbor in (*refs, *citers):
                nid = deduper.resolve_id(neighbor.id) if deduper else neighbor.id
                if nid not in seen:
                    seen.add(nid)
                    next_frontier.add(nid)
                    added_this_hop.add(nid)

        if hop == 0:
            first_ring |= added_this_hop

        # Per-hop trim (not used in connections mode). Skip hop 0: neighbors only link to seed.
        if (
            trim_after_each_hop
            and trim_mode != "connections"
            and hop > 0
            and added_this_hop
        ):
            prune_after_hop(
                network,
                hop=hop,
                candidate_ids=frozenset(added_this_hop),
                first_ring=frozenset(first_ring),
                trim_mode=trim_mode,
                min_connections=min_connections,
                smart_config=smart_trim,
                report=network.trim_report,
            )

        frontier = next_frontier & set(network.nodes)
        if not frontier:
            break
        time.sleep(0.11)

    if deduper:
        _finalize_network_nodes(network, deduper)
        network.dedupe_report = deduper.report

    if trim_after_each_hop and max_works is not None:
        cap_network_by_connections(network, max_works, report=network.trim_report)

    return network
