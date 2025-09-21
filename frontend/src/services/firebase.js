import { initializeApp } from 'firebase/app'
import { getAuth } from 'firebase/auth'
import { getFirestore } from 'firebase/firestore'
import { getStorage } from 'firebase/storage'
import { initializeAppCheck, ReCaptchaEnterpriseProvider } from 'firebase/app-check'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID
}

// Aviso temprano si faltan variables en desarrollo
if (import.meta.env.DEV) {
  const missing = Object.entries(firebaseConfig)
    .filter(([, v]) => !v)
    .map(([k]) => k)
  if (missing.length) {
    console.warn('[Firebase] Faltan variables de entorno:', missing.join(', '))
  }
}

// Initialize Firebase
const app = initializeApp(firebaseConfig)

// Initialize App Check with reCAPTCHA v3
if (typeof window !== 'undefined') {
  try {
    const appCheck = initializeAppCheck(app, {
      provider: new ReCaptchaEnterpriseProvider('6LecCtArAAAAAHkrUIUvCef9nq4iCCWgcm8SQhDe'),
      isTokenAutoRefreshEnabled: true
    })
    console.log('App Check initialized successfully')
  } catch (error) {
    console.warn('App Check initialization failed:', error)
  }
}

// Initialize Firebase services
export const auth = getAuth(app)
export const db = getFirestore(app)
export const storage = getStorage(app)

export default app