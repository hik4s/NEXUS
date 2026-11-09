import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from './api';

export function useResource<T>(load: () => Promise<T>, dependencies: unknown[]) {
  const [data, setData] = useState<T>(); const [error, setError] = useState<ApiError>();
  const [loading, setLoading] = useState(true);
  const loader = useRef(load); loader.current = load;
  const mounted = useRef(false); const generation = useRef(0);
  const reload = useCallback(async (): Promise<boolean> => {
    if (!mounted.current) return false;
    const current = ++generation.current; setLoading(true); setError(undefined);
    try {
      const value = await loader.current();
      if (mounted.current && current === generation.current) { setData(value); return true; }
    } catch (error) {
      if (mounted.current && current === generation.current) setError(error instanceof ApiError ? error : new ApiError(0, 'unavailable'));
    } finally {
      if (mounted.current && current === generation.current) setLoading(false);
    }
    return false;
  }, []);
  useEffect(() => {
    mounted.current = true; void reload();
    return () => { mounted.current = false; ++generation.current; };
  }, [reload, ...dependencies]);
  return { data, error, loading, reload };
}

export function useAction() {
  const lock = useRef(false); const [busy, setBusy] = useState(false); const [error, setError] = useState<ApiError>();
  async function run(work: () => Promise<void>) {
    if (lock.current) return; lock.current = true; setBusy(true); setError(undefined);
    try { await work(); } catch (error) { setError(error instanceof ApiError ? error : new ApiError(0, 'unavailable', true)); }
    finally { lock.current = false; setBusy(false); }
  }
  return { run, busy, error, blocked: busy || !!error?.uncertain, reset: () => setError(undefined) };
}
