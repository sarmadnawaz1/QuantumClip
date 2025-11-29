import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import toast from 'react-hot-toast'
import AppBackground from '../components/AppBackground'
import Logo from '../components/Logo'

export default function GoogleOAuthCallback() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { googleLogin } = useAuthStore()

  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')

    if (code) {
      googleLogin(code, state || undefined)
        .then(() => {
          toast.success('✅ Signed in with Google!')
          navigate('/')
        })
        .catch((error: any) => {
          toast.error(error.message || 'Google sign in failed')
          navigate('/login')
        })
    } else {
      toast.error('No authorization code received')
      navigate('/login')
    }
  }, [searchParams, googleLogin, navigate])

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <AppBackground intensity={0.5} />
      <div className="relative z-10 text-center">
        <Logo size={64} />
        <p className="mt-4 text-white/70">Completing sign in...</p>
      </div>
    </div>
  )
}

