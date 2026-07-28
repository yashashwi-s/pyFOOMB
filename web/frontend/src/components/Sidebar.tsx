"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
    LayoutDashboard,
    FlaskConical,
    Play,
    Database,
    Target,
    Activity,
    Copy,
    BookOpen,
    Menu,
    X,
    type LucideIcon,
} from "lucide-react";

interface NavItem {
    href: string;
    label: string;
    icon: LucideIcon;
}

const WORKFLOW: NavItem[] = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/model", label: "Model", icon: FlaskConical },
    { href: "/simulation", label: "Simulation", icon: Play },
    { href: "/data", label: "Data", icon: Database },
    { href: "/estimation", label: "Estimation", icon: Target },
    { href: "/analysis", label: "Analysis", icon: Activity },
    { href: "/replicates", label: "Replicates", icon: Copy },
];

const EXTRA: NavItem[] = [{ href: "/examples", label: "Examples", icon: BookOpen }];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
    const pathname = usePathname();

    function renderLink(item: NavItem, stepNum?: number) {
        const active = pathname === item.href;
        const Icon = item.icon;
        return (
            <Link
                key={item.href}
                href={item.href}
                onClick={onNavigate}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-2.5 border-l-2 px-4 py-[7px] text-xs no-underline transition-colors ${active
                        ? "border-accent bg-border text-foreground"
                        : "border-transparent text-muted hover:bg-card-hover hover:text-foreground"
                    }`}
            >
                <Icon size={14} strokeWidth={2} className={active ? "text-accent" : "text-subtle"} />
                <span>{item.label}</span>
                {stepNum !== undefined && (
                    <span className="ml-auto font-mono text-[9px] text-subtle">{stepNum}</span>
                )}
            </Link>
        );
    }

    return (
        <div className="flex-1 py-3">
            <div className="px-4 pb-2 text-[9px] font-semibold uppercase tracking-wider text-subtle">
                Workflow
            </div>
            {WORKFLOW.map((item, i) => renderLink(item, i === 0 ? undefined : i))}

            <div className="mx-4 my-2.5 border-t border-border" />

            <div className="px-4 pb-2 text-[9px] font-semibold uppercase tracking-wider text-subtle">
                Resources
            </div>
            {EXTRA.map((item) => renderLink(item))}
        </div>
    );
}

/** Desktop: persistent left rail. Mobile (<md): a top bar + slide-in drawer. */
export default function Sidebar() {
    const pathname = usePathname();
    const [open, setOpen] = useState(false);

    // Close the drawer whenever the route changes (adjusting state during
    // render, per React's guidance, rather than in a useEffect).
    const [lastPathname, setLastPathname] = useState(pathname);
    if (pathname !== lastPathname) {
        setLastPathname(pathname);
        setOpen(false);
    }

    return (
        <>
            {/* Mobile top bar */}
            <div className="sticky top-0 z-40 flex h-12 flex-shrink-0 items-center justify-between border-b border-border bg-card px-4 md:hidden">
                <div className="text-sm font-semibold tracking-tight text-foreground">pyFOOMB</div>
                <button
                    className="btn-ghost px-2 py-1.5"
                    aria-label={open ? "Close navigation menu" : "Open navigation menu"}
                    aria-expanded={open}
                    onClick={() => setOpen((v) => !v)}
                >
                    {open ? <X size={18} /> : <Menu size={18} />}
                </button>
            </div>

            {/* Mobile drawer + backdrop */}
            {open && (
                <div className="fixed inset-0 z-30 md:hidden">
                    <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
                    <nav className="absolute left-0 top-12 flex max-h-[calc(100vh-3rem)] w-[240px] flex-col overflow-y-auto border-r border-border bg-card py-2 shadow-2xl">
                        <NavLinks onNavigate={() => setOpen(false)} />
                        <div className="border-t border-border px-4 py-3 text-[10px] text-subtle">v2.17.7</div>
                    </nav>
                </div>
            )}

            {/* Desktop persistent rail */}
            <nav className="sticky top-0 hidden min-h-screen w-[200px] flex-shrink-0 flex-col border-r border-border bg-card py-4 md:flex">
                <div className="border-b border-border px-4 pb-5">
                    <div className="text-sm font-semibold tracking-tight text-foreground">pyFOOMB</div>
                    <div className="mt-0.5 text-[10px] text-subtle">Bioprocess Modelling</div>
                </div>
                <NavLinks />
                <div className="border-t border-border px-4 py-3 text-[10px] text-subtle">v2.17.7</div>
            </nav>
        </>
    );
}
