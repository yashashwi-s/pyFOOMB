"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import MathTex from "@/components/Math";
import { paramToTex } from "@/lib/paramToTex";
import { Target } from "lucide-react";
import PageHeader from "@/components/ui/PageHeader";
import StatusMessage from "@/components/ui/StatusMessage";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonChart } from "@/components/ui/Skeleton";
import { CHART_COLORS, CHART_TOOLTIP_STYLE, CHART_TOOLTIP_LABEL_STYLE, CHART_TOOLTIP_ITEM_STYLE, formatNumber } from "@/lib/chartTheme";

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
        if (!id) { setModelMeta(null); return; }
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
            <PageHeader title="Parameter Estimation" description="Fit model parameters to your measurement data." />

            <div className="hint-bar">
                Select which parameters to estimate and set their bounds. Choose a metric
                (SS = sum of squares, WSS = weighted, negLL = neg. log-likelihood) and an optimization method.
                Requires measurement data to be uploaded first.
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {/* Left: Configuration */}
                <div>
                    {/* Model selector */}
                    <div className="card mb-3">
                        <label className="mb-1 block text-[10px] text-muted-2">Model</label>
                        <select value={modelId} onChange={(e) => loadModel(e.target.value)} className="w-full">
                            <option value="">Select model...</option>
                            {models.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.id})</option>)}
                        </select>
                    </div>

                    {/* Unknowns */}
                    {modelMeta && (
                        <div className="card mb-3">
                            <div className="mb-2 text-[11px] font-medium text-muted">
                                Select Unknowns &amp; Bounds
                            </div>
                            <div className="flex flex-col gap-1">
                                {Object.entries(allParams).map(([key, val]) => {
                                    const isSelected = !!unknowns[key];
                                    return (
                                        <div key={key} className="flex items-center gap-1.5">
                                            <input
                                                type="checkbox"
                                                checked={isSelected}
                                                onChange={() => toggleUnknown(key)}
                                            />
                                            <span className="w-[70px] flex-shrink-0"><MathTex tex={paramToTex(key)} /></span>
                                            <span className="w-[50px] text-[10px] text-subtle">= {typeof val === 'number' ? val.toFixed(3) : String(val)}</span>
                                            {isSelected && (
                                                <>
                                                    <input
                                                        type="number" step="any"
                                                        value={unknowns[key][0]}
                                                        onChange={(e) => setUnknowns({ ...unknowns, [key]: [parseFloat(e.target.value) || 0, unknowns[key][1]] })}
                                                        className="w-[70px]"
                                                    />
                                                    <span className="text-[10px] text-subtle">→</span>
                                                    <input
                                                        type="number" step="any"
                                                        value={unknowns[key][1]}
                                                        onChange={(e) => setUnknowns({ ...unknowns, [key]: [unknowns[key][0], parseFloat(e.target.value) || 0] })}
                                                        className="w-[70px]"
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
                        <div className="card mb-3">
                            <div className="mb-2.5 flex gap-4">
                                <div>
                                    <div className="mb-1 text-[10px] text-muted-2">Metric</div>
                                    <select value={metric} onChange={(e) => setMetric(e.target.value)} className="w-[120px]">
                                        <option value="SS">Sum of Squares</option>
                                        <option value="WSS">Weighted SS</option>
                                        <option value="negLL">Neg. Log-Likelihood</option>
                                    </select>
                                </div>
                                <div>
                                    <div className="mb-1 text-[10px] text-muted-2">Method</div>
                                    <select value={method} onChange={(e) => setMethod(e.target.value)} className="w-[140px]">
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
                                <div className="mb-2 flex flex-wrap gap-2">
                                    <div>
                                        <label className="text-[9px] text-subtle">Islands</label>
                                        <input type="number" value={nIslands} onChange={(e) => setNIslands(parseInt(e.target.value) || 4)} className="w-[60px]" />
                                    </div>
                                    <div>
                                        <label className="text-[9px] text-subtle">Pop Size</label>
                                        <input type="number" value={popSize} onChange={(e) => setPopSize(parseInt(e.target.value) || 20)} className="w-[60px]" />
                                    </div>
                                    <div>
                                        <label className="text-[9px] text-subtle">Evolutions</label>
                                        <input type="number" value={nEvolutions} onChange={(e) => setNEvolutions(parseInt(e.target.value) || 50)} className="w-[60px]" />
                                    </div>
                                </div>
                            )}
                            {method === "repeated" && (
                                <div>
                                    <label className="text-[9px] text-subtle">Jobs</label>
                                    <input type="number" value={nJobs} onChange={(e) => setNJobs(parseInt(e.target.value) || 10)} className="w-[60px]" />
                                </div>
                            )}
                            {(method === "mc" || method === "parallel_mc") && (
                                <div>
                                    <label className="text-[9px] text-subtle">MC Samples</label>
                                    <input type="number" value={mcSamples} onChange={(e) => setMcSamples(parseInt(e.target.value) || 100)} className="w-[70px]" />
                                </div>
                            )}
                            {(method === "parallel" || method === "parallel_mc" || method === "repeated") && (
                                <div className="mt-2 text-[10px] text-faint">
                                    Global/parallel methods use pygmo islands and may take a while — the tab will stay busy until it completes.
                                </div>
                            )}
                        </div>
                    )}

                    {modelMeta && (
                        <button className="btn-primary w-full" onClick={runEstimation} disabled={running || Object.keys(unknowns).length === 0}>
                            {running ? <><span className="spinner" /> Estimating...</> : "Run Estimation"}
                        </button>
                    )}
                </div>

                {/* Right: Results */}
                <div>
                    {error && (
                        <div className="mb-3">
                            <StatusMessage type="error">{error}</StatusMessage>
                        </div>
                    )}

                    {running && (
                        <div className="card mb-3">
                            <SkeletonChart height={200} />
                        </div>
                    )}

                    {!running && result && result.estimates && (
                        <div className="card mb-3">
                            <div className="mb-2 text-[11px] font-medium text-muted">Estimated Parameters</div>
                            <table>
                                <thead><tr><th>Parameter</th><th>Value</th></tr></thead>
                                <tbody>
                                    {Object.entries(result.estimates).map(([k, v]) => (
                                        <tr key={k}>
                                            <td><MathTex tex={paramToTex(k)} /></td>
                                            <td className="font-mono">{v.toFixed(6)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {result.loss != null && (
                                <div className="mt-2 text-[11px] text-muted-2">
                                    Loss ({metric}): <span className="font-mono text-foreground">{result.loss.toExponential(4)}</span>
                                </div>
                            )}
                        </div>
                    )}

                    {!running && result && result.distributions && (
                        <div className="card mb-3">
                            <div className="mb-2 text-[11px] font-medium text-muted">Parameter Distributions</div>
                            {Object.entries(result.distributions).map(([k, vals], i) => {
                                if (!Array.isArray(vals) || vals.length === 0) return null;
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
                                const color = CHART_COLORS[i % CHART_COLORS.length];

                                return (
                                    <div key={k} className="mb-3 last:mb-0">
                                        <div className="mb-1 flex items-center gap-1.5 text-[11px]">
                                            <MathTex tex={paramToTex(k)} /> <span className="text-muted-2">mean={formatNumber(mean)}, sd={formatNumber(std)}</span>
                                        </div>
                                        <ResponsiveContainer width="100%" height={90}>
                                            <BarChart data={bins} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
                                                <XAxis dataKey="x" tick={{ fontSize: 9, fill: "#52525b" }} tickFormatter={formatNumber} />
                                                <YAxis dataKey="count" hide />
                                                <Tooltip
                                                    contentStyle={CHART_TOOLTIP_STYLE}
                                                    labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                                                    itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                                                    labelFormatter={(v) => `≈ ${formatNumber(Number(v))}`}
                                                    formatter={(value) => [value, "samples"]}
                                                />
                                                <Bar dataKey="count" fill={color} radius={[2, 2, 0, 0]} isAnimationActive={false} />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>
                                );
                            })}
                        </div>
                    )}

                    {!running && !result && !error && (
                        <div className="card">
                            <EmptyState
                                icon={Target}
                                title="No estimation run yet"
                                description="Select parameters to fit and their bounds on the left, then run an estimation to see results here."
                            />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
