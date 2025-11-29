import { useState } from 'react'
import { useRef } from 'react'
import { ALL_STYLES, STYLE_CATEGORIES, getStylesByCategory } from '../data/styles'
import { Search, Sparkles, Check, ChevronLeft, ChevronRight } from 'lucide-react'

interface StyleGalleryProps {
  selectedStyle: string
  onSelect: (style: string) => void
}

export default function StyleGallery({ selectedStyle, onSelect }: StyleGalleryProps) {
  const [selectedCategory, setSelectedCategory] = useState('All Styles')
  const [searchQuery, setSearchQuery] = useState('')
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const cardWidth = 220

  // Filter styles by category and search
  const filteredStyles = getStylesByCategory(selectedCategory).filter(style =>
    style.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    style.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const scrollByOffset = (direction: 'left' | 'right') => {
    if (!scrollRef.current) return
    const offset = direction === 'left' ? -cardWidth : cardWidth
    scrollRef.current.scrollBy({ left: offset, behavior: 'smooth' })
  }

  const isCompact = filteredStyles.length > 0 && filteredStyles.length <= 3

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Sparkles className="w-6 h-6 text-primary-500" />
          <div>
            <h3 className="text-xl font-semibold text-gray-900">Choose Visual Style</h3>
            <p className="text-sm text-gray-600">Select from {ALL_STYLES.length} professional styles</p>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search styles..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-12 pr-4 py-3 rounded-desktop border border-gray-300 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 outline-none transition-all"
        />
      </div>

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-2">
        {STYLE_CATEGORIES.map(category => (
          <button
            key={category}
            onClick={() => setSelectedCategory(category)}
            className={`px-4 py-2 rounded-desktop text-sm font-medium transition-all ${
              selectedCategory === category
                ? 'bg-primary-500 text-white shadow-md'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {category}
          </button>
        ))}
      </div>

      {/* Style Grid */}
      <div className="relative">
        {!isCompact && (
          <>
            <button
              type="button"
              aria-label="Scroll styles left"
              onClick={() => scrollByOffset('left')}
              className="hidden sm:flex absolute left-0 top-1/2 z-10 -translate-y-1/2 rounded-full bg-white shadow-md hover:bg-white/90"
            >
              <ChevronLeft className="w-5 h-5 text-gray-700" />
            </button>
            <button
              type="button"
              aria-label="Scroll styles right"
              onClick={() => scrollByOffset('right')}
              className="hidden sm:flex absolute right-0 top-1/2 z-10 -translate-y-1/2 rounded-full bg-white shadow-md hover:bg-white/90"
            >
              <ChevronRight className="w-5 h-5 text-gray-700" />
            </button>
            <div className="pointer-events-none absolute inset-y-0 left-0 w-12 bg-gradient-to-r from-white to-transparent" />
            <div className="pointer-events-none absolute inset-y-0 right-0 w-12 bg-gradient-to-l from-white to-transparent" />
          </>
        )}
        <div
          ref={scrollRef}
          className={
            isCompact
              ? 'flex flex-wrap justify-center gap-4 pb-4'
              : 'flex gap-4 overflow-x-auto pb-4 snap-x snap-mandatory scroll-smooth'
          }
        >
        {filteredStyles.map(style => (
          <button
            key={style.id}
            onClick={() => onSelect(style.normalizedName)}
            className={`group relative rounded-desktop overflow-hidden border-2 transition-all duration-300 ${
              isCompact ? 'w-[220px]' : 'min-w-[200px] snap-center'
            } ${
              selectedStyle === style.normalizedName
                ? 'border-primary-500 ring-4 ring-primary-500/30 scale-105'
                : 'border-gray-200 hover:border-primary-300 hover:scale-102'
            }`}
          >
            {/* Preview Image */}
            <div className="aspect-square relative overflow-hidden bg-gray-100">
              <img
                src={style.previewImage}
                alt={style.name}
                className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                loading="lazy"
                onError={(e) => {
                  // Fallback if image doesn't load
                  e.currentTarget.src = `data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect fill="%23f3f4f6" width="200" height="200"/><text x="50%" y="50%" fill="%236b7280" font-size="48" text-anchor="middle" dy=".3em">${style.icon}</text></svg>`
                }}
              />
              
              {/* Selected Indicator */}
              {selectedStyle === style.normalizedName && (
                <div className="absolute inset-0 bg-primary-500/20 flex items-center justify-center">
                  <div className="bg-primary-500 text-white rounded-full p-2">
                    <Check className="w-6 h-6" />
                  </div>
                </div>
              )}

              {/* Hover Overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                <div className="absolute bottom-0 left-0 right-0 p-3">
                  <p className="text-white text-xs line-clamp-2">
                    {style.description}
                  </p>
                </div>
              </div>
            </div>

            {/* Style Name */}
            <div className="p-3 bg-white">
              <div className="flex items-center gap-2">
                <span className="text-xl">{style.icon}</span>
                <span className={`text-sm font-medium truncate ${
                  selectedStyle === style.normalizedName ? 'text-primary-600' : 'text-gray-900'
                }`}>
                  {style.name}
                </span>
              </div>
            </div>
          </button>
        ))}
        </div>
      </div>

      {/* No Results */}
      {filteredStyles.length === 0 && (
        <div className="text-center py-16">
          <Sparkles className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">No styles found matching "{searchQuery}"</p>
          <button
            onClick={() => setSearchQuery('')}
            className="mt-4 text-primary-500 hover:text-primary-600 font-medium"
          >
            Clear search
          </button>
        </div>
      )}

      {/* Stats */}
      <div className="text-center text-sm text-gray-500">
        Showing {filteredStyles.length} of {ALL_STYLES.length} styles
      </div>
    </div>
  )
}

