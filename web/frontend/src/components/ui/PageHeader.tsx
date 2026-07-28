import { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

/** Consistent page title + subtitle block, used at the top of every page. */
export default function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="mb-5 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-base font-semibold text-foreground tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-xs text-muted-2">{description}</p>}
      </div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  );
}
