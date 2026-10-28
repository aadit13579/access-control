import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import {
  Button,
  InlineLoading,
  InlineNotification,
  Tag,
  Tile,
} from '@carbon/react';

type HistoryItem = {
  id: number;
  actor_id: number;
  actor_name: string;
  action: string;
  from_stage: string | null;
  to_stage: string | null;
  outcome: string;
  grant_id: number | null;
  reason: string | null;
  at: string;
};

type HistoryResponse = {
  job_id: number;
  history: HistoryItem[];
};

export function JobDetailsPage() {
  const { jobId } = useParams();
  const navigate = useNavigate();

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) {
      return;
    }

    setLoading(true);
    setError(null);

    fetch(`${API_BASE_URL}/api/jobs/${jobId}/history`)
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to load job history');
        }

        return response.json();
      })
      .then((result: HistoryResponse) => {
        setHistory(result.history);
      })
      .catch((error) => {
        setError(error.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [jobId, API_BASE_URL]);

  return (
    <>
      <Button
        kind="ghost"
        onClick={() => navigate('/jobs')}
      >
        Back to jobs
      </Button>

      <h1 style={{ marginTop: '1rem' }}>
        Job {jobId}
      </h1>

      <h3 style={{ marginTop: '2rem' }}>
        History
      </h3>

      {loading && (
        <InlineLoading description="Loading history..." />
      )}

      {error && (
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={error}
        />
      )}

      {!loading && history.length === 0 && (
        <p style={{ marginTop: '1rem' }}>
          No history found.
        </p>
      )}

      {history.map((item) => (
        <Tile
          key={item.id}
          style={{
            marginTop: '1rem',
            maxWidth: '800px',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
            }}
          >
            <strong>{item.actor_name}</strong>

            <Tag
              type={
                item.outcome === 'allowed'
                  ? 'green'
                  : 'red'
              }
            >
              {item.action}
            </Tag>
          </div>

          <p style={{ marginTop: '0.75rem' }}>
            {item.from_stage ?? '-'}
            {' → '}
            {item.to_stage ?? '-'}
          </p>

          {item.reason && (
            <p style={{ marginTop: '0.5rem' }}>
              {item.reason}
            </p>
          )}

          <p style={{ marginTop: '0.5rem' }}>
            Grant #{item.grant_id ?? '-'}
          </p>

          <p>
            {new Date(item.at).toLocaleString()}
          </p>
        </Tile>
      ))}
    </>
  );
}