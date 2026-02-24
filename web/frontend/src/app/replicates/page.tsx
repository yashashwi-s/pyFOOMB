"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface ModelInfo { id: string; name: string; }

export default function ReplicatesPage() {
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [modelId, setModelId] = useState("");
    const [replicateIds, setReplicateIds] = useState<(string | null)[]>([]);
    const [newRepId, setNewRepId] = useState("");
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");

    // Mapping form
    const [mappings, setMappings] = useState<Array<{ replicate_id: string; global_name: string; local_name: string; value: string }>>([]);

    // Integrator
    const [intKwargs, setIntKwargs] = useState<Record<string, string>>({ atol: "1e-8", rtol: "1e-6" });

    // Parameters
    const [parameters, setParameters] = useState<Record<string, number>>({});

    useEffect(() => {
        api.getModels().then((r) => setModels(r.models)).catch(console.error);
    }, []);

    async function loadModel(id: string) {
        setModelId(id);
        setError("");
        setMessage("");
        try {
            const r = await api.getReplicates(id);
            setReplicateIds(r.replicate_ids);
            const p = await api.getParameters(id);
            setParameters(p.parameters);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed");
        }
    }

    async function addReplicate() {
        if (!modelId || !newRepId) return;
        setError("");
        try {
            const r = await api.addReplicate(modelId, newRepId);
            setReplicateIds(r.replicate_ids);
            setNewRepId("");
            setMessage(`Replicate '${newRepId}' added`);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed");
        }
    }

    function addMappingRow() {
        setMappings([...mappings, { replicate_id: "", global_name: "", local_name: "", value: "" }]);
    }

    async function submitMappings() {
        if (!modelId || mappings.length === 0) return;
        setError("");
        try {
            const formatted = mappings.map((m) => ({
                replicate_id: m.replicate_id,
                global_name: m.global_name,
                local_name: m.local_name || undefined,
                value: m.value ? parseFloat(m.value) : undefined,
            }));
            await api.applyMappings(modelId, formatted);
            setMessage(`Applied ${formatted.length} mappings`);
            const p = await api.getParameters(modelId);
            setParameters(p.parameters);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed");
        }
    }

    async function updateIntegrator() {
        if (!modelId) return;
        try {
            const kwargs: Record<string, number> = {};
            for (const [k, v] of Object.entries(intKwargs)) {
                kwargs[k] = parseFloat(v);
            }
            await api.setIntegrator(modelId, kwargs);
            setMessage("Integrator settings updated");
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed");
        }
    }

    return (
        <div>
            <div style={{ marginBottom: 20 }}>
                <h1 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>Replicates & Settings</h1>
                <p style={{ fontSize: 12, color: "#a1a1aa" }}>Multi-reactor parameter mapping and integrator configuration.</p>
            </div>

            <div className="hint-bar">
                For experiments with multiple reactors or conditions, use replicates to share model structure
                while allowing parameter variation. Map global parameters (shared, e.g. µ_max) to local names
                (reactor-specific, e.g. initial biomass per reactor).
            </div>

            {/* Model selector */}
            <div className="card" style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 10, color: "#71717a", display: "block", marginBottom: 3 }}>Model</label>
                <select value={modelId} onChange={(e) => loadModel(e.target.value)} style={{ width: 200 }}>
                    <option value="">Select model...</option>
                    {models.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.id})</option>)}
                </select>
            </div>

            {error && (
                <div style={{ padding: "8px 12px", background: "#450a0a", border: "1px solid #991b1b", borderRadius: 6, fontSize: 11, marginBottom: 12 }}>
                    <span className="dot dot-red" />{error}
                </div>
            )}
            {message && (
                <div style={{ padding: "8px 12px", background: "#052e16", border: "1px solid #166534", borderRadius: 6, fontSize: 11, marginBottom: 12 }}>
                    <span className="dot dot-green" />{message}
                </div>
            )}

            {modelId && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                    {/* Left column */}
                    <div>
                        {/* Replicates */}
                        <div className="card" style={{ marginBottom: 12 }}>
                            <div style={{ fontSize: 11, fontWeight: 500, color: "#a1a1aa", marginBottom: 8 }}>Replicates</div>
                            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
                                {replicateIds.map((rid, i) => (
                                    <span key={i} style={{
                                        fontSize: 10, padding: "3px 8px", background: "#27272a", borderRadius: 4,
                                        fontFamily: "var(--font-mono)", color: rid === null ? "#52525b" : "#fafafa",
                                    }}>
                                        {rid === null ? "(single)" : rid}
                                    </span>
                                ))}
                            </div>
                            <div style={{ display: "flex", gap: 6 }}>
                                <input type="text" placeholder="Replicate ID" value={newRepId} onChange={(e) => setNewRepId(e.target.value)} style={{ width: 140 }} />
                                <button className="btn-secondary" onClick={addReplicate}>Add</button>
                            </div>
                        </div>

                        {/* Parameter Mappings */}
                        <div className="card" style={{ marginBottom: 12 }}>
                            <div style={{ fontSize: 11, fontWeight: 500, color: "#a1a1aa", marginBottom: 8 }}>Parameter Mappings</div>
                            {mappings.length > 0 && (
                                <table style={{ marginBottom: 8 }}>
                                    <thead>
                                        <tr>
                                            <th>Replicate</th>
                                            <th>Global</th>
                                            <th>Local</th>
                                            <th>Value</th>
                                            <th></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {mappings.map((m, i) => (
                                            <tr key={i}>
                                                <td><input type="text" value={m.replicate_id} onChange={(e) => { const n = [...mappings]; n[i].replicate_id = e.target.value; setMappings(n); }} style={{ width: 70 }} /></td>
                                                <td><input type="text" value={m.global_name} onChange={(e) => { const n = [...mappings]; n[i].global_name = e.target.value; setMappings(n); }} style={{ width: 70 }} /></td>
                                                <td><input type="text" value={m.local_name} onChange={(e) => { const n = [...mappings]; n[i].local_name = e.target.value; setMappings(n); }} style={{ width: 70 }} /></td>
                                                <td><input type="text" value={m.value} onChange={(e) => { const n = [...mappings]; n[i].value = e.target.value; setMappings(n); }} style={{ width: 60 }} /></td>
                                                <td><button className="btn-secondary" style={{ padding: "2px 6px", fontSize: 10 }} onClick={() => setMappings(mappings.filter((_, j) => j !== i))}>×</button></td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                            <div style={{ display: "flex", gap: 6 }}>
                                <button className="btn-secondary" onClick={addMappingRow}>+ Add Mapping</button>
                                {mappings.length > 0 && <button className="btn-primary" onClick={submitMappings}>Apply</button>}
                            </div>
                        </div>
                    </div>

                    {/* Right column */}
                    <div>
                        {/* Current Parameters */}
                        <div className="card" style={{ marginBottom: 12 }}>
                            <div style={{ fontSize: 11, fontWeight: 500, color: "#a1a1aa", marginBottom: 8 }}>Current Parameters</div>
                            <table>
                                <thead><tr><th>Parameter</th><th>Value</th></tr></thead>
                                <tbody>
                                    {Object.entries(parameters).map(([k, v]) => (
                                        <tr key={k}>
                                            <td style={{ fontFamily: "var(--font-mono)" }}>{k}</td>
                                            <td style={{ fontFamily: "var(--font-mono)" }}>{typeof v === 'number' ? v.toFixed(6) : String(v)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {/* Integrator Settings */}
                        <div className="card">
                            <div style={{ fontSize: 11, fontWeight: 500, color: "#a1a1aa", marginBottom: 8 }}>Integrator Settings</div>
                            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                                {Object.entries(intKwargs).map(([k, v]) => (
                                    <div key={k} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                        <label style={{ fontSize: 10, fontFamily: "var(--font-mono)", width: 50 }}>{k}</label>
                                        <input type="text" value={v} onChange={(e) => setIntKwargs({ ...intKwargs, [k]: e.target.value })} style={{ width: 100 }} />
                                    </div>
                                ))}
                                <div style={{ display: "flex", gap: 6 }}>
                                    <button className="btn-secondary" onClick={() => setIntKwargs({ ...intKwargs, [prompt("Key:") || ""]: "" })}>+ Add</button>
                                    <button className="btn-primary" onClick={updateIntegrator}>Update</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
