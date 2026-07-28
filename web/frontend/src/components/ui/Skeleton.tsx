interface SkeletonProps {
  className?: string;
}

/** Shimmering placeholder block for content that is still loading. */
export function Skeleton({ className = "" }: SkeletonProps) {
  return <div className={`skeleton ${className}`} />;
}

/** A handful of skeleton rows, sized like a data table. */
export function SkeletonTable({ rows = 4, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-3">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-3">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

/** A skeleton shaped like a chart card — axis line + a few "bars". */
export function SkeletonChart({ height = 300 }: { height?: number }) {
  return (
    <div className="flex flex-col gap-3" style={{ height }}>
      <Skeleton className="h-full w-full" />
    </div>
  );
}
