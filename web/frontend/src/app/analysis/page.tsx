"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Activity, Sigma } from "lucide-react";
import PageHeader from "@/components/ui/PageHeader";
import StatusMessage from "@/components/ui/StatusMessage";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonChart } from "@/components/ui/Skeleton";
import {
    CHART_COLORS,
    CHART_GRID_STROKE,
    CHART_AXIS_TICK,
    CHART_TOOLTIP_STYLE,
    CHART_TOOLTIP_LABEL_STYLE,
    CHART_TOOLTIP_ITEM_STYLE,
    CHART_LEGEND_STYLE,
    formatNumber,
} from "@/lib/chartTheme";

interface ModelInfo { id: string; name: string; }
interface MatrixData { data: number[][]; labels: string[] }

export default function AnalysisPage() {
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [modelId, setModelId] = useState("");
    const [tab, setTab] = useState<"sensitivity" | "uncertainty">("sensitivity");
    const [tEnd, setTEnd] = useState(20);
    const [relH, setRelH] = useState(0.001);
    const [sensitivities, setSensitivities] = useState<Array<{ name: string; timepoints: number[]; values: number[] }>>([]);
    const [running, setRunning] = useState(false);
    const [error, setError] = useState("");

    // Uncertainty
    const [estimates, setEstimates] = useState<Record<string, number>>({});
    const [matrices, setMatrices] = useState<{ FIM?: MatrixData; Cov?: MatrixData; Corr?: MatrixData } | null>(null);

    useEffect(() => {
        api.getModels().then((r) => setModels(r.models)).catch(console.error);
    }, []);

    async function loadModel(id: string) {
        setModelId(id);
        setSensitivities([]);
        setMatrices(null);
        setError("");
        if (!id) return;
        try {
            const r = await api.getModel(id);
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

    // Sensitivities come back as one series per (state, parameter) pair,
    // named "d(STATE)/d(PARAM)" — that can be a lot of series (states ×
    // parameters). Per the dataviz guidance, past ~8 series a single chart
    // stops reading as one system, so facet into one small chart per state,
    // and keep each parameter's color identity fixed across facets (assign
    // by parameter, not by position within a facet).
    const SENS_NAME_RE = /^d\((.+)\)\/d\((.+)\)$/;
    const paramOrder: string[] = [];
    const byState = new Map<string, typeof sensitivities>();
    for (const s of sensitivities) {
        const m = s.name.match(SENS_NAME_RE);
        const state = m ? m[1] : "?";
        const param = m ? m[2] : s.name;
        if (!paramOrder.includes(param)) paramOrder.push(param);
        if (!byState.has(state)) byState.set(state, []);
        byState.get(state)!.push(s);
    }
    const paramColor = (param: string) => CHART_COLORS[paramOrder.indexOf(param) % CHART_COLORS.length];
    const sensFacets = [...byState.entries()].map(([state, series]) => ({
        state,
        series,
        chartData: series.length > 0
            ? series[0].timepoints.map((t, i) => {
                const point: Record<string, number> = { time: t };
                series.forEach((s) => {
                    const m = s.name.match(SENS_NAME_RE);
                    point[m ? m[2] : s.name] = s.values[i];
                });
                return point;
            })
            : [],
    }));

    function renderMatrix(m: MatrixData | null | undefined, title: string) {
        if (!m) return null;
        return (
            <div className="mb-4 last:mb-0">
                <div className="mb-1.5 text-[11px] font-medium text-muted">{title}</div>
                <div className="overflow-x-auto">
                    <table>
                        <thead>
                            <tr>
                                <th></th>
                                {m.labels?.map((l) => <th key={l} className="font-mono text-[10px]">{l}</th>)}
                            </tr>
                        </thead>
                        <tbody>
                            {m.data.map((row, i) => (
                                <tr key={i}>
                                    <td className="font-mono text-[10px] text-muted">{m.labels?.[i]}</td>
                                    {row.map((v, j) => {
                                        const absV = Math.abs(v);
                                        let bg: string | undefined;
                                        if (title === "Correlation" && i !== j) {
                                            const intensity = Math.min(absV, 1) * 0.3;
                                            bg = v > 0 ? `rgba(57,135,229,${intensity})` : `rgba(230,103,103,${intensity})`;
                                        }
                                        return (
                                            <td key={j} className="text-right font-mono text-[10px]" style={{ background: bg }}>
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
            <PageHeader title="Analysis" description="Sensitivity analysis and parameter uncertainty quantification." />

            <div className="hint-bar">
                <strong>Sensitivity:</strong> How much each parameter influences the model output over time.{" "}
                <strong>Uncertainty:</strong> Fisher Information Matrix (FIM) → variance-covariance → correlation matrices.
                Requires measurement data for uncertainty analysis.
            </div>

            {/* Model selector */}
            <div className="card mb-4 flex flex-wrap items-end gap-3">
                <div>
                    <label className="mb-1 block text-[10px] text-muted-2">Model</label>
                    <select value={modelId} onChange={(e) => loadModel(e.target.value)} className="w-[200px]">
                        <option value="">Select model...</option>
                        {models.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.id})</option>)}
                    </select>
                </div>
                <div className="flex gap-0.5">
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
                <div className="mb-3">
                    <StatusMessage type="error">{error}</StatusMessage>
                </div>
            )}

            {!modelId && (
                <div className="card">
                    <EmptyState icon={Activity} title="No model selected" description="Select a model above to compute sensitivities or uncertainty matrices." />
                </div>
            )}

            {/* Sensitivity tab */}
            {tab === "sensitivity" && modelId && (
                <div>
                    <div className="card mb-3 flex flex-wrap items-end gap-3">
                        <div>
                            <label className="mb-1 block text-[10px] text-muted-2">t_end</label>
                            <input type="number" step="any" value={tEnd} onChange={(e) => setTEnd(parseFloat(e.target.value) || 20)} />
                        </div>
                        <div>
                            <label className="mb-1 block text-[10px] text-muted-2">rel_h</label>
                            <input type="number" step="any" value={relH} onChange={(e) => setRelH(parseFloat(e.target.value) || 0.001)} />
                        </div>
                        <button className="btn-primary" onClick={runSensitivity} disabled={running}>
                            {running ? <><span className="spinner" /> Computing...</> : "Compute Sensitivities"}
                        </button>
                    </div>

                    {running && (
                        <div className="card">
                            <SkeletonChart height={400} />
                        </div>
                    )}
                    {!running && sensFacets.length === 0 && (
                        <div className="card">
                            <EmptyState
                                icon={Sigma}
                                title="No sensitivities computed yet"
                                description="Click Compute Sensitivities to see how each parameter influences the model states over time."
                                compact
                            />
                        </div>
                    )}
                    {!running && sensFacets.length > 0 && (
                        <div className={`grid grid-cols-1 gap-3 ${sensFacets.length > 1 ? "xl:grid-cols-2" : ""}`}>
                            {sensFacets.map(({ state, series, chartData }) => (
                                <div key={state} className="card">
                                    <div className="mb-1 text-[11px] font-medium text-muted">
                                        Sensitivity of <span className="font-mono">{state}</span>
                                    </div>
                                    <ResponsiveContainer width="100%" height={300}>
                                        <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                                            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} vertical={false} />
                                            <XAxis
                                                dataKey="time"
                                                type="number"
                                                domain={["auto", "auto"]}
                                                tick={CHART_AXIS_TICK}
                                                label={{ value: "Time [h]", position: "insideBottom", offset: -4, style: { fontSize: 10, fill: "#71717a" } }}
                                            />
                                            <YAxis tick={CHART_AXIS_TICK} tickFormatter={formatNumber} width={56} />
                                            <Tooltip
                                                contentStyle={CHART_TOOLTIP_STYLE}
                                                labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                                                itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                                                labelFormatter={(v) => `t = ${formatNumber(Number(v))} h`}
                                                formatter={(value) => formatNumber(value as number)}
                                            />
                                            <Legend wrapperStyle={CHART_LEGEND_STYLE} />
                                            {series.map((s) => {
                                                const m = s.name.match(SENS_NAME_RE);
                                                const param = m ? m[2] : s.name;
                                                return (
                                                    <Line key={s.name} type="monotone" data={chartData} dataKey={param} stroke={paramColor(param)} dot={false} strokeWidth={2} isAnimationActive={false} />
                                                );
                                            })}
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Uncertainty tab */}
            {tab === "uncertainty" && modelId && (
                <div>
                    <div className="card mb-3">
                        <div className="mb-2 text-[11px] font-medium text-muted">Estimated Parameter Values</div>
                        <div className="mb-2 flex flex-wrap gap-2">
                            {Object.entries(estimates).map(([k, v]) => (
                                <div key={k} className="flex items-center gap-1">
                                    <label className="font-mono text-[10px] text-muted">{k}</label>
                                    <input
                                        type="number" step="any" value={v}
                                        onChange={(e) => setEstimates({ ...estimates, [k]: parseFloat(e.target.value) || 0 })}
                                        className="w-20"
                                    />
                                </div>
                            ))}
                        </div>
                        <button className="btn-primary" onClick={runUncertainty} disabled={running}>
                            {running ? <><span className="spinner" /> Computing...</> : "Compute Matrices"}
                        </button>
                    </div>

                    {running && (
                        <div className="card">
                            <SkeletonChart height={220} />
                        </div>
                    )}
                    {!running && !matrices && (
                        <div className="card">
                            <EmptyState
                                icon={Sigma}
                                title="No uncertainty matrices yet"
                                description="Click Compute Matrices to derive the Fisher Information, covariance, and correlation matrices from measurement data."
                                compact
                            />
                        </div>
                    )}
                    {!running && matrices && (
                        <div className="card">
                            {renderMatrix(matrices.FIM, "Fisher Information Matrix (FIM)")}
                            {renderMatrix(matrices.Cov, "Variance-Covariance Matrix")}
                            {renderMatrix(matrices.Corr, "Correlation")}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
