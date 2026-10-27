import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { api, errorMessage } from "../lib/api";
import type { Metrics, SystemStatus } from "../lib/types";

export type ToastTone = "success" | "error" | "info";

export interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
}

interface AppContextValue {
  metrics: Metrics | null;
  status: SystemStatus | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  toast: (message: string, tone?: ToastTone) => void;
  toasts: ToastItem[];
  dismissToast: (id: number) => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const toastId = useRef(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts((current) => current.filter((item) => item.id !== id));
  }, []);

  const toast = useCallback(
    (message: string, tone: ToastTone = "success") => {
      toastId.current += 1;
      const id = toastId.current;
      setToasts((current) => [...current.slice(-2), { id, message, tone }]);
      window.setTimeout(() => {
        setToasts((current) => current.filter((item) => item.id !== id));
      }, 5000);
    },
    [],
  );

  const refresh = useCallback(async () => {
    try {
      const [nextMetrics, nextStatus] = await Promise.all([api.metrics(), api.status()]);
      if (!mounted.current) return;
      setMetrics(nextMetrics);
      setStatus(nextStatus);
      setError(null);
    } catch (cause) {
      if (!mounted.current) return;
      setError(errorMessage(cause));
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo<AppContextValue>(
    () => ({ metrics, status, loading, error, refresh, toast, toasts, dismissToast }),
    [metrics, status, loading, error, refresh, toast, toasts, dismissToast],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used inside AppProvider");
  return context;
}