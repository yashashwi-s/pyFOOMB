"use client";

import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { ClipboardPaste, UploadCloud, Link2, Trash2, Database } from "lucide-react";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonTable } from "@/components/ui/Skeleton";

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
    const [measLoading, setMeasLoading] = useState(false);
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
        if (!id) { setMeasurements([]); return; }
        setMeasLoading(true);
        try {
            const r = await api.getMeasurements(id);
            setMeasurements(r.measurements);
        } catch { setMeasurements([]); }
        setMeasLoading(false);
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
            toast(`Parsed ${r.names.length} series: ${r.names.join(", ")}`, "success");
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
            toast(`Uploaded ${r.names.length} series: ${r.names.join(", ")}`, "success");
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
            toast(`Imported ${r.names.length} series from Google Sheets`, "success");
            setSheetsUrl("");
            loadMeasurements(modelId);
        } catch (e: unknown) {
            toast(e instanceof Error ? e.message : "Import failed", "error");
        }
        setBusy(false);
    }

    const tabs: { key: Tab; label: string; icon: typeof ClipboardPaste }[] = [
        { key: "paste", label: "Paste Data", icon: ClipboardPaste },
        { key: "upload", label: "Upload File", icon: UploadCloud },
        { key: "sheets", label: "Google Sheets", icon: Link2 },
    ];

    return (
        <div>
            <PageHeader title="Measurement Data" description="Import experimental measurements for model calibration." />

            <div className="hint-bar leading-[1.7]">
                Paste, upload, or import data in <strong>wide format</strong> — one column per state.
                Column names are parsed automatically:
                <span className="font-mono text-[10px] text-muted-2"> &quot;Biomass (X) [g/L]&quot; → X</span>.
                Values with annotations like <span className="font-mono text-[10px] text-muted-2">&quot;2.1 (Feed starts)&quot;</span> are handled.
            </div>

            {/* Model selector */}
            <div className="card mb-4 flex flex-wrap items-end gap-3">
                <div>
                    <label className="mb-1 block text-[10px] text-muted-2">Model</label>
                    <select value={modelId} onChange={(e) => loadMeasurements(e.target.value)} className="w-[220px]">
                        <option value="">Select model...</option>
                        {models.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.id.slice(0, 6)})</option>)}
                    </select>
                </div>
                {modelId && measurements.length > 0 && (
                    <button className="btn-secondary py-1 text-[10px] text-muted" onClick={clearAll}>
                        <Trash2 size={11} /> Clear All
                    </button>
                )}
            </div>

            {!modelId && (
                <div className="card">
                    <EmptyState icon={Database} title="No model selected" description="Select a model above to import or view its measurement data." />
                </div>
            )}

            {/* Import tabs */}
            {modelId && (
                <div className="card mb-4">
                    {/* Tab bar */}
                    <div className="mb-3.5 flex gap-0 border-b border-border">
                        {tabs.map((t) => (
                            <button
                                key={t.key}
                                onClick={() => setTab(t.key)}
                                className={`rounded-none border-b-2 bg-transparent px-4 py-2 text-[11px] font-medium ${tab === t.key ? "border-accent text-foreground" : "border-transparent text-subtle"
                                    }`}
                            >
                                <t.icon size={12} className="inline -mt-0.5 mr-1.5" />
                                {t.label}
                            </button>
                        ))}
                    </div>

                    {/* ── Paste tab ── */}
                    {tab === "paste" && (
                        <div>
                            <div className="mb-2 flex items-center justify-between">
                                <span className="text-[11px] text-muted-2">
                                    Paste CSV or tab-separated data with a header row
                                </span>
                                <button
                                    className="btn-secondary py-1 text-[10px]"
                                    onClick={() => { setPasteText(SAMPLE_DATA); toast("Sample data loaded"); }}
                                >
                                    Insert sample
                                </button>
                            </div>
                            <textarea
                                value={pasteText}
                                onChange={(e) => setPasteText(e.target.value)}
                                placeholder={`Time (h),Biomass (X) [g/L],Substrate (S) [g/L],Product (P) [g/L]\n0,0.5,10.0,0.0\n4,2.8,1.2,0.1\n...`}
                                className="min-h-[180px] w-full resize-y p-2.5 text-[11px] leading-[1.6]"
                            />
                            {/* Preview */}
                            {pasteText.trim() && (
                                <div className="mt-2">
                                    <PastePreview text={pasteText} />
                                </div>
                            )}
                            <div className="mt-2.5 flex justify-end">
                                <button className="btn-primary" onClick={submitPaste} disabled={busy || !pasteText.trim()}>
                                    {busy ? <span className="spinner h-3 w-3 border" /> : "Import Data"}
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
                                className={`cursor-pointer rounded-lg border-2 border-dashed px-5 py-10 text-center transition-colors ${dragOver ? "border-accent bg-accent-soft" : "border-border"
                                    }`}
                            >
                                <UploadCloud size={22} className="mx-auto mb-2 text-subtle" strokeWidth={1.5} />
                                <div className="mb-1 text-xs text-muted-2">
                                    Drop a <strong>.csv</strong> or <strong>.xlsx</strong> file here
                                </div>
                                <div className="text-[10px] text-faint">or click to browse</div>
                                <input
                                    ref={fileRef}
                                    type="file"
                                    accept=".csv,.xlsx,.xls"
                                    onChange={onFileSelect}
                                    className="hidden"
                                />
                            </div>
                            <div className="mt-2.5 text-[10px] text-faint">
                                Expected format — wide table with a &quot;Time&quot; column and one column per state.
                                Column names like <span className="font-mono">&quot;Biomass (X) [g/L]&quot;</span> are auto-parsed to state name <span className="font-mono">X</span>.
                            </div>
                            {busy && <div className="mt-2 flex items-center gap-2 text-[11px] text-muted-2"><span className="spinner" /> Uploading…</div>}
                        </div>
                    )}

                    {/* ── Google Sheets tab ── */}
                    {tab === "sheets" && (
                        <div>
                            <div className="mb-2 text-[11px] leading-[1.6] text-muted-2">
                                Paste a <strong>public</strong> Google Sheets link.
                                The sheet must be shared as &quot;Anyone with the link can view&quot;.
                            </div>
                            <div className="flex gap-2">
                                <input
                                    type="text"
                                    value={sheetsUrl}
                                    onChange={(e) => setSheetsUrl(e.target.value)}
                                    placeholder="https://docs.google.com/spreadsheets/d/..."
                                    className="flex-1 text-[11px]"
                                />
                                <button className="btn-primary" onClick={submitSheets} disabled={busy || !sheetsUrl.trim()}>
                                    {busy ? <span className="spinner h-3 w-3 border" /> : "Import"}
                                </button>
                            </div>
                            <div className="mt-2.5 text-[10px] text-faint">
                                Uses the same wide-format column parsing. First row should be headers.
                                Supports specific sheet tabs via the <span className="font-mono">gid=</span> parameter in the URL.
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ── Stored measurements ── */}
            {modelId && measLoading && (
                <div className="card">
                    <SkeletonTable rows={3} cols={5} />
                </div>
            )}
            {modelId && !measLoading && measurements.length === 0 && (
                <div className="card">
                    <EmptyState
                        icon={Database}
                        title="No measurements stored yet"
                        description="Use one of the import options above to load experimental data for this model."
                        compact
                    />
                </div>
            )}
            {measurements.length > 0 && (
                <div className="card">
                    <div className="mb-2.5 text-[11px] font-medium text-muted">
                        Stored Measurements ({measurements.length} series)
                    </div>

                    {/* Summary table */}
                    <div className="mb-4 overflow-x-auto">
                        <table>
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
                                            <td className="font-medium">{m.name}</td>
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
                    </div>

                    {/* Wide-format data view */}
                    <div className="mb-1.5 text-[10px] font-medium text-subtle">Raw Data</div>
                    <div className="max-h-[300px] overflow-y-auto overflow-x-auto">
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
        <div className="text-[10px] text-subtle">
            <div className="mb-1">
                Preview: {headers.length} columns, {lines.length - 1} rows
            </div>
            <div className="overflow-x-auto">
                <table>
                    <thead>
                        <tr>
                            {headers.map((h, i) => (
                                <th key={i} className="whitespace-nowrap text-[9px]">{h}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((row, i) => (
                            <tr key={i}>
                                {row.map((cell, j) => (
                                    <td key={j} className="whitespace-nowrap text-[9px]">{cell}</td>
                                ))}
                            </tr>
                        ))}
                        {lines.length > 4 && (
                            <tr><td colSpan={headers.length} className="text-[9px] text-faint">… {lines.length - 4} more rows</td></tr>
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
                    <th className="text-[9px]">Time (h)</th>
                    {stateNames.map((s) => (
                        <th key={s} className="text-[9px]">{s}</th>
                    ))}
                </tr>
            </thead>
            <tbody>
                {sortedTimes.map((t) => (
                    <tr key={t}>
                        <td className="text-[10px]">{t.toFixed(2)}</td>
                        {stateNames.map((s) => (
                            <td key={s} className={`text-[10px] ${lookup[s][t] !== undefined ? "text-[#d4d4d8]" : "text-border"}`}>
                                {lookup[s][t] !== undefined ? lookup[s][t].toFixed(4) : "—"}
                            </td>
                        ))}
                    </tr>
                ))}
            </tbody>
        </table>
    );
}
