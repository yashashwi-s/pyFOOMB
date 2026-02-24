"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Link from "next/link";

interface ModelInfo {
  id: string;
  name: string;
  states: string[];
  parameters: string[];
  has_observations: boolean;
  has_measurements: boolean;
}

export default function Dashboard() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [backendOk, setBackendOk] = useState(false);

  useEffect(() => {
    fetch("http://localhost:8000/api/health")
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false));
    api.getModels().then((r) => { setModels(r.models); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>Dashboard</h1>
        <p style={{ fontSize: 12, color: "#a1a1aa" }}>
          pyFOOMB — Python Framework for Object Oriented Modelling of Bioprocesses
        </p>
      </div>

      {/* Status */}
      <div className="card" style={{ marginBottom: 16, display: "flex", gap: 24, alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
          <span className={`dot ${backendOk ? "dot-green" : "dot-red"}`} />
          Backend {backendOk ? "connected" : "offline"}
        </div>
        <div style={{ fontSize: 12, color: "#71717a" }}>
          {models.length} active model{models.length !== 1 ? "s" : ""}
        </div>
      </div>

      {/* Quick start */}
      <div className="hint-bar">
        <strong style={{ color: "#fafafa" }}>Getting started:</strong>{" "}
        Go to <Link href="/model" style={{ color: "#3b82f6", textDecoration: "none" }}>Model</Link> to select a bioprocess template, then{" "}
        <Link href="/simulation" style={{ color: "#3b82f6", textDecoration: "none" }}>Simulate</Link> to run it forward in time.
        Upload experimental data in <Link href="/data" style={{ color: "#3b82f6", textDecoration: "none" }}>Data</Link>, and
        fit parameters in <Link href="/estimation" style={{ color: "#3b82f6", textDecoration: "none" }}>Estimation</Link>.
      </div>

      {/* Workflow cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 24 }}>
        {[
          { href: "/model", title: "1. Define Model", desc: "Select a bioprocess template and configure parameters", icon: "⬡" },
          { href: "/simulation", title: "2. Simulate", desc: "Run forward simulations and explore dynamics", icon: "▸" },
          { href: "/data", title: "3. Upload Data", desc: "Add experimental measurements for calibration", icon: "◫" },
          { href: "/estimation", title: "4. Estimate", desc: "Fit model parameters to measurement data", icon: "⊞" },
          { href: "/analysis", title: "5. Analyze", desc: "Sensitivity analysis and parameter uncertainties", icon: "◇" },
          { href: "/replicates", title: "6. Replicates", desc: "Multi-reactor parameter mapping", icon: "⧉" },
        ].map((item) => (
          <Link key={item.href} href={item.href} style={{ textDecoration: "none", color: "inherit" }}>
            <div className="card" style={{ cursor: "pointer", minHeight: 80 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <span style={{ fontSize: 14 }}>{item.icon}</span>
                <span style={{ fontSize: 12, fontWeight: 500, color: "#fafafa" }}>{item.title}</span>
              </div>
              <p style={{ fontSize: 11, color: "#71717a", lineHeight: 1.5 }}>{item.desc}</p>
            </div>
          </Link>
        ))}
      </div>

      {/* Active models */}
      {models.length > 0 && (
        <div>
          <h2 style={{ fontSize: 13, fontWeight: 500, marginBottom: 8 }}>Active Models</h2>
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
                  <td style={{ color: "#71717a" }}>{m.id}</td>
                  <td>{m.name}</td>
                  <td>{m.states.join(", ")}</td>
                  <td>{m.parameters.length}</td>
                  <td>
                    <span className={`dot ${m.has_measurements ? "dot-green" : "dot-gray"}`} />
                    {m.has_measurements ? "Yes" : "No"}
                  </td>
                  <td>
                    <button className="btn-danger" style={{ padding: "3px 8px", fontSize: 10 }} onClick={(e) => {
                      e.preventDefault();
                      api.deleteModel(m.id).then(() => setModels((prev) => prev.filter((x) => x.id !== m.id)));
                    }}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {loading && <div style={{ textAlign: "center", padding: 40 }}><span className="spinner" /></div>}
    </div>
  );
}
