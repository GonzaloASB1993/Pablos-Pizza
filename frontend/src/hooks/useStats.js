import { useState, useEffect } from 'react'
import { STATS as FALLBACK_STATS } from '../data/stats'

// Hook que obtiene stats en tiempo real del backend.
// Fallback a los valores hardcodeados de stats.js si el endpoint falla o no está listo.
export function useStats() {
  const [stats, setStats] = useState(FALLBACK_STATS)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // TODO: activar cuando el endpoint /api/stats/public esté disponible en backend
    // const fetchStats = async () => {
    //   try {
    //     const res = await fetch('/api/stats/public')
    //     const data = await res.json()
    //     setStats({
    //       ...FALLBACK_STATS,
    //       kidsServed: data.totalKids ? `${data.totalKids}+` : FALLBACK_STATS.kidsServed,
    //       eventsCount: data.totalEvents ? `${data.totalEvents}+` : FALLBACK_STATS.eventsCount,
    //     })
    //   } catch {
    //     // usar fallback silenciosamente
    //   } finally {
    //     setLoading(false)
    //   }
    // }
    // fetchStats()
    setLoading(false) // remover cuando el endpoint esté listo
  }, [])

  return { stats, loading }
}
