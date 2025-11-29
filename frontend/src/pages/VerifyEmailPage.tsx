import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { useAuthStore } from '../stores/authStore'
import { Mail, CheckCircle, ArrowLeft } from 'lucide-react'
import AppBackground from '../components/AppBackground'
import Logo from '../components/Logo'
import { Link } from 'react-router-dom'

const verifySchema = z.object({
  code: z.string().length(6, 'Code must be 6 digits').regex(/^\d+$/, 'Code must contain only numbers'),
})

type VerifyForm = z.infer<typeof verifySchema>

export default function VerifyEmailPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const email = searchParams.get('email') || ''
  const { verifyEmail, resendVerification } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)
  const [isResending, setIsResending] = useState(false)
  const [countdown, setCountdown] = useState(0)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<VerifyForm>({
    resolver: zodResolver(verifySchema),
  })

  useEffect(() => {
    if (!email) {
      navigate('/register')
    }
  }, [email, navigate])

  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000)
      return () => clearTimeout(timer)
    }
  }, [countdown])

  const onSubmit = async (data: VerifyForm) => {
    setIsLoading(true)
    try {
      await verifyEmail(email, data.code)
      toast.success('✅ Email verified successfully!')
      navigate('/login')
    } catch (error: any) {
      toast.error(error.message || 'Verification failed')
    } finally {
      setIsLoading(false)
    }
  }

  const handleResend = async () => {
    setIsResending(true)
    try {
      await resendVerification(email)
      toast.success('📧 Verification code sent!')
      setCountdown(60) // 60 second cooldown
    } catch (error: any) {
      toast.error(error.message || 'Failed to resend code')
    } finally {
      setIsResending(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <AppBackground intensity={0.5} />

      <div className="relative z-10 w-full max-w-md">
        <div className="mb-8 text-center">
          <Logo size={64} />
          <p className="mt-3 text-sm font-semibold uppercase tracking-wide text-primary-200">
            Verify Your Email
          </p>
        </div>

        <div className="app-panel p-8 text-slate-100">
          <div className="mb-6 text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary-500/20">
              <Mail className="h-8 w-8 text-primary-200" />
            </div>
            <h2 className="text-3xl font-bold text-white">Check your email</h2>
            <p className="mt-2 text-sm text-white/70">
              We've sent a 6-digit verification code to
            </p>
            <p className="mt-1 font-semibold text-primary-200">{email}</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-white/80">
                Verification Code
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

            <button
              type="submit"
              disabled={isLoading}
              className="group mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#4f7dff] via-[#6c4aff] to-[#a13cff] py-4 text-lg font-semibold text-white shadow-lg shadow-indigo-500/40 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-indigo-500/60 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isLoading ? (
                <>
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Verifying...
                </>
              ) : (
                <>
                  <CheckCircle className="h-5 w-5" />
                  Verify Email
                </>
              )}
            </button>
          </form>

          <div className="mt-6 space-y-3">
            <button
              type="button"
              onClick={handleResend}
              disabled={isResending || countdown > 0}
              className="w-full text-sm font-semibold text-primary-200 transition hover:text-primary-100 disabled:text-white/40"
            >
              {countdown > 0
                ? `Resend code in ${countdown}s`
                : isResending
                ? 'Sending...'
                : "Didn't receive code? Resend"}
            </button>

            <Link
              to="/register"
              className="flex items-center justify-center gap-2 text-sm font-medium text-white/70 transition hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to registration
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

