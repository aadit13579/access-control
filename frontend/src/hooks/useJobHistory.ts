import { useCallback, useEffect, useState } from 'react';
import type { HistoryItem, HistoryResponse } from '../types';

/**
 * Loads and re-loads the history for a specific job.
 */
export function useJobHistory(apiBaseUrl: string, jobId: string | undefined) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!jobId) return;

    setLoading(true);

    fetch(`${apiBaseUrl}/api/jobs/${jobId}/history`)
      .then((response) => {
        if (!response.ok) throw new Error('Failed to load job history');
        return response.json();
      })
      .then((result: HistoryResponse) => setHistory(result.history))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [apiBaseUrl, jobId]);

  useEffect(() => {
    setError(null);
    load();
  }, [load]);

  return { history, loading, error, setError, reload: load };
}

