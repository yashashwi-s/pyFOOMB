"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Math from "@/components/Math";
import { paramToTex } from "@/lib/paramToTex";
import { FlaskConical } from "lucide-react";
import PageHeader from "@/components/ui/PageHeader";
import StatusMessage from "@/components/ui/StatusMessage";
import EmptyState from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";

interface Template {
    id: string;
    name: string;
    category: string;
    description: string;
    equation: string;
    states: string[];
    state_labels: Record<string, string>;
    parameters: Record<string, number>;
    parameter_labels: Record<string, string>;
    initial_values: Record<string, number>;
    initial_value_labels: Record<string, string>;
    default_t_end: number;
}

export default function ModelPage() {
    const [templates, setTemplates] = useState<Template[]>([]);
    const [loadingTemplates, setLoadingTemplates] = useState(true);
    const [selected, setSelected] = useState<Template | null>(null);
    const [params, setParams] = useState<Record<string, number>>({});
    const [initVals, setInitVals] = useState<Record<string, number>>({});
    const [modelName, setModelName] = useState("");
    const [creating, setCreating] = useState(false);
    const [result, setResult] = useState<{ model_id?: string; error?: string } | null>(null);

    useEffect(() => {
        api.getTemplates()
            .then((r) => setTemplates(r.templates))
            .catch(console.error)
            .finally(() => setLoadingTemplates(false));
    }, []);

    function selectTemplate(t: Template) {
        setSelected(t);
        setParams({ ...t.parameters });
        setInitVals({ ...t.initial_values });
        setModelName(t.name);
        setResult(null);
    }

    async function createModel() {
        if (!selected) return;
        setCreating(true);
        setResult(null);
        try {
            const r = await api.createModel({
                template_id: selected.id,
                model_name: modelName,
                model_parameters: params,
                initial_values: initVals,
            });
            setResult({ model_id: r.model_id });
        } catch (e: unknown) {
            setResult({ error: e instanceof Error ? e.message : "Failed" });
        }
        setCreating(false);
    }

    const categories = [...new Set(templates.map((t) => t.category))];

    return (
        <div>
            <PageHeader
                title="Model Definition"
                description="Select a bioprocess model template and configure its parameters."
            />

            <div className="hint-bar">
                Define your bioprocess as a system of ODEs. Choose a template below — each implements a validated kinetic model.
                Parameters and initial values can be adjusted before or after creation.
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {/* Left: Template selector */}
                <div>
                    {loadingTemplates ? (
                        <div className="flex flex-col gap-2">
                            {Array.from({ length: 4 }).map((_, i) => (
                                <Skeleton key={i} className="h-16 w-full" />
                            ))}
                        </div>
                    ) : (
                        categories.map((cat) => (
                            <div key={cat} className="mb-4">
                                <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-subtle">
                                    {cat}
                                </div>
                                <div className="flex flex-col gap-1.5">
                                    {templates.filter((t) => t.category === cat).map((t) => (
                                        <div
                                            key={t.id}
                                            className={`card cursor-pointer p-3 ${selected?.id === t.id ? "border-accent" : ""}`}
                                            onClick={() => selectTemplate(t)}
                                        >
                                            <div className="mb-1 flex items-center justify-between">
                                                <span className="text-xs font-medium">{t.name}</span>
                                                <span className="font-mono text-[10px] text-subtle">
                                                    {t.states.length} state{t.states.length > 1 ? "s" : ""}
                                                </span>
                                            </div>
                                            <div className="mb-1 text-[11px] text-muted-2">{t.description}</div>
                                            <div className="overflow-x-auto rounded px-2 py-1">
                                                <Math tex={t.equation} />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))
                    )}
                </div>

                {/* Right: Configuration */}
                <div>
                    {selected ? (
                        <div>
                            <div className="card mb-3">
                                <div className="mb-3 flex items-center justify-between gap-3">
                                    <div className="min-w-0">
                                        <div className="text-sm font-medium">{selected.name}</div>
                                        <div className="mt-1 overflow-x-auto rounded px-2 py-1">
                                            <Math tex={selected.equation} />
                                        </div>
                                    </div>
                                    <div className="flex flex-shrink-0 flex-wrap gap-1.5">
                                        {selected.states.map((s) => (
                                            <span key={s} className="whitespace-nowrap rounded bg-border px-2 py-0.5 font-mono text-[10px]">
                                                {s}: {selected.state_labels[s]}
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                <div>
                                    <label className="mb-1 block text-[10px] text-muted-2">Model Name</label>
                                    <input type="text" value={modelName} onChange={(e) => setModelName(e.target.value)} className="w-full" />
                                </div>
                            </div>

                            {/* Parameters */}
                            <div className="card mb-3">
                                <div className="mb-2 text-[11px] font-medium text-muted">Model Parameters</div>
                                <div className="flex flex-col gap-1.5">
                                    {Object.entries(params).map(([key, val]) => (
                                        <div key={key} className="flex items-center gap-2">
                                            <label className="w-20 flex-shrink-0"><Math tex={paramToTex(key)} /></label>
                                            <input
                                                type="number"
                                                step="any"
                                                value={val}
                                                onChange={(e) => setParams({ ...params, [key]: parseFloat(e.target.value) || 0 })}
                                            />
                                            <span className="flex-1 text-[10px] text-subtle">{selected.parameter_labels[key]}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Initial Values */}
                            <div className="card mb-3">
                                <div className="mb-2 text-[11px] font-medium text-muted">Initial Values</div>
                                <div className="flex flex-col gap-1.5">
                                    {Object.entries(initVals).map(([key, val]) => (
                                        <div key={key} className="flex items-center gap-2">
                                            <label className="w-20 flex-shrink-0"><Math tex={paramToTex(key)} /></label>
                                            <input
                                                type="number"
                                                step="any"
                                                value={val}
                                                onChange={(e) => setInitVals({ ...initVals, [key]: parseFloat(e.target.value) || 0 })}
                                            />
                                            <span className="flex-1 text-[10px] text-subtle">{selected.initial_value_labels[key]}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Create button */}
                            <button className="btn-primary w-full" onClick={createModel} disabled={creating}>
                                {creating ? <><span className="spinner" /> Creating...</> : "Create Model"}
                            </button>

                            {result?.model_id && (
                                <div className="mt-2">
                                    <StatusMessage type="success">
                                        Model created — ID: <strong className="font-mono">{result.model_id}</strong>
                                    </StatusMessage>
                                </div>
                            )}
                            {result?.error && (
                                <div className="mt-2">
                                    <StatusMessage type="error">{result.error}</StatusMessage>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="card">
                            <EmptyState
                                icon={FlaskConical}
                                title="No template selected"
                                description="Select a model template from the list on the left to configure its parameters."
                            />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
