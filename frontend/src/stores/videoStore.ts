/**
 * Zustand store for video state management.
 * Manages the list of user videos and provides actions to fetch/update them.
 */

import { create } from 'zustand'
import { createVideo, getVideo, getVideoStatus, listVideos, deleteVideo, downloadVideo } from '../services/videoService'
import type { Video, VideoListResponse } from '../services/videoService'

interface VideoState {
  videos: Video[]
  loading: boolean
  error: string | null
  lastFetched: number | null
  
  // Actions
  fetchVideos: (params?: { page?: number; page_size?: number; status?: string }) => Promise<void>
  refreshVideos: () => Promise<void>
  addVideo: (video: Video) => void
  updateVideo: (id: number, updates: Partial<Video>) => void
  removeVideo: (id: number) => void
  clearError: () => void
}

export const useVideoStore = create<VideoState>((set, get) => ({
  videos: [],
  loading: false,
  error: null,
  lastFetched: null,

  fetchVideos: async (params) => {
    set({ loading: true, error: null })
    try {
      const response: VideoListResponse = await listVideos(params)
      set({
        videos: response.videos,
        loading: false,
        lastFetched: Date.now(),
      })
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to fetch videos',
        loading: false,
      })
    }
  },

  refreshVideos: async () => {
    await get().fetchVideos()
  },

  addVideo: (video) => {
    set((state) => ({
      videos: [video, ...state.videos],
    }))
  },

  updateVideo: (id, updates) => {
    set((state) => ({
      videos: state.videos.map((v) =>
        v.id === id ? { ...v, ...updates } : v
      ),
    }))
  },

  removeVideo: (id) => {
    set((state) => ({
      videos: state.videos.filter((v) => v.id !== id),
    }))
  },

  clearError: () => {
    set({ error: null })
  },
}))

