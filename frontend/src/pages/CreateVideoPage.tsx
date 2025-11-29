import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Settings as SettingsIcon, Video, Music, Type, Wand2, Sparkles, Mic, Image as ImageIcon, Heart, Star } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../services/api'
import StyleGallery from '../components/StyleGallery'

interface VideoForm {
  title: string
  description?: string
  script: string
  style: string
  image_service?: string
  image_model?: string
  resolution: string
  orientation: string
  tts_provider?: string
  tts_voice?: string
  tts_model?: string
  backgroundMusic?: string
  videoOverlay?: string
  font?: string
  customInstructions?: string
  transition_type?: string
  transition_duration?: number
  image_animation?: string
  image_animation_intensity?: number
  rendering_preset?: string
  ai_provider?: string
  ai_model?: string
  target_scene_count?: number
  subtitle_style?: {
    enabled?: boolean
    font_size?: number
    position?: string
    text_color?: string
    bg_opacity?: number
    outline_width?: number
  }
}

type StepId =
  | 'script'
  | 'style'
  | 'video'
  | 'tts'
  | 'subtitles'
  | 'advanced'
  | 'review'

interface WizardStep {
  id: StepId
  title: string
  description: string
  required: boolean
}

const WIZARD_STEPS: WizardStep[] = [
  { id: 'script', title: 'Script & Story', description: 'Write your narrative and scenes', required: true },
  { id: 'style', title: 'Visual Style & Image', description: 'Pick style and AI image provider', required: true },
  { id: 'video', title: 'Video Settings', description: 'Resolution & orientation', required: true },
  { id: 'tts', title: 'Voice & Audio', description: 'Choose voice, music & overlays', required: true },
  { id: 'subtitles', title: 'Subtitles', description: 'Customize caption styling', required: false },
  { id: 'advanced', title: 'Advanced', description: 'Fine-tune extra instructions', required: false },
  { id: 'review', title: 'Review & Create', description: 'Double-check everything', required: true }
]

