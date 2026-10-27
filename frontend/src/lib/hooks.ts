import { useCallback, useEffect, useState } from "react";

import { api, errorMessage } from "./api";
import type { TicketDetail, TicketFilters, TicketListResponse } from "./types";

export function useDebounced<T>(value: T, delay = 250): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export function useTicketList(filters: TicketFilters) {
  const [data, setData] = useState<TicketListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const key = JSON.stringify(filters);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.tickets(JSON.parse(key) as TicketFilters);
      setData(response);
      setError(null);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setLoading(false);
    }
  }, [key]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .tickets(JSON.parse(key) as TicketFilters)
      .then((response) => {
        if (!active) return;
        setData(response);
        setError(null);
      })
      .catch((cause) => {
        if (!active) return;
        setError(errorMessage(cause));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [key]);

  return { data, loading, error, reload: load };
}

export function useTicket(id: number | null) {
  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (silent = false) => {
      if (id === null) {
        setTicket(null);
        return;
      }
      if (!silent) setLoading(true);
      try {
        const response = await api.ticket(id);
        setTicket(response);
        setError(null);
      } catch (cause) {
        setError(errorMessage(cause));
      } finally {
        setLoading(false);
      }
    },
    [id],
  );

  useEffect(() => {
    setTicket(null);
    void load();
  }, [load]);

  return { ticket, setTicket, loading, error, reload: load };
}