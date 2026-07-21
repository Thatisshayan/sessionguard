/**
 * frontend/src/pages/ImportWizard.tsx - V14
 * Session Import Wizard: CSV, manual entry, video.
 * Fixed: VITE_API_URL env var (was VITE_API_BASE_URL)
 * Original: ChatGPT | Fixed: Claude
 */
import React, { ChangeEvent, FormEvent, useMemo, useState } from "react";
import axios from "axios";

type SourceType = "csv" | "manual" | "video";
type PreviewRow = Record<string, string | number | null>;
type SuggestedMapping = { date?: string; bet?: string; win?: string; balance?: string; spin_number?: string };
type ColumnMapping = { date: string; bet: string; win: string; balance: string; spin_number?: string };
type PreviewResponse = { upload_id: string; columns: string[]; preview_rows: PreviewRow[]; suggested_mapping: SuggestedMapping };
type ImportResult = { session_id?: string; id?: string; event_count?: number; imported?: number; warnings?: string[]; message?: string };
type ManualRow = { date: string; bet: string; win: string; balance: string; spin_number: string };

// FIX: use VITE_API_URL to match the rest of the codebase
const API_BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

const emptyRow: ManualRow = { date: "", bet: "", win: "", balance: "", spin_number: "" };
const sourceOptions = [
  { id: "csv" as SourceType, title: "CSV Upload", description: "Import a real exported session or transaction CSV." },
  { id: "manual" as SourceType, title: "Manual Entry", description: "Type session rows manually and import through the CSV pipeline." },
  { id: "video" as SourceType, title: "Video Upload", description: "Send gameplay footage to the upload pipeline for processing." },
];
const requiredFields: Array<keyof ColumnMapping> = ["date", "bet", "win", "balance"];

