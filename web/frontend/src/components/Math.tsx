"use client";

import { useEffect, useRef } from "react";
import katex from "katex";

interface MathProps {
    tex: string;
    display?: boolean;
}

export default function Math({ tex, display = false }: MathProps) {
    const ref = useRef<HTMLSpanElement>(null);

    useEffect(() => {
        if (ref.current) {
            katex.render(tex, ref.current, {
                throwOnError: false,
                displayMode: display,
            });
        }
    }, [tex, display]);

    return <span ref={ref} />;
}
