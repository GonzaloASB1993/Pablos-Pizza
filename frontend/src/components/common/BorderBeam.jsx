import React from 'react'
import { motion } from 'framer-motion'

/**
 * BorderBeam Component - Animated border beam effect from Magic UI
 * An animated beam of light which travels along the border of its container
 *
 * @param {Object} props
 * @param {string} props.className - Additional CSS classes
 * @param {number} props.size - Size of the beam in pixels (default: 200)
 * @param {number} props.duration - Animation duration in seconds (default: 15)
 * @param {number} props.delay - Animation delay in seconds (default: 0)
 * @param {string} props.colorFrom - Start color of the beam gradient (default: #ffaa40)
 * @param {string} props.colorTo - End color of the beam gradient (default: #9c40ff)
 * @param {number} props.borderWidth - Width of the border (default: 1.5)
 * @param {boolean} props.reverse - Whether to reverse animation direction (default: false)
 * @param {number} props.initialOffset - Initial offset position 0-100 (default: 0)
 */
export default function BorderBeam({
  className = '',
  size = 200,
  duration = 15,
  delay = 0,
  colorFrom = '#ffaa40',
  colorTo = '#9c40ff',
  borderWidth = 1.5,
  reverse = false,
  initialOffset = 0,
  style = {}
}) {
  return (
    <div
      className={`pointer-events-none absolute inset-0 rounded-[inherit] ${className}`}
      style={{
        border: `${borderWidth}px solid transparent`,
        borderRadius: 'inherit',
        maskImage: 'linear-gradient(transparent, transparent), linear-gradient(#000, #000)',
        maskComposite: 'intersect',
        maskClip: 'padding-box, border-box',
        WebkitMaskImage: 'linear-gradient(transparent, transparent), linear-gradient(#000, #000)',
        WebkitMaskComposite: 'xor',
        WebkitMaskClip: 'padding-box, border-box'
      }}
    >
      <motion.div
        style={{
          width: size,
          aspectRatio: '1',
          background: `linear-gradient(to left, ${colorFrom}, ${colorTo}, transparent)`,
          offsetPath: `rect(0 auto auto 0 round ${size}px)`,
          position: 'absolute',
          ...style
        }}
        initial={{ offsetDistance: `${initialOffset}%` }}
        animate={{
          offsetDistance: reverse
            ? [`${100 - initialOffset}%`, `${-initialOffset}%`]
            : [`${initialOffset}%`, `${100 + initialOffset}%`]
        }}
        transition={{
          repeat: Infinity,
          ease: 'linear',
          duration: duration,
          delay: -delay
        }}
      />
    </div>
  )
}
