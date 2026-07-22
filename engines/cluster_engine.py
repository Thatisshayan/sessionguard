"""
engines/cluster_engine.py
--------------------------
V12: Cross-session intelligence.
Groups sessions into behaviour clusters using cosine similarity
between session fingerprints. No ML library needed — pure similarity math.

Also provides:
  - Dataset-wide risk summary
  - Peer benchmarking (compare vs cluster average)
  - Anomaly detection (sessions that don't fit any cluster)
  - Similarity map

Maturity: Working Prototype
Future:   sklearn KMeans for larger datasets (V12+), UMAP visualisation (V13).
"""

from __future__ import annotations
import json
from database.db import get_connection
from engines.session_fingerprint import (
    get_fingerprint, rebuild_all_fingerprints, cosine_similarity
)

try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False


# ── Clustering ────────────────────────────────────────────────────────────────

def _build_session_vectors(session_ids: list[int] | None = None) -> list[dict]:
    """Build session feature vectors for clustering."""
    conn = get_connection()
    if session_ids:
        placeholders = ",".join("?" * len(session_ids))
        rows = conn.execute(
            f"SELECT id, name, game_name, rtp, net_result, spins, avg_bet, losing_streak, biggest_win FROM sessions WHERE id IN ({placeholders})",
            session_ids
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, name, game_name, rtp, net_result, spins, avg_bet, losing_streak, biggest_win FROM sessions"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cluster_sessions_hdbscan(session_vectors: list[dict], min_cluster_size: int = 3) -> list[dict]:
    """Cluster sessions using HDBSCAN (optional dependency)."""
    if not HDBSCAN_AVAILABLE:
        return []

    import numpy as np

    features = []
    for sv in session_vectors:
        feat = [
            float(sv.get("rtp", 0)),
            float(sv.get("net_result", 0)),
            float(sv.get("spins", 0)),
            float(sv.get("avg_bet", 0)),
            float(sv.get("losing_streak", 0)),
            float(sv.get("biggest_win", 0)),
        ]
        features.append(feat)

    if len(features) < min_cluster_size:
        return []

    X = np.array(features)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        metric='euclidean',
        cluster_selection_method='eom',
    )
    labels = clusterer.fit_predict(X)

    result = []
    for i, (sv, label) in enumerate(zip(session_vectors, labels)):
        result.append({
            **sv,
            "cluster_label": str(label) if label >= 0 else "noise",
            "cluster_probability": float(clusterer.probabilities_[i]) if label >= 0 else 0.0,
            "clustering_method": "hdbscan",
        })
    return result


def cluster_sessions(session_ids: list[int] | None = None, use_hdbscan: bool = False) -> dict:
    """
    Cluster sessions. If use_hdbscan=True and HDBSCAN is installed, use it.
    Otherwise use cosine-similarity clustering (existing behavior).
    """
    if use_hdbscan and HDBSCAN_AVAILABLE:
        vectors = _build_session_vectors(session_ids)
        return {"method": "hdbscan", "clusters": cluster_sessions_hdbscan(vectors)}

    return _cosine_cluster_sessions(session_ids)


