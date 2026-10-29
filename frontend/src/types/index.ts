// Shared domain types used across pages and hooks

export type Job = {
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

export type Action = {
  code: string;
  from_stages: string[] | null;
  to_stage: string | null;
  approvals_required: number;
};

export type HistoryItem = {
  id: number;
  actor_id: number;
  actor_name: string;
  action: string;
  from_stage: string | null;
  to_stage: string | null;
  outcome: string;
  grant_id: number | null;
  reason: string | null;
  at: string;
};

export type Approval = {
  id: number;
  job_id: number;
  action: string;
  requested_by: number;
  reason: string | null;
  decided_by: number | null;
};

export type AuthorizationResponse = {
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

// API response wrappers

export type ActionsResponse = {
  actions: Action[];
};

export type WaitingResponse = {
  user_id: number;
  action: string;
  count: number;
  jobs: Job[];
};

export type HistoryResponse = {
  job_id: number;
  history: HistoryItem[];
};

export type ApprovalsResponse = {
  approvals: Approval[];
};

