"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";
import Math from "@/components/Math";

interface Example {
    id: string;
    title: string;
    source: string;
    category: string;
    description: string;
    equation: string;
    template_id: string;
    model_parameters: Record<string, number>;
    initial_values: Record<string, number>;
    t_end: number;
    measurements?: Array<{ name: string; timepoints: number[]; values: number[] }>;
    unknowns?: Record<string, [number, number]>;
}

const EXAMPLES: Example[] = [
    // ── Example 01: Modelling ──
    {
        id: "ex01_modelling",
        title: "Sequential Kinetics A → B → C",
        source: "Example01_Modelling.ipynb",
        category: "Modelling Basics",
        description: "Sequential first-order kinetics from Example 01. Species A converts to B, then B converts to C. Two rate constants k₁ and k₂ control the process. Demonstrates basic Caretaker usage, forward simulation, and replicate management.",
        equation: "\\frac{dA}{dt} = -k_1 A, \\quad \\frac{dB}{dt} = k_1 A - k_2 B, \\quad \\frac{dC}{dt} = k_2 B",
        template_id: "exponential_decay",
        model_parameters: { k: 0.2 },
        initial_values: { C0: 50.0 },
        t_end: 24,
    },
    // ── Example 04: Parameter Estimation ──
    {
        id: "ex04_estimation",
        title: "Parameter Estimation (A → B → C)",
        source: "Example04_ParameterEstimation.ipynb",
        category: "Parameter Estimation",
        description: "From Example 04 — same sequential kinetics but with noisy synthetic data. Estimates k₁, k₂, and initial B₀ from 3 measurement series. Uses local optimization (scipy). Shows the typical estimation workflow: simulate → add noise → estimate → compare.",
        equation: "\\text{unknowns} = \\{k_1, k_2, B_0\\}, \\quad \\text{metric} = SS",
        template_id: "exponential_decay",
        model_parameters: { k: 0.2 },
        initial_values: { C0: 50.0 },
        t_end: 24,
        measurements: [
            { name: "C", timepoints: [0, 2, 4, 6, 8, 10, 14, 18, 24], values: [50.0, 33.5, 22.5, 15.1, 10.1, 6.8, 3.1, 1.4, 0.4] },
        ],
        unknowns: { k: [0.01, 1.0] },
    },
    // ── Example 05: Sensitivities ──
    {
        id: "ex05_sensitivities",
        title: "Complex Network Sensitivities",
        source: "Example05_Sensitivities.ipynb",
        category: "Analysis",
        description: "5-state reaction network from Example 05. Nine rate constants control interconversion between species A–E. Used to demonstrate sensitivity analysis: how each parameter influences each state over time via central difference quotients.",
        equation: "A \\xrightarrow{k_{AB}} B, \\quad A \\rightleftharpoons D, \\quad B \\rightleftharpoons D, \\quad B \\rightleftharpoons C, \\quad D \\to E, \\quad D \\to C",
        template_id: "exponential_decay",
        model_parameters: { k: 0.2 },
        initial_values: { C0: 100.0 },
        t_end: 20,
    },
    // ── Example 09: Parallel Estimation — Growth-Coupled Production ──
    {
        id: "ex09_monod_growth",
        title: "Growth-Coupled Production (Monod)",
        source: "Example09_ParallelizedParameterEstimation.ipynb",
        category: "Parameter Estimation",
        description: "Monod growth with growth-coupled product formation from Example 09. Parameters: µ_max=0.4, K_S=0.05, Y_XS=0.6, Y_PS=0.4, Y_PX=0.2. Uses parallel estimation (pygmo island model) with two replicates sharing kinetic parameters but differing in initial substrate.",
        equation: "\\mu = \\frac{\\mu_{max} \\cdot S}{K_S + S}, \\quad q_P = Y_{PX} \\cdot \\mu",
        template_id: "monod_growth",
        model_parameters: { mu_max: 0.4, K_S: 0.05, Y_XS: 0.6, Y_PS: 0.4 },
        initial_values: { P0: 0.0, S0: 20.0, X0: 0.01 },
        t_end: 20,
        measurements: [
            { name: "X", timepoints: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20], values: [0.01, 0.015, 0.024, 0.045, 0.10, 0.26, 0.75, 2.1, 4.8, 7.5, 9.2] },
            { name: "S", timepoints: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20], values: [20.0, 19.99, 19.98, 19.95, 19.85, 19.58, 18.75, 16.55, 12.0, 5.5, 1.2] },
            { name: "P", timepoints: [0, 4, 8, 12, 16, 20], values: [0.0, 0.005, 0.04, 0.30, 1.9, 3.6] },
        ],
        unknowns: { mu_max: [0.05, 1.5], K_S: [0.001, 1.0], Y_XS: [0.1, 1.0], Y_PS: [0.05, 1.0] },
    },
    // ── Logistic Growth ──
    {
        id: "logistic_batch",
        title: "Logistic Batch Culture",
        source: "Model template",
        category: "Modelling Basics",
        description: "Growth with carrying capacity — biomass approaches a maximum value K. Common in batch cultures where nutrients or space limit growth. Shows the characteristic S-curve dynamics.",
        equation: "\\frac{dX}{dt} = \\mu_{max} \\cdot X \\cdot \\left(1 - \\frac{X}{K}\\right)",
        template_id: "logistic_growth",
        model_parameters: { mu_max: 0.4, K: 8.0 },
        initial_values: { X0: 0.2 },
        t_end: 30,
        measurements: [
            { name: "X", timepoints: [0, 3, 6, 9, 12, 15, 18, 21, 24, 27], values: [0.2, 0.42, 0.95, 2.1, 3.8, 5.5, 6.7, 7.3, 7.6, 7.8] },
        ],
        unknowns: { mu_max: [0.1, 1.0], K: [1.0, 20.0] },
    },
    // ── Substrate Inhibition ──
    {
        id: "substrate_inhibition",
        title: "Substrate Inhibition (Andrews/Haldane)",
        source: "Model template",
        category: "Kinetic Models",
        description: "At low S, growth increases with S (Monod-like). At high S, growth is inhibited. Common in waste-water treatment and toxic substrate fermentations. Shows the bell-shaped µ(S) relationship.",
        equation: "\\mu = \\frac{\\mu_{max} \\cdot S}{K_S + S + \\frac{S^2}{K_I}}",
        template_id: "monod_inhibition",
        model_parameters: { mu_max: 0.6, K_S: 0.5, K_I: 20.0, Y_XS: 0.4, Y_PS: 0.2 },
        initial_values: { P0: 0.0, S0: 30.0, X0: 0.1 },
        t_end: 50,
    },
    // ── Fed-Batch Pulse Feed ──
    {
        id: "fed_batch_pulse",
        title: "Fed-Batch with Pulse Feed",
        source: "Example07_FedBatchModels.ipynb",
        category: "Event Handling",
        description: "From Example 07 — Monod growth with a single pulse feed event at t=10h. Substrate is depleted during batch phase, then replenished by concentrated feed. Volume and concentrations are adjusted upon feeding. Demonstrates pyFOOMB's event handling via state_events and change_states.",
        equation: "\\text{At } t = t_{feed}: \\quad S \\leftarrow \\frac{S \\cdot V + S_f \\cdot V_f}{V + V_f}, \\quad V \\leftarrow V + V_f",
        template_id: "fed_batch_monod",
        model_parameters: { mu_max: 0.5, K_S: 0.1, Y_XS: 0.5, S_feed: 200.0, V_feed: 0.2, t_feed: 10.0 },
        initial_values: { S0: 10.0, V0: 1.0, X0: 0.5 },
        t_end: 24,
    },
    // ── Double Monod ──
    {
        id: "double_monod",
        title: "Co-Metabolism (Double Monod)",
        source: "Model template",
        category: "Kinetic Models",
        description: "Growth limited by two substrates simultaneously. Common in co-metabolism, denitrification (carbon + nitrogen source), or microaerobic fermentation. Growth rate is the product of two saturation terms.",
        equation: "\\mu = \\mu_{max} \\cdot \\frac{S_1}{K_{S1} + S_1} \\cdot \\frac{S_2}{K_{S2} + S_2}",
        template_id: "double_monod",
        model_parameters: { mu_max: 0.35, K_S1: 0.5, K_S2: 1.0, Y_XS1: 0.5, Y_XS2: 0.3 },
        initial_values: { S10: 10.0, S20: 5.0, X0: 0.1 },
        t_end: 30,
    },
];

