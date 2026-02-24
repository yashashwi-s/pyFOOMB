"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface ModelInfo { id: string; name: string; }
interface MRow { name: string; time: string; value: string; error: string; }

export default function DataPage() {
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [modelId, setModelId] = useState("");
    const [measurements, setMeasurements] = useState<Array<{ name: string; timepoints: number[]; values: number[]; errors: number[] | null }>>([]);
    const [rows, setRows] = useState<MRow[]>([{ name: "", time: "", value: "", error: "" }]);
    const [submitting, setSubmitting] = useState(false);
    const [message, setMessage] = useState("");

    useEffect(() => {
        api.getModels().then((r) => setModels(r.models)).catch(console.error);
    }, []);

    async function loadMeasurements(id: string) {
        setModelId(id);
        setMessage("");
        try {
            const r = await api.getMeasurements(id);
            setMeasurements(r.measurements);
        } catch { setMeasurements([]); }
    }

    function addRow() {
        setRows([...rows, { name: "", time: "", value: "", error: "" }]);
    }

    function updateRow(i: number, field: keyof MRow, val: string) {
        const newRows = [...rows];
        newRows[i] = { ...newRows[i], [field]: val };
        setRows(newRows);
    }

    function removeRow(i: number) {
        setRows(rows.filter((_, idx) => idx !== i));
    }

    async function submit() {
        if (!modelId) return;
        setSubmitting(true);
        setMessage("");

        // Group rows by name
        const grouped: Record<string, { timepoints: number[]; values: number[]; errors: number[] }> = {};
        for (const row of rows) {
            if (!row.name || !row.time || !row.value) continue;
            if (!grouped[row.name]) grouped[row.name] = { timepoints: [], values: [], errors: [] };
            grouped[row.name].timepoints.push(parseFloat(row.time));
            grouped[row.name].values.push(parseFloat(row.value));
            if (row.error) grouped[row.name].errors.push(parseFloat(row.error));
        }

        const mList = Object.entries(grouped).map(([name, data]) => ({
            name,
            timepoints: data.timepoints,
            values: data.values,
            errors: data.errors.length === data.timepoints.length ? data.errors : undefined,
        }));

        try {
            await api.addMeasurements(modelId, { measurements: mList as Array<{ name: string; timepoints: number[]; values: number[]; errors?: number[] }> });
            setMessage(`Added ${mList.length} measurement series`);
            loadMeasurements(modelId);
            setRows([{ name: "", time: "", value: "", error: "" }]);
        } catch (e: unknown) {
            setMessage(e instanceof Error ? e.message : "Failed");
        }
        setSubmitting(false);
    }

    async function clearAll() {
        if (!modelId) return;
        await api.clearMeasurements(modelId);
        setMeasurements([]);
        setMessage("All measurements cleared");
    }

    // Paste handler for tab-separated data
    function handlePaste(e: React.ClipboardEvent) {
        const text = e.clipboardData.getData("text");
        const lines = text.trim().split("\n").filter(Boolean);
        if (lines.length < 2) return;

        e.preventDefault();
        const newRows: MRow[] = [];
        for (const line of lines) {
            const parts = line.split(/[\t,]/).map((s) => s.trim());
            if (parts.length >= 3) {
                newRows.push({ name: parts[0], time: parts[1], value: parts[2], error: parts[3] || "" });
            }
        }
        if (newRows.length > 0) setRows(newRows);
    }

    return (
        <div>
            <div style={{ marginBottom: 20 }}>
                <h1 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>Measurement Data</h1>
                <p style={{ fontSize: 12, color: "#a1a1aa" }}>Add experimental measurements for model calibration.</p>
            </div>

            <div className="hint-bar">
                Enter measurement data manually or paste from a spreadsheet (tab/comma-separated: name, time, value, error).
                Errors are optional but required for WSS and negLL metrics in estimation.
            </div>

            {/* Model selector */}
            <div className="card" style={{ marginBottom: 16, display: "flex", gap: 12, alignItems: "flex-end" }}>
                <div>
                    <label style={{ fontSize: 10, color: "#71717a", display: "block", marginBottom: 3 }}>Model</label>
                    <select value={modelId} onChange={(e) => loadMeasurements(e.target.value)} style={{ width: 200 }}>
                        <option value="">Select model...</option>
                        {models.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.id})</option>)}
                    </select>
                </div>
                {modelId && measurements.length > 0 && (
                    <button className="btn-danger" style={{ fontSize: 10, padding: "4px 10px" }} onClick={clearAll}>Clear All</button>
                )}
            </div>

            {/* Entry table */}
            {modelId && (
                <div className="card" style={{ marginBottom: 16 }} onPaste={handlePaste}>
                    <div style={{ fontSize: 11, fontWeight: 500, color: "#a1a1aa", marginBottom: 8 }}>
                        Enter Data <span style={{ fontWeight: 400, color: "#52525b" }}>(or paste tab-separated: name, time, value, error)</span>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Time</th>
                                <th>Value</th>
                                <th>Error (opt.)</th>
                                <th style={{ width: 30 }}></th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((row, i) => (
                                <tr key={i}>
                                    <td><input type="text" value={row.name} onChange={(e) => updateRow(i, "name", e.target.value)} placeholder="e.g. X" style={{ width: 80 }} /></td>
                                    <td><input type="text" value={row.time} onChange={(e) => updateRow(i, "time", e.target.value)} placeholder="0.0" style={{ width: 70 }} /></td>
                                    <td><input type="text" value={row.value} onChange={(e) => updateRow(i, "value", e.target.value)} placeholder="0.0" style={{ width: 80 }} /></td>
                                    <td><input type="text" value={row.error} onChange={(e) => updateRow(i, "error", e.target.value)} placeholder="—" style={{ width: 70 }} /></td>
                                    <td>
                                        <button className="btn-secondary" style={{ padding: "2px 6px", fontSize: 10 }} onClick={() => removeRow(i)}>×</button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                        <button className="btn-secondary" onClick={addRow}>+ Add Row</button>
                        <button className="btn-primary" onClick={submit} disabled={submitting}>
                            {submitting ? "Submitting..." : "Submit Measurements"}
                        </button>
                    </div>
                    {message && (
                        <div style={{ marginTop: 8, fontSize: 11, color: message.includes("Added") ? "#22c55e" : "#ef4444" }}>
                            {message}
                        </div>
                    )}
                </div>
            )}

            {/* Existing measurements */}
            {measurements.length > 0 && (
                <div className="card">
                    <div style={{ fontSize: 11, fontWeight: 500, color: "#a1a1aa", marginBottom: 8 }}>
                        Stored Measurements ({measurements.length})
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Points</th>
                                <th>Time Range</th>
                                <th>Errors</th>
                            </tr>
                        </thead>
                        <tbody>
                            {measurements.map((m, i) => (
                                <tr key={i}>
                                    <td style={{ fontWeight: 500 }}>{m.name}</td>
                                    <td>{m.timepoints.length}</td>
                                    <td>{m.timepoints[0]?.toFixed(1)} — {m.timepoints[m.timepoints.length - 1]?.toFixed(1)}</td>
                                    <td>
                                        <span className={`dot ${m.errors ? "dot-green" : "dot-gray"}`} />
                                        {m.errors ? "Yes" : "No"}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