export default function CreateVideoPage() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [showStyleGallery, setShowStyleGallery] = useState(false)
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  
  // Form state
  const [formData, setFormData] = useState<VideoForm>({
    title: '',
    description: '',
    script: '',
    style: 'cinematic',
    image_service: 'pollination',
    image_model: '',
    resolution: '1080p',
    orientation: 'portrait',
    tts_provider: 'edge',
    tts_voice: '',
    tts_model: '',
    backgroundMusic: '',
    videoOverlay: '',
    font: '',
    customInstructions: '',
    transition_type: 'none',
    transition_duration: 0.5,
    image_animation: 'none',
    image_animation_intensity: 1.2,
    rendering_preset: 'fast',
    ai_provider: 'groq',
    ai_model: '',
    target_scene_count: undefined,
    subtitle_style: {
      enabled: true,
      font_size: 60,
      position: 'bottom',
      text_color: '#FFFFFF',
      bg_opacity: 180,
      outline_width: 3
    }
  })

  // Available options
  const [musicFiles, setMusicFiles] = useState<string[]>([])
  const [overlayFiles, setOverlayFiles] = useState<string[]>([])
  const [fonts, setFonts] = useState<string[]>([])
  const [ttsServices, setTtsServices] = useState<Record<string, any>>({})
  const [imageServices, setImageServices] = useState<Record<string, any>>({})
  const [previewingVoice, setPreviewingVoice] = useState<string | null>(null)
  const [favoriteVoices, setFavoriteVoices] = useState<Array<{provider: string, voice_id: string, voice_label: string}>>([])
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null)
  const [transitions, setTransitions] = useState<Array<{id: string, name: string, description: string}>>([])
  const [transitionPreviewUrl, setTransitionPreviewUrl] = useState<string | null>(null)

  // Load available options
  useEffect(() => {
    loadOptions()
    loadFavoriteVoices()
  }, [])

  // Reload TTS services (with voices) when provider changes or if voices are missing
  useEffect(() => {
    const reloadTtsServices = async () => {
      if (!formData.tts_provider) return
      
      const currentService = ttsServices[formData.tts_provider]
      // If service exists but has no voices, reload it
      if (currentService && (!currentService.voices || currentService.voices.length === 0)) {
        try {
          const ttsRes = await api.get('/settings/tts-services/options')
          setTtsServices(ttsRes.data || {})
        } catch (error) {
          console.error('Failed to reload TTS services:', error)
        }
      }
    }
    
    reloadTtsServices()
  }, [formData.tts_provider])

  const loadFavoriteVoices = async () => {
    try {
      const response = await api.get('/settings/tts-voices/favorites')
      setFavoriteVoices(response.data.favorites || [])
    } catch (error) {
      console.error('Failed to load favorite voices:', error)
      // Fallback to localStorage
      const stored = localStorage.getItem('favorite_voices')
      if (stored) {
        try {
          setFavoriteVoices(JSON.parse(stored))
        } catch (e) {
          console.error('Failed to parse stored favorites:', e)
        }
      }
    }
  }

  const toggleFavorite = async (provider: string, voiceId: string, voiceLabel: string) => {
    const isFavorite = favoriteVoices.some(fav => fav.provider === provider && fav.voice_id === voiceId)
    
    try {
      if (isFavorite) {
        // Remove from favorites
        await api.delete(`/settings/tts-voices/favorites?provider=${encodeURIComponent(provider)}&voice_id=${encodeURIComponent(voiceId)}`)
        setFavoriteVoices(prev => prev.filter(fav => !(fav.provider === provider && fav.voice_id === voiceId)))
        toast.success('Removed from favorites')
      } else {
        // Add to favorites
        await api.post(`/settings/tts-voices/favorites?provider=${encodeURIComponent(provider)}&voice_id=${encodeURIComponent(voiceId)}&voice_label=${encodeURIComponent(voiceLabel)}`)
        setFavoriteVoices(prev => [...prev, { provider, voice_id: voiceId, voice_label: voiceLabel }])
        toast.success('Added to favorites')
      }
      // Also save to localStorage as backup
      const updated = isFavorite 
        ? favoriteVoices.filter(fav => !(fav.provider === provider && fav.voice_id === voiceId))
        : [...favoriteVoices, { provider, voice_id: voiceId, voice_label: voiceLabel }]
      localStorage.setItem('favorite_voices', JSON.stringify(updated))
    } catch (error: any) {
      console.error('Failed to update favorites:', error)
      // Fallback to localStorage only
      const updated = isFavorite 
        ? favoriteVoices.filter(fav => !(fav.provider === provider && fav.voice_id === voiceId))
        : [...favoriteVoices, { provider, voice_id: voiceId, voice_label: voiceLabel }]
      setFavoriteVoices(updated)
      localStorage.setItem('favorite_voices', JSON.stringify(updated))
      toast.success(isFavorite ? 'Removed from favorites' : 'Added to favorites')
    }
  }

  const loadOptions = async () => {
    try {
      const [musicRes, overlayRes, fontRes, ttsRes, imageRes, transitionsRes] = await Promise.all([
        api.get('/settings/music'),
        api.get('/settings/overlays'),
        api.get('/settings/fonts'),
        api.get('/settings/tts-services/options'),
        api.get('/settings/image-services/options'),
        api.get('/settings/transitions')
      ])
      setMusicFiles(musicRes.data.music || [])
      setOverlayFiles(overlayRes.data.overlays || [])
      setFonts(fontRes.data.fonts || [])
      // TTS services is returned as an object with keys like 'edge', 'elevenlabs', 'fish'
      setTtsServices(ttsRes.data || {})
      // Image services is returned as an object with keys like 'pollination', 'runware', etc.
      setImageServices(imageRes.data || {})
      // Transitions
      setTransitions(transitionsRes.data.transitions || [])
    } catch (error) {
      console.error('Failed to load options:', error)
    }
  }


  const generateTransitionPreview = async () => {
    if (!formData.transition_type || formData.transition_type === 'none' || formData.transition_type === 'mix') {
      toast.error('Please select a specific transition to preview')
      return
    }
    
    try {
      const params = new URLSearchParams({
        transition_type: formData.transition_type,
        duration: String(formData.transition_duration || 0.5),
        width: '1080',
        height: '1920'
      })
      
      const response = await api.get(`/settings/transition/preview?${params.toString()}`, {
        responseType: 'blob'
      })
      
      const blob = new Blob([response.data], { type: 'image/gif' })
      const url = URL.createObjectURL(blob)
      setTransitionPreviewUrl(url)
    } catch (error: any) {
      console.error('Failed to generate transition preview:', error)
      toast.error(error.response?.data?.detail || 'Failed to generate transition preview')
    }
  }

  const previewVoice = async (provider: string, voiceId: string, modelId?: string) => {
    const previewKey = `${provider}-${voiceId}`
    
    // Stop current audio if playing
    if (currentAudio) {
      currentAudio.pause()
      currentAudio.currentTime = 0
      currentAudio.src = ''
      setCurrentAudio(null)
    }
    
    if (previewingVoice === previewKey) {
      setPreviewingVoice(null)
      return
    }

    setPreviewingVoice(previewKey)
    let blobUrl: string | null = null
    let timeout: ReturnType<typeof setTimeout> | null = null
    
    try {
      // Build the preview URL - backend now returns the file directly
      const params = new URLSearchParams({
        provider,
        voice_id: voiceId,
        ...(modelId && { model_id: modelId })
      })
      
      // Get auth token for the request
      let authToken = ''
      try {
        const storageItem = localStorage.getItem('auth-storage')
        if (storageItem) {
          const { state } = JSON.parse(storageItem)
          if (state && state.token) {
            authToken = state.token
          }
        }
      } catch (e) {
        console.error('Failed to get auth token:', e)
      }
      
      // Use fetch to get the audio blob with authentication
      const previewUrl = `/api/v1/settings/tts-services/preview?${params.toString()}`
      
      // Fetch the audio with authentication
      const response = await fetch(previewUrl, {
        headers: authToken ? {
          'Authorization': `Bearer ${authToken}`
        } : {},
        credentials: 'include'
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
      }
      
      // Create blob URL from the response
      const audioBlob = await response.blob()
      blobUrl = URL.createObjectURL(audioBlob)
      
      // Create audio element and set up event handlers before loading
      const audio = new Audio(blobUrl)
      setCurrentAudio(audio)
      
      // Set up event handlers
      audio.onloadeddata = () => {
        if (timeout) clearTimeout(timeout)
        // Audio is ready to play
        audio.play().catch((playError) => {
          console.error('Audio play error:', playError)
          if (blobUrl) URL.revokeObjectURL(blobUrl)
          setPreviewingVoice(null)
          setCurrentAudio(null)
          toast.error('Failed to play voice preview. Your browser may be blocking autoplay.')
        })
      }
      
      audio.onended = () => {
        if (timeout) clearTimeout(timeout)
        // Clean up blob URL
        if (blobUrl) URL.revokeObjectURL(blobUrl)
        setPreviewingVoice(null)
        setCurrentAudio(null)
      }
      
      audio.onerror = (error) => {
        if (timeout) clearTimeout(timeout)
        // Clean up blob URL
        if (blobUrl) URL.revokeObjectURL(blobUrl)
        console.error('Audio error:', error, 'URL:', previewUrl, 'Error details:', audio.error)
        setPreviewingVoice(null)
        setCurrentAudio(null)
        // Try to get more specific error info
        if (audio.error) {
          const errorCode = audio.error.code
          const errorMessages: Record<number, string> = {
            1: 'Media aborted',
            2: 'Network error - preview may not be available for this voice',
            3: 'Decode error - audio format issue',
            4: 'Source not supported'
          }
          const errorMsg = errorMessages[errorCode] || `Error code: ${errorCode}`
          toast.error(`Preview failed: ${errorMsg}`)
        } else {
          toast.error('Failed to load voice preview. This voice may not be available or the preview generation failed.')
        }
      }
      
      // Set timeout
      timeout = setTimeout(() => {
        if (previewingVoice === previewKey) {
          if (blobUrl) URL.revokeObjectURL(blobUrl)
          setPreviewingVoice(null)
          setCurrentAudio(null)
          toast.error('Preview generation timed out. This voice may not be available.')
        }
      }, 30000)
      
      // Start loading and playing
      audio.load()
      
    } catch (error: any) {
      if (timeout) clearTimeout(timeout)
      if (blobUrl) URL.revokeObjectURL(blobUrl)
      console.error('Preview error:', error)
      setPreviewingVoice(null)
      setCurrentAudio(null)
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to generate voice preview'
      toast.error(errorMsg)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!isFinalStep) {
      handleNextStep()
      return
    }
    
    if (!formData.title || !formData.script) {
      toast.error('Please fill in title and script')
      setCurrentStepIndex(0)
      return
    }

    setIsLoading(true)
    try {
      // Map frontend camelCase to backend snake_case
      const videoData: any = {
        title: formData.title,
        description: formData.description,
        script: formData.script,
        style: formData.style,
        ai_provider: formData.ai_provider || 'groq',
        ai_model: formData.ai_model || undefined,
        image_service: formData.image_service || 'pollination',
        image_model: formData.image_model || undefined,
        custom_instructions: formData.customInstructions || undefined,  // Map camelCase to snake_case
        tts_provider: formData.tts_provider || 'edge',
        tts_voice: formData.tts_voice || undefined,
        tts_model: formData.tts_model || undefined,
        resolution: formData.resolution,
        orientation: formData.orientation,
        fps: formData.fps,
        background_music: formData.backgroundMusic || undefined,  // Map camelCase to snake_case
        video_overlay: formData.videoOverlay || undefined,  // Map camelCase to snake_case
        font: formData.font || undefined,
        subtitle_style: formData.subtitle_style,
        transition_type: formData.transition_type || 'none',
        transition_duration: formData.transition_duration || 0.5,
        image_animation: formData.image_animation || 'none',
        image_animation_intensity: formData.image_animation_intensity || 1.2,
        rendering_preset: formData.rendering_preset || 'fast',
        target_scene_count: formData.target_scene_count || undefined,
      }
      const response = await api.post('/videos/', videoData)
      const videoId = response.data.id
      console.log('[CreateVideoPage] Video created with ID:', videoId)
      toast.success('🎬 Video generation started!')
      // Small delay to ensure video is fully created in database before navigation
      await new Promise(resolve => setTimeout(resolve, 100))
      // Navigate to video detail page which will connect to WebSocket for real-time updates
      navigate(`/videos/${videoId}`)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to create video')
    } finally {
      setIsLoading(false)
    }
  }

  const extractTitleFromScript = (script: string) => {
    const words = script.trim().split(/\s+/).filter(Boolean)
    if (!words.length) return ''
    return words.slice(0, Math.min(Math.max(words.length >= 3 ? 3 : words.length, 3), 6)).join(' ')
  }

  const loadSampleScript = (sample: string) => {
    // Load sample scripts (these would come from API)
    const samples: Record<string, string> = {
      'space': 'In the beginning, humanity looked up at the stars with wonder.\n\nWe dreamed of reaching beyond our world.\n\nToday, we explore the infinite universe.',
      'nature': 'The forest awakens with morning light.\n\nBirds sing their ancient songs.\n\nNature reminds us of simple beauty.',
      'tech': 'Technology shapes our future.\n\nInnovation drives progress.\n\nThe digital age transforms everything.'
    }
    const script = samples[sample] || ''
    setFormData({ ...formData, script, title: extractTitleFromScript(script) })
    toast.success('Sample script loaded!')
  }

  const currentStep = WIZARD_STEPS[currentStepIndex]
  const lastStepIndex = WIZARD_STEPS.length - 1
  const isFirstStep = currentStepIndex === 0
  const isFinalStep = currentStep.id === 'review'

  const validateStep = (step: StepId) => {
    switch (step) {
      case 'script':
        return Boolean(formData.title.trim()) && Boolean(formData.script.trim())
      case 'style':
        return Boolean(formData.style && formData.image_service)
      case 'video':
        return Boolean(formData.resolution && formData.orientation)
      case 'tts':
        return Boolean(formData.tts_provider && formData.tts_voice)
      default:
        return true
    }
  }

  const canProceedCurrentStep = validateStep(currentStep.id)

  const handleNextStep = () => {
    if (!canProceedCurrentStep && currentStep.required) {
      toast.error('Please complete the required fields before moving on.')
          return
        }
    if (currentStepIndex < lastStepIndex) {
      setCurrentStepIndex((prev) => prev + 1)
    }
  }

  const handlePreviousStep = () => {
    if (!isFirstStep) {
      setCurrentStepIndex((prev) => prev - 1)
    }
  }

  const handleSkipStep = () => {
    if (currentStepIndex < lastStepIndex) {
      setCurrentStepIndex((prev) => prev + 1)
    }
  }

  const handleStepClick = (index: number) => {
    if (index <= currentStepIndex) {
      setCurrentStepIndex(index)
    }
  }

  const renderStepContent = () => {
    switch (currentStep.id) {
      case 'script':
  return (
          <section className="app-panel p-6 space-y-5">
            <div className="flex items-center gap-2 pb-4 border-b glass-divider">
            <FileText className="w-6 h-6 text-indigo-300" />
              <h2 className="text-2xl font-bold text-white">Script & Story</h2>
          </div>
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <label className="text-sm font-semibold text-white/80">
                  Video Script <span className="text-rose-300">*</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => loadSampleScript('space')} className="text-xs glass-chip whitespace-nowrap">
                    Load Space Sample
                  </button>
                  <button type="button" onClick={() => loadSampleScript('nature')} className="text-xs glass-chip whitespace-nowrap">
                    Load Nature Sample
                  </button>
                  <button type="button" onClick={() => loadSampleScript('tech')} className="text-xs glass-chip whitespace-nowrap">
                    Load Tech Sample
                  </button>
                </div>
              </div>
              <textarea
                value={formData.script}
                onChange={(e) => {
                  const script = e.target.value
                  setFormData({
                    ...formData,
                    script,
                    title: extractTitleFromScript(script),
                  })
                }}
                className="glass-field w-full font-mono text-sm min-h-[220px] pl-4"
                rows={10}
                placeholder="Enter your video script here..."
                required
              />
              <p className="flex items-start gap-2 text-sm text-white/60">
                <span className="mt-0.5">💡</span>
                <span>
                <strong className="text-white/80">Tip:</strong> Separate each scene with a blank line. Each paragraph becomes one scene in your video.
                </span>
              </p>
              
              {/* Scene Count Input */}
              <div className="mt-4">
                <label className="block text-sm font-semibold text-white/80 mb-2">
                  Number of Scenes (Optional)
                </label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={formData.target_scene_count || ''}
                  onChange={(e) => {
                    const value = e.target.value ? parseInt(e.target.value, 10) : undefined
                    setFormData({
                      ...formData,
                      target_scene_count: value && value > 0 && value <= 50 ? value : undefined
                    })
                  }}
                  className="glass-field w-full max-w-xs"
                  placeholder="Auto (AI will decide)"
                />
                <p className="mt-1 text-xs text-white/50">
                  Leave empty for AI to decide, or specify 1-50 scenes. AI will create exactly this many scenes.
                </p>
              </div>
            </div>
          </section>
        )
      case 'style':
        const selectedImageService = imageServices[formData.image_service || 'pollination']
        const allImageServices = Object.entries(imageServices)
        
        return (
          <section className="app-panel p-6 space-y-6">
        {/* Visual Style Section */}
            <div>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b glass-divider">
            <div className="flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-indigo-300" />
                  <h2 className="text-2xl font-bold text-white">Visual Style</h2>
            </div>
            <button
              onClick={() => setShowStyleGallery(!showStyleGallery)}
                  type="button"
                  className="glass-chip bg-gradient-to-r from-[#527dff] to-[#7450ff] text-white whitespace-nowrap"
            >
              {showStyleGallery ? 'Hide Gallery' : 'Browse All 73 Styles'}
            </button>
          </div>
              <div className="glass-gradient-card p-5 mt-4">
                <p className="text-sm text-white/70 mb-2">Selected Style:</p>
            <p className="text-lg font-semibold text-white capitalize">{formData.style.replace(/_/g, ' ')}</p>
          </div>
          {showStyleGallery && (
                <div className="mt-4">
              <StyleGallery
                selectedStyle={formData.style}
                onSelect={(style) => {
                      setFormData({ ...formData, style })
                  setShowStyleGallery(false)
                  toast.success(`Style changed to: ${style.replace(/_/g, ' ')}`)
                }}
              />
                </div>
          )}
        </div>

            {/* Image Provider Section */}
            <div className="pt-6 border-t glass-divider">
              <div className="flex items-center gap-2 pb-4 border-b glass-divider">
                <ImageIcon className="w-6 h-6 text-indigo-300" />
                <h2 className="text-2xl font-bold text-white">Image Provider</h2>
          </div>
              <div className="space-y-5 mt-4">
            <div>
              <label className="block text-sm font-semibold text-white/80 mb-2">
                    AI Image Service <span className="text-rose-300">*</span>
              </label>
              <select
                    value={formData.image_service || 'pollination'}
                    onChange={(e) => {
                      const service = imageServices[e.target.value]
                      if (service?.requires_api_key && !service?.configured) {
                        toast.error('This service requires an API key. Please configure it in Settings first.')
                        return
                      }
                      setFormData({ 
                        ...formData, 
                        image_service: e.target.value,
                        image_model: service?.default_model || ''
                      })
                    }}
                    className="glass-field w-full"
                  >
                    {allImageServices.map(([id, service]) => (
                      <option key={id} value={id}>
                        {service.label} {service.requires_api_key ? (service.configured ? '(API Key Configured)' : '(API Key Required ⚠️)') : '(Free)'}
                        {service.recommended && ' ⭐'}
                      </option>
                    ))}
              </select>
                  {selectedImageService && (
                    <p className="mt-2 text-xs text-white/60">
                      {selectedImageService.description}
                      {selectedImageService.requires_api_key && !selectedImageService.configured && (
                        <span className="block mt-1 text-rose-300">
                          ⚠️ API key not configured. Please add your API key in Settings.
                        </span>
                      )}
                    </p>
                  )}
            </div>
 
                {selectedImageService && selectedImageService.models && selectedImageService.models.length > 0 && (
            <div>
              <label className="block text-sm font-semibold text-white/80 mb-2">
                      AI Model & Version
              </label>
              <select
                      value={formData.image_model || selectedImageService.default_model || ''}
                      onChange={(e) => setFormData({ ...formData, image_model: e.target.value })}
                      className="glass-field w-full"
                    >
                      {selectedImageService.default_model && (
                        <option value={selectedImageService.default_model}>
                          {selectedImageService.default_model} (Default)
                        </option>
                      )}
                      {selectedImageService.models.map((model: any) => (
                        <option key={model.id} value={model.id}>
                          {model.label || model.id} 
                          {model.description ? ` - ${model.description}` : ''}
                          {model.quality ? ` (${model.quality})` : ''}
                          {model.default_steps ? ` - ${model.default_steps} steps` : ''}
                  </option>
                ))}
              </select>
                    <p className="mt-2 text-xs text-white/60">
                      Select the AI model version for image generation. Higher steps = better quality but slower.
                    </p>
          </div>
          )}
 
                {selectedImageService && (!selectedImageService.models || selectedImageService.models.length === 0) && (
                  <div className="glass-gradient-card p-4 text-center">
                    <p className="text-white/70">
                      {selectedImageService.label} uses default settings. No model selection needed.
                    </p>
          </div>
               )}
              </div>
             </div>
          </section>
        )
      case 'video':
        return (
          <section className="app-panel p-6 space-y-5">
            <div className="flex items-center gap-2 pb-4 border-b glass-divider">
              <SettingsIcon className="w-6 h-6 text-indigo-300" />
              <h2 className="text-2xl font-bold text-white">Video Settings</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-2">Resolution</label>
                <select
                  value={formData.resolution}
                  onChange={(e) => setFormData({ ...formData, resolution: e.target.value })}
                  className="glass-field w-full"
                >
                  <option value="720p">720p (HD)</option>
                  <option value="1080p">1080p (Full HD) ⭐</option>
                  <option value="2K">2K (QHD)</option>
                  <option value="4K">4K (Ultra HD)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-2">Orientation</label>
                <select
                  value={formData.orientation}
                  onChange={(e) => setFormData({ ...formData, orientation: e.target.value })}
                  className="glass-field w-full"
                >
                  <option value="portrait">📱 Portrait (9:16)</option>
                  <option value="landscape">🖥️ Landscape (16:9)</option>
                  <option value="square">⬜ Square (1:1)</option>
                </select>
              </div>
              </div>

            {/* Transitions */}
            <div className="mt-6 space-y-4">
              <div className="flex items-center justify-between">
                <label className="block text-sm font-semibold text-white/80">
                  Scene Transitions
                </label>
              <button
                type="button"
                  onClick={generateTransitionPreview}
                  className="text-xs px-3 py-1.5 bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-200 rounded-lg transition-colors"
              >
                  Preview
              </button>
             </div>
 
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
               <div>
                 <select
                    value={formData.transition_type || 'none'}
                    onChange={(e) => setFormData({ ...formData, transition_type: e.target.value })}
                    className="glass-field w-full"
                  >
                    <option value="none">None</option>
                    {transitions.map(transition => (
                      <option key={transition.id} value={transition.id}>
                        {transition.name}
                     </option>
                   ))}
                 </select>
                  {transitions.find(t => t.id === formData.transition_type) && (
                    <p className="mt-1 text-xs text-white/60">
                      {transitions.find(t => t.id === formData.transition_type)?.description}
                    </p>
                  )}
               </div>
 
                 <div>
                  <label className="block text-sm font-semibold text-white/80 mb-2">
                    Duration (seconds)
                  </label>
                  <input
                    type="number"
                    min="0.1"
                    max="2.0"
                    step="0.1"
                    value={formData.transition_duration || 0.5}
                    onChange={(e) => setFormData({ ...formData, transition_duration: parseFloat(e.target.value) })}
                    className="glass-field w-full"
                    disabled={formData.transition_type === 'none'}
                  />
                </div>
              </div>

              {transitionPreviewUrl && (
                <div className="mt-4 p-4 bg-black/20 rounded-lg">
                  <p className="text-sm text-white/70 mb-2">Transition Preview:</p>
                  <img src={transitionPreviewUrl} alt="Transition preview" className="w-full rounded-lg" />
                 </div>
               )}
             </div>
 
            {/* Image Animation */}
            <div className="mt-6 space-y-4">
              <label className="block text-sm font-semibold text-white/80">
                Image Animation
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
               <div>
                  <select
                    value={formData.image_animation || 'none'}
                    onChange={(e) => setFormData({ ...formData, image_animation: e.target.value })}
                    className="glass-field w-full"
                  >
                    <option value="none">None (Static)</option>
                    <option value="zoom_in">Zoom In</option>
                    <option value="zoom_out">Zoom Out</option>
                    <option value="pan_left">Pan Left</option>
                    <option value="pan_right">Pan Right</option>
                    <option value="pan_up">Pan Up</option>
                    <option value="pan_down">Pan Down</option>
                    <option value="ken_burns">Ken Burns (Zoom + Pan)</option>
                  </select>
                </div>
                
                {formData.image_animation && formData.image_animation !== 'none' && (
                  <div>
                    <label className="block text-sm font-semibold text-white/80 mb-2">
                      Intensity: {formData.image_animation_intensity || 1.2}x
                    </label>
                    <input
                      type="range"
                      min="1.0"
                      max="2.0"
                      step="0.1"
                      value={formData.image_animation_intensity || 1.2}
                      onChange={(e) => setFormData({ ...formData, image_animation_intensity: parseFloat(e.target.value) })}
                      className="w-full"
                    />
                    <p className="mt-1 text-xs text-white/60">
                      Higher values = more zoom/pan movement
                    </p>
                       </div>
                 )}
               </div>
             </div>
          </section>
        )
      case 'tts':
        const selectedService = ttsServices[formData.tts_provider || 'edge']
        const allTtsServices = Object.entries(ttsServices)
        
        return (
          <section className="app-panel p-6 space-y-6">
            <div className="flex items-center gap-2 pb-4 border-b glass-divider">
              <Mic className="w-6 h-6 text-indigo-300" />
              <h2 className="text-2xl font-bold text-white">Voice & TTS</h2>
             </div>
 
            <div className="space-y-5">
              {/* TTS Provider Selection */}
               <div>
                <label className="block text-sm font-semibold text-white/80 mb-2">
                  TTS Provider <span className="text-rose-300">*</span>
                </label>
                 <select
                  value={formData.tts_provider || 'edge'}
                   onChange={async (e) => {
                    const newProvider = e.target.value
                    const service = ttsServices[newProvider]
                    if (service?.requires_api_key && !service?.configured) {
                      toast.error('This service requires an API key. Please configure it in Settings first.')
                      return
                    }
                    // If service exists but has no voices, reload TTS services
                    if (service && (!service.voices || service.voices.length === 0)) {
                      try {
                        const ttsRes = await api.get('/settings/tts-services/options')
                        setTtsServices(ttsRes.data || {})
                        // Update form data after services are reloaded
                        setTimeout(() => {
                          setFormData({ ...formData, tts_provider: newProvider, tts_voice: '', tts_model: '' })
                        }, 100)
                      } catch (error) {
                        console.error('Failed to reload TTS services:', error)
                        setFormData({ ...formData, tts_provider: newProvider, tts_voice: '', tts_model: '' })
                      }
                    } else {
                      setFormData({ ...formData, tts_provider: newProvider, tts_voice: '', tts_model: '' })
                    }
                  }}
                  className="glass-field w-full"
                >
                  {allTtsServices.map(([id, service]) => (
                     <option key={id} value={id}>
                      {service.label} {service.requires_api_key ? (service.configured ? '(API Key Configured)' : '(API Key Required ⚠️)') : '(Free)'}
                     </option>
                   ))}
                 </select>
                {selectedService && (
                  <p className="mt-2 text-xs text-white/60">
                    {selectedService.description}
                  </p>
                )}
               </div>
 
              {/* Model Selection (if available) */}
              {selectedService && selectedService.models && selectedService.models.length > 0 && (
                 <div>
                  <label className="block text-sm font-semibold text-white/80 mb-2">
                    AI Model & Version
                  </label>
                   <select
                    value={formData.tts_model || selectedService.default_model || ''}
                    onChange={(e) => setFormData({ ...formData, tts_model: e.target.value })}
                    className="glass-field w-full"
                  >
                    {selectedService.default_model && (
                      <option value={selectedService.default_model}>
                        {selectedService.default_model} (Default)
                      </option>
                    )}
                    {selectedService.models.map((model: any) => (
                       <option key={model.id} value={model.id}>
                        {model.label || model.id} {model.description ? `- ${model.description}` : ''}
                       </option>
                     ))}
                   </select>
                  <p className="mt-2 text-xs text-white/60">
                    Select the AI model version for voice synthesis
                  </p>
                 </div>
               )}
 
              {/* Voice Selection */}
              {selectedService && selectedService.voices && selectedService.voices.length > 0 && (
                 <div>
                  <label className="block text-sm font-semibold text-white/80 mb-3">
                    Voice <span className="text-rose-300">*</span>
                  </label>
                  
                  {/* Favorites Section */}
                  {favoriteVoices.filter(fav => fav.provider === (formData.tts_provider || 'edge')).length > 0 && (
                    <div className="mb-4">
                      <div className="flex items-center gap-2 mb-3">
                        <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                        <span className="text-sm font-semibold text-white/80">Favorite Voices</span>
             </div>
                      <div className="space-y-2 mb-4 pb-4 border-b glass-divider">
                        {favoriteVoices
                          .filter(fav => fav.provider === (formData.tts_provider || 'edge'))
                          .map((fav) => {
                            const voice = selectedService.voices.find((v: any) => (v.id || v.voice_id || v.name) === fav.voice_id)
                            if (!voice) return null
                            
                            const voiceId = voice.id || voice.voice_id || voice.name
                            const isSelected = formData.tts_voice === voiceId
                            const previewKey = `${formData.tts_provider}-${voiceId}`
                            const isPreviewing = previewingVoice === previewKey
                            const isFavorite = favoriteVoices.some(f => f.provider === formData.tts_provider && f.voice_id === voiceId)
                            
                            return (
                              <div
                                key={`fav-${voiceId}`}
                                className={`glass-gradient-card p-4 cursor-pointer transition-all ${
                                  isSelected ? 'ring-2 ring-indigo-400' : 'hover:ring-1 hover:ring-indigo-300'
                                }`}
                                onClick={() => setFormData({ ...formData, tts_voice: voiceId })}
                              >
                                <div className="flex items-start justify-between gap-3">
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                      <input
                                        type="radio"
                                        checked={isSelected}
                                        onChange={() => setFormData({ ...formData, tts_voice: voiceId })}
                                        className="w-4 h-4 text-indigo-500"
                                      />
                                      <span className="font-semibold text-white">
                                        {voice.label || voice.name || voiceId}
                     </span>
                                      {voice.gender && (
                                        <span className="text-xs text-white/60">({voice.gender})</span>
                                      )}
               </div>
                                    {voice.description && (
                                      <p className="text-xs text-white/70 mb-1">{voice.description}</p>
                                    )}
                                    <div className="flex items-center gap-3 text-xs text-white/50">
                                      {voice.language && <span>🌐 {voice.language}</span>}
                                      {voice.locale && <span>📍 {voice.locale}</span>}
                                      {voice.accent && <span>🎯 {voice.accent}</span>}
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    {selectedService.supports_preview && (
                       <button
                         type="button"
                                        onClick={(e) => {
                                          e.stopPropagation()
                                          previewVoice(formData.tts_provider || 'edge', voiceId, formData.tts_model)
                                        }}
                                        className="glass-chip px-3 py-1.5 text-xs whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
                                        disabled={isPreviewing}
                                        title="Preview voice"
                                      >
                                        {isPreviewing ? '⏸️ Playing...' : '▶️ Preview'}
                       </button>
                     )}
                                    {!selectedService.supports_preview && (
                                      <span className="text-xs text-white/40 px-2">No preview</span>
                                    )}
                       <button
                         type="button"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        toggleFavorite(formData.tts_provider || 'edge', voiceId, voice.label || voice.name || voiceId)
                                      }}
                                      className="p-2 hover:bg-white/10 rounded transition-colors"
                                      title="Remove from favorites"
                                    >
                                      <Heart className={`w-4 h-4 ${isFavorite ? 'text-rose-400 fill-rose-400' : 'text-white/40'}`} />
                       </button>
                   </div>
                 </div>
                 </div>
                            )
                          })}
                      </div>
             </div>
             )}
 
                  {/* All Voices Section */}
                  <div className="space-y-2 max-h-[500px] overflow-y-auto">
                    {selectedService.voices.map((voice: any) => {
                      const voiceId = voice.id || voice.voice_id || voice.name
                      const isSelected = formData.tts_voice === voiceId
                      const previewKey = `${formData.tts_provider}-${voiceId}`
                      const isPreviewing = previewingVoice === previewKey
                      const isFavorite = favoriteVoices.some(f => f.provider === formData.tts_provider && f.voice_id === voiceId)
                      const isInFavoritesSection = favoriteVoices.some(f => f.provider === formData.tts_provider && f.voice_id === voiceId)
                      
                      // Skip if already shown in favorites
                      if (isInFavoritesSection) return null
                      
                      return (
                        <div
                          key={voiceId}
                          className={`glass-gradient-card p-4 cursor-pointer transition-all ${
                            isSelected ? 'ring-2 ring-indigo-400' : 'hover:ring-1 hover:ring-indigo-300'
                          }`}
                          onClick={() => setFormData({ ...formData, tts_voice: voiceId })}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <input
                                  type="radio"
                                  checked={isSelected}
                                  onChange={() => setFormData({ ...formData, tts_voice: voiceId })}
                                  className="w-4 h-4 text-indigo-500"
                                />
                                <span className="font-semibold text-white">
                                  {voice.label || voice.name || voiceId}
                           </span>
                                {voice.gender && (
                                  <span className="text-xs text-white/60">({voice.gender})</span>
                         )}
                       </div>
                              {voice.description && (
                                <p className="text-xs text-white/70 mb-1">{voice.description}</p>
                              )}
                              <div className="flex items-center gap-3 text-xs text-white/50">
                                {voice.language && <span>🌐 {voice.language}</span>}
                                {voice.locale && <span>📍 {voice.locale}</span>}
                                {voice.accent && <span>🎯 {voice.accent}</span>}
                           </div>
                         </div>
                            <div className="flex items-center gap-2">
                              {selectedService.supports_preview && (
                               <button
                                 type="button"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    previewVoice(formData.tts_provider || 'edge', voiceId, formData.tts_model)
                                  }}
                                  className="glass-chip px-3 py-1.5 text-xs whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
                                  disabled={isPreviewing}
                                  title="Preview voice"
                                >
                                  {isPreviewing ? '⏸️ Playing...' : '▶️ Preview'}
                               </button>
                             )}
                              {!selectedService.supports_preview && (
                                <span className="text-xs text-white/40 px-2">No preview</span>
                              )}
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  toggleFavorite(formData.tts_provider || 'edge', voiceId, voice.label || voice.name || voiceId)
                                }}
                                className="p-2 hover:bg-white/10 rounded transition-colors"
                                title={isFavorite ? "Remove from favorites" : "Add to favorites"}
                              >
                                <Heart className={`w-4 h-4 ${isFavorite ? 'text-rose-400 fill-rose-400' : 'text-white/40'}`} />
                              </button>
                         </div>
                       </div>
               </div>
                      )
                    })}
             </div>
                  <p className="mt-2 text-xs text-white/50">
                    {selectedService.voices.length} voices available
                  </p>
           </div>
              )}
 
              {selectedService && (!selectedService.voices || selectedService.voices.length === 0) && (
                <div className="glass-gradient-card p-4 text-center">
                  <p className="text-white/70">No voices available for this provider.</p>
                  {selectedService.requires_api_key && !selectedService.configured && (
                    <p className="text-xs text-white/50 mt-2">
                      Please configure your API key in Settings.
                    </p>
                 )}
        </div>
              )}
            </div>

            {/* Audio & Music Section */}
            <div className="pt-6 border-t glass-divider">
              <div className="flex items-center gap-2 pb-4 border-b glass-divider">
                <Music className="w-6 h-6 text-indigo-300" />
                <h2 className="text-2xl font-bold text-white">Audio & Overlays</h2>
        </div>
              <div className="space-y-5 mt-4">
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-2">
                  Background Music <span className="text-white/50">(Optional)</span>
                </label>
                <select
                  value={formData.backgroundMusic || ''}
                    onChange={(e) => setFormData({ ...formData, backgroundMusic: e.target.value })}
                    className="glass-field w-full"
                >
                  <option value="">No Background Music</option>
                  {musicFiles.map(music => (
                    <option key={music} value={music}>{music.replace('.mp3', '').replace('.MP3', '')}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-2">
                  Video Overlay <span className="text-white/50">(Optional)</span>
                </label>
                <select
                  value={formData.videoOverlay || ''}
                    onChange={(e) => setFormData({ ...formData, videoOverlay: e.target.value })}
                    className="glass-field w-full"
                >
                  <option value="">No Overlay Effect</option>
                  {overlayFiles.map(overlay => (
                    <option key={overlay} value={overlay}>{overlay.replace('.mp4', '')}</option>
                  ))}
                </select>
              </div>
              </div>
            </div>
          </section>
        )
      case 'subtitles':
        return (
          <section className="app-panel p-6 space-y-5">
            <div className="flex items-center gap-2 pb-4 border-b glass-divider">
              <Type className="w-6 h-6 text-indigo-300" />
              <h2 className="text-2xl font-bold text-white">Subtitle Settings</h2>
              </div>

            <div className="space-y-4">
              {/* Enable/Disable Subtitles */}
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="subtitle-enabled"
                  checked={formData.subtitle_style?.enabled !== false}
                  onChange={(e) => setFormData({
                    ...formData,
                    subtitle_style: {
                      ...formData.subtitle_style,
                      enabled: e.target.checked
                    }
                  })}
                  className="w-5 h-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="subtitle-enabled" className="text-sm font-semibold text-white/80">
                  Enable Subtitles
                </label>
              </div>

              {formData.subtitle_style?.enabled !== false && (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-semibold text-white/80 mb-2">
                        Font
                      </label>
                      <select
                        value={formData.font || ''}
                        onChange={(e) => setFormData({ ...formData, font: e.target.value })}
                        className="glass-field w-full"
                      >
                        <option value="">Default Font</option>
                        {fonts.map(font => (
                          <option key={font} value={font}>{font.replace('.ttf', '')}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-white/80 mb-2">
                        Font Size
                      </label>
                      <input
                        type="number"
                        min="20"
                        max="200"
                        value={formData.subtitle_style?.font_size || 60}
                        onChange={(e) => setFormData({
                          ...formData,
                          subtitle_style: {
                            ...formData.subtitle_style,
                            font_size: parseInt(e.target.value)
                          }
                        })}
                        className="glass-field w-full"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-white/80 mb-2">
                        Position
                      </label>
                      <select
                        value={formData.subtitle_style?.position || 'bottom'}
                        onChange={(e) => setFormData({
                          ...formData,
                          subtitle_style: {
                            ...formData.subtitle_style,
                            position: e.target.value
                          }
                        })}
                        className="glass-field w-full"
                      >
                        <option value="top">Top</option>
                        <option value="center">Center</option>
                        <option value="bottom">Bottom</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-white/80 mb-2">
                        Text Color
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="color"
                          value={formData.subtitle_style?.text_color || '#FFFFFF'}
                          onChange={(e) => setFormData({
                            ...formData,
                            subtitle_style: {
                              ...formData.subtitle_style,
                              text_color: e.target.value
                            }
                          })}
                          className="w-16 h-10 rounded-lg cursor-pointer"
                        />
                        <input
                          type="text"
                          value={formData.subtitle_style?.text_color || '#FFFFFF'}
                          onChange={(e) => setFormData({
                            ...formData,
                            subtitle_style: {
                              ...formData.subtitle_style,
                              text_color: e.target.value
                            }
                          })}
                          className="glass-field flex-1"
                          placeholder="#FFFFFF"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-white/80 mb-2">
                        Background Opacity: {formData.subtitle_style?.bg_opacity || 180}
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="255"
                        value={formData.subtitle_style?.bg_opacity || 180}
                        onChange={(e) => setFormData({
                          ...formData,
                          subtitle_style: {
                            ...formData.subtitle_style,
                            bg_opacity: parseInt(e.target.value)
                          }
                        })}
                        className="w-full"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-white/80 mb-2">
                        Outline Width: {formData.subtitle_style?.outline_width || 3}
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="10"
                        value={formData.subtitle_style?.outline_width || 3}
                        onChange={(e) => setFormData({
                          ...formData,
                          subtitle_style: {
                            ...formData.subtitle_style,
                            outline_width: parseInt(e.target.value)
                          }
                        })}
                        className="w-full"
                      />
                    </div>
                  </div>

                </>
              )}
            </div>
          </section>
        )
      case 'advanced':
        return (
          <section className="app-panel p-6 space-y-5">
            <div className="flex items-center gap-2 pb-4 border-b glass-divider">
              <Wand2 className="w-6 h-6 text-indigo-300" />
              <h2 className="text-2xl font-bold text-white">Advanced Settings</h2>
            </div>
            
            <div className="space-y-5">
              {/* AI Provider Selection */}
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-2">
                  AI Provider for Scene Analysis <span className="text-white/50">(Required)</span>
                </label>
                <p className="mb-3 text-xs text-white/60">
                  Choose which AI will analyze your script and create logical scenes. The AI reads your entire script first, then intelligently divides it into scenes.
                </p>
                <select
                  value={formData.ai_provider || 'groq'}
                  onChange={(e) => setFormData({ ...formData, ai_provider: e.target.value, ai_model: '' })}
                  className="glass-field w-full px-4 py-3 text-white"
                >
                  <option value="groq">Groq (Fast & Efficient)</option>
                  <option value="gemini">Google Gemini (High Quality)</option>
                  <option value="openai">OpenAI (Premium Quality)</option>
                </select>
                <p className="mt-2 text-xs text-white/60">
                  {formData.ai_provider === 'groq' && 'Groq provides fast scene analysis with excellent quality.'}
                  {formData.ai_provider === 'gemini' && 'Gemini offers high-quality scene analysis with deep understanding.'}
                  {formData.ai_provider === 'openai' && 'OpenAI provides premium quality scene analysis.'}
                </p>
              </div>

              {/* AI Model Selection (Optional) */}
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-2">
                  AI Model <span className="text-white/50">(Optional - uses default if not specified)</span>
                </label>
                <input
                  type="text"
                  value={formData.ai_model || ''}
                  onChange={(e) => setFormData({ ...formData, ai_model: e.target.value })}
                  className="glass-field w-full px-4 py-3 text-white placeholder-white/40"
                  placeholder={formData.ai_provider === 'groq' ? 'e.g., llama-3.1-8b-instant, llama-3.1-70b-versatile' : formData.ai_provider === 'gemini' ? 'e.g., gemini-1.5-flash, gemini-1.5-pro' : 'e.g., gpt-4, gpt-3.5-turbo'}
                />
                <p className="mt-2 text-xs text-white/60">
                  Leave empty to use the default model for {formData.ai_provider === 'groq' ? 'Groq' : formData.ai_provider === 'gemini' ? 'Gemini' : 'OpenAI'}.
                </p>
              </div>

              {/* Custom Instructions */}
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-2">
                  Custom Image Instructions <span className="text-white/50">(Optional)</span>
                </label>
                <textarea
                  value={formData.customInstructions || ''}
                  onChange={(e) => setFormData({ ...formData, customInstructions: e.target.value })}
                  className="glass-field w-full px-4 py-3 text-white placeholder-white/40"
                  rows={5}
                  placeholder="Describe characters, camera angles, color palettes, or anything that should stay consistent across scenes."
                />
                <p className="mt-2 text-xs text-white/60">These instructions will be appended to every generated scene.</p>
              </div>
            </div>
          </section>
        )
      case 'review':
        return (
          <section className="app-panel p-6 space-y-5">
            <div className="flex items-center gap-2 pb-4 border-b glass-divider">
              <Sparkles className="w-6 h-6 text-indigo-300" />
              <h2 className="text-2xl font-bold text-white">Review & Confirm</h2>
            </div>
            <dl className="grid gap-4 md:grid-cols-2">
              <div className="p-4 glass-gradient-card rounded-lg border border-white/10">
                <dt className="text-sm font-semibold text-white/70 mb-1">Title</dt>
                <dd className="text-white">{formData.title || '—'}</dd>
        </div>
              <div className="p-4 glass-gradient-card rounded-lg border border-white/10">
                <dt className="text-sm font-semibold text-white/70 mb-1">Style</dt>
                <dd className="text-white capitalize">{formData.style.replace(/_/g, ' ')}</dd>
              </div>
              <div className="p-4 glass-gradient-card rounded-lg border border-white/10">
                <dt className="text-sm font-semibold text-white/70 mb-1">Image Provider</dt>
                <dd className="text-white">
                  {imageServices[formData.image_service || 'pollination']?.label || formData.image_service || 'Pollination'}
                  {formData.image_model && ` · ${formData.image_model}`}
                </dd>
              </div>
              <div className="p-4 glass-gradient-card rounded-lg border border-white/10">
                <dt className="text-sm font-semibold text-white/70 mb-1">Voice Provider</dt>
                <dd className="text-white">
                  {ttsServices[formData.tts_provider || 'edge']?.label || formData.tts_provider || 'Edge TTS'}
                  {formData.tts_voice && ` · ${formData.tts_voice}`}
                </dd>
              </div>
              <div className="p-4 glass-gradient-card rounded-lg border border-white/10">
                <dt className="text-sm font-semibold text-white/70 mb-1">AI Provider (Scene Analysis)</dt>
                <dd className="text-white capitalize">
                  {formData.ai_provider === 'groq' ? 'Groq (Fast & Efficient)' : 
                   formData.ai_provider === 'gemini' ? 'Google Gemini (High Quality)' : 
                   formData.ai_provider === 'openai' ? 'OpenAI (Premium Quality)' : 
                   formData.ai_provider || 'Groq'}
                  {formData.ai_model && ` · ${formData.ai_model}`}
                </dd>
              </div>
              {formData.target_scene_count && (
                <div className="p-4 glass-gradient-card rounded-lg border border-white/10">
                  <dt className="text-sm font-semibold text-white/70 mb-1">Target Scene Count</dt>
                  <dd className="text-white">{formData.target_scene_count} scenes</dd>
                </div>
              )}
              <div className="p-4 glass-gradient-card rounded-lg border border-white/10">
                <dt className="text-sm font-semibold text-white/70 mb-1">Resolution & Orientation</dt>
                <dd className="text-white">{formData.resolution} · {formData.orientation}</dd>
              </div>
              <div className="p-4 glass-gradient-card rounded-lg border border-white/10">
                <dt className="text-sm font-semibold text-white/70 mb-1">Audio & Overlay</dt>
                <dd className="text-white">
                  {formData.backgroundMusic ? formData.backgroundMusic.replace('.mp3', '') : 'No music'} / {formData.videoOverlay ? formData.videoOverlay.replace('.mp4', '') : 'No overlay'}
                </dd>
              </div>
              <div className="p-4 glass-gradient-card rounded-lg border border-white/10">
                <dt className="text-sm font-semibold text-white/70 mb-1">Transitions</dt>
                <dd className="text-white">
                  {formData.transition_type === 'none' ? 'None' : 
                   transitions.find(t => t.id === formData.transition_type)?.name || formData.transition_type}
                  {formData.transition_type !== 'none' && ` (${formData.transition_duration || 0.5}s)`}
                </dd>
              </div>
              <div className="p-4 glass-gradient-card rounded-lg border border-white/10">
                <dt className="text-sm font-semibold text-white/70 mb-1">Subtitles</dt>
                <dd className="text-white">
                  {formData.subtitle_style?.enabled !== false ? (
                    <>
                      {formData.font ? formData.font.replace('.ttf', '') : 'Default'} · 
                      Size: {formData.subtitle_style?.font_size || 60} · 
                      {formData.subtitle_style?.position || 'bottom'}
                    </>
                  ) : 'Disabled'}
                </dd>
              </div>
              <div className="p-4 glass-gradient-card rounded-lg border border-white/10">
                <dt className="text-sm font-semibold text-white/70 mb-1">Rendering Quality</dt>
                <dd className="text-white">
                  {formData.rendering_preset === 'fast' ? 'Fast (Quick Previews)' : 'Quality (Final Exports)'}
                </dd>
              </div>
              <div className="p-4 glass-gradient-card rounded-lg border border-white/10">
                <dt className="text-sm font-semibold text-white/70 mb-1">Image Animation</dt>
                <dd className="text-white">
                  {formData.image_animation === 'none' || !formData.image_animation ? 'None (Static)' : 
                   formData.image_animation.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  {formData.image_animation && formData.image_animation !== 'none' && 
                   ` (${formData.image_animation_intensity || 1.2}x intensity)`}
                </dd>
              </div>
            </dl>
            <div className="p-4 glass-gradient-card rounded-lg border border-white/10">
              <dt className="text-sm font-semibold text-white/70 mb-2">Script Preview</dt>
              <dd className="text-sm text-white/90 whitespace-pre-line">
                {formData.script.split('\n\n').slice(0, 2).join('\n\n') || 'No script provided.'}
              </dd>
            </div>
          </section>
        )
      default:
        return null
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4">
      {/* Step Indicator */}
      <div className="mb-6 -mx-4">
        <WizardStepIndicator steps={WIZARD_STEPS} currentIndex={currentStepIndex} onStepClick={handleStepClick} />
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {renderStepContent()}

        {currentStep.id === 'review' ? (
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-end">
            {!isFirstStep && (
          <button
            type="button"
                onClick={handlePreviousStep}
                className="px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-desktop hover:bg-gray-50 transition-all font-semibold"
          >
                Back
          </button>
            )}
          <div className="space-y-3">
            <button
              type="submit"
              disabled={isLoading}
              className="w-full px-8 py-3 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-desktop hover:from-primary-600 hover:to-primary-700 transition-all font-semibold shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <div className="w-5 h-5 border-3 border-white border-t-transparent rounded-full animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Video className="w-5 h-5" />
                  Create Video
                  <Sparkles className="w-4 h-4" />
                </>
              )}
            </button>
            <p className="text-xs text-center text-white/60 px-4">
              💡 Video generation happens in the background. After clicking "Create Video", you'll be redirected to a status page where you can monitor progress. 
              You can safely close the page and return later from <strong>My Videos</strong>.
            </p>
          </div>
        </div>
        ) : (
          <WizardControls
            isFirstStep={isFirstStep}
            isOptional={!currentStep.required}
            canProceed={canProceedCurrentStep}
            onBack={handlePreviousStep}
            onNext={handleNextStep}
            onSkip={!currentStep.required ? handleSkipStep : undefined}
            nextLabel={currentStepIndex === lastStepIndex - 1 ? 'Continue to Review' : 'Continue'}
          />
        )}
      </form>

      {/* Info Card */}
      <div className="app-panel p-6 mt-6">
        <h3 className="font-bold text-white mb-2 flex items-center gap-2">
          <span>💡</span> Pro Tips for Best Results
        </h3>
        <ul className="space-y-2 text-sm text-white/70">
          <li className="flex items-start gap-2">
            <span className="text-indigo-300 font-bold">→</span>
            <span><strong>Script Format:</strong> Each blank line creates a new scene. Keep paragraphs concise (2-3 sentences)</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-300 font-bold">→</span>
            <span><strong>Visual Styles:</strong> Browse all 73 styles to find the perfect look for your video</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-300 font-bold">→</span>
            <span><strong>Custom Instructions:</strong> Describe consistent characters or settings for better scene coherence</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-300 font-bold">→</span>
            <span><strong>Background Music:</strong> Add mood with background music (optional but recommended)</span>
          </li>
        </ul>
      </div>
    </div>
  )
}



interface WizardStepIndicatorProps {
  steps: WizardStep[]
  currentIndex: number
  onStepClick: (index: number) => void
}

function WizardStepIndicator({ steps, currentIndex, onStepClick }: WizardStepIndicatorProps) {
  return (
    <div className="app-panel p-4 mx-4">
      <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1" style={{ scrollbarWidth: 'thin' }}>
        {steps.map((step, index) => {
          const isCompleted = index < currentIndex
          const isActive = index === currentIndex
          
          // Active step: gradient with indigo accent
          const activeClasses = 'border-indigo-400/60 bg-gradient-to-br from-indigo-500/30 to-purple-500/20 text-white shadow-lg shadow-indigo-500/20'
          // Completed step: subtle green accent
          const completedClasses = 'border-emerald-400/40 bg-emerald-500/15 text-emerald-300'
          // Inactive step: muted glass style
          const inactiveClasses = 'border-white/10 bg-white/5 text-white/50'

          const classes = isActive
            ? activeClasses
            : isCompleted
              ? completedClasses
              : inactiveClasses

          return (
            <button
              key={step.id}
              type="button"
              onClick={() => onStepClick(index)}
              disabled={index > currentIndex}
              className={`flex-shrink-0 rounded-desktop border px-3 py-2.5 text-left transition-all ${isActive ? 'min-w-[140px] max-w-[180px]' : 'min-w-[110px] max-w-[140px]'} ${classes} ${
                index > currentIndex 
                  ? 'opacity-40 cursor-not-allowed' 
                  : 'hover:border-indigo-400/40 hover:bg-white/10'
              }`}
            >
              <div className="text-xs font-semibold uppercase tracking-wide mb-1 whitespace-nowrap">
                {step.required ? `Step ${index + 1}` : `Step ${index + 1} · Opt`}
              </div>
              <div className="text-sm font-bold truncate">{step.title}</div>
              {isActive && (
                <p className="text-xs opacity-80 mt-1 line-clamp-2">{step.description}</p>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

interface WizardControlsProps {
  isFirstStep: boolean
  isOptional: boolean
  canProceed: boolean
  onBack: () => void
  onNext: () => void
  onSkip?: () => void
  nextLabel: string
}

function WizardControls({ isFirstStep, isOptional, canProceed, onBack, onNext, onSkip, nextLabel }: WizardControlsProps) {
  return (
    <div className="bg-white rounded-desktop p-5 shadow-md border border-gray-200 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div className="text-sm text-gray-600">
        {isOptional ? 'This step is optional.' : 'Complete this step to continue.'}
      </div>
      <div className="flex flex-wrap gap-3 justify-end">
        {!isFirstStep && (
          <button
            type="button"
            onClick={onBack}
            className="px-4 py-2 rounded-desktop bg-gray-100 text-gray-700 hover:bg-gray-200 font-semibold"
          >
            Back
          </button>
        )}
        {isOptional && onSkip && (
          <button
            type="button"
            onClick={onSkip}
            className="px-4 py-2 rounded-desktop border-2 border-gray-200 text-gray-600 hover:bg-gray-50 font-semibold"
          >
            Skip
          </button>
        )}
        <button
          type="button"
          onClick={onNext}
          disabled={!canProceed && !isOptional}
          className="px-6 py-2 rounded-desktop bg-primary-500 text-white font-semibold shadow hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {nextLabel}
        </button>
      </div>
    </div>
  )
}
