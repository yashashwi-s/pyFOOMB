import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { ReactNode } from "react";

type StatusType = "error" | "success" | "info" | "warning";

const STYLES: Record<StatusType, { bg: string; border: string; text: string; Icon: typeof Info }> = {
  error: { bg: "bg-error-soft", border: "border-error-border", text: "text-[#f5a3a3]", Icon: AlertTriangle },
  success: { bg: "bg-success-soft", border: "border-success-border", text: "text-[#7cd97c]", Icon: CheckCircle2 },
  warning: { bg: "bg-warning-soft", border: "border-warning-border", text: "text-[#e0ab4a]", Icon: AlertTriangle },
  info: { bg: "bg-card", border: "border-border", text: "text-muted", Icon: Info },
};

interface StatusMessageProps {
  type: StatusType;
  children: ReactNode;
  className?: string;
}

/** Inline banner for error / success / warning / info feedback — replaces raw hex-colored divs. */
export default function StatusMessage({ type, children, className = "" }: StatusMessageProps) {
  const s = STYLES[type];
  return (
    <div
      role={type === "error" ? "alert" : "status"}
      className={`flex items-start gap-2 rounded-lg border ${s.bg} ${s.border} px-3 py-2 text-xs leading-relaxed ${s.text} ${className}`}
    >
      <s.Icon size={14} className="mt-0.5 flex-shrink-0" strokeWidth={2} />
      <div className="min-w-0 break-words">{children}</div>
    </div>
  );
}
