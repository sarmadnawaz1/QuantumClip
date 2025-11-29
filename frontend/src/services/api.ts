import axios from 'axios'

// Use relative URL to leverage Vite proxy in development
// In production, VITE_API_URL should be set to the backend URL
// If VITE_API_URL is set, use it directly; otherwise use relative path for proxy
export const API_URL = import.meta.env.VITE_API_URL || ''
const baseURL = API_URL ? `${API_URL}/api/v1` : '/api/v1'

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false, // Don't send cookies for CORS
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    // Read token from localStorage to avoid circular dependency with authStore
    try {
      const storageItem = localStorage.getItem('auth-storage')
      if (storageItem) {
        const { state } = JSON.parse(storageItem)
        if (state && state.token) {
          config.headers.Authorization = `Bearer ${state.token}`
        }
      }
    } catch (error) {
      console.error('Error reading token from storage:', error)
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle 401 Unauthorized (token expired or invalid)
    if (error.response?.status === 401) {
      console.warn('[api] 401 Unauthorized - clearing auth state')
      
      // Token expired or invalid
      // We can't use authStore.getState().logout() here due to circular dependency
      // So we manually clear storage and redirect
      try {
        const storageItem = localStorage.getItem('auth-storage')
        if (storageItem) {
          const parsed = JSON.parse(storageItem)
          // Reset auth state in storage (keep structure for Zustand)
          const newState = { 
            ...parsed, 
            state: { 
              ...parsed.state, 
              token: null, 
              isAuthenticated: false, 
              user: null 
            } 
          }
          localStorage.setItem('auth-storage', JSON.stringify(newState))
        }
      } catch (e) {
        console.error('[api] Error clearing auth storage:', e)
        // Fallback: remove entire storage item
        localStorage.removeItem('auth-storage')
      }

      // Only redirect if we're not already on the login or register page
      const currentPath = window.location.pathname
      if (!currentPath.includes('/login') && 
          !currentPath.includes('/register') && 
          !currentPath.includes('/verify-email')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api

