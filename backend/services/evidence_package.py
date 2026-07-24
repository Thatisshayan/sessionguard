"""
backend/services/evidence_package.py
--------------------------------------
Generates a complete evidence package as a ZIP archive containing:
  - PDF report (styled, with charts)
  - CSV events export
  - OCR results JSON
  - Frame thumbnails (up to 20 sampled)
  - Session metadata JSON
  - README.txt explaining the package contents

Maturity: Working Prototype
Future:   Add cryptographic hash manifest for legal integrity (V9).
          Add video clip extraction at scene-change timestamps (V10).
"""

from __future__ import annotations
import csv
import hashlib
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from database.db import get_connection
from engines.analysis_engine import get_session_metrics
from engines.insights_engine import get_insights
from engines.alerts_engine import get_alerts
from engines.review_queue_engine import get_review_queue

BASE_DIR    = Path(__file__).resolve().parent.parent.parent
EXPORTS_DIR = BASE_DIR / "storage" / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _generate_manifest(zip_path: str) -> dict:
    """
    Generate a SHA-256 hash manifest for all files in the evidence ZIP.
    Returns a dict {filename: sha256_hex}.
    """
    manifest = {}
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for name in zf.namelist():
            if name.endswith('/'):
                continue
            data = zf.read(name)
            sha = hashlib.sha256(data).hexdigest()
            manifest[name] = sha
    return manifest


def _get_ai_narrative(session_id: int) -> str | None:
    """Get AI narrative for a session if available."""
    try:
        from engines.ai_insights_engine import analyse_session_with_ai
        result = analyse_session_with_ai(session_id)
        if result and result.get("source") in ("nvidia_ai", "ollama_ai"):
            return json.dumps({
                "headline": result.get("headline", ""),
                "risk_level": result.get("risk_level", ""),
                "behaviour_summary": result.get("behaviour_summary", ""),
                "one_line_verdict": result.get("one_line_verdict", ""),
                "discipline_score": result.get("discipline_score", ""),
                "source": result.get("source", ""),
                "model": result.get("model", ""),
                "generated_at": result.get("generated_at", ""),
            }, indent=2)
    except Exception:
        pass
    return None


def verify_evidence_manifest(zip_path: str) -> dict:
    """
    Verify each file in the ZIP against the embedded manifest.json.
    Returns dict of {filename: "ok" | "tampered" | "missing"}.
    """
    status = {}
    with zipfile.ZipFile(zip_path, 'r') as zf:
        if "manifest.json" not in zf.namelist():
            return {"error": "No manifest.json in archive"}
        manifest = json.loads(zf.read("manifest.json"))
        for filename, expected_hash in manifest.items():
            if filename == "manifest.json":
                continue
            try:
                data = zf.read(filename)
                actual = hashlib.sha256(data).hexdigest()
                status[filename] = "ok" if actual == expected_hash else "tampered"
            except Exception:
                status[filename] = "not_found"
    return status


