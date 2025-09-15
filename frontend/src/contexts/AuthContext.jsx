import { createContext, useContext, useEffect, useState } from 'react'
import { auth } from '../services/firebase'
import { 
  signInWithEmailAndPassword, 
  signOut, 
  onAuthStateChanged 
} from 'firebase/auth'
import toast from 'react-hot-toast'

const AuthContext = createContext({})

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Login function
  const login = async (email, password) => {
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password)
      toast.success('¡Bienvenido!')
      return userCredential.user
    } catch (error) {
      console.error('Error logging in:', error)
      let errorMessage = 'Error al iniciar sesión'
      
      switch (error.code) {
        case 'auth/user-not-found':
          errorMessage = 'Usuario no encontrado'
          break
        case 'auth/wrong-password':
          errorMessage = 'Contraseña incorrecta'
          break
        case 'auth/invalid-email':
          errorMessage = 'Email inválido'
          break
        case 'auth/too-many-requests':
          errorMessage = 'Demasiados intentos. Intenta más tarde'
          break
        default:
          errorMessage = 'Error al iniciar sesión'
      }
      
      toast.error(errorMessage)
      throw error
    }
  }

  // Logout function
  const logout = async () => {
    try {
      await signOut(auth)
      toast.success('Sesión cerrada')
    } catch (error) {
      console.error('Error logging out:', error)
      toast.error('Error al cerrar sesión')
      throw error
    }
  }

  // Check if user is admin
  const isAdmin = () => {
    return user && user.email // Simplificado - en producción verificar roles
  }

  // Get auth token
  const getAuthToken = async () => {
    if (!user) return null
    try {
      return await user.getIdToken()
    } catch (error) {
      console.error('Error getting auth token:', error)
      return null
    }
  }

  useEffect(() => {
    let resolved = false
    let unsubscribe = () => {}
    try {
      unsubscribe = onAuthStateChanged(auth, (user) => {
        setUser(user)
        setLoading(false)
        resolved = true
      })
    } catch (err) {
      console.error('Auth initialization error:', err)
      setLoading(false)
      resolved = true
    }

    // Fallback: si Auth no responde, no bloquear la app
    const timeout = setTimeout(() => {
      if (!resolved) {
        console.warn('Auth check timeout. Continuando sin sesión para evitar bloqueo de carga.')
        setLoading(false)
      }
    }, 4000)

    return () => {
      clearTimeout(timeout)
      try { unsubscribe() } catch {}
    }
  }, [])

  const value = {
    user,
    login,
    logout,
    loading,
    isAdmin,
    getAuthToken
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}