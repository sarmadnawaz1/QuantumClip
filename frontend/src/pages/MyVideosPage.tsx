/**
 * My Videos Dashboard Page
 * 
 * Displays all videos for the current user with:
 * - Status indicators
 * - Progress bars for in-progress videos
 * - Thumbnails
 * - Actions (View, Download, Delete)
 * - Filtering and sorting
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Video as VideoIcon, 
  Download, 
  Trash2, 
  Eye, 
  Filter,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  FileVideo
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useVideoStore } from '../stores/videoStore'
import { deleteVideo, downloadVideo, Video } from '../services/videoService'
import { formatDistanceToNow } from 'date-fns'
import api from '../services/api'

type StatusFilter = 'all' | 'in_progress' | 'completed' | 'failed'

export default function MyVideosPage() {
  const navigate = useNavigate()
  const { videos, loading, error, fetchVideos, removeVideo, refreshVideos } = useVideoStore()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [isDeleting, setIsDeleting] = useState<number | null>(null)

  useEffect(() => {
    // Fetch videos on mount
    fetchVideos({ page_size: 100 }).catch((err) => {
      console.error('Failed to fetch videos:', err)
      toast.error('Failed to load videos. Please try again.')
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run once on mount
  
  // Poll for status updates if there are any in-progress videos
  useEffect(() => {
    const hasInProgressVideos = videos.some(v => {
      const statusLower = v.status.toLowerCase()
      return statusLower === 'in_progress' || 
             ['pending', 'processing', 'generating_prompts', 'generating_images', 'generating_audio', 'rendering'].includes(statusLower)
    })
    
    if (!hasInProgressVideos) {
      return // No need to poll if all videos are completed/failed
    }
    
    // Poll every 10 seconds for status updates
    const pollInterval = setInterval(() => {
      refreshVideos().catch((err) => {
        console.error('Failed to refresh videos during polling:', err)
        // Don't show error toast for polling failures to avoid spam
      })
    }, 10000) // Poll every 10 seconds
    
    return () => clearInterval(pollInterval)
  }, [videos, refreshVideos])

  const handleDelete = async (videoId: number, title: string) => {
    if (!confirm(`Are you sure you want to delete "${title}"? This action cannot be undone.`)) {
      return
    }

    setIsDeleting(videoId)
    try {
      await deleteVideo(videoId)
      removeVideo(videoId)
      toast.success('Video deleted successfully')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete video')
    } finally {
      setIsDeleting(null)
    }
  }

  const handleDownload = async (video: Video) => {
    if (!video.video_url) {
      toast.error('Video not available for download')
      return
    }

    try {
      toast.loading('Preparing download...', { id: 'download' })
      const url = await downloadVideo(video.id)
      
      // Create temporary link and trigger download
      const link = document.createElement('a')
      link.href = url
      link.download = `${video.title || 'video'}.mp4`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      // Clean up blob URL after a delay
      setTimeout(() => window.URL.revokeObjectURL(url), 100)
      
      toast.success('Download started', { id: 'download' })
    } catch (error: any) {
      toast.error('Failed to download video', { id: 'download' })
    }
  }

  /**
   * Get status badge component for a video.
   * 
   * Backend now returns normalized status values:
   * - "in_progress" (for all processing states: pending, processing, generating_prompts, etc.)
   * - "completed" (for completed videos)
   * - "failed" (for failed/cancelled videos)
   * 
   * This function maps these normalized values to UI badges.
   */
  const getStatusBadge = (status: string) => {
    const statusLower = status.toLowerCase()
    
    // Completed status
    if (statusLower === 'completed') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-green-500/20 text-green-300 border border-green-500/30">
          <CheckCircle2 className="w-3.5 h-3.5" />
          Completed
        </span>
      )
    }
    
    // Failed status (includes cancelled)
    if (statusLower === 'failed' || statusLower === 'cancelled') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/20 text-red-300 border border-red-500/30">
          <XCircle className="w-3.5 h-3.5" />
          Failed
        </span>
      )
    }
    
    // In progress status (normalized from backend, or fallback for old/internal statuses)
    if (statusLower === 'in_progress' || 
        ['pending', 'processing', 'generating_prompts', 'generating_images', 'generating_audio', 'rendering'].includes(statusLower)) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          In Progress
        </span>
      )
    }
    
    // Fallback for unknown statuses (shouldn't happen with normalized statuses)
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-500/20 text-gray-300 border border-gray-500/30">
        {status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
      </span>
    )
  }

  /**
   * Filter videos by status.
   * 
   * Backend returns normalized status values: "in_progress", "completed", "failed"
   * This filter matches against these normalized values.
   */
  const filteredVideos = videos.filter((video) => {
    if (statusFilter === 'all') return true
    
    const statusLower = video.status.toLowerCase()
    
    if (statusFilter === 'completed') {
      return statusLower === 'completed'
    }
    
    if (statusFilter === 'failed') {
      return statusLower === 'failed' || statusLower === 'cancelled'
    }
    
    if (statusFilter === 'in_progress') {
      // Match normalized "in_progress" or any processing state (fallback for old data)
      return statusLower === 'in_progress' || 
             ['pending', 'processing', 'generating_prompts', 'generating_images', 'generating_audio', 'rendering'].includes(statusLower)
    }
    
    return true
  })

  // Sort by created_at (newest first)
  const sortedVideos = [...filteredVideos].sort((a, b) => {
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })

  const formatDate = (dateString: string) => {
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true })
    } catch {
      return dateString
    }
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A'
    const mb = bytes / (1024 * 1024)
    return `${mb.toFixed(2)} MB`
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold mb-2 flex items-center gap-3">
                <VideoIcon className="w-10 h-10 text-indigo-400" />
                My Videos
              </h1>
              <p className="text-white/70">
                Manage and view all your generated videos
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => refreshVideos()}
                disabled={loading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              {sortedVideos.length > 0 && (
                <button
                  onClick={async () => {
                    if (!confirm(`Are you sure you want to delete ALL ${sortedVideos.length} videos? This action cannot be undone.`)) {
                      return
                    }
                    try {
                      await api.delete('/videos/all')
                      toast.success('All videos deleted successfully')
                      await fetchVideos({ page_size: 100 })
                    } catch (error: any) {
                      toast.error(error.response?.data?.detail || 'Failed to delete all videos')
                    }
                  }}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete All
                </button>
              )}
              <button
                onClick={() => navigate('/create')}
                className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white rounded-lg transition-all shadow-lg shadow-indigo-500/50"
              >
                Create New Video
              </button>
            </div>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-3 flex-wrap">
            <Filter className="w-5 h-5 text-white/70" />
            <span className="text-sm text-white/70">Filter:</span>
            {(['all', 'in_progress', 'completed', 'failed'] as StatusFilter[]).map((filter) => (
              <button
                key={filter}
                onClick={() => setStatusFilter(filter)}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  statusFilter === filter
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white/10 text-white/70 hover:bg-white/20'
                }`}
              >
                {filter === 'all' ? 'All Videos' : filter === 'in_progress' ? 'In Progress' : filter.charAt(0).toUpperCase() + filter.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-200">
            {error}
            <button
              onClick={() => refreshVideos()}
              className="ml-4 underline hover:text-red-100"
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading State */}
        {loading && videos.length === 0 && (
          <div className="text-center py-12">
            <Loader2 className="w-12 h-12 animate-spin text-indigo-400 mx-auto mb-4" />
            <p className="text-white/70">Loading your videos...</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && sortedVideos.length === 0 && (
          <div className="text-center py-16 bg-white/5 rounded-2xl border border-white/10">
            <VideoIcon className="w-16 h-16 text-white/30 mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">No videos found</h3>
            <p className="text-white/60 mb-6">
              {statusFilter === 'all'
                ? "You haven't created any videos yet. Get started by creating your first video!"
                : `No ${statusFilter === 'in_progress' ? 'in progress' : statusFilter} videos found.`}
            </p>
            {statusFilter === 'all' && (
              <button
                onClick={() => navigate('/create')}
                className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white rounded-lg transition-all shadow-lg shadow-indigo-500/50"
              >
                Create Your First Video
              </button>
            )}
          </div>
        )}

        {/* Video Grid */}
        {sortedVideos.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {sortedVideos.map((video) => (
              <div
                key={video.id}
                className="bg-white/5 rounded-xl border border-white/10 overflow-hidden hover:border-indigo-500/50 transition-all group"
              >
                {/* Thumbnail */}
                <div className="relative aspect-video bg-gradient-to-br from-indigo-900/20 to-purple-900/20 overflow-hidden">
                  {video.thumbnail_url ? (
                    <img
                      src={video.thumbnail_url}
                      alt={video.title}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <FileVideo className="w-16 h-16 text-white/20" />
                    </div>
                  )}
                  
                  {/* Status Badge Overlay */}
                  <div className="absolute top-3 right-3">
                    {getStatusBadge(video.status)}
                  </div>

                  {/* Progress Bar for In-Progress Videos */}
                  {video.status.toLowerCase() === 'in_progress' || 
                   (video.status.toLowerCase() !== 'completed' && 
                    video.status.toLowerCase() !== 'failed' && 
                    video.status.toLowerCase() !== 'cancelled') && (
                    <div className="absolute bottom-0 left-0 right-0 bg-black/50 p-2">
                      <div className="flex items-center justify-between text-xs text-white/90 mb-1">
                        <span>{video.progress.toFixed(0)}%</span>
                        <span>{video.progress < 30 ? 'Generating...' : video.progress < 80 ? 'Rendering...' : 'Finalizing...'}</span>
                      </div>
                      <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-300"
                          style={{ width: `${video.progress}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="p-4">
                  <h3 className="font-semibold text-lg mb-2 line-clamp-2 min-h-[3rem]">
                    {video.title || 'Untitled Video'}
                  </h3>
                  
                  <div className="space-y-2 text-sm text-white/60 mb-4">
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      <span>{formatDate(video.created_at)}</span>
                    </div>
                    {video.duration && (
                      <div className="flex items-center gap-2">
                        <VideoIcon className="w-4 h-4" />
                        <span>{formatDuration(video.duration)}</span>
                        {video.file_size && <span className="text-white/40">• {formatFileSize(video.file_size)}</span>}
                      </div>
                    )}
                    {video.scene_count && (
                      <div className="text-white/50">
                        {video.scene_count} scene{video.scene_count !== 1 ? 's' : ''}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => navigate(`/videos/${video.id}`)}
                      className="flex-1 px-3 py-2 bg-indigo-600/80 hover:bg-indigo-600 text-white rounded-lg transition-colors text-sm font-medium flex items-center justify-center gap-2"
                    >
                      <Eye className="w-4 h-4" />
                      View
                    </button>
                    
                    {video.status.toLowerCase() === 'completed' && video.video_url && (
                      <button
                        onClick={() => handleDownload(video)}
                        className="px-3 py-2 bg-green-600/80 hover:bg-green-600 text-white rounded-lg transition-colors"
                        title="Download"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                    )}
                    
                    <button
                      onClick={() => handleDelete(video.id, video.title)}
                      disabled={isDeleting === video.id}
                      className="px-3 py-2 bg-red-600/80 hover:bg-red-600 text-white rounded-lg transition-colors disabled:opacity-50"
                      title="Delete"
                    >
                      {isDeleting === video.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Stats Footer */}
        {videos.length > 0 && (
          <div className="mt-8 p-4 bg-white/5 rounded-lg border border-white/10 text-center text-sm text-white/70">
            Showing {sortedVideos.length} of {videos.length} video{sortedVideos.length !== 1 ? 's' : ''}
            {statusFilter !== 'all' && ` (filtered by ${statusFilter})`}
          </div>
        )}
      </div>
    </div>
  )
}

