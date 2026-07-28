"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import MathTex from "@/components/Math";
import { paramToTex } from "@/lib/paramToTex";
import { Copy, X } from "lucide-react";
import PageHeader from "@/components/ui/PageHeader";
import StatusMessage from "@/components/ui/StatusMessage";
import EmptyState from "@/components/ui/EmptyState";

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
        if (!id) { setReplicateIds([]); setParameters({}); return; }
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

    function addIntegratorKey() {
        const key = prompt("Key:");
        if (key) setIntKwargs({ ...intKwargs, [key]: "" });
    }

    return (
        <div>
            <PageHeader title="Replicates & Settings" description="Multi-reactor parameter mapping and integrator configuration." />

            <div className="hint-bar">
                For experiments with multiple reactors or conditions, use replicates to share model structure
                while allowing parameter variation. Map global parameters (shared, e.g. µ_max) to local names
                (reactor-specific, e.g. initial biomass per reactor).
            </div>

            {/* Model selector */}
            <div className="card mb-4">
                <label className="mb-1 block text-[10px] text-muted-2">Model</label>
                <select value={modelId} onChange={(e) => loadModel(e.target.value)} className="w-[200px]">
                    <option value="">Select model...</option>
                    {models.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.id})</option>)}
                </select>
            </div>

            {error && (
                <div className="mb-3">
                    <StatusMessage type="error">{error}</StatusMessage>
                </div>
            )}
            {message && (
                <div className="mb-3">
                    <StatusMessage type="success">{message}</StatusMessage>
                </div>
            )}

            {!modelId && (
                <div className="card">
                    <EmptyState icon={Copy} title="No model selected" description="Select a model above to manage replicates, parameter mappings, and integrator settings." />
                </div>
            )}

            {modelId && (
                <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                    {/* Left column */}
                    <div>
                        {/* Replicates */}
                        <div className="card mb-3">
                            <div className="mb-2 text-[11px] font-medium text-muted">Replicates</div>
                            <div className="mb-2 flex flex-wrap gap-1.5">
                                {replicateIds.length === 0 && <span className="text-[11px] text-subtle">No replicates yet</span>}
                                {replicateIds.map((rid, i) => (
                                    <span key={i} className={`rounded bg-border px-2 py-0.5 font-mono text-[10px] ${rid === null ? "text-subtle" : "text-foreground"}`}>
                                        {rid === null ? "(single)" : rid}
                                    </span>
                                ))}
                            </div>
                            <div className="flex gap-1.5">
                                <input type="text" placeholder="Replicate ID" value={newRepId} onChange={(e) => setNewRepId(e.target.value)} className="w-[140px]" />
                                <button className="btn-secondary" onClick={addReplicate}>Add</button>
                            </div>
                        </div>

                        {/* Parameter Mappings */}
                        <div className="card mb-3">
                            <div className="mb-2 text-[11px] font-medium text-muted">Parameter Mappings</div>
                            {mappings.length > 0 && (
                                <div className="mb-2 overflow-x-auto">
                                    <table>
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
                                                    <td><input type="text" value={m.replicate_id} onChange={(e) => { const n = [...mappings]; n[i].replicate_id = e.target.value; setMappings(n); }} className="w-[70px]" /></td>
                                                    <td><input type="text" value={m.global_name} onChange={(e) => { const n = [...mappings]; n[i].global_name = e.target.value; setMappings(n); }} className="w-[70px]" /></td>
                                                    <td><input type="text" value={m.local_name} onChange={(e) => { const n = [...mappings]; n[i].local_name = e.target.value; setMappings(n); }} className="w-[70px]" /></td>
                                                    <td><input type="text" value={m.value} onChange={(e) => { const n = [...mappings]; n[i].value = e.target.value; setMappings(n); }} className="w-[60px]" /></td>
                                                    <td>
                                                        <button className="btn-secondary px-1.5 py-0.5 text-[10px]" onClick={() => setMappings(mappings.filter((_, j) => j !== i))}>
                                                            <X size={11} />
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                            <div className="flex gap-1.5">
                                <button className="btn-secondary" onClick={addMappingRow}>+ Add Mapping</button>
                                {mappings.length > 0 && <button className="btn-primary" onClick={submitMappings}>Apply</button>}
                            </div>
                        </div>
                    </div>

                    {/* Right column */}
                    <div>
                        {/* Current Parameters */}
                        <div className="card mb-3">
                            <div className="mb-2 text-[11px] font-medium text-muted">Current Parameters</div>
                            {Object.keys(parameters).length === 0 ? (
                                <div className="text-[11px] text-subtle">No parameters found for this model.</div>
                            ) : (
                                <table>
                                    <thead><tr><th>Parameter</th><th>Value</th></tr></thead>
                                    <tbody>
                                        {Object.entries(parameters).map(([k, v]) => (
                                            <tr key={k}>
                                                <td><MathTex tex={paramToTex(k)} /></td>
                                                <td className="font-mono">{typeof v === 'number' ? v.toFixed(6) : String(v)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>

                        {/* Integrator Settings */}
                        <div className="card">
                            <div className="mb-2 text-[11px] font-medium text-muted">Integrator Settings</div>
                            <div className="flex flex-col gap-1.5">
                                {Object.entries(intKwargs).map(([k, v]) => (
                                    <div key={k} className="flex items-center gap-1.5">
                                        <label className="w-[50px] text-[10px]"><MathTex tex={paramToTex(k)} /></label>
                                        <input type="text" value={v} onChange={(e) => setIntKwargs({ ...intKwargs, [k]: e.target.value })} className="w-[100px]" />
                                    </div>
                                ))}
                                <div className="flex gap-1.5">
                                    <button className="btn-secondary" onClick={addIntegratorKey}>+ Add</button>
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
