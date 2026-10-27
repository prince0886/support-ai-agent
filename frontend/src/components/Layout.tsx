import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Info,
  Inbox,
  LayoutDashboard,
  LifeBuoy,
  Menu,
  Plus,
  Settings,
  Sparkles,
  X,
} from "lucide-react";

import { AI_MODE_LABEL } from "../lib/labels";
import { useApp, type ToastItem } from "../store/AppStore";
import { NewTicketProvider, useNewTicket } from "./NewTicketModal";

const NAV_ITEMS = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/inbox", label: "Support Inbox", icon: Inbox, end: false },
  { to: "/knowledge", label: "Knowledge Base", icon: BookOpen, end: false },
  { to: "/settings", label: "Settings", icon: Settings, end: false },
];

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { status } = useApp();
  const aiMode = status?.ai.mode ?? "fallback";
  const modelLabel =
    aiMode === "llm" ? status?.ai.model ?? "configured model" : "Deterministic analyst v1";
  const newCount = status?.counts.new ?? 0;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 text-white shadow-lg shadow-brand-950/40">
          <Sparkles className="h-[18px] w-[18px]" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold text-white">SupportPilot</p>
          <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
            AI teammate
          </p>
        </div>
      </div>

      <nav className="mt-2 flex-1 space-y-1 px-3" aria-label="Main navigation">
        <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">
          Workspace
        </p>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `group flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition ${
                isActive
                  ? "bg-white/[0.09] text-white shadow-[inset_2px_0_0_0_#818cf8]"
                  : "text-slate-400 hover:bg-white/[0.05] hover:text-slate-200"
              }`
            }
          >
            <item.icon className="h-4 w-4 shrink-0" />
            <span className="flex-1">{item.label}</span>
            {item.label === "Support Inbox" && newCount > 0 ? (
              <span className="rounded-full bg-brand-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-brand-200 ring-1 ring-inset ring-brand-400/30">
                {newCount}
              </span>
            ) : null}
          </NavLink>
        ))}
      </nav>

      <div className="px-3 pb-4">
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.04] p-3">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              AI engine
            </span>
            <span className="flex items-center gap-1 text-[10px] font-medium text-slate-300">
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  aiMode === "llm" ? "bg-emerald-400" : "bg-amber-400"
                }`}
              />
              {aiMode === "llm" ? "Live" : "Fallback"}
            </span>
          </div>
          <p className="mt-1.5 text-xs font-medium text-slate-200">
            {AI_MODE_LABEL[aiMode]}
          </p>
          <p className="mt-0.5 truncate text-[10px] text-slate-500" title={modelLabel}>
            {modelLabel}
          </p>
        </div>
        <div className="mt-3 flex items-center gap-1.5 px-1 text-[10px] text-slate-500">
          <LifeBuoy className="h-3 w-3" />
          OpenFire Hackathon · v{status?.app_version ?? "1.0.0"}
        </div>
      </div>
    </div>
  );
}

function MobileHeader({ onMenu }: { onMenu: () => void }) {
  const { open } = useNewTicket();
  return (
    <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white/90 px-4 py-2.5 backdrop-blur lg:hidden">
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-brand-400 to-brand-600 text-white">
          <Sparkles className="h-4 w-4" />
        </div>
        <span className="text-sm font-semibold text-slate-900">SupportPilot</span>
      </div>
      <div className="flex items-center gap-1">
        <button type="button" className="btn btn-primary btn-sm" onClick={open}>
          <Plus className="h-3.5 w-3.5" /> New
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onMenu} aria-label="Open menu">
          <Menu className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}

function ToastViewport() {
  const { toasts, dismissToast } = useApp();
  if (toasts.length === 0) return null;

  const styles: Record<ToastItem["tone"], { wrap: string; icon: JSX.Element }> = {
    success: {
      wrap: "border-emerald-200 bg-white text-slate-800",
      icon: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
    },
    error: {
      wrap: "border-rose-200 bg-white text-slate-800",
      icon: <AlertTriangle className="h-4 w-4 text-rose-500" />,
    },
    info: {
      wrap: "border-slate-200 bg-white text-slate-800",
      icon: <Info className="h-4 w-4 text-brand-500" />,
    },
  };

  return (
    <div className="pointer-events-none fixed bottom-5 right-5 z-[60] flex w-full max-w-sm flex-col gap-2">
      {toasts.map((item) => (
        <div
          key={item.id}
          role="status"
          className={`pointer-events-none flex animate-fade-in items-start gap-2.5 rounded-xl border px-3.5 py-3 shadow-raised ${styles[item.tone].wrap}`}
        >
          <span className="mt-0.5">{styles[item.tone].icon}</span>
          <p className="flex-1 text-sm">{item.message}</p>
          <button
            type="button"
            className="pointer-events-auto rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            onClick={() => dismissToast(item.id)}
            aria-label="Dismiss notification"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}

export function Layout() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [location.pathname]);

  return (
    <NewTicketProvider>
      <div className="min-h-screen lg:pl-[248px]">
        <aside className="fixed inset-y-0 left-0 z-40 hidden w-[248px] border-r border-white/[0.06] bg-[#0b1220] lg:block">
          <SidebarContent />
        </aside>

        {drawerOpen ? (
          <div className="fixed inset-0 z-50 lg:hidden">
            <div
              className="absolute inset-0 bg-slate-950/50 backdrop-blur-sm"
              onClick={() => setDrawerOpen(false)}
              aria-hidden
            />
            <aside className="absolute inset-y-0 left-0 w-[248px] bg-[#0b1220] shadow-raised">
              <button
                type="button"
                className="absolute right-3 top-4 rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white"
                onClick={() => setDrawerOpen(false)}
                aria-label="Close menu"
              >
                <X className="h-4 w-4" />
              </button>
              <SidebarContent onNavigate={() => setDrawerOpen(false)} />
            </aside>
          </div>
        ) : null}

        <MobileHeader onMenu={() => setDrawerOpen(true)} />

        <main className="mx-auto w-full max-w-[1560px] px-4 pb-16 pt-5 sm:px-6 lg:px-8 lg:pt-8">
          <Outlet />
        </main>

        <ToastViewport />
      </div>
    </NewTicketProvider>
  );
}