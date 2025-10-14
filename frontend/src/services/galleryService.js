import { collection, query, where, onSnapshot, orderBy } from 'firebase/firestore'
import { db } from './firebase'

/**
 * Listen to published gallery photos in real-time
 * @param {Function} callback - Function to call with the photos array
 * @param {Object} options - Optional configuration
 * @returns {Function} Unsubscribe function
 */
export const listenGalleryPhotos = (callback, options = {}) => {
  try {
    const galleryRef = collection(db, 'gallery')

    // Build query - only get published photos
    let q = query(
      galleryRef,
      where('published', '==', true),
      orderBy('uploadedAt', 'desc')
    )

    // Set up real-time listener
    const unsubscribe = onSnapshot(
      q,
      (snapshot) => {
        const photos = []
        snapshot.forEach((doc) => {
          photos.push({
            id: doc.id,
            ...doc.data()
          })
        })

        callback(photos)
      },
      (error) => {
        console.error('Error listening to gallery photos:', error)
        if (options.onError) {
          options.onError(error)
        }
      }
    )

    return unsubscribe
  } catch (error) {
    console.error('Error setting up gallery listener:', error)
    if (options.onError) {
      options.onError(error)
    }
    return () => {} // Return empty unsubscribe function
  }
}

/**
 * Get gallery photo URLs for the rolling gallery
 * @param {Array} photos - Array of photo objects from Firebase
 * @returns {Array} Array of photo URLs
 */
export const getGalleryImageUrls = (photos) => {
  if (!Array.isArray(photos) || photos.length === 0) {
    return []
  }

  return photos
    .filter(photo => photo.url) // Only include photos with valid URLs
    .map(photo => photo.url)
}
