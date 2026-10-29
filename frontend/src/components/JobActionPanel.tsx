import { useState } from 'react';
import {
  Button,
  Dropdown,
  InlineNotification,
  TextArea,
  Tile,
} from '@carbon/react';

import type { Action, AuthorizationResponse } from '../types';
import { StatusNotifications } from './StatusNotifications';

type Props = {
  actions: Action[];
  selectedAction: Action | null;
  actorName: string | undefined;
  userId: number | null;
  jobId: string;
  apiBaseUrl: string;
  onActionSuccess: () => void;
  onActionSelect: (action: Action | null) => void;
};

/**
 * Right-side panel on the Job Details page:
 * action picker, authorization check, and perform / raise-approval button.
 */
export function JobActionPanel({
  actions,
  selectedAction,
  actorName,
  userId,
  jobId,
  apiBaseUrl,
  onActionSuccess,
  onActionSelect,
}: Props) {
  const [authorized, setAuthorized] = useState(false);
  const [authMessage, setAuthMessage] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  function handleActionSelect(action: Action | null) {
    onActionSelect(action);
    setAuthorized(false);
    setAuthMessage(null);
    setSuccess(null);
    setReason('');
  }

  function checkAction() {
    if (!jobId || userId === null || selectedAction === null) return;

    setLoading(true);
    setAuthorized(false);
    setAuthMessage(null);
    setError(null);
    setSuccess(null);

    fetch(`${apiBaseUrl}/api/auth/authorize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        action: selectedAction.code,
        job_id: Number(jobId),
      }),
    })
      .then((r) => r.json())
      .then((result: AuthorizationResponse) => {
        if (!result.allowed) {
          setAuthorized(false);
          setAuthMessage(`${result.reason_code}: ${result.reason}`);
          return;
        }
        setAuthorized(true);
        setAuthMessage(result.reason);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  function submitAction() {
    if (!jobId || userId === null || selectedAction === null || !authorized)
      return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    const requiresApproval = selectedAction.approvals_required > 0;
    const endpoint = requiresApproval
      ? `${apiBaseUrl}/api/jobs/${jobId}/approvals/request`
      : `${apiBaseUrl}/api/jobs/${jobId}/action`;

    fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        action: selectedAction.code,
        reason,
      }),
    })
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok) {
          const detail = result.detail;
          if (typeof detail === 'string') throw new Error(detail);
          if (detail?.reason) throw new Error(detail.reason);
          if (detail?.message) throw new Error(detail.message);
          throw new Error('Action failed');
        }
        return result;
      })
      .then((result) => {
        if (requiresApproval) {
          setSuccess(
            `Approval request for ${selectedAction.code} created successfully.`
          );
        } else {
          const transition = result.transition;
          setSuccess(
            transition
              ? `${selectedAction.code} completed: ${transition.from_stage} → ${transition.to_stage}`
              : `${selectedAction.code} completed successfully.`
          );
          onActionSuccess();
        }
        setReason('');
        setAuthorized(false);
        setAuthMessage(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  return (
    <Tile>
      <h3>Job action</h3>

      <p style={{ marginTop: '1rem', marginBottom: '1rem' }}>
        Acting as: <strong>{actorName}</strong>
      </p>

      <Dropdown
        id="job-action"
        titleText="Action"
        label="Select action"
        items={actions}
        itemToString={(action) => (action ? action.code : '')}
        selectedItem={selectedAction}
        onChange={({ selectedItem }) => handleActionSelect(selectedItem ?? null)}
      />

      <Button
        style={{ marginTop: '1rem', width: '100%' }}
        disabled={!selectedAction || loading}
        onClick={checkAction}
      >
        {loading ? 'Checking...' : 'Check action'}
      </Button>

      {authMessage && (
        <div style={{ marginTop: '1rem' }}>
          <InlineNotification
            kind={authorized ? 'success' : 'error'}
            title={authorized ? 'Action allowed' : 'Action denied'}
            subtitle={authMessage}
          />
        </div>
      )}

      <StatusNotifications error={error} success={success} />

      {authorized && selectedAction && (
        <div style={{ marginTop: '1.5rem' }}>
          <TextArea
            id="action-reason"
            labelText="Reason"
            placeholder="Enter reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />

          <Button
            kind={selectedAction.approvals_required > 0 ? 'secondary' : 'primary'}
            style={{ marginTop: '1rem', width: '100%' }}
            disabled={loading || reason.trim() === ''}
            onClick={submitAction}
          >
            {loading
              ? 'Processing...'
              : selectedAction.approvals_required > 0
                ? `Raise approval for ${selectedAction.code}`
                : `Perform ${selectedAction.code}`}
          </Button>
        </div>
      )}
    </Tile>
  );
}

