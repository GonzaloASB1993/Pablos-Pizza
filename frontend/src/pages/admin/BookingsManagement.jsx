import { useState, useEffect, useMemo } from 'react'
import {
    Box,
    Typography,
    Card,
    CardContent,
    Button,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Chip,
    Paper,
    ToggleButton,
    ToggleButtonGroup,
    Grid,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Alert,
    IconButton,
    Tabs,
    Tab,
    CircularProgress,
    Tooltip,
    Accordion,
    AccordionSummary,
    AccordionDetails
} from '@mui/material'
import {
    Add,
    Edit,
    Delete,
    ViewList,
    CalendarMonth,
    CheckCircle,
    Cancel,
    Close,
    PendingActions,
    EventAvailable,
    Assignment,
    TrendingUp,
    Refresh,
    AddBox,
    Search,
    ArrowUpward,
    ArrowDownward,
    UnfoldMore,
    ExpandMore
} from '@mui/icons-material'
import { Calendar, dateFnsLocalizer } from 'react-big-calendar'
import { format, parse, startOfWeek, getDay } from 'date-fns'
import { es } from 'date-fns/locale'
import { bookingsAPI, eventsAPI, inventoryAPI, eventSuppliesAPI, eventConsumptionAPI } from '../../services/api'
import { formatCurrency, formatStock, safeFormatCost, formatDateTime } from '../../utils/formatters'
import toast from 'react-hot-toast'
import 'react-big-calendar/lib/css/react-big-calendar.css'

const locales = { 'es': es }
const localizer = dateFnsLocalizer({
    format,
    parse,
    startOfWeek: (date) => startOfWeek(date, { weekStartsOn: 1 }), // Monday = 1
    getDay,
    locales,
})

