import {
  DataTable,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
  Tag,
} from '@carbon/react';

type Header = { key: string; header: string };
type Row = Record<string, unknown> & { id: string };

type Props = {
  title: string;
  headers: Header[];
  rows: Row[];
  onRowClick?: (rowId: string) => void;
  /** Column key whose value should be rendered as a blue Tag */
  stageColumnKey?: string;
};

/**
 * Generic Carbon DataTable with optional row-click and stage-tag rendering.
 */
export function JobsTable({
  title,
  headers,
  rows,
  onRowClick,
  stageColumnKey = 'stage',
}: Props) {
  return (
    <DataTable rows={rows} headers={headers}>
      {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
        <TableContainer title={title}>
          <Table {...getTableProps()}>
            <TableHead>
              <TableRow>
                {headers.map((header) => (
                  <TableHeader {...getHeaderProps({ header })}>
                    {header.header}
                  </TableHeader>
                ))}
              </TableRow>
            </TableHead>

            <TableBody>
              {rows.map((row) => (
                <TableRow
                  {...getRowProps({ row })}
                  onClick={() => onRowClick?.(row.id)}
                  style={onRowClick ? { cursor: 'pointer' } : undefined}
                >
                  {row.cells.map((cell) => (
                    <TableCell key={cell.id}>
                      {cell.info.header === stageColumnKey ? (
                        <Tag type="blue">{String(cell.value)}</Tag>
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
  );
}

