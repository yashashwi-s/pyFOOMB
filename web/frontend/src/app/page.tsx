"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Link from "next/link";
import {
  LayoutDashboard,
  FlaskConical,
  Play,
  Database,
  Target,
  Activity,
  Copy,
  Trash2,
  type LucideIcon,
} from "lucide-react";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonTable } from "@/components/ui/Skeleton";

interface ModelInfo {
  id: string;
  name: string;
  states: string[];
  parameters: string[];
  has_observations: boolean;
  has_measurements: boolean;
}

interface WorkflowCard {
  href: string;
  step: number;
  title: string;
  desc: string;
  icon: LucideIcon;
}

const WORKFLOW_CARDS: WorkflowCard[] = [
  { href: "/model", step: 1, title: "Define Model", desc: "Select a bioprocess template and configure parameters", icon: FlaskConical },
  { href: "/simulation", step: 2, title: "Simulate", desc: "Run forward simulations and explore dynamics", icon: Play },
  { href: "/data", step: 3, title: "Upload Data", desc: "Add experimental measurements for calibration", icon: Database },
  { href: "/estimation", step: 4, title: "Estimate", desc: "Fit model parameters to measurement data", icon: Target },
  { href: "/analysis", step: 5, title: "Analyze", desc: "Sensitivity analysis and parameter uncertainties", icon: Activity },
  { href: "/replicates", step: 6, title: "Replicates", desc: "Multi-reactor parameter mapping", icon: Copy },
];

export default function Dashboard() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    api.health()
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false));
    api.getModels().then((r) => { setModels(r.models); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="pyFOOMB — Python Framework for Object Oriented Modelling of Bioprocesses"
      />

      {/* Status */}
      <div className="card mb-4 flex flex-wrap items-center gap-6">
        <div className="flex items-center gap-1.5 text-xs">
          <span className={`dot ${backendOk === null ? "dot-yellow" : backendOk ? "dot-green" : "dot-red"}`} />
          Backend {backendOk === null ? "connecting…" : backendOk ? "connected" : "offline"}
        </div>
        <div className="text-xs text-muted-2">
          {loading ? "…" : models.length} active model{models.length !== 1 ? "s" : ""}
        </div>
      </div>

      {backendOk === false && (
        <div className="hint-bar border-error-border bg-error-soft text-[#f5a3a3]">
          Could not reach the backend API at <code className="font-mono">localhost:8000</code>. Start it with{" "}
          <code className="font-mono">uvicorn main:app --reload</code> from <code className="font-mono">web/backend</code>, then reload this page.
        </div>
      )}

      {/* Quick start */}
      <div className="hint-bar">
        <strong>Getting started:</strong>{" "}
        Go to <Link href="/model">Model</Link> to select a bioprocess template, then{" "}
        <Link href="/simulation">Simulate</Link> to run it forward in time.
        Upload experimental data in <Link href="/data">Data</Link>, and
        fit parameters in <Link href="/estimation">Estimation</Link>.
      </div>

      {/* Workflow cards */}
      <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {WORKFLOW_CARDS.map((item) => (
          <Link key={item.href} href={item.href} className="no-underline text-inherit">
            <div className="card flex min-h-[92px] cursor-pointer flex-col gap-1.5">
              <div className="flex items-center gap-2">
                <item.icon size={14} className="text-accent" strokeWidth={2} />
                <span className="text-xs font-medium text-foreground">
                  {item.step}. {item.title}
                </span>
              </div>
              <p className="text-[11px] leading-relaxed text-muted-2">{item.desc}</p>
            </div>
          </Link>
        ))}
      </div>

      {/* Active models */}
      <div>
        <h2 className="mb-2 text-sm font-medium text-foreground">Active Models</h2>
        {loading ? (
          <div className="card">
            <SkeletonTable rows={3} cols={6} />
          </div>
        ) : models.length > 0 ? (
          <div className="card overflow-x-auto p-0">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>States</th>
                  <th>Parameters</th>
                  <th>Data</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {models.map((m) => (
                  <tr key={m.id}>
                    <td className="text-muted-2">{m.id}</td>
                    <td>{m.name}</td>
                    <td>{m.states.join(", ")}</td>
                    <td>{m.parameters.length}</td>
                    <td>
                      <span className={`dot ${m.has_measurements ? "dot-green" : "dot-gray"}`} />
                      {m.has_measurements ? "Yes" : "No"}
                    </td>
                    <td>
                      <button
                        className="btn-danger px-2 py-1 text-[10px]"
                        disabled={deletingId === m.id}
                        onClick={(e) => {
                          e.preventDefault();
                          setDeletingId(m.id);
                          api.deleteModel(m.id)
                            .then(() => setModels((prev) => prev.filter((x) => x.id !== m.id)))
                            .finally(() => setDeletingId(null));
                        }}
                      >
                        <Trash2 size={11} />
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="card">
            <EmptyState
              icon={LayoutDashboard}
              title="No models yet"
              description="Define a bioprocess model to get started, or load a ready-made scenario from Examples."
              action={
                <div className="flex gap-2">
                  <Link href="/model" className="btn-primary">Define a model</Link>
                  <Link href="/examples" className="btn-secondary">Browse examples</Link>
                </div>
              }
            />
          </div>
        )}
      </div>
    </div>
  );
}
