import { Button, TextArea } from '@carbon/react';

type Props = {
  approvalId: number;
  reason: string;
  loading: boolean;
  canApprove: boolean;
  canReject: boolean;
  onReasonChange: (id: number, value: string) => void;
  onDecide: (id: number, decision: 'approved' | 'rejected') => void;
};

/**
 * The decision cell for a single approval row: reason textarea + approve/reject buttons.
 */
export function ApprovalDecisionCell({
  approvalId,
  reason,
  loading,
  canApprove,
  canReject,
  onReasonChange,
  onDecide,
}: Props) {
  return (
    <div style={{ minWidth: '320px' }}>
      <TextArea
        id={`decision-reason-${approvalId}`}
        labelText="Decision reason"
        placeholder="Enter reason"
        value={reason}
        onChange={(event) => onReasonChange(approvalId, event.target.value)}
      />

      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
        {canApprove && (
          <Button
            size="sm"
            onClick={() => onDecide(approvalId, 'approved')}
            disabled={loading}
          >
            Approve
          </Button>
        )}

        {canReject && (
          <Button
            size="sm"
            kind="danger"
            onClick={() => onDecide(approvalId, 'rejected')}
            disabled={loading}
          >
            Reject
          </Button>
        )}
      </div>
    </div>
  );
}

