export const MAX_IMAGES = 3
const MAX_SIDE = 1600
const JPEG_QUALITY = 0.8

const loadImage = (file) => new Promise((resolve, reject) => {
  const url = URL.createObjectURL(file)
  const img = new Image()
  img.onload = () => {
    URL.revokeObjectURL(url)
    resolve(img)
  }
  img.onerror = () => {
    URL.revokeObjectURL(url)
    reject(new Error('No se pudo leer la imagen'))
  }
  img.src = url
})

// Resize (longest side <= 1600 px) and re-encode as JPEG ~0.8 before upload:
// receipts stay legible and the request stays small on mobile data.
export const compressImage = async (file) => {
  if (!file.type.startsWith('image/')) {
    throw new Error('El archivo no es una imagen')
  }
  const img = await loadImage(file)
  const scale = Math.min(1, MAX_SIDE / Math.max(img.naturalWidth, img.naturalHeight))
  const width = Math.round(img.naturalWidth * scale)
  const height = Math.round(img.naturalHeight * scale)

  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = '#ffffff' // PNG transparency would turn black in JPEG
  ctx.fillRect(0, 0, width, height)
  ctx.drawImage(img, 0, 0, width, height)

  const dataUrl = canvas.toDataURL('image/jpeg', JPEG_QUALITY)
  return {
    preview: dataUrl,
    media_type: 'image/jpeg',
    data: dataUrl.split(',')[1]
  }
}
