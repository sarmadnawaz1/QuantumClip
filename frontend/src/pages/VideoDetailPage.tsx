import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Download, Trash2, Play, RefreshCw, Share2, Clock, FileVideo, FileText, XCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../services/api'
import { videoProgressWS, VideoProgressMessage } from '../services/websocket'
import { useAuthStore } from '../stores/authStore'

const IMAGE_SERVICE_LABELS: Record<string, string> = {
  pollination: 'Pollination AI',
  runware: 'Runware.ai',
  replicate: 'Replicate',
  together: 'Together AI',
  fal: 'FAL AI'
}

const IMAGE_MODEL_LABELS: Record<string, Record<string, string>> = {
  runware: {
    flux_dev: 'Flux Dev',
    hidream_i1_dev: 'HiDream-i1 Dev',
    flex_schenele: 'Flex Schenele',
    juggernaut_lightning: 'Juggernaut Lightning',
    hidream_i1_fast: 'HiDream-i1 Fast'
  },
  replicate: {
    'black-forest-labs/flux-schnell': 'Flux Schnell'
  },
  together: {
    'black-forest-labs/FLUX.1-schnell-Free': 'FLUX.1 Schnell Free'
  },
  fal: {
    'fal-ai/flux/schnell': 'Flux Schnell'
  }
}

const TTS_SERVICE_LABELS: Record<string, string> = {
  edge: 'Edge TTS',
  elevenlabs: 'ElevenLabs',
  fishaudio: 'Fish Audio',
  azure: 'Azure Neural TTS'
}

