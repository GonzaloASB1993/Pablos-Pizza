import { useEffect } from 'react'
import { motion, useMotionValue, useAnimation, useTransform } from 'framer-motion'
import { Box, useTheme, useMediaQuery } from '@mui/material'

const IMGS = [
  '/images/gallery_rolling/IMG-20250615-WA0018.jpg',
  '/images/gallery_rolling/IMG-20251001-WA0003.jpg',
  '/images/gallery_rolling/IMG-20251001-WA0007.jpg',
  '/images/gallery_rolling/IMG-20251001-WA0011.jpg',
  '/images/gallery_rolling/IMG-20251001-WA0018.jpg',
  '/images/gallery_rolling/IMG-20251001-WA0022.jpg',
  '/images/gallery_rolling/IMG-20251001-WA0027.jpg',
  '/images/gallery_rolling/IMG-20251001-WA0031.jpg',
  '/images/gallery_rolling/IMG-20251001-WA0032.jpg',
  '/images/gallery_rolling/IMG-20251001-WA0033.jpg'
]

const RollingGallery = ({ autoplay = true, pauseOnHover = true, images = [] }) => {
  images = images.length > 0 ? images : IMGS

  const theme = useTheme()
  const isScreenSizeSm = useMediaQuery(theme.breakpoints.down('sm'))

  const cylinderWidth = isScreenSizeSm ? 1500 : 2500
  const faceCount = images.length
  const imageSize = isScreenSizeSm ? 200 : 280  // Tamaño de las imágenes
  const faceWidth = cylinderWidth / faceCount
  const radius = cylinderWidth / (2 * Math.PI)

  const dragFactor = 0.05
  const rotation = useMotionValue(0)
  const controls = useAnimation()

  const transform = useTransform(rotation, val => `rotate3d(0,1,0,${val}deg)`)

  const startInfiniteSpin = startAngle => {
    controls.start({
      rotateY: [startAngle, startAngle - 360],
      transition: {
        duration: 60,
        ease: 'linear',
        repeat: Infinity
      }
    })
  }

  useEffect(() => {
    if (autoplay) {
      const currentAngle = rotation.get()
      startInfiniteSpin(currentAngle)
    } else {
      controls.stop()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoplay])

  const handleUpdate = latest => {
    if (typeof latest.rotateY === 'number') {
      rotation.set(latest.rotateY)
    }
  }

  const handleDrag = (_, info) => {
    controls.stop()
    rotation.set(rotation.get() + info.offset.x * dragFactor)
  }

  const handleDragEnd = (_, info) => {
    const finalAngle = rotation.get() + info.velocity.x * dragFactor
    rotation.set(finalAngle)

    if (autoplay) {
      startInfiniteSpin(finalAngle)
    }
  }

  const handleMouseEnter = () => {
    if (autoplay && pauseOnHover) {
      controls.stop()
    }
  }

  const handleMouseLeave = () => {
    if (autoplay && pauseOnHover) {
      const currentAngle = rotation.get()
      startInfiniteSpin(currentAngle)
    }
  }

  return (
    <Box sx={{ position: 'relative', height: { xs: '350px', sm: '450px', md: '500px' }, width: '100%', overflow: 'hidden' }}>
      {/* Left Gradient */}
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          height: '100%',
          width: '48px',
          zIndex: 10,
          background: 'linear-gradient(to left, rgba(0,0,0,0) 0%, #000000 100%)'
        }}
      />

      {/* Right Gradient */}
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          right: 0,
          height: '100%',
          width: '48px',
          zIndex: 10,
          background: 'linear-gradient(to right, rgba(0,0,0,0) 0%, #000000 100%)'
        }}
      />

      <Box
        sx={{
          display: 'flex',
          height: '100%',
          alignItems: 'center',
          justifyContent: 'center',
          perspective: '1000px',
          transformStyle: 'preserve-3d'
        }}
      >
        <motion.div
          drag="x"
          dragElastic={0}
          onDrag={handleDrag}
          onDragEnd={handleDragEnd}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          animate={controls}
          onUpdate={handleUpdate}
          style={{
            transform: transform,
            rotateY: rotation,
            width: cylinderWidth,
            transformStyle: 'preserve-3d',
            display: 'flex',
            minHeight: '200px',
            cursor: 'grab',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          {images.map((url, i) => (
            <Box
              key={i}
              sx={{
                position: 'absolute',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: `${faceWidth}px`,
                height: 'fit-content',
                backfaceVisibility: 'hidden',
                transform: `rotateY(${(360 / faceCount) * i}deg) translateZ(${radius}px)`,
                '&:hover img': {
                  transform: 'scale(1.05)'
                }
              }}
            >
              <Box
                component="img"
                src={url}
                alt={`Foto de taller de pizza para niños - Pablo's Pizza ${i + 1}`}
                loading="lazy"
                sx={{
                  pointerEvents: 'none',
                  height: { xs: '150px', sm: '260px' },
                  width: { xs: '150px', sm: '260px' },
                  borderRadius: '12px',
                  border: '3px solid white',
                  objectFit: 'cover',
                  objectPosition: 'center',
                  transition: 'transform 0.3s ease-out',
                  boxShadow: '0 8px 30px rgba(0, 0, 0, 0.5)'
                }}
              />
            </Box>
          ))}
        </motion.div>
      </Box>
    </Box>
  )
}

export default RollingGallery
