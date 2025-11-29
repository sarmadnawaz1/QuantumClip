interface LogoProps {
  size?: number
  showWordmark?: boolean
}

export default function Logo({ size = 44, showWordmark = true }: LogoProps) {
  const src = '/logo.png'
  return (
    <div className="flex items-center gap-3">
      <img
        src={src}
        alt="QuantumClip"
        onError={(event) => {
          const target = event.currentTarget
          target.style.display = 'none'
          const fallback = target.nextElementSibling as HTMLDivElement | null
          if (fallback) fallback.style.display = 'flex'
        }}
        style={{ width: size, height: size, borderRadius: size * 0.22, objectFit: 'cover' }}
        className="shadow-lg shadow-indigo-900/40" 
      />
      <div
        style={{ width: size, height: size, borderRadius: size * 0.22, display: 'none' }}
        className="flex items-center justify-center bg-gradient-to-br from-[#4287ff] via-[#6241ff] to-[#9f3cff] text-white shadow-lg shadow-indigo-500/30"
      >
        <span className="text-lg font-semibold">QC</span>
      </div>
      {showWordmark && (
        <div className="leading-tight">
          <p className="text-lg font-semibold tracking-tight text-white">QuantumClip</p>
          <p className="text-xs font-medium uppercase text-indigo-200">AI Video Engine</p>
        </div>
      )}
    </div>
  )
}
