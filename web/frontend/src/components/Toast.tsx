"use client";

import { useState, createContext, useContext, useCallback, ReactNode } from "react";
import { CheckCircle2, AlertTriangle, Info } from "lucide-react";

interface Toast {
    id: number;
    message: string;
    type: "info" | "success" | "error";
}

interface ToastContextValue {
    toast: (message: string, type?: "info" | "success" | "error") => void;
}

const ToastContext = createContext<ToastContextValue>({ toast: () => { } });

export function useToast() {
    return useContext(ToastContext);
}

const ICONS = { info: Info, success: CheckCircle2, error: AlertTriangle };

let _nextId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const addToast = useCallback((message: string, type: "info" | "success" | "error" = "info") => {
        const id = _nextId++;
        setToasts((prev) => [...prev, { id, message, type }]);
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, 3200);
    }, []);

    return (
        <ToastContext.Provider value={{ toast: addToast }}>
            {children}
            {/* Toast container — bottom-right */}
            <div className="pointer-events-none fixed bottom-5 right-5 z-[9999] flex flex-col gap-2">
                {toasts.map((t) => {
                    const Icon = ICONS[t.type];
                    return (
                        <div
                            key={t.id}
                            role="status"
                            className={`pointer-events-auto flex max-w-[340px] items-start gap-2 rounded-lg border px-4 py-2.5 text-xs leading-relaxed shadow-[0_4px_24px_rgba(0,0,0,0.4)] backdrop-blur-md ${t.type === "error"
                                    ? "border-error-border bg-error-soft text-[#fca5a5]"
                                    : t.type === "success"
                                        ? "border-success-border bg-success-soft text-[#86efac]"
                                        : "border-border-light bg-[#1c1c1e] text-[#d4d4d8]"
                                }`}
                            style={{
                                animation: "toast-in 0.25s ease-out, toast-out 0.3s ease-in 2.9s forwards",
                            }}
                        >
                            <Icon size={14} className="mt-0.5 flex-shrink-0" strokeWidth={2} />
                            <span>{t.message}</span>
                        </div>
                    );
                })}
            </div>
        </ToastContext.Provider>
    );
}
