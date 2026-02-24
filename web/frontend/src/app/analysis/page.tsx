"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

const COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

interface ModelInfo { id: string; name: string; }

export default function AnalysisPage() {
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [modelId, setModelId] = useState("");
    const [modelMeta, setModelMeta] = useState<Record<string, unknown> | null>(null);
    const [tab, setTab] = useState<"sensitivity" | "uncertainty">("sensitivity");
    const [tEnd, setTEnd] = useState(20);
    const [relH, setRelH] = useState(0.001);
    const [sensitivities, setSensitivities] = useState<Array<{ name: string; timepoints: number[]; values: number[] }>>([]);
    const [running, setRunning] = useState(false);
    const [error, setError] = useState("");

    // Uncertainty
    const [estimates, setEstimates] = useState<Record<string, number>>({});
    const [matrices, setMatrices] = useState<{ FIM?: { data: number[][]; labels: string[] }; Cov?: { data: number[][]; labels: string[] }; Corr?: { data: number[][]; labels: string[] } } | null>(null);

    useEffect(() => {
        api.getModels().then((r) => setModels(r.models)).catch(console.error);
    }, []);

    async function loadModel(id: string) {
        setModelId(id);
        setSensitivities([]);
        setMatrices(null);
        setError("");
        try {
            const r = await api.getModel(id);
            setModelMeta(r.metadata);
            if (r.metadata?.default_t_end) setTEnd(r.metadata.default_t_end as number);
            // Pre-populate estimates from model parameters
            const mp = (r.metadata?.model_parameters || {}) as Record<string, number>;
            setEstimates({ ...mp });
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed");
        }
    }

    async function runSensitivity() {
        if (!modelId) return;
        setRunning(true);
        setError("");
        try {
            const r = await api.getSensitivities(modelId, { t_end: tEnd, rel_h: relH });
            setSensitivities(r.sensitivities);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed");
        }
        setRunning(false);
    }

    async function runUncertainty() {
        if (!modelId) return;
        setRunning(true);
        setError("");
        try {
            const r = await api.getParameterMatrices(modelId, { estimates });
            setMatrices(r);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed");
        }
        setRunning(false);
    }

    // Transform sensitivity data for chart
    const sensChartData = sensitivities.length > 0
        ? sensitivities[0].timepoints.map((t, i) => {
            const point: Record<string, number> = { time: t };
            sensitivities.forEach((s) => { point[s.name] = s.values[i]; });
            return point;
        })
        : [];

    function renderMatrix(m: { data: number[][]; labels: string[] } | null | undefined, title: string) {
        if (!m) return null;
        return (
            <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 500, color: "#a1a1aa", marginBottom: 6 }}>{title}</div>
                <div style={{ overflowX: "auto" }}>
                    <table style={{ fontSize: 11 }}>
                        <thead>
                            <tr>
                                <th></th>
                                {m.labels?.map((l) => <th key={l} style={{ fontFamily: "var(--font-mono)", fontSize: 10 }}>{l}</th>)}
                            </tr>
                        </thead>
                        <tbody>
                            {m.data.map((row, i) => (
                                <tr key={i}>
                                    <td style={{ fontFamily: "var(--font-mono)", color: "#a1a1aa", fontSize: 10 }}>{m.labels?.[i]}</td>
                                    {row.map((v, j) => {
                                        const absV = Math.abs(v);
                                        let bg = "transparent";
                                        if (title === "Correlation" && i !== j) {
                                            const intensity = Math.min(absV, 1) * 0.3;
                                            bg = v > 0 ? `rgba(59,130,246,${intensity})` : `rgba(239,68,68,${intensity})`;
                                        }
                                        return (
                                            <td key={j} style={{ fontFamily: "var(--font-mono)", fontSize: 10, textAlign: "right", background: bg }}>
                                                {v != null ? v.toExponential(2) : "—"}
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        );
    }

    return (
        <div>
            <div style={{ marginBottom: 20 }}>
                <h1 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>Analysis</h1>
                <p style={{ fontSize: 12, color: "#a1a1aa" }}>Sensitivity analysis and parameter uncertainty quantification.</p>
            </div>

            <div className="hint-bar">
                <strong>Sensitivity:</strong> How much each parameter influences the model output over time.{" "}
                <strong>Uncertainty:</strong> Fisher Information Matrix (FIM) → variance-covariance → correlation matrices.
                Requires measurement data for uncertainty analysis.
            </div>

            {/* Model selector */}
            <div className="card" style={{ marginBottom: 16, display: "flex", gap: 12, alignItems: "flex-end" }}>
                <div>
                    <label style={{ fontSize: 10, color: "#71717a", display: "block", marginBottom: 3 }}>Model</label>
                    <select value={modelId} onChange={(e) => loadModel(e.target.value)} style={{ width: 200 }}>
                        <option value="">Select model...</option>
                        {models.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.id})</option>)}
                    </select>
                </div>
                <div style={{ display: "flex", gap: 2 }}>
                    <button
                        className={tab === "sensitivity" ? "btn-primary" : "btn-secondary"}
                        onClick={() => setTab("sensitivity")}
                    >
                        Sensitivity
                    </button>
                    <button
                        className={tab === "uncertainty" ? "btn-primary" : "btn-secondary"}
                        onClick={() => setTab("uncertainty")}
                    >
                        Uncertainty
                    </button>
                </div>
            </div>

            {error && (
                <div style={{ padding: "8px 12px", background: "#450a0a", border: "1px solid #991b1b", borderRadius: 6, fontSize: 11, marginBottom: 12 }}>
                    <span className="dot dot-red" />{error}
                </div>
            )}

            {/* Sensitivity tab */}
            {tab === "sensitivity" && modelId && (
                <div>
                    <div className="card" style={{ marginBottom: 12, display: "flex", gap: 12, alignItems: "flex-end" }}>
                        <div>
                            <label style={{ fontSize: 10, color: "#71717a", display: "block", marginBottom: 3 }}>t_end</label>
                            <input type="number" step="any" value={tEnd} onChange={(e) => setTEnd(parseFloat(e.target.value) || 20)} />
                        </div>
                        <div>
                            <label style={{ fontSize: 10, color: "#71717a", display: "block", marginBottom: 3 }}>rel_h</label>
                            <input type="number" step="any" value={relH} onChange={(e) => setRelH(parseFloat(e.target.value) || 0.001)} />
                        </div>
                        <button className="btn-primary" onClick={runSensitivity} disabled={running}>
                            {running ? <><span className="spinner" style={{ marginRight: 6 }} /> Computing...</> : "Compute Sensitivities"}
                        </button>
                    </div>

                    {sensChartData.length > 0 && (
                        <div className="card">
                            <ResponsiveContainer width="100%" height={400}>
                                <LineChart data={sensChartData} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                                    <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#71717a" }} label={{ value: "Time", position: "insideBottom", offset: -4, style: { fontSize: 10, fill: "#71717a" } }} />
                                    <YAxis tick={{ fontSize: 10, fill: "#71717a" }} />
                                    <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #27272a", borderRadius: 6, fontSize: 11 }} />
                                    <Legend wrapperStyle={{ fontSize: 10 }} />
                                    {sensitivities.map((s, i) => (
                                        <Line key={s.name} type="monotone" dataKey={s.name} stroke={COLORS[i % COLORS.length]} dot={false} strokeWidth={1.5} />
                                    ))}
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </div>
            )}

            {/* Uncertainty tab */}
            {tab === "uncertainty" && modelId && (
                <div>
                    <div className="card" style={{ marginBottom: 12 }}>
                        <div style={{ fontSize: 11, fontWeight: 500, color: "#a1a1aa", marginBottom: 8 }}>Estimated Parameter Values</div>
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                            {Object.entries(estimates).map(([k, v]) => (
                                <div key={k} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                    <label style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "#a1a1aa" }}>{k}</label>
                                    <input
                                        type="number" step="any" value={v}
                                        onChange={(e) => setEstimates({ ...estimates, [k]: parseFloat(e.target.value) || 0 })}
                                        style={{ width: 80 }}
                                    />
                                </div>
                            ))}
                        </div>
                        <button className="btn-primary" onClick={runUncertainty} disabled={running}>
                            {running ? <><span className="spinner" style={{ marginRight: 6 }} /> Computing...</> : "Compute Matrices"}
                        </button>
                    </div>

                    {matrices && (
                        <div className="card">
                            {renderMatrix(matrices.FIM, "Fisher Information Matrix (FIM)")}
                            {renderMatrix(matrices.Cov, "Variance-Covariance Matrix")}
                            {renderMatrix(matrices.Corr, "Correlation Matrix")}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
