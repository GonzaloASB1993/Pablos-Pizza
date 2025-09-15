import { db, storage } from './firebase'
import {
  collection,
  addDoc,
  onSnapshot,
  query,
  orderBy,
  serverTimestamp,
  updateDoc,
  deleteDoc,
  doc,
  where
} from 'firebase/firestore'
import { ref, uploadBytes, getDownloadURL } from 'firebase/storage'

const COLLECTION = 'reviews'

// Suscripción en tiempo real a las reseñas, ordenadas por fecha desc
export function listenTestimonials(callback, { approvedOnly = false } = {}) {
  const base = collection(db, COLLECTION)
  // Para evitar requerir un índice compuesto, no ordenamos en servidor cuando filtramos por 'approved'
  const q = approvedOnly
    ? query(base, where('approved', '==', true))
    : query(base, orderBy('createdAt', 'desc'))
  const unsubscribe = onSnapshot(q, (snapshot) => {
    let items = snapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() }))
    if (approvedOnly) {
      items = items.sort((a, b) => {
        const ta = a.createdAt?.toDate ? a.createdAt.toDate().getTime() : 0
        const tb = b.createdAt?.toDate ? b.createdAt.toDate().getTime() : 0
        return tb - ta
      })
    }
    callback(items)
  })
  return unsubscribe
}

// Sube fotos opcionales y crea la reseña en Firestore
export async function addTestimonial({ name, email, rating, comment, files = [], token = null, isTest = false }) {
  const photoUrls = []
  for (const file of files.slice(0, 5)) {
    const path = `reviews/${Date.now()}-${file.name}`
    const storageRef = ref(storage, path)
    await uploadBytes(storageRef, file)
    const url = await getDownloadURL(storageRef)
    photoUrls.push(url)
  }

  const docData = {
    name,
    email: email || null,
    rating: Number(rating) || 0,
    comment,
    photos: photoUrls,
    createdAt: serverTimestamp(),
    token: token || null,
    isTest: Boolean(isTest),
    approved: null
  }

  await addDoc(collection(db, COLLECTION), docData)
}

export async function updateReview(id, data) {
  const ref = doc(db, COLLECTION, id)
  await updateDoc(ref, data)
}

export async function deleteReview(id) {
  const ref = doc(db, COLLECTION, id)
  await deleteDoc(ref)
}

export default {
  listenTestimonials,
  addTestimonial,
  updateReview,
  deleteReview
}