export default function ExamplesPage() {
    const router = useRouter();
    const [loading, setLoading] = useState<string | null>(null);
    const [result, setResult] = useState<{ id: string; example: string } | null>(null);
    const [error, setError] = useState("");

    const categories = [...new Set(EXAMPLES.map((e) => e.category))];

    async function loadExample(ex: Example) {
        setLoading(ex.id);
        setError("");
        setResult(null);

        try {
            const model = await api.createModel({
                template_id: ex.template_id,
                model_name: ex.title,
                model_parameters: ex.model_parameters,
                initial_values: ex.initial_values,
            });

            if (ex.measurements) {
                await api.addMeasurements(model.model_id, { measurements: ex.measurements });
            }

            setResult({ id: model.model_id, example: ex.title });
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to load example");
        }
        setLoading(null);
    }

    return (
        <div>
            <div style={{ marginBottom: 20 }}>
                <h1 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>Examples</h1>
                <p style={{ fontSize: 12, color: "#a1a1aa" }}>Pre-configured scenarios from the pyFOOMB example notebooks.</p>
            </div>

            <div className="hint-bar">
                Each example mirrors a scenario from the <strong style={{ color: "#fafafa" }}>pyFOOMB/examples/</strong> Jupyter notebooks.
                Click <strong style={{ color: "#fafafa" }}>Load</strong> to create the model with sample data, then navigate to Simulation or Estimation.
            </div>

            {result && (
                <div style={{ marginBottom: 16, padding: "10px 14px", background: "#052e16", border: "1px solid #166534", borderRadius: 6, fontSize: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span>
                        <span className="dot dot-green" />
                        <strong>{result.example}</strong> loaded — ID: <span style={{ fontFamily: "var(--font-mono)" }}>{result.id}</span>
                    </span>
                    <div style={{ display: "flex", gap: 6 }}>
                        <button className="btn-primary" style={{ fontSize: 11, padding: "4px 10px" }} onClick={() => router.push("/simulation")}>
                            ▸ Simulate
                        </button>
                        <button className="btn-secondary" style={{ fontSize: 11, padding: "4px 10px" }} onClick={() => router.push("/estimation")}>
                            ⊞ Estimate
                        </button>
                    </div>
                </div>
            )}

            {error && (
                <div style={{ marginBottom: 16, padding: "8px 12px", background: "#450a0a", border: "1px solid #991b1b", borderRadius: 6, fontSize: 11 }}>
                    <span className="dot dot-red" />{error}
                </div>
            )}

            {categories.map((cat) => (
                <div key={cat} style={{ marginBottom: 20 }}>
                    <div style={{ fontSize: 10, color: "#52525b", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 600, marginBottom: 8 }}>
                        {cat}
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10 }}>
                        {EXAMPLES.filter((e) => e.category === cat).map((ex) => (
                            <div key={ex.id} className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                                <div>
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                                        <span style={{ fontSize: 12, fontWeight: 500 }}>{ex.title}</span>
                                        <div style={{ display: "flex", gap: 4 }}>
                                            {ex.measurements && (
                                                <span style={{ fontSize: 9, padding: "1px 6px", background: "#052e16", color: "#22c55e", borderRadius: 3 }}>data</span>
                                            )}
                                            {ex.unknowns && (
                                                <span style={{ fontSize: 9, padding: "1px 6px", background: "#172554", color: "#3b82f6", borderRadius: 3 }}>fit</span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Source notebook */}
                                    <div style={{ fontSize: 10, color: "#52525b", fontFamily: "var(--font-mono)", marginBottom: 6 }}>
                                        {ex.source}
                                    </div>

                                    {/* Equation rendered with KaTeX */}
                                    <div style={{ marginBottom: 8, padding: "6px 10px", borderRadius: 4, overflowX: "auto" }}>
                                        <Math tex={ex.equation} display />
                                    </div>

                                    <p style={{ fontSize: 11, color: "#71717a", lineHeight: 1.6, marginBottom: 10 }}>{ex.description}</p>

                                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
                                        {Object.entries(ex.model_parameters).map(([k, v]) => (
                                            <span key={k} style={{ fontSize: 9, fontFamily: "var(--font-mono)", padding: "2px 6px", background: "#27272a", borderRadius: 3, color: "#a1a1aa" }}>
                                                {k}={v}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                    <span style={{ fontSize: 10, color: "#52525b" }}>
                                        t: 0 → {ex.t_end}h
                                        {ex.measurements ? ` · ${ex.measurements.length} series` : ""}
                                    </span>
                                    <button
                                        className="btn-primary"
                                        style={{ fontSize: 10, padding: "4px 12px" }}
                                        onClick={() => loadExample(ex)}
                                        disabled={loading === ex.id}
                                    >
                                        {loading === ex.id ? <span className="spinner" /> : "Load"}
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}
