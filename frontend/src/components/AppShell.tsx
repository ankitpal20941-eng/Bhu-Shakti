import { useEffect, useMemo, type ReactNode } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Activity, AlertTriangle, BarChart3, Bell, BookOpenCheck, ChevronDown, CloudRain, Compass, Database, FlaskConical,
  History, Hospital, LayoutDashboard, LogOut, Map, Menu, Moon, RadioTower, Satellite, Scale, ShieldAlert,
  ShieldCheck, Smartphone, Sun, TrendingDown, Users, WifiOff, X, Zap,
} from "lucide-react";
import clsx from "clsx";
import { api } from "../lib/api";
import { useSession } from "../store/session";
import { applyTheme, useUi } from "../store/ui";
import { useFallbackPolling, useLiveUpdates } from "../hooks/useLiveUpdates";
import { Toaster } from "./ui";
import { BhuShaktiLogo } from "./BhuShaktiLogo";
import { ROLE_HOMES } from "../lib/roles";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  Avatar,
  AvatarFallback,
  Badge,
} from "./shadcn";

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  permission?: string;
  end?: boolean;
}

const NAV: Array<{ group: string; items: NavItem[] }> = [
  {
    group: "Operations & Command",
    items: [
      { to: "/", label: "Command Center", icon: <LayoutDashboard size={16} />, end: true, permission: "risk:read" },
      { to: "/situation-room", label: "Situation Room", icon: <ShieldAlert size={16} />, permission: "risk:read" },
      { to: "/map", label: "Live Risk Map", icon: <Map size={16} />, permission: "risk:read" },
      { to: "/response", label: "Response Center", icon: <Activity size={16} />, permission: "response:read" },
      { to: "/field-teams", label: "Field Teams Cadre", icon: <Users size={16} />, permission: "teams:read" },
      { to: "/alerts", label: "Alerts", icon: <AlertTriangle size={16} />, permission: "alerts:read" },
      { to: "/notification-monitor", label: "Notification Monitor", icon: <Bell size={16} />, permission: "notifications:read" },
    ],
  },
  {
    group: "Disaster Intelligence",
    items: [
      { to: "/impact-analysis", label: "Impact Analysis", icon: <Compass size={16} />, permission: "risk:read" },
      { to: "/rainfall-intelligence", label: "Rainfall Intelligence", icon: <CloudRain size={16} />, permission: "weather:read" },
      { to: "/runout-analysis", label: "Runout Envelopes", icon: <TrendingDown size={16} />, permission: "runout:read" },
      { to: "/satellite-change", label: "Satellite Change", icon: <Satellite size={16} />, permission: "satellite:read" },
      { to: "/historical-replay", label: "Historical Replay", icon: <History size={16} />, permission: "replay:read" },
      { to: "/district-comparison", label: "District Comparison", icon: <Scale size={16} /> },
      { to: "/analytics", label: "Analytics", icon: <BarChart3 size={16} />, permission: "analytics:read" },
      { to: "/scenarios", label: "Scenario Lab", icon: <FlaskConical size={16} />, permission: "scenarios:run" },
    ],
  },
  {
    group: "Facilities & Governance",
    items: [
      { to: "/emergency-facilities", label: "Emergency Facilities", icon: <Hospital size={16} />, permission: "facilities:read" },
      { to: "/data-confidence", label: "Data Confidence", icon: <ShieldCheck size={16} />, permission: "quality:read" },
      { to: "/model-monitoring", label: "Model Fairness", icon: <BookOpenCheck size={16} />, permission: "models:read" },
      { to: "/data-health", label: "Data Health", icon: <Database size={16} />, permission: "sources:read" },
      { to: "/field", label: "Field Operations", icon: <Smartphone size={16} />, permission: "reports:create" },
      { to: "/citizen", label: "Citizen Portal", icon: <ShieldCheck size={16} /> },
      { to: "/admin", label: "Administration", icon: <Users size={16} />, permission: "admin:read" },
    ],
  },
];

