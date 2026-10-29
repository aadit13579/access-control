import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import {
  Button,
  Dropdown,
  InlineNotification,
  Select,
  SelectItem,
  TextInput,
} from '@carbon/react';

import { useUser } from '../context/UserContext';

export function GrantsPage() {
  const { users, currentUser, currentUserId, permissions } = useUser();
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

  const canManageGrants = permissions.includes('manage_grants');
  if (!canManageGrants) return <Navigate to="/jobs" replace />;

  const targetUsers = users.filter((u) => u.id !== currentUserId);

  const [targetUserId, setTargetUserId] = useState<number | null>(null);
  const [roleCode, setRoleCode] = useState('');
  const [clientId, setClientId] = useState<number | null>(null);
  const [branchId, setBranchId] = useState<number | null>(null);
  const [direction, setDirection] = useState<string | null>(null);
  const [mode, setMode] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function resetForm() {
    setTargetUserId(null);
    setRoleCode('');
    setClientId(null);
    setBranchId(null);
    setDirection(null);
    setMode(null);
    setReason('');
  }

  function createGrant() {
    if (currentUserId === null || targetUserId === null || roleCode.trim() === '')
      return;

    setLoading(true);
    setSuccess(null);
    setError(null);

    fetch(`${API_BASE_URL}/api/grants/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        manager_id: currentUserId,
        target_user_id: targetUserId,
        role_code: roleCode,
        client_id: clientId,
        branch_id: branchId,
        direction,
        mode,
        reason,
      }),
    })
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok) {
          throw new Error(
            typeof result.detail === 'string'
              ? result.detail
              : 'Failed to create grant'
          );
        }
        return result;
      })
      .then((result) => {
        setSuccess(`Grant #${result.grant_id} created successfully.`);
        resetForm();
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  return (
    <>
      <h1>Manage Grants</h1>

      <p style={{ marginTop: '0.5rem', marginBottom: '2rem' }}>
        Acting as {currentUser?.name}
      </p>

      {success && (
        <InlineNotification kind="success" title="Grant created" subtitle={success} />
      )}

      {error && (
        <InlineNotification kind="error" title="Grant failed" subtitle={error} />
      )}

      <div style={{ maxWidth: '500px', display: 'grid', gap: '1rem', marginTop: '1rem' }}>
        <Dropdown
          id="target-user"
          titleText="Target user"
          label="Select user"
          items={targetUsers}
          itemToString={(user) => (user ? user.name : '')}
          onChange={({ selectedItem }) =>
            setTargetUserId(selectedItem?.id ?? null)
          }
        />

        <TextInput
          id="role-code"
          labelText="Role"
          placeholder="checker"
          value={roleCode}
          onChange={(e) => setRoleCode(e.target.value)}
        />

        <TextInput
          id="client-id"
          labelText="Client ID"
          placeholder="Leave blank for ALL"
          onChange={(e) => {
            const v = e.target.value;
            setClientId(v === '' ? null : Number(v));
          }}
        />

        <TextInput
          id="branch-id"
          labelText="Branch ID"
          placeholder="Leave blank for ALL"
          onChange={(e) => {
            const v = e.target.value;
            setBranchId(v === '' ? null : Number(v));
          }}
        />

        <Select
          id="direction"
          labelText="Direction"
          value={direction ?? ''}
          onChange={(e) =>
            setDirection(e.target.value === '' ? null : e.target.value)
          }
        >
          <SelectItem value="" text="All directions" />
          <SelectItem value="import" text="Import" />
          <SelectItem value="export" text="Export" />
        </Select>

        <Select
          id="mode"
          labelText="Mode"
          value={mode ?? ''}
          onChange={(e) =>
            setMode(e.target.value === '' ? null : e.target.value)
          }
        >
          <SelectItem value="" text="All modes" />
          <SelectItem value="air" text="Air" />
          <SelectItem value="sea" text="Sea" />
        </Select>

        <TextInput
          id="reason"
          labelText="Reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />

        <Button
          onClick={createGrant}
          disabled={loading || targetUserId === null || roleCode.trim() === ''}
        >
          {loading ? 'Creating...' : 'Create grant'}
        </Button>
      </div>
    </>
  );
}
