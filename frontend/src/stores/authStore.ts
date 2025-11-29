/**
 * Authentication Store
 * 
 * Manages authentication state and API calls for login/register.
 * 
 * Token Storage:
 * - Tokens are stored in localStorage via Zustand persist middleware
 * - Token is added to API requests via axios interceptor (see api.ts)
 * 
 * Auth Flow:
 * 1. Register: POST /auth/register with {email, username, password, full_name?}
 *    - Returns: UserResponse (no token - user must verify email)
 *    - Redirects to email verification page
 * 
 * 2. Login: POST /auth/login with {email, password}
 *    - Returns: {access_token, refresh_token, token_type: "bearer"}
 *    - Stores token in Zustand state (persisted to localStorage)
 *    - Loads user data via GET /users/me
 *    - Redirects to home/dashboard
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../services/api'

interface User {
  id: number
  email: string
  username: string
  full_name?: string
  avatar_url?: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: { email: string; username: string; password: string; full_name?: string }) => Promise<{ email: string }>
  logout: () => void
  loadUser: () => Promise<void>
  verifyEmail: (email: string, code: string) => Promise<void>
  resendVerification: (email: string) => Promise<void>
  forgotPassword: (email: string) => Promise<void>
  resetPassword: (email: string, code: string, newPassword: string) => Promise<void>
  getGoogleAuthUrl: () => Promise<string>
  googleLogin: (code: string, state?: string) => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: async (email: string, password: string) => {
        try {
          // Backend expects: {email, password}
          // Backend returns: {access_token, refresh_token, token_type: "bearer"}
          const response = await api.post('/auth/login', { email, password })
          
          // Validate response structure
          if (!response.data || !response.data.access_token) {
            console.error('[authStore] Invalid login response:', response.data)
            throw new Error('Invalid response from server. Please try again.')
          }
          
          const { access_token } = response.data
          
          // Store token and update auth state
          set({ token: access_token, isAuthenticated: true })
          
          // Load user data (this will update the user in state)
          await get().loadUser()
        } catch (error: any) {
          // Preserve original error message from backend
          const errorMessage = error.response?.data?.detail || error.message || 'Login failed'
          console.error('[authStore] Login error:', {
            error,
            response: error?.response?.data,
            message: errorMessage
          })
          throw new Error(errorMessage)
        }
      },

      register: async (data) => {
        try {
          // Backend expects: {email, username, password, full_name?}
          // Backend returns: UserResponse (no token - user must verify email)
          const response = await api.post('/auth/register', data)
          
          // Validate response structure
          if (!response.data || !response.data.email) {
            console.error('[authStore] Invalid register response:', response.data)
            throw new Error('Invalid response from server. Please try again.')
          }
          
          // Return email for verification page (don't auto-login)
          return { email: data.email }
        } catch (error: any) {
          // Preserve original error message from backend
          const errorMessage = error.response?.data?.detail || error.message || 'Registration failed'
          console.error('[authStore] Registration error:', {
            error,
            response: error?.response?.data,
            message: errorMessage
          })
          throw new Error(errorMessage)
        }
      },

      verifyEmail: async (email: string, code: string) => {
        try {
          await api.post('/auth/verify-email', { email, code })
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Email verification failed')
        }
      },

      resendVerification: async (email: string) => {
        try {
          await api.post('/auth/resend-verification', null, { params: { email } })
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to resend verification code')
        }
      },

      forgotPassword: async (email: string) => {
        try {
          await api.post('/auth/forgot-password', { email })
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to send reset code')
        }
      },

      resetPassword: async (email: string, code: string, newPassword: string) => {
        try {
          await api.post('/auth/reset-password', { email, code, new_password: newPassword })
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Password reset failed')
        }
      },

      getGoogleAuthUrl: async () => {
        try {
          const response = await api.get('/auth/google/authorize')
          return response.data.auth_url
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to get Google auth URL')
        }
      },

      googleLogin: async (code: string, state?: string) => {
        try {
          const response = await api.post('/auth/google/callback', { code, state })
          const { access_token } = response.data
          
          set({ token: access_token, isAuthenticated: true })
          
          // Load user data
          await get().loadUser()
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Google login failed')
        }
      },

      logout: () => {
        set({ user: null, token: null, isAuthenticated: false })
      },

      loadUser: async () => {
        try {
          // Backend returns: UserResponse
          const response = await api.get('/users/me')
          
          if (!response.data || !response.data.id) {
            console.error('[authStore] Invalid user response:', response.data)
            get().logout()
            return
          }
          
          set({ user: response.data })
        } catch (error: any) {
          console.error('[authStore] Failed to load user:', {
            error,
            response: error?.response?.data,
            status: error?.response?.status
          })
          // If token is invalid, logout
          get().logout()
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

