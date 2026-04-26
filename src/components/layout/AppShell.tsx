import { Link, NavLink, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { Activity, Map as MapIcon, Search, Settings, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { getStats } from "@/lib/api";

const NAV = [
  { to: "/", label: "Search", icon: Search, exact: true },
  { to: "/map", label: "Map", icon: MapIcon },
  { to: "/insights", label: "Insights", icon: BarChart3 },
  { to: "/admin", label: "Admin", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const loc = useLocation();
  const isFullWidth = ["/", "/results", "/map"].includes(loc.pathname);
  const [facilityCount, setFacilityCount] = useState<number>(0);

  useEffect(() => {
    const run = async () => {
      try {
        const stats = await getStats();
        setFacilityCount(Number(stats.total_facilities || 0));
      } catch {
        setFacilityCount(0);
      }
    };
    run();
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <header className={cn(
        "sticky top-0 z-50 bg-background/95 backdrop-blur-xl border-b border-border/80",
      )}>
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between gap-6 px-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
              <Activity className="h-5 w-5" strokeWidth={2.5} />
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-[18px] font-sans font-bold tracking-tight text-foreground">MediFind</span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-1 rounded-full bg-surface px-1.5 py-1.5 shadow-sm border border-border">
            {NAV.map(({ to, label, icon: Icon, exact }) => (
              <NavLink
                key={to}
                to={to}
                end={exact}
                className={({ isActive }) => cn(
                  "flex items-center gap-2 rounded-full px-5 py-2 text-[14px] font-medium transition-all duration-200",
                  isActive
                    ? "bg-surface-muted text-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-surface-muted/50"
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <span className="hidden sm:inline text-[12px] font-mono text-muted-foreground tracking-wide">
              {facilityCount} facilities indexed
            </span>
            <span className="inline-flex h-2 w-2 rounded-full bg-success shadow-[0_0_8px_rgba(16,185,129,0.5)]" title="System online" />
          </div>
        </div>
      </header>

      <main className={cn(isFullWidth ? "" : "mx-auto max-w-7xl px-4 sm:px-6 py-6")}>
        {children}
      </main>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 border-t border-border bg-background/95 backdrop-blur-xl">
        <div className="grid grid-cols-4">
          {NAV.map(({ to, label, icon: Icon, exact }) => (
            <NavLink key={to} to={to} end={exact}
              className={({ isActive }) => cn(
                "flex flex-col items-center gap-1 py-2.5 text-[10px] font-medium",
                isActive ? "text-accent" : "text-muted-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
