import { createTheme } from '@mui/material/styles'

// Design tokens reutilizables para estilos (gradientes, radios, sombras, paleta extendida)
export const designTokens = {
  colors: {
    golden: {
      50: '#FFF9DB',
      100: '#FFF0A6',
      200: '#FFE46B',
      300: '#FFD940',
      400: '#FFCC1A',
      500: '#FFD700', // dorado base
      600: '#E6C200',
      700: '#CCAC00',
    },
    charcoal: {
      50: '#F5F5F6',
      100: '#E9EAEC',
      200: '#D4D6DA',
      300: '#B7BAC1',
      600: '#565A64',
      800: '#2F3340',
      900: '#1E2230',
    },
    semantic: {
      success: '#4CAF50',
      error: '#F44336',
      warning: '#FF9800',
    },
    aurora: {
      // Gradientes y fondos translúcidos usados en páginas públicas
      sunset: 'linear-gradient(135deg, #FFB800 0%, #FF6A00 100%)',
      golden: 'linear-gradient(135deg, #FFD700 0%, #FF8A00 100%)',
      glassMorph: 'rgba(255, 255, 255, 0.15)',
    },
  },
  radius: {
    sm: 6,
    md: 8,
    lg: 12,
    xl: 20,
    full: 9999,
  },
  shadows: {
    medium: '0 8px 24px rgba(0,0,0,0.12)',
    glowHover: '0 10px 30px rgba(255, 215, 0, 0.35), 0 4px 12px rgba(0,0,0,0.1)',
  },
}

// Colores de Pablo's Pizza - Negro y Amarillo
const theme = createTheme({
  palette: {
    primary: {
      main: '#FFD700', // Amarillo dorado
      light: '#FFED4E',
      dark: '#CCAC00',
      contrastText: '#000000',
    },
    secondary: {
      main: '#000000', // Negro
      light: '#333333',
      dark: '#000000',
      contrastText: '#FFFFFF',
    },
    background: {
      default: '#FAFAFA',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#333333',
      secondary: '#666666',
    },
    success: {
      main: '#4CAF50',
    },
    error: {
      main: '#F44336',
    },
    warning: {
      main: '#FF9800',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 700,
      fontSize: '2.5rem',
      color: '#000000',
    },
    h2: {
      fontWeight: 600,
      fontSize: '2rem',
      color: '#000000',
    },
    h3: {
      fontWeight: 600,
      fontSize: '1.5rem',
      color: '#000000',
    },
    h4: {
      fontWeight: 500,
      fontSize: '1.25rem',
      color: '#000000',
    },
    h5: {
      fontWeight: 500,
      fontSize: '1.125rem',
      color: '#000000',
    },
    h6: {
      fontWeight: 500,
      fontSize: '1rem',
      color: '#000000',
    },
    subtitle1: {
      fontSize: '1rem',
      fontWeight: 400,
      color: '#666666',
    },
    body1: {
      fontSize: '0.875rem',
      color: '#333333',
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 600,
          padding: '10px 24px',
        },
        containedPrimary: {
          backgroundColor: '#FFD700',
          color: '#000000',
          '&:hover': {
            backgroundColor: '#CCAC00',
          },
        },
        containedSecondary: {
          backgroundColor: '#000000',
          color: '#FFFFFF',
          '&:hover': {
            backgroundColor: '#333333',
          },
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#000000',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
          border: '1px solid #f0f0f0',
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

export default theme