import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { useAuthStore } from '../stores/authStore'
import { Lock, CheckCircle, ArrowLeft } from 'lucide-react'
import AppBackground from '../components/AppBackground'
import Logo from '../components/Logo'

const resetPasswordSchema = z.object({
  code: z.string().length(6, 'Code must be 6 digits').regex(/^\d+$/, 'Code must contain only numbers'),
  newPassword: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
})

type ResetPasswordForm = z.infer<typeof resetPasswordSchema>

export default function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const email = searchParams.get('email') || ''
  const { resetPassword } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordForm>({
    resolver: zodResolver(resetPasswordSchema),
  })

  useEffect(() => {
    if (!email) {
      navigate('/forgot-password')
    }
  }, [email, navigate])

  const onSubmit = async (data: ResetPasswordForm) => {
    setIsLoading(true)
    try {
      await resetPassword(email, data.code, data.newPassword)
      toast.success('✅ Password reset successfully!')
      navigate('/login')
    } catch (error: any) {
      toast.error(error.message || 'Password reset failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <AppBackground intensity={0.5} />

      <div className="relative z-10 w-full max-w-md">
        <div className="mb-8 text-center">
          <Logo size={64} />
          <p className="mt-3 text-sm font-semibold uppercase tracking-wide text-primary-200">
            Reset Your Password
          </p>
        </div>

        <div className="app-panel p-8 text-slate-100">
          <div className="mb-6 text-center">
            <h2 className="text-3xl font-bold text-white">Enter reset code</h2>
            <p className="mt-2 text-sm text-white/70">
              Check your email for the 6-digit code
            </p>
            <p className="mt-1 text-xs text-white/60">{email}</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-white/80">
                Reset Code
              </label>
              <input
                {...register('code')}
                type="text"
                maxLength={6}
                className="glass-field w-full text-center text-2xl font-bold tracking-widest"
                placeholder="000000"
                autoComplete="one-time-code"
                autoFocus
              />
              {errors.code && (
                <p className="flex items-center gap-1 text-sm font-medium text-red-300">
                  <span aria-hidden="true">⚠️</span> {errors.code.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-semibold text-white/80">
                New Password
              </label>
              <div className="relative group">
                <Lock className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 transform text-primary-200/70 transition-colors group-focus-within:text-primary-100" />
                <input
                  {...register('newPassword')}
                  type="password"
                  className="glass-field w-full pr-4"
                  placeholder="Enter new password"
                />
              </div>
              {errors.newPassword && (
                <p className="flex items-center gap-1 text-sm font-medium text-red-300">
                  <span aria-hidden="true">⚠️</span> {errors.newPassword.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-semibold text-white/80">
                Confirm Password
              </label>
              <div className="relative group">
                <Lock className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 transform text-primary-200/70 transition-colors group-focus-within:text-primary-100" />
                <input
                  {...register('confirmPassword')}
                  type="password"
                  className="glass-field w-full pr-4"
                  placeholder="Confirm new password"
                />
              </div>
              {errors.confirmPassword && (
                <p className="flex items-center gap-1 text-sm font-medium text-red-300">
                  <span aria-hidden="true">⚠️</span> {errors.confirmPassword.message}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="group mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#4f7dff] via-[#6c4aff] to-[#a13cff] py-4 text-lg font-semibold text-white shadow-lg shadow-indigo-500/40 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-indigo-500/60 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isLoading ? (
                <>
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Resetting...
                </>
              ) : (
                <>
                  <CheckCircle className="h-5 w-5" />
                  Reset Password
                </>
              )}
            </button>
          </form>

          <Link
            to="/login"
            className="mt-6 flex items-center justify-center gap-2 text-sm font-medium text-white/70 transition hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to login
          </Link>
        </div>
      </div>
    </div>
  )
}

