import { useEffect, useState } from 'react';
import {
  Button,
  Dropdown,
  InlineLoading,
  InlineNotification,
} from '@carbon/react';

import { useUser } from '../context/UserContext';
import { useWaitingJobs } from '../hooks/useWaitingJobs';
import { AuthorizationResult } from '../components/AuthorizationResult';
import type { AuthorizationResponse, Job } from '../types';

const ACTIONS = [
  'view', 'prepare', 'check', 'file',
  'cancel', 'reopen', 'approve', 'reject', 'parse',
];

export function AuthorizationPage() {
  const { currentUserId, currentUser } = useUser();
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [selectedAction, setSelectedAction] = useState('check');
  const [authResult, setAuthResult] = useState<AuthorizationResponse | null>(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const { jobs, loading: jobsLoading, error: jobsError } = useWaitingJobs(
    API_BASE_URL,
    currentUserId,
    'view'
  );

  // Reset selections when user changes
  useEffect(() => {
    setSelectedJob(null);
    setAuthResult(null);
  }, [currentUserId]);

  function checkAuthorization() {
    if (currentUserId === null || selectedJob === null) return;

    setAuthLoading(true);
    setAuthResult(null);
    setAuthError(null);

    fetch(`${API_BASE_URL}/api/auth/authorize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: currentUserId,
        action: selectedAction,
        job_id: selectedJob.id,
      }),
    })
      .then((response) => {
        if (!response.ok) throw new Error('Authorization request failed');
        return response.json();
      })
      .then((result: AuthorizationResponse) => setAuthResult(result))
      .catch((err) => setAuthError(err.message))
      .finally(() => setAuthLoading(false));
  }

  const error = jobsError ?? authError;

  return (
    <>
      <h1>Authorization</h1>

      <p style={{ marginTop: '0.5rem', marginBottom: '2rem' }}>
        Check what {currentUser?.name ?? 'the selected user'} can do.
      </p>

      {jobsLoading && (
        <InlineLoading description="Loading viewable jobs..." />
      )}

      {error && (
        <div style={{ marginBottom: '1rem' }}>
          <InlineNotification kind="error" title="Error" subtitle={error} />
        </div>
      )}

      {!jobsLoading && (
        <div
          style={{
            display: 'flex',
            gap: '1rem',
            alignItems: 'end',
            marginBottom: '2rem',
          }}
        >
          <div style={{ width: '300px' }}>
            <Dropdown
              id="authorization-job"
              titleText="Job"
              label="Select job"
              items={jobs}
              itemToString={(job) =>
                job ? `${job.ref} — ${job.stage}` : ''
              }
              selectedItem={selectedJob}
              onChange={({ selectedItem }) => {
                setSelectedJob(selectedItem ?? null);
                setAuthResult(null);
              }}
            />
          </div>

          <div style={{ width: '220px' }}>
            <Dropdown
              id="authorization-action"
              titleText="Action"
              label="Select action"
              items={ACTIONS}
              selectedItem={selectedAction}
              onChange={({ selectedItem }) => {
                if (selectedItem) {
                  setSelectedAction(selectedItem);
                  setAuthResult(null);
                }
              }}
            />
          </div>

          <Button
            onClick={checkAuthorization}
            disabled={selectedJob === null || currentUserId === null || authLoading}
          >
            Check authorization
          </Button>
        </div>
      )}

      {!jobsLoading && jobs.length === 0 && (
        <InlineNotification
          kind="info"
          title="No viewable jobs"
          subtitle="The selected user is not currently authorized to view any jobs."
        />
      )}

      {authLoading && (
        <InlineLoading description="Checking authorization..." />
      )}

      {authResult && (
        <AuthorizationResult
          result={authResult}
          userName={currentUser?.name}
          jobRef={selectedJob?.ref}
          action={selectedAction}
        />
      )}
    </>
  );
}
