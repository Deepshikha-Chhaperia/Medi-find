import { CAPABILITY_META } from "@/data/capabilities";
import { Capability } from "@/types/medifind";
import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

interface Props {
  capability: Capability;
  status?: "matched" | "available" | "missing";
  size?: "sm" | "md";
}

export function CapabilityChip({ capability, status = "available", size = "sm" }: Props) {
  const meta = CAPABILITY_META[capability];
  if (!meta) return null;

  return (
    <span className={cn(
      "inline-flex items-center gap-1 rounded-md border font-medium transition-colors",
      size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs",
      status === "matched" && "border-accent/30 bg-accent-soft text-accent",
      status === "available" && "border-border bg-surface-muted text-muted-foreground",
      status === "missing" && "border-destructive/30 bg-destructive/5 text-destructive line-through"
    )}>
      {status === "matched" && <Check className="h-2.5 w-2.5" strokeWidth={3} />}
      {meta.label}
    </span>
  );
}