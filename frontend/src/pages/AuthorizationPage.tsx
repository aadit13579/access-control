import { useEffect, useState } from 'react';

import {
  Button,
  Dropdown,
  InlineLoading,
  InlineNotification,
  Tag,
  Tile,
} from '@carbon/react';

import { useUser } from '../context/UserContext';

type Job = {
  id: number;
  ref: string;
  client_id: number;
  branch_id: number;
  direction: string;
  mode: string;
  stage: string;
  grant_id: number;
  role_code: string;
};

type WaitingResponse = {
  user_id: number;
  action: string;
  count: number;
  jobs: Job[];
};

type AuthorizationResponse = {
  allowed: boolean;
  reason_code: string;
  reason: string;

  current_stage?: string;

  grant_id?: number;
  role_code?: string;

  grant_scope?: {
    client?: string;
    branch?: string;
    direction?: string;
    mode?: string;
  };

  job_stage?: string;
  as_of?: string;
};

const actions = [
  'view',
  'prepare',
  'check',
  'file',
  'cancel',
  'reopen',
  'approve',
  'reject',
  'parse'
];

export function AuthorizationPage() {
  const { currentUserId, currentUser } = useUser();

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

  // Jobs the current user is allowed to view
  const [jobs, setJobs] = useState<Job[]>([]);

  // Job selected in the dropdown
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  // Action selected in the dropdown
  const [selectedAction, setSelectedAction] = useState('check');

  // Result from /api/auth/authorize
  const [authorizationResult, setAuthorizationResult] =
    useState<AuthorizationResponse | null>(null);

  const [jobsLoading, setJobsLoading] = useState(false);
  const [authorizationLoading, setAuthorizationLoading] =
    useState(false);

  const [error, setError] = useState<string | null>(null);

  // ---------------------------------------
  // 1. Load jobs this user is allowed to VIEW
  // ---------------------------------------

  useEffect(() => {
    if (currentUserId === null) {
      return;
    }

    setJobsLoading(true);
    setError(null);

    // Reset old selections when user changes
    setSelectedJob(null);
    setAuthorizationResult(null);

    fetch(
      `${API_BASE_URL}/api/jobs/waiting?user_id=${currentUserId}&action=view`
    )
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to load viewable jobs');
        }

        return response.json();
      })
      .then((result: WaitingResponse) => {
        setJobs(result.jobs);
      })
      .catch((error) => {
        setError(error.message);
      })
      .finally(() => {
        setJobsLoading(false);
      });
  }, [currentUserId, API_BASE_URL]);

  // ---------------------------------------
  // 2. Check authorization
  // ---------------------------------------

  function checkAuthorization() {
    if (currentUserId === null || selectedJob === null) {
      return;
    }

    setAuthorizationLoading(true);
    setAuthorizationResult(null);
    setError(null);

    fetch(`${API_BASE_URL}/api/auth/authorize`, {
      method: 'POST',

      headers: {
        'Content-Type': 'application/json',
      },

      body: JSON.stringify({
        user_id: currentUserId,
        action: selectedAction,
        job_id: selectedJob.id,
      }),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error('Authorization request failed');
        }

        return response.json();
      })
      .then((result: AuthorizationResponse) => {
        setAuthorizationResult(result);
      })
      .catch((error) => {
        setError(error.message);
      })
      .finally(() => {
        setAuthorizationLoading(false);
      });
  }

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
          <InlineNotification
            kind="error"
            title="Error"
            subtitle={error}
          />
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
                job
                  ? `${job.ref} — ${job.stage}`
                  : ''
              }
              selectedItem={selectedJob}
              onChange={({ selectedItem }) => {
                setSelectedJob(selectedItem ?? null);

                // Clear result when changing jobs
                setAuthorizationResult(null);
              }}
            />
          </div>

          <div style={{ width: '220px' }}>
            <Dropdown
              id="authorization-action"
              titleText="Action"
              label="Select action"
              items={actions}
              selectedItem={selectedAction}
              onChange={({ selectedItem }) => {
                if (selectedItem) {
                  setSelectedAction(selectedItem);

                  // Clear result when changing action
                  setAuthorizationResult(null);
                }
              }}
            />
          </div>

          <Button
            onClick={checkAuthorization}
            disabled={
              selectedJob === null ||
              currentUserId === null ||
              authorizationLoading
            }
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

      {authorizationLoading && (
        <InlineLoading description="Checking authorization..." />
      )}

      {authorizationResult && (
        <Tile style={{ marginTop: '2rem', maxWidth: '700px' }}>
          <div style={{ marginBottom: '1.5rem' }}>
            {authorizationResult.allowed ? (
              <Tag type="green">ALLOWED</Tag>
            ) : (
              <Tag type="red">DENIED</Tag>
            )}
          </div>

          <p>
            <strong>User:</strong>{' '}
            {currentUser?.name}
          </p>

          <p>
            <strong>Job:</strong>{' '}
            {selectedJob?.ref}
          </p>

          <p>
            <strong>Action:</strong>{' '}
            {selectedAction}
          </p>

          <p style={{ marginTop: '1rem' }}>
            <strong>Reason code:</strong>{' '}
            {authorizationResult.reason_code}
          </p>

          <p>
            <strong>Reason:</strong>{' '}
            {authorizationResult.reason}
          </p>

          {authorizationResult.current_stage && (
            <p>
              <strong>Current stage:</strong>{' '}
              {authorizationResult.current_stage}
            </p>
          )}

          {authorizationResult.role_code && (
            <p>
              <strong>Role:</strong>{' '}
              {authorizationResult.role_code}
            </p>
          )}

          {authorizationResult.grant_id !== undefined && (
            <p>
              <strong>Grant:</strong> #
              {authorizationResult.grant_id}
            </p>
          )}

          {authorizationResult.grant_scope && (
            <div style={{ marginTop: '1rem' }}>
              <strong>Grant scope</strong>

              <p>
                Client:{' '}
                {authorizationResult.grant_scope.client ?? '-'}
              </p>

              <p>
                Branch:{' '}
                {authorizationResult.grant_scope.branch ?? '-'}
              </p>

              <p>
                Direction:{' '}
                {authorizationResult.grant_scope.direction ?? '-'}
              </p>

              <p>
                Mode:{' '}
                {authorizationResult.grant_scope.mode ?? '-'}
              </p>
            </div>
          )}
        </Tile>
      )}
    </>
  );
}