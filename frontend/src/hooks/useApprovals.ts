import { useCallback, useEffect, useState } from 'react';
import type { Approval, ApprovalsResponse } from '../types';

/**
 * Loads pending approvals (decided_by === null) from /api/approvals.
 */
export function useApprovals(apiBaseUrl: string) {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);

    fetch(`${apiBaseUrl}/api/approvals`)
      .then((response) => {
        if (!response.ok) throw new Error('Failed to load approvals');
        return response.json();
      })
      .then((result: ApprovalsResponse) =>
        setApprovals(result.approvals.filter((a) => a.decided_by === null))
      )
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [apiBaseUrl]);

  useEffect(() => {
    load();
  }, [load]);

  return { approvals, setApprovals, loading, error, setError };
}

