import { useState, useEffect } from 'react';

type Status = 'idle' | 'pending' | 'success' | 'error';

interface ApiState<T> {
  data: T | null;
  status: Status;
  error: string | null;
}

export function useApi<T>(fetcher: () => Promise<T>, enabled = true): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    status: 'idle',
    error: null,
  });

  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;

    setState({ data: null, status: 'pending', error: null });

    fetcher()
      .then((data) => {
        if (!cancelled) setState({ data, status: 'success', error: null });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({
            data: null,
            status: 'error',
            error: err instanceof Error ? err.message : String(err),
          });
        }
      });

    return () => {
      cancelled = true;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetcher, enabled]);

  return state;
}
