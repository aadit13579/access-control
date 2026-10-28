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
  const {
    users,
    currentUser,
    currentUserId,
    permissions,
  } = useUser();

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

  const canManageGrants =
    permissions.includes('manage_grants');

  const targetUsers = users.filter(
    (user) => user.id !== currentUserId
  );

  const [targetUserId, setTargetUserId] =
    useState<number | null>(null);

  const [roleCode, setRoleCode] = useState('');

  const [clientId, setClientId] =
    useState<number | null>(null);

  const [branchId, setBranchId] =
    useState<number | null>(null);

  const [direction, setDirection] =
    useState<string | null>(null);

  const [mode, setMode] =
    useState<string | null>(null);

  const [reason, setReason] = useState('');

  const [loading, setLoading] = useState(false);
  const [success, setSuccess] =
    useState<string | null>(null);

  const [error, setError] =
    useState<string | null>(null);

  if (!canManageGrants) {
    return <Navigate to="/jobs" replace />;
  }

  function createGrant() {
    if (
      currentUserId === null ||
      targetUserId === null ||
      roleCode.trim() === ''
    ) {
      return;
    }

    setLoading(true);
    setSuccess(null);
    setError(null);

    fetch(`${API_BASE_URL}/api/grants/`, {
      method: 'POST',

      headers: {
        'Content-Type': 'application/json',
      },

      body: JSON.stringify({
        manager_id: currentUserId,
        target_user_id: targetUserId,
        role_code: roleCode,
        client_id: clientId,
        branch_id: branchId,
        direction: direction,
        mode: mode,
        reason: reason,
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
        setSuccess(
          `Grant #${result.grant_id} created successfully.`
        );
        setTargetUserId(null);
        setRoleCode('');
        setClientId(null);
        setBranchId(null);
        setDirection(null);
        setMode(null);
        setReason('');
      })
      .catch((error) => {
        setError(error.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }

  return (
    <>
      <h1>Manage Grants</h1>

      <p
        style={{
          marginTop: '0.5rem',
          marginBottom: '2rem',
        }}
      >
        Acting as {currentUser?.name}
      </p>

      {success && (
        <InlineNotification
          kind="success"
          title="Grant created"
          subtitle={success}
        />
      )}

      {error && (
        <InlineNotification
          kind="error"
          title="Grant failed"
          subtitle={error}
        />
      )}

      <div
        style={{
          maxWidth: '500px',
          display: 'grid',
          gap: '1rem',
          marginTop: '1rem',
        }}
      >
        <Dropdown
          id="target-user"
          titleText="Target user"
          label="Select user"
          items={targetUsers}
          itemToString={(user) =>
            user ? user.name : ''
          }
          onChange={({ selectedItem }) => {
            setTargetUserId(
              selectedItem?.id ?? null
            );
          }}
        />

        <TextInput
          id="role-code"
          labelText="Role"
          placeholder="checker"
          value={roleCode}
          onChange={(event) =>
            setRoleCode(event.target.value)
          }
        />

        <TextInput
          id="client-id"
          labelText="Client ID"
          placeholder="Leave blank for ALL"
          onChange={(event) => {
            const value = event.target.value;

            setClientId(
              value === ''
                ? null
                : Number(value)
            );
          }}
        />

        <TextInput
          id="branch-id"
          labelText="Branch ID"
          placeholder="Leave blank for ALL"
          onChange={(event) => {
            const value = event.target.value;

            setBranchId(
              value === ''
                ? null
                : Number(value)
            );
          }}
        />

        <Select
          id="direction"
          labelText="Direction"
          value={direction ?? ''}
          onChange={(event) => {
            setDirection(
              event.target.value === ''
                ? null
                : event.target.value
            );
          }}
        >
          <SelectItem value="" text="All directions" />
          <SelectItem value="import" text="Import" />
          <SelectItem value="export" text="Export" />
        </Select>

        <Select
          id="mode"
          labelText="Mode"
          value={mode ?? ''}
          onChange={(event) => {
            setMode(
              event.target.value === ''
                ? null
                : event.target.value
            );
          }}
        >
          <SelectItem value="" text="All modes" />
          <SelectItem value="air" text="Air" />
          <SelectItem value="sea" text="Sea" />
        </Select>

        <TextInput
          id="reason"
          labelText="Reason"
          value={reason}
          onChange={(event) =>
            setReason(event.target.value)
          }
        />

        <Button
          onClick={createGrant}
          disabled={
            loading ||
            targetUserId === null ||
            roleCode.trim() === ''
          }
        >
          {loading ? 'Creating...' : 'Create grant'}
        </Button>
      </div>
    </>
  );
}