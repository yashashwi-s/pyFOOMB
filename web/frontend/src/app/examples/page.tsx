"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/Toast";
import Math from "@/components/Math";
import { paramToTex } from "@/lib/paramToTex";
import PageHeader from "@/components/ui/PageHeader";

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
    unknowns: Record<string, [number, number]>;
    states: string[];
    /* Smart data generation profile */
    dataProfile: { n_points: number; noise_percent: number; abs_noise: number };
}

const EXAMPLES: Example[] = [
    {
        id: "ex01_modelling",
        title: "Sequential Kinetics A → B → C",
        source: "Example01_Modelling.ipynb",
        category: "Modelling Basics",
        description: "Sequential first-order kinetics. Species A converts to B, then B converts to C. Two rate constants k₁ and k₂ control the process.",
        equation: "\\frac{dA}{dt} = -k_1 A, \\quad \\frac{dB}{dt} = k_1 A - k_2 B, \\quad \\frac{dC}{dt} = k_2 B",
        template_id: "exponential_decay",
        model_parameters: { k: 0.2 },
        initial_values: { C0: 50.0 },
        t_end: 24,
        states: ["C"],
        unknowns: { k: [0.01, 1.0] },
        dataProfile: { n_points: 12, noise_percent: 3, abs_noise: 0.5 },
    },
    {
        id: "ex04_estimation",
        title: "Parameter Estimation (Exponential Decay)",
        source: "Example04_ParameterEstimation.ipynb",
        category: "Parameter Estimation",
        description: "Exponential decay with noisy synthetic data. Estimates k from measurement data using local / global optimization.",
        equation: "\\frac{dC}{dt} = -k \\cdot C, \\quad \\text{unknowns} = \\{k\\}",
        template_id: "exponential_decay",
        model_parameters: { k: 0.2 },
        initial_values: { C0: 50.0 },
        t_end: 24,
        states: ["C"],
        measurements: [
            { name: "C", timepoints: [0, 2, 4, 6, 8, 10, 14, 18, 24], values: [50.0, 33.5, 22.5, 15.1, 10.1, 6.8, 3.1, 1.4, 0.4] },
        ],
        unknowns: { k: [0.01, 1.0] },
        dataProfile: { n_points: 10, noise_percent: 5, abs_noise: 0.3 },
    },
    {
        id: "logistic_batch",
        title: "Logistic Batch Culture",
        source: "Model template",
        category: "Modelling Basics",
        description: "Growth with carrying capacity — biomass approaches a maximum value K. Common in batch cultures. Shows the characteristic S-curve.",
        equation: "\\frac{dX}{dt} = \\mu_{max} \\cdot X \\cdot \\left(1 - \\frac{X}{K}\\right)",
        template_id: "logistic_growth",
        model_parameters: { mu_max: 0.4, K: 8.0 },
        initial_values: { X0: 0.2 },
        t_end: 30,
        states: ["X"],
        measurements: [
            { name: "X", timepoints: [0, 3, 6, 9, 12, 15, 18, 21, 24, 27], values: [0.2, 0.42, 0.95, 2.1, 3.8, 5.5, 6.7, 7.3, 7.6, 7.8] },
        ],
        unknowns: { mu_max: [0.1, 1.0], K: [1.0, 20.0] },
        dataProfile: { n_points: 12, noise_percent: 4, abs_noise: 0.05 },
    },
    {
        id: "ex09_monod_growth",
        title: "Growth-Coupled Production (Monod)",
        source: "Example09_ParallelizedParameterEstimation.ipynb",
        category: "Parameter Estimation",
        description: "Monod growth with three states: Biomass X, Substrate S, Product P. Growth-coupled product formation. Used for parallel estimation.",
        equation: "\\mu = \\frac{\\mu_{max} \\cdot S}{K_S + S}, \\quad \\frac{dP}{dt} = Y_{PS} \\cdot \\mu \\cdot X",
        template_id: "monod_growth",
        model_parameters: { mu_max: 0.4, K_S: 0.05, Y_XS: 0.6, Y_PS: 0.4 },
        initial_values: { P0: 0.0, S0: 20.0, X0: 0.01 },
        t_end: 20,
        states: ["P", "S", "X"],
        measurements: [
            { name: "X", timepoints: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20], values: [0.01, 0.015, 0.024, 0.045, 0.10, 0.26, 0.75, 2.1, 4.8, 7.5, 9.2] },
            { name: "S", timepoints: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20], values: [20.0, 19.99, 19.98, 19.95, 19.85, 19.58, 18.75, 16.55, 12.0, 5.5, 1.2] },
            { name: "P", timepoints: [0, 4, 8, 12, 16, 20], values: [0.0, 0.005, 0.04, 0.30, 1.9, 3.6] },
        ],
        unknowns: { mu_max: [0.05, 1.5], K_S: [0.001, 1.0], Y_XS: [0.1, 1.0], Y_PS: [0.05, 1.0] },
        dataProfile: { n_points: 15, noise_percent: 5, abs_noise: 0.005 },
    },
    {
        id: "ex05_sensitivities",
        title: "Decay Kinetics — Sensitivity Analysis",
        source: "Example05_Sensitivities.ipynb",
        category: "Analysis",
        description: "Exponential decay for sensitivity analysis. Shows how each parameter influences each state over time via central difference quotients.",
        equation: "\\frac{dC}{dt} = -k \\cdot C, \\quad S_k(t) = \\frac{\\partial C(t)}{\\partial k}",
        template_id: "exponential_decay",
        model_parameters: { k: 0.2 },
        initial_values: { C0: 100.0 },
        t_end: 20,
        states: ["C"],
        unknowns: { k: [0.01, 1.0] },
        dataProfile: { n_points: 20, noise_percent: 2, abs_noise: 0.5 },
    },
    {
        id: "substrate_inhibition",
        title: "Substrate Inhibition (Andrews/Haldane)",
        source: "Model template",
        category: "Kinetic Models",
        description: "At low S, growth increases with S. At high S, growth is inhibited. Shows the bell-shaped µ(S) relationship. Common in toxic substrate fermentations.",
        equation: "\\mu = \\frac{\\mu_{max} \\cdot S}{K_S + S + \\frac{S^2}{K_I}}",
        template_id: "monod_inhibition",
        model_parameters: { mu_max: 0.6, K_S: 0.5, K_I: 20.0, Y_XS: 0.4, Y_PS: 0.2 },
        initial_values: { P0: 0.0, S0: 30.0, X0: 0.1 },
        t_end: 50,
        states: ["P", "S", "X"],
        unknowns: { mu_max: [0.1, 2.0], K_S: [0.01, 5.0], K_I: [1.0, 100.0] },
        dataProfile: { n_points: 18, noise_percent: 6, abs_noise: 0.02 },
    },
    {
        id: "fed_batch_pulse",
        title: "Fed-Batch with Pulse Feed",
        source: "Example07_FedBatchModels.ipynb",
        category: "Event Handling",
        description: "Monod growth with a pulse feed event at t=10h. Substrate depleted during batch phase, replenished on feeding. Demonstrates event handling.",
        equation: "\\text{At } t = t_{feed}: \\; S \\leftarrow \\frac{S V + S_f V_f}{V + V_f}, \\; V \\leftarrow V + V_f",
        template_id: "fed_batch_monod",
        model_parameters: { mu_max: 0.5, K_S: 0.1, Y_XS: 0.5, S_feed: 200.0, V_feed: 0.2, t_feed: 10.0 },
        initial_values: { S0: 10.0, V0: 1.0, X0: 0.5 },
        t_end: 24,
        states: ["S", "V", "X"],
        unknowns: { mu_max: [0.1, 2.0], K_S: [0.01, 1.0], Y_XS: [0.1, 1.0] },
        dataProfile: { n_points: 20, noise_percent: 4, abs_noise: 0.05 },
    },
    {
        id: "double_monod",
        title: "Co-Metabolism (Double Monod)",
        source: "Model template",
        category: "Kinetic Models",
        description: "Growth limited by two substrates simultaneously. Common in denitrification (C + N sources). Growth rate is the product of two saturation terms.",
        equation: "\\mu = \\mu_{max} \\cdot \\frac{S_1}{K_{S1} + S_1} \\cdot \\frac{S_2}{K_{S2} + S_2}",
        template_id: "double_monod",
        model_parameters: { mu_max: 0.35, K_S1: 0.5, K_S2: 1.0, Y_XS1: 0.5, Y_XS2: 0.3 },
        initial_values: { S10: 10.0, S20: 5.0, X0: 0.1 },
        t_end: 30,
        states: ["S1", "S2", "X"],
        unknowns: { mu_max: [0.1, 1.0], K_S1: [0.05, 5.0], K_S2: [0.1, 10.0] },
        dataProfile: { n_points: 15, noise_percent: 5, abs_noise: 0.03 },
    },
];

