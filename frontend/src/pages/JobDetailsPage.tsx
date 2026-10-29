import { useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Button, Tag } from '@carbon/react';

import { useUser } from '../context/UserContext';
import { useJobHistory } from '../hooks/useJobHistory';
import { useActions } from '../hooks/useActions';
import { StatusNotifications } from '../components/StatusNotifications';
import { JobHistory } from '../components/JobHistory';
import { JobActionPanel } from '../components/JobActionPanel';
import type { Action } from '../types';

type LocationState = { action?: string; from?: string };

export function JobDetailsPage() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { currentUserId, currentUser } = useUser();

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
  const locationState = location.state as LocationState | null;

  const { history, loading, error, setError, reload } = useJobHistory(
    API_BASE_URL,
    jobId
  );

  const { actions, selectedAction, setSelectedAction } = useActions(
    API_BASE_URL,
    { preselectCode: locationState?.action }
  );

  const [pageError, setPageError] = useState<string | null>(null);
  const [pageSuccess, setPageSuccess] = useState<string | null>(null);

  const latestHistory = history.length > 0 ? history[history.length - 1] : null;
  const currentStage =
    latestHistory?.to_stage ?? latestHistory?.from_stage ?? null;

  const backPath =
    locationState?.from === 'waiting' ? '/waiting' : '/jobs';

  return (
    <>
      <Button kind="ghost" onClick={() => navigate(backPath)}>
        Back
      </Button>

      <h1 style={{ marginTop: '1rem' }}>Job {jobId}</h1>

      {currentStage && (
        <p style={{ marginTop: '0.5rem' }}>
          Current stage: <Tag type="blue">{currentStage}</Tag>
        </p>
      )}

      <StatusNotifications
        error={error ?? pageError}
        success={pageSuccess}
      />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 2fr) minmax(320px, 1fr)',
          gap: '2rem',
          marginTop: '2rem',
          alignItems: 'start',
        }}
      >
        <JobHistory history={history} loading={loading} />

        <aside>
          <JobActionPanel
            actions={actions}
            selectedAction={selectedAction}
            actorName={currentUser?.name}
            userId={currentUserId}
            jobId={jobId ?? ''}
            apiBaseUrl={API_BASE_URL}
            onActionSelect={(action: Action | null) => {
              setSelectedAction(action);
              setPageError(null);
              setPageSuccess(null);
              setError(null);
            }}
            onActionSuccess={reload}
          />
        </aside>
      </div>
    </>
  );
}
