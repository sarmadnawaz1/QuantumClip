import { Link } from 'react-router-dom'
import Logo from './Logo'

interface PublicTopNavProps {
  highlight?: 'home' | 'pricing'
  isAuthenticated?: boolean
}

export default function PublicTopNav({ highlight = 'home', isAuthenticated = false }: PublicTopNavProps) {
  return (
    <header className="flex items-center justify-between">
      <Logo />
      <nav className="hidden items-center gap-6 text-sm font-semibold text-white/80 md:flex">
        <a href="#how-it-works" className="rounded-full px-3 py-1 transition hover:bg-white/10 hover:text-white">
          How it works
        </a>
        <a href="#why-quantumclip" className="rounded-full px-3 py-1 transition hover:bg-white/10 hover:text-white">
          Benefits
        </a>
        <a href="#sample" className="rounded-full px-3 py-1 transition hover:bg-white/10 hover:text-white">
          Sample video
        </a>
        <Link
          to="/pricing"
          className={`rounded-full px-3 py-1 transition ${
            highlight === 'pricing' ? 'bg-white text-[#05071a]' : 'hover:bg-white/10 hover:text-white'
          }`}
        >
          Pricing
        </Link>
      </nav>
      <div className="flex items-center gap-3 text-sm font-semibold">
        {isAuthenticated ? (
          <Link
            to="/create"
            className="rounded-full border border-white/40 px-4 py-2 text-white transition hover:bg-white/10"
          >
            Create video
          </Link>
        ) : (
          <Link
            to="/login"
            className="rounded-full border border-white/40 px-4 py-2 text-white transition hover:bg-white/10"
          >
            Log in
          </Link>
        )}
        <Link
          to={isAuthenticated ? '/create' : '/register'}
          className="hidden items-center gap-2 rounded-full bg-gradient-to-r from-[#4287ff] via-[#6241ff] to-[#9f3cff] px-5 py-2 text-white shadow-lg shadow-indigo-500/40 transition hover:brightness-105 sm:flex"
        >
          {isAuthenticated ? 'New project' : 'Start free'}
        </Link>
      </div>
    </header>
  )
}
