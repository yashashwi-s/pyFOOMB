"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ComposedChart, Line, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import MathTex from "@/components/Math";
import { paramToTex } from "@/lib/paramToTex";
import { Play, Download, LineChart as LineChartIcon } from "lucide-react";
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
    const [modelLoading, setModelLoading] = useState(false);

    useEffect(() => {
        api.getModels().then((r) => setModels(r.models)).catch(console.error);
    }, []);

    async function loadModel(id: string) {
        setModelId(id);
        setResults([]);
        setError("");
        if (!id) { setModelMeta(null); return; }
        setModelLoading(true);
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
        setModelLoading(false);
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
            <PageHeader title="Simulation" description="Run forward simulations and explore model dynamics." />

            <div className="hint-bar">
                Run a forward simulation to verify your model produces sensible dynamics before fitting to data.
                Adjust parameters interactively to explore behavior.
            </div>

            {/* Controls */}
            <div className="card mb-4">
                <div className="flex flex-wrap items-end gap-3">
                    <div>
                        <label className="mb-1 block text-[10px] text-muted-2">Model</label>
                        <select value={modelId} onChange={(e) => loadModel(e.target.value)} className="w-[180px]">
                            <option value="">Select model...</option>
                            {models.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.id})</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="mb-1 block text-[10px] text-muted-2">t_start</label>
                        <input type="number" step="any" value={tStart} onChange={(e) => setTStart(parseFloat(e.target.value) || 0)} />
                    </div>
                    <div>
                        <label className="mb-1 block text-[10px] text-muted-2">t_end</label>
                        <input type="number" step="any" value={tEnd} onChange={(e) => setTEnd(parseFloat(e.target.value) || 0)} />
                    </div>
                    <div>
                        <label className="mb-1 block text-[10px] text-muted-2">Points</label>
                        <input type="number" value={nPoints} onChange={(e) => setNPoints(parseInt(e.target.value) || 100)} />
                    </div>
                    <button className="btn-primary" onClick={runSimulation} disabled={running || !modelId}>
                        {running ? <><span className="spinner" /> Running...</> : <><Play size={12} /> Run Simulation</>}
                    </button>
                </div>
            </div>

            {/* Parameter overrides */}
            {modelMeta && (
                <div className="card mb-4">
                    <div className="mb-2 text-[11px] font-medium text-muted">
                        Parameters <span className="font-normal text-subtle">(modify to override defaults)</span>
                    </div>
                    <div className="flex flex-wrap gap-3">
                        {Object.entries(allParams).map(([key, defaultVal]) => (
                            <div key={key} className="flex items-center gap-1">
                                <label className="text-[10px] text-muted"><MathTex tex={paramToTex(key)} /></label>
                                <input
                                    type="number"
                                    step="any"
                                    defaultValue={defaultVal}
                                    className="w-20"
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
                <div className="mb-4">
                    <StatusMessage type="error">{error}</StatusMessage>
                </div>
            )}

            {!modelId && !modelLoading && (
                <div className="card">
                    <EmptyState
                        icon={LineChartIcon}
                        title="No model selected"
                        description="Pick a model above to run a forward simulation, or create one on the Model page first."
                    />
                </div>
            )}

            {modelLoading && (
                <div className="card mb-4">
                    <SkeletonChart height={80} />
                </div>
            )}

            {/* Chart */}
            {running && (
                <div className="card mb-4">
                    <SkeletonChart height={360} />
                </div>
            )}
            {!running && (chartData.length > 0 || measurements.length > 0) && (
                <div className="card mb-4">
                    {measurements.length > 0 && chartData.length === 0 && (
                        <div className="mb-2 text-[11px] text-muted-2">
                            {measurements.length} measurement series loaded — run simulation to overlay model fit
                        </div>
                    )}
                    <ResponsiveContainer width="100%" height={360}>
                        <ComposedChart margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} vertical={false} />
                            <XAxis
                                dataKey="time"
                                type="number"
                                tick={CHART_AXIS_TICK}
                                label={{ value: "Time [h]", position: "insideBottom", offset: -4, style: { fontSize: 10, fill: "#71717a" } }}
                                domain={["auto", "auto"]}
                            />
                            <YAxis tick={CHART_AXIS_TICK} tickFormatter={formatNumber} width={52} />
                            <Tooltip
                                contentStyle={CHART_TOOLTIP_STYLE}
                                labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                                itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                                labelFormatter={(v) => `t = ${formatNumber(Number(v))} h`}
                                formatter={(value) => formatNumber(value as number)}
                            />
                            <Legend wrapperStyle={CHART_LEGEND_STYLE} />
                            {/* Simulation lines */}
                            {results.map((r, i) => (
                                <Line key={r.name} type="monotone" data={chartData} dataKey={r.name} stroke={CHART_COLORS[i % CHART_COLORS.length]} dot={false} strokeWidth={2} name={r.name} isAnimationActive={false} />
                            ))}
                            {/* Measurement scatter points */}
                            {measNames.map((name, i) => {
                                const colorIdx = results.findIndex((r) => r.name === name);
                                const color = CHART_COLORS[(colorIdx >= 0 ? colorIdx : i) % CHART_COLORS.length];
                                return (
                                    <Scatter
                                        key={`${name}_meas`}
                                        data={measPoints[name]}
                                        dataKey={`${name}_meas`}
                                        fill={color}
                                        name={`${name} (data)`}
                                        shape="circle"
                                        legendType="circle"
                                        isAnimationActive={false}
                                    />
                                );
                            })}
                        </ComposedChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* Data table */}
            {chartData.length > 0 && (
                <div className="card max-h-[300px] overflow-y-auto">
                    <div className="mb-2 flex items-center justify-between">
                        <span className="text-[11px] font-medium text-muted">Data Table</span>
                        <button className="btn-secondary py-1 text-[10px]" onClick={() => {
                            const header = ["time", ...results.map((r) => r.name)].join(",");
                            const rows = chartData.map((d) => [d.time, ...results.map((r) => d[r.name])].join(","));
                            const csv = [header, ...rows].join("\n");
                            const blob = new Blob([csv], { type: "text/csv" });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement("a"); a.href = url; a.download = "simulation.csv"; a.click();
                        }}>
                            <Download size={11} /> Export CSV
                        </button>
                    </div>
                    <div className="overflow-x-auto">
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
                </div>
            )}
        </div>
    );
}
