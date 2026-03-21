import { useTheme, useMediaQuery, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Stack } from '@mui/material'

/**
 * Renders a standard MUI Table on desktop (md+) and a Stack of cards on mobile.
 *
 * Props:
 *   columns     - array of { field, label, render? } for desktop table headers
 *   rows        - array of data objects
 *   mobileCardRender - (row, index) => ReactNode — renders one card per row on mobile
 *   onRowClick  - optional (row) => void for desktop row click
 *   stickyHeader - boolean (default false)
 */
const ResponsiveTable = ({ columns = [], rows = [], mobileCardRender, onRowClick, stickyHeader = false }) => {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))

  if (isMobile && mobileCardRender) {
    return (
      <Stack spacing={1.5}>
        {rows.map((row, i) => mobileCardRender(row, i))}
      </Stack>
    )
  }

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table stickyHeader={stickyHeader} size="small">
        <TableHead>
          <TableRow>
            {columns.map((col) => (
              <TableCell key={col.field} sx={{ fontWeight: 700, whiteSpace: 'nowrap' }}>
                {col.label}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow
              key={row.id || i}
              hover={!!onRowClick}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              sx={onRowClick ? { cursor: 'pointer' } : undefined}
            >
              {columns.map((col) => (
                <TableCell key={col.field}>
                  {col.render ? col.render(row) : row[col.field]}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

export default ResponsiveTable
