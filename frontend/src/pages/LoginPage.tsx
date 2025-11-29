import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { useAuthStore } from '../stores/authStore'
import { Mail, Lock, Sparkles, Play, Chrome } from 'lucide-react'
import AppBackground from '../components/AppBackground'
import Logo from '../components/Logo'

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
})

type LoginForm = z.infer<typeof loginSchema>

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, getGoogleAuthUrl } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [announcement, setAnnouncement] = useState<string | null>(null)

  const handleGoogleSignIn = async () => {
    try {
      const authUrl = await getGoogleAuthUrl()
      window.location.href = authUrl
    } catch (error: any) {
      toast.error(error.message || 'Failed to initiate Google sign in')
    }
  }

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true)
    setFormError(null)
    setAnnouncement(null)
    try {
      // Login - backend expects: {email, password}
      // Backend returns: {access_token, refresh_token, token_type: "bearer"}
      // authStore.login() handles storing token and loading user
      await login(data.email, data.password)
      
      // Login successful - redirect to home/dashboard
      toast.success('Welcome back! 🎬')
      navigate('/')
    } catch (error: any) {
      // Extract error message from API response
      const errorMessage =
        error?.response?.data?.detail ||
        error?.message ||
        'We could not sign you in. Please check your credentials and try again.'
      
      console.error('[LoginPage] Login error:', {
        error,
        response: error?.response?.data,
        message: errorMessage,
        status: error?.response?.status
      })
      
      setFormError(errorMessage)
      setAnnouncement(errorMessage)
      toast.error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (!isLoading && !formError) {
      setAnnouncement(null)
    }
  }, [isLoading, formError])

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <AppBackground intensity={0.5} />

      <div className="relative z-10 w-full max-w-md">
        <div className="mb-10 text-center">
          <Logo size={64} />
          <p className="mt-3 flex items-center justify-center gap-2 text-sm font-semibold uppercase tracking-wide text-primary-200">
            <Sparkles className="h-4 w-4 text-primary-200" aria-hidden="true" />
            Sign in to QuantumClip
            <Sparkles className="h-4 w-4 text-primary-200" aria-hidden="true" />
          </p>
        </div>

        <div className="app-panel p-8 text-slate-100">
          <div className="mb-6 text-center">
            <h2 className="text-3xl font-bold text-white">Welcome back</h2>
            <p className="mt-2 text-sm text-white/70">Continue crafting cinematic AI videos</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {/* Email Field */}
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-white/80">
                Email Address
              </label>
              <div className="relative group">
                <Mail
                  aria-hidden="true"
                  className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 transform text-primary-200/70 transition-colors group-focus-within:text-primary-100"
                />
                <input
                  {...register('email')}
                  type="email"
                  autoComplete="email"
                  aria-invalid={Boolean(errors.email)}
                  aria-describedby={errors.email ? 'email-error' : undefined}
                  className="glass-field w-full pr-4 aria-[invalid=true]:border-red-500 aria-[invalid=true]:ring-red-500/10"
                  placeholder="you@example.com"
                />
              </div>
              {errors.email && (
                <p id="email-error" className="flex items-center gap-1 text-sm font-medium text-red-300">
                  <span aria-hidden="true">⚠️</span> {errors.email.message}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-white/80">
                Password
              </label>
              <div className="relative group">
                <Lock
                  aria-hidden="true"
                  className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 transform text-primary-200/70 transition-colors group-focus-within:text-primary-100"
                />
                <input
                  {...register('password')}
                  type="password"
                  autoComplete="current-password"
                  aria-invalid={Boolean(errors.password)}
                  aria-describedby={errors.password ? 'password-error' : undefined}
                  className="glass-field w-full pr-4 aria-[invalid=true]:border-red-500 aria-[invalid=true]:ring-red-500/10"
                  placeholder="Enter your password"
                />
              </div>
              {errors.password && (
                <p id="password-error" className="flex items-center gap-1 text-sm font-medium text-red-300">
                  <span aria-hidden="true">⚠️</span> {errors.password.message}
                </p>
              )}
            </div>

            <div className="flex flex-col gap-3 text-sm md:flex-row md:items-center md:justify-between">
              <Link
                to="/forgot-password"
                className="font-semibold text-primary-200 underline-offset-4 transition hover:text-primary-100 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
              >
                Forgot your password?
              </Link>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              aria-busy={isLoading}
              className="group flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#4f7dff] via-[#6c4aff] to-[#a13cff] py-4 text-lg font-semibold text-white shadow-lg shadow-indigo-500/40 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-indigo-500/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-indigo-600 disabled:cursor-not-allowed disabled:opacity-70 disabled:shadow-none disabled:transition-none"
            >
              {isLoading ? (
                <>
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" aria-hidden="true"></div>
                  Signing in...
                </>
              ) : (
                <>
                  Sign In
                  <Play aria-hidden="true" className="h-5 w-5 transition-transform group-hover:translate-x-1" />
                </>
              )}
            </button>
            <p aria-live="assertive" className="text-sm font-medium text-red-300" role="status">
              {announcement}
            </p>
            {formError && (
              <div className="rounded-lg border border-red-400/40 bg-red-500/10 p-3 text-sm text-red-200">
                {formError}
                <span className="block text-xs text-red-300">
                  Still stuck?{' '}
                  <a className="underline underline-offset-2 hover:text-red-200" href="mailto:support@quantumclip.io">
                    Email support@quantumclip.io
                  </a>
                </span>
              </div>
            )}
          </form>

          {/* Google Sign In */}
          <button
            type="button"
            onClick={handleGoogleSignIn}
            className="group flex w-full items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/5 py-4 text-lg font-semibold text-white transition-all duration-300 hover:bg-white/10 hover:border-white/30"
          >
            <Chrome className="h-5 w-5" />
            Sign in with Google
          </button>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/15"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 text-sm font-medium text-white/60">New here?</span>
            </div>
          </div>

          {/* Sign Up Link */}
          <div className="text-center">
            <p className="font-medium text-white/70">
              Don't have an account?{' '}
              <Link 
                to="/register" 
                className="group bg-gradient-to-r from-primary-200 to-purple-200 bg-clip-text font-bold text-transparent transition-all duration-300 hover:from-primary-100 hover:to-purple-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
              >
                Create one now
                <Sparkles aria-hidden="true" className="h-4 w-4 text-primary-100 transition-transform group-hover:rotate-12" />
              </Link>
            </p>
          </div>
        </div>

        <p className="mt-6 text-center text-sm text-white/70 drop-shadow-md">
          🎬 Transform ideas into motion with QuantumClip
        </p>
      </div>
    </div>
  )
}

