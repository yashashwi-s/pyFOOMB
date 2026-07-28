import { ReactNode } from "react";
import { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
  compact?: boolean;
}

/** Helpful placeholder for a card/table/chart area that has no data yet. */
export default function EmptyState({ icon: Icon, title, description, action, compact = false }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center text-center ${compact ? "py-8" : "py-14"} px-6`}>
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-border/60 text-subtle">
        <Icon size={18} strokeWidth={1.75} />
      </div>
      <div className="text-xs font-medium text-muted">{title}</div>
      {description && <div className="mt-1 max-w-xs text-[11px] leading-relaxed text-subtle">{description}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
