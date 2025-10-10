import { createTheme } from '@mui/material/styles'

// Dark theme for Pablo's Pizza - Optimized for admin panel
const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#FFD700', // Amarillo dorado
      light: '#FFED4E',
      dark: '#CCAC00',
      contrastText: '#000000',
    },
    secondary: {
      main: '#FFFFFF', // Blanco para dark mode
      light: '#FFFFFF',
      dark: '#CCCCCC',
      contrastText: '#000000',
    },
    background: {
      default: '#121212',  // Material Design dark surface
      paper: '#1E1E1E',     // Elevated surface
    },
    text: {
      primary: '#FFFFFF',
      secondary: 'rgba(255, 255, 255, 0.7)',
    },
    success: {
      main: '#66BB6A',  // Lighter for dark backgrounds
    },
    error: {
      main: '#EF5350',
    },
    warning: {
      main: '#FFA726',
    },
    info: {
      main: '#29B6F6',
    },
    divider: 'rgba(255, 255, 255, 0.12)',
  },
  // Chart.js colors for dark mode
  charts: {
    income: {
      border: '#FFD700',
      background: 'rgba(255, 215, 0, 0.2)',
    },
    expenses: {
      border: '#EF5350',
      background: 'rgba(239, 83, 80, 0.2)',
    },
    pieColors: [
      '#FF6384',
      '#36A2EB',
      '#FFCE56',
      '#4BC0C0',
      '#9966FF',
      '#FF9F40',
    ],
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 700,
      fontSize: '2.5rem',
      color: '#FFFFFF'
    },
    h2: {
      fontWeight: 600,
      fontSize: '2rem',
      color: '#FFFFFF'
    },
    h3: {
      fontWeight: 600,
      fontSize: '1.5rem',
      color: '#FFFFFF'
    },
    h4: {
      fontWeight: 500,
      fontSize: '1.25rem',
      color: '#FFFFFF'
    },
    h5: {
      fontWeight: 500,
      fontSize: '1.125rem',
      color: '#FFFFFF'
    },
    h6: {
      fontWeight: 500,
      fontSize: '1rem',
      color: '#FFFFFF'
    },
    subtitle1: {
      fontSize: '1rem',
      fontWeight: 400,
      color: 'rgba(255, 255, 255, 0.7)',
    },
    body1: {
      fontSize: '0.875rem',
      color: '#FFFFFF',
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.05))',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:focus-visible': {
            outline: '3px solid #FFD700',
            outlineOffset: '4px',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.05))',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 600,
          padding: '10px 24px',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:focus-visible': {
            outline: '3px solid #FFD700',
            outlineOffset: '2px',
          },
        },
        containedPrimary: {
          backgroundColor: '#FFD700',
          color: '#000000',
          '&:hover': {
            backgroundColor: '#FFED4E',
          },
        },
        containedSecondary: {
          backgroundColor: '#FFFFFF',
          color: '#000000',
          '&:hover': {
            backgroundColor: '#CCCCCC',
          },
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          minWidth: 48,
          minHeight: 48,
          '&:hover': {
            backgroundColor: 'rgba(255, 215, 0, 0.08)',
          },
          '&:focus-visible': {
            outline: '3px solid #FFD700',
            outlineOffset: '2px',
          },
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#1E1E1E',
          boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
            '&:hover fieldset': {
              borderColor: '#FFD700',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#FFD700',
            },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 16,
        },
        colorPrimary: {
          backgroundColor: '#FFD700',
          color: '#000000',
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        root: {
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: '#FFD700',
          },
        },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          '&:hover': {
            backgroundColor: 'rgba(255, 215, 0, 0.1)',
          },
          '&.Mui-selected': {
            backgroundColor: 'rgba(255, 215, 0, 0.2)',
            '&:hover': {
              backgroundColor: 'rgba(255, 215, 0, 0.3)',
            },
          },
        },
      },
    },
  },
  breakpoints: {
    values: {
      xs: 0,
      sm: 600,
      md: 900,
      lg: 1200,
      xl: 1536,
    },
  },
})

export default darkTheme
