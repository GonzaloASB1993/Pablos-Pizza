import { useState, useEffect, useCallback } from 'react'
import {
    Autocomplete,
    TextField,
    Box,
    Typography,
    CircularProgress,
    Chip,
    Paper
} from '@mui/material'
import { PersonAdd, Person } from '@mui/icons-material'
import { customersAPI } from '../../services/api'
import { debounce } from 'lodash'

/**
 * CustomerAutocomplete Component
 *
 * Intelligent autocomplete for customer selection with real-time search.
 * Features:
 * - Real-time search with 300ms debounce
 * - "Create new customer" option when no results
 * - Auto-fill form fields on selection
 * - Loading states and error handling
 *
 * @param {Object} props
 * @param {Object} props.value - Selected customer object
 * @param {Function} props.onChange - Callback with selected customer
 * @param {Function} props.onCreateNew - Callback when "create new" is clicked
 * @param {boolean} props.required - Field is required
 * @param {boolean} props.disabled - Field is disabled
 */
const CustomerAutocomplete = ({
    value,
    onChange,
    onCreateNew,
    required = false,
    disabled = false
}) => {
    const [inputValue, setInputValue] = useState('')
    const [options, setOptions] = useState([])
    const [loading, setLoading] = useState(false)
    const [open, setOpen] = useState(false)

    // Debounced search function
    const searchCustomers = useCallback(
        debounce(async (query) => {
            if (!query || query.length < 2) {
                setOptions([])
                setLoading(false)
                return
            }

            try {
                setLoading(true)
                const response = await customersAPI.search(query)
                const customers = response.data.results || []

                // Add "Create new" option at the end if we have a query
                const optionsWithCreate = [
                    ...customers,
                    {
                        id: 'create-new',
                        name: `Crear nuevo cliente "${query}"`,
                        isCreateNew: true
                    }
                ]

                setOptions(optionsWithCreate)
            } catch (error) {
                console.error('Error searching customers:', error)
                // On error, show create new option only
                setOptions([
                    {
                        id: 'create-new',
                        name: `Crear nuevo cliente "${query}"`,
                        isCreateNew: true
                    }
                ])
            } finally {
                setLoading(false)
            }
        }, 300),
        []
    )

    useEffect(() => {
        if (inputValue) {
            setLoading(true)
            searchCustomers(inputValue)
        } else {
            setOptions([])
        }

        // Cleanup
        return () => {
            searchCustomers.cancel()
        }
    }, [inputValue, searchCustomers])

    const handleChange = (event, newValue) => {
        if (newValue && newValue.isCreateNew) {
            // User selected "Create new customer"
            onCreateNew && onCreateNew(inputValue)
            setInputValue('')
            setOptions([])
        } else {
            // User selected an existing customer
            onChange(newValue)
        }
    }

    const handleInputChange = (event, newInputValue, reason) => {
        if (reason === 'input') {
            setInputValue(newInputValue)
        } else if (reason === 'clear') {
            setInputValue('')
            onChange(null)
        }
    }

    return (
        <Autocomplete
            fullWidth
            open={open}
            onOpen={() => setOpen(true)}
            onClose={() => setOpen(false)}
            value={value}
            onChange={handleChange}
            inputValue={inputValue}
            onInputChange={handleInputChange}
            options={options}
            loading={loading}
            disabled={disabled}
            isOptionEqualToValue={(option, value) => option.id === value.id}
            getOptionLabel={(option) => {
                if (option.isCreateNew) return option.name
                return option.name || ''
            }}
            filterOptions={(x) => x} // Disable built-in filtering (we do server-side search)
            noOptionsText="Escribe para buscar clientes..."
            loadingText="Buscando..."
            renderInput={(params) => (
                <TextField
                    {...params}
                    label="Cliente"
                    required={required}
                    placeholder="Buscar cliente por nombre, email o teléfono..."
                    InputProps={{
                        ...params.InputProps,
                        endAdornment: (
                            <>
                                {loading ? <CircularProgress color="inherit" size={20} /> : null}
                                {params.InputProps.endAdornment}
                            </>
                        ),
                    }}
                    helperText="Escribe al menos 2 caracteres para buscar"
                />
            )}
            renderOption={(props, option) => {
                // Extract key from props to avoid React warning
                const { key, ...otherProps } = props

                if (option.isCreateNew) {
                    return (
                        <Box
                            component="li"
                            key={key}
                            {...otherProps}
                            sx={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 1,
                                borderTop: '1px solid #e0e0e0',
                                backgroundColor: '#f5f5f5',
                                '&:hover': {
                                    backgroundColor: '#e0e0e0'
                                }
                            }}
                        >
                            <PersonAdd color="primary" />
                            <Typography variant="body1" color="primary" sx={{ fontWeight: 600 }}>
                                {option.name}
                            </Typography>
                        </Box>
                    )
                }

                return (
                    <Box
                        component="li"
                        key={key}
                        {...otherProps}
                        sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 1 }}
                    >
                        <Person color="action" />
                        <Box sx={{ flex: 1 }}>
                            <Typography variant="body1" sx={{ fontWeight: 600 }}>
                                {option.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                {option.email}
                            </Typography>
                            {option.phone && (
                                <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                                    • {option.phone}
                                </Typography>
                            )}
                            {option.total_bookings > 0 && (
                                <Chip
                                    label={`${option.total_bookings} reserva${option.total_bookings > 1 ? 's' : ''}`}
                                    size="small"
                                    color="primary"
                                    variant="outlined"
                                    sx={{ ml: 1, height: 20, fontSize: '0.7rem' }}
                                />
                            )}
                        </Box>
                    </Box>
                )
            }}
            PaperComponent={({ children }) => (
                <Paper elevation={8}>
                    {children}
                </Paper>
            )}
        />
    )
}

export default CustomerAutocomplete
