import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
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

type JobsResponse = {
  user_id: number;
  action: string;
  count: number;
  jobs: Job[];
};


export function JobsPage() {
  const { currentUserId, currentUser } = useUser();

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

  const [jobs, setJobs] = useState<Job[]>([]);


  const [jobsLoading, setJobsLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  // Load all jobs this user can VIEW
  useEffect(() => {
    if (currentUserId === null) {
      return;
    }

    setJobsLoading(true);
    setError(null);


    fetch(
      `${API_BASE_URL}/api/jobs/waiting?user_id=${currentUserId}&action=view`
    )
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to load jobs');
        }

        return response.json();
      })
      .then((result: JobsResponse) => {
        setJobs(result.jobs);
      })
      .catch((error) => {
        setError(error.message);
      })
      .finally(() => {
        setJobsLoading(false);
      });
  }, [currentUserId, API_BASE_URL]);

  const navigate = useNavigate();

  const headers = [
    { key: 'ref', header: 'Job' },
    { key: 'client_id', header: 'Client' },
    { key: 'branch_id', header: 'Branch' },
    { key: 'direction', header: 'Direction' },
    { key: 'mode', header: 'Mode' },
    { key: 'stage', header: 'Stage' },
  ];

  const rows = jobs.map((job) => ({
    id: String(job.id),
    ref: job.ref,
    client_id: job.client_id,
    branch_id: job.branch_id,
    direction: job.direction,
    mode: job.mode,
    stage: job.stage,
  }));

  return (
    <>
      <h1>Jobs</h1>

      <p style={{ marginTop: '0.5rem', marginBottom: '2rem' }}>
        Jobs visible to {currentUser?.name ?? 'selected user'}
      </p>

      {jobsLoading && (
        <InlineLoading description="Loading jobs..." />
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

      {!jobsLoading && jobs.length === 0 && (
        <InlineNotification
          kind="info"
          title="No visible jobs"
          subtitle="This user is not currently allowed to view any jobs."
        />
      )}

      {!jobsLoading && jobs.length > 0 && (
        <DataTable rows={rows} headers={headers}>
          {({
            rows,
            headers,
            getTableProps,
            getHeaderProps,
            getRowProps,
          }) => (
            <TableContainer title="Visible jobs">
              <Table {...getTableProps()}>
                <TableHead>
                  <TableRow>
                    {headers.map((header) => (
                      <TableHeader
                        {...getHeaderProps({ header })}
                      >
                        {header.header}
                      </TableHeader>
                    ))}
                  </TableRow>
                </TableHead>

                <TableBody>
                  {rows.map((row) => {
                    
                    return (
                      <TableRow
                        {...getRowProps({ row })}
                        onClick={() => {
                          navigate(`/jobs/${row.id}`);
                        }}
                        style={{ cursor: 'pointer' }}
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