import { ArrowRight, Check, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import AppBackground from '../components/AppBackground'
import PublicTopNav from '../components/PublicTopNav'
import { useAuthStore } from '../stores/authStore'

const plans = [
  {
    name: 'Creator',
    price: '$0',
    cadence: 'per month',
    tagline: 'Everything you need to ship your first AI video.',
    features: [
      '3 video projects per month',
      '5 AI image renders per project',
      'Edge TTS voices with 15 languages',
      '2 subtitle styles with brand colors',
      '720p exports with watermark',
    ],
    cta: 'Start for free',
    highlighted: false,
  },
  {
    name: 'Studio',
    price: '$39',
    cadence: 'per editor/month',
    tagline: 'Scale your AI video pipeline with unlimited projects.',
    features: [
      'Unlimited projects & renders',
      'Runware, Pollination & Replicate access',
      'ElevenLabs + Fish Audio premium voices',
      'Custom subtitles & motion overlays',
      '4K exports + social aspect ratios',
      'Collaboration workspace with comments',
    ],
    cta: 'Upgrade to Studio',
    highlighted: true,
  },
  {
    name: 'Enterprise',
    price: 'Let’s talk',
    cadence: 'annual partnership',
    tagline: 'Dedicated infrastructure and workflow integrations.',
    features: [
      'Private model hosting & custom voices',
      'Advanced render queue with SLAs',
      'Single sign-on and roles/permissions',
      'Webhook + API automation at scale',
      'Dedicated success engineer & roadmap input',
    ],
    cta: 'Book a demo',
    highlighted: false,
  },
]

export default function PricingPage() {
  const { isAuthenticated } = useAuthStore()

  return (
    <div className="relative min-h-screen overflow-hidden text-white">
      <AppBackground intensity={0.5} showFloatingIcons />
      <div className="relative z-10 mx-auto w-full max-w-5xl px-6 pb-24 pt-16">
        <PublicTopNav highlight="pricing" isAuthenticated={isAuthenticated} />
        <header className="text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1 text-xs uppercase tracking-widest text-indigo-200">
            <Sparkles className="w-4 h-4" /> Pricing
          </span>
          <h1 className="mt-4 text-4xl font-bold tracking-tight sm:text-5xl">
            Pick the QuantumClip plan that fits your motion workflow
          </h1>
          <p className="mt-4 max-w-3xl mx-auto text-base text-white/80">
            Every plan includes AI scene prompts, subtitle designer, transition packs, and our render intelligence engine. Upgrade when you need more throughput or advanced control.
          </p>
        </header>

        <div className="mt-16 grid gap-8 lg:grid-cols-3">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-[32px] border border-white/15 bg-white/8 p-8 backdrop-blur transition hover:border-white/40 hover:bg-white/12 ${
                plan.highlighted ? 'scale-[1.02] shadow-xl shadow-indigo-500/30' : ''
              }`}
            >
              <div className="flex items-baseline justify-between">
                <h2 className="text-xl font-semibold text-white">{plan.name}</h2>
                {plan.highlighted && (
                  <span className="rounded-full bg-white/20 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-indigo-100">
                    Most popular
                  </span>
                )}
              </div>
              <div className="mt-6 text-white">
                <span className="text-4xl font-bold">{plan.price}</span>
                <span className="ml-2 text-sm text-white/70">{plan.cadence}</span>
              </div>
              <p className="mt-3 text-sm text-white/80">{plan.tagline}</p>

              <ul className="mt-6 space-y-3 text-sm text-white/85">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-3">
                    <span className="mt-1 flex h-5 w-5 items-center justify-center rounded-full bg-indigo-500/80">
                      <Check className="w-3 h-3" />
                    </span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>

              <Link
                to={plan.name === 'Enterprise' ? '/contact' : plan.highlighted ? '/register' : '/register'}
                className={`mt-10 inline-flex w-full items-center justify-center gap-2 rounded-full border px-5 py-3 text-sm font-semibold transition ${
                  plan.highlighted
                    ? 'border-transparent bg-white text-indigo-700 hover:bg-indigo-100'
                    : 'border-white/40 bg-transparent text-white hover:bg-white/10'
                }`}
              >
                {plan.cta}
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          ))}
        </div>

        <section className="mt-20 rounded-[32px] border border-white/15 bg-white/8 p-8 backdrop-blur lg:flex lg:items-center lg:justify-between">
          <div>
            <h3 className="text-2xl font-semibold text-white">Need custom AI models, on-prem renders, or compliance reviews?</h3>
            <p className="mt-3 max-w-2xl text-sm text-white/80">
              Our team can host bespoke Runware or Pollination models, wire up custom voice banks, and secure render infrastructure in your preferred region. We’ll map the ideal workflow with you.
            </p>
          </div>
          <Link
            to="/contact"
            className="mt-6 inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 text-sm font-semibold text-indigo-700 shadow-lg shadow-indigo-500/30 transition hover:bg-indigo-100 lg:mt-0"
          >
            Talk to sales
            <ArrowRight className="w-4 h-4" />
          </Link>
        </section>
      </div>
    </div>
  )
}