def _cosine_cluster_sessions(session_ids: list[int] | None = None) -> dict:
    """
    Group all sessions into clusters based on fingerprint similarity.
    Uses greedy agglomerative approach — fast, no ML needed.

    Returns cluster assignments and saves them to session_clusters table.
    """
    conn = get_connection()
    sessions = [dict(r) for r in conn.execute(
        "SELECT id, name, game_name, rtp, net_result FROM sessions"
    ).fetchall()]
    conn.close()

    if not sessions:
        return {"clusters": {}, "sessions": 0}

    # Ensure all fingerprints are computed
    rebuild_all_fingerprints()

    # Load all fingerprints
    fps = {}
    for s in sessions:
        fp = get_fingerprint(s["id"])
        if fp:
            fps[s["id"]] = fp

    # Greedy clustering
    clusters     : dict[str, list[int]] = {}   # label → [session_ids]
    assigned     : dict[int, str]       = {}   # session_id → cluster_label
    cluster_count = 0

    for sid, fp in fps.items():
        best_cluster = None
        best_score   = 0.0

        for label, members in clusters.items():
            # Compare against cluster centroid (first member for simplicity)
            centroid_fp = fps.get(members[0])
            if centroid_fp:
                score = cosine_similarity(fp, centroid_fp)
                if score > best_score:
                    best_score   = score
                    best_cluster = label

        if best_score >= similarity_threshold and best_cluster:
            clusters[best_cluster].append(sid)
            assigned[sid] = best_cluster
        else:
            # New cluster
            label = f"cluster_{cluster_count:02d}"
            clusters[label] = [sid]
            assigned[sid]   = label
            cluster_count  += 1

    # Persist to DB
    conn2 = get_connection()
    conn2.execute("DELETE FROM session_clusters")
    for sid, label in assigned.items():
        members = clusters[label]
        # Compute score vs centroid
        fp    = fps.get(sid, {})
        c_fp  = fps.get(members[0], {})
        score = cosine_similarity(fp, c_fp) if sid != members[0] else 1.0
        conn2.execute(
            "INSERT OR REPLACE INTO session_clusters "
            "(cluster_label, session_id, similarity_score) VALUES (?,?,?)",
            (label, sid, round(score, 4))
        )
    conn2.commit()
    conn2.close()

    # Build result
    result_clusters = {}
    for label, members in clusters.items():
        member_data = []
        for sid in members:
            s = next((x for x in sessions if x["id"] == sid), None)
            if s:
                member_data.append({
                    "session_id":   sid,
                    "session_name": s["name"],
                    "game_name":    s["game_name"],
                    "rtp":          s["rtp"],
                    "net_result":   s["net_result"],
                    "similarity":   round(
                        cosine_similarity(fps.get(sid,{}), fps.get(members[0],{})), 4
                    ) if sid != members[0] else 1.0,
                })
        result_clusters[label] = {
            "size":    len(member_data),
            "members": member_data,
        }

    return {
        "cluster_count":   len(clusters),
        "sessions_total":  len(sessions),
        "singleton_count": sum(1 for m in clusters.values() if len(m) == 1),
        "threshold":       similarity_threshold,
        "clusters":        result_clusters,
    }


def get_session_cluster(session_id: int) -> dict | None:
    """Return which cluster a session belongs to, and its cluster members."""
    conn = get_connection()
    row  = conn.execute(
        "SELECT cluster_label, similarity_score FROM session_clusters WHERE session_id=?",
        (session_id,)
    ).fetchone()
    if not row:
        conn.close()
        return None

    label   = row["cluster_label"]
    members = conn.execute("""
        SELECT sc.session_id, sc.similarity_score, s.name, s.game_name, s.rtp, s.net_result
        FROM session_clusters sc
        JOIN sessions s ON s.id = sc.session_id
        WHERE sc.cluster_label=? ORDER BY sc.similarity_score DESC
    """, (label,)).fetchall()
    conn.close()

    return {
        "session_id":    session_id,
        "cluster_label": label,
        "similarity":    row["similarity_score"],
        "cluster_size":  len(members),
        "members":       [dict(m) for m in members],
    }


# ── Peer benchmarking ─────────────────────────────────────────────────────────

def peer_benchmark(session_id: int) -> dict:
    """
    Compare a session against its cluster peers.
    Shows where it ranks on key metrics vs similar sessions.
    """
    cluster = get_session_cluster(session_id)
    if not cluster or cluster["cluster_size"] < 2:
        return {"status": "no_peers", "session_id": session_id}

    peers = [m for m in cluster["members"] if m["session_id"] != session_id]
    if not peers:
        return {"status": "no_peers", "session_id": session_id}

    conn  = get_connection()
    me    = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    conn.close()
    if not me:
        return {"status": "not_found"}

    def _safe(v): return float(v) if v is not None else 0.0
    def _rank(val, vals, higher_better=True):
        sorted_vals = sorted(vals, reverse=higher_better)
        try:    return sorted_vals.index(val) + 1
        except: return len(sorted_vals)

    peer_rtps = [_safe(p["rtp"]) for p in peers]
    peer_nets = [_safe(p["net_result"]) for p in peers]

    my_rtp = _safe(me["rtp"])
    my_net = _safe(me["net_result"])

    return {
        "session_id":     session_id,
        "cluster_label":  cluster["cluster_label"],
        "peer_count":     len(peers),
        "benchmarks": {
            "rtp": {
                "mine":     my_rtp,
                "peer_avg": round(sum(peer_rtps)/len(peer_rtps), 2),
                "peer_min": round(min(peer_rtps), 2),
                "peer_max": round(max(peer_rtps), 2),
                "rank":     _rank(my_rtp, peer_rtps + [my_rtp]),
                "rank_of":  len(peers) + 1,
                "percentile": round(
                    sum(1 for v in peer_rtps if v <= my_rtp) / len(peer_rtps) * 100, 1
                ),
            },
            "net_result": {
                "mine":     my_net,
                "peer_avg": round(sum(peer_nets)/len(peer_nets), 2),
                "peer_min": round(min(peer_nets), 2),
                "peer_max": round(max(peer_nets), 2),
                "rank":     _rank(my_net, peer_nets + [my_net]),
                "rank_of":  len(peers) + 1,
            },
        },
    }


