import { cn } from "@/lib/utils";

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn(
      "rounded-xl border bg-surface p-5 space-y-4 animate-pulse",
      className
    )}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2 flex-1">
          <div className="h-4 bg-surface-muted rounded w-3/4" />
          <div className="h-3 bg-surface-muted rounded w-1/3" />
        </div>
        <div className="h-6 w-16 bg-surface-muted rounded-md" />
      </div>

      {/* Capability chips */}
      <div className="flex flex-wrap gap-1.5">
        {[80, 64, 96, 72, 56].map((w, i) => (
          <div key={i} className="h-5 bg-surface-muted rounded-md" style={{ width: w }} />
        ))}
      </div>

      {/* Stats row */}
      <div className="flex gap-4">
        {[48, 40, 56].map((w, i) => (
          <div key={i} className="space-y-1">
            <div className="h-2.5 bg-surface-muted rounded" style={{ width: w }} />
            <div className="h-3 bg-surface-muted rounded w-8" />
          </div>
        ))}
      </div>

      {/* Source */}
      <div className="pt-2 border-t border-border space-y-1">
        <div className="h-3 bg-surface-muted rounded w-full" />
        <div className="h-3 bg-surface-muted rounded w-2/3" />
      </div>
    </div>
  );
}
