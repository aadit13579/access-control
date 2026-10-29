import { useNavigate } from 'react-router-dom';
import { InlineLoading, InlineNotification } from '@carbon/react';

import { useUser } from '../context/UserContext';
import { useWaitingJobs } from '../hooks/useWaitingJobs';
import { JobsTable } from '../components/JobsTable';

const HEADERS = [
  { key: 'ref', header: 'Job' },
  { key: 'client_id', header: 'Client' },
  { key: 'branch_id', header: 'Branch' },
  { key: 'direction', header: 'Direction' },
  { key: 'mode', header: 'Mode' },
  { key: 'stage', header: 'Stage' },
];

export function JobsPage() {
  const { currentUserId, currentUser } = useUser();
  const navigate = useNavigate();

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
  const { jobs, loading, error } = useWaitingJobs(
    API_BASE_URL,
    currentUserId,
    'view'
  );

  const rows = jobs.map((job) => ({
    id: String(job.id),
    ref: job.ref,
    client_id: job.client_id,
    branch_id: job.branch_id,
    direction: job.direction,
    mode: job.mode,
    stage: job.stage,
  }));

  return (
    <>
      <h1>Jobs</h1>

      <p style={{ marginTop: '0.5rem', marginBottom: '2rem' }}>
        Jobs visible to {currentUser?.name ?? 'selected user'}
      </p>

      {loading && <InlineLoading description="Loading jobs..." />}

      {error && (
        <div style={{ marginBottom: '1rem' }}>
          <InlineNotification kind="error" title="Error" subtitle={error} />
        </div>
      )}

      {!loading && jobs.length === 0 && (
        <InlineNotification
          kind="info"
          title="No visible jobs"
          subtitle="This user is not currently allowed to view any jobs."
        />
      )}

      {!loading && jobs.length > 0 && (
        <JobsTable
          title="Visible jobs"
          headers={HEADERS}
          rows={rows}
          onRowClick={(id) => navigate(`/jobs/${id}`)}
        />
      )}
    </>
  );
}