# ── Dataset-wide risk summary ─────────────────────────────────────────────────

def get_dataset_summary() -> dict:
    """Aggregate risk summary across ALL sessions."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT rtp, net_result, losing_streak, spins, status FROM sessions"
    ).fetchall()
    conn.close()

    if not rows:
        return {"status": "no_data"}

    rtps    = [float(r["rtp"])          for r in rows if r["rtp"]]
    nets    = [float(r["net_result"])   for r in rows if r["net_result"] is not None]
    streaks = [float(r["losing_streak"]) for r in rows if r["losing_streak"]]
    spins   = [float(r["spins"])        for r in rows if r["spins"]]
    flagged = sum(1 for r in rows if r["status"] == "flagged")

    def _pct(vals, p):
        idx = int(len(vals) * p / 100)
        return round(sorted(vals)[max(0, min(idx, len(vals)-1))], 2)

    return {
        "status":          "ok",
        "total_sessions":  len(rows),
        "flagged_sessions": flagged,
        "rtp": {
            "mean":   round(sum(rtps)/len(rtps), 2) if rtps else 0,
            "median": _pct(rtps, 50),
            "p25":    _pct(rtps, 25),
            "p75":    _pct(rtps, 75),
            "min":    round(min(rtps), 2) if rtps else 0,
            "max":    round(max(rtps), 2) if rtps else 0,
            "below_85": sum(1 for v in rtps if v < 85),
            "below_96": sum(1 for v in rtps if v < 96),
        },
        "net_result": {
            "total":    round(sum(nets), 2) if nets else 0,
            "mean":     round(sum(nets)/len(nets), 2) if nets else 0,
            "best":     round(max(nets), 2) if nets else 0,
            "worst":    round(min(nets), 2) if nets else 0,
            "positive": sum(1 for v in nets if v > 0),
            "negative": sum(1 for v in nets if v < 0),
        },
        "losing_streak": {
            "mean":   round(sum(streaks)/len(streaks), 1) if streaks else 0,
            "worst":  int(max(streaks)) if streaks else 0,
            "over_15": sum(1 for v in streaks if v > 15),
        },
        "total_spins": int(sum(spins)),
    }


# ── Anomaly detection ─────────────────────────────────────────────────────────

def detect_anomalies(z_threshold: float = 2.0) -> list[dict]:
    """
    Flag sessions that deviate significantly from the overall distribution.
    Uses Z-score on RTP and net_result.
    """
    conn = get_connection()
    rows = [dict(r) for r in conn.execute(
        "SELECT id, name, game_name, rtp, net_result, losing_streak FROM sessions"
    ).fetchall()]
    conn.close()

    if len(rows) < 4:
        return []

    import math
    def _stats(vals):
        n    = len(vals)
        mean = sum(vals) / n
        std  = math.sqrt(sum((v-mean)**2 for v in vals) / n) or 1e-9
        return mean, std

    rtps = [float(r["rtp"] or 0) for r in rows]
    nets = [float(r["net_result"] or 0) for r in rows]
    rtp_mean, rtp_std = _stats(rtps)
    net_mean, net_std = _stats(nets)

    anomalies = []
    for i, s in enumerate(rows):
        rtp_z = abs(rtps[i] - rtp_mean) / rtp_std
        net_z = abs(nets[i] - net_mean) / net_std
        reasons = []
        if rtp_z > z_threshold: reasons.append(f"RTP z={rtp_z:.1f} ({rtps[i]:.0f}% vs avg {rtp_mean:.0f}%)")
        if net_z > z_threshold: reasons.append(f"Net z={net_z:.1f} (${nets[i]:.0f} vs avg ${net_mean:.0f})")
        if reasons:
            anomalies.append({
                "session_id":   s["id"],
                "session_name": s["name"],
                "game_name":    s["game_name"],
                "rtp":          s["rtp"],
                "net_result":   s["net_result"],
                "rtp_z":        round(rtp_z, 2),
                "net_z":        round(net_z, 2),
                "reasons":      reasons,
                "severity":     "critical" if max(rtp_z, net_z) > 3 else "warning",
            })

    anomalies.sort(key=lambda x: -max(x["rtp_z"], x["net_z"]))
    return anomalies
