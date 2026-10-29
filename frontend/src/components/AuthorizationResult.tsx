import { Tag, Tile } from '@carbon/react';
import type { AuthorizationResponse } from '../types';

type Props = {
  result: AuthorizationResponse;
  userName: string | undefined;
  jobRef: string | undefined;
  action: string;
};

/**
 * Displays the authorization check result tile on the Authorization page.
 */
export function AuthorizationResult({ result, userName, jobRef, action }: Props) {
  return (
    <Tile style={{ marginTop: '2rem', maxWidth: '700px' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        {result.allowed ? (
          <Tag type="green">ALLOWED</Tag>
        ) : (
          <Tag type="red">DENIED</Tag>
        )}
      </div>

      <p><strong>User:</strong> {userName}</p>
      <p><strong>Job:</strong> {jobRef}</p>
      <p><strong>Action:</strong> {action}</p>

      <p style={{ marginTop: '1rem' }}>
        <strong>Reason code:</strong> {result.reason_code}
      </p>
      <p><strong>Reason:</strong> {result.reason}</p>

      {result.current_stage && (
        <p><strong>Current stage:</strong> {result.current_stage}</p>
      )}

      {result.role_code && (
        <p><strong>Role:</strong> {result.role_code}</p>
      )}

      {result.grant_id !== undefined && (
        <p><strong>Grant:</strong> #{result.grant_id}</p>
      )}

      {result.grant_scope && (
        <div style={{ marginTop: '1rem' }}>
          <strong>Grant scope</strong>
          <p>Client: {result.grant_scope.client ?? '-'}</p>
          <p>Branch: {result.grant_scope.branch ?? '-'}</p>
          <p>Direction: {result.grant_scope.direction ?? '-'}</p>
          <p>Mode: {result.grant_scope.mode ?? '-'}</p>
        </div>
      )}
    </Tile>
  );
}