def build_evidence_package(session_id: int) -> dict:
    """
    Build a complete evidence package ZIP for a session.

    Returns:
        {"success": bool, "file_path": str, "filename": str,
         "contents": [...], "error": str|None}
    """
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"evidence_session_{session_id}_{ts}.zip"
    filepath = EXPORTS_DIR / filename

    contents = []
    errors   = []

    # ── Gather data ───────────────────────────────────────────────────────────
    metrics  = get_session_metrics(session_id)
    if not metrics:
        return {"success": False, "file_path": "", "filename": "",
                "contents": [], "error": f"Session {session_id} not found."}

    insights = get_insights(session_id=session_id)
    alerts_  = get_alerts(session_id=session_id)
    queue    = get_review_queue(session_id=session_id)

    conn     = get_connection()
    events   = [dict(r) for r in conn.execute(
        "SELECT * FROM events WHERE session_id=? ORDER BY timestamp", (session_id,)
    ).fetchall()]
    ocr_rows = [dict(r) for r in conn.execute(
        "SELECT * FROM ocr_results WHERE session_id=? ORDER BY id", (session_id,)
    ).fetchall()]
    uploads_ = [dict(r) for r in conn.execute(
        "SELECT * FROM uploads WHERE session_id=? ORDER BY created_at", (session_id,)
    ).fetchall()]
    conn.close()

    # ── Build ZIP ─────────────────────────────────────────────────────────────
    with zipfile.ZipFile(str(filepath), "w", zipfile.ZIP_DEFLATED) as zf:

        # 1. Session metadata JSON
        meta = {
            "exported_at":  datetime.now().isoformat(),
            "session_id":   session_id,
            "session_name": metrics["name"],
            "game_name":    metrics["game_name"],
            "platform":     metrics["platform"],
            "date":         metrics["date"],
            "metrics":      metrics,
        }
        zf.writestr("metadata/session.json", json.dumps(meta, indent=2))
        contents.append("metadata/session.json")

        # 2. Events CSV
        if events:
            _write_csv_to_zip(zf, "data/events.csv", events)
            contents.append(f"data/events.csv ({len(events)} rows)")

        # 3. Insights JSON
        if insights:
            zf.writestr("data/insights.json", json.dumps(insights, indent=2))
            contents.append(f"data/insights.json ({len(insights)} items)")

        # 4. Alerts JSON
        if alerts_:
            zf.writestr("data/alerts.json", json.dumps(alerts_, indent=2))
            contents.append(f"data/alerts.json ({len(alerts_)} items)")

        # 5. Review queue JSON
        if queue:
            zf.writestr("data/review_queue.json", json.dumps(queue, indent=2))
            contents.append(f"data/review_queue.json ({len(queue)} items)")

        # 6. OCR results JSON
        if ocr_rows:
            zf.writestr("ocr/ocr_results.json", json.dumps(ocr_rows, indent=2))
            contents.append(f"ocr/ocr_results.json ({len(ocr_rows)} frames)")

        # 7. Frame thumbnails (up to 20 sampled)
        frame_count = 0
        for ocr_row in ocr_rows[:20]:
            frame_path = Path(ocr_row.get("frame_path", ""))
            if frame_path.exists():
                try:
                    zf.write(str(frame_path), f"frames/{frame_path.name}")
                    frame_count += 1
                except Exception as e:
                    errors.append(f"Frame thumbnail {frame_path.name}: {e}")
            elif frame_path.name:
                errors.append(f"Frame thumbnail missing: {frame_path.name}")
        if frame_count:
            contents.append(f"frames/ ({frame_count} thumbnails)")

        # 8. PDF report
        try:
            from backend.services.export_service import generate_pdf
            pdf_result = generate_pdf(session_id=session_id)
            if pdf_result["success"]:
                pdf_path = Path(pdf_result["file_path"])
                if pdf_path.exists():
                    zf.write(str(pdf_path), f"reports/{pdf_path.name}")
                    contents.append(f"reports/{pdf_path.name}")
        except Exception as e:
            errors.append(f"PDF: {e}")

        # 9. Upload file list
        if uploads_:
            upload_list = [{"filename": u["filename"], "type": u["file_type"],
                            "status": u["status"], "created": u["created_at"]}
                           for u in uploads_]
            zf.writestr("metadata/uploads.json", json.dumps(upload_list, indent=2))
            contents.append("metadata/uploads.json")

        # 10. README
        readme = _build_readme(metrics, contents, errors)
        zf.writestr("README.txt", readme)
        contents.insert(0, "README.txt")

    # ── Append manifest and AI narrative ───────────────────────────────────────
    manifest = _generate_manifest(str(filepath))
    manifest_json = json.dumps(manifest, indent=2)
    with zipfile.ZipFile(str(filepath), 'a') as zf:
        zf.writestr("manifest.json", manifest_json)
        contents.insert(0, "manifest.json")

    ai_narrative = _get_ai_narrative(session_id)
    if ai_narrative:
        with zipfile.ZipFile(str(filepath), 'a') as zf:
            zf.writestr("ai_narrative.json", ai_narrative)
        contents.insert(0, "ai_narrative.json")

    # Register in exports table
    conn2 = get_connection()
    cur   = conn2.execute(
        "INSERT INTO exports (session_id, format, file_path) VALUES (?, 'evidence', ?)",
        (session_id, str(filepath))
    )
    export_id = cur.lastrowid
    conn2.commit()
    conn2.close()

    return {
        "success":   True,
        "export_id": export_id,
        "file_path": str(filepath),
        "filename":  filename,
        "contents":  contents,
        "errors":    errors,
        "error":     None if not errors else "Evidence package completed with partial issues.",
    }


def _write_csv_to_zip(zf: zipfile.ZipFile, arcname: str, rows: list[dict]):
    """Write a list of dicts as CSV inside a ZIP."""
    if not rows:
        return
    import io
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    zf.writestr(arcname, buf.getvalue())


def _build_readme(metrics: dict, contents: list, errors: list) -> str:
    return f"""SessionGuard Evidence Package
==============================

Session:   {metrics['name']}
Game:      {metrics['game_name']}
Platform:  {metrics['platform']}
Date:      {metrics['date']}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Key Metrics
-----------
Net Result:     ${metrics['net_result']:.2f}
RTP:            {metrics['rtp']}%
Total Spins:    {metrics['spins']}
Total Wagered:  ${metrics['total_bets']:.2f}
Biggest Win:    ${metrics['biggest_win']:.2f}
Losing Streak:  {metrics['losing_streak']} spins
Max Drawdown:   ${metrics.get('max_drawdown', 0):.2f}

Package Contents
----------------
{chr(10).join(f'  - {c}' for c in contents)}

{'Warnings' + chr(10) + chr(10).join(f'  - {e}' for e in errors) if errors else ''}

Notes
-----
This package was generated by SessionGuard, a session intelligence
and review platform. All OCR data carries confidence scores. Low-
confidence readings are flagged for human review. This package is
intended for personal review and record-keeping purposes.

SessionGuard v0.6.0 — local-first session intelligence
"""
