import { useEffect, useState } from 'react';
import type { Job, WaitingResponse } from '../types';

/**
 * Fetches jobs the given user is waiting on for a specific action.
 * Re-fetches when userId or action changes.
 */
export function useWaitingJobs(
  apiBaseUrl: string,
  userId: number | null,
  action: string | null
) {
  const [data, setData] = useState<WaitingResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (userId === null || action === null) return;

    setLoading(true);
    setError(null);
    setData(null);

    fetch(
      `${apiBaseUrl}/api/jobs/waiting?user_id=${userId}&action=${action}`
    )
      .then((response) => {
        if (!response.ok) throw new Error('Failed to load waiting jobs');
        return response.json();
      })
      .then((result: WaitingResponse) => setData(result))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [apiBaseUrl, userId, action]);

  const jobs: Job[] = data?.jobs ?? [];
  return { data, jobs, loading, error };
}

