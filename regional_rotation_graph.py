"""Readable Global/USA/India rotation knowledge graph.

All verified memberships are retained.  The default overview summarizes company
counts to fit a screen; Focus and All connections expose individual companies.
Requires existing rotation_graph_evidence.py and generated *_signals.csv/*_edges.csv.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from rotation_graph_evidence import QUADRANTS, graph_elements

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "data" / "dashboard_cache" / "rotation_graphs"
COLORS = {
    "Leading": "#38d9a9", "Improving": "#60a5fa",
    "Weakening": "#fbbf24", "Lagging": "#fb7185",
    "sector": "#b3e5fc", "factor": "#c4b5fd", "company": "#e5e7eb",
}
BACKGROUND = "#101827"


@st.cache_data(show_spinner=False, max_entries=48)
def _read_csv(filename: str, mtime: int) -> pd.DataFrame:
    try:
        return pd.read_csv(filename, keep_default_na=False)
    except (OSError, ValueError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def _load(region: str, period: str, kind: str) -> pd.DataFrame:
    path = STORE / f"{region.lower()}_{period}_{kind}.csv"
    return _read_csv(str(path), path.stat().st_mtime_ns if path.is_file() else -1)


def _manifest() -> dict:
    try:
        return json.loads((STORE / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def _available_index_nodes(nodes: list[dict]) -> list[dict]:
    rank = {q: i for i, q in enumerate(QUADRANTS)}
    return sorted(
        (n for n in nodes if n["type"] in ("sector", "factor")),
        key=lambda n: (rank.get(n["quadrant"], 99), n["type"], n["label"].lower()),
    )


def _node_hover(n: dict, member_count: int = 0) -> str:
    if n["type"] == "rotation":
        return f"<b>{n['label']}</b>"
    if n["type"] == "company":
        return f"<b>{n.get('name') or n['label']}</b><br>ID: {n['company_key']}"
    return (f"<b>{n['label']}</b><br>{n['type'].title()} · {n['quadrant']}"
            f"<br>Relative strength: {n.get('rs', 'N/A')}"
            f"<br>RS momentum: {n.get('momentum', 'N/A')}"
            f"<br>Connected companies: {member_count:,}")


def _connections(nodes: list[dict], links: list[tuple[str, str]]):
    by_id = {n["id"]: n for n in nodes}
    members = {n["id"]: set() for n in nodes if n["type"] in ("sector", "factor")}
    for source, target in links:
        if source in members and target.startswith("c:"):
            members[source].add(target)
    return by_id, members


def _draw(nodes: list[dict], links: list[tuple[str, str]], mode: str,
          focus_id: str | None = None, show_labels: bool = True):
    by_id, members = _connections(nodes, links)
    indices = _available_index_nodes(nodes)
    companies = sorted((n for n in nodes if n["type"] == "company"),
                       key=lambda n: n["label"].lower())
    if mode == "Focus on a sector / factor" and focus_id:
        chosen = {focus_id}
        visible_companies = [n for n in companies if n["id"] in members.get(focus_id, ())]
    elif mode == "All individual companies":
        chosen = {n["id"] for n in indices}
        visible_companies = companies
    else:  # Complete four-quadrant overview, each source retains its member count.
        chosen = {n["id"] for n in indices}
        visible_companies = []

    positions = {f"q:{q}": (0., 1 - (i + .5) / 4) for i, q in enumerate(QUADRANTS)}
    for i, n in enumerate(indices):
        positions[n["id"]] = (1.25, 1 - (i + .5) / max(1, len(indices)))

    # Each index has a visible summary node on the right in overview mode.
    summary_nodes = []
    if mode == "Overview (fits screen)":
        for i, n in enumerate(indices):
            sid = "summary:" + n["id"]
            summary_nodes.append({"id": sid, "label": f"{len(members[n['id']]):,} companies",
                                  "type": "summary", "quadrant": n["quadrant"],
                                  "source": n["id"]})
            positions[sid] = (2.55, 1 - (i + .5) / max(1, len(indices)))
    else:
        for i, n in enumerate(visible_companies):
            positions[n["id"]] = (2.55, 1 - (i + .5) / max(1, len(visible_companies)))

    fig = go.Figure()
    # Keep all index signals visible, including those with zero company memberships.
    for quadrant in QUADRANTS:
        xs, ys = [], []
        for n in indices:
            if n["quadrant"] != quadrant:
                continue
            a, b = positions[f"q:{quadrant}"], positions[n["id"]]
            xs += [a[0], b[0], None]
            ys += [a[1], b[1], None]
        if xs:
            fig.add_trace(go.Scattergl(x=xs, y=ys, mode="lines",
                    line=dict(color=COLORS[quadrant], width=1.5),
                    opacity=.35, hoverinfo="skip", showlegend=False))

        xs, ys = [], []
        if mode == "Overview (fits screen)":
            for n in indices:
                if n["quadrant"] != quadrant:
                    continue
                a, b = positions[n["id"]], positions["summary:" + n["id"]]
                xs += [a[0], b[0], None]
                ys += [a[1], b[1], None]
        else:
            for source, target in links:
                if source not in chosen or target not in positions:
                    continue
                if by_id.get(source, {}).get("quadrant") != quadrant:
                    continue
                a, b = positions[source], positions[target]
                xs += [a[0], b[0], None]
                ys += [a[1], b[1], None]
        if xs:
            fig.add_trace(go.Scattergl(x=xs, y=ys, mode="lines",
                    line=dict(color=COLORS[quadrant], width=1),
                    opacity=.28 if mode != "Overview (fits screen)" else .45,
                    hoverinfo="skip", showlegend=False))

    def add_group(group, name, color, size, label_mode="text", symbol="circle"):
        if not group:
            return
        fig.add_trace(go.Scattergl(
            x=[positions[n["id"]][0] for n in group],
            y=[positions[n["id"]][1] for n in group],
            mode="markers+text" if label_mode == "text" else "markers",
            marker=dict(color=color, size=size, symbol=symbol),
            text=[n["label"] for n in group],
            textposition="middle right" if name != "Rotations" else "middle left",
            textfont=dict(size=11 if name != "Companies" else 10, color="#edf2f7"),
            hovertext=[_node_hover(n, len(members.get(n["id"], ()))) for n in group],
            hovertemplate="%{hovertext}<extra></extra>", name=name,
        ))

    rotations = [by_id[f"q:{q}"] for q in QUADRANTS]
    add_group(rotations, "Rotations", [COLORS[q] for q in QUADRANTS], 21)
    add_group([n for n in indices if n["type"] == "sector"], "Sectors", COLORS["sector"], 10)
    add_group([n for n in indices if n["type"] == "factor"], "Factors", COLORS["factor"], 10, symbol="diamond")
    if summary_nodes:
        fig.add_trace(go.Scattergl(
            x=[positions[n["id"]][0] for n in summary_nodes],
            y=[positions[n["id"]][1] for n in summary_nodes],
            mode="markers+text", marker=dict(size=8, color="#94a3b8"),
            text=[n["label"] for n in summary_nodes], textposition="middle right",
            textfont=dict(size=10, color="#e5e7eb"),
            hovertext=[f"{n['label']}<br>Select Focus mode to see every company" for n in summary_nodes],
            hovertemplate="%{hovertext}<extra></extra>", name="Company counts"))
    else:
        show_company_text = show_labels and len(visible_companies) <= 45
        add_group(visible_companies, "Companies", COLORS["company"], 7,
                  label_mode="text" if show_company_text else "hover")

    for x, caption in ((0, "ROTATIONS"), (1.25, "SECTORS / FACTORS"),
                       (2.55, "COMPANIES" if not summary_nodes else "COMPANY MEMBERSHIPS")):
        fig.add_annotation(x=x, y=1.065, text=f"<b>{caption}</b>",
                           showarrow=False, font=dict(size=12, color="#e5edf7"))
    graph_height = 720 if mode != "All individual companies" else max(720, min(3800, len(companies) * 12))
    fig.update_layout(
        height=graph_height, paper_bgcolor=BACKGROUND, plot_bgcolor=BACKGROUND,
        margin=dict(l=110, r=120, t=75, b=25),
        xaxis=dict(visible=False, range=[-.38, 3.03], fixedrange=True),
        yaxis=dict(visible=False, range=[-.035, 1.12], fixedrange=True),
        font=dict(color="#e5edf7"), hovermode="closest", showlegend=True,
        legend=dict(orientation="h", y=-.02, x=.02),
    )
    st.plotly_chart(fig, use_container_width=True,
                    config={"displaylogo": False, "scrollZoom": False})


def render_graph(region: str):
    if region not in ("Global", "USA", "India"):
        st.error("Unsupported region")
        return
    st.title(f"{region} Rotation Knowledge Graph")
    st.caption("One network · Four rotations → Sectors & Factors → Companies")
    period = st.selectbox("Lookback", ["1m", "3m", "6m"], index=1,
                          key=f"kg_period_{region}")
    signals = _load(region, period, "signals")
    edges = _load(region, period, "edges")
    status = _manifest().get("regions", {}).get(f"{region.lower()}_{period}", {})
    if signals.empty:
        st.warning("No rotation signals available. Run the automatic refresh workflow.")
        if status.get("error"):
            st.error(str(status["error"]))
        return
    if not (STORE / f"{region.lower()}_{period}_edges.csv").is_file():
        st.error("Graph membership snapshot missing. Run the Refresh Knowledge Graphs workflow.")
        return
    if status.get("error"):
        st.warning(f"Latest build issue: {status['error']}")
    nodes, links = graph_elements(signals, edges)
    cols = st.columns(4)
    for col, quadrant in zip(cols, QUADRANTS):
        signals_count = int(signals["quadrant"].eq(quadrant).sum()) if "quadrant" in signals else 0
        company_count = (int(edges.loc[edges["quadrant"].eq(quadrant), "company_key"].nunique())
                         if not edges.empty and {"quadrant", "company_key"}.issubset(edges.columns) else 0)
        col.metric(quadrant, f"{signals_count} indices", f"{company_count} companies", delta_color="off")
    st.caption(f"{len(nodes):,} nodes · {len(links):,} relationships · "
               "All memberships retained in the data")

    mode = st.radio("Graph display", ["Overview (fits screen)",
                      "Focus on a sector / factor", "All individual companies"],
                    horizontal=True, key=f"kg_mode_{region}")
    index_nodes = _available_index_nodes(nodes)
    focus_id = None
    if mode == "Focus on a sector / factor":
        if not index_nodes:
            st.info("No sector or factor signals to select.")
        else:
            options = {n["id"]: f"{n['quadrant']} · {n['type'].title()} · {n['label']}" for n in index_nodes}
            focus_id = st.selectbox("Choose a sector or factor", options,
                                    format_func=lambda key: options[key], key=f"kg_focus_{region}")
            st.caption("All four rotations and all sector/factor signals remain visible. "
                       "Only the selected source's company links are expanded.")
    elif mode == "Overview (fits screen)":
        st.info("To keep everything readable on one screen, the right column shows company counts "
                "for every sector/factor. Choose Focus to see individual companies or "
                "All individual companies for the complete network.")
    else:
        st.caption("Full network: all company nodes and verified links. "
                   "Large networks need scrolling; hover over company dots for names.")
    _draw(nodes, links, mode, focus_id)

    if status.get("signal_asof"):
        st.caption(f"Signals as of: {status['signal_asof']}")
    if any(not signals["quadrant"].eq(q).any() for q in QUADRANTS) if "quadrant" in signals else True:
        st.warning("Some rotations have no valid index signals in this snapshot; no signals were invented.")
    with st.expander("All sector and factor signals"):
        st.dataframe(signals, use_container_width=True, hide_index=True)
    with st.expander("All company memberships (search and sort)"):
        st.dataframe(edges, use_container_width=True, hide_index=True)
    with st.expander("Unmapped holdings sources"):
        st.dataframe(_load(region, period, "unmapped"), use_container_width=True, hide_index=True)
    st.caption("Rotation applies to sector/factor indices. A company link represents "
               "verified holdings membership, not independent company price rotation.")
