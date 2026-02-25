"use client";

import { useState, useEffect, createContext, useContext, useCallback, ReactNode } from "react";

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
            <div style={{
                position: "fixed", bottom: 20, right: 20, zIndex: 9999,
                display: "flex", flexDirection: "column", gap: 8,
                pointerEvents: "none",
            }}>
                {toasts.map((t) => (
                    <div
                        key={t.id}
                        style={{
                            padding: "10px 16px",
                            borderRadius: 8,
                            fontSize: 12,
                            fontFamily: "var(--font-sans)",
                            fontWeight: 400,
                            color: t.type === "error" ? "#fca5a5" : "#d4d4d8",
                            background: t.type === "error" ? "#1c1012" : "#1c1c1e",
                            border: `1px solid ${t.type === "error" ? "#3f1418" : "#2e2e32"}`,
                            backdropFilter: "blur(12px)",
                            boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
                            animation: "toast-in 0.25s ease-out, toast-out 0.3s ease-in 2.9s forwards",
                            maxWidth: 340,
                            lineHeight: 1.5,
                            pointerEvents: "auto",
                        }}
                    >
                        {t.message}
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
}
