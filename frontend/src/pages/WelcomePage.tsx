import { Link } from 'react-router-dom'
import { ArrowRight, Play } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import AppBackground from '../components/AppBackground'
import PublicTopNav from '../components/PublicTopNav'

export default function WelcomePage() {
  const { isAuthenticated } = useAuthStore()

  return (
    <div className="relative min-h-screen overflow-hidden text-white">
      <AppBackground showFloatingIcons />
      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 pb-20 pt-12 sm:px-10 lg:px-16">
        <PublicTopNav isAuthenticated={isAuthenticated} />

        <main className="mt-16 flex flex-1 flex-col items-center text-center">
          <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl md:text-6xl">
            Create AI videos with stunning images and voiceovers
          </h1>
          <p className="mt-4 max-w-2xl text-base text-white/85 sm:text-lg">
            QuantumClip turns scripts into finished videos—scene prompts, AI artwork, voiceovers, subtitles, and renders—all in one streamlined workspace.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            {isAuthenticated ? (
              <>
                <Link
                  to="/create"
                  className="inline-flex items-center gap-2 rounded-full border border-white/40 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  Continue generating
                  <Play className="w-4 h-4" />
                </Link>
              </>
            ) : (
              <>
                <Link
                  to="/register"
                  className="group inline-flex items-center gap-2 rounded-full bg-black/90 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-black/40 transition hover:bg-black"
                >
                  Get started
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </Link>
                <a
                  href="#sample"
                  className="inline-flex items-center gap-2 rounded-full border border-white/40 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  View sample video
                  <Play className="w-4 h-4" />
                </a>
              </>
            )}
          </div>
          <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-white/70">
            7-day free trial — no credit card required
          </p>

          <section
            id="how-it-works"
            className="mt-14 w-full max-w-4xl rounded-[40px] border border-white/15 bg-white/8 p-8 backdrop-blur"
          >
            <div className="grid gap-8 lg:grid-cols-2">
              <div className="space-y-6">
                <p className="text-xs font-semibold uppercase tracking-widest text-white/60">How QuantumClip Works</p>
                <div className="rounded-3xl bg-white/5 p-5 text-left shadow-inner shadow-black/20 space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold text-white/90">1. Script becomes organized scenes</h3>
                    <ul className="mt-2 space-y-1 text-sm text-white/70">
                      <li>• Paste any script or use our auto-generated stories.</li>
                      <li>• Scene splitter respects paragraphs and manual scene tags.</li>
                      <li>• Configurable word counts keep visuals aligned with audio.</li>
                    </ul>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white/90">2. Visual prompts tailored to your style</h3>
                    <ul className="mt-2 space-y-1 text-sm text-white/70">
                      <li>• Choose from curated styles or add custom instructions.</li>
                      <li>• Prompts are auto-personalized for each scene.</li>
                      <li>• Pollination AI works out of the box; Runware, Replicate, and Together unlock with API keys.</li>
                    </ul>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white/90">3. Voiceover & sound in one pass</h3>
                    <ul className="mt-2 space-y-1 text-sm text-white/70">
                      <li>• Edge TTS voices are included; ElevenLabs & Fish Audio connect instantly.</li>
                      <li>• Auto-align narration timing to each scene.</li>
                      <li>• Drop in background music and optional overlay effects.</li>
                    </ul>
                  </div>
              <div>
                    <h3 className="text-lg font-semibold text-white/90">4. Render and download instantly</h3>
                    <ul className="mt-2 space-y-1 text-sm text-white/70">
                      <li>• Live progress view covers prompts, images, audio, and rendering.</li>
                      <li>• Finished MP4 and thumbnails download right away.</li>
                      <li>• Scenes, prompts, and assets stay accessible for future edits.</li>
                    </ul>
                    </div>
                </div>
              </div>

              <div className="space-y-6">
                <p id="why-quantumclip" className="text-xs font-semibold uppercase tracking-widest text-white/60">
                  Why teams love it
                </p>
                <div className="rounded-3xl border border-white/10 bg-white/10 p-5 space-y-5">
                  <div>
                    <h3 className="text-lg font-semibold text-white/90">Consistent characters & branding</h3>
                    <p className="mt-1 text-sm text-white/70">
                      Scene-level edits and global instructions keep characters, locations, and palettes consistent—even across regenerations.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white/90">Connect your favorite providers</h3>
                    <p className="mt-1 text-sm text-white/70">
                      Manage Groq, OpenAI, Gemini, Runware, Replicate, Together, ElevenLabs, and Fish Audio keys in one place. Switch providers mid-project without rebuilding.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white/90">Full visibility while rendering</h3>
                    <p className="mt-1 text-sm text-white/70">
                      Detailed progress pages show every stage—prompts, images, audio, and final render—so you know exactly where each project stands before download.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white/90">One-click exports</h3>
                    <p className="mt-1 text-sm text-white/70">
                      Finished videos, thumbnails, and individual scene assets are available immediately—ready for social uploads, ads, or client delivery.
                    </p>
                    </div>
                </div>
              </div>
            </div>
          </section>

          <section
            id="sample"
            className="mt-12 w-full max-w-4xl rounded-[32px] border border-white/15 bg-black/20 p-6 backdrop-blur"
          >
            <div className="flex flex-col gap-6 md:flex-row md:items-center">
              <div className="md:w-2/5 space-y-3 text-left">
                <p className="text-xs font-semibold uppercase tracking-widest text-white/60">See it in action</p>
                <h2 className="text-2xl font-semibold text-white">Sample render generated with default settings</h2>
                <p className="text-sm text-white/70">
                  This 30-second clip was created with Pollination AI images and Edge TTS—no premium keys attached. Every scene, subtitle, and transition came from the workflow shown above.
                </p>
                  </div>
              <div className="md:w-3/5 overflow-hidden rounded-2xl border border-white/10 shadow-xl shadow-black/30">
                <video
                  controls
                  preload="metadata"
                  poster="https://images.unsplash.com/photo-1522199997319-bc941daa977a?auto=format&fit=crop&w=900&q=80"
                  className="w-full"
                >
                  <source src="https://storage.googleapis.com/coverr-main/mp4/Mt_Baker.mp4" type="video/mp4" />
                  Your browser does not support the video tag.
                </video>
              </div>
            </div>
          </section>

          <section className="mt-12 w-full max-w-4xl rounded-[32px] border border-white/15 bg-white/8 p-6 backdrop-blur">
            <div className="grid gap-6 text-center sm:grid-cols-3">
              <div>
                <p className="text-3xl font-bold text-white">4.7★</p>
                <p className="mt-1 text-sm text-white/70">Average creator satisfaction</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-white">90%</p>
                <p className="mt-1 text-sm text-white/70">Videos rendered with free providers</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-white">60s</p>
                <p className="mt-1 text-sm text-white/70">Setup time from sign-up to first render</p>
              </div>
          </div>
          </section>

        </main>
      </div>
    </div>
  )
}
