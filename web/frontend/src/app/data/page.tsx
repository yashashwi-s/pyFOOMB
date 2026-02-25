"use client";

import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";

interface ModelInfo { id: string; name: string; }
interface MeasSeries { name: string; timepoints: number[]; values: number[]; errors: number[] | null; }

type Tab = "paste" | "upload" | "sheets";

const SAMPLE_DATA = `Time (h),Biomass (X) [g/L],Substrate (S) [g/L],Product (P) [g/L],Volume (V) [L]
0,0.5,10.0,0.0,2.0
4,2.8,1.2,0.1,2.0
6,8.5,0.2,0.5,2.1
10,25.0,0.15,2.4,2.4
15,55.0,0.1,6.8,2.8
20,85.0,0.1,12.5,3.2`;

export default function DataPage() {
    const { toast } = useToast();
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [modelId, setModelId] = useState("");
    const [measurements, setMeasurements] = useState<MeasSeries[]>([]);
    const [tab, setTab] = useState<Tab>("paste");
    const [busy, setBusy] = useState(false);

    // Paste
    const [pasteText, setPasteText] = useState("");

    // Upload
    const fileRef = useRef<HTMLInputElement>(null);
    const [dragOver, setDragOver] = useState(false);

    // Google Sheets
    const [sheetsUrl, setSheetsUrl] = useState("");

    useEffect(() => {
        api.getModels().then((r) => setModels(r.models)).catch(console.error);
    }, []);

    async function loadMeasurements(id: string) {
        setModelId(id);
        try {
            const r = await api.getMeasurements(id);
            setMeasurements(r.measurements);
        } catch { setMeasurements([]); }
    }

    async function clearAll() {
        if (!modelId) return;
        await api.clearMeasurements(modelId);
        setMeasurements([]);
        toast("All measurements cleared");
    }

    // ── Paste handler ──
    async function submitPaste() {
        if (!modelId || !pasteText.trim()) return;
        setBusy(true);
        try {
            const r = await api.pasteMeasurements(modelId, pasteText);
            toast(`Parsed ${r.names.length} series: ${r.names.join(", ")}`);
            setPasteText("");
            loadMeasurements(modelId);
        } catch (e: unknown) {
            toast(e instanceof Error ? e.message : "Parse failed", "error");
        }
        setBusy(false);
    }

    // ── File upload handler ──
    async function handleFile(file: File) {
        if (!modelId) return;
        setBusy(true);
        try {
            const r = await api.uploadMeasurementFile(modelId, file);
            toast(`Uploaded ${r.names.length} series: ${r.names.join(", ")}`);
            loadMeasurements(modelId);
        } catch (e: unknown) {
            toast(e instanceof Error ? e.message : "Upload failed", "error");
        }
        setBusy(false);
    }

    function onFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0];
        if (file) handleFile(file);
    }

    function onDrop(e: React.DragEvent) {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
    }

    // ── Google Sheets handler ──
    async function submitSheets() {
        if (!modelId || !sheetsUrl.trim()) return;
        setBusy(true);
        try {
            const r = await api.importGoogleSheets(modelId, sheetsUrl);
            toast(`Imported ${r.names.length} series from Google Sheets`);
            setSheetsUrl("");
            loadMeasurements(modelId);
        } catch (e: unknown) {
            toast(e instanceof Error ? e.message : "Import failed", "error");
        }
        setBusy(false);
    }

    const tabs: { key: Tab; label: string }[] = [
        { key: "paste", label: "Paste Data" },
        { key: "upload", label: "Upload File" },
        { key: "sheets", label: "Google Sheets" },
    ];

    return (
        <div>
            <div style={{ marginBottom: 20 }}>
                <h1 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>Measurement Data</h1>
                <p style={{ fontSize: 12, color: "#a1a1aa" }}>Import experimental measurements for model calibration.</p>
            </div>

            <div className="hint-bar" style={{ lineHeight: 1.7 }}>
                Paste, upload, or import data in <strong style={{ color: "#d4d4d8" }}>wide format</strong> — one column per state.
                Column names are parsed automatically:
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#71717a" }}> &quot;Biomass (X) [g/L]&quot; → X</span>.
                Values with annotations like <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#71717a" }}>&quot;2.1 (Feed starts)&quot;</span> are handled.
            </div>

            {/* Model selector */}
            <div className="card" style={{ marginBottom: 16, display: "flex", gap: 12, alignItems: "flex-end" }}>
                <div>
                    <label style={{ fontSize: 10, color: "#71717a", display: "block", marginBottom: 3 }}>Model</label>
                    <select value={modelId} onChange={(e) => loadMeasurements(e.target.value)} style={{ width: 220 }}>
                        <option value="">Select model...</option>
                        {models.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.id.slice(0, 6)})</option>)}
                    </select>
                </div>
                {modelId && measurements.length > 0 && (
                    <button className="btn-secondary" style={{ fontSize: 10, padding: "4px 10px", color: "#a1a1aa" }} onClick={clearAll}>Clear All</button>
                )}
            </div>

            {/* Import tabs */}
            {modelId && (
                <div className="card" style={{ marginBottom: 16 }}>
                    {/* Tab bar */}
                    <div style={{ display: "flex", gap: 0, borderBottom: "1px solid #27272a", marginBottom: 14 }}>
                        {tabs.map((t) => (
                            <button
                                key={t.key}
                                onClick={() => setTab(t.key)}
                                style={{
                                    padding: "8px 16px", fontSize: 11, fontWeight: 500,
                                    color: tab === t.key ? "#fafafa" : "#52525b",
                                    background: "transparent", border: "none", borderRadius: 0,
                                    borderBottom: tab === t.key ? "2px solid #3b82f6" : "2px solid transparent",
                                    cursor: "pointer", transition: "all 0.15s",
                                }}
                            >
                                {t.label}
                            </button>
                        ))}
                    </div>

                    {/* ── Paste tab ── */}
                    {tab === "paste" && (
                        <div>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                                <span style={{ fontSize: 11, color: "#71717a" }}>
                                    Paste CSV or tab-separated data with a header row
                                </span>
                                <button
                                    className="btn-secondary"
                                    style={{ fontSize: 10, padding: "3px 8px" }}
                                    onClick={() => { setPasteText(SAMPLE_DATA); toast("Sample data loaded"); }}
                                >
                                    Insert sample
                                </button>
                            </div>
                            <textarea
                                value={pasteText}
                                onChange={(e) => setPasteText(e.target.value)}
                                placeholder={`Time (h),Biomass (X) [g/L],Substrate (S) [g/L],Product (P) [g/L]\n0,0.5,10.0,0.0\n4,2.8,1.2,0.1\n...`}
                                style={{
                                    width: "100%", minHeight: 180, padding: "10px 12px",
                                    background: "#09090b", border: "1px solid #27272a", borderRadius: 6,
                                    color: "#d4d4d8", fontFamily: "var(--font-mono)", fontSize: 11,
                                    lineHeight: 1.6, resize: "vertical", outline: "none",
                                }}
                            />
                            {/* Preview */}
                            {pasteText.trim() && (
                                <div style={{ marginTop: 8 }}>
                                    <PastePreview text={pasteText} />
                                </div>
                            )}
                            <div style={{ marginTop: 10, display: "flex", justifyContent: "flex-end" }}>
                                <button className="btn-primary" onClick={submitPaste} disabled={busy || !pasteText.trim()}>
                                    {busy ? <span className="spinner" style={{ width: 12, height: 12, borderWidth: 1.5 }} /> : "Import Data"}
                                </button>
                            </div>
                        </div>
                    )}

                    {/* ── Upload tab ── */}
                    {tab === "upload" && (
                        <div>
                            <div
                                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                                onDragLeave={() => setDragOver(false)}
                                onDrop={onDrop}
                                onClick={() => fileRef.current?.click()}
                                style={{
                                    border: `2px dashed ${dragOver ? "#3b82f6" : "#27272a"}`,
                                    borderRadius: 8, padding: "40px 20px", textAlign: "center",
                                    cursor: "pointer", transition: "border-color 0.15s",
                                    background: dragOver ? "#0c1929" : "transparent",
                                }}
                            >
                                <div style={{ fontSize: 12, color: "#71717a", marginBottom: 4 }}>
                                    Drop a <strong>.csv</strong> or <strong>.xlsx</strong> file here
                                </div>
                                <div style={{ fontSize: 10, color: "#3f3f46" }}>
                                    or click to browse
                                </div>
                                <input
                                    ref={fileRef}
                                    type="file"
                                    accept=".csv,.xlsx,.xls"
                                    onChange={onFileSelect}
                                    style={{ display: "none" }}
                                />
                            </div>
                            <div style={{ marginTop: 10, fontSize: 10, color: "#3f3f46" }}>
                                Expected format — wide table with a &quot;Time&quot; column and one column per state.
                                Column names like <span style={{ fontFamily: "var(--font-mono)" }}>&quot;Biomass (X) [g/L]&quot;</span> are auto-parsed to state name <span style={{ fontFamily: "var(--font-mono)" }}>X</span>.
                            </div>
                        </div>
                    )}

                    {/* ── Google Sheets tab ── */}
                    {tab === "sheets" && (
                        <div>
                            <div style={{ fontSize: 11, color: "#71717a", marginBottom: 8, lineHeight: 1.6 }}>
                                Paste a <strong style={{ color: "#d4d4d8" }}>public</strong> Google Sheets link.
                                The sheet must be shared as &quot;Anyone with the link can view&quot;.
                            </div>
                            <div style={{ display: "flex", gap: 8 }}>
                                <input
                                    type="text"
                                    value={sheetsUrl}
                                    onChange={(e) => setSheetsUrl(e.target.value)}
                                    placeholder="https://docs.google.com/spreadsheets/d/..."
                                    style={{ flex: 1, fontFamily: "var(--font-mono)", fontSize: 11 }}
                                />
                                <button className="btn-primary" onClick={submitSheets} disabled={busy || !sheetsUrl.trim()}>
                                    {busy ? <span className="spinner" style={{ width: 12, height: 12, borderWidth: 1.5 }} /> : "Import"}
                                </button>
                            </div>
                            <div style={{ marginTop: 10, fontSize: 10, color: "#3f3f46" }}>
                                Uses the same wide-format column parsing. First row should be headers.
                                Supports specific sheet tabs via the <span style={{ fontFamily: "var(--font-mono)" }}>gid=</span> parameter in the URL.
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ── Stored measurements ── */}
            {measurements.length > 0 && (
                <div className="card">
                    <div style={{ fontSize: 11, fontWeight: 500, color: "#a1a1aa", marginBottom: 10 }}>
                        Stored Measurements ({measurements.length} series)
                    </div>

                    {/* Summary table */}
                    <table style={{ marginBottom: 16 }}>
                        <thead>
                            <tr>
                                <th>State</th>
                                <th>Points</th>
                                <th>Time Range</th>
                                <th>Value Range</th>
                                <th>Errors</th>
                            </tr>
                        </thead>
                        <tbody>
                            {measurements.map((m, i) => {
                                const vMin = m.values.length > 0 ? Math.min(...m.values) : 0;
                                const vMax = m.values.length > 0 ? Math.max(...m.values) : 0;
                                return (
                                    <tr key={i}>
                                        <td style={{ fontWeight: 500 }}>{m.name}</td>
                                        <td>{m.timepoints.length}</td>
                                        <td>{m.timepoints[0]?.toFixed(1)} – {m.timepoints[m.timepoints.length - 1]?.toFixed(1)} h</td>
                                        <td>{vMin.toFixed(3)} – {vMax.toFixed(3)}</td>
                                        <td>
                                            <span className={`dot ${m.errors ? "dot-green" : "dot-gray"}`} />
                                            {m.errors ? "Yes" : "No"}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>

                    {/* Wide-format data view */}
                    <div style={{ fontSize: 10, color: "#52525b", marginBottom: 6, fontWeight: 500 }}>Raw Data</div>
                    <div style={{ maxHeight: 300, overflowY: "auto", overflowX: "auto" }}>
                        <WideDataTable measurements={measurements} />
                    </div>
                </div>
            )}
        </div>
    );
}


/** Preview parsed columns from paste text */
function PastePreview({ text }: { text: string }) {
    const lines = text.trim().split("\n").filter(Boolean);
    if (lines.length < 2) return null;

    const sep = lines[0].includes("\t") ? "\t" : ",";
    const headers = lines[0].split(sep).map((h) => h.trim());
    const rows = lines.slice(1, 4).map((l) => l.split(sep).map((c) => c.trim()));

    return (
        <div style={{ fontSize: 10, color: "#52525b" }}>
            <div style={{ marginBottom: 4 }}>
                Preview: {headers.length} columns, {lines.length - 1} rows
            </div>
            <div style={{ overflowX: "auto" }}>
                <table>
                    <thead>
                        <tr>
                            {headers.map((h, i) => (
                                <th key={i} style={{ fontSize: 9, whiteSpace: "nowrap" }}>{h}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((row, i) => (
                            <tr key={i}>
                                {row.map((cell, j) => (
                                    <td key={j} style={{ fontSize: 9, whiteSpace: "nowrap" }}>{cell}</td>
                                ))}
                            </tr>
                        ))}
                        {lines.length > 4 && (
                            <tr><td colSpan={headers.length} style={{ color: "#3f3f46", fontSize: 9 }}>… {lines.length - 4} more rows</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}


/** Display stored measurements in a wide-format table (time rows × state columns) */
function WideDataTable({ measurements }: { measurements: MeasSeries[] }) {
    // Collect all unique timepoints across all series
    const allTimes = new Set<number>();
    measurements.forEach((m) => m.timepoints.forEach((t) => allTimes.add(t)));
    const sortedTimes = [...allTimes].sort((a, b) => a - b);

    // Build lookup: state → time → value
    const lookup: Record<string, Record<number, number>> = {};
    measurements.forEach((m) => {
        lookup[m.name] = {};
        m.timepoints.forEach((t, i) => {
            lookup[m.name][t] = m.values[i];
        });
    });

    const stateNames = measurements.map((m) => m.name);

    return (
        <table>
            <thead>
                <tr>
                    <th style={{ fontSize: 9 }}>Time (h)</th>
                    {stateNames.map((s) => (
                        <th key={s} style={{ fontSize: 9 }}>{s}</th>
                    ))}
                </tr>
            </thead>
            <tbody>
                {sortedTimes.map((t) => (
                    <tr key={t}>
                        <td style={{ fontSize: 10 }}>{t.toFixed(2)}</td>
                        {stateNames.map((s) => (
                            <td key={s} style={{ fontSize: 10, color: lookup[s][t] !== undefined ? "#d4d4d8" : "#27272a" }}>
                                {lookup[s][t] !== undefined ? lookup[s][t].toFixed(4) : "—"}
                            </td>
                        ))}
                    </tr>
                ))}
            </tbody>
        </table>
    );
}
