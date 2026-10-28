import { useEffect, useState } from 'react';

import {
  Dropdown,
  DataTable,
  Table,
  TableHead,
  TableRow,
  TableHeader,
  TableBody,
  TableCell,
  TableContainer,
  InlineLoading,
  InlineNotification,
  Tag,
} from '@carbon/react';

import { useUser } from '../context/UserContext';

type WaitingJob = {
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
  jobs: WaitingJob[];
};

const actions = [
  'prepare',
  'check',
  'file',
  'cancel',
  'reopen',
  'approve',
  'reject',
];

export function WaitingPage() {
  const { currentUserId, currentUser } = useUser();

  const [selectedAction, setSelectedAction] = useState('prepare');
  const [data, setData] = useState<WaitingResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

  useEffect(() => {
    if (currentUserId === null) {
      return;
    }

    setLoading(true);
    setError(null);

    fetch(
      `${API_BASE_URL}/api/jobs/waiting?user_id=${currentUserId}&action=${selectedAction}`
    )
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to load waiting jobs');
        }

        return response.json();
      })
      .then((result: WaitingResponse) => {
        setData(result);
      })
      .catch((error) => {
        setError(error.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [currentUserId, selectedAction, API_BASE_URL]);

  const headers = [
    { key: 'ref', header: 'Job' },
    { key: 'client_id', header: 'Client' },
    { key: 'branch_id', header: 'Branch' },
    { key: 'direction', header: 'Direction' },
    { key: 'mode', header: 'Mode' },
    { key: 'stage', header: 'Stage' },
    { key: 'role_code', header: 'Role' }
  ];

  const rows =
    data?.jobs.map((job) => ({
      id: String(job.id),
      ref: job.ref,
      client_id: job.client_id,
      branch_id: job.branch_id,
      direction: job.direction,
      mode: job.mode,
      stage: job.stage,
      role_code: job.role_code,
    })) ?? [];

  return (
    <>
      <h1>Waiting</h1>

      <p style={{ marginTop: '0.5rem', marginBottom: '2rem' }}>
        Jobs currently available to {currentUser?.name ?? 'selected user'}
      </p>

      <div style={{ width: '250px', marginBottom: '2rem' }}>
        <Dropdown
          id="action-dropdown"
          titleText="Action"
          label="Select action"
          items={actions}
          selectedItem={selectedAction}
          onChange={({ selectedItem }) => {
            if (selectedItem) {
              setSelectedAction(selectedItem);
            }
          }}
        />
      </div>

      {loading && (
        <InlineLoading description="Loading waiting jobs..." />
      )}

      {error && (
        <InlineNotification
          kind="error"
          title="Unable to load jobs"
          subtitle={error}
        />
      )}

      {!loading && !error && data && (
        <>
          <p style={{ marginBottom: '1rem' }}>
            Found <strong>{data.count}</strong> job(s) for action{' '}
            <strong>{data.action}</strong>
          </p>

          <DataTable rows={rows} headers={headers}>
            {({
              rows,
              headers,
              getTableProps,
              getHeaderProps,
              getRowProps,
            }) => (
              <TableContainer title="Available jobs">
                <Table {...getTableProps()}>
                  <TableHead>
                    <TableRow>
                      {headers.map((header) => (
                        <TableHeader
                          {...getHeaderProps({
                            header,
                          })}
                        >
                          {header.header}
                        </TableHeader>
                      ))}
                    </TableRow>
                  </TableHead>

                  <TableBody>
                    {rows.map((row) => (
                      <TableRow
                        {...getRowProps({
                          row,
                        })}
                      >
                        {row.cells.map((cell) => (
                          <TableCell key={cell.id}>
                            {cell.info.header === 'stage' ? (
                              <Tag type="blue">
                                {String(cell.value)}
                              </Tag>
                            ) : (
                              String(cell.value ?? '')
                            )}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </DataTable>
        </>
      )}
    </>
  );
}