/**
 * Video service for API calls related to videos.
 * Centralizes all video-related API interactions.
 */

import api from './api'

/**
 * User-facing video status values returned by the backend API.
 * Backend normalizes internal statuses (pending, processing, generating_prompts, etc.)
 * to these three user-facing values.
 */
export type NormalizedVideoStatus = 'in_progress' | 'completed' | 'failed'

export interface Video {
  id: number
  title: string
  description?: string
  script: string
  style: string
  resolution: string
  orientation: string
  status: NormalizedVideoStatus  // Normalized status: "in_progress", "completed", or "failed"
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
  updated_at?: string
  completed_at?: string
  transition_type?: string
  transition_duration?: number
  image_animation?: string
  image_animation_intensity?: number
  rendering_preset?: string
}

export interface VideoStatusResponse {
  id: number
  status: NormalizedVideoStatus  // Normalized status: "in_progress", "completed", or "failed"
  progress: number
  error_message?: string | null
  video_url?: string | null
  current_step?: string | null
  estimated_time_remaining?: number | null
  scene_count?: number | null
  current_scene?: number | null
}

export interface VideoListResponse {
  videos: Video[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface VideoCreateData {
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
  subtitle_style?: {
    enabled?: boolean
    font_size?: number
    position?: string
    text_color?: string
    bg_opacity?: number
    outline_width?: number
  }
}

/**
 * Create a new video generation job.
 */
export const createVideo = async (data: VideoCreateData): Promise<Video> => {
  const response = await api.post<Video>('/videos/', data)
  return response.data
}

/**
 * Get a single video by ID.
 */
export const getVideo = async (id: number): Promise<Video> => {
  const response = await api.get<Video>(`/videos/${id}`)
  return response.data
}

/**
 * Get video status (lightweight endpoint for polling).
 * Returns normalized status: "in_progress", "completed", or "failed"
 */
export const getVideoStatus = async (id: number): Promise<VideoStatusResponse> => {
  const response = await api.get<VideoStatusResponse>(`/videos/${id}/status`)
  return response.data
}

/**
 * List all videos for the current user.
 */
export const listVideos = async (params?: {
  page?: number
  page_size?: number
  status?: string
}): Promise<VideoListResponse> => {
  const response = await api.get<VideoListResponse>('/videos/', { params })
  return response.data
}

/**
 * Delete a video.
 */
export const deleteVideo = async (id: number): Promise<void> => {
  await api.delete(`/videos/${id}`)
}

/**
 * Download a video (returns blob URL).
 */
export const downloadVideo = async (id: number): Promise<string> => {
  const response = await api.get(`/videos/${id}/download`, {
    responseType: 'blob',
  })
  
  // Create a blob URL for download
  const blob = new Blob([response.data], { type: 'video/mp4' })
  const url = window.URL.createObjectURL(blob)
  return url
}


