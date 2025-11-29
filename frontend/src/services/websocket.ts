/**
 * WebSocket service for real-time video progress updates.
 */

import { API_URL } from './api'

export interface VideoProgressMessage {
  type: 'connected' | 'progress' | 'pong'
  video_id: number
  status: string
  progress: number
  current_step?: string | null
  error_message?: string | null
  scene_count?: number | null
  current_scene?: number | null
}

export type ProgressCallback = (message: VideoProgressMessage) => void

class VideoProgressWebSocket {
  private ws: WebSocket | null = null
  private videoId: number | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private callbacks: Set<ProgressCallback> = new Set()
  private pingInterval: number | null = null

  connect(videoId: number, token: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN && this.videoId === videoId) {
      console.log(`[WebSocket] Already connected to video ${videoId}`)
      return
    }

    this.disconnect()
    this.videoId = videoId
    this.reconnectAttempts = 0

    // Determine WebSocket URL
    // In development, use Vite proxy (connect to same origin, Vite will proxy to backend)
    // In production, use API_URL or current host
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    let wsHost: string
    
    if (import.meta.env.DEV) {
      // Development: use Vite proxy (connect to same origin, Vite will proxy)
      wsHost = window.location.host
    } else {
      // Production: use API_URL or current host
      if (API_URL) {
        wsHost = API_URL.replace(/^https?:\/\//, '').replace(/^wss?:\/\//, '')
      } else {
        wsHost = window.location.host
      }
    }
    
    const wsUrl = `${wsProtocol}//${wsHost}/api/v1/videos/${videoId}/progress?token=${encodeURIComponent(token)}`

    console.log(`[WebSocket] Connecting to video ${videoId}...`)

    try {
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log(`[WebSocket] Connected to video ${videoId}`)
        this.reconnectAttempts = 0
        
        // Start ping interval to keep connection alive
        this.pingInterval = window.setInterval(() => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send('ping')
          }
        }, 30000) // Ping every 30 seconds
      }

      this.ws.onmessage = (event) => {
        try {
          const message: VideoProgressMessage = JSON.parse(event.data)
          
          // Handle pong
          if (message.type === 'pong') {
            return
          }

          // Notify all callbacks
          this.callbacks.forEach(callback => {
            try {
              callback(message)
            } catch (error) {
              console.error('[WebSocket] Error in progress callback:', error)
            }
          })
        } catch (error) {
          console.error('[WebSocket] Error parsing message:', error, event.data)
        }
      }

      this.ws.onerror = (error) => {
        console.error(`[WebSocket] Error for video ${videoId}:`, error)
      }

      this.ws.onclose = (event) => {
        console.log(`[WebSocket] Disconnected from video ${videoId}`, event.code, event.reason)
        
        if (this.pingInterval) {
          clearInterval(this.pingInterval)
          this.pingInterval = null
        }

        // Attempt to reconnect if not a normal closure and we haven't exceeded max attempts
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
          console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)
          
          setTimeout(() => {
            if (this.videoId && token) {
              this.connect(this.videoId, token)
            }
          }, delay)
        } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          console.error(`[WebSocket] Max reconnection attempts reached for video ${videoId}`)
          // Notify callbacks of disconnection
          this.callbacks.forEach(callback => {
            try {
              callback({
                type: 'progress',
                video_id: videoId,
                status: 'disconnected',
                progress: 0,
                current_step: 'Connection lost. Please refresh the page.',
              })
            } catch (error) {
              console.error('[WebSocket] Error in disconnect callback:', error)
            }
          })
        }
      }
    } catch (error) {
      console.error(`[WebSocket] Failed to create connection:`, error)
    }
  }

  disconnect(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }

    this.videoId = null
    this.reconnectAttempts = 0
  }

  onProgress(callback: ProgressCallback): () => void {
    this.callbacks.add(callback)
    
    // Return unsubscribe function
    return () => {
      this.callbacks.delete(callback)
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  getVideoId(): number | null {
    return this.videoId
  }
}

// Singleton instance
export const videoProgressWS = new VideoProgressWebSocket()

