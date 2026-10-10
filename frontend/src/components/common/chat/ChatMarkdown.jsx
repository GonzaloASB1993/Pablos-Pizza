import { memo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Box } from '@mui/material'

// Raw HTML is NOT enabled (react-markdown ignores it by default); links open in a new tab.
// Markdown images are removed: the browser would fetch the URL on its own, which lets
// text injected through a receipt photo leak data in the query string.
const DISALLOWED = ['img']

const components = {
  a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />,
  table: ({ node, ...props }) => (
    <Box sx={{ overflowX: 'auto', my: 1 }}>
      <table {...props} />
    </Box>
  )
}

const ChatMarkdown = ({ children }) => (
  <Box
    sx={{
      wordBreak: 'break-word',
      fontSize: '0.95rem',
      lineHeight: 1.55,
      '& > :first-of-type': { mt: 0 },
      '& > :last-child': { mb: 0 },
      '& p': { my: 0.75 },
      '& ul, & ol': { pl: 3, my: 0.75 },
      '& li': { mb: 0.25 },
      '& h1, & h2, & h3, & h4': { fontSize: '1rem', fontWeight: 700, mt: 1.5, mb: 0.5 },
      '& code': {
        fontFamily: 'monospace',
        fontSize: '0.85em',
        px: 0.5,
        borderRadius: 0.5,
        bgcolor: 'action.hover'
      },
      '& table': { borderCollapse: 'collapse', fontSize: '0.85rem', minWidth: '100%' },
      '& th, & td': {
        border: 1,
        borderColor: 'divider',
        px: 1,
        py: 0.5,
        textAlign: 'left',
        whiteSpace: 'nowrap'
      },
      '& th': { bgcolor: 'action.hover', fontWeight: 700 },
      '& a': { color: 'primary.main' }
    }}
  >
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components} disallowedElements={DISALLOWED}>
      {children}
    </ReactMarkdown>
  </Box>
)

export default memo(ChatMarkdown)