const BookingsManagement = () => {
    const [bookings, setBookings] = useState([])
    const [view, setView] = useState('table')
    const [loading, setLoading] = useState(true)
    const [updating, setUpdating] = useState(false)
    const [selectedMonth, setSelectedMonth] = useState("")
    // '' => mostrar Pendientes y Confirmados por defecto
    const [statusFilter, setStatusFilter] = useState('')
    const [searchQuery, setSearchQuery] = useState('')
    const [tabValue, setTabValue] = useState(0)
    const [sortField, setSortField] = useState('event_date')
    const [sortDirection, setSortDirection] = useState('asc')
    const [editDialog, setEditDialog] = useState(false)
    const [createDialog, setCreateDialog] = useState(false)
    const [deleteDialog, setDeleteDialog] = useState(false)
    const [viewDialog, setViewDialog] = useState(false)
    const [costDialog, setCostDialog] = useState(false)
    const [expenseDialog, setExpenseDialog] = useState(false)
    const [editExpenseDialog, setEditExpenseDialog] = useState(false)
    const [selectedExpenseIndex, setSelectedExpenseIndex] = useState(null)
    const [selectedBooking, setSelectedBooking] = useState(null)
    const [costData, setCostData] = useState({
        event_cost: '',
        event_revenue: '',
        notes: ''
    })
    const [expenseData, setExpenseData] = useState({
        description: '',
        amount: '',
        category: 'ingredientes'
    })

    // States for integrated supplies and consumption management
    const [costTabValue, setCostTabValue] = useState(0) // 0: gastos, 1: insumos
    const [inventoryItems, setInventoryItems] = useState([])
    const [integratedSupplies, setIntegratedSupplies] = useState({
        items: [], // Each item has: estimated_quantity, actual_quantity_consumed, item_id, etc.
        notes: '',
        consumption_notes: ''
    })
    const [supplyStatus, setSupplyStatus] = useState({
        has_supplies: false,
        has_consumption: false,
        can_complete_event: false
    })
    const [loadingSupplies, setLoadingSupplies] = useState(false)
    const [formData, setFormData] = useState({
        status: '',
        notes: '',
        event_date: '',
        event_time: '',
        service_type: '',
        participants: '',
        estimated_price: '',
        client_name: '',
        client_email: '',
        client_phone: '',
        location: '',
        pizzeros_participants: 0,
        party_participants: 0,
        party_guests: 0, // Nueva field para personas en pizza party
        pizza_quantity: 10
    })
    const [newBookingData, setNewBookingData] = useState({
        client_name: '',
        client_email: '',
        client_phone: '',
        service_type: '',
        event_type: '',
        event_date: '',
        event_time: '',
        duration_hours: 4,
        participants: '',
        pizzeros_participants: 0,
        party_participants: 0,
        party_guests: 0, // Nueva field para personas en pizza party
        pizza_quantity: 10,
        location: '',
        special_requests: ''
    })

    // Calculate estimated price based on service types and participants
    const calculateEstimatedPrice = (serviceTypes, pizParams = 0, partyParams = 0, legacyParams = 0) => {
        let totalPrice = 0
        const services = serviceTypes ? serviceTypes.split(',').map(s => s.trim()).filter(s => s) : []

        for (const service of services) {
            if (service === 'workshop' || service === 'pizzeros') {
                // Pizzeros en Acción pricing
                const participants = pizParams > 0 ? pizParams : legacyParams
                if (participants <= 0) continue

                let serviceTotal = 0
                if (participants <= 10) {
                    serviceTotal = Math.max(135000, participants * 13500)  // $13,500/niño con mínimo $135,000
                } else if (participants <= 14) {
                    serviceTotal = participants * 10500
                } else if (participants <= 19) {
                    serviceTotal = participants * 9500
                } else {
                    serviceTotal = participants * 9000
                }
                totalPrice += serviceTotal

            } else if (service === 'pizza_party' || service === 'party') {
                // Pizza Party pricing
                const participants = partyParams > 0 ? partyParams : legacyParams
                if (participants <= 0) continue

                const unitBase = 11990  // DEFAULT_PIZZA_PARTY_PRICE
                const unitFinal = participants >= 20 ? Math.round(unitBase * 0.9) : unitBase
                const serviceTotal = unitFinal * participants
                totalPrice += serviceTotal
            }
        }

        return Math.round(totalPrice)
    }

    // Utility functions moved before their usage
    const getServiceLabel = (type) => {
        if (!type) return 'No especificado'

        // Manejar múltiples servicios separados por coma
        if (type.includes(',')) {
            const services = type.split(',').map(s => s.trim())
            return services.map(s => s === 'workshop' ? 'Pizzeros en Acción' : 'Pizza Party').join(' + ')
        }

        // Servicio único
        return type === 'workshop' ? 'Pizzeros en Acción' : 'Pizza Party'
    }

    // Función para calcular pizzas sugeridas
    const calculateSuggestedPizzas = (guests) => {
        // Cada persona come 5 rebanadas, cada pizza tiene 8 rebanadas
        return Math.ceil((guests * 5) / 8)
    }

    const getStatusLabel = (status) => {
        const labels = {
            pending: 'Pendiente',
            confirmed: 'Confirmado',
            completed: 'Completado',
            cancelled: 'Cancelado'
        }
        return labels[status] || status
    }

    const getStatusColor = (status) => {
        const colors = {
            pending: 'warning',
            confirmed: 'success',
            completed: 'info',
            cancelled: 'error'
        }
        return colors[status] || 'default'
    }

    const filteredBookings = useMemo(() => {
        let filtered = bookings

        // Filter by month
        if (selectedMonth) {
            filtered = filtered.filter(booking => {
                if (!booking.event_date) return false
                const eventDate = parseEventDate(booking.event_date)
                if (!eventDate) return false
                const eventMonth = `${String(eventDate.getMonth() + 1).padStart(2, '0')}-${eventDate.getFullYear()}`
                return eventMonth === selectedMonth
            })
        }

        // Filter by search query
        if (searchQuery) {
            const query = searchQuery.toLowerCase()
            filtered = filtered.filter(booking =>
                booking.client_name?.toLowerCase().includes(query) ||
                booking.client_phone?.toLowerCase().includes(query) ||
                booking.client_email?.toLowerCase().includes(query) ||
                booking.location?.toLowerCase().includes(query) ||
                getServiceLabel(booking.service_type).toLowerCase().includes(query)
            )
        }

        // Apply status filter (default: pending + confirmed)
        if (statusFilter === '') {
            filtered = filtered.filter(b => ['pending', 'confirmed'].includes(b.status))
        } else {
            filtered = filtered.filter(b => b.status === statusFilter)
        }

        // Apply sorting
        filtered.sort((a, b) => {
            let aValue, bValue

            switch (sortField) {
                case 'client_name':
                    aValue = (a.client_name || '').toLowerCase()
                    bValue = (b.client_name || '').toLowerCase()
                    break
                case 'event_date':
                    aValue = a.event_date ? new Date(a.event_date).getTime() : 0
                    bValue = b.event_date ? new Date(b.event_date).getTime() : 0
                    break
                case 'service_type':
                    aValue = getServiceLabel(a.service_type).toLowerCase()
                    bValue = getServiceLabel(b.service_type).toLowerCase()
                    break
                case 'status':
                    aValue = (a.status || '').toLowerCase()
                    bValue = (b.status || '').toLowerCase()
                    break
                case 'participants':
                    aValue = a.participants || 0
                    bValue = b.participants || 0
                    break
                default:
                    aValue = 0
                    bValue = 0
            }

            if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1
            if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1
            return 0
        })

        return filtered
    }, [bookings, selectedMonth, searchQuery, statusFilter, sortField, sortDirection])

    const handleSort = (field) => {
        if (sortField === field) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
        } else {
            setSortField(field)
            setSortDirection('asc')
        }
    }

    const getSortIcon = (field) => {
        if (sortField !== field) {
            return <UnfoldMore sx={{ ml: 1, fontSize: 16, opacity: 0.5 }} />
        }
        return sortDirection === 'asc' ?
            <ArrowUpward sx={{ ml: 1, fontSize: 16 }} /> :
            <ArrowDownward sx={{ ml: 1, fontSize: 16 }} />
    }

    useEffect(() => {
        loadBookings()
    }, [])

    // Helper function to safely parse date strings without timezone shifts
    const parseEventDate = (dateString) => {
        if (!dateString) return null

        try {
            if (dateString.includes('T')) {
                // ISO format - extract date part only to avoid timezone issues
                const dateOnly = dateString.split('T')[0]
                const [year, month, day] = dateOnly.split('-').map(Number)
                return new Date(year, month - 1, day)
            } else {
                // Date-only string
                const [year, month, day] = dateString.split('-').map(Number)
                return new Date(year, month - 1, day)
            }
        } catch (error) {
            console.error('Error parsing date:', dateString, error)
            return null
        }
    }

    const loadBookings = async () => {
        try {
            setLoading(true)
            const response = await bookingsAPI.getAll()
            // Handle paginated response format: {items: [], pagination: {}}
            const bookingsData = response.data.items || response.data
            setBookings(bookingsData)
        } catch (error) {
            console.error('Error loading bookings:', error)
            toast.error('Error al cargar agendamientos')
        } finally {
            setLoading(false)
        }
    }

    // Helper function to calculate total cost (supplies + expenses)
    const calculateTotalCost = (booking) => {
        const accumulatedExpenses = (booking.expenses || []).reduce((sum, expense) => sum + expense.amount, 0)
        const supplyCost = booking.financials?.total_expenses || 0
        return supplyCost + accumulatedExpenses || booking.event_cost || 0
    }

    // Load inventory items for supplies management
    const loadInventoryItems = async () => {
        try {
            const response = await inventoryAPI.getAll()
            setInventoryItems(response.data || [])
        } catch (error) {
            console.error('Error loading inventory:', error)
            toast.error('Error al cargar inventario')
        }
    }

    // Load supply status for a booking
    const loadSupplyStatus = async (bookingId) => {
        try {
            setLoadingSupplies(true)
            const response = await eventSuppliesAPI.getStatus(bookingId)
            setSupplyStatus(response.data)

            // Merge supplies and consumption data into integrated structure
            let integratedItems = []

            if (response.data.has_supplies && response.data.supplies) {
                // Start with supplies data (estimated quantities)
                integratedItems = response.data.supplies.items.map(supplyItem => ({
                    item_id: supplyItem.item_id,
                    item_name: supplyItem.item_name,
                    estimated_quantity: supplyItem.estimated_quantity,
                    actual_quantity_consumed: 0, // Will be filled from consumption if exists
                    unit: supplyItem.unit,
                    cost_per_unit: supplyItem.cost_per_unit,
                    estimated_total_cost: supplyItem.estimated_total_cost,
                    actual_total_cost: 0,
                    variance: 0,
                    batch_id: supplyItem.batch_id
                }))
            }

            if (response.data.has_consumption && response.data.consumption) {
                // Merge consumption data with supplies
                const consumptionItems = response.data.consumption.items_consumed

                consumptionItems.forEach(consItem => {
                    const existingItemIndex = integratedItems.findIndex(item => item.item_id === consItem.item_id)

                    if (existingItemIndex >= 0) {
                        // Update existing item with consumption data
                        integratedItems[existingItemIndex].actual_quantity_consumed = consItem.actual_quantity_consumed
                        integratedItems[existingItemIndex].actual_total_cost = consItem.total_cost
                        integratedItems[existingItemIndex].variance = consItem.variance || 0
                    } else {
                        // Add consumption-only item (if somehow not in supplies)
                        integratedItems.push({
                            item_id: consItem.item_id,
                            item_name: consItem.item_name,
                            estimated_quantity: consItem.estimated_quantity || 0,
                            actual_quantity_consumed: consItem.actual_quantity_consumed,
                            unit: consItem.unit,
                            cost_per_unit: consItem.cost_per_unit,
                            estimated_total_cost: 0,
                            actual_total_cost: consItem.total_cost,
                            variance: consItem.variance || 0,
                            batch_id: consItem.batch_id
                        })
                    }
                })
            }

            setIntegratedSupplies({
                items: integratedItems,
                notes: response.data.supplies?.notes || '',
                consumption_notes: response.data.consumption?.notes || ''
            })
        } catch (error) {
            console.error('Error loading supply status:', error)
            setSupplyStatus({
                has_supplies: false,
                has_consumption: false,
                can_complete_event: false
            })
        } finally {
            setLoadingSupplies(false)
        }
    }

    // Add item to integrated supplies
    const handleAddSupplyItem = () => {
        setIntegratedSupplies(prev => ({
            ...prev,
            items: [...prev.items, {
                item_id: '',
                item_name: '',
                estimated_quantity: 0,
                actual_quantity_consumed: 0,
                unit: '',
                cost_per_unit: 0,
                estimated_total_cost: 0,
                actual_total_cost: 0,
                variance: 0,
                batch_id: null
            }]
        }))
    }

    // Remove item from supplies
    const handleRemoveSupplyItem = (index) => {
        setIntegratedSupplies(prev => ({
            ...prev,
            items: prev.items.filter((_, i) => i !== index)
        }))
    }

    // Update integrated supply item
    const handleSupplyItemChange = (index, field, value) => {
        setIntegratedSupplies(prev => {
            const newItems = [...prev.items]
            const item = { ...newItems[index] }

            if (field === 'item_id') {
                const inventoryItem = inventoryItems.find(inv => inv.id === value)
                if (inventoryItem) {
                    item.item_id = value
                    item.item_name = inventoryItem.name
                    item.unit = inventoryItem.unit
                    item.cost_per_unit = inventoryItem.weighted_avg_cost || inventoryItem.cost_per_unit || 0
                    // Recalculate costs
                    item.estimated_total_cost = item.estimated_quantity * item.cost_per_unit
                    item.actual_total_cost = item.actual_quantity_consumed * item.cost_per_unit
                }
            } else if (field === 'estimated_quantity') {
                item[field] = parseFloat(value) || 0
                item.estimated_total_cost = item.estimated_quantity * item.cost_per_unit
                // Update variance
                item.variance = item.actual_quantity_consumed - item.estimated_quantity
            } else if (field === 'actual_quantity_consumed') {
                item[field] = parseFloat(value) || 0
                item.actual_total_cost = item.actual_quantity_consumed * item.cost_per_unit
                // Update variance
                item.variance = item.actual_quantity_consumed - item.estimated_quantity
            } else {
                item[field] = value
            }

            newItems[index] = item
            return { ...prev, items: newItems }
        })
    }

    // Save supplies estimation
    const handleSaveSupplies = async () => {
        try {
            if (!selectedBooking) return

            // Validate items
            const validItems = integratedSupplies.items.filter(item =>
                item.item_id && item.estimated_quantity > 0
            )

            if (validItems.length === 0) {
                toast.error('Agrega al menos un insumo válido')
                return
            }

            const suppliesPayload = {
                booking_id: selectedBooking.id,
                items: validItems.map(item => ({
                    item_id: item.item_id,
                    estimated_quantity: item.estimated_quantity,
                    batch_id: item.batch_id || null,
                    notes: item.notes || ''
                })),
                notes: integratedSupplies.notes
            }

            if (supplyStatus.has_supplies) {
                // Update existing supplies
                await eventSuppliesAPI.update(supplyStatus.supplies.id, suppliesPayload)
                toast.success('Insumos estimados actualizados exitosamente')
            } else {
                // Create new supplies
                await eventSuppliesAPI.create(suppliesPayload)
                toast.success('Insumos estimados guardados exitosamente')
            }

            // Reload supply status
            await loadSupplyStatus(selectedBooking.id)
        } catch (error) {
            console.error('Error saving supplies:', error)
            toast.error('Error al guardar insumos: ' + (error.response?.data?.error || error.message))
        }
    }

    // Save consumption (confirmed quantities)
    const handleSaveConsumption = async () => {
        try {
            if (!selectedBooking) return

            // Validate that we have consumption data
            const itemsWithConsumption = integratedSupplies.items.filter(item =>
                item.item_id && item.actual_quantity_consumed > 0
            )

            if (itemsWithConsumption.length === 0) {
                toast.error('Agrega las cantidades consumidas')
                return
            }

            const consumptionPayload = {
                booking_id: selectedBooking.id,
                items_consumed: itemsWithConsumption.map(item => ({
                    item_id: item.item_id,
                    actual_quantity_consumed: item.actual_quantity_consumed,
                    batch_id: item.batch_id || null
                })),
                total_other_expenses: parseFloat(costData.event_cost) || 0,
                notes: integratedSupplies.consumption_notes
            }

            await eventConsumptionAPI.create(consumptionPayload)
            toast.success('Consumo registrado exitosamente')

            // Reload supply status and bookings to get updated financials
            await loadSupplyStatus(selectedBooking.id)
            await loadBookings()
        } catch (error) {
            console.error('Error saving consumption:', error)
            toast.error('Error al registrar consumo: ' + (error.response?.data?.error || error.message))
        }
    }

    // Calculate total costs
    const getTotalEstimatedCost = () => {
        return integratedSupplies.items.reduce((total, item) => {
            return total + (item.estimated_total_cost || 0)
        }, 0)
    }

    const getTotalActualCost = () => {
        return integratedSupplies.items.reduce((total, item) => {
            return total + (item.actual_total_cost || 0)
        }, 0)
    }

    const handleEditClick = (booking) => {
        if (booking.status === 'completed') {
            toast.error('No se puede editar un evento completado')
            return
        }
        setSelectedBooking(booking)


        // Safe date processing
        let formattedDate = ''
        if (booking.event_date) {
            try {
                // Handle different date formats that might come from backend
                let dateToProcess = booking.event_date

                // If it's already in YYYY-MM-DD format, use it directly
                if (typeof dateToProcess === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(dateToProcess)) {
                    formattedDate = dateToProcess
                } else {
                    // Try to create a proper date object
                    const dateObj = new Date(dateToProcess)
                    if (!isNaN(dateObj.getTime())) {
                        formattedDate = dateObj.toISOString().split('T')[0]
                    }
                }
            } catch (error) {
                console.error('Error processing event_date:', error, booking.event_date)
                formattedDate = ''
            }
        }

        setFormData({
            status: booking.status,
            notes: booking.notes || '',
            event_date: formattedDate,
            event_time: booking.event_time || '',
            service_type: booking.service_type || '',
            participants: booking.participants || booking.party_participants || booking.pizzeros_participants || 0,
            estimated_price: booking.estimated_price || '',
            event_cost: booking.event_cost || '',
            event_profit: booking.event_profit || '',
            client_name: booking.client_name || '',
            client_email: booking.client_email || '',
            client_phone: booking.client_phone || '',
            location: booking.location || '',
            pizzeros_participants: booking.pizzeros_participants || 0,
            party_participants: booking.party_participants || 0,
            party_guests: booking.party_guests || booking.party_participants || 0,
            pizza_quantity: booking.pizza_quantity || booking.party_participants || 10
        })
        setEditDialog(true)
    }

    const handleUpdateBooking = async () => {
        try {
            setUpdating(true)

            const oldStatus = selectedBooking.status
            const updatePayload = {}

            if (formData.status) updatePayload.status = formData.status
            if (formData.notes) updatePayload.special_requests = formData.notes
            if (formData.event_date) {
                // Ensure the date is sent in the correct format to avoid timezone issues
                const localDate = new Date(formData.event_date + 'T12:00:00')
                updatePayload.event_date = localDate.toISOString().split('T')[0]
            }
            if (formData.event_time) updatePayload.event_time = formData.event_time
            if (formData.service_type) updatePayload.service_type = formData.service_type
            if (formData.participants) updatePayload.participants = parseInt(formData.participants)

            // Fixed estimated_price handling with better validation
            const priceValue = formData.estimated_price
            if (priceValue !== '' && priceValue !== null && priceValue !== undefined) {
                const parsedPrice = parseFloat(priceValue)
                if (!isNaN(parsedPrice)) {
                    updatePayload.estimated_price = parsedPrice
                }
            }

            if (formData.client_name) updatePayload.client_name = formData.client_name
            if (formData.client_email) updatePayload.client_email = formData.client_email
            if (formData.client_phone) updatePayload.client_phone = formData.client_phone
            if (formData.location) updatePayload.location = formData.location
            if (formData.pizzeros_participants !== undefined) updatePayload.pizzeros_participants = parseInt(formData.pizzeros_participants) || 0
            if (formData.party_participants !== undefined) updatePayload.party_participants = parseInt(formData.party_participants) || 0
            if (formData.party_guests !== undefined) updatePayload.party_guests = parseInt(formData.party_guests) || 0
            if (formData.pizza_quantity !== undefined) updatePayload.pizza_quantity = parseInt(formData.pizza_quantity) || 10

            // Add cost and profit fields when completing
            if (formData.status === 'completed') {
                if (formData.event_cost !== undefined) updatePayload.event_cost = parseFloat(formData.event_cost) || 0
                if (formData.event_profit !== undefined) updatePayload.event_profit = parseFloat(formData.event_profit) || 0
            }

            const response = await bookingsAPI.update(selectedBooking.id, updatePayload)

            if (oldStatus !== 'confirmed' && formData.status === 'confirmed') {
                toast.success('Agendamiento confirmado - Notificaciones enviadas por email y WhatsApp', {
                    duration: 4000,
                    icon: '🎉'
                })
            } else {
                toast.success('Agendamiento actualizado')
            }

            setEditDialog(false)
            loadBookings()
        } catch (error) {
            console.error('Error updating booking:', error)
            console.error('Error details:', {
                message: error.message,
                response: error.response,
                status: error.response?.status,
                data: error.response?.data
            })
            toast.error('Error al actualizar agendamiento: ' + (error.response?.data?.detail || error.message))
        } finally {
            setUpdating(false)
        }
    }

    const handleOpenCostDialog = async (booking) => {
        setSelectedBooking(booking)

        // Calculate total cost using helper function
        const totalCostWithSupplies = calculateTotalCost(booking)

        setCostData({
            event_cost: totalCostWithSupplies,
            event_revenue: (booking.estimated_price || 0),
            notes: ''
        })

        // Load inventory and supply status
        await loadInventoryItems()
        await loadSupplyStatus(booking.id)

        // Reset tab to gastos (expenses) by default
        setCostTabValue(0)
        setCostDialog(true)
    }

    const handleCompleteWithCost = async () => {
        try {
            const revenue = parseFloat(costData.event_revenue) || 0
            const cost = parseFloat(costData.event_cost) || 0
            const updateData = {
                status: 'completed',
                event_cost: cost,
                event_profit: revenue - cost,
                estimated_price: revenue,
                notes: costData.notes || selectedBooking.notes
            }

            await bookingsAPI.update(selectedBooking.id, updateData)

            toast.success('¡Evento completado con costos registrados!')
            setCostDialog(false)
            setCostData({ event_cost: '', event_revenue: '', notes: '' })
            loadBookings()
        } catch (error) {
            console.error('Error completing booking:', error)
            toast.error('Error al completar evento')
        }
    }

    const handleAddExpense = async () => {
        try {
            if (!expenseData.description || !expenseData.amount) {
                toast.error('Por favor completa todos los campos del gasto')
                return
            }

            const currentExpenses = selectedBooking.expenses || []
            const newExpense = {
                id: Date.now().toString(),
                description: expenseData.description,
                amount: parseFloat(expenseData.amount),
                category: expenseData.category,
                date: new Date().toISOString()
            }

            const updatedExpenses = [...currentExpenses, newExpense]
            const totalExpenses = updatedExpenses.reduce((sum, expense) => sum + expense.amount, 0)

            const updateData = {
                expenses: updatedExpenses,
                event_cost: totalExpenses,
                event_profit: (selectedBooking.estimated_price || 0) - totalExpenses
            }

            await bookingsAPI.update(selectedBooking.id, updateData)

            // Update selectedBooking with new data to reflect changes immediately
            const updatedBooking = { ...selectedBooking, ...updateData }
            setSelectedBooking(updatedBooking)

            toast.success('Gasto agregado correctamente')
            // Don't close dialog - setExpenseDialog(false) removed for better UX
            setExpenseData({ description: '', amount: '', category: 'ingredientes' })
            loadBookings()
        } catch (error) {
            console.error('Error adding expense:', error)
            toast.error('Error al agregar gasto')
        }
    }

    const handleEditExpense = (expenseIndex) => {
        const expense = selectedBooking.expenses[expenseIndex]
        setSelectedExpenseIndex(expenseIndex)
        setExpenseData({
            description: expense.description,
            amount: expense.amount.toString(),
            category: expense.category
        })
        setEditExpenseDialog(true)
    }

    const handleUpdateExpense = async () => {
        try {
            if (!expenseData.description || !expenseData.amount) {
                toast.error('Por favor completa todos los campos del gasto')
                return
            }

            const currentExpenses = [...selectedBooking.expenses]
            currentExpenses[selectedExpenseIndex] = {
                ...currentExpenses[selectedExpenseIndex],
                description: expenseData.description,
                amount: parseFloat(expenseData.amount),
                category: expenseData.category,
                date: currentExpenses[selectedExpenseIndex].date
            }

            const totalExpenses = currentExpenses.reduce((sum, expense) => sum + expense.amount, 0)

            const updateData = {
                expenses: currentExpenses,
                event_cost: totalExpenses,
                event_profit: (selectedBooking.estimated_price || 0) - totalExpenses
            }

            await bookingsAPI.update(selectedBooking.id, updateData)

            // Update selectedBooking with new data to reflect changes immediately
            const updatedBooking = { ...selectedBooking, ...updateData }
            setSelectedBooking(updatedBooking)

            toast.success('Gasto actualizado correctamente')
            setEditExpenseDialog(false)
            setExpenseData({ description: '', amount: '', category: 'ingredientes' })
            setSelectedExpenseIndex(null)
            loadBookings()
        } catch (error) {
            console.error('Error updating expense:', error)
            toast.error('Error al actualizar gasto')
        }
    }

    const handleDeleteExpense = async (expenseIndex) => {
        if (!window.confirm('¿Estás seguro de que quieres eliminar este gasto?')) {
            return
        }

        try {
            const currentExpenses = selectedBooking.expenses.filter((_, index) => index !== expenseIndex)
            const totalExpenses = currentExpenses.reduce((sum, expense) => sum + expense.amount, 0)

            const updateData = {
                expenses: currentExpenses,
                event_cost: totalExpenses,
                event_profit: (selectedBooking.estimated_price || 0) - totalExpenses
            }

            await bookingsAPI.update(selectedBooking.id, updateData)

            // Update selectedBooking with new data to reflect changes immediately
            const updatedBooking = { ...selectedBooking, ...updateData }
            setSelectedBooking(updatedBooking)

            toast.success('Gasto eliminado correctamente')
            loadBookings()
        } catch (error) {
            console.error('Error deleting expense:', error)
            toast.error('Error al eliminar gasto')
        }
    }

    const handleOpenExpenseDialog = async (booking) => {
        setSelectedBooking(booking)

        // Load inventory and supply status for the enhanced expense dialog
        await loadInventoryItems()
        await loadSupplyStatus(booking.id)

        // Reset to expenses tab by default
        setCostTabValue(0)
        setExpenseDialog(true)
    }

    const handleNewBookingClick = () => {
        setNewBookingData({
            client_name: '',
            client_email: '',
            client_phone: '',
            service_type: '',
            event_type: '',
            event_date: '',
            event_time: '',
            duration_hours: 4,
            participants: '',
            pizzeros_participants: 0,
            party_participants: 0,
            party_guests: 0,
            pizza_quantity: 10,
            location: '',
            special_requests: ''
        })
        setCreateDialog(true)
    }

    const handleNewBookingChange = (event) => {
        const { name, value } = event.target
        setNewBookingData(prev => ({
            ...prev,
            [name]: value
        }))
    }

    // Precio estimado dinámico para el modal de creación
    const newEstimatedPrice = useMemo(() => {
        return calculateEstimatedPrice(
            newBookingData.service_type,
            parseInt(newBookingData.pizzeros_participants || 0, 10),
            parseInt(newBookingData.pizza_quantity || 0, 10),
            parseInt(newBookingData.participants || 0, 10)
        )
    }, [newBookingData.service_type, newBookingData.pizzeros_participants, newBookingData.pizza_quantity, newBookingData.participants])

    const handleCreateBooking = async () => {
        try {
            const bookingData = {
                client_name: newBookingData.client_name,
                client_email: newBookingData.client_email,
                client_phone: newBookingData.client_phone,
                service_type: newBookingData.service_type || 'workshop',
                event_type: newBookingData.event_type || 'private',
                event_date: newBookingData.event_date,
                event_time: newBookingData.event_time,
                duration_hours: parseInt(newBookingData.duration_hours || 4),
                participants: parseInt(newBookingData.participants || 0),
                pizzeros_participants: parseInt(newBookingData.pizzeros_participants || 0, 10),
                party_guests: parseInt(newBookingData.party_guests || 0, 10),
                pizza_quantity: parseInt(newBookingData.pizza_quantity || 10, 10),
                estimated_price: newEstimatedPrice,
                location: newBookingData.location,
                special_requests: newBookingData.special_requests || ''
            }

            await bookingsAPI.create(bookingData)
            toast.success('Agendamiento creado exitosamente')
            setCreateDialog(false)
            loadBookings()
        } catch (error) {
            console.error('Error creating booking:', error)
            toast.error('Error al crear agendamiento')
        }
    }

    const handleDeleteBooking = async () => {
        try {
            await bookingsAPI.delete(selectedBooking.id)
            toast.success('Agendamiento eliminado')
            setDeleteDialog(false)
            loadBookings()
        } catch (error) {
            console.error('Error deleting booking:', error)
            toast.error('Error al eliminar agendamiento')
        }
    }

    const calendarEvents = useMemo(() => {
        return bookings
            .filter(booking => booking.event_date && booking.status !== 'cancelled')
            .map(booking => {
                // Parse the event date - avoid timezone conversion issues
                let eventDate
                if (booking.event_date.includes('T')) {
                    // Already has time in ISO format - parse carefully to avoid timezone issues
                    const dateOnly = booking.event_date.split('T')[0]
                    const timeOnly = booking.event_time || '10:00'
                    eventDate = new Date(dateOnly + 'T' + timeOnly + ':00')
                } else {
                    // Just a date string - create date in local timezone to avoid shifting
                    const [year, month, day] = booking.event_date.split('-').map(Number)
                    const [hour, minute] = (booking.event_time || '10:00').split(':').map(Number)
                    eventDate = new Date(year, month - 1, day, hour, minute)
                }

                return {
                    id: booking.id,
                    title: `${getServiceLabel(booking.service_type)} - ${booking.client_name}`,
                    start: eventDate,
                    end: new Date(eventDate.getTime() + (2 * 60 * 60 * 1000)), // Add 2 hours for end time
                    resource: booking
                }
            })
    }, [bookings])

    const getMonthOptions = () => {
        const months = []
        const today = new Date()
        const startDate = new Date(2025, 8) // September 2025 (0-indexed months)

        // Generate months from current month backward 1 month and forward 2 months
        for (let i = -1; i <= 2; i++) {
            const date = new Date(today.getFullYear(), today.getMonth() + i)

            // Only include months from September 2025 onwards
            if (date >= startDate) {
                const monthKey = `${String(date.getMonth() + 1).padStart(2, '0')}-${date.getFullYear()}`
                const monthLabel = format(date, 'MMMM yyyy', { locale: es })
                months.push({ key: monthKey, label: monthLabel })
            }
        }

        // Sort in descending order (newest first)
        months.sort((a, b) => {
            const [monthA, yearA] = a.key.split('-').map(Number)
            const [monthB, yearB] = b.key.split('-').map(Number)

            if (yearA !== yearB) return yearB - yearA
            return monthB - monthA
        })

        return months
    }

    const pendingBookings = bookings.filter(b => b.status === 'pending')
    const confirmedBookings = bookings.filter(b => b.status === 'confirmed')
    const completedBookings = bookings.filter(b => b.status === 'completed')
    const cancelledBookings = bookings.filter(b => b.status === 'cancelled')

    const getBookingsByStatus = (status) => {
        return bookings.filter(booking => booking.status === status)
    }

    const BookingCard = ({ booking }) => (
        <Card sx={{ mb: 2, borderLeft: `4px solid ${getStatusColor(booking.status) === 'warning' ? '#ff9800' : getStatusColor(booking.status) === 'success' ? '#4caf50' : getStatusColor(booking.status) === 'info' ? '#2196f3' : '#f44336'}` }}>
            <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                            {booking.client_name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            📧 {booking.client_email}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            📞 {booking.client_phone}
                        </Typography>
                        {booking.location && (
                            <Typography variant="body2" color="text.secondary">
                                📍 {booking.location}
                            </Typography>
                        )}
                    </Box>
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
                        <Chip
                            label={getServiceLabel(booking.service_type)}
                            sx={{ backgroundColor: booking.service_type === 'workshop' ? '#e3f2fd' : '#fff3e0', color: booking.service_type === 'workshop' ? '#1976d2' : '#ed6c02' }}
                            size="small"
                        />
                        <Chip
                            label={getStatusLabel(booking.status)}
                            color={getStatusColor(booking.status)}
                            size="small"
                        />
                    </Box>
                </Box>

                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                    {booking.event_date ? (
                        parseEventDate(booking.event_date) ?
                        format(parseEventDate(booking.event_date), 'dd/MM/yyyy', { locale: es }) :
                        'Fecha inválida'
                    ) : 'Fecha por definir'}
                    {booking.event_time && ` a las ${booking.event_time}`}
                </Typography>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 2 }}>
                    {/* Mostrar participantes por servicio */}
                    {booking.pizzeros_participants > 0 && (
                        <Typography variant="body2">
                            <strong>Pizzeros en Acción:</strong> {booking.pizzeros_participants} niños
                        </Typography>
                    )}
                    {(booking.party_guests > 0 || booking.pizza_quantity > 0) && (
                        <Typography variant="body2">
                            <strong>Pizza Party:</strong> {booking.party_guests || '-'} personas, {booking.pizza_quantity || 10} pizzas
                        </Typography>
                    )}
                    {(!booking.pizzeros_participants && !(booking.party_guests > 0 || booking.pizza_quantity > 0)) && (
                        <Typography variant="body2">
                            <strong>Participantes:</strong> {booking.participants}
                        </Typography>
                    )}
                    <Typography variant="body2">
                        <strong>Precio:</strong> ${booking.estimated_price ? booking.estimated_price.toLocaleString() : 'Por definir'}
                    </Typography>
                </Box>

                {booking.special_requests && (
                    <Typography variant="body2" sx={{ mb: 2, fontStyle: 'italic', color: 'text.secondary' }}>
                        "{booking.special_requests}"
                    </Typography>
                )}

                <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
                    Creado: {format(new Date(booking.created_at), 'dd/MM/yyyy HH:mm', { locale: es })}
                </Typography>

                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {booking.status !== 'completed' && (
                        <Button size="small" variant="outlined" startIcon={<Edit />} onClick={() => handleEditClick(booking)}>
                            Editar
                        </Button>
                    )}
                    {booking.status === 'confirmed' && (
                        <>
                            <Button
                                size="small"
                                variant="outlined"
                                color="primary"
                                startIcon={<AddBox />}
                                onClick={() => handleOpenExpenseDialog(booking)}
                            >
                                +Agregar Gasto
                            </Button>
                            <Button
                                size="small"
                                variant="contained"
                                color="info"
                                startIcon={<CheckCircle />}
                                onClick={() => handleOpenCostDialog(booking)}
                            >
                                Completar
                            </Button>
                        </>
                    )}
                    {booking.status === 'completed' ? (
                        <Button
                            size="small"
                            variant="outlined"
                            startIcon={<ViewList />}
                            onClick={async () => { setSelectedBooking(booking); await loadSupplyStatus(booking.id); setViewDialog(true) }}
                        >
                            Ver detalle
                        </Button>
                    ) : (
                        <Button
                            size="small"
                            variant="outlined"
                            color="error"
                            startIcon={<Delete />}
                            onClick={() => {
                                setSelectedBooking(booking)
                                setDeleteDialog(true)
                            }}
                        >
                            Eliminar
                        </Button>
                    )}
                </Box>
            </CardContent>
        </Card>
    )

    return (
        <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h4" sx={{ fontWeight: 700 }}>
                    Gestión de Agendamientos
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    <Button
                        variant="outlined"
                        startIcon={<Refresh />}
                        onClick={loadBookings}
                        disabled={loading}
                    >
                        Actualizar
                    </Button>
                    <Button
                        variant="contained"
                        startIcon={<Add />}
                        onClick={handleNewBookingClick}
                    >
                        Nuevo Agendamiento
                    </Button>
                    <ToggleButtonGroup
                        value={view}
                        exclusive
                        onChange={(e, newView) => newView && setView(newView)}
                        size="small"
                    >
                        <ToggleButton value="table">
                            <Assignment />
                        </ToggleButton>
                        <ToggleButton value="calendar">
                            <CalendarMonth />
                        </ToggleButton>
                    </ToggleButtonGroup>
                </Box>
            </Box>

            {/* Statistics Cards */}
            <Grid container spacing={3} sx={{ mb: 4 }}>
                <Grid item xs={12} md={3}>
                    <Card sx={{ bgcolor: '#fff3e0' }}>
                        <CardContent sx={{ textAlign: 'center' }}>
                            <PendingActions sx={{ fontSize: 40, color: '#ff9800', mb: 1 }} />
                            <Typography variant="h4" sx={{ fontWeight: 700, color: '#ff9800' }}>
                                {pendingBookings.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Pendientes
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} md={3}>
                    <Card sx={{ bgcolor: '#e8f5e8' }}>
                        <CardContent sx={{ textAlign: 'center' }}>
                            <CheckCircle sx={{ fontSize: 40, color: '#4caf50', mb: 1 }} />
                            <Typography variant="h4" sx={{ fontWeight: 700, color: '#4caf50' }}>
                                {confirmedBookings.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Confirmados
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} md={3}>
                    <Card sx={{ bgcolor: '#e3f2fd' }}>
                        <CardContent sx={{ textAlign: 'center' }}>
                            <EventAvailable sx={{ fontSize: 40, color: '#2196f3', mb: 1 }} />
                            <Typography variant="h4" sx={{ fontWeight: 700, color: '#2196f3' }}>
                                {completedBookings.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Completados
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} md={3}>
                    <Card sx={{ bgcolor: '#fce4ec' }}>
                        <CardContent sx={{ textAlign: 'center' }}>
                            <TrendingUp sx={{ fontSize: 40, color: '#e91e63', mb: 1 }} />
                            <Typography variant="h4" sx={{ fontWeight: 700, color: '#e91e63' }}>
                                {bookings.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Total
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {pendingBookings.length > 0 && (
                <Alert severity="warning" sx={{ mb: 3 }}>
                    Tienes {pendingBookings.length} agendamiento(s) pendiente(s) de confirmación.
                </Alert>
            )}

            {/* Filters and Search - only show for table view */}
            {view === 'table' && (
                <Card sx={{ mb: 3, p: 2 }}>
                    <Grid container spacing={2} alignItems="center">
                        <Grid item xs={12} sm={6} md={4}>
                            <TextField
                                fullWidth
                                placeholder="Buscar por cliente, teléfono, email, ubicación..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                InputProps={{
                                    startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
                                }}
                                size="small"
                            />
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                            <FormControl fullWidth size="small">
                                <Select
                                    value={selectedMonth}
                                    label="Filtrar por mes"
                                    displayEmpty
                                    renderValue={(value) => value || 'Filtrar por mes'}
                                    onChange={(e) => setSelectedMonth(e.target.value)}
                                >
                                    <MenuItem value="">Todos los meses</MenuItem>
                                    {getMonthOptions().map(month => (
                                        <MenuItem key={month.key} value={month.key}>
                                            {month.label}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                            <FormControl fullWidth size="small">
                                <Select
                                    value={statusFilter}
                                    onChange={(e) => setStatusFilter(e.target.value)}
                                    displayEmpty
                                    renderValue={(value) => (
                                        value === ''
                                            ? <Chip size="small" label="Pendientes y Confirmados" color="warning" />
                                            : value === 'pending'
                                                ? <Chip size="small" label="Pendientes" color="warning" />
                                                : value === 'confirmed'
                                                    ? <Chip size="small" label="Confirmados" color="success" />
                                                    : value === 'completed'
                                                        ? <Chip size="small" label="Completados" color="info" />
                                                        : <Chip size="small" label="Cancelados" color="error" />
                                    )}
                                    sx={{ '& .MuiSelect-select': { py: 0.5 } }}
                                >
                                    <MenuItem value=""><Chip size="small" label="Pendientes y Confirmados" color="warning" /></MenuItem>
                                    <MenuItem value={'pending'}><Chip size="small" label="Pendientes" color="warning" /></MenuItem>
                                    <MenuItem value={'confirmed'}><Chip size="small" label="Confirmados" color="success" /></MenuItem>
                                    <MenuItem value={'completed'}><Chip size="small" label="Completados" color="info" /></MenuItem>
                                    <MenuItem value={'cancelled'}><Chip size="small" label="Cancelados" color="error" /></MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item xs={12} sm={12} md={5}>
                            <Typography variant="body2" color="text.secondary">
                                Mostrando {filteredBookings.length} de {bookings.length} agendamientos
                            </Typography>
                        </Grid>
                    </Grid>
                </Card>
            )}

            {/* Tabs for different statuses - only show in cards view */}
            {view === 'cards' && (
                <Paper sx={{ mb: 3 }}>
                    <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
                        <Tab label={`Pendientes (${pendingBookings.length})`} />
                        <Tab label={`Confirmados (${confirmedBookings.length})`} />
                        <Tab label={`Completados (${completedBookings.length})`} />
                    </Tabs>
                </Paper>
            )}

            {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress />
                </Box>
            ) : view === 'cards' ? (
                <Box>
                    {tabValue === 0 && (
                        <Box>
                            {pendingBookings.length === 0 ? (
                                <Alert severity="info">No hay agendamientos pendientes</Alert>
                            ) : (
                                pendingBookings.map(booking => (
                                    <BookingCard key={booking.id} booking={booking} />
                                ))
                            )}
                        </Box>
                    )}

                    {tabValue === 1 && (
                        <Box>
                            {confirmedBookings.length === 0 ? (
                                <Alert severity="info">No hay agendamientos confirmados</Alert>
                            ) : (
                                confirmedBookings.map(booking => (
                                    <BookingCard key={booking.id} booking={booking} />
                                ))
                            )}
                        </Box>
                    )}

                    {tabValue === 2 && (
                        <Box>
                            {completedBookings.length === 0 ? (
                                <Alert severity="info">No hay agendamientos completados</Alert>
                            ) : (
                                completedBookings.map(booking => (
                                    <BookingCard key={booking.id} booking={booking} />
                                ))
                            )}
                        </Box>
                    )}
                </Box>
            ) : view === 'table' ? (
                <Card>
                    <CardContent>
                        <TableContainer component={Paper}>
                            <Table>
                                <TableHead>
                                    <TableRow>
                                        <TableCell
                                            sx={{ cursor: 'pointer', userSelect: 'none' }}
                                            onClick={() => handleSort('client_name')}
                                        >
                                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                                Cliente
                                                {getSortIcon('client_name')}
                                            </Box>
                                        </TableCell>
                                        <TableCell
                                            sx={{ cursor: 'pointer', userSelect: 'none' }}
                                            onClick={() => handleSort('service_type')}
                                        >
                                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                                Servicio
                                                {getSortIcon('service_type')}
                                            </Box>
                                        </TableCell>
                                        <TableCell
                                            sx={{ cursor: 'pointer', userSelect: 'none' }}
                                            onClick={() => handleSort('event_date')}
                                        >
                                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                                Fecha
                                                {getSortIcon('event_date')}
                                            </Box>
                                        </TableCell>
                                        <TableCell
                                            sx={{ cursor: 'pointer', userSelect: 'none' }}
                                            onClick={() => handleSort('status')}
                                        >
                                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                                Estado
                                                {getSortIcon('status')}
                                            </Box>
                                        </TableCell>
                                        <TableCell
                                            sx={{ cursor: 'pointer', userSelect: 'none' }}
                                            onClick={() => handleSort('participants')}
                                        >
                                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                                Participantes
                                                {getSortIcon('participants')}
                                            </Box>
                                        </TableCell>
                                        <TableCell>Total</TableCell>
                                        <TableCell>Costo</TableCell>
                                        <TableCell>Utilidad</TableCell>
                                        <TableCell>Acciones</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {filteredBookings.map((booking) => (
                                        <TableRow key={booking.id}>
                                            <TableCell>
                                                <Box>
                                                    <Typography variant="body2" fontWeight="bold">
                                                        {booking.client_name}
                                                    </Typography>
                                                    <Typography variant="caption" color="text.secondary">
                                                        {booking.client_phone}
                                                    </Typography>
                                                </Box>
                                            </TableCell>
                                            <TableCell>
                                                {getServiceLabel(booking.service_type)}
                                            </TableCell>
                                            <TableCell>
                                                {booking.event_date ? (
                                                    parseEventDate(booking.event_date) ?
                                                    format(parseEventDate(booking.event_date), 'dd/MM/yyyy') :
                                                    'Fecha inválida'
                                                ) : '-'}
                                                {booking.event_time && (
                                                    <Typography variant="caption" display="block">
                                                        {booking.event_time}
                                                    </Typography>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                <Chip
                                                    label={getStatusLabel(booking.status)}
                                                    color={getStatusColor(booking.status)}
                                                    size="small"
                                                />
                                            </TableCell>
                                            <TableCell>
                                                {booking.pizzeros_participants > 0 && (
                                                    <Typography variant="body2" sx={{ fontSize: '0.75rem' }}>
                                                        Pizzeros: {booking.pizzeros_participants}
                                                    </Typography>
                                                )}
                                                {booking.party_guests > 0 || booking.pizza_quantity > 0 ? (
                                                    <Typography variant="body2" sx={{ fontSize: '0.75rem' }}>
                                                        Party: {booking.party_guests || '-'} personas / {booking.pizza_quantity || 10} pizzas
                                                    </Typography>
                                                ) : null}
                                                {(!booking.pizzeros_participants && !(booking.party_guests > 0 || booking.pizza_quantity > 0)) && (
                                                    <Typography variant="body2">
                                                        {booking.participants}
                                                    </Typography>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                <Typography variant="body2" fontWeight="bold">
                                                    ${booking.estimated_price ? booking.estimated_price.toLocaleString() : '-'}
                                                </Typography>
                                            </TableCell>
                                            <TableCell>
                                                <Typography variant="body2" color={calculateTotalCost(booking) ? 'text.primary' : 'text.secondary'}>
                                                    ${calculateTotalCost(booking) ? calculateTotalCost(booking).toLocaleString() : '-'}
                                                </Typography>
                                            </TableCell>
                                            <TableCell>
                                                {(() => {
                                                    const est = booking.estimated_price || 0
                                                    const cost = calculateTotalCost(booking) || 0
                                                    const profit = est - cost
                                                    return (
                                                        <Typography
                                                            variant="body2"
                                                            fontWeight="bold"
                                                            color={profit > 0 ? 'success.main' : 'text.secondary'}
                                                        >
                                                            ${profit ? profit.toLocaleString() : '-'}
                                                        </Typography>
                                                    )
                                                })()}
                                            </TableCell>
                                            <TableCell>
                                                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                                    {booking.status !== 'completed' && (
                                                        <Button
                                                            size="small"
                                                            startIcon={<Edit />}
                                                            onClick={() => handleEditClick(booking)}
                                                        >
                                                            Editar
                                                        </Button>
                                                    )}
                                                    {booking.status === 'confirmed' && (
                                                        <>
                                                            <Button
                                                                size="small"
                                                                color="primary"
                                                                startIcon={<AddBox />}
                                                                onClick={() => handleOpenExpenseDialog(booking)}
                                                            >
                                                                +Gasto
                                                            </Button>
                                                            <Button
                                                                size="small"
                                                                color="info"
                                                                startIcon={<CheckCircle />}
                                                                onClick={() => handleOpenCostDialog(booking)}
                                                            >
                                                                Completar
                                                            </Button>
                                                        </>
                                                    )}
                                                    {booking.status === 'completed' ? (
                                                        <Button
                                                            size="small"
                                                            startIcon={<ViewList />}
                                                            onClick={() => { setSelectedBooking(booking); setViewDialog(true) }}
                                                        >
                                                            Ver detalle
                                                        </Button>
                                                    ) : (
                                                        <Button
                                                            size="small"
                                                            color="error"
                                                            startIcon={<Delete />}
                                                            onClick={() => {
                                                                setSelectedBooking(booking)
                                                                setDeleteDialog(true)
                                                            }}
                                                        >
                                                            Eliminar
                                                        </Button>
                                                    )}
                                                </Box>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                    {filteredBookings.length === 0 && (
                                        <TableRow>
                                            <TableCell colSpan={6} align="center">
                                                <Typography color="text.secondary">
                                                    No hay agendamientos disponibles
                                                </Typography>
                                            </TableCell>
                                        </TableRow>
                                    )}
                                </TableBody>
                            </Table>
                        </TableContainer>
                    </CardContent>
                </Card>
            ) : (
                <Card>
                    <CardContent>
                        <Box sx={{ height: 600 }}>
                            <Calendar
                                localizer={localizer}
                                events={calendarEvents}
                                startAccessor="start"
                                endAccessor="end"
                                culture="es"
                                formats={{
                                    dayHeaderFormat: (date, culture, localizer) => {
                                        return localizer.format(date, 'eeeeee', culture)
                                    },
                                    dayFormat: 'dd'
                                }}
                                messages={{
                                    next: "Siguiente",
                                    previous: "Anterior",
                                    today: "Hoy",
                                    month: "Mes",
                                    week: "Semana",
                                    day: "Día"
                                }}
                                onSelectEvent={(event) => handleEditClick(event.resource)}
                            />
                        </Box>
                    </CardContent>
                </Card>
            )}

            <Dialog open={editDialog} onClose={() => setEditDialog(false)} maxWidth="md" fullWidth>
                <DialogTitle>
                    Editar Agendamiento
                    <IconButton
                        onClick={() => setEditDialog(false)}
                        sx={{ position: 'absolute', right: 8, top: 8 }}
                    >
                        <Close />
                    </IconButton>
                </DialogTitle>
                <DialogContent>
                    <Grid container spacing={2} sx={{ mt: 1 }}>
                        <Grid item xs={12} sm={6}>
                            <FormControl fullWidth>
                                <Select
                                    value={formData.status}
                                    label="Estado"
                                    displayEmpty
                                    renderValue={(value) => value ? {
                                        'pending': 'Pendiente',
                                        'confirmed': 'Confirmado',
                                        'in_progress': 'En Progreso',
                                        'completed': 'Completado',
                                        'cancelled': 'Cancelado'
                                    }[value] : 'Selecciona Estado'}
                                    onChange={(e) => setFormData(prev => ({ ...prev, status: e.target.value }))}
                                >
                                    <MenuItem value="pending">Pendiente</MenuItem>
                                    <MenuItem value="confirmed">Confirmado</MenuItem>
                                    <MenuItem value="completed">Completado</MenuItem>
                                    <MenuItem value="cancelled">Cancelado</MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <FormControl fullWidth>
                                <Select
                                    value={formData.service_type}
                                    label="Tipo de Servicio"
                                    displayEmpty
                                    renderValue={(value) => value ? {
                                        'workshop': 'Pizzeros en Acción',
                                        'pizza_party': 'Pizza Party',
                                        'workshop,pizza_party': 'Ambos Servicios'
                                    }[value] : 'Selecciona Tipo de Servicio'}
                                    onChange={(e) => setFormData(prev => ({ ...prev, service_type: e.target.value }))}
                                >
                                    <MenuItem value="workshop">Pizzeros en Acción</MenuItem>
                                    <MenuItem value="pizza_party">Pizza Party</MenuItem>
                                    <MenuItem value="workshop,pizza_party">Ambos Servicios</MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Nombre del Cliente"
                                value={formData.client_name}
                                onChange={(e) => setFormData(prev => ({ ...prev, client_name: e.target.value }))}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Email del Cliente"
                                type="email"
                                value={formData.client_email}
                                onChange={(e) => setFormData(prev => ({ ...prev, client_email: e.target.value }))}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Teléfono del Cliente"
                                value={formData.client_phone}
                                onChange={(e) => setFormData(prev => ({ ...prev, client_phone: e.target.value }))}
                            />
                        </Grid>
                        {/* Campos condicionales según tipo de servicio */}
                        {formData.service_type?.includes('workshop') && (
                            <Grid item xs={12} sm={6}>
                                <TextField
                                    fullWidth
                                    label="Pizzeros en Acción - Niños"
                                    value={formData.pizzeros_participants}
                                    onChange={(e) => {
                                        const participants = parseInt(e.target.value || '0', 10)
                                        const newPrice = calculateEstimatedPrice(
                                            formData.service_type,
                                            participants,
                                            formData.pizza_quantity || formData.party_participants,
                                            formData.participants
                                        )
                                        setFormData(prev => ({
                                            ...prev,
                                            pizzeros_participants: participants,
                                            estimated_price: newPrice
                                        }))
                                    }}
                                    type="number"
                                    helperText="Cantidad de niños participantes"
                                />
                            </Grid>
                        )}
                        {formData.service_type?.includes('pizza_party') && (
                            <>
                                <Grid item xs={12} sm={6}>
                                    <TextField
                                        fullWidth
                                        label="Pizza Party - Cantidad de personas"
                                        value={formData.party_guests}
                                        onChange={(e) => {
                                            const guests = parseInt(e.target.value || '0', 10)
                                            setFormData(prev => {
                                                const suggested = guests > 0 ? calculateSuggestedPizzas(guests) : 0
                                                const pizzaQuantity = Math.max(10, suggested)
                                                const newPrice = calculateEstimatedPrice(
                                                    prev.service_type,
                                                    prev.pizzeros_participants,
                                                    pizzaQuantity,
                                                    prev.participants
                                                )
                                                return {
                                                    ...prev,
                                                    party_guests: guests,
                                                    pizza_quantity: pizzaQuantity,
                                                    estimated_price: newPrice
                                                }
                                            })
                                        }}
                                        type="number"
                                        helperText="Número de invitados al evento"
                                    />
                                </Grid>
                                <Grid item xs={12} sm={6}>
                                    <TextField
                                        fullWidth
                                        label="Pizza Party - Pizzas sugeridas"
                                        value={formData.pizza_quantity}
                                        onChange={(e) => {
                                            const quantity = parseInt(e.target.value || '10', 10)
                                            setFormData(prev => {
                                                const finalQuantity = Math.max(10, quantity)
                                                const newPrice = calculateEstimatedPrice(
                                                    prev.service_type,
                                                    prev.pizzeros_participants,
                                                    finalQuantity,
                                                    prev.participants
                                                )
                                                return {
                                                    ...prev,
                                                    pizza_quantity: finalQuantity,
                                                    estimated_price: newPrice
                                                }
                                            })
                                        }}
                                        type="number"
                                        helperText="Mínimo 10 pizzas - Ajustable según necesidades"
                                    />
                                </Grid>
                            </>
                        )}
                        {/* Campo total solo para servicios mixtos */}
                        {(formData.service_type?.includes('workshop') && formData.service_type?.includes('pizza_party')) && (
                            <Grid item xs={12} sm={6}>
                                <TextField
                                    fullWidth
                                    label="Participantes Total (ambos servicios)"
                                    value={(formData.pizzeros_participants || 0) + (formData.party_guests || 0)}
                                    InputProps={{ readOnly: true }}
                                    type="number"
                                    helperText="Calculado automáticamente: Pizzeros + Pizza Party"
                                />
                            </Grid>
                        )}
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Fecha del Evento"
                                type="date"
                                value={formData.event_date}
                                onChange={(e) => setFormData(prev => ({ ...prev, event_date: e.target.value }))}
                                InputLabelProps={{ shrink: true }}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Hora del Evento"
                                select
                                value={formData.event_time}
                                onChange={(e) => setFormData(prev => ({ ...prev, event_time: e.target.value }))}
                                SelectProps={{ native: true }}
                                InputLabelProps={{ shrink: true }}
                                helperText="Solo horarios :00 y :30"
                            >
                                <option value="">Seleccionar hora...</option>
                                <option value="08:00">08:00</option>
                                <option value="08:30">08:30</option>
                                <option value="09:00">09:00</option>
                                <option value="09:30">09:30</option>
                                <option value="10:00">10:00</option>
                                <option value="10:30">10:30</option>
                                <option value="11:00">11:00</option>
                                <option value="11:30">11:30</option>
                                <option value="12:00">12:00</option>
                                <option value="12:30">12:30</option>
                                <option value="13:00">13:00</option>
                                <option value="13:30">13:30</option>
                                <option value="14:00">14:00</option>
                                <option value="14:30">14:30</option>
                                <option value="15:00">15:00</option>
                                <option value="15:30">15:30</option>
                                <option value="16:00">16:00</option>
                                <option value="16:30">16:30</option>
                                <option value="17:00">17:00</option>
                                <option value="17:30">17:30</option>
                                <option value="18:00">18:00</option>
                                <option value="18:30">18:30</option>
                                <option value="19:00">19:00</option>
                                <option value="19:30">19:30</option>
                                <option value="20:00">20:00</option>
                                <option value="20:30">20:30</option>
                            </TextField>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Ubicación"
                                value={formData.location}
                                onChange={(e) => setFormData(prev => ({ ...prev, location: e.target.value }))}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Total a Cobrar"
                                type="number"
                                value={formData.estimated_price}
                                onChange={(e) => {
                                    const newValue = e.target.value
                                    setFormData(prev => ({ ...prev, estimated_price: newValue }))
                                }}
                                InputProps={{
                                    startAdornment: <Typography variant="body2" sx={{ mr: 1 }}>$</Typography>,
                                }}
                            />
                        </Grid>
                        {formData.status === 'completed' && (
                            <>
                                <Grid item xs={12} sm={6}>
                                    <TextField
                                        fullWidth
                                        label="Costo del Evento"
                                        type="number"
                                        value={formData.event_cost || ''}
                                        onChange={(e) => {
                                            const cost = parseFloat(e.target.value) || 0;
                                            const price = parseFloat(formData.estimated_price) || 0;
                                            setFormData(prev => ({
                                                ...prev,
                                                event_cost: cost,
                                                event_profit: price - cost
                                            }));
                                        }}
                                        InputProps={{
                                            startAdornment: <Typography variant="body2" sx={{ mr: 1 }}>$</Typography>,
                                        }}
                                    />
                                </Grid>
                                <Grid item xs={12} sm={6}>
                                    <TextField
                                        fullWidth
                                        label="Utilidad"
                                        type="number"
                                        value={formData.event_profit || ''}
                                        InputProps={{
                                            startAdornment: <Typography variant="body2" sx={{ mr: 1 }}>$</Typography>,
                                            readOnly: true,
                                        }}
                                        sx={{
                                            '& .MuiInputBase-input': {
                                                color: (formData.event_profit || 0) > 0 ? 'success.main' : 'text.secondary',
                                                fontWeight: 'bold'
                                            }
                                        }}
                                    />
                                </Grid>
                            </>
                        )}
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                label="Notas adicionales"
                                multiline
                                rows={3}
                                value={formData.notes}
                                onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                            />
                        </Grid>
                    </Grid>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setEditDialog(false)}>Cancelar</Button>
                    <Button
                        onClick={() => {
                            handleUpdateBooking()
                        }}
                        variant="contained"
                        disabled={updating}
                        startIcon={updating ? <CircularProgress size={20} /> : null}
                    >
                        {updating ? 'Actualizando...' : 'Actualizar'}
                    </Button>
                </DialogActions>
            </Dialog>

            <Dialog open={createDialog} onClose={() => setCreateDialog(false)} maxWidth="md" fullWidth>
                <DialogTitle>Crear Nuevo Agendamiento</DialogTitle>
                <DialogContent>
                    <Grid container spacing={2} sx={{ mt: 1 }}>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Nombre del Cliente"
                                name="client_name"
                                value={newBookingData.client_name}
                                onChange={handleNewBookingChange}
                                required
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Email"
                                name="client_email"
                                type="email"
                                value={newBookingData.client_email}
                                onChange={handleNewBookingChange}
                                required
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Teléfono"
                                name="client_phone"
                                value={newBookingData.client_phone}
                                onChange={handleNewBookingChange}
                                required
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <FormControl fullWidth>
                                <Select
                                    name="service_type"
                                    value={newBookingData.service_type}
                                    displayEmpty
                                    renderValue={(value) => value ? {
                                        'workshop': 'Pizzeros en Acción',
                                        'pizza_party': 'Pizza Party',
                                        'workshop,pizza_party': 'Ambos Servicios'
                                    }[value] : 'Selecciona Tipo de Servicio'}
                                    onChange={handleNewBookingChange}
                                >
                                    <MenuItem value="workshop">Pizzeros en Acción</MenuItem>
                                    <MenuItem value="pizza_party">Pizza Party</MenuItem>
                                    <MenuItem value="workshop,pizza_party">Ambos Servicios</MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <FormControl fullWidth>
                                <Select
                                    name="event_type"
                                    value={newBookingData.event_type}
                                    onChange={handleNewBookingChange}
                                    displayEmpty
                                    renderValue={(value) => value ? {
                                        'birthday': '🎂 Cumpleaños',
                                        'school': '🏫 Escolar',
                                        'corporate': '🏢 Corporativo',
                                        'private': '✨ Otro'
                                    }[value] : 'Selecciona Tipo de Evento'}
                                >
                                    <MenuItem value="birthday">🎂 Cumpleaños</MenuItem>
                                    <MenuItem value="school">🏫 Escolar</MenuItem>
                                    <MenuItem value="corporate">🏢 Corporativo</MenuItem>
                                    <MenuItem value="private">✨ Otro</MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Fecha del Evento"
                                name="event_date"
                                type="date"
                                value={newBookingData.event_date}
                                onChange={handleNewBookingChange}
                                InputLabelProps={{ shrink: true }}
                                required
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Hora del Evento"
                                name="event_time"
                                select
                                value={newBookingData.event_time}
                                onChange={handleNewBookingChange}
                                SelectProps={{ native: true }}
                                InputLabelProps={{ shrink: true }}
                                helperText="Solo horarios :00 y :30"
                            >
                                <option value="">Seleccionar hora...</option>
                                <option value="08:00">08:00</option>
                                <option value="08:30">08:30</option>
                                <option value="09:00">09:00</option>
                                <option value="09:30">09:30</option>
                                <option value="10:00">10:00</option>
                                <option value="10:30">10:30</option>
                                <option value="11:00">11:00</option>
                                <option value="11:30">11:30</option>
                                <option value="12:00">12:00</option>
                                <option value="12:30">12:30</option>
                                <option value="13:00">13:00</option>
                                <option value="13:30">13:30</option>
                                <option value="14:00">14:00</option>
                                <option value="14:30">14:30</option>
                                <option value="15:00">15:00</option>
                                <option value="15:30">15:30</option>
                                <option value="16:00">16:00</option>
                                <option value="16:30">16:30</option>
                                <option value="17:00">17:00</option>
                                <option value="17:30">17:30</option>
                                <option value="18:00">18:00</option>
                                <option value="18:30">18:30</option>
                                <option value="19:00">19:00</option>
                                <option value="19:30">19:30</option>
                                <option value="20:00">20:00</option>
                                <option value="20:30">20:30</option>
                            </TextField>
                        </Grid>
                        {/* Dynamic participant fields based on service type */}
                        {newBookingData.service_type.includes('workshop') && (
                            <Grid item xs={12} sm={6}>
                                <TextField
                                    fullWidth
                                    label="Participantes en Pizzeros en Acción"
                                    name="pizzeros_participants"
                                    type="number"
                                    value={newBookingData.pizzeros_participants}
                                    onChange={handleNewBookingChange}
                                    inputProps={{ min: 10, max: 200 }}
                                    helperText="Mínimo 10 niños"
                                    required
                                />
                            </Grid>
                        )}
                        {newBookingData.service_type.includes('pizza_party') && (
                            <>
                                <Grid item xs={12} sm={6}>
                                    <TextField
                                        fullWidth
                                        label="Pizza Party - Cantidad de personas"
                                        name="party_guests"
                                        type="number"
                                        value={newBookingData.party_guests}
                                        onChange={(e) => {
                                            const guests = parseInt(e.target.value || '0', 10)
                                            const suggested = guests > 0 ? calculateSuggestedPizzas(guests) : 0
                                            setNewBookingData(prev => ({
                                                ...prev,
                                                party_guests: guests,
                                                pizza_quantity: Math.max(10, suggested)
                                            }))
                                        }}
                                        inputProps={{ min: 1, max: 200 }}
                                        helperText="Número de invitados al evento"
                                        required
                                    />
                                </Grid>
                                <Grid item xs={12} sm={6}>
                                    <TextField
                                        fullWidth
                                        label="Pizza Party - Pizzas sugeridas"
                                        name="pizza_quantity"
                                        type="number"
                                        value={newBookingData.pizza_quantity}
                                        onChange={(e) => {
                                            const quantity = Math.max(10, parseInt(e.target.value || '10', 10))
                                            setNewBookingData(prev => ({
                                                ...prev,
                                                pizza_quantity: quantity
                                            }))
                                        }}
                                        inputProps={{ min: 10, max: 200 }}
                                        helperText="Mínimo 10 pizzas - Ajustable según necesidades"
                                        required
                                    />
                                </Grid>
                            </>
                        )}
                        {!newBookingData.service_type && (
                            <Grid item xs={12} sm={6}>
                                <TextField
                                    fullWidth
                                    label="Número de Participantes"
                                    name="participants"
                                    type="number"
                                    value={newBookingData.participants}
                                    onChange={handleNewBookingChange}
                                    helperText="Selecciona un tipo de servicio primero"
                                    disabled
                                />
                            </Grid>
                        )}
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Duración (horas)"
                                name="duration_hours"
                                type="number"
                                value={newBookingData.duration_hours}
                                onChange={handleNewBookingChange}
                                inputProps={{ min: 1, max: 8 }}
                                helperText="Duración del evento en horas"
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Total a Cobrar"
                                value={newEstimatedPrice}
                                InputProps={{ readOnly: true, startAdornment: <Typography variant="body2" sx={{ mr: 1 }}>$</Typography> }}
                                helperText="Calculado automáticamente según reglas de precios"
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Ubicación"
                                name="location"
                                value={newBookingData.location}
                                onChange={handleNewBookingChange}
                            />
                        </Grid>
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                label="Solicitudes Especiales"
                                name="special_requests"
                                multiline
                                rows={3}
                                value={newBookingData.special_requests}
                                onChange={handleNewBookingChange}
                            />
                        </Grid>
                    </Grid>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setCreateDialog(false)}>Cancelar</Button>
                    <Button onClick={handleCreateBooking} variant="contained">
                        Crear Agendamiento
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Enhanced Cost Dialog with Supplies and Consumption */}
            <Dialog open={costDialog} onClose={() => setCostDialog(false)} maxWidth="lg" fullWidth>
                <DialogTitle>
                    Gestión de Evento - {selectedBooking?.client_name}
                </DialogTitle>
                <DialogContent>
                    <Box sx={{ mt: 2 }}>
                        {/* Event Summary */}
                        <Card sx={{ mb: 3, bgcolor: 'grey.50' }}>
                            <CardContent>
                                <Grid container spacing={2}>
                                    <Grid item xs={12} sm={6}>
                                        <Typography variant="body2" color="text.secondary">
                                            <strong>Evento:</strong> {selectedBooking?.event_type} - {selectedBooking?.participants} participantes
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            <strong>Fecha:</strong> {selectedBooking?.event_date} {selectedBooking?.event_time}
                                        </Typography>
                                    </Grid>
                                    <Grid item xs={12} sm={6}>
                                        <Typography variant="body2" color="text.secondary">
                                            <strong>Precio estimado:</strong> ${selectedBooking?.estimated_price?.toLocaleString()}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            <strong>Estado:</strong> {selectedBooking?.status}
                                        </Typography>
                                    </Grid>
                                </Grid>
                            </CardContent>
                        </Card>

                        {/* Tabs for Gastos and Insumos */}
                        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
                            <Tabs
                                value={costTabValue}
                                onChange={(e, newValue) => setCostTabValue(newValue)}
                                aria-label="cost management tabs"
                            >
                                <Tab label="Gastos del Evento" />
                                <Tab label="Insumos Estimados" />
                            </Tabs>
                        </Box>

                        {/* Tab Panel 0: Gastos (Expenses) */}
                        {costTabValue === 0 && (
                            <Box>
                                {/* Existing expenses */}
                                {selectedBooking?.expenses && selectedBooking.expenses.length > 0 && (
                                    <Card sx={{ mb: 3 }}>
                                        <CardContent>
                                            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                                                Gastos Registrados:
                                            </Typography>
                                            {selectedBooking.expenses.map((expense, index) => (
                                                <Box key={index} sx={{
                                                    display: 'flex',
                                                    justifyContent: 'space-between',
                                                    py: 1,
                                                    borderBottom: index < selectedBooking.expenses.length - 1 ? '1px solid #eee' : 'none'
                                                }}>
                                                    <Box>
                                                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                                            {expense.description}
                                                        </Typography>
                                                        <Typography variant="caption" color="text.secondary">
                                                            {expense.category}
                                                        </Typography>
                                                    </Box>
                                                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                                        ${expense.amount.toLocaleString()}
                                                    </Typography>
                                                </Box>
                                            ))}
                                            <Box sx={{ mt: 2, pt: 2, borderTop: '2px solid #e0e0e0' }}>
                                                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                                                    Total gastos: ${(selectedBooking.expenses.reduce((sum, expense) => sum + expense.amount, 0)).toLocaleString()}
                                                </Typography>
                                            </Box>
                                        </CardContent>
                                    </Card>
                                )}

                                {/* Cost calculation fields */}
                                <Grid container spacing={3}>
                                    <Grid item xs={12} sm={6}>
                                        <TextField
                                            label="Costo Real del Evento"
                                            type="number"
                                            fullWidth
                                            value={costData.event_cost}
                                            onChange={(e) => setCostData({...costData, event_cost: e.target.value})}
                                            helperText="Total calculado automáticamente desde insumos + gastos"
                                            InputProps={{
                                                startAdornment: '$'
                                            }}
                                        />
                                    </Grid>
                                    <Grid item xs={12} sm={6}>
                                        <TextField
                                            label="Precio Final Cobrado"
                                            type="number"
                                            fullWidth
                                            value={costData.event_revenue}
                                            onChange={(e) => setCostData({...costData, event_revenue: e.target.value})}
                                            helperText="Monto total cobrado al cliente"
                                            InputProps={{
                                                startAdornment: '$'
                                            }}
                                        />
                                    </Grid>
                                    <Grid item xs={12}>
                                        <Alert severity="info" sx={{ mb: 2 }}>
                                            <Typography variant="body2">
                                                <strong>Ganancia estimada:</strong> $
                                                {costData.event_revenue && costData.event_cost
                                                    ? formatCurrency((parseFloat(costData.event_revenue) || 0) - (parseFloat(costData.event_cost) || 0))
                                                    : '0.00'
                                                }
                                            </Typography>
                                        </Alert>
                                    </Grid>
                                    <Grid item xs={12}>
                                        <TextField
                                            label="Notas del Evento (Opcional)"
                                            multiline
                                            rows={3}
                                            fullWidth
                                            value={costData.notes}
                                            onChange={(e) => setCostData({...costData, notes: e.target.value})}
                                            helperText="Observaciones, problemas, comentarios del cliente, etc."
                                        />
                                    </Grid>
                                </Grid>
                            </Box>
                        )}

                        {/* Tab Panel 1: Integrated Supplies Table */}
                        {costTabValue === 1 && (
                            <Box>
                                {loadingSupplies ? (
                                    <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                                        <CircularProgress />
                                    </Box>
                                ) : (
                                    <>
                                        {/* Supply Status Alert */}
                                        <Alert
                                            severity={supplyStatus.can_complete_event ? "success" : "warning"}
                                            sx={{ mb: 3 }}
                                        >
                                            {supplyStatus.can_complete_event
                                                ? `✅ Insumos y consumo completos. Listo para completar evento.`
                                                : supplyStatus.has_supplies && !supplyStatus.has_consumption
                                                    ? "⚠️ Insumos estimados listos. Falta registrar consumo real."
                                                    : "⚠️ Necesitas registrar los insumos para este evento."
                                            }
                                        </Alert>

                                        {/* Integrated Supplies Table */}
                                        <Card sx={{ mb: 3 }}>
                                            <CardContent>
                                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                                                    <Typography variant="h6">
                                                        Gestión de Insumos
                                                    </Typography>
                                                    <Button
                                                        onClick={handleAddSupplyItem}
                                                        startIcon={<Add />}
                                                        variant="outlined"
                                                        size="small"
                                                    >
                                                        Agregar Insumo
                                                    </Button>
                                                </Box>

                                                {integratedSupplies.items.length === 0 ? (
                                                    <Alert severity="info">
                                                        No hay insumos agregados. Haz clic en "Agregar Insumo" para empezar.
                                                    </Alert>
                                                ) : (
                                                    <TableContainer component={Paper} variant="outlined">
                                                        <Table>
                                                            <TableHead>
                                                                <TableRow sx={{ bgcolor: 'grey.50' }}>
                                                                    <TableCell><strong>Insumo</strong></TableCell>
                                                                    <TableCell align="center"><strong>Estimado</strong></TableCell>
                                                                    <TableCell align="center"><strong>Confirmado</strong></TableCell>
                                                                    <TableCell align="center"><strong>Costo/Unidad</strong></TableCell>
                                                                    <TableCell align="center"><strong>Costo Total</strong></TableCell>
                                                                    <TableCell align="center"><strong>Variación</strong></TableCell>
                                                                    <TableCell align="center"><strong>Acciones</strong></TableCell>
                                                                </TableRow>
                                                            </TableHead>
                                                            <TableBody>
                                                                {integratedSupplies.items.map((item, index) => (
                                                                    <TableRow key={index}>
                                                                        <TableCell>
                                                                            <FormControl fullWidth size="small">
                                                                                <Select
                                                                                    value={item.item_id}
                                                                                    onChange={(e) => handleSupplyItemChange(index, 'item_id', e.target.value)}
                                                                                    displayEmpty
                                                                                >
                                                                                    <MenuItem value="">
                                                                                        <em>Seleccionar...</em>
                                                                                    </MenuItem>
                                                                                    {inventoryItems.map((inv) => (
                                                                                        <MenuItem key={inv.id} value={inv.id}>
                                                                                            {inv.name}
                                                                                            <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                                                                                                ({inv.current_stock} {inv.unit})
                                                                                            </Typography>
                                                                                        </MenuItem>
                                                                                    ))}
                                                                                </Select>
                                                                            </FormControl>
                                                                        </TableCell>
                                                                        <TableCell align="center">
                                                                            <TextField
                                                                                type="number"
                                                                                size="small"
                                                                                value={item.estimated_quantity}
                                                                                onChange={(e) => handleSupplyItemChange(index, 'estimated_quantity', e.target.value)}
                                                                                InputProps={{
                                                                                    endAdornment: <Typography variant="caption">{item.unit}</Typography>
                                                                                }}
                                                                                sx={{ width: 100 }}
                                                                            />
                                                                        </TableCell>
                                                                        <TableCell align="center">
                                                                            <TextField
                                                                                type="number"
                                                                                size="small"
                                                                                value={item.actual_quantity_consumed}
                                                                                onChange={(e) => handleSupplyItemChange(index, 'actual_quantity_consumed', e.target.value)}
                                                                                InputProps={{
                                                                                    endAdornment: <Typography variant="caption">{item.unit}</Typography>
                                                                                }}
                                                                                sx={{ width: 100 }}
                                                                                disabled={!supplyStatus.has_supplies}
                                                                            />
                                                                        </TableCell>
                                                                        <TableCell align="center">
                                                                            <Typography variant="body2">
                                                                                ${item.cost_per_unit?.toFixed(2) || '0.00'}
                                                                            </Typography>
                                                                        </TableCell>
                                                                        <TableCell align="center">
                                                                            <Box>
                                                                                <Typography variant="body2" color="text.secondary">
                                                                                    Est: ${item.estimated_total_cost?.toFixed(2) || '0.00'}
                                                                                </Typography>
                                                                                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                                                                    Real: ${item.actual_total_cost?.toFixed(2) || '0.00'}
                                                                                </Typography>
                                                                            </Box>
                                                                        </TableCell>
                                                                        <TableCell align="center">
                                                                            {item.variance !== 0 && (
                                                                                <Chip
                                                                                    label={`${item.variance > 0 ? '+' : ''}${item.variance?.toFixed(1)} ${item.unit}`}
                                                                                    size="small"
                                                                                    color={item.variance > 0 ? "error" : "success"}
                                                                                    variant="outlined"
                                                                                />
                                                                            )}
                                                                        </TableCell>
                                                                        <TableCell align="center">
                                                                            <IconButton
                                                                                onClick={() => handleRemoveSupplyItem(index)}
                                                                                color="error"
                                                                                size="small"
                                                                            >
                                                                                <Delete />
                                                                            </IconButton>
                                                                        </TableCell>
                                                                    </TableRow>
                                                                ))}
                                                            </TableBody>
                                                        </Table>
                                                    </TableContainer>
                                                )}

                                                {/* Summary Cards */}
                                                {integratedSupplies.items.length > 0 && (
                                                    <Grid container spacing={2} sx={{ mt: 2 }}>
                                                        <Grid item xs={12} sm={6}>
                                                            <Card variant="outlined" sx={{ bgcolor: 'blue.50' }}>
                                                                <CardContent sx={{ py: 1 }}>
                                                                    <Typography variant="body2" color="text.secondary">
                                                                        Costo Estimado
                                                                    </Typography>
                                                                    <Typography variant="h6">
                                                                        ${getTotalEstimatedCost().toFixed(2)}
                                                                    </Typography>
                                                                </CardContent>
                                                            </Card>
                                                        </Grid>
                                                        <Grid item xs={12} sm={6}>
                                                            <Card variant="outlined" sx={{ bgcolor: 'green.50' }}>
                                                                <CardContent sx={{ py: 1 }}>
                                                                    <Typography variant="body2" color="text.secondary">
                                                                        Costo Real
                                                                    </Typography>
                                                                    <Typography variant="h6">
                                                                        ${getTotalActualCost().toFixed(2)}
                                                                    </Typography>
                                                                </CardContent>
                                                            </Card>
                                                        </Grid>
                                                    </Grid>
                                                )}

                                                {/* Notes Section */}
                                                <Box sx={{ mt: 3 }}>
                                                    <Grid container spacing={2}>
                                                        <Grid item xs={12} sm={6}>
                                                            <TextField
                                                                label="Notas de Estimación"
                                                                multiline
                                                                rows={2}
                                                                fullWidth
                                                                value={integratedSupplies.notes}
                                                                onChange={(e) => setIntegratedSupplies({...integratedSupplies, notes: e.target.value})}
                                                                placeholder="Observaciones sobre los insumos estimados..."
                                                            />
                                                        </Grid>
                                                        <Grid item xs={12} sm={6}>
                                                            <TextField
                                                                label="Notas de Consumo"
                                                                multiline
                                                                rows={2}
                                                                fullWidth
                                                                value={integratedSupplies.consumption_notes}
                                                                onChange={(e) => setIntegratedSupplies({...integratedSupplies, consumption_notes: e.target.value})}
                                                                placeholder="Observaciones sobre el consumo real..."
                                                                disabled={!supplyStatus.has_supplies}
                                                            />
                                                        </Grid>
                                                    </Grid>
                                                </Box>

                                                {/* Action Buttons */}
                                                <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
                                                    <Button
                                                        onClick={handleSaveSupplies}
                                                        variant="contained"
                                                        disabled={integratedSupplies.items.length === 0}
                                                        color="primary"
                                                    >
                                                        {supplyStatus.has_supplies ? 'Actualizar Estimación' : 'Guardar Estimación'}
                                                    </Button>

                                                    {supplyStatus.has_supplies && (
                                                        <Button
                                                            onClick={handleSaveConsumption}
                                                            variant="contained"
                                                            disabled={!supplyStatus.has_supplies || supplyStatus.has_consumption}
                                                            color="success"
                                                        >
                                                            {supplyStatus.has_consumption ? 'Consumo Registrado' : 'Registrar Consumo'}
                                                        </Button>
                                                    )}
                                                </Box>
                                            </CardContent>
                                        </Card>
                                    </>
                                )}
                            </Box>
                        )}
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setCostDialog(false)}>
                        Cancelar
                    </Button>
                    <Button
                        onClick={() => {
                            if (!supplyStatus.can_complete_event) {
                                toast.error('Necesitas registrar insumos y consumo antes de completar el evento')
                                return
                            }
                            if (window.confirm('¿Estás seguro de que quieres marcar este evento como completado? Esta acción calculará la ganancia final y cambiará el estado del evento.')) {
                                handleCompleteWithCost()
                            }
                        }}
                        variant="contained"
                        color="success"
                        disabled={!supplyStatus.can_complete_event}
                        startIcon={<CheckCircle />}
                    >
                        Completar Evento
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Enhanced Expense Dialog with Tabs (Gastos | Insumos) */}
            <Dialog open={expenseDialog} onClose={() => setExpenseDialog(false)} maxWidth="lg" fullWidth>
                <DialogTitle>
                    Gestión de Gastos e Insumos - {selectedBooking?.client_name}
                    <IconButton
                        onClick={() => setExpenseDialog(false)}
                        sx={{ position: 'absolute', right: 8, top: 8 }}
                    >
                        <Close />
                    </IconButton>
                </DialogTitle>
                <DialogContent>
                    {selectedBooking && (
                        <Box sx={{ mt: 2 }}>
                            {/* Event Summary */}
                            <Card sx={{ mb: 3, bgcolor: 'grey.50' }}>
                                <CardContent>
                                    <Grid container spacing={2}>
                                        <Grid item xs={12} sm={6}>
                                            <Typography variant="body2" color="text.secondary">
                                                <strong>Evento:</strong> {selectedBooking.event_type} - {selectedBooking.participants} participantes
                                            </Typography>
                                            <Typography variant="body2" color="text.secondary">
                                                <strong>Fecha:</strong> {selectedBooking.event_date} {selectedBooking.event_time}
                                            </Typography>
                                        </Grid>
                                        <Grid item xs={12} sm={6}>
                                            <Typography variant="body2" color="text.secondary">
                                                <strong>Precio estimado:</strong> ${selectedBooking.estimated_price?.toLocaleString()}
                                            </Typography>
                                            <Typography variant="body2" color="text.secondary">
                                                <strong>Estado:</strong> {selectedBooking.status}
                                            </Typography>
                                        </Grid>
                                    </Grid>
                                </CardContent>
                            </Card>

                            {/* Tabs for Gastos and Insumos */}
                            <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
                                <Tabs
                                    value={costTabValue}
                                    onChange={(e, newValue) => setCostTabValue(newValue)}
                                    aria-label="gastos e insumos tabs"
                                >
                                    <Tab label="Gastos" />
                                    <Tab label="Insumos" />
                                </Tabs>
                            </Box>

                            {/* Tab Panel 0: Gastos (Expenses) */}
                            {costTabValue === 0 && (
                                <Box>
                                    {/* Add new expense */}
                                    <Card sx={{ mb: 3 }}>
                                        <CardContent>
                                            <Typography variant="h6" sx={{ mb: 2 }}>
                                                Agregar Nuevo Gasto
                                            </Typography>
                                            <Grid container spacing={2}>
                                                <Grid item xs={12}>
                                                    <TextField
                                                        label="Descripción del Gasto"
                                                        fullWidth
                                                        required
                                                        value={expenseData.description}
                                                        onChange={(e) => setExpenseData({...expenseData, description: e.target.value})}
                                                        placeholder="Ej: Ingredientes para pizzas"
                                                    />
                                                </Grid>
                                                <Grid item xs={12} sm={6}>
                                                    <TextField
                                                        label="Monto"
                                                        type="number"
                                                        fullWidth
                                                        required
                                                        value={expenseData.amount}
                                                        onChange={(e) => setExpenseData({...expenseData, amount: e.target.value})}
                                                        InputProps={{
                                                            startAdornment: '$'
                                                        }}
                                                    />
                                                </Grid>
                                                <Grid item xs={12} sm={6}>
                                                    <FormControl fullWidth>
                                                        <Select
                                                            value={expenseData.category}
                                                            label="Categoría"
                                                            displayEmpty
                                                            renderValue={(value) => value ? {
                                                                'ingredients': 'Ingredientes',
                                                                'transport': 'Transporte',
                                                                'supplies': 'Materiales',
                                                                'other': 'Otros'
                                                            }[value] : 'Selecciona Categoría'}
                                                            onChange={(e) => setExpenseData({...expenseData, category: e.target.value})}
                                                        >
                                                            <MenuItem value="ingredientes">Ingredientes</MenuItem>
                                                            <MenuItem value="transporte">Transporte</MenuItem>
                                                            <MenuItem value="equipos">Equipos/Materiales</MenuItem>
                                                            <MenuItem value="personal">Personal Extra</MenuItem>
                                                            <MenuItem value="otros">Otros</MenuItem>
                                                        </Select>
                                                    </FormControl>
                                                </Grid>
                                                <Grid item xs={12}>
                                                    <Button
                                                        onClick={handleAddExpense}
                                                        variant="contained"
                                                        color="primary"
                                                        disabled={!expenseData.description || !expenseData.amount}
                                                        startIcon={<AddBox />}
                                                    >
                                                        Agregar Gasto
                                                    </Button>
                                                </Grid>
                                            </Grid>
                                        </CardContent>
                                    </Card>

                                    {/* Existing expenses */}
                                    {selectedBooking.expenses && selectedBooking.expenses.length > 0 && (
                                        <Card>
                                            <CardContent>
                                                <Typography variant="h6" sx={{ mb: 2 }}>
                                                    Gastos Registrados
                                                </Typography>
                                                {selectedBooking.expenses.map((expense, index) => (
                                                    <Box key={index} sx={{
                                                        p: 2,
                                                        border: '1px solid #e0e0e0',
                                                        borderRadius: 1,
                                                        mb: 1,
                                                        display: 'flex',
                                                        justifyContent: 'space-between',
                                                        alignItems: 'center'
                                                    }}>
                                                        <Box sx={{ flex: 1 }}>
                                                            <Typography variant="body1" sx={{ fontWeight: 500 }}>
                                                                {expense.description}
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary">
                                                                {expense.category}
                                                            </Typography>
                                                        </Box>
                                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                            <Typography variant="h6" sx={{ fontWeight: 600, mr: 2 }}>
                                                                ${expense.amount.toLocaleString()}
                                                            </Typography>
                                                            <IconButton
                                                                size="small"
                                                                onClick={() => handleEditExpense(index)}
                                                                sx={{ color: 'primary.main' }}
                                                            >
                                                                <Edit fontSize="small" />
                                                            </IconButton>
                                                            <IconButton
                                                                size="small"
                                                                onClick={() => handleDeleteExpense(index)}
                                                                sx={{ color: 'error.main' }}
                                                            >
                                                                <Delete fontSize="small" />
                                                            </IconButton>
                                                        </Box>
                                                    </Box>
                                                ))}
                                                <Box sx={{
                                                    p: 2,
                                                    bgcolor: 'grey.100',
                                                    borderRadius: 1,
                                                    display: 'flex',
                                                    justifyContent: 'space-between',
                                                    mt: 2
                                                }}>
                                                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                                                        Total Gastos:
                                                    </Typography>
                                                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                                                        ${(selectedBooking.expenses.reduce((sum, expense) => sum + expense.amount, 0)).toLocaleString()}
                                                    </Typography>
                                                </Box>
                                            </CardContent>
                                        </Card>
                                    )}
                                </Box>
                            )}

                            {/* Tab Panel 1: Integrated Supplies Table */}
                            {costTabValue === 1 && (
                                <Box>
                                    {loadingSupplies ? (
                                        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                                            <CircularProgress />
                                        </Box>
                                    ) : (
                                        <>
                                            {/* Supply Status Alert */}
                                            <Alert
                                                severity={supplyStatus.has_consumption ? "success" : supplyStatus.has_supplies ? "info" : "warning"}
                                                sx={{ mb: 3 }}
                                            >
                                                {supplyStatus.has_consumption
                                                    ? `✅ Consumo registrado. Evento listo para completar.`
                                                    : supplyStatus.has_supplies
                                                        ? "⚠️ Insumos estimados guardados. Registra el consumo real al terminar el evento."
                                                        : "ℹ️ Primero registra los insumos estimados para el evento."
                                                }
                                            </Alert>

                                            {/* Integrated Supplies Table */}
                                            <Card sx={{ mb: 3 }}>
                                                <CardContent>
                                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                                                        <Typography variant="h6">
                                                            Gestión de Insumos
                                                        </Typography>
                                                        <Button
                                                            onClick={handleAddSupplyItem}
                                                            startIcon={<Add />}
                                                            variant="outlined"
                                                            size="small"
                                                        >
                                                            Agregar Insumo
                                                        </Button>
                                                    </Box>

                                                    {integratedSupplies.items.length === 0 ? (
                                                        <Alert severity="info">
                                                            No hay insumos agregados. Haz clic en "Agregar Insumo" para empezar.
                                                        </Alert>
                                                    ) : (
                                                        <TableContainer component={Paper} variant="outlined">
                                                            <Table>
                                                                <TableHead>
                                                                    <TableRow sx={{ bgcolor: 'grey.50' }}>
                                                                        <TableCell><strong>Insumo</strong></TableCell>
                                                                        <TableCell align="center"><strong>Estimado</strong></TableCell>
                                                                        <TableCell align="center"><strong>Confirmado</strong></TableCell>
                                                                        <TableCell align="center"><strong>Costo/Unidad</strong></TableCell>
                                                                        <TableCell align="center"><strong>Costo Total</strong></TableCell>
                                                                        <TableCell align="center"><strong>Variación</strong></TableCell>
                                                                        <TableCell align="center"><strong>Acciones</strong></TableCell>
                                                                    </TableRow>
                                                                </TableHead>
                                                                <TableBody>
                                                                    {integratedSupplies.items.map((item, index) => (
                                                                        <TableRow key={index}>
                                                                            <TableCell>
                                                                                <FormControl fullWidth size="small">
                                                                                    <Select
                                                                                        value={item.item_id}
                                                                                        onChange={(e) => handleSupplyItemChange(index, 'item_id', e.target.value)}
                                                                                        displayEmpty
                                                                                    >
                                                                                        <MenuItem value="">
                                                                                            <em>Seleccionar...</em>
                                                                                        </MenuItem>
                                                                                        {inventoryItems.map((inv) => (
                                                                                            <MenuItem key={inv.id} value={inv.id}>
                                                                                                {inv.name}
                                                                                                <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                                                                                                    ({inv.current_stock} {inv.unit})
                                                                                                </Typography>
                                                                                            </MenuItem>
                                                                                        ))}
                                                                                    </Select>
                                                                                </FormControl>
                                                                            </TableCell>
                                                                            <TableCell align="center">
                                                                                <TextField
                                                                                    type="number"
                                                                                    size="small"
                                                                                    value={item.estimated_quantity}
                                                                                    onChange={(e) => handleSupplyItemChange(index, 'estimated_quantity', e.target.value)}
                                                                                    InputProps={{
                                                                                        endAdornment: <Typography variant="caption">{item.unit}</Typography>
                                                                                    }}
                                                                                    sx={{ width: 100 }}
                                                                                />
                                                                            </TableCell>
                                                                            <TableCell align="center">
                                                                                <TextField
                                                                                    type="number"
                                                                                    size="small"
                                                                                    value={item.actual_quantity_consumed}
                                                                                    onChange={(e) => handleSupplyItemChange(index, 'actual_quantity_consumed', e.target.value)}
                                                                                    InputProps={{
                                                                                        endAdornment: <Typography variant="caption">{item.unit}</Typography>
                                                                                    }}
                                                                                    sx={{ width: 100 }}
                                                                                    disabled={!supplyStatus.has_supplies}
                                                                                    placeholder="Después del evento"
                                                                                />
                                                                            </TableCell>
                                                                            <TableCell align="center">
                                                                                <Typography variant="body2">
                                                                                    ${item.cost_per_unit?.toFixed(2) || '0.00'}
                                                                                </Typography>
                                                                            </TableCell>
                                                                            <TableCell align="center">
                                                                                <Box>
                                                                                    <Typography variant="body2" color="text.secondary">
                                                                                        Est: ${item.estimated_total_cost?.toFixed(2) || '0.00'}
                                                                                    </Typography>
                                                                                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                                                                        Real: ${item.actual_total_cost?.toFixed(2) || '0.00'}
                                                                                    </Typography>
                                                                                </Box>
                                                                            </TableCell>
                                                                            <TableCell align="center">
                                                                                {item.variance !== 0 && (
                                                                                    <Chip
                                                                                        label={`${item.variance > 0 ? '+' : ''}${item.variance?.toFixed(1)} ${item.unit}`}
                                                                                        size="small"
                                                                                        color={item.variance > 0 ? "error" : "success"}
                                                                                        variant="outlined"
                                                                                    />
                                                                                )}
                                                                            </TableCell>
                                                                            <TableCell align="center">
                                                                                <IconButton
                                                                                    onClick={() => handleRemoveSupplyItem(index)}
                                                                                    color="error"
                                                                                    size="small"
                                                                                >
                                                                                    <Delete />
                                                                                </IconButton>
                                                                            </TableCell>
                                                                        </TableRow>
                                                                    ))}
                                                                </TableBody>
                                                            </Table>
                                                        </TableContainer>
                                                    )}

                                                    {/* Summary Cards */}
                                                    {integratedSupplies.items.length > 0 && (
                                                        <Grid container spacing={2} sx={{ mt: 2 }}>
                                                            <Grid item xs={12} sm={6}>
                                                                <Card variant="outlined" sx={{ bgcolor: 'blue.50' }}>
                                                                    <CardContent sx={{ py: 1 }}>
                                                                        <Typography variant="body2" color="text.secondary">
                                                                            Costo Estimado
                                                                        </Typography>
                                                                        <Typography variant="h6">
                                                                            ${getTotalEstimatedCost().toFixed(2)}
                                                                        </Typography>
                                                                    </CardContent>
                                                                </Card>
                                                            </Grid>
                                                            <Grid item xs={12} sm={6}>
                                                                <Card variant="outlined" sx={{ bgcolor: 'green.50' }}>
                                                                    <CardContent sx={{ py: 1 }}>
                                                                        <Typography variant="body2" color="text.secondary">
                                                                            Costo Real
                                                                        </Typography>
                                                                        <Typography variant="h6">
                                                                            ${getTotalActualCost().toFixed(2)}
                                                                        </Typography>
                                                                    </CardContent>
                                                                </Card>
                                                            </Grid>
                                                        </Grid>
                                                    )}

                                                    {/* Notes Section */}
                                                    <Box sx={{ mt: 3 }}>
                                                        <Grid container spacing={2}>
                                                            <Grid item xs={12} sm={6}>
                                                                <TextField
                                                                    label="Notas de Estimación"
                                                                    multiline
                                                                    rows={2}
                                                                    fullWidth
                                                                    value={integratedSupplies.notes}
                                                                    onChange={(e) => setIntegratedSupplies({...integratedSupplies, notes: e.target.value})}
                                                                    placeholder="Observaciones sobre los insumos estimados..."
                                                                />
                                                            </Grid>
                                                            <Grid item xs={12} sm={6}>
                                                                <TextField
                                                                    label="Notas de Consumo"
                                                                    multiline
                                                                    rows={2}
                                                                    fullWidth
                                                                    value={integratedSupplies.consumption_notes}
                                                                    onChange={(e) => setIntegratedSupplies({...integratedSupplies, consumption_notes: e.target.value})}
                                                                    placeholder="Observaciones sobre el consumo real..."
                                                                    disabled={!supplyStatus.has_supplies}
                                                                />
                                                            </Grid>
                                                        </Grid>
                                                    </Box>

                                                    {/* Action Buttons */}
                                                    <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
                                                        <Button
                                                            onClick={handleSaveSupplies}
                                                            variant="contained"
                                                            disabled={integratedSupplies.items.length === 0}
                                                            color="primary"
                                                        >
                                                            {supplyStatus.has_supplies ? 'Actualizar Estimación' : 'Guardar Estimación'}
                                                        </Button>

                                                        {supplyStatus.has_supplies && (
                                                            <Button
                                                                onClick={handleSaveConsumption}
                                                                variant="contained"
                                                                disabled={!supplyStatus.has_supplies || supplyStatus.has_consumption}
                                                                color="success"
                                                            >
                                                                {supplyStatus.has_consumption ? 'Consumo Registrado' : 'Registrar Consumo'}
                                                            </Button>
                                                        )}
                                                    </Box>
                                                </CardContent>
                                            </Card>
                                        </>
                                    )}
                                </Box>
                            )}
                        </Box>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setExpenseDialog(false)}>
                        Cerrar
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Edit Expense Dialog */}
            <Dialog open={editExpenseDialog} onClose={() => setEditExpenseDialog(false)} maxWidth="sm" fullWidth>
                <DialogTitle>
                    Editar Gasto
                    <IconButton
                        onClick={() => setEditExpenseDialog(false)}
                        sx={{ position: 'absolute', right: 8, top: 8 }}
                    >
                        <Close />
                    </IconButton>
                </DialogTitle>
                <DialogContent>
                    <Grid container spacing={2} sx={{ mt: 1 }}>
                        <Grid item xs={12}>
                            <TextField
                                label="Descripción del Gasto"
                                fullWidth
                                required
                                value={expenseData.description}
                                onChange={(e) => setExpenseData({...expenseData, description: e.target.value})}
                                placeholder="Ej: Ingredientes para pizzas"
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                label="Monto"
                                type="number"
                                fullWidth
                                required
                                value={expenseData.amount}
                                onChange={(e) => setExpenseData({...expenseData, amount: e.target.value})}
                                InputProps={{
                                    startAdornment: '$'
                                }}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <FormControl fullWidth>
                                <Select
                                    value={expenseData.category}
                                    label="Categoría"
                                    displayEmpty
                                    renderValue={(value) => value ? {
                                        'ingredients': 'Ingredientes',
                                        'transport': 'Transporte',
                                        'supplies': 'Materiales',
                                        'other': 'Otros'
                                    }[value] : 'Selecciona Categoría'}
                                    onChange={(e) => setExpenseData({...expenseData, category: e.target.value})}
                                >
                                    <MenuItem value="ingredientes">Ingredientes</MenuItem>
                                    <MenuItem value="transporte">Transporte</MenuItem>
                                    <MenuItem value="equipos">Equipos/Materiales</MenuItem>
                                    <MenuItem value="personal">Personal Extra</MenuItem>
                                    <MenuItem value="otros">Otros</MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>
                    </Grid>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setEditExpenseDialog(false)}>
                        Cancelar
                    </Button>
                    <Button
                        onClick={handleUpdateExpense}
                        variant="contained"
                        color="primary"
                        disabled={!expenseData.description || !expenseData.amount}
                        startIcon={<Edit />}
                    >
                        Actualizar Gasto
                    </Button>
                </DialogActions>
            </Dialog>

            <Dialog open={deleteDialog} onClose={() => setDeleteDialog(false)}>
                <DialogTitle>Confirmar Eliminación</DialogTitle>
                <DialogContent>
                    <Typography>
                        ¿Estás seguro de que quieres eliminar este agendamiento?
                        Esta acción no se puede deshacer.
                    </Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDeleteDialog(false)}>Cancelar</Button>
                    <Button onClick={handleDeleteBooking} color="error" variant="contained">
                        Eliminar
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Ver Detalle (solo lectura) */}
            <Dialog open={viewDialog} onClose={() => setViewDialog(false)} maxWidth="md" fullWidth>
                <DialogTitle>
                    Resumen del Evento
                    <IconButton onClick={() => setViewDialog(false)} sx={{ position: 'absolute', right: 8, top: 8 }}>
                        <Close />
                    </IconButton>
                </DialogTitle>
                <DialogContent dividers>
                    {selectedBooking && (
                        <Box>
                            <Grid container spacing={2} sx={{ mb: 2 }}>
                                <Grid item xs={12} md={6}>
                                    <Chip size="small" color={getStatusColor(selectedBooking.status)} label={getStatusLabel(selectedBooking.status)} />
                                </Grid>
                                <Grid item xs={12} md={6}>
                                    <Typography variant="body2" align="right">Creado: {format(new Date(selectedBooking.created_at), 'dd/MM/yyyy HH:mm')}</Typography>
                                </Grid>
                            </Grid>

                            {/* Secciones en acordeones */}
                            <Box>
                                <Accordion defaultExpanded>
                                    <AccordionSummary expandIcon={<ExpandMore />}>
                                        <Typography sx={{ fontWeight: 600 }}>Información</Typography>
                                    </AccordionSummary>
                                    <AccordionDetails>
                                        <Grid container spacing={1}>
                                            <Grid item xs={12} sm={6}><Typography variant="body2"><strong>Cliente:</strong> {selectedBooking.client_name}</Typography></Grid>
                                            <Grid item xs={12} sm={6}><Typography variant="body2"><strong>Teléfono:</strong> {selectedBooking.client_phone}</Typography></Grid>
                                            <Grid item xs={12} sm={6}><Typography variant="body2"><strong>Email:</strong> {selectedBooking.client_email}</Typography></Grid>
                                            <Grid item xs={12} sm={6}><Typography variant="body2"><strong>Ubicación:</strong> {selectedBooking.location || '-'}</Typography></Grid>
                                        </Grid>
                                    </AccordionDetails>
                                </Accordion>

                                <Accordion defaultExpanded>
                                    <AccordionSummary expandIcon={<ExpandMore />}>
                                        <Typography sx={{ fontWeight: 600 }}>Detalle del Evento</Typography>
                                    </AccordionSummary>
                                    <AccordionDetails>
                                        <Grid container spacing={1}>
                                            <Grid item xs={12} sm={6}><Typography variant="body2"><strong>Servicio:</strong> {getServiceLabel(selectedBooking.service_type)}</Typography></Grid>
                                            <Grid item xs={12} sm={6}><Typography variant="body2"><strong>Fecha:</strong> {selectedBooking.event_date} {selectedBooking.event_time}</Typography></Grid>
                                            {selectedBooking.pizzeros_participants > 0 && (
                                                <Grid item xs={12}><Typography variant="body2"><strong>Pizzeros en Acción:</strong> {selectedBooking.pizzeros_participants} niños</Typography></Grid>
                                            )}
                                            {(selectedBooking.party_guests || selectedBooking.pizza_quantity) && (
                                                <Grid item xs={12}><Typography variant="body2"><strong>Pizza Party:</strong> {selectedBooking.party_guests || '-'} personas / {selectedBooking.pizza_quantity || 10} pizzas</Typography></Grid>
                                            )}
                                            {selectedBooking.special_requests && (
                                                <Grid item xs={12}><Typography variant="body2"><strong>Notas:</strong> {selectedBooking.special_requests}</Typography></Grid>
                                            )}
                                        </Grid>
                                    </AccordionDetails>
                                </Accordion>

                                <Accordion defaultExpanded>
                                    <AccordionSummary expandIcon={<ExpandMore />}>
                                        <Typography sx={{ fontWeight: 600 }}>Ingresos y Costos</Typography>
                                    </AccordionSummary>
                                    <AccordionDetails>
                                        <Grid container spacing={1}>
                                            <Grid item xs={12} sm={4}><Typography variant="body2"><strong>Total cobrado:</strong> ${selectedBooking.estimated_price?.toLocaleString() || '-'}</Typography></Grid>
                                            <Grid item xs={12} sm={4}><Typography variant="body2"><strong>Costo:</strong> ${calculateTotalCost(selectedBooking)?.toLocaleString() || '-'}</Typography></Grid>
                                            <Grid item xs={12} sm={4}><Typography variant="body2"><strong>Utilidad:</strong> ${selectedBooking.event_profit?.toLocaleString() || '-'}</Typography></Grid>
                                        </Grid>
                                        {Array.isArray(selectedBooking.expenses) && selectedBooking.expenses.length > 0 && (
                                            <Box sx={{ mt: 2 }}>
                                                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>Detalle de Gastos</Typography>
                                                {selectedBooking.expenses.map((e, i) => (
                                                    <Box key={i} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}>
                                                        <Typography variant="body2">{e.description}</Typography>
                                                        <Typography variant="body2">${(e.amount||0).toLocaleString()}</Typography>
                                                    </Box>
                                                ))}
                                            </Box>
                                        )}
                                    </AccordionDetails>
                                </Accordion>

                                <Accordion>
                                    <AccordionSummary expandIcon={<ExpandMore />}>
                                        <Typography sx={{ fontWeight: 600 }}>Insumos y Consumo</Typography>
                                    </AccordionSummary>
                                    <AccordionDetails>
                                        {loadingSupplies ? (
                                            <Typography variant="body2">Cargando...</Typography>
                                        ) : (
                                            <>
                                                <Typography variant="body2" sx={{ mb: 1 }}>
                                                    Estado: {supplyStatus.can_complete_event
                                                        ? 'Insumos y consumo registrados'
                                                        : supplyStatus.has_supplies
                                                            ? 'Insumos estimados listos; falta consumo'
                                                            : 'Sin registros de insumos'}
                                                </Typography>
                                                {integratedSupplies.items.length > 0 && (
                                                    <>
                                                        <Typography variant="body2">Costo Estimado: ${getTotalEstimatedCost().toFixed(0)}</Typography>
                                                        <Typography variant="body2">Costo Real: ${getTotalActualCost().toFixed(0)}</Typography>
                                                    </>
                                                )}
                                            </>
                                        )}
                                    </AccordionDetails>
                                </Accordion>
                            </Box>
                        </Box>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setViewDialog(false)}>Cerrar</Button>
                </DialogActions>
            </Dialog>
        </Box>
    )
}

export default BookingsManagement
