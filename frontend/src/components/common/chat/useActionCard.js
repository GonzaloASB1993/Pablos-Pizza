import { useCallback, useEffect, useState } from 'react'
import { cancelPending, confirmPending, describeError, fetchPending } from './chatApi'

// Shared behaviour of every action card: confirm / cancel with busy + error state, and a
// refresh on mount (the proposal may have been resolved elsewhere or expired meanwhile).
export const useActionCard = (action, getAuthToken, onChange) => {
  const [busy, setBusy] = useState(null) // 'confirm' | 'cancel' | null
  const [error, setError] = useState(null)

  useEffect(() => {
    if (action.status !== 'pending') return undefined
    let alive = true
    fetchPending(getAuthToken, action.id)
      .then((fresh) => {
        if (alive && fresh.status !== action.status) onChange(fresh)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [action.id])

  const run = useCallback(async (kind, fn) => {
    setBusy(kind)
    setError(null)
    try {
      onChange(await fn())
    } catch (err) {
      setError(describeError(err).message)
    } finally {
      setBusy(null)
    }
  }, [onChange])

  // `payload` is optional: without it the server confirms exactly what it proposed
  const confirm = useCallback((payload) => run('confirm', () => confirmPending(getAuthToken, action.id, payload)), [run, getAuthToken, action.id])
  const cancel = useCallback(() => run('cancel', () => cancelPending(getAuthToken, action.id)), [run, getAuthToken, action.id])

  return { busy, error, confirm, cancel, editable: action.status === 'pending' || action.status === 'failed' }
}

export const clp = (n) => `$${Math.round(Number(n) || 0).toLocaleString('es-CL')}`
export const num = (v) => (v === '' || v === null || v === undefined ? NaN : Number(v))
