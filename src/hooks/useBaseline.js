import { useEffect, useState } from 'react';
import { fetchBaseline } from '../services/dataService.js';

export function useBaseline() {
  const [state, setState] = useState({ data: null, error: null, loading: true });

  useEffect(() => {
    const ctrl = new AbortController();
    fetchBaseline({ signal: ctrl.signal })
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error) => {
        if (error.name !== 'AbortError') setState({ data: null, error, loading: false });
      });
    return () => ctrl.abort();
  }, []);

  return state;
}
