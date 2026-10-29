import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import {
  DataTable,
  InlineLoading,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
} from '@carbon/react';

import { useUser } from '../context/UserContext';
import { useApprovals } from '../hooks/useApprovals';
import { ApprovalDecisionCell } from '../components/ApprovalDecisionCell';
import { StatusNotifications } from '../components/StatusNotifications';

const HEADERS = [
  { key: 'id', header: 'Approval' },
  { key: 'job_id', header: 'Job' },
  { key: 'action', header: 'Action' },
  { key: 'requested_by', header: 'Requested by' },
  { key: 'reason', header: 'Request reason' },
];

export function ApprovalsPage() {
  const { currentUserId, currentUser, permissions } = useUser();
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

  const canApprove = permissions.includes('approve');
  const canReject = permissions.includes('reject');

  if (!canApprove && !canReject) {
    return <Navigate to="/jobs" replace />;
  }

  const { approvals, setApprovals, loading, error, setError } =
    useApprovals(API_BASE_URL);

  const [decisionReasons, setDecisionReasons] = useState<Record<number, string>>({});
  const [decisionLoading, setDecisionLoading] = useState<number | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  function handleReasonChange(id: number, value: string) {
    setDecisionReasons((current) => ({ ...current, [id]: value }));
  }

  function decideApproval(approvalId: number, decision: 'approved' | 'rejected') {
    if (currentUserId === null) return;

    setDecisionLoading(approvalId);
    setError(null);
    setSuccess(null);

    fetch(`${API_BASE_URL}/api/jobs/approvals/${approvalId}/decide`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: currentUserId, decision }),
    })
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok) {
          const detail = result.detail;
          if (typeof detail === 'string') throw new Error(detail);
          if (detail?.reason) throw new Error(detail.reason);
          if (detail?.message) throw new Error(detail.message);
          throw new Error('Failed to decide approval');
        }
        return result;
      })
      .then(() => {
        setSuccess(
          `Approval #${approvalId} ${decision === 'approved' ? 'approved' : 'rejected'} successfully.`
        );
        setApprovals((current) =>
          current.filter((a) => a.id !== approvalId)
        );
      })
      .catch((err) => setError(err.message))
      .finally(() => setDecisionLoading(null));
  }

  const rows = approvals.map((approval) => ({
    id: String(approval.id),
    approval_id: approval.id,
    job_id: approval.job_id,
    action: approval.action,
    requested_by: approval.requested_by,
    reason: approval.reason ?? '-',
  }));

  return (
    <>
      <h1>Approvals</h1>

      <p style={{ marginTop: '0.5rem', marginBottom: '2rem' }}>
        Pending approvals for <strong>{currentUser?.name}</strong>
      </p>

      {loading && <InlineLoading description="Loading approvals..." />}

      <StatusNotifications
        error={error}
        success={success}
        errorStyle={{ marginBottom: '1rem' }}
        successStyle={{ marginBottom: '1rem' }}
      />

      {!loading && approvals.length === 0 && <p>No pending approvals.</p>}

      {!loading && approvals.length > 0 && (
        <DataTable rows={rows} headers={HEADERS}>
          {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
            <TableContainer title="Pending approvals">
              <Table {...getTableProps()}>
                <TableHead>
                  <TableRow>
                    {headers.map((header) => (
                      <TableHeader {...getHeaderProps({ header })}>
                        {header.header}
                      </TableHeader>
                    ))}
                    <TableHeader>Decision</TableHeader>
                  </TableRow>
                </TableHead>

                <TableBody>
                  {rows.map((row) => {
                    const approvalId = Number(row.id);
                    return (
                      <TableRow {...getRowProps({ row })}>
                        {row.cells.map((cell) => (
                          <TableCell key={cell.id}>
                            {String(cell.value ?? '')}
                          </TableCell>
                        ))}

                        <TableCell>
                          <ApprovalDecisionCell
                            approvalId={approvalId}
                            reason={decisionReasons[approvalId] ?? ''}
                            loading={decisionLoading === approvalId}
                            canApprove={canApprove}
                            canReject={canReject}
                            onReasonChange={handleReasonChange}
                            onDecide={decideApproval}
                          />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </DataTable>
      )}
    </>
  );
}
