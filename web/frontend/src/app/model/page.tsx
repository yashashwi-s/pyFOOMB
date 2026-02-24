"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

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
    const [selected, setSelected] = useState<Template | null>(null);
    const [params, setParams] = useState<Record<string, number>>({});
    const [initVals, setInitVals] = useState<Record<string, number>>({});
    const [modelName, setModelName] = useState("");
    const [creating, setCreating] = useState(false);
    const [result, setResult] = useState<{ model_id?: string; error?: string } | null>(null);

    useEffect(() => {
        api.getTemplates().then((r) => setTemplates(r.templates)).catch(console.error);
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
            <div style={{ marginBottom: 20 }}>
                <h1 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>Model Definition</h1>
                <p style={{ fontSize: 12, color: "#a1a1aa" }}>Select a bioprocess model template and configure its parameters.</p>
            </div>

            <div className="hint-bar">
                Define your bioprocess as a system of ODEs. Choose a template below — each implements a validated kinetic model.
                Parameters and initial values can be adjusted before or after creation.
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                {/* Left: Template selector */}
                <div>
                    {categories.map((cat) => (
                        <div key={cat} style={{ marginBottom: 16 }}>
                            <div style={{ fontSize: 10, color: "#52525b", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 600, marginBottom: 6 }}>
                                {cat}
                            </div>
                            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                                {templates.filter((t) => t.category === cat).map((t) => (
                                    <div
                                        key={t.id}
                                        className="card"
                                        onClick={() => selectTemplate(t)}
                                        style={{
                                            cursor: "pointer",
                                            borderColor: selected?.id === t.id ? "#3b82f6" : undefined,
                                            padding: 12,
                                        }}
                                    >
                                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                                            <span style={{ fontSize: 12, fontWeight: 500 }}>{t.name}</span>
                                            <span style={{ fontSize: 10, color: "#52525b", fontFamily: "var(--font-mono)" }}>
                                                {t.states.length} state{t.states.length > 1 ? "s" : ""}
                                            </span>
                                        </div>
                                        <div style={{ fontSize: 11, color: "#71717a", marginBottom: 4 }}>{t.description}</div>
                                        <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "#3b82f6" }}>{t.equation}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Right: Configuration */}
                <div>
                    {selected ? (
                        <div>
                            <div className="card" style={{ marginBottom: 12 }}>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                                    <div>
                                        <div style={{ fontSize: 13, fontWeight: 500 }}>{selected.name}</div>
                                        <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "#3b82f6", marginTop: 2 }}>{selected.equation}</div>
                                    </div>
                                    <div style={{ display: "flex", gap: 6 }}>
                                        {selected.states.map((s) => (
                                            <span key={s} style={{ fontSize: 10, padding: "2px 8px", background: "#27272a", borderRadius: 4, fontFamily: "var(--font-mono)" }}>
                                                {s}: {selected.state_labels[s]}
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                <div style={{ marginBottom: 8 }}>
                                    <label style={{ fontSize: 10, color: "#71717a", display: "block", marginBottom: 3 }}>Model Name</label>
                                    <input type="text" value={modelName} onChange={(e) => setModelName(e.target.value)} style={{ width: "100%" }} />
                                </div>
                            </div>

                            {/* Parameters */}
                            <div className="card" style={{ marginBottom: 12 }}>
                                <div style={{ fontSize: 11, fontWeight: 500, marginBottom: 8, color: "#a1a1aa" }}>Model Parameters</div>
                                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                                    {Object.entries(params).map(([key, val]) => (
                                        <div key={key} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                            <label style={{ fontSize: 11, fontFamily: "var(--font-mono)", width: 80, flexShrink: 0 }}>{key}</label>
                                            <input
                                                type="number"
                                                step="any"
                                                value={val}
                                                onChange={(e) => setParams({ ...params, [key]: parseFloat(e.target.value) || 0 })}
                                            />
                                            <span style={{ fontSize: 10, color: "#52525b", flex: 1 }}>{selected.parameter_labels[key]}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Initial Values */}
                            <div className="card" style={{ marginBottom: 12 }}>
                                <div style={{ fontSize: 11, fontWeight: 500, marginBottom: 8, color: "#a1a1aa" }}>Initial Values</div>
                                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                                    {Object.entries(initVals).map(([key, val]) => (
                                        <div key={key} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                            <label style={{ fontSize: 11, fontFamily: "var(--font-mono)", width: 80, flexShrink: 0 }}>{key}</label>
                                            <input
                                                type="number"
                                                step="any"
                                                value={val}
                                                onChange={(e) => setInitVals({ ...initVals, [key]: parseFloat(e.target.value) || 0 })}
                                            />
                                            <span style={{ fontSize: 10, color: "#52525b", flex: 1 }}>{selected.initial_value_labels[key]}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Create button */}
                            <button className="btn-primary" onClick={createModel} disabled={creating} style={{ width: "100%" }}>
                                {creating ? <><span className="spinner" style={{ marginRight: 6 }} /> Creating...</> : "Create Model"}
                            </button>

                            {result?.model_id && (
                                <div style={{ marginTop: 8, padding: "8px 12px", background: "#052e16", border: "1px solid #166534", borderRadius: 6, fontSize: 11 }}>
                                    <span className="dot dot-green" />
                                    Model created — ID: <strong style={{ fontFamily: "var(--font-mono)" }}>{result.model_id}</strong>
                                </div>
                            )}
                            {result?.error && (
                                <div style={{ marginTop: 8, padding: "8px 12px", background: "#450a0a", border: "1px solid #991b1b", borderRadius: 6, fontSize: 11 }}>
                                    <span className="dot dot-red" />
                                    {result.error}
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="card" style={{ textAlign: "center", padding: 40, color: "#52525b" }}>
                            <div style={{ fontSize: 24, marginBottom: 8 }}>⬡</div>
                            <div style={{ fontSize: 12 }}>Select a model template from the left</div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
