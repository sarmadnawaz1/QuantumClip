import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { useAuthStore } from '../stores/authStore'
import { Mail, ArrowLeft, CheckCircle } from 'lucide-react'
import AppBackground from '../components/AppBackground'
import Logo from '../components/Logo'

const forgotPasswordSchema = z.object({
  email: z.string().email('Invalid email address'),
})

type ForgotPasswordForm = z.infer<typeof forgotPasswordSchema>

export default function ForgotPasswordPage() {
  const navigate = useNavigate()
  const { forgotPassword } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)
  const [emailSent, setEmailSent] = useState(false)
  const [email, setEmail] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordForm>({
    resolver: zodResolver(forgotPasswordSchema),
  })

  const onSubmit = async (data: ForgotPasswordForm) => {
    setIsLoading(true)
    try {
      await forgotPassword(data.email)
      setEmail(data.email)
      setEmailSent(true)
      toast.success('📧 Password reset code sent!')
    } catch (error: any) {
      toast.error(error.message || 'Failed to send reset code')
    } finally {
      setIsLoading(false)
    }
  }

  if (emailSent) {
    return (
      <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
        <AppBackground intensity={0.5} />

        <div className="relative z-10 w-full max-w-md">
          <div className="mb-8 text-center">
            <Logo size={64} />
          </div>

          <div className="app-panel p-8 text-slate-100">
            <div className="mb-6 text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-500/20">
                <CheckCircle className="h-8 w-8 text-green-400" />
              </div>
              <h2 className="text-3xl font-bold text-white">Check your email</h2>
              <p className="mt-2 text-sm text-white/70">
                We've sent a password reset code to
              </p>
              <p className="mt-1 font-semibold text-primary-200">{email}</p>
            </div>

            <Link
              to={`/reset-password?email=${encodeURIComponent(email)}`}
              className="group mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#4f7dff] via-[#6c4aff] to-[#a13cff] py-4 text-lg font-semibold text-white shadow-lg shadow-indigo-500/40 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-indigo-500/60"
            >
              Continue to Reset Password
            </Link>

            <Link
              to="/login"
              className="mt-4 flex items-center justify-center gap-2 text-sm font-medium text-white/70 transition hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to login
            </Link>
          </div>
        </div>
      </div>
    )
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
            <h2 className="text-3xl font-bold text-white">Forgot password?</h2>
            <p className="mt-2 text-sm text-white/70">
              Enter your email address and we'll send you a reset code
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-white/80">
                Email Address
              </label>
              <div className="relative group">
                <Mail
                  className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 transform text-primary-200/70 transition-colors group-focus-within:text-primary-100"
                />
                <input
                  {...register('email')}
                  type="email"
                  className="glass-field w-full pr-4"
                  placeholder="you@example.com"
                  autoComplete="email"
                />
              </div>
              {errors.email && (
                <p className="flex items-center gap-1 text-sm font-medium text-red-300">
                  <span aria-hidden="true">⚠️</span> {errors.email.message}
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
                  Sending...
                </>
              ) : (
                <>
                  <Mail className="h-5 w-5" />
                  Send Reset Code
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

