import { useEffect, useRef, type CSSProperties } from 'react'

const FLOAT_IMAGES: { src: string; alt: string; style: CSSProperties }[] = [
  {
    src: 'https://cdn-icons-png.flaticon.com/512/4712/4712104.png',
    alt: 'AI brain',
    style: { top: '15%', left: '8%', animationDelay: '0s' },
  },
  {
    src: 'https://cdn-icons-png.flaticon.com/512/4712/4712100.png',
    alt: 'Neural network',
    style: { top: '38%', right: '12%', animationDelay: '2s' },
  },
  {
    src: 'https://cdn-icons-png.flaticon.com/512/4712/4712105.png',
    alt: 'Data flow',
    style: { bottom: '18%', left: '22%', animationDelay: '4s' },
  },
  {
    src: 'https://cdn-icons-png.flaticon.com/512/4712/4712108.png',
    alt: 'AI circuit',
    style: { bottom: '20%', right: '8%', animationDelay: '6s' },
  },
]

interface AppBackgroundProps {
  showFloatingIcons?: boolean
  intensity?: number
}

export default function AppBackground({ showFloatingIcons = false, intensity = 1 }: AppBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const styleId = 'qc-float-keyframes'
    if (!document.getElementById(styleId)) {
      const style = document.createElement('style')
      style.id = styleId
      style.innerHTML = `@keyframes qcFloat {0%,100%{transform:translateY(0) rotate(0deg);opacity:0.8;}50%{transform:translateY(-40px) rotate(10deg);opacity:1;}}`
      document.head.appendChild(style)
    }

    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const clampedIntensity = Math.max(0, Math.min(intensity, 1))

    const CONFIG = {
      PARTICLE_COUNT: Math.max(12, Math.round(90 * (0.3 + 0.7 * clampedIntensity))),
      MAX_DISTANCE: 180 * (0.5 + 0.5 * clampedIntensity),
      NODE_SIZE: 1.6 * (0.6 + 0.4 * clampedIntensity),
      SPEED: 0.3 * (0.4 + 0.6 * clampedIntensity),
      LINE_OPACITY: 0.18 * (0.4 + 0.6 * clampedIntensity),
      ENABLE_MOTION: clampedIntensity > 0,
      THEME: {
        primary: [97, 218, 251] as [number, number, number],
        secondary: [175, 103, 255] as [number, number, number],
      },
    }

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      CONFIG.ENABLE_MOTION = false
    }

    let dpr = Math.max(1, window.devicePixelRatio || 1)
    let width = window.innerWidth
    let height = window.innerHeight

    const resize = () => {
      dpr = Math.max(1, window.devicePixelRatio || 1)
      width = window.innerWidth
      height = window.innerHeight
      canvas.width = width * dpr
      canvas.height = height * dpr
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    resize()
    window.addEventListener('resize', resize)

    const lerp = (a: number, b: number, t: number) => a + (b - a) * t

    class Node {
      x = 0
      y = 0
      vx = 0
      vy = 0
      size = 0
      h = Math.random()
      life = 0
      age = 0

      constructor() {
        this.reset(true)
      }

      reset(force: boolean) {
        this.x = Math.random() * width
        this.y = Math.random() * height
        const ang = Math.random() * Math.PI * 2
        const sp = (0.1 + Math.random() * 0.9) * CONFIG.SPEED
        this.vx = Math.cos(ang) * sp
        this.vy = Math.sin(ang) * sp
        this.size = CONFIG.NODE_SIZE * (0.7 + Math.random() * 1.4)
        this.h = Math.random()
        this.life = (3000 + Math.random() * 3000) * (0.6 + 0.4 * clampedIntensity)
        this.age = force ? Math.random() * this.life : 0
      }

      step(dt: number) {
        if (!CONFIG.ENABLE_MOTION) return
        this.x += this.vx * dt
        this.y += this.vy * dt
        this.age += dt * 1000
        if (this.x < -50) this.x = width + 50
        if (this.x > width + 50) this.x = -50
        if (this.y < -50) this.y = height + 50
        if (this.y > height + 50) this.y = -50
        if (this.age > this.life) this.reset(false)
      }
    }

    let nodes: Node[] = []
    const initParticles = () => {
      nodes = []
      for (let i = 0; i < CONFIG.PARTICLE_COUNT; i++) {
        nodes.push(new Node())
      }
    }

    initParticles()

    let animationId = 0
    let last = performance.now()

    const loop = (now: number) => {
      const dt = Math.min(0.04, (now - last) / 1000)
      last = now

      ctx.fillStyle = 'rgba(5,7,25,1)'
      ctx.fillRect(0, 0, width, height)

      nodes.forEach((node) => node.step(dt))

      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i]
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j]
          const dx = a.x - b.x
          const dy = a.y - b.y
          const distSq = dx * dx + dy * dy
          if (distSq < CONFIG.MAX_DISTANCE * CONFIG.MAX_DISTANCE) {
            const t = 1 - Math.sqrt(distSq) / CONFIG.MAX_DISTANCE
            const alpha = t * CONFIG.LINE_OPACITY
            const r = Math.floor(lerp(CONFIG.THEME.primary[0], CONFIG.THEME.secondary[0], t))
            const g = Math.floor(lerp(CONFIG.THEME.primary[1], CONFIG.THEME.secondary[1], t))
            const bcol = Math.floor(lerp(CONFIG.THEME.primary[2], CONFIG.THEME.secondary[2], t))
            ctx.strokeStyle = `rgba(${r},${g},${bcol},${alpha})`
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            ctx.stroke()
          }
        }
      }

      ctx.globalCompositeOperation = 'lighter'
      for (const node of nodes) {
        const pulse = 0.6 + 0.4 * Math.sin(now * 0.002 + node.h * 30)
        const r = Math.floor(lerp(CONFIG.THEME.primary[0], CONFIG.THEME.secondary[0], node.h))
        const g = Math.floor(lerp(CONFIG.THEME.primary[1], CONFIG.THEME.secondary[1], node.h))
        const bcol = Math.floor(lerp(CONFIG.THEME.primary[2], CONFIG.THEME.secondary[2], node.h))
        const size = node.size * (1 + 0.6 * pulse)
        ctx.fillStyle = `rgba(${r},${g},${bcol},0.75)`
        ctx.beginPath()
        ctx.arc(node.x, node.y, size, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.globalCompositeOperation = 'source-over'

      animationId = requestAnimationFrame(loop)
    }

    animationId = requestAnimationFrame(loop)

    return () => {
      window.removeEventListener('resize', resize)
      cancelAnimationFrame(animationId)
    }
  }, [intensity])

  const clampedIntensity = Math.max(0, Math.min(intensity, 1))
  const iconScale = 0.6 + 0.4 * clampedIntensity
  const iconOpacity = 0.2 + 0.3 * clampedIntensity

  return (
    <>
      <canvas
        ref={canvasRef}
        className="fixed inset-0 -z-10 h-full w-full"
        style={{ background: 'linear-gradient(180deg,#05071a 0%, #071033 50%, #031022 100%)' }}
      />
      {showFloatingIcons && clampedIntensity > 0 && (
        <div className="pointer-events-none absolute inset-0 -z-[5]">
          {FLOAT_IMAGES.map((img) => (
            <img
              key={img.src}
              src={img.src}
              alt={img.alt}
              style={{
                position: 'absolute',
                width: `${96 * iconScale}px`,
                opacity: iconOpacity,
                filter: 'drop-shadow(0 12px 24px rgba(30, 60, 130, 0.2)) saturate(0.75)',
                animation: `qcFloat ${12 / (0.6 + 0.4 * clampedIntensity)}s ease-in-out infinite`,
                ...img.style,
              }}
            />
          ))}
        </div>
      )}
    </>
  )
}