function LiveIndicator() {
  const status = useUi((s) => s.liveStatus);
  const label = status === "live" ? "Live updates" : status === "connecting" ? "Connecting" : "Live updates paused";
  return (
    <span
      className={clsx("chip", status === "live" ? "border-safe/40 text-safe" : status === "paused" ? "border-watch/50 text-watch" : "border-line text-muted")}
      title={status === "paused" ? "The event stream is unavailable. Data refreshes every 60 seconds." : "Server-Sent Events connected"}
    >
      <RadioTower size={12} />
      {label}
    </span>
  );
}

export function AppShell() {
  const { user, permissions, clear } = useSession();
  const { theme, toggleTheme, lowBandwidth, setLowBandwidth, sidebarOpen, setSidebarOpen } = useUi();
  const live = useUi((s) => s.liveStatus);
  const navigate = useNavigate();
  useLiveUpdates();

  useEffect(() => applyTheme(theme), [theme]);

  useEffect(() => {
    if (user?.role === "citizen" && (window.location.pathname === "/" || window.location.pathname === "/map" || window.location.pathname === "/situation-room")) {
      navigate("/citizen", { replace: true });
    }
  }, [user?.role, navigate]);

  // Keeps screens fresh when SSE is unavailable (LIVE UPDATES PAUSED contract).
  useQuery({
    queryKey: ["stream-fallback"],
    queryFn: () => api("/api/v1/health"),
    ...useFallbackPolling(live === "paused"),
  });

  const jurisdiction = useMemo(() => {
    if (!user) return "";
    if (user.statewide) return "Statewide scope";
    if (user.districts.length === 0) return user.role_label;
    return user.districts.join(", ");
  }, [user]);

  const items = NAV.map((group) => ({
    ...group,
    items: group.items.filter((item) => !item.permission || permissions.includes(item.permission)),
  })).filter((group) => group.items.length > 0);

  const logout = async () => {
    try {
      await api("/api/v1/auth/logout", { method: "POST" });
    } catch {
      /* cookie may already be gone */
    }
    clear();
    navigate("/login");
  };

  return (
    <div className="flex min-h-full flex-col">
      <div className="flex flex-1">
        <aside
          className={clsx(
            "no-print fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col border-r border-line/80 bg-surface/90 dark:bg-[#121614]/90 backdrop-blur-2xl transition-transform lg:static lg:translate-x-0 shadow-sm",
            sidebarOpen ? "translate-x-0" : "-translate-x-full",
          )}
          aria-label="Primary navigation"
        >
          <div className="flex items-center justify-between gap-2 border-b border-line/80 px-4 py-3.5">
            <BhuShaktiLogo size={36} />
            <button className="btn btn-ghost btn-sm lg:hidden" onClick={() => setSidebarOpen(false)} aria-label="Close navigation">
              <X size={16} />
            </button>
          </div>

          <nav className="flex-1 overflow-y-auto px-3 py-3 space-y-4">
            {user?.role && ROLE_HOMES[user.role] && (
              <div className="mb-2 p-2 rounded-2xl bg-forest/10 dark:bg-forest/20 border border-forest/30">
                <div className="px-1 pb-1 text-[10px] font-bold uppercase tracking-[0.14em] text-forest">
                  Your Primary Duty Workspace
                </div>
                <NavLink
                  to={ROLE_HOMES[user.role].route}
                  className={({ isActive }) =>
                    clsx(
                      "flex items-center gap-2 rounded-xl px-2.5 py-1.5 text-xs font-semibold transition-all duration-200",
                      isActive
                        ? "bg-forest text-white shadow-sm"
                        : "text-ink hover:bg-forest/15"
                    )
                  }
                  onClick={() => setSidebarOpen(false)}
                >
                  <ShieldCheck size={15} className="shrink-0 text-forest" />
                  <span className="truncate">{ROLE_HOMES[user.role].label}</span>
                </NavLink>
              </div>
            )}

            {items.map((group) => (
              <div key={group.group}>
                <div className="px-2 pb-1.5 text-[11px] font-bold uppercase tracking-[0.14em] text-muted/80">{group.group}</div>
                <div className="space-y-1">
                  {group.items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.end}
                      className={({ isActive }) =>
                        clsx(
                          "flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-medium transition-all duration-200",
                          isActive
                            ? "bg-forest/10 text-forest dark:bg-forest/20 dark:text-emerald-400 font-semibold shadow-sm border border-forest/20"
                            : "text-muted hover:text-ink hover:bg-surface-2/70"
                        )
                      }
                      onClick={() => setSidebarOpen(false)}
                    >
                      {item.icon}
                      <span className="truncate">{item.label}</span>
                    </NavLink>
                  ))}
                </div>
              </div>
            ))}
          </nav>

          <div className="border-t border-line/80 p-3 bg-surface-2/40">
            <div className="p-2.5 rounded-xl bg-surface/80 border border-line text-[11px] space-y-1">
              <div className="flex items-center justify-between text-muted">
                <span className="font-semibold uppercase tracking-wider text-[10px]">Active Kernel</span>
                <span className="font-mono text-forest font-bold">v0.9.0</span>
              </div>
              <div className="mono font-semibold text-ink truncate">suscept-v0.1+trigger-v0.1</div>
              <div className="text-[10px] text-muted">Deterministic decision support</div>
            </div>
          </div>
        </aside>

        {sidebarOpen ? <button className="fixed inset-0 z-40 bg-charcoal/40 lg:hidden backdrop-blur-sm" onClick={() => setSidebarOpen(false)} aria-label="Close navigation overlay" /> : null}

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="no-print sticky top-0 z-40 flex min-h-[58px] items-center gap-3 border-b border-line/80 bg-white/95 dark:bg-[#121614]/95 px-4 backdrop-blur-2xl shadow-sm">
            <button className="btn btn-ghost btn-sm lg:hidden" onClick={() => setSidebarOpen(true)} aria-label="Open navigation">
              <Menu size={18} />
            </button>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2.5">
                <span className="truncate text-sm font-bold tracking-tight text-ink">{jurisdiction}</span>
              </div>
            </div>
            <div className="hidden items-center gap-2 md:flex">
              <LiveIndicator />
              <button
                className={clsx("btn btn-sm rounded-xl text-xs", lowBandwidth && "border-watch/50 text-watch")}
                onClick={() => setLowBandwidth(!lowBandwidth)}
                aria-pressed={lowBandwidth}
                title="Low-bandwidth mode: no basemap tiles, fewer effects"
              >
                {lowBandwidth ? <WifiOff size={14} /> : <Zap size={14} />}
                {lowBandwidth ? "Low data" : "Full"}
              </button>
            </div>
            <button className="btn btn-ghost btn-sm rounded-xl" onClick={toggleTheme} aria-label="Toggle colour theme">
              {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
            </button>
            <DropdownMenu>
              <DropdownMenuTrigger>
                <button
                  type="button"
                  className="btn btn-sm rounded-xl flex items-center gap-2 hover:bg-surface-2 transition"
                  aria-label="User profile menu"
                >
                  <Avatar className="h-6 w-6 rounded-lg">
                    <AvatarFallback>{user?.name?.slice(0, 1) ?? "?"}</AvatarFallback>
                  </Avatar>
                  <span className="hidden max-w-[140px] truncate sm:block text-xs font-semibold text-ink">
                    {user?.name}
                  </span>
                  <ChevronDown size={14} className="text-muted" />
                </button>
              </DropdownMenuTrigger>

              <DropdownMenuContent align="right" className="w-72 p-3 bg-white dark:bg-[#181e1a] shadow-2xl border border-stone-200 dark:border-stone-800">
                <div className="px-3.5 py-2.5 rounded-xl bg-stone-100/90 dark:bg-stone-800/90 border border-stone-200/60 dark:border-stone-700/60 mb-2">
                  <div className="text-sm font-bold text-ink">{user?.name}</div>
                  <div className="text-xs text-muted truncate mt-0.5">{user?.email}</div>
                  <div className="mt-2">
                    <Badge variant="default" className="text-[10px] uppercase font-bold tracking-wider">
                      {user?.role_label ?? user?.role}
                    </Badge>
                  </div>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={logout}
                  className="text-critical hover:bg-critical/10 font-semibold rounded-xl px-3 py-2 cursor-pointer"
                >
                  <LogOut size={15} /> Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </header>

          <main className="min-w-0 flex-1 px-4 py-5 sm:px-6 sm:py-6 bg-canvas bg-dot-pattern">
            <Outlet />
          </main>
        </div>
      </div>
      <Toaster />
    </div>
  );
}
