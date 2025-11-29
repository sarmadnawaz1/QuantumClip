import { useEffect, useMemo, useRef, useState } from 'react'
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { LogOut, Settings, ChevronDown, User as UserIcon, CreditCard, FileVideo } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import Logo from './Logo'

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement | null>(null)

  const navigation = useMemo(
    () => [
      { name: 'Create Video', href: '/create' },
      { name: 'My Videos', href: '/my-videos' },
    ],
    []
  )

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      if (!menuRef.current) return
      if (!menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false)
      }
    }
    if (menuOpen) {
      window.addEventListener('click', handleClick)
    }
    return () => window.removeEventListener('click', handleClick)
  }, [menuOpen])

  const isActive = (href: string) => {
    if (href === '/') {
      return location.pathname === '/'
    }
    return location.pathname.startsWith(href)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const initials = user?.full_name?.split(' ').map((part) => part[0]).slice(0, 2).join('') || user?.username?.slice(0, 2)?.toUpperCase() || 'QC'

  return (
    <div className="relative min-h-screen overflow-hidden text-white">
      <header className="sticky top-0 z-40 border-b border-white/10 bg-[#05071a]/70 backdrop-blur">
        <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center gap-3">
            <Logo size={38} showWordmark={false} />
            <span className="text-lg font-semibold tracking-wider text-white">QuantumClip</span>
          </Link>

          <nav className="hidden gap-6 md:flex">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={`text-sm font-semibold transition ${
                  isActive(item.href)
                    ? 'text-white underline underline-offset-8'
                    : 'text-white/70 hover:text-white'
                }`}
              >
                {item.name}
              </Link>
            ))}
          </nav>

          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenuOpen((prev) => !prev)}
              className="flex items-center gap-3 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-left shadow-sm transition hover:border-white/50"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 text-white shadow-lg shadow-indigo-500/30">
                <span className="text-sm font-semibold">{initials}</span>
              </div>
              <div className="hidden text-sm text-white sm:block">
                <p className="font-semibold">{user?.full_name || user?.username || 'Creator'}</p>
                <p className="text-xs text-white/60">{user?.email}</p>
              </div>
              <ChevronDown className={`w-4 h-4 text-white/60 transition ${menuOpen ? 'rotate-180' : ''}`} />
            </button>

            {menuOpen && (
              <div className="absolute right-0 mt-3 w-64 rounded-2xl border border-white/15 bg-[#05071a]/95 shadow-2xl backdrop-blur">
                <div className="flex items-center gap-3 border-b border-white/10 px-4 py-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-500 text-white shadow-lg shadow-indigo-500/30">
                    <UserIcon className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-white">{user?.full_name || user?.username || 'Creator'}</p>
                    <p className="truncate text-xs text-white/60">{user?.email}</p>
                  </div>
                </div>
                <div className="flex flex-col py-2">
                  <Link
                    to="/my-videos"
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white/80 transition hover:bg-white/10 hover:text-white"
                  >
                    <FileVideo className="w-4 h-4" />
                    My Videos
                  </Link>
                  <Link
                    to="/settings"
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white/80 transition hover:bg-white/10 hover:text-white"
                  >
                    <Settings className="w-4 h-4" />
                    Manage API Keys
                  </Link>
                  <Link
                    to="/pricing"
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white/80 transition hover:bg-white/10 hover:text-white"
                  >
                    <CreditCard className="w-4 h-4" />
                    Pricing
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm font-semibold text-rose-400 transition hover:bg-rose-500/10 hover:text-rose-200"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="relative z-10 mx-auto w-full max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="rounded-[32px] border border-white/10 bg-white/5 p-6 backdrop-blur">
          <Outlet />
        </div>
      </div>
    </div>
  )
}

