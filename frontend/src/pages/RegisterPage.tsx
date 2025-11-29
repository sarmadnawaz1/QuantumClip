import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { useAuthStore } from '../stores/authStore'
import { Mail, Lock, User, Sparkles, Rocket, Star } from 'lucide-react'
import { Chrome } from 'lucide-react'
import AppBackground from '../components/AppBackground'
import Logo from '../components/Logo'

const registerSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
})

type RegisterForm = z.infer<typeof registerSchema>

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register: registerUser } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  })

  const onSubmit = async (data: RegisterForm) => {
    setIsLoading(true)
    try {
      // Register user - backend expects: {email, username, password, full_name?}
      // Backend returns: UserResponse (no token, user must verify email)
      const result = await registerUser({
        username: data.username,
        email: data.email,
        password: data.password,
        // full_name is optional, not included in form
      })
      
      // Registration successful - redirect to email verification
      toast.success('📧 Verification code sent to your email!')
      navigate(`/verify-email?email=${encodeURIComponent(data.email)}`)
    } catch (error: any) {
      // Extract error message from API response
      const errorMessage = 
        error?.response?.data?.detail || 
        error?.message || 
        'Registration failed. Please check your information and try again.'
      
      console.error('[RegisterPage] Registration error:', {
        error,
        response: error?.response?.data,
        message: errorMessage
      })
      
      toast.error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const handleGoogleSignUp = async () => {
    try {
      const authStore = useAuthStore.getState()
      const authUrl = await authStore.getGoogleAuthUrl()
      window.location.href = authUrl
    } catch (error: any) {
      toast.error(error.message || 'Failed to initiate Google sign up')
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <AppBackground intensity={0.5} />

      <div className="relative z-10 w-full max-w-md">
        <div className="mb-8 text-center">
          <Logo size={64} />
          <p className="mt-3 flex items-center justify-center gap-2 text-sm font-semibold uppercase tracking-wide text-primary-200">
            <Sparkles className="h-4 w-4 text-primary-200" aria-hidden="true" />
            Create your QuantumClip account
            <Sparkles className="h-4 w-4 text-primary-200" aria-hidden="true" />
          </p>
        </div>

        <div className="app-panel p-8 text-slate-100">
          <div className="mb-6 text-center">
            <h2 className="text-3xl font-bold text-white">Join the studio</h2>
            <p className="mt-2 text-sm text-white/70">Sign up to start building AI-powered video stories</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Username Field */}
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-white/80">
                Username
              </label>
              <div className="relative group">
                <User
                  aria-hidden="true"
                  className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 transform text-primary-200/70 transition-colors group-focus-within:text-primary-100"
                />
                <input
                  {...register('username')}
                  type="text"
                  className="glass-field w-full pr-4"
                  placeholder="Choose a unique username"
                />
              </div>
              {errors.username && (
                <p className="flex items-center gap-1 text-sm font-medium text-red-300">
                  <span aria-hidden="true">⚠️</span> {errors.username.message}
                </p>
              )}
            </div>

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
                  className="glass-field w-full pr-4"
                  placeholder="you@example.com"
                />
              </div>
              {errors.email && (
                <p className="flex items-center gap-1 text-sm font-medium text-red-300">
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
                  className="glass-field w-full pr-4"
                  placeholder="Create a strong password"
                />
              </div>
              {errors.password && (
                <p className="flex items-center gap-1 text-sm font-medium text-red-300">
                  <span aria-hidden="true">⚠️</span> {errors.password.message}
                </p>
              )}
            </div>

            {/* Confirm Password Field */}
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-white/80">
                Confirm Password
              </label>
              <div className="relative group">
                <Lock
                  aria-hidden="true"
                  className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 transform text-primary-200/70 transition-colors group-focus-within:text-primary-100"
                />
                <input
                  {...register('confirmPassword')}
                  type="password"
                  className="glass-field w-full pr-4"
                  placeholder="Confirm your password"
                />
              </div>
              {errors.confirmPassword && (
                <p className="flex items-center gap-1 text-sm font-medium text-red-300">
                  <span aria-hidden="true">⚠️</span> {errors.confirmPassword.message}
                </p>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="group mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#4f7dff] via-[#6c4aff] to-[#a13cff] py-4 text-lg font-semibold text-white shadow-lg shadow-indigo-500/40 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-indigo-500/60 disabled:cursor-not-allowed disabled:opacity-70 disabled:shadow-none"
            >
              {isLoading ? (
                <>
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" aria-hidden="true"></div>
                  Creating your account...
                </>
              ) : (
                <>
                  <Rocket aria-hidden="true" className="h-5 w-5 transition-transform group-hover:-translate-y-1 group-hover:translate-x-1" />
                  Create account
                  <Sparkles aria-hidden="true" className="h-5 w-5" />
                </>
              )}
            </button>
          </form>

          {/* Google Sign Up */}
          <button
            type="button"
            onClick={handleGoogleSignUp}
            className="group flex w-full items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/5 py-4 text-lg font-semibold text-white transition-all duration-300 hover:bg-white/10 hover:border-white/30"
          >
            <Chrome className="h-5 w-5" />
            Sign up with Google
          </button>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/15"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 text-sm font-medium text-white/60">Already a member?</span>
            </div>
          </div>

          {/* Sign In Link */}
          <div className="text-center text-sm text-white/70">
            <p>
              Already have an account?{' '}
              <Link
                to="/login"
                className="group inline-flex items-center gap-1 font-semibold text-primary-200 transition hover:text-primary-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
              >
                Sign in here
                <Star aria-hidden="true" className="h-4 w-4 transition-transform group-hover:rotate-12" />
              </Link>
            </p>
          </div>
        </div>

        <p className="mt-6 text-center text-sm text-white/70 drop-shadow-md">
          🚀 Built for creators who ship AI video every day
        </p>
      </div>
    </div>
  )
}

