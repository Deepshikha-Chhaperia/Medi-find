import { cn } from "@/lib/utils";

export function ConfidenceDot({ score, label }: { score: number; label?: string }) {
  const level = score >= 0.75 ? "high" : score >= 0.5 ? "med" : "low";
  const colors = {
    high: "bg-success",
    med: "bg-warning",
    low: "bg-destructive",
  };
  const labels = { high: "High match", med: "Medium match", low: "Low match" };
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
      <span className={cn("h-1.5 w-1.5 rounded-full", colors[level])} />
      <span>{label ?? labels[level]} · {Math.round(score * 100)}%</span>
    </span>
  );
}