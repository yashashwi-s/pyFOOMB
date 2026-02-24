"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
    { href: "/", label: "Dashboard", icon: "◎" },
    { href: "/model", label: "Model", icon: "⬡" },
    { href: "/simulation", label: "Simulation", icon: "▸" },
    { href: "/data", label: "Data", icon: "◫" },
    { href: "/estimation", label: "Estimation", icon: "⊞" },
    { href: "/analysis", label: "Analysis", icon: "◇" },
    { href: "/replicates", label: "Replicates", icon: "⧉" },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <nav
            style={{
                width: 200,
                minHeight: "100vh",
                background: "#18181b",
                borderRight: "1px solid #27272a",
                display: "flex",
                flexDirection: "column",
                padding: "16px 0",
                flexShrink: 0,
            }}
        >
            {/* Logo */}
            <div style={{ padding: "0 16px 20px", borderBottom: "1px solid #27272a" }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: "#fafafa", letterSpacing: "-0.02em" }}>
                    pyFOOMB
                </div>
                <div style={{ fontSize: 10, color: "#71717a", marginTop: 2 }}>
                    Bioprocess Modelling
                </div>
            </div>

            {/* Workflow steps */}
            <div style={{ padding: "12px 0", flex: 1 }}>
                <div style={{ padding: "0 16px 8px", fontSize: 9, color: "#52525b", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 600 }}>
                    Workflow
                </div>
                {NAV.map((item, i) => {
                    const active = pathname === item.href;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 10,
                                padding: "7px 16px",
                                fontSize: 12,
                                color: active ? "#fafafa" : "#a1a1aa",
                                background: active ? "#27272a" : "transparent",
                                textDecoration: "none",
                                borderLeft: active ? "2px solid #3b82f6" : "2px solid transparent",
                                transition: "all 0.1s",
                            }}
                        >
                            <span style={{ fontSize: 13, width: 18, textAlign: "center", opacity: active ? 1 : 0.5 }}>
                                {item.icon}
                            </span>
                            <span>{item.label}</span>
                            {i > 0 && (
                                <span style={{
                                    marginLeft: "auto",
                                    fontSize: 9,
                                    color: "#52525b",
                                    fontFamily: "var(--font-mono)",
                                }}>
                                    {i}
                                </span>
                            )}
                        </Link>
                    );
                })}
            </div>

            {/* Footer */}
            <div style={{ padding: "12px 16px", borderTop: "1px solid #27272a", fontSize: 10, color: "#52525b" }}>
                v2.17.7
            </div>
        </nav>
    );
}
