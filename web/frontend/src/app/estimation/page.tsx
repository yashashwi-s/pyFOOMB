"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter } from "recharts";
import MathTex from "@/components/Math";
import { paramToTex } from "@/lib/paramToTex";

const COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

interface ModelInfo { id: string; name: string; }

interface EstimationResult {
    estimates?: Record<string, number>;
    distributions?: Record<string, number[]>;
    loss?: number;
}

export default function EstimationPage() {
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [modelId, setModelId] = useState("");
    const [modelMeta, setModelMeta] = useState<Record<string, unknown> | null>(null);
    const [unknowns, setUnknowns] = useState<Record<string, [number, number]>>({});
    const [metric, setMetric] = useState("SS");
    const [method, setMethod] = useState("local");
    const [running, setRunning] = useState(false);
    const [result, setResult] = useState<EstimationResult | null>(null);
    const [error, setError] = useState("");
    // Parallel options
    const [nIslands, setNIslands] = useState(4);
    const [popSize, setPopSize] = useState(20);
    const [nEvolutions, setNEvolutions] = useState(50);
    const [nJobs, setNJobs] = useState(10);
    const [mcSamples, setMcSamples] = useState(100);

    useEffect(() => {
        api.getModels().then((r) => setModels(r.models)).catch(console.error);
    }, []);

    async function loadModel(id: string) {
        setModelId(id);
        setResult(null);
        setError("");
        try {
            const r = await api.getModel(id);
            setModelMeta(r.metadata);
            // Initialize unknowns from model parameters
            const mp = (r.metadata?.model_parameters || {}) as Record<string, number>;
            const init: Record<string, [number, number]> = {};
            for (const [k, v] of Object.entries(mp)) {
                const lo = v > 0 ? v * 0.1 : v * 10;
                const hi = v > 0 ? v * 10 : v * 0.1;
                init[k] = [Math.min(lo, hi), Math.max(lo, hi)];
            }
            setUnknowns(init);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed");
        }
    }

    function toggleUnknown(key: string) {
        const next = { ...unknowns };
        if (next[key]) delete next[key];
        else {
            const mp = (modelMeta?.model_parameters || {}) as Record<string, number>;
            const iv = (modelMeta?.initial_values || {}) as Record<string, number>;
            const v = mp[key] ?? iv[key] ?? 1;
            next[key] = [v * 0.1, v * 10];
        }
        setUnknowns(next);
    }

    async function runEstimation() {
        if (!modelId || Object.keys(unknowns).length === 0) return;
        setRunning(true);
        setError("");
        setResult(null);
        try {
            const r = await api.estimate(modelId, {
                unknowns,
                metric,
                method,
                n_islands: nIslands,
                pop_size: popSize,
                n_evolutions: nEvolutions,
                n_jobs: nJobs,
                mc_samples: mcSamples,
            });
            setResult(r);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Estimation failed");
        }
        setRunning(false);
    }

    const allParams = modelMeta ? { ...((modelMeta.model_parameters as Record<string, number>) || {}), ...((modelMeta.initial_values as Record<string, number>) || {}) } : {};

    return (
        <div>
            <div style={{ marginBottom: 20 }}>
                <h1 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>Parameter Estimation</h1>
                <p style={{ fontSize: 12, color: "#a1a1aa" }}>Fit model parameters to your measurement data.</p>
            </div>

            <div className="hint-bar">
                Select which parameters to estimate and set their bounds. Choose a metric
                (SS = sum of squares, WSS = weighted, negLL = neg. log-likelihood) and an optimization method.
                Requires measurement data to be uploaded first.
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                {/* Left: Configuration */}
                <div>
                    {/* Model selector */}
                    <div className="card" style={{ marginBottom: 12 }}>
                        <label style={{ fontSize: 10, color: "#71717a", display: "block", marginBottom: 3 }}>Model</label>
                        <select value={modelId} onChange={(e) => loadModel(e.target.value)} style={{ width: "100%" }}>
                            <option value="">Select model...</option>
                            {models.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.id})</option>)}
                        </select>
                    </div>

                    {/* Unknowns */}
                    {modelMeta && (
                        <div className="card" style={{ marginBottom: 12 }}>
                            <div style={{ fontSize: 11, fontWeight: 500, color: "#a1a1aa", marginBottom: 8 }}>
                                Select Unknowns & Bounds
                            </div>
                            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                                {Object.entries(allParams).map(([key, val]) => {
                                    const isSelected = !!unknowns[key];
                                    return (
                                        <div key={key} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                            <input
                                                type="checkbox"
                                                checked={isSelected}
                                                onChange={() => toggleUnknown(key)}
                                                style={{ accentColor: "#3b82f6" }}
                                            />
                                            <span style={{ width: 70, flexShrink: 0 }}><MathTex tex={paramToTex(key)} /></span>
                                            <span style={{ fontSize: 10, color: "#52525b", width: 50 }}>= {typeof val === 'number' ? val.toFixed(3) : String(val)}</span>
                                            {isSelected && (
                                                <>
                                                    <input
                                                        type="number" step="any"
                                                        value={unknowns[key][0]}
                                                        onChange={(e) => setUnknowns({ ...unknowns, [key]: [parseFloat(e.target.value) || 0, unknowns[key][1]] })}
                                                        style={{ width: 70 }}
                                                    />
                                                    <span style={{ fontSize: 10, color: "#52525b" }}>→</span>
                                                    <input
                                                        type="number" step="any"
                                                        value={unknowns[key][1]}
                                                        onChange={(e) => setUnknowns({ ...unknowns, [key]: [unknowns[key][0], parseFloat(e.target.value) || 0] })}
                                                        style={{ width: 70 }}
                                                    />
                                                </>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Metric & Method */}
                    {modelMeta && (
                        <div className="card" style={{ marginBottom: 12 }}>
                            <div style={{ display: "flex", gap: 16, marginBottom: 10 }}>
                                <div>
                                    <div style={{ fontSize: 10, color: "#71717a", marginBottom: 3 }}>Metric</div>
                                    <select value={metric} onChange={(e) => setMetric(e.target.value)} style={{ width: 120 }}>
                                        <option value="SS">Sum of Squares</option>
                                        <option value="WSS">Weighted SS</option>
                                        <option value="negLL">Neg. Log-Likelihood</option>
                                    </select>
                                </div>
                                <div>
                                    <div style={{ fontSize: 10, color: "#71717a", marginBottom: 3 }}>Method</div>
                                    <select value={method} onChange={(e) => setMethod(e.target.value)} style={{ width: 140 }}>
                                        <option value="local">Local (scipy)</option>
                                        <option value="parallel">Parallel (pygmo)</option>
                                        <option value="repeated">Repeated</option>
                                        <option value="mc">MC Sampling</option>
                                        <option value="parallel_mc">Parallel MC</option>
                                    </select>
                                </div>
                            </div>

                            {/* Method-specific options */}
                            {(method === "parallel" || method === "parallel_mc") && (
                                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                                    <div>
                                        <label style={{ fontSize: 9, color: "#52525b" }}>Islands</label>
                                        <input type="number" value={nIslands} onChange={(e) => setNIslands(parseInt(e.target.value) || 4)} style={{ width: 60 }} />
                                    </div>
                                    <div>
                                        <label style={{ fontSize: 9, color: "#52525b" }}>Pop Size</label>
                                        <input type="number" value={popSize} onChange={(e) => setPopSize(parseInt(e.target.value) || 20)} style={{ width: 60 }} />
                                    </div>
                                    <div>
                                        <label style={{ fontSize: 9, color: "#52525b" }}>Evolutions</label>
                                        <input type="number" value={nEvolutions} onChange={(e) => setNEvolutions(parseInt(e.target.value) || 50)} style={{ width: 60 }} />
                                    </div>
                                </div>
                            )}
                            {method === "repeated" && (
                                <div>
                                    <label style={{ fontSize: 9, color: "#52525b" }}>Jobs</label>
                                    <input type="number" value={nJobs} onChange={(e) => setNJobs(parseInt(e.target.value) || 10)} style={{ width: 60 }} />
                                </div>
                            )}
                            {(method === "mc" || method === "parallel_mc") && (
                                <div>
                                    <label style={{ fontSize: 9, color: "#52525b" }}>MC Samples</label>
                                    <input type="number" value={mcSamples} onChange={(e) => setMcSamples(parseInt(e.target.value) || 100)} style={{ width: 70 }} />
                                </div>
                            )}
                        </div>
                    )}

                    {modelMeta && (
                        <button className="btn-primary" onClick={runEstimation} disabled={running || Object.keys(unknowns).length === 0} style={{ width: "100%" }}>
                            {running ? <><span className="spinner" style={{ marginRight: 6 }} /> Estimating...</> : "Run Estimation"}
                        </button>
                    )}
                </div>

                {/* Right: Results */}
                <div>
                    {error && (
                        <div style={{ padding: "8px 12px", background: "#450a0a", border: "1px solid #991b1b", borderRadius: 6, fontSize: 11, marginBottom: 12 }}>
                            <span className="dot dot-red" />{error}
                        </div>
                    )}

                    {result && result.estimates && (
                        <div className="card" style={{ marginBottom: 12 }}>
                            <div style={{ fontSize: 11, fontWeight: 500, color: "#a1a1aa", marginBottom: 8 }}>Estimated Parameters</div>
                            <table>
                                <thead><tr><th>Parameter</th><th>Value</th></tr></thead>
                                <tbody>
                                    {Object.entries(result.estimates).map(([k, v]) => (
                                        <tr key={k}>
                                            <td><MathTex tex={paramToTex(k)} /></td>
                                            <td style={{ fontFamily: "var(--font-mono)" }}>{v.toFixed(6)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {result.loss != null && (
                                <div style={{ marginTop: 8, fontSize: 11, color: "#71717a" }}>
                                    Loss ({metric}): <span style={{ fontFamily: "var(--font-mono)", color: "#fafafa" }}>{result.loss.toExponential(4)}</span>
                                </div>
                            )}
                        </div>
                    )}

                    {result && result.distributions && (
                        <div className="card" style={{ marginBottom: 12 }}>
                            <div style={{ fontSize: 11, fontWeight: 500, color: "#a1a1aa", marginBottom: 8 }}>Parameter Distributions</div>
                            {Object.entries(result.distributions).map(([k, vals], i) => {
                                if (!Array.isArray(vals)) return null;
                                const mean = vals.reduce((a: number, b: number) => a + b, 0) / vals.length;
                                const std = Math.sqrt(vals.reduce((a: number, b: number) => a + (b - mean) ** 2, 0) / vals.length);
                                const nBins = 20;
                                const min = Math.min(...vals);
                                const max = Math.max(...vals);
                                const binWidth = (max - min) / nBins || 1;
                                const bins = Array.from({ length: nBins }, (_, bi) => {
                                    const lo = min + bi * binWidth;
                                    const hi = lo + binWidth;
                                    const count = vals.filter((v: number) => v >= lo && v < hi).length;
                                    return { x: (lo + hi) / 2, count };
                                });

                                return (
                                    <div key={k} style={{ marginBottom: 12 }}>
                                        <div style={{ fontSize: 11, marginBottom: 4, display: "flex", alignItems: "center", gap: 6 }}>
                                            <MathTex tex={paramToTex(k)} /> <span style={{ color: "#71717a" }}>&mu;={mean.toFixed(4)}, &sigma;={std.toFixed(4)}</span>
                                        </div>
                                        <ResponsiveContainer width="100%" height={80}>
                                            <ScatterChart margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
                                                <XAxis dataKey="x" tick={{ fontSize: 9, fill: "#52525b" }} />
                                                <YAxis dataKey="count" tick={{ fontSize: 9, fill: "#52525b" }} hide />
                                                <Scatter data={bins} fill={COLORS[i % COLORS.length]} />
                                            </ScatterChart>
                                        </ResponsiveContainer>
                                    </div>
                                );
                            })}
                        </div>
                    )}

                    {!result && !error && (
                        <div className="card" style={{ textAlign: "center", padding: 40, color: "#52525b" }}>
                            <div style={{ fontSize: 24, marginBottom: 8 }}>⊞</div>
                            <div style={{ fontSize: 12 }}>Configure and run an estimation to see results</div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