export default function ExamplesPage() {
    const router = useRouter();
    const { toast } = useToast();
    const [busy, setBusy] = useState<string | null>(null);

    const categories = [...new Set(EXAMPLES.map((e) => e.category))];

    /** Load example with hardcoded data (if any) */
    async function loadExample(ex: Example) {
        setBusy(ex.id);
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
            toast(`${ex.title} loaded`, "success");
            router.push("/simulation");
        } catch (e: unknown) {
            toast(e instanceof Error ? e.message : "Failed to load", "error");
        }
        setBusy(null);
    }

    /** Load example + generate smart synthetic data */
    async function loadWithData(ex: Example) {
        setBusy(`${ex.id}_gen`);
        try {
            const model = await api.createModel({
                template_id: ex.template_id,
                model_name: ex.title,
                model_parameters: ex.model_parameters,
                initial_values: ex.initial_values,
            });
            const dp = ex.dataProfile;
            await api.generateData(model.model_id, {
                t_end: ex.t_end,
                n_points: dp.n_points,
                noise_percent: dp.noise_percent,
                abs_noise: dp.abs_noise,
                seed: 42,
            });
            toast(`${ex.title} loaded with ${dp.n_points}-point synthetic data`, "success");
            router.push("/simulation");
        } catch (e: unknown) {
            toast(e instanceof Error ? e.message : "Failed to generate", "error");
        }
        setBusy(null);
    }

    const isBusy = (id: string) => busy === id || busy === `${id}_gen`;

    return (
        <div>
            <PageHeader title="Examples" description="Pre-configured scenarios from the pyFOOMB example notebooks." />

            <div className="hint-bar">
                Each card has two loading options — <strong>Load</strong> uses
                hardcoded reference data when available, while <strong>Load + Data</strong> generates
                noisy synthetic measurements tuned to the model&apos;s dynamics.
            </div>

            {categories.map((cat) => (
                <div key={cat} className="mb-5">
                    <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-subtle">
                        {cat}
                    </div>
                    <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
                        {EXAMPLES.filter((e) => e.category === cat).map((ex) => (
                            <div key={ex.id} className="card flex flex-col justify-between">
                                <div>
                                    <div className="mb-1.5 flex items-start justify-between">
                                        <span className="text-xs font-medium">{ex.title}</span>
                                        <div className="flex flex-shrink-0 gap-1">
                                            {ex.measurements && (
                                                <span className="rounded bg-accent-soft px-1.5 py-0.5 text-[8px] tracking-wide text-[#8ab4e8]">data</span>
                                            )}
                                            <span className="rounded bg-accent-soft px-1.5 py-0.5 text-[8px] tracking-wide text-[#8ab4e8]">fit</span>
                                        </div>
                                    </div>

                                    <div className="mb-1.5 font-mono text-[10px] text-faint">
                                        {ex.source}
                                    </div>

                                    <div className="mb-2 overflow-x-auto rounded px-2.5 py-1.5">
                                        <Math tex={ex.equation} display />
                                    </div>

                                    <p className="mb-2 text-[11px] leading-relaxed text-muted-2">{ex.description}</p>

                                    {/* Parameters */}
                                    <div className="mb-1 flex flex-wrap gap-1">
                                        {Object.entries(ex.model_parameters).map(([k, v]) => (
                                            <span key={k} className="inline-flex items-center gap-0.5 rounded bg-background px-1.5 py-0.5 text-[9px] text-muted-2">
                                                <Math tex={`${paramToTex(k)} = ${v}`} />
                                            </span>
                                        ))}
                                    </div>

                                    {/* Estimation bounds */}
                                    <div className="mb-2.5 flex flex-wrap gap-1">
                                        {Object.entries(ex.unknowns).map(([k, v]) => (
                                            <span key={k} className="inline-flex items-center rounded bg-background/60 px-1.5 py-0.5 text-[9px] text-subtle">
                                                <Math tex={`${paramToTex(k)} \\in [${v[0]},\\, ${v[1]}]`} />
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                {/* Footer */}
                                <div className="flex items-center justify-between border-t border-border pt-2.5">
                                    <span className="text-[10px] text-faint">
                                        t: 0–{ex.t_end}h · {ex.states.join(", ")}
                                    </span>
                                    <div className="flex gap-1">
                                        <button
                                            className="btn-secondary px-3 py-1 text-[10px]"
                                            onClick={() => loadWithData(ex)}
                                            disabled={isBusy(ex.id)}
                                            title={`Generate ${ex.dataProfile.n_points} noisy points (σ=${ex.dataProfile.noise_percent}%)`}
                                        >
                                            {busy === `${ex.id}_gen` ? <span className="spinner h-3 w-3 border" /> : "Load + Data"}
                                        </button>
                                        <button
                                            className="btn-primary px-3 py-1 text-[10px]"
                                            onClick={() => loadExample(ex)}
                                            disabled={isBusy(ex.id)}
                                        >
                                            {busy === ex.id ? <span className="spinner h-3 w-3 border" /> : "Load"}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}
