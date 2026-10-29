import { InlineLoading, Tag, Tile } from '@carbon/react';
import type { HistoryItem } from '../types';

type Props = {
  history: HistoryItem[];
  loading: boolean;
};

/**
 * Displays the job history list on the Job Details page.
 */
export function JobHistory({ history, loading }: Props) {
  return (
    <section>
      <h3>History</h3>

      {loading && <InlineLoading description="Loading history..." />}

      {!loading && history.length === 0 && (
        <p style={{ marginTop: '1rem' }}>No history found.</p>
      )}

      {history.map((item) => (
        <Tile key={item.id} style={{ marginTop: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <strong>{item.actor_name}</strong>

            <Tag type={item.outcome === 'allowed' ? 'green' : 'red'}>
              {item.action}
            </Tag>
          </div>

          <p style={{ marginTop: '0.75rem' }}>
            {item.from_stage ?? '-'}
            {' → '}
            {item.to_stage ?? '-'}
          </p>

          {item.reason && (
            <p style={{ marginTop: '0.5rem' }}>{item.reason}</p>
          )}

          <p style={{ marginTop: '0.5rem' }}>Grant #{item.grant_id ?? '-'}</p>

          <p>{new Date(item.at).toLocaleString()}</p>
        </Tile>
      ))}
    </section>
  );
}

