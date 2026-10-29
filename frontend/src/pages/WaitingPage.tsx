import { useNavigate } from 'react-router-dom';
import { Dropdown, InlineLoading, InlineNotification } from '@carbon/react';

import { useUser } from '../context/UserContext';
import { useActions } from '../hooks/useActions';
import { useWaitingJobs } from '../hooks/useWaitingJobs';
import { JobsTable } from '../components/JobsTable';

const HEADERS = [
  { key: 'ref', header: 'Job' },
  { key: 'client_id', header: 'Client' },
  { key: 'branch_id', header: 'Branch' },
  { key: 'direction', header: 'Direction' },
  { key: 'mode', header: 'Mode' },
  { key: 'stage', header: 'Stage' },
  { key: 'role_code', header: 'Role' },
];

export function WaitingPage() {
  const { currentUserId, currentUser } = useUser();
  const navigate = useNavigate();

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

  const {
    actions,
    selectedAction,
    setSelectedAction,
    loading: actionsLoading,
    error: actionsError,
  } = useActions(API_BASE_URL, { onlyWithFromStages: true });

  const {
    data,
    jobs,
    loading: jobsLoading,
    error: jobsError,
  } = useWaitingJobs(API_BASE_URL, currentUserId, selectedAction?.code ?? null);

  const error = actionsError ?? jobsError;

  const rows = jobs.map((job) => ({
    id: String(job.id),
    ref: job.ref,
    client_id: job.client_id,
    branch_id: job.branch_id,
    direction: job.direction,
    mode: job.mode,
    stage: job.stage,
    role_code: job.role_code,
  }));

  return (
    <>
      <h1>Waiting</h1>

      <p style={{ marginTop: '0.5rem', marginBottom: '2rem' }}>
        Jobs currently available to{' '}
        {currentUser?.name ?? 'selected user'}
      </p>

      {actionsLoading && <InlineLoading description="Loading actions..." />}

      {!actionsLoading && (
        <div style={{ width: '250px', marginBottom: '2rem' }}>
          <Dropdown
            id="action-dropdown"
            titleText="Action"
            label="Select action"
            items={actions}
            itemToString={(action) => (action ? action.code : '')}
            selectedItem={selectedAction}
            onChange={({ selectedItem }) =>
              setSelectedAction(selectedItem ?? null)
            }
          />
        </div>
      )}

      {jobsLoading && (
        <InlineLoading description="Loading waiting jobs..." />
      )}

      {error && (
        <div style={{ marginBottom: '1rem' }}>
          <InlineNotification
            kind="error"
            title="Unable to load data"
            subtitle={error}
          />
        </div>
      )}

      {!jobsLoading && !error && data && selectedAction && (
        <>
          <p style={{ marginBottom: '1rem' }}>
            Found <strong>{data.count}</strong> job(s) for action{' '}
            <strong>{selectedAction.code}</strong>
            {selectedAction.approvals_required > 0 && (
              <>
                {' '}— requires {selectedAction.approvals_required} approval(s)
              </>
            )}
          </p>

          <JobsTable
            title="Available jobs"
            headers={HEADERS}
            rows={rows}
            onRowClick={(id) =>
              navigate(`/jobs/${id}`, {
                state: {
                  action: selectedAction.code,
                  approvalsRequired: selectedAction.approvals_required,
                  from: 'waiting',
                },
              })
            }
          />
        </>
      )}
    </>
  );
}
