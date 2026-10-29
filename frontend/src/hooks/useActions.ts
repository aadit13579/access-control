import { useEffect, useState } from 'react';
import type { Action, ActionsResponse } from '../types';

/**
 * Loads the full list of actions from /api/actions.
 * Optionally pre-selects an action by code on load.
 */
export function useActions(
  apiBaseUrl: string,
  options?: { preselectCode?: string; onlyWithFromStages?: boolean }
) {
  const [actions, setActions] = useState<Action[]>([]);
  const [selectedAction, setSelectedAction] = useState<Action | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    fetch(`${apiBaseUrl}/api/actions`)
      .then((response) => {
        if (!response.ok) throw new Error('Failed to load actions');
        return response.json();
      })
      .then((result: ActionsResponse) => {
        setActions(result.actions);

        if (options?.preselectCode) {
          const match = result.actions.find(
            (a) => a.code === options.preselectCode
          );
          if (match) setSelectedAction(match);
        } else if (options?.onlyWithFromStages) {
          const first = result.actions.find((a) => a.from_stages !== null);
          if (first) setSelectedAction(first);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [apiBaseUrl]);

  return { actions, selectedAction, setSelectedAction, loading, error };
}

