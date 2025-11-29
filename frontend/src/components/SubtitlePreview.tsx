import { useState, useEffect, memo } from 'react'
import { Type, Eye, EyeOff, ChevronDown } from 'lucide-react'

interface SubtitlePreviewProps {
  text: string
  position?: 'top' | 'center' | 'bottom'
  fontSize?: number
  textColor?: string
  bgOpacity?: number
  outlineWidth?: number
  font?: string
  orientation?: 'portrait' | 'landscape'
  enabled?: boolean
  onToggleEnabled?: (enabled: boolean) => void
  onChange?: (style: {
    position: 'top' | 'center' | 'bottom'
    font_size: number
    text_color: [number, number, number]
    bg_opacity: number
    outline_width: number
    enabled?: boolean
  }) => void
}

function SubtitlePreview({
  text = "This is how your subtitles will look on the video",
  position = 'bottom',
  fontSize = 60,
  textColor = '#FFFFFF',
  bgOpacity = 180,
  outlineWidth = 3,
  font = '',
  orientation = 'portrait',
  enabled = true,
  onToggleEnabled,
  onChange
}: SubtitlePreviewProps) {
  const [showPreview, setShowPreview] = useState(true)
  const [showSettings, setShowSettings] = useState(false)
  const [subtitlesEnabled, setSubtitlesEnabled] = useState(enabled)

  // Local state for customization
  const [localPosition, setLocalPosition] = useState(position)
  const [localFontSize, setLocalFontSize] = useState(fontSize)
  const [localTextColor, setLocalTextColor] = useState(textColor)
  const [localBgOpacity, setLocalBgOpacity] = useState(bgOpacity)
  const [localOutlineWidth, setLocalOutlineWidth] = useState(outlineWidth)

  useEffect(() => {
    setLocalPosition(position)
    setLocalFontSize(fontSize)
    setLocalTextColor(textColor)
    setLocalBgOpacity(bgOpacity)
    setLocalOutlineWidth(outlineWidth)
  }, [position, fontSize, textColor, bgOpacity, outlineWidth])

  useEffect(() => {
    setSubtitlesEnabled(enabled)
  }, [enabled])

  useEffect(() => {
    if (!onChange) return

    const rgb: [number, number, number] = localTextColor.startsWith('#')
      ? [
        parseInt(localTextColor.slice(1, 3), 16),
        parseInt(localTextColor.slice(3, 5), 16),
        parseInt(localTextColor.slice(5, 7), 16)
      ]
      : localTextColor
        .replace('rgb(', '')
        .replace(')', '')
        .split(',')
        .map(v => parseInt(v.trim())) as [number, number, number]

    onChange({
      position: localPosition,
      font_size: localFontSize,
      text_color: rgb,
      bg_opacity: localBgOpacity,
      outline_width: localOutlineWidth,
      enabled: subtitlesEnabled
    })
  }, [localPosition, localFontSize, localTextColor, localBgOpacity, localOutlineWidth, subtitlesEnabled, onChange])

  // Calculate preview dimensions based on orientation
  const previewWidth = orientation === 'portrait' ? 360 : 640

  // Calculate font size for preview (scaled down)
  const scaledFontSize = localFontSize * (previewWidth / 1080)

  // Calculate position styles
  const getPositionStyles = () => {
    const baseStyles = {
      position: 'absolute' as const,
      left: '20px',
      right: '20px',
      padding: '15px 20px',
      backgroundColor: `rgba(0, 0, 0, ${localBgOpacity / 255})`,
      color: localTextColor,
      fontSize: `${scaledFontSize}px`,
      fontWeight: 700,
      textAlign: 'center' as const,
      textShadow: `
        ${-localOutlineWidth}px ${-localOutlineWidth}px 0 #000,
        ${localOutlineWidth}px ${-localOutlineWidth}px 0 #000,
        ${-localOutlineWidth}px ${localOutlineWidth}px 0 #000,
        ${localOutlineWidth}px ${localOutlineWidth}px 0 #000
      `,
      borderRadius: '8px',
      fontFamily: font ? font.replace('.ttf', '') : 'system-ui, -apple-system, sans-serif',
      lineHeight: 1.4,
      wordWrap: 'break-word' as const,
      overflowWrap: 'break-word' as const,
    }

    if (localPosition === 'top') {
      return { ...baseStyles, top: '20px' }
    } else if (localPosition === 'center') {
      return { ...baseStyles, top: '50%', transform: 'translateY(-50%)' }
    } else {
      return { ...baseStyles, bottom: '20px' }
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Eye className="w-5 h-5 text-indigo-300" />
          <h3 className="text-sm font-semibold text-white uppercase tracking-wide">Subtitle Preview</h3>
        </div>
        <div className="flex gap-2 flex-wrap">
          <label className="glass-chip flex items-center gap-2 cursor-pointer text-xs text-white/70">
            <input
              type="checkbox"
              checked={subtitlesEnabled}
              onChange={(e) => {
                const next = e.target.checked
                setSubtitlesEnabled(next)
                onToggleEnabled?.(next)
              }}
              className="rounded border-white/30 text-indigo-300 focus:ring-indigo-300"
            />
            Show
          </label>
          <button
            type="button"
            onClick={() => setShowSettings(!showSettings)}
            className="glass-chip text-xs flex items-center gap-1"
          >
            <Type className="w-4 h-4" />
            {showSettings ? 'Close' : 'Customize'}
            <ChevronDown className={`w-4 h-4 transition-transform ${showSettings ? 'rotate-180' : ''}`} />
          </button>
          <button
            type="button"
            onClick={() => setShowPreview(!showPreview)}
            className="glass-chip text-xs flex items-center gap-1"
          >
            {showPreview ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            {showPreview ? 'Hide' : 'Show'}
          </button>
        </div>
      </div>

      {/* Customization Settings */}
      {showSettings && showPreview && subtitlesEnabled && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-white/5 rounded-xl border border-white/10 text-xs">
          <div>
            <label className="block font-semibold text-white/80 mb-2">Position</label>
            <select
              value={localPosition}
              onChange={(e) => setLocalPosition(e.target.value as any)}
              className="glass-field w-full text-xs"
            >
              <option value="top">Top</option>
              <option value="center">Center</option>
              <option value="bottom">Bottom</option>
            </select>
          </div>

          <div>
            <label className="block font-semibold text-white/80 mb-2">Font Size: {localFontSize}px</label>
            <input
              type="range"
              min="30"
              max="120"
              value={localFontSize}
              onChange={(e) => setLocalFontSize(parseInt(e.target.value))}
              className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-indigo-300"
            />
          </div>

          <div>
            <label className="block font-semibold text-white/80 mb-2">Text Color</label>
            <div className="flex gap-2">
              <input
                type="color"
                value={localTextColor}
                onChange={(e) => setLocalTextColor(e.target.value)}
                className="w-12 h-10 border-2 border-white/30 rounded-lg cursor-pointer"
              />
              <input
                type="text"
                value={localTextColor}
                onChange={(e) => setLocalTextColor(e.target.value)}
                className="flex-1 px-3 py-2 glass-field text-xs font-mono"
                placeholder="#FFFFFF"
              />
            </div>
          </div>

          <div>
            <label className="block font-semibold text-white/80 mb-2">Background Opacity: {Math.round((localBgOpacity / 255) * 100)}%</label>
            <input
              type="range"
              min="0"
              max="255"
              value={localBgOpacity}
              onChange={(e) => setLocalBgOpacity(parseInt(e.target.value))}
              className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-indigo-300"
            />
          </div>

          <div>
            <label className="block font-semibold text-white/80 mb-2">Outline Width: {localOutlineWidth}px</label>
            <input
              type="range"
              min="0"
              max="8"
              value={localOutlineWidth}
              onChange={(e) => setLocalOutlineWidth(parseInt(e.target.value))}
              className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-indigo-300"
            />
          </div>

          <p className="md:col-span-2 text-[11px] text-white/55 italic">
            Fine-tune subtitles for readability and brand alignment.
          </p>
        </div>
      )}

      {/* Preview Container */}
      {showPreview && subtitlesEnabled && (
        <div className="relative">
          {/* Preview Frame */}
          <div
            className="relative mx-auto rounded-2xl overflow-hidden shadow-[0_20px_40px_rgba(8,12,35,0.55)] border border-white/10"
            style={{
              width: orientation === 'portrait' ? 220 : 280,
              height: orientation === 'portrait' ? 360 : 200,
              background: 'linear-gradient(145deg, rgba(20,32,80,0.9), rgba(10,16,48,0.85))'
            }}
          >
            {/* Overlay gradient for better text visibility */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/45 to-transparent" />

            {/* Subtitle */}
            <div style={getPositionStyles()}>
              {text || "Your subtitle text will appear here"}
            </div>

            {/* Orientation indicator */}
            <div className="absolute top-2 left-2 px-2 py-1 bg-white/10 text-white text-[10px] rounded-full uppercase tracking-wide">
              {orientation === 'portrait' ? '📱 Portrait (9:16)' : '🖥️ Landscape (16:9)'}
            </div>
          </div>

          {/* Info text */}
          <p className="text-center text-xs text-white/55 mt-3">
            Preview of baked-in subtitles in the final render
          </p>
        </div>
      )}

      {/* Export Settings Info */}
      {!subtitlesEnabled && (
        <div className="p-4 bg-white/5 border border-white/10 rounded-lg text-xs text-white/65">
          Subtitles are turned off for this video. Enable the checkbox above to customize and preview subtitles.
        </div>
      )}
    </div>
  )
}

export default memo(SubtitlePreview)