const humanize = (value?: string | null) => {
  if (!value) return ''
  return value.replace(/[_-]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

const getImageServiceLabel = (service?: string) => {
  if (!service) return 'Unknown'
  return IMAGE_SERVICE_LABELS[service] || humanize(service)
}

const getImageModelLabel = (service?: string, model?: string | null) => {
  if (!model) return ''
  if (service && IMAGE_MODEL_LABELS[service] && IMAGE_MODEL_LABELS[service][model]) {
    return IMAGE_MODEL_LABELS[service][model]
  }
  return humanize(model)
}

const getTtsVoiceLabel = (voice?: string | null) => {
  if (!voice) return ''
  return humanize(voice)
}

const getTtsServiceLabel = (service?: string) => {
  if (!service) return 'Unknown'
  return TTS_SERVICE_LABELS[service] || humanize(service)
}

const getTransitionLabel = (value?: string | null) => {
  if (!value) return 'None'
  const lower = value.toLowerCase()
  if (lower === 'none') return 'None'
  if (lower === 'random') return 'Random Mix'
  if (lower === 'fade_black') return 'Fade to Black'
  if (lower === 'fade_white') return 'Fade to White'
  if (lower === 'zoom_cross') return 'Cross Zoom'
  return humanize(value)
}

interface Video {
  id: number
  title: string
  description?: string
  script: string
  style: string
  resolution: string
  orientation: string
  status: string
  progress: number
  error_message?: string
  video_url?: string
  thumbnail_url?: string
  duration?: number
  file_size?: number
  scene_count?: number
  image_service: string
  image_model?: string | null
  ai_provider?: string
  ai_model?: string | null
  tts_provider?: string
  tts_voice?: string | null
  tts_model?: string | null
  created_at: string
  transition_type?: string
  transition_duration?: number
}

export default function VideoDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [video, setVideo] = useState<Video | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [logMessages, setLogMessages] = useState<string[]>([])
  const [videoError, setVideoError] = useState<string | null>(null)
  const [videoBlobUrl, setVideoBlobUrl] = useState<string | null>(null)
  const { token } = useAuthStore()
  const unsubscribeRef = useRef<(() => void) | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  
  // For video URLs, use empty string (relative path) so it goes through Vite proxy
  // The proxy will forward /uploads requests to the backend
  const apiBaseUrl = ''
  
  // Load video as blob when video is completed
  useEffect(() => {
    if (!video?.id || !isCompleted || videoBlobUrl) return
    
    const loadVideoBlob = async () => {
      try {
        console.log(`[VideoDetailPage] Loading video ${video.id} as blob from download endpoint...`)
        const response = await api.get(`/videos/${video.id}/download`, {
          responseType: 'blob',
        })
        const blob = new Blob([response.data], { type: 'video/mp4' })
        const url = window.URL.createObjectURL(blob)
        setVideoBlobUrl(url)
        console.log(`[VideoDetailPage] Video blob loaded successfully: ${url}`)
      } catch (error) {
        console.error('[VideoDetailPage] Failed to load video blob:', error)
        // Don't set error here - let the video element try the direct URL first
      }
    }
    
    loadVideoBlob()
  }, [video?.id, isCompleted, videoBlobUrl])
  
  // Cleanup blob URL on unmount or when video changes
  useEffect(() => {
    return () => {
      if (videoBlobUrl) {
        window.URL.revokeObjectURL(videoBlobUrl)
        setVideoBlobUrl(null)
      }
    }
  }, [video?.id]) // Cleanup when video ID changes

  useEffect(() => {
    if (!id) return

    // Load video initially
    loadVideo()
    
    // Connect to WebSocket for real-time updates if video is not completed
    const videoId = parseInt(id, 10)
    if (videoId && token) {
      // Connect WebSocket
      videoProgressWS.connect(videoId, token)
      setIsConnected(videoProgressWS.isConnected())
      
      // Subscribe to progress updates
      const unsubscribe = videoProgressWS.onProgress((message: VideoProgressMessage) => {
        console.log('[VideoDetailPage] Progress update:', message)
        
        if (message.type === 'connected') {
          setIsConnected(true)
          setIsLoading(false) // Stop loading once connected
        }
        
        if (message.type === 'progress') {
          // Add log message
          const timestamp = new Date().toLocaleTimeString()
          const stageMessage = message.current_step || message.status || 'Processing...'
          setLogMessages(prev => {
            const newMessage = `[${timestamp}] ${stageMessage} (${message.progress ?? 0}%)`
            // Keep last 20 messages
            return [...prev.slice(-19), newMessage]
          })
          
          // Update video state with real-time progress
          setVideo(prev => {
            // Ensure progress is always a number
            const progress = message.progress ?? 0
            if (!prev) {
              // If we don't have video data yet, create a minimal object
              return {
                id: message.video_id,
                title: 'Loading...',
                script: '',
                style: '',
                resolution: '',
                orientation: '',
                status: message.status,
                progress: progress,
                error_message: message.error_message || undefined,
                image_service: '',
                created_at: new Date().toISOString(),
              } as Video
            }
            return {
              ...prev,
              status: message.status,
              progress: progress,
              error_message: message.error_message || undefined,
            }
          })
          
          setIsLoading(false) // Stop loading when we receive progress updates
          
          // If completed, reload full video data
          if (message.status === 'completed') {
            setTimeout(() => {
              loadVideo()
            }, 1000)
            toast.success('🎉 Video generation completed!')
          }
          
          // If failed, show error
          if (message.status === 'failed' && message.error_message) {
            setIsLoading(false)
            toast.error(`Video generation failed: ${message.error_message}`)
          }
        }
      })
      
      unsubscribeRef.current = unsubscribe
      
      // Check connection status periodically
      const connectionCheck = setInterval(() => {
        setIsConnected(videoProgressWS.isConnected())
      }, 2000)
      
      return () => {
        unsubscribe()
        videoProgressWS.disconnect()
        clearInterval(connectionCheck)
      }
    } else {
      // Fallback to polling if no token or WebSocket not available
      console.log('[VideoDetailPage] WebSocket not available, using polling fallback')
      const interval = setInterval(() => {
        loadVideo()
      }, 3000) // Poll every 3 seconds

      return () => clearInterval(interval)
    }
  }, [id, token])
  
  // Additional polling fallback for status updates (even when WebSocket is connected)
  useEffect(() => {
    if (!id || !video) return
    
    const statusLower = (video.status || '').toLowerCase()
    const isProcessing = statusLower === 'in_progress' || 
      ['pending', 'processing', 'generating_prompts', 'generating_images', 'generating_audio', 'rendering'].includes(statusLower)
    
    // If processing and WebSocket might not be working, add polling as backup
    if (isProcessing && !isConnected) {
      console.log('[VideoDetailPage] WebSocket not connected, starting backup polling')
      const pollInterval = setInterval(async () => {
        try {
          const response = await api.get(`/videos/${id}/status`)
          const statusData = response.data
          
          // Add log message
          const timestamp = new Date().toLocaleTimeString()
          const stageMessage = statusData.current_step || statusData.status || 'Processing...'
          setLogMessages(prev => {
            const newMessage = `[${timestamp}] ${stageMessage} (${statusData.progress ?? 0}%)`
            // Only add if different from last message
            if (prev.length === 0 || prev[prev.length - 1] !== newMessage) {
              return [...prev.slice(-19), newMessage]
            }
            return prev
          })
          
          setVideo(prev => prev ? {
            ...prev,
            status: statusData.status,
            progress: statusData.progress ?? 0,
            error_message: statusData.error_message || undefined,
          } : prev)
          
          // Stop polling if completed or failed
          if (statusData.status === 'completed' || statusData.status === 'failed') {
            clearInterval(pollInterval)
            if (statusData.status === 'completed') {
              loadVideo() // Reload full video data
            }
          }
        } catch (error) {
          console.error('[VideoDetailPage] Polling error:', error)
        }
      }, 3000) // Poll every 3 seconds
      
      return () => clearInterval(pollInterval)
    }
  }, [id, video, isConnected])

  const loadVideo = async () => {
    if (!id) {
      setIsLoading(false)
      return
    }
    
    try {
      setIsLoading(true)
      const response = await api.get(`/videos/${id}`)
      const videoData = response.data
      
      // Ensure video_url is properly formatted
      if (videoData.video_url) {
        // If it's already a full URL, keep it
        if (videoData.video_url.startsWith('http://') || videoData.video_url.startsWith('https://')) {
          // Already a full URL, keep as is
        } else if (videoData.video_url.startsWith('/uploads/')) {
          // Already has /uploads/ prefix, keep as is (will go through Vite proxy)
        } else if (videoData.video_url.startsWith('/')) {
          // Starts with / but not /uploads/, assume it's correct
        } else {
          // No leading slash, add /uploads/
          videoData.video_url = `/uploads/${videoData.video_url}`
        }
        console.log('[VideoDetailPage] Video URL formatted:', videoData.video_url)
      }
      
      // Same for thumbnail
      if (videoData.thumbnail_url) {
        if (videoData.thumbnail_url.startsWith('http://') || videoData.thumbnail_url.startsWith('https://')) {
          // Already a full URL
        } else if (videoData.thumbnail_url.startsWith('/uploads/')) {
          // Already has /uploads/ prefix
        } else if (videoData.thumbnail_url.startsWith('/')) {
          // Starts with /, assume correct
        } else {
          // No leading slash, add /uploads/
          videoData.thumbnail_url = `/uploads/${videoData.thumbnail_url}`
        }
        console.log('[VideoDetailPage] Thumbnail URL formatted:', videoData.thumbnail_url)
      }
      
      console.log('[VideoDetailPage] Video data loaded:', {
        id: videoData.id,
        status: videoData.status,
        video_url: videoData.video_url,
        thumbnail_url: videoData.thumbnail_url,
        progress: videoData.progress
      })
      
      console.log('[VideoDetailPage] Setting video data:', videoData)
      // Ensure progress is always a number
      if (videoData.progress === null || videoData.progress === undefined) {
        videoData.progress = 0
      }
      setVideo(videoData)
      setIsLoading(false)
      
      // Add initial log message
      const timestamp = new Date().toLocaleTimeString()
      const statusMessage = videoData.status === 'pending' 
        ? 'Video queued, starting generation...'
        : videoData.status === 'processing'
        ? 'Processing video...'
        : `Status: ${videoData.status}`
      setLogMessages(prev => {
        const newMessage = `[${timestamp}] ${statusMessage} (${videoData.progress ?? 0}%)`
        return [newMessage]
      })
      
      // If video is completed or failed, disconnect WebSocket
      if (videoData.status === 'completed' || videoData.status === 'failed') {
        videoProgressWS.disconnect()
        setIsConnected(false)
      }
    } catch (error: any) {
      console.error('[VideoDetailPage] Error loading video:', error)
      console.error('[VideoDetailPage] Error details:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message
      })
      setIsLoading(false)
      
      // If unauthorized, might need to re-login
      if (error.response?.status === 401) {
        console.log('Not authenticated, redirecting to login...')
        navigate('/login')
        return
      }
      
      // If video not found, show error but don't redirect immediately
      if (error.response?.status === 404) {
        toast.error('Video not found')
        setVideo(null) // Explicitly set to null so error state shows
        return
      }
      
      toast.error(error.response?.data?.detail || 'Failed to load video. Please try again.')
      setVideo(null) // Set to null on error so error state shows
    }
  }

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this video?')) return

    setIsDeleting(true)
    try {
      await api.delete(`/videos/${id}`)
      toast.success('Video deleted successfully')
      navigate('/create')
    } catch (error) {
      toast.error('Failed to delete video')
    } finally {
      setIsDeleting(false)
    }
  }

  const handleDownload = async () => {
    if (!video?.id) return
    
    try {
      toast.loading('Preparing download...', { id: 'download' })
      
      // Use the download endpoint
      const response = await api.get(`/videos/${video.id}/download`, {
        responseType: 'blob',
        validateStatus: (status) => status < 500 // Don't throw on 4xx, we'll handle it
      })
      
      // Check if response is an error (status >= 400)
      if (response.status >= 400) {
        // Try to parse error message from blob
        try {
          const text = await response.data.text()
          const errorData = JSON.parse(text)
          toast.error(errorData.detail || 'Failed to download video', { id: 'download' })
        } catch {
          toast.error('Failed to download video', { id: 'download' })
        }
        return
      }
      
      // Create download link
      const url = window.URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = `${video.title.replace(/[^a-zA-Z0-9]/g, '_')}.mp4`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      toast.success('Download started!', { id: 'download' })
    } catch (error: any) {
      console.error('Download error:', error)
      
      // Try to parse error if it's a blob
      let errorMsg = 'Failed to download video'
      if (error.response?.data) {
        if (error.response.data instanceof Blob) {
          try {
            const text = await error.response.data.text()
            const errorData = JSON.parse(text)
            errorMsg = errorData.detail || errorMsg
          } catch {
            errorMsg = error.response?.statusText || errorMsg
          }
        } else if (error.response.data.detail) {
          errorMsg = error.response.data.detail
        }
      } else if (error.message) {
        errorMsg = error.message
      }
      
      toast.error(errorMsg, { id: 'download' })
    }
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A'
    const mb = bytes / (1024 * 1024)
    return `${mb.toFixed(2)} MB`
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Show realistic progress skeleton while loading
  if (isLoading && !video) {
    return (
      <div className="mx-auto max-w-6xl p-8">
        <div className="rounded-desktop border border-white/10 bg-white/5 p-8 shadow-md backdrop-blur">
          <h3 className="mb-6 text-center text-2xl font-bold text-white">🎬 Creating Your Video</h3>
          
          {/* Show realistic progress bar */}
          <div className="max-w-2xl mx-auto mb-8">
            <div className="flex justify-between text-sm text-white/70 mb-2">
              <span className="font-semibold">Overall Progress</span>
              <span className="text-lg font-bold text-primary-200 animate-pulse">...</span>
            </div>
            <div className="h-4 overflow-hidden rounded-full bg-white/10 shadow-inner">
              <div className="relative h-full animate-pulse bg-gradient-to-r from-primary-500 via-blue-500 to-primary-600 transition-all duration-500" style={{ width: '10%' }}>
                <div className="absolute inset-0 bg-white/20" />
              </div>
            </div>
          </div>

          {/* Show 4 stages with realistic labels */}
          <div className="max-w-3xl mx-auto space-y-4">
            {/* Stage 1 - Assume active while loading */}
            <div className="rounded-desktop border-2 border-primary-400/70 bg-primary-500/10 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full border-4 border-primary-400/80 border-t-transparent animate-spin" />
                <div className="flex-1">
                  <h4 className="flex items-center gap-2 font-bold text-white">
                    <span className="text-xl">🤖</span>
                    <span>Stage 1: Generating Scene Prompts</span>
                  </h4>
                  <p className="mt-1 text-sm text-white/70 animate-pulse">
                    🔄 AI is analyzing your script and creating detailed visual descriptions...
                  </p>
                </div>
                <span className="text-sm font-bold text-primary-200">10-30%</span>
              </div>
            </div>

            {/* Stage 2 - Pending */}
            <div className="rounded-desktop border-2 border-white/10 bg-white/5 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-white/10">
                  <span className="text-xl text-white/80">2</span>
                </div>
                <div className="flex-1">
                  <h4 className="flex items-center gap-2 font-bold text-white">
                    <span className="text-xl">🖼️</span>
                    <span>Stage 2: Generating Images</span>
                  </h4>
                  <p className="mt-1 text-sm text-white/60">
                    Waiting for scene prompts...
                  </p>
                </div>
                <span className="text-sm font-bold text-white/30">30-60%</span>
              </div>
            </div>

            {/* Stage 3 - Pending */}
            <div className="rounded-desktop border-2 border-white/10 bg-white/5 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-white/10">
                  <span className="text-xl text-white/80">3</span>
                </div>
                <div className="flex-1">
                  <h4 className="flex items-center gap-2 font-bold text-white">
                    <span className="text-xl">🎤</span>
                    <span>Stage 3: Generating Audio</span>
                  </h4>
                  <p className="mt-1 text-sm text-white/60">
                    Waiting for images...
                  </p>
                </div>
                <span className="text-sm font-bold text-white/30">60-80%</span>
              </div>
            </div>

            {/* Stage 4 - Pending */}
            <div className="rounded-desktop border-2 border-white/10 bg-white/5 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-white/10">
                  <span className="text-xl text-white/80">4</span>
                </div>
                <div className="flex-1">
                  <h4 className="flex items-center gap-2 font-bold text-white">
                    <span className="text-xl">🎬</span>
                    <span>Stage 4: Rendering Final Video</span>
                  </h4>
                  <p className="mt-1 text-sm text-white/60">
                    Waiting for audio...
                  </p>
                </div>
                <span className="text-sm font-bold text-white/30">80-100%</span>
              </div>
            </div>
          </div>

          {/* Connection Status - Only show if processing */}
          {false && (
            <div className="mt-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
              <p className="text-center text-sm text-blue-200">
                {isConnected ? (
                  <>
                    <span className="inline-block w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></span>
                    Connected - Receiving real-time progress updates
                  </>
                ) : (
                  <>
                    <span className="inline-block w-2 h-2 bg-yellow-400 rounded-full mr-2 animate-pulse"></span>
                    Connecting to backend for real-time updates... (If this persists, try refreshing the page)
                  </>
                )}
              </p>
            </div>
          )}
          
          {/* Background Processing Message - Always show during loading */}
          <div className="mt-4 p-4 bg-white/5 border border-white/10 rounded-lg">
            <p className="text-center text-xs text-white/60 leading-relaxed">
              💡 <strong>Your video is being generated in the background.</strong> This process can take several minutes, especially for longer videos. 
              You can safely close this tab and return later from <button onClick={() => navigate('/my-videos')} className="underline hover:text-white">My Videos</button>.
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (!video) {
    // If still loading, show loading skeleton
    if (isLoading) {
      return (
        <div className="mx-auto max-w-6xl p-8">
          <div className="rounded-desktop border border-white/10 bg-white/5 p-8 shadow-md backdrop-blur">
            <h3 className="mb-6 text-center text-2xl font-bold text-white">🎬 Loading Video...</h3>
            <div className="text-center text-white/70">Please wait while we load your video information...</div>
          </div>
        </div>
      )
    }
    // Video not found
    return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <p className="text-gray-600">Video not found</p>
      </div>
    </div>
  )
  }

  // Check video status (handle both normalized and internal statuses)
  const statusLower = (video.status || '').toLowerCase()
  // Normalized statuses from backend: 'in_progress', 'completed', 'failed'
  // Internal statuses (for backward compatibility): 'pending', 'processing', 'generating_prompts', etc.
  const isProcessing = statusLower === 'in_progress' || 
    ['pending', 'processing', 'generating_prompts', 'generating_images', 'generating_audio', 'rendering'].includes(statusLower)
  const isCompleted = statusLower === 'completed'
  const isFailed = statusLower === 'failed'
  
  // Determine which stages are complete based on progress percentage
  // Since backend returns normalized 'in_progress' status, we use progress % to determine stages
  const progress = video.progress ?? 0
  const stage1Complete = progress >= 20  // Prompts complete
  const stage2Complete = progress >= 60  // Images complete
  const stage3Complete = progress >= 80  // Audio complete
  const stage4Complete = isCompleted
  
  // Determine active stage based on progress
  const activeStage = progress < 20 ? 1 : progress < 60 ? 2 : progress < 80 ? 3 : 4
  
  console.log('[VideoDetailPage] Video status check:', {
    status: video.status,
    statusLower,
    isProcessing,
    isCompleted,
    isFailed,
    progress: video.progress,
    activeStage
  })

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6 rounded-desktop border border-white/10 bg-white/5 p-6 shadow-sm backdrop-blur">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/my-videos')}
              className="p-2 rounded-desktop transition-colors hover:bg-white/10"
              title="Back to My Videos"
            >
              <ArrowLeft className="w-5 h-5 text-white/70" />
            </button>
            <div>
              <h1 className="text-3xl font-bold text-white">{video.title}</h1>
              {video.description && (
                <p className="mt-1 text-white/70">{video.description}</p>
              )}
            </div>
          </div>
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="flex items-center gap-2 rounded-desktop border border-red-500/40 px-4 py-2 font-medium text-red-200 transition-colors hover:bg-red-500/10 disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" />
            Delete
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Video Player / Status */}
          <div className="rounded-desktop border border-white/10 bg-white/5 shadow-md overflow-hidden">
            {isCompleted ? (
              video.video_url ? (
                <div className="relative">
                  {videoError && (
                    <div className="absolute inset-0 bg-black/80 flex items-center justify-center z-10 rounded-lg">
                      <div className="text-center p-6">
                        <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
                        <p className="text-white mb-4">{videoError}</p>
                        <a 
                          href={`/api/v1/videos/${video.id}/download`}
                          download
                          className="inline-block px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
                        >
                          Download Video Instead
                        </a>
                      </div>
                    </div>
                  )}
                  <video
                    ref={videoRef}
                    controls
                    className="w-full"
                    poster={video.thumbnail_url || undefined}
                    key={video.video_url} // Force re-render when URL changes
                    preload="auto"
                    onError={async (e) => {
                      const videoEl = e.currentTarget
                      const error = videoEl.error
                      let errorMsg = 'Failed to load video'
                      
                      if (error) {
                        switch (error.code) {
                          case error.MEDIA_ERR_ABORTED:
                            errorMsg = 'Video loading was aborted'
                            break
                          case error.MEDIA_ERR_NETWORK:
                            errorMsg = 'Network error while loading video'
                            break
                          case error.MEDIA_ERR_DECODE:
                            errorMsg = 'Video decoding error'
                            break
                          case error.MEDIA_ERR_SRC_NOT_SUPPORTED:
                            errorMsg = 'Video format not supported'
                            break
                          default:
                            errorMsg = `Video error: ${error.message || 'Unknown error'}`
                        }
                      }
                      
                      console.error('Video playback error:', {
                        error,
                        code: error?.code,
                        message: error?.message,
                        videoURL: video.video_url,
                        networkState: videoEl.networkState,
                        readyState: videoEl.readyState
                      })
                      
                      // Try loading video as blob from download endpoint
                      if (!videoBlobUrl && video.id) {
                        try {
                          console.log('Attempting to load video from download endpoint...')
                          const response = await api.get(`/videos/${video.id}/download`, {
                            responseType: 'blob',
                          })
                          const blob = new Blob([response.data], { type: 'video/mp4' })
                          const url = window.URL.createObjectURL(blob)
                          setVideoBlobUrl(url)
                          videoEl.src = url
                          setVideoError(null)
                          console.log('Video loaded successfully from download endpoint')
                          return
                        } catch (blobError) {
                          console.error('Failed to load video blob:', blobError)
                        }
                      }
                      
                      setVideoError(errorMsg)
                      toast.error(errorMsg)
                    }}
                    onLoadStart={() => {
                      console.log('Video loading started:', video.video_url)
                      setVideoError(null)
                    }}
                    onCanPlay={() => {
                      console.log('Video can play:', video.video_url)
                      setVideoError(null)
                    }}
                    onLoadedMetadata={() => {
                      console.log('Video metadata loaded:', video.video_url)
                      setVideoError(null)
                    }}
                    onLoadedData={() => {
                      console.log('Video data loaded:', video.video_url)
                      setVideoError(null)
                    }}
                  >
                    {videoBlobUrl ? (
                      <source src={videoBlobUrl} type="video/mp4" />
                    ) : (
                      <source src={video.video_url} type="video/mp4" />
                    )}
                    Your browser does not support video playback.
                  </video>
                  
                  {/* Download Button Overlay */}
                  <div className="absolute top-4 right-4">
                    <button
                      onClick={handleDownload}
                      className="px-4 py-2 bg-primary-500 text-white rounded-desktop hover:bg-primary-600 transition-all shadow-lg hover:shadow-xl flex items-center gap-2 font-semibold"
                    >
                      <Download className="w-4 h-4" />
                      Download
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-12 text-center space-y-4">
                  <div className="w-24 h-24 bg-amber-500/20 rounded-full flex items-center justify-center mx-auto">
                    <FileVideo className="w-12 h-12 text-amber-300" />
                  </div>
                  <h3 className="text-xl font-bold text-white">Video Render Complete</h3>
                  <p className="text-amber-200">The status is completed, but the video file is not available yet. This usually means the file is still being saved.</p>
                  <div className="flex items-center justify-center gap-3">
                    <button
                      onClick={loadVideo}
                      className="px-4 py-2 bg-primary-500 text-white rounded-desktop hover:bg-primary-600 transition-colors font-semibold"
                    >
                      Refresh
                    </button>
                    <button
                      onClick={handleDownload}
                      className="px-4 py-2 border border-primary-400 text-primary-200 rounded-desktop hover:bg-primary-500/10 transition-colors font-semibold"
                    >
                      Try Download
                    </button>
                  </div>
                </div>
              )
            ) : isProcessing ? (
              <div className="p-8">
                <h3 className="mb-6 text-center text-2xl font-bold text-white">🎬 Creating Your Video</h3>
                
                {/* Overall Progress Bar */}
                <div className="max-w-2xl mx-auto mb-8">
                  <div className="mb-2 flex justify-between text-sm text-white/70">
                    <span className="font-semibold">Overall Progress</span>
                    <span className="text-lg font-bold text-primary-200">{video.progress ?? 0}%</span>
                  </div>
                  <div className="h-4 overflow-hidden rounded-full bg-white/10 shadow-inner">
                    <div
                      className="relative h-full bg-gradient-to-r from-primary-500 via-blue-500 to-primary-600 transition-all duration-500 ease-out"
                      style={{ width: `${Math.max(0, Math.min(100, video.progress ?? 0))}%` }}
                    >
                      <div className="absolute inset-0 bg-white/20 animate-pulse" />
                    </div>
                  </div>
                </div>

                {/* Detailed Stage Progress */}
                <div className="max-w-3xl mx-auto space-y-4">
                  {/* Stage 1: Generating Prompts */}
                  <div className={`p-4 rounded-desktop border-2 transition-all ${
                    activeStage === 1 && isProcessing
                      ? 'border-primary-400 bg-primary-500/10'
                      : stage1Complete
                        ? 'border-green-400 bg-green-500/10'
                        : 'border-white/10 bg-white/5'
                  }`}>
                    <div className="flex items-center gap-3">
                      {stage1Complete ? (
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-green-500/80">
                          <span className="text-xl text-white">✓</span>
                        </div>
                      ) : activeStage === 1 && isProcessing ? (
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full border-4 border-primary-400/80 border-t-transparent animate-spin" />
                      ) : (
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-white/10">
                          <span className="text-xl text-white/70">1</span>
                        </div>
                      )}
                      <div className="flex-1">
                        <h4 className="flex items-center gap-2 font-bold text-white">
                          <span className="text-xl">🤖</span>
                          <span>Stage 1: Generating Scene Prompts</span>
                        </h4>
                        <p className="mt-1 text-sm text-white/70">
                          {activeStage === 1 && isProcessing
                            ? '🔄 AI is creating detailed visual descriptions for each scene...'
                            : stage1Complete
                              ? `✅ Generated ${video.scene_count || 'N/A'} scene prompts using AI`
                              : 'Waiting to start...'}
                        </p>
                      </div>
                      {stage1Complete && (
                        <span className="text-sm font-bold text-green-200">10-30%</span>
                      )}
                    </div>
                  </div>

                  {/* Stage 2: Generating Images */}
                  <div className={`p-4 rounded-desktop border-2 transition-all ${
                    activeStage === 2 && isProcessing
                      ? 'border-primary-400 bg-primary-500/10'
                      : stage2Complete
                        ? 'border-green-400 bg-green-500/10'
                        : 'border-white/10 bg-white/5'
                  }`}>
                    <div className="flex items-center gap-3">
                      {stage2Complete ? (
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-green-500/80">
                          <span className="text-xl text-white">✓</span>
                        </div>
                      ) : activeStage === 2 && isProcessing ? (
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full border-4 border-primary-400/80 border-t-transparent animate-spin" />
                      ) : (
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-white/10">
                          <span className="text-xl text-white/70">2</span>
                        </div>
                      )}
                      <div className="flex-1">
                        <h4 className="flex items-center gap-2 font-bold text-white">
                          <span className="text-xl">🖼️</span>
                          <span>Stage 2: Generating Images</span>
                        </h4>
                        <p className="mt-1 text-sm text-white/70">
                          {activeStage === 2 && isProcessing
                            ? `🔄 Creating beautiful ${video.style ? humanize(video.style) : 'AI-generated'} visuals for ${video.scene_count ?? 'N/A'} scenes...`
                            : stage2Complete
                              ? `✅ Generated ${video.scene_count ?? 'N/A'} high-quality images using ${getImageServiceLabel(video.image_service)}${video.image_model ? ` • ${getImageModelLabel(video.image_service, video.image_model)}` : ''}`
                              : 'Waiting for prompts...'}
                        </p>
                      </div>
                      {stage2Complete && (
                        <span className="text-sm font-bold text-green-200">30-60%</span>
                      )}
                    </div>
                  </div>

                  {/* Stage 3: Generating Audio */}
                  <div className={`p-4 rounded-desktop border-2 transition-all ${
                    activeStage === 3 && isProcessing
                      ? 'border-primary-400 bg-primary-500/10'
                      : stage3Complete
                        ? 'border-green-400 bg-green-500/10'
                        : 'border-white/10 bg-white/5'
                  }`}>
                    <div className="flex items-center gap-3">
                      {stage3Complete ? (
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-green-500/80">
                          <span className="text-xl text-white">✓</span>
                        </div>
                      ) : activeStage === 3 && isProcessing ? (
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full border-4 border-primary-400/80 border-t-transparent animate-spin" />
                      ) : (
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-white/10">
                          <span className="text-xl text-white/70">3</span>
                        </div>
                      )}
                      <div className="flex-1">
                        <h4 className="flex items-center gap-2 font-bold text-white">
                          <span className="text-xl">🎤</span>
                          <span>Stage 3: Generating Audio</span>
                        </h4>
                        <p className="mt-1 text-sm text-white/70">
                          {activeStage === 3 && isProcessing
                            ? `🔄 Converting script to natural-sounding voice narration with ${getTtsServiceLabel(video.tts_provider)}${video.tts_model ? ` • ${humanize(video.tts_model)}` : ''}...`
                            : stage3Complete
                              ? `✅ Generated voice narration for ${video.scene_count ?? 'N/A'} scenes using ${getTtsServiceLabel(video.tts_provider)}${video.tts_voice ? ` • ${getTtsVoiceLabel(video.tts_voice)}` : ''}`
                              : 'Waiting for images...'}
                        </p>
                      </div>
                      {stage3Complete && (
                        <span className="text-sm font-bold text-green-200">60-80%</span>
                      )}
                    </div>
                  </div>

                  {/* Stage 4: Rendering Video */}
                  <div className={`p-4 rounded-desktop border-2 transition-all ${
                    activeStage === 4 && isProcessing
                      ? 'border-primary-400 bg-primary-500/10'
                      : stage4Complete
                        ? 'border-green-400 bg-green-500/10'
                        : 'border-white/10 bg-white/5'
                  }`}>
                    <div className="flex items-center gap-3">
                      {stage4Complete ? (
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-green-500/80">
                          <span className="text-xl text-white">✓</span>
                        </div>
                      ) : activeStage === 4 && isProcessing ? (
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full border-4 border-primary-400/80 border-t-transparent animate-spin" />
                      ) : (
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-white/10">
                          <span className="text-xl text-white/70">4</span>
                        </div>
                      )}
                      <div className="flex-1">
                        <h4 className="flex items-center gap-2 font-bold text-white">
                          <span className="text-xl">🎬</span>
                          <span>Stage 4: Rendering Final Video</span>
                        </h4>
                        <p className="mt-1 text-sm text-white/70">
                          {activeStage === 4 && isProcessing
                            ? '🔄 Combining images, audio, and effects into final video with FFmpeg...'
                            : stage4Complete
                              ? '✅ Video rendered successfully! Ready to watch and download.'
                              : 'Waiting for audio...'}
                        </p>
                      </div>
                      {stage4Complete && (
                        <span className="text-sm font-bold text-green-200">80-100%</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Live Log Area */}
                <div className="mt-8 max-w-3xl mx-auto">
                  <div className="bg-black/40 border border-white/10 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-semibold text-white/80 flex items-center gap-2">
                        <span>📋</span>
                        Live Activity Log
                      </h4>
                      <span className="text-xs text-white/50">
                        {logMessages.length} {logMessages.length === 1 ? 'message' : 'messages'}
                      </span>
                    </div>
                    <div className="bg-black/60 rounded p-3 font-mono text-xs text-green-300/80 h-32 overflow-y-auto space-y-1">
                      {logMessages.length > 0 ? (
                        logMessages.map((msg, idx) => (
                          <div key={idx} className="whitespace-pre-wrap">{msg}</div>
                        ))
                      ) : (
                        <div className="text-white/40 italic">
                          Waiting for activity updates...
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                
                {/* Estimated Time Remaining */}
                <div className="mt-6 text-center">
                  <p className="text-sm text-white/60">
                    ⏱️ Estimated time: {
                      (video.progress ?? 0) < 30 ? '45-60 seconds remaining' :
                      (video.progress ?? 0) < 60 ? '30-45 seconds remaining' :
                      (video.progress ?? 0) < 80 ? '15-30 seconds remaining' :
                      (video.progress ?? 0) < 100 ? '10-15 seconds remaining' :
                      'Complete!'
                    }
                  </p>
                </div>
                
                {/* Connection Status */}
                <div className="mt-4 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                  <p className="text-center text-sm text-blue-200">
                    {isConnected ? (
                      <>
                        <span className="inline-block w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></span>
                        Connected - Receiving real-time progress updates
                      </>
                    ) : (
                      <>
                        <span className="inline-block w-2 h-2 bg-yellow-400 rounded-full mr-2 animate-pulse"></span>
                        Using polling for updates... {video.progress === 0 ? '(Video generation starting...)' : ''}
                      </>
                    )}
                  </p>
                </div>
                
                {/* Background Processing Message */}
                <div className="mt-4 p-4 bg-white/5 border border-white/10 rounded-lg">
                  <p className="text-center text-xs text-white/60 leading-relaxed">
                    💡 <strong>Your video is being generated in the background.</strong> This process can take several minutes, especially for longer videos. 
                    You can safely close this tab and return later from <button onClick={() => navigate('/my-videos')} className="underline hover:text-white">My Videos</button>.
                  </p>
                </div>
              </div>
            ) : isFailed ? (
              <div className="p-12 text-center">
                <div className="w-24 h-24 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4 border-2 border-red-500/50">
                  <XCircle className="w-12 h-12 text-red-400" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">Video Generation Failed</h3>
                <p className="text-red-300 mb-6 max-w-md mx-auto">
                  {video.error_message || 'An error occurred during video generation. Please try again or contact support if the issue persists.'}
                </p>
                <div className="flex items-center justify-center gap-3">
                <button
                  onClick={() => navigate('/create')}
                    className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-semibold flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                    Create New Video
                  </button>
                  <button
                    onClick={() => navigate('/my-videos')}
                    className="px-6 py-3 bg-white/10 text-white rounded-lg hover:bg-white/20 transition-colors font-semibold"
                  >
                    View My Videos
                </button>
                </div>
              </div>
            ) : (
              <div className="p-12 text-center">
                <div className="w-24 h-24 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <FileVideo className="w-12 h-12 text-white/60" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">Video Pending</h3>
                <p className="text-white/70">Your video is queued for generation</p>
              </div>
            )}
          </div>

          {/* Script */}
          <div className="rounded-desktop border border-white/10 bg-white/5 p-6 shadow-md">
            <h3 className="mb-4 flex items-center gap-2 text-lg font-bold text-white">
              <FileText className="w-5 h-5 text-primary-500" />
              Script
            </h3>
            <div className="rounded-desktop border border-white/10 bg-white/5 p-4">
              <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-white/80">
                {video.script}
              </pre>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Video Info */}
          <div className="rounded-desktop border border-white/10 bg-white/5 p-6 shadow-md">
            <h3 className="mb-4 text-lg font-bold text-white">Video Information</h3>
            <dl className="space-y-3 text-white/80">
              <div>
                <dt className="text-sm text-white/60">Style</dt>
                <dd className="text-sm font-semibold text-white capitalize">{video.style.replace(/_/g, ' ')}</dd>
              </div>
              <div>
                <dt className="text-sm text-white/60">Resolution</dt>
                <dd className="text-sm font-semibold text-white">{video.resolution}</dd>
              </div>
              <div>
                <dt className="text-sm text-white/60">Orientation</dt>
                <dd className="text-sm font-semibold text-white capitalize">{video.orientation}</dd>
              </div>
              <div>
                <dt className="text-sm text-white/60">Image Provider</dt>
                <dd className="text-sm font-semibold text-white">
                  {getImageServiceLabel(video.image_service)}
                  {video.image_model ? ` • ${getImageModelLabel(video.image_service, video.image_model)}` : ''}
                </dd>
              </div>
              {video.ai_provider && (
                <div>
                  <dt className="text-sm text-white/60">Prompt AI</dt>
                  <dd className="text-sm font-semibold text-white">{humanize(video.ai_provider)}</dd>
                </div>
              )}
              {video.tts_provider && (
                <div>
                  <dt className="text-sm text-white/60">Voice Provider</dt>
                  <dd className="text-sm font-semibold text-white">
                    {humanize(video.tts_provider)}
                    {video.tts_voice ? ` • ${getTtsVoiceLabel(video.tts_voice)}` : ''}
                  </dd>
                </div>
              )}
              {(video.transition_type && video.transition_type !== 'none') && (
                <div>
                  <dt className="text-sm text-white/60">Transition</dt>
                  <dd className="text-sm font-semibold text-white">
                    {getTransitionLabel(video.transition_type)}
                    {video.transition_duration ? ` • ${video.transition_duration.toFixed(1)}s` : ''}
                  </dd>
                </div>
              )}
              <div>
                <dt className="text-sm text-white/60 flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  Duration
                </dt>
                <dd className="text-sm font-semibold text-white">{formatDuration(video.duration)}</dd>
              </div>
              <div>
                <dt className="text-sm text-white/60">File Size</dt>
                <dd className="text-sm font-semibold text-white">{formatFileSize(video.file_size)}</dd>
              </div>
              <div>
                <dt className="text-sm text-white/60">Scenes</dt>
                <dd className="text-sm font-semibold text-white">{video.scene_count || 'N/A'}</dd>
              </div>
              <div>
                <dt className="text-sm text-white/60">Status</dt>
                <dd className={`text-sm font-bold ${
                  isCompleted ? 'text-green-600' : 
                  isProcessing ? 'text-blue-600' : 
                  isFailed ? 'text-red-600' : 
                  'text-gray-600'
                }`}>
                  {getStatusBadge(video.status)}
                </dd>
              </div>
            </dl>
          </div>

          {/* Actions */}
          {isCompleted && (
            <div className="rounded-desktop border border-white/10 bg-white/5 p-6 shadow-md backdrop-blur space-y-3">
              <button
                onClick={handleDownload}
                className="w-full px-4 py-3 bg-primary-500 text-white rounded-desktop hover:bg-primary-600 transition-all font-semibold flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
              >
                <Download className="w-5 h-5" />
                Download Video
              </button>
              <button
                onClick={() => toast.success('Share feature coming soon!')}
                className="w-full px-4 py-3 bg-white/10 text-primary-200 border-2 border-primary-400 rounded-desktop hover:bg-primary-500/10 transition-all font-semibold flex items-center justify-center gap-2"
              >
                <Share2 className="w-5 h-5" />
                Share Video
              </button>
            </div>
          )}

          {/* Create Another */}
          <button
            onClick={() => navigate('/create')}
            className="w-full px-4 py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-desktop hover:from-green-600 hover:to-emerald-700 transition-all font-semibold flex items-center justify-center gap-2 shadow-lg"
          >
            <Play className="w-5 h-5" />
            Create Another Video
          </button>
        </div>
      </div>
    </div>
  )
}

function getStatusBadge(status: string): string {
  const badgeMap: Record<string, string> = {
    PENDING: '⏳ Pending',
    PROCESSING: '🔄 Processing',
    GENERATING_PROMPTS: '🤖 Generating Prompts',
    GENERATING_IMAGES: '🖼️ Creating Images',
    GENERATING_AUDIO: '🎤 Adding Voice',
    RENDERING: '🎬 Rendering',
    COMPLETED: '✅ Completed',
    FAILED: '❌ Failed'
  }
  return badgeMap[status] || status
}

