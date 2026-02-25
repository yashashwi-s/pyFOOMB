"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ComposedChart, Line, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import MathTex from "@/components/Math";
import { paramToTex } from "@/lib/paramToTex";

const COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4", "#f97316"];

interface ModelInfo { id: string; name: string; }

interface TimeSeriesData { name: string; timepoints: number[]; values: number[]; }
interface MeasData { name: string; timepoints: number[]; values: number[]; errors?: number[] | null; }

export default function SimulationPage() {
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [modelId, setModelId] = useState("");
    const [modelMeta, setModelMeta] = useState<Record<string, unknown> | null>(null);
    const [tStart, setTStart] = useState(0);
    const [tEnd, setTEnd] = useState(20);
    const [nPoints, setNPoints] = useState(200);
    const [paramOverrides, setParamOverrides] = useState<Record<string, number>>({});
    const [results, setResults] = useState<TimeSeriesData[]>([]);
    const [running, setRunning] = useState(false);
    const [error, setError] = useState("");
    const [measurements, setMeasurements] = useState<MeasData[]>([]);

    useEffect(() => {
        api.getModels().then((r) => setModels(r.models)).catch(console.error);
    }, []);

    async function loadModel(id: string) {
        setModelId(id);
        setResults([]);
        setError("");
        try {
            const r = await api.getModel(id);
            setModelMeta(r.metadata);
            setParamOverrides({});
            if (r.metadata?.default_t_end) setTEnd(r.metadata.default_t_end as number);
            // Fetch stored measurements
            try {
                const meas = await api.getMeasurements(id);
                setMeasurements(meas.measurements || []);
            } catch { setMeasurements([]); }
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed");
        }
    }

    async function runSimulation() {
        if (!modelId) return;
        setRunning(true);
        setError("");
        try {
            const r = await api.simulate(modelId, {
                t_start: tStart,
                t_end: tEnd,
                n_points: nPoints,
                parameters: Object.keys(paramOverrides).length > 0 ? paramOverrides : undefined,
            });
            setResults(r.results);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Simulation failed");
        }
        setRunning(false);
    }

    // Transform simulation data for Recharts
    const chartData = results.length > 0
        ? results[0].timepoints.map((t, i) => {
            const point: Record<string, number> = { time: t };
            results.forEach((r) => { point[r.name] = r.values[i]; });
            return point;
        })
        : [];

    // Merge measurement scatter points into chart data
    const measPoints: Record<string, Array<Record<string, number>>> = {};
    measurements.forEach((m) => {
        if (!measPoints[m.name]) measPoints[m.name] = [];
        m.timepoints.forEach((t, i) => {
            measPoints[m.name].push({ time: t, [`${m.name}_meas`]: m.values[i] });
        });
    });
    // All unique measurement state names
    const measNames = [...new Set(measurements.map((m) => m.name))];

    const allParams = modelMeta ? { ...((modelMeta.model_parameters as Record<string, number>) || {}), ...((modelMeta.initial_values as Record<string, number>) || {}) } : {};

    return (
        <div>
            <div style={{ marginBottom: 20 }}>
                <h1 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>Simulation</h1>
                <p style={{ fontSize: 12, color: "#a1a1aa" }}>Run forward simulations and explore model dynamics.</p>
            </div>

            <div className="hint-bar">
                Run a forward simulation to verify your model produces sensible dynamics before fitting to data.
                Adjust parameters interactively to explore behavior.
            </div>

            {/* Controls */}
            <div className="card" style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
                    <div>
                        <label style={{ fontSize: 10, color: "#71717a", display: "block", marginBottom: 3 }}>Model</label>
                        <select value={modelId} onChange={(e) => loadModel(e.target.value)} style={{ width: 180 }}>
                            <option value="">Select model...</option>
                            {models.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.id})</option>)}
                        </select>
                    </div>
                    <div>
                        <label style={{ fontSize: 10, color: "#71717a", display: "block", marginBottom: 3 }}>t_start</label>
                        <input type="number" step="any" value={tStart} onChange={(e) => setTStart(parseFloat(e.target.value) || 0)} />
                    </div>
                    <div>
                        <label style={{ fontSize: 10, color: "#71717a", display: "block", marginBottom: 3 }}>t_end</label>
                        <input type="number" step="any" value={tEnd} onChange={(e) => setTEnd(parseFloat(e.target.value) || 0)} />
                    </div>
                    <div>
                        <label style={{ fontSize: 10, color: "#71717a", display: "block", marginBottom: 3 }}>Points</label>
                        <input type="number" value={nPoints} onChange={(e) => setNPoints(parseInt(e.target.value) || 100)} />
                    </div>
                    <button className="btn-primary" onClick={runSimulation} disabled={running || !modelId}>
                        {running ? <><span className="spinner" style={{ marginRight: 6 }} /> Running...</> : "▸ Run Simulation"}
                    </button>
                </div>
            </div>

            {/* Parameter overrides */}
            {modelMeta && (
                <div className="card" style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 11, fontWeight: 500, color: "#a1a1aa", marginBottom: 8 }}>
                        Parameters <span style={{ fontWeight: 400, color: "#52525b" }}>(modify to override defaults)</span>
                    </div>
                    <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                        {Object.entries(allParams).map(([key, defaultVal]) => (
                            <div key={key} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                <label style={{ fontSize: 10, color: "#a1a1aa" }}><MathTex tex={paramToTex(key)} /></label>
                                <input
                                    type="number"
                                    step="any"
                                    defaultValue={defaultVal}
                                    style={{ width: 80 }}
                                    onChange={(e) => {
                                        const v = parseFloat(e.target.value);
                                        if (!isNaN(v)) setParamOverrides((p) => ({ ...p, [key]: v }));
                                    }}
                                />
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {error && (
                <div style={{ padding: "8px 12px", background: "#450a0a", border: "1px solid #991b1b", borderRadius: 6, fontSize: 11, marginBottom: 16 }}>
                    <span className="dot dot-red" />{error}
                </div>
            )}

            {/* Chart */}
            {(chartData.length > 0 || measurements.length > 0) && (
                <div className="card" style={{ marginBottom: 16 }}>
                    {measurements.length > 0 && chartData.length === 0 && (
                        <div style={{ fontSize: 11, color: "#71717a", marginBottom: 8 }}>
                            {measurements.length} measurement series loaded — run simulation to overlay model fit
                        </div>
                    )}
                    <ResponsiveContainer width="100%" height={360}>
                        <ComposedChart margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                            <XAxis dataKey="time" type="number" tick={{ fontSize: 10, fill: "#71717a" }} label={{ value: "Time [h]", position: "insideBottom", offset: -4, style: { fontSize: 10, fill: "#71717a" } }} domain={["auto", "auto"]} />
                            <YAxis tick={{ fontSize: 10, fill: "#71717a" }} />
                            <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #27272a", borderRadius: 6, fontSize: 11 }} />
                            <Legend wrapperStyle={{ fontSize: 11 }} />
                            {/* Simulation lines */}
                            {results.map((r, i) => (
                                <Line key={r.name} type="monotone" data={chartData} dataKey={r.name} stroke={COLORS[i % COLORS.length]} dot={false} strokeWidth={1.5} name={r.name} />
                            ))}
                            {/* Measurement scatter points */}
                            {measNames.map((name, i) => {
                                const colorIdx = results.findIndex((r) => r.name === name);
                                const color = COLORS[(colorIdx >= 0 ? colorIdx : i) % COLORS.length];
                                return (
                                    <Scatter
                                        key={`${name}_meas`}
                                        data={measPoints[name]}
                                        dataKey={`${name}_meas`}
                                        fill={color}
                                        name={`${name} (data)`}
                                        shape="circle"
                                        legendType="circle"
                                    />
                                );
                            })}
                        </ComposedChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* Data table */}
            {chartData.length > 0 && (
                <div className="card" style={{ maxHeight: 300, overflowY: "auto" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                        <span style={{ fontSize: 11, fontWeight: 500, color: "#a1a1aa" }}>Data Table</span>
                        <button className="btn-secondary" style={{ fontSize: 10, padding: "3px 10px" }} onClick={() => {
                            const header = ["time", ...results.map((r) => r.name)].join(",");
                            const rows = chartData.map((d) => [d.time, ...results.map((r) => d[r.name])].join(","));
                            const csv = [header, ...rows].join("\n");
                            const blob = new Blob([csv], { type: "text/csv" });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement("a"); a.href = url; a.download = "simulation.csv"; a.click();
                        }}>
                            Export CSV
                        </button>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Time</th>
                                {results.map((r) => <th key={r.name}>{r.name}</th>)}
                            </tr>
                        </thead>
                        <tbody>
                            {chartData.filter((_, i) => i % Math.ceil(chartData.length / 50) === 0).map((d, i) => (
                                <tr key={i}>
                                    <td>{typeof d.time === 'number' ? d.time.toFixed(3) : d.time}</td>
                                    {results.map((r) => <td key={r.name}>{typeof d[r.name] === 'number' ? (d[r.name] as number).toFixed(4) : d[r.name]}</td>)}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