function displayValue(v: string | number | null | undefined): string { return v === null || v === undefined ? "" : String(v) }
function csvEscape(v: string): string { const n = String(v ?? ""); return /[",\n\r]/.test(n) ? `"${n.replace(/"/g, '""')}"` : n }
function parseNumber(v: unknown): number | null {
  const raw = String(v ?? "").trim(); if (!raw) return null;
  const neg = raw.startsWith("(") && raw.endsWith(")");
  const cleaned = raw.replace(/[,$£€\s()A-Za-z]/g, "");
  if (!cleaned || cleaned === "-" || cleaned === ".") return null;
  const n = Number(cleaned); if (!Number.isFinite(n)) return null;
  return neg ? -Math.abs(n) : n;
}
function isProbablyValidDate(v: unknown): boolean { return Number.isFinite(Date.parse(String(v ?? "").trim())) }
function buildManualCsvFile(rows: ManualRow[]): File {
  const header = "date,bet,win,balance,spin_number";
  const body = rows.filter(r => Object.values(r).some(v => String(v).trim()))
    .map(r => [r.date, r.bet, r.win, r.balance, r.spin_number].map(csvEscape).join(","));
  return new File([new Blob([[header, ...body].join("\n")], { type: "text/csv" })], "manual-session-import.csv", { type: "text/csv" });
}
function buildPreviewIssues(rows: PreviewRow[], mapping: ColumnMapping, source: SourceType, videoFile: File | null): string[] {
  if (source === "video") { if (!videoFile) return ["No video file selected."]; if (!videoFile.type.startsWith("video/")) return ["Not a video file."]; return []; }
  const issues: string[] = [];
  requiredFields.forEach(f => { if (!mapping[f]) issues.push(`Missing required mapping for "${f}".`) });
  if (issues.length) return issues;
  rows.forEach((row, i) => {
    const n = i + 1;
    if (!displayValue(row[mapping.date]).trim()) issues.push(`Row ${n}: missing date.`);
    else if (!isProbablyValidDate(row[mapping.date])) issues.push(`Row ${n}: date may need review.`);
    const bet = parseNumber(row[mapping.bet]); const win = parseNumber(row[mapping.win]); const bal = parseNumber(row[mapping.balance]);
    if (bet === null) issues.push(`Row ${n}: missing or invalid bet.`);
    else if (bet < 0) issues.push(`Row ${n}: negative bet.`);
    if (win === null) issues.push(`Row ${n}: missing or invalid win.`);
    if (bal === null) issues.push(`Row ${n}: missing or invalid balance.`);
  });
  return issues;
}
function getSessionLink(r: ImportResult | null): string {
  const id = r?.session_id || r?.id; return id ? `/sessions/${encodeURIComponent(id)}` : "";
}

export default function ImportWizard() {
  const [step, setStep]           = useState(1);
  const [source, setSource]       = useState<SourceType>("csv");
  const [csvFile, setCsvFile]     = useState<File | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [manualRows, setManualRows] = useState<ManualRow[]>([{...emptyRow},{...emptyRow},{...emptyRow}]);
  const [uploadId, setUploadId]   = useState("");
  const [columns, setColumns]     = useState<string[]>([]);
  const [previewRows, setPreviewRows] = useState<PreviewRow[]>([]);
  const [mapping, setMapping]     = useState<ColumnMapping>({ date:"", bet:"", win:"", balance:"", spin_number:"" });
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState("");
  const [result, setResult]       = useState<ImportResult | null>(null);

  const previewIssues = useMemo(() => buildPreviewIssues(previewRows, mapping, source, videoFile), [previewRows, mapping, source, videoFile]);
  const sessionLink   = useMemo(() => getSessionLink(result), [result]);

  async function requestPreview(file: File) {
    const fd = new FormData(); fd.append("file", file);
    const res = await axios.post<PreviewResponse>(`${API_BASE}/import/preview`, fd);
    const d = res.data; const s = d.suggested_mapping || {};
    setUploadId(d.upload_id); setColumns(d.columns || []); setPreviewRows(d.preview_rows || []);
    setMapping({ date: s.date||"", bet: s.bet||"", win: s.win||"", balance: s.balance||"", spin_number: s.spin_number||"" });
  }

  async function handlePrepare(e?: FormEvent) {
    e?.preventDefault(); setError(""); setResult(null); setLoading(true);
    try {
      if (source === "csv") { if (!csvFile) throw new Error("Choose a CSV file first."); await requestPreview(csvFile); setStep(2); return; }
      if (source === "manual") {
        if (!manualRows.some(r => Object.values(r).some(v => String(v).trim()))) throw new Error("Enter at least one row.");
        await requestPreview(buildManualCsvFile(manualRows)); setStep(2); return;
      }
      if (!videoFile) throw new Error("Choose a video file first.");
      setColumns([]); setPreviewRows([{ file_name: videoFile.name, size_mb: (videoFile.size/1024/1024).toFixed(2) }]); setStep(2);
    } catch(err) { setError(err instanceof Error ? err.message : "Failed to prepare."); }
    finally { setLoading(false); }
  }

  async function handleConfirm() {
    setError(""); setResult(null); setLoading(true);
    try {
      if (source === "video") {
        if (!videoFile) throw new Error("No video file.");
        const fd = new FormData(); fd.append("file", videoFile); fd.append("source", "video_upload");
        setResult((await axios.post<ImportResult>(`${API_BASE}/upload`, fd)).data); setStep(4); return;
      }
      if (!uploadId) throw new Error("Missing upload id. Go back and preview again.");
      requiredFields.forEach(f => { if (!mapping[f]) throw new Error(`Missing mapping for "${f}".`) });
      const res = await axios.post<ImportResult>(`${API_BASE}/import/confirm`, { upload_id: uploadId, column_mapping: mapping });
      setResult(res.data); setStep(4);
    } catch(err) {
      if (axios.isAxiosError(err)) { const d = err.response?.data?.detail; setError(typeof d === "string" ? d : "Import failed."); }
      else setError(err instanceof Error ? err.message : "Import failed.");
    } finally { setLoading(false); }
  }

  function updateRow(i: number, f: keyof ManualRow, v: string) { setManualRows(rows => rows.map((r,j) => j===i ? {...r,[f]:v} : r)) }
  function addRow() { setManualRows(r => [...r, {...emptyRow}]) }
  function removeRow(i: number) { setManualRows(r => { const n=r.filter((_,j)=>j!==i); return n.length>0?n:[{...emptyRow}] }) }
  function updateMapping(f: keyof ColumnMapping, v: string) { setMapping(m => ({...m,[f]:v})) }
  function reset() { setStep(1); setUploadId(""); setColumns([]); setPreviewRows([]); setMapping({date:"",bet:"",win:"",balance:"",spin_number:""}); setError(""); setResult(null); }

  const card = { background:"var(--bg-elevated)", border:"1px solid var(--bg-border)", borderRadius:"var(--radius-md)", padding:20, marginBottom:12 } as const;
  const btn  = { border:"1px solid var(--bg-border)", background:"var(--bg-surface)", color:"var(--text-primary)", borderRadius:"var(--radius-md)", padding:"10px 18px", cursor:"pointer", fontWeight:700 } as const;
  const btnP = { ...btn, border:"1px solid var(--accent-blue)", background:"var(--accent-blue)", color:"#fff" } as const;
  const sel  = { width:"100%", background:"var(--bg-surface)", color:"var(--text-primary)", border:"1px solid var(--bg-border)", borderRadius:"var(--radius-md)", padding:"10px 12px" } as const;
  const inp  = { ...sel } as const;

  return (
    <div style={{ padding:28, minHeight:"100%", background:"var(--bg-surface)", color:"var(--text-primary)" }}>
      <div style={{ maxWidth:1100, margin:"0 auto" }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:24 }}>
          <div>
            <div style={{ color:"var(--accent-blue)", fontWeight:800, fontSize:11, textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:6 }}>SessionGuard V14</div>
            <h1 style={{ margin:0, fontSize:28 }}>Session Import Wizard</h1>
            <p style={{ color:"var(--text-secondary)", marginTop:8 }}>Import real session data — CSV, manual entry, or video.</p>
          </div>
          <button style={btn} onClick={reset}>Reset</button>
        </div>

        {/* Step indicators */}
        <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:10, marginBottom:20 }}>
          {["Choose source","Map columns","Preview","Confirm"].map((t,i) => (
            <div key={t} style={{ ...card, marginBottom:0, borderColor: step===i+1 ? "var(--accent-blue)" : "var(--bg-border)", background: step===i+1 ? "rgba(59,130,246,0.1)" : "var(--bg-elevated)" }}>
              <div style={{ fontSize:11, color:"var(--text-muted)" }}>Step {i+1}</div>
              <div style={{ fontWeight:700, fontSize:13 }}>{t}</div>
            </div>
          ))}
        </div>

        {error && <div style={{ ...card, borderColor:"rgba(239,68,68,0.5)", background:"rgba(127,29,29,0.2)", color:"#fca5a5", marginBottom:16 }}>{error}</div>}

        <div style={card}>
          {/* STEP 1 */}
          {step===1 && (
            <form onSubmit={handlePrepare}>
              <h2 style={{ marginTop:0 }}>1. Choose import source</h2>
              <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:12, marginBottom:20 }}>
                {sourceOptions.map(o => (
                  <button key={o.id} type="button" onClick={() => setSource(o.id)}
                    style={{ textAlign:"left", padding:16, border:`1px solid ${source===o.id?"var(--accent-blue)":"var(--bg-border)"}`, background:source===o.id?"rgba(59,130,246,0.1)":"var(--bg-surface)", borderRadius:"var(--radius-md)", cursor:"pointer", color:"var(--text-primary)" }}>
                    <div style={{ fontWeight:800, marginBottom:6 }}>{o.title}</div>
                    <div style={{ color:"var(--text-secondary)", fontSize:13 }}>{o.description}</div>
                  </button>
                ))}
              </div>
              {source==="csv" && <div style={{ marginBottom:16 }}><label style={{ display:"block", fontSize:13, color:"var(--text-secondary)", marginBottom:6 }}>CSV file</label><input type="file" accept=".csv,text/csv" style={inp} onChange={(e:ChangeEvent<HTMLInputElement>) => setCsvFile(e.target.files?.[0]||null)} /></div>}
              {source==="video" && <div style={{ marginBottom:16 }}><label style={{ display:"block", fontSize:13, color:"var(--text-secondary)", marginBottom:6 }}>Video file</label><input type="file" accept="video/*" style={inp} onChange={(e:ChangeEvent<HTMLInputElement>) => setVideoFile(e.target.files?.[0]||null)} /></div>}
              {source==="manual" && (
                <div style={{ marginBottom:16 }}>
                  <label style={{ display:"block", fontSize:13, color:"var(--text-secondary)", marginBottom:8 }}>Manual rows</label>
                  <table style={{ width:"100%", borderCollapse:"collapse" }}>
                    <thead><tr>{["Date","Bet","Win","Balance","Spin #",""].map(h => <th key={h} style={{ padding:"8px 10px", borderBottom:"1px solid var(--bg-border)", fontSize:11, textAlign:"left", color:"var(--text-muted)", textTransform:"uppercase" }}>{h}</th>)}</tr></thead>
                    <tbody>{manualRows.map((row,i) => (
                      <tr key={i}>
                        {(["date","bet","win","balance","spin_number"] as const).map(f => (
                          <td key={f} style={{ padding:4 }}><input value={row[f]} onChange={e => updateRow(i,f,e.target.value)} style={{...inp, padding:"8px 10px"}} placeholder={f==="date"?"2026-05-03":f==="balance"?"250.00":"1.00"} /></td>
                        ))}
                        <td style={{ padding:4 }}><button type="button" onClick={() => removeRow(i)} style={{ ...btn, color:"#fca5a5", padding:"8px 12px" }}>✕</button></td>
                      </tr>
                    ))}</tbody>
                  </table>
                  <button type="button" onClick={addRow} style={{ ...btn, marginTop:8 }}>+ Add row</button>
                </div>
              )}
              <div style={{ display:"flex", justifyContent:"flex-end", marginTop:16 }}>
                <button type="submit" style={btnP} disabled={loading}>{loading?"Preparing...":"Continue →"}</button>
              </div>
            </form>
          )}

          {/* STEP 2 */}
          {step===2 && (
            <div>
              <h2 style={{ marginTop:0 }}>2. Map columns</h2>
              {source==="video" ? <div style={{ color:"var(--text-secondary)" }}>Video files skip column mapping. Confirm to upload.</div> : (
                <div style={{ display:"grid", gridTemplateColumns:"repeat(2,1fr)", gap:14 }}>
                  {requiredFields.map(f => (
                    <div key={f}><label style={{ display:"block", fontSize:13, color:"var(--text-secondary)", marginBottom:6 }}>{f} *</label>
                    <select style={sel} value={mapping[f]} onChange={e => updateMapping(f, e.target.value)}>
                      <option value="">Select column</option>
                      {columns.map(c => <option key={c} value={c}>{c}</option>)}
                    </select></div>
                  ))}
                  <div><label style={{ display:"block", fontSize:13, color:"var(--text-secondary)", marginBottom:6 }}>spin_number (optional)</label>
                  <select style={sel} value={mapping.spin_number||""} onChange={e => updateMapping("spin_number", e.target.value)}>
                    <option value="">None</option>
                    {columns.map(c => <option key={c} value={c}>{c}</option>)}
                  </select></div>
                </div>
              )}
              <div style={{ display:"flex", justifyContent:"space-between", marginTop:20 }}>
                <button style={btn} onClick={() => setStep(1)}>← Back</button>
                <button style={btnP} onClick={() => setStep(3)}>Preview rows →</button>
              </div>
            </div>
          )}

          {/* STEP 3 */}
          {step===3 && (
            <div>
              <h2 style={{ marginTop:0 }}>3. Preview first 10 rows</h2>
              {previewIssues.length > 0
                ? <div style={{ padding:12, marginBottom:16, borderRadius:"var(--radius-sm)", border:"1px solid rgba(239,68,68,0.4)", background:"rgba(127,29,29,0.15)", color:"#fca5a5" }}><strong>Issues:</strong><ul style={{ margin:"6px 0 0", paddingLeft:20 }}>{previewIssues.map(i=><li key={i}>{i}</li>)}</ul></div>
                : <div style={{ padding:12, marginBottom:16, borderRadius:"var(--radius-sm)", border:"1px solid rgba(34,197,94,0.4)", background:"rgba(20,83,45,0.15)", color:"#86efac" }}>✅ No blocking issues in preview rows.</div>
              }
              <div style={{ overflowX:"auto" }}>
                <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
                  <thead><tr>{(source==="video" ? Object.keys(previewRows[0]||{}) : columns).map(c => <th key={c} style={{ padding:"8px 10px", borderBottom:"1px solid var(--bg-border)", textAlign:"left", fontSize:11, color:"var(--text-muted)", textTransform:"uppercase" }}>{c}</th>)}</tr></thead>
                  <tbody>{previewRows.slice(0,10).map((row,i) => <tr key={i}>{(source==="video" ? Object.keys(previewRows[0]||{}) : columns).map(c => <td key={c} style={{ padding:"8px 10px", borderBottom:"1px solid var(--bg-border)", color:"var(--text-secondary)" }}>{displayValue(row[c])}</td>)}</tr>)}</tbody>
                </table>
              </div>
              <div style={{ display:"flex", justifyContent:"space-between", marginTop:20 }}>
                <button style={btn} onClick={() => setStep(2)}>← Back</button>
                <button style={btnP} disabled={loading || previewIssues.some(i=>i.includes("Missing required"))} onClick={handleConfirm}>{loading?"Importing...":"Confirm import →"}</button>
              </div>
            </div>
          )}

          {/* STEP 4 */}
          {step===4 && (
            <div>
              <h2 style={{ marginTop:0 }}>4. Import complete</h2>
              <div style={{ padding:16, borderRadius:"var(--radius-sm)", border:"1px solid rgba(34,197,94,0.4)", background:"rgba(20,83,45,0.15)", color:"#86efac", marginBottom:16 }}>
                ✅ {source==="video" ? "Video sent to upload pipeline." : `Imported ${result?.event_count ?? result?.imported ?? 0} events successfully.`}
              </div>
              {result?.warnings?.length ? <div style={{ padding:12, borderRadius:"var(--radius-sm)", border:"1px solid var(--bg-border)", color:"var(--text-secondary)", marginBottom:16 }}><strong>Warnings:</strong><ul style={{ margin:"6px 0 0", paddingLeft:20 }}>{result.warnings.map(w=><li key={w}>{w}</li>)}</ul></div> : null}
              {sessionLink && <div style={{ padding:12, borderRadius:"var(--radius-sm)", border:"1px solid var(--bg-border)", marginBottom:16 }}>Session: <a href={sessionLink} style={{ color:"var(--accent-blue)" }}>{sessionLink}</a></div>}
              <div style={{ display:"flex", gap:12 }}>
                <button style={btn} onClick={reset}>Import another</button>
                {sessionLink && <a href={sessionLink} style={{ ...btnP, textDecoration:"none", display:"inline-block" }}>Open session →</a>}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
