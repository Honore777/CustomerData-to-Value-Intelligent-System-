import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

const heroWords = ['drifting', 'returning', 'expanding', 'worth more']

const differentiators = [
  {
    title: 'See revenue risk before it compounds',
    description:
      'Track recency, frequency, and spending shifts early enough to act before your most valuable customers quietly fade away.',
  },
  {
    title: 'Turn customer data into operating decisions',
    description:
      'Your uploads become segment worklists, revenue signals, comparison snapshots, and customer pages your team can immediately use.',
  },
  {
    title: 'Operate across branches with clarity',
    description:
      'Review performance by location, compare snapshots over time, and keep owners, managers, and admins aligned around the same truth.',
  },
]

const proofPoints = [
  'Revenue concentration shows the customer group carrying a disproportionate share of your income.',
  'Snapshot comparison shows who improved, slipped, recovered, or weakened between uploads.',
  'Customer workspaces turn raw data into context, memory, and next action.',
]

const outcomes = [
  {
    label: 'From customer data to direction',
    value: 'Minutes',
  },
  {
    label: 'Revenue risk made visible',
    value: 'Per segment',
  },
  {
    label: 'One system for action',
    value: 'One workspace',
  },
]

const screenshots = [
  {
    src: '/screenshots/dashboard-overview.png',
    title: 'Revenue overview',
    description: 'A dashboard that turns customer movement into visible business priorities.',
  },
  {
    src: '/screenshots/customer-workspace.png',
    title: 'Customer workspace',
    description: 'The full customer story, with context your team can act on immediately.',
  },
  {
    src: '/screenshots/vip-view.png',
    title: 'High-value segments',
    description: 'Revenue concentration and priority customer groups in one focused view.',
  },
]

const plans = [
  {
    name: 'Start Plan',
    price: '$15',
    cadence: '/month',
    description: 'A focused starting point for businesses that want customer-data-to-revenue clarity without operational complexity.',
    features: [
      'Customer health and revenue-risk dashboard',
      'Branch comparison and upload snapshots',
      'Priority customer worklists',
      'Revenue concentration and high-value customer views',
      'Initial onboarding and training for your team',
    ],
  },
  {
    name: 'Pro Plan',
    price: '$20',
    cadence: '/month',
    description: 'For businesses that want a more tailored operating system with a dedicated model shaped around their own use case.',
    features: [
      'Everything in Start Plan',
      'Dedicated machine learning model for your use case',
      'More tailored customer scoring and revenue signals',
      'Priority guidance for business-specific workflows',
      'Initial onboarding and training for your team',
    ],
  },
]

export default function LandingPage() {
  const [activeWordIndex, setActiveWordIndex] = useState(0)
  const [selectedScreenshot, setSelectedScreenshot] = useState<(typeof screenshots)[number] | null>(null)
  const [subscriberEmail, setSubscriberEmail] = useState('')

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setActiveWordIndex((currentIndex) => (currentIndex + 1) % heroWords.length)
    }, 2200)

    return () => window.clearInterval(intervalId)
  }, [])

  const activeWord = heroWords[activeWordIndex]

  const handleSubscribe = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const trimmedEmail = subscriberEmail.trim()
    if (!trimmedEmail) {
      return
    }

    const subject = encodeURIComponent('New landing page subscriber')
    const body = encodeURIComponent(`Please add this subscriber to updates:\n\nEmail: ${trimmedEmail}`)
    window.location.href = `mailto:transeffex@gmail.com?subject=${subject}&body=${body}`
  }

  return (
    <div className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(249,115,22,0.16),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(8,145,178,0.18),_transparent_24%),linear-gradient(180deg,_#fff7ed_0%,_#f8fafc_36%,_#e2e8f0_100%)] text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <header className="flex items-center justify-between rounded-full border border-white/70 bg-white/70 px-4 py-3 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur md:px-6">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-cyan-700">Customer Revenue Intelligence</p>
            <p className="mt-1 text-sm font-medium text-slate-600">A customer-data-to-revenue system for modern businesses</p>
          </div>

          <nav className="hidden items-center gap-6 text-sm font-semibold text-slate-600 lg:flex">
            <a href="#product" className="transition hover:text-slate-950">
              Product
            </a>
            <a href="#pricing" className="transition hover:text-slate-950">
              Pricing
            </a>
            <a href="#contact" className="transition hover:text-slate-950">
              Contact
            </a>
          </nav>

          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              to="/login"
              className="rounded-full border border-slate-300/80 bg-slate-50/88 px-4 py-2 text-sm font-semibold text-slate-700 shadow-[0_10px_24px_rgba(15,23,42,0.06)] transition hover:border-cyan-300 hover:bg-white hover:text-slate-900"
            >
              Sign in
            </Link>
            <Link
              to="/register"
              className="rounded-full bg-[linear-gradient(135deg,#0f172a_0%,#155e75_52%,#c2410c_100%)] px-4 py-2 text-sm font-semibold text-white shadow-[0_16px_32px_rgba(15,23,42,0.18)] transition hover:translate-y-[-1px]"
            >
              Start free trial
            </Link>
          </div>
        </header>

        <main className="flex-1 py-14 lg:py-20">
          <section className="grid gap-12 lg:grid-cols-[1.08fr_0.92fr] lg:items-center">
            <div className="space-y-8">
              <div className="inline-flex items-center gap-2 rounded-full border border-orange-200 bg-white/80 px-4 py-2 text-sm font-medium text-slate-700 shadow-sm backdrop-blur">
                <span className="h-2.5 w-2.5 rounded-full bg-orange-500" />
                Your customer data becomes revenue motion, not another static report.
              </div>

              <div className="space-y-6">
                <h1 className="max-w-4xl text-5xl font-black tracking-[-0.04em] text-slate-950 sm:text-6xl lg:text-7xl">
                  Know which customers are
                  <span className="relative mx-3 inline-flex min-w-[6.8ch] items-center justify-center align-baseline text-transparent [text-shadow:none]">
                    <span className="absolute inset-0 rounded-2xl bg-[linear-gradient(135deg,_rgba(251,146,60,0.24),_rgba(34,211,238,0.18))] blur-md" />
                    <span
                      key={activeWord}
                      className="relative inline-block bg-[linear-gradient(135deg,#c2410c_0%,#0f766e_100%)] bg-clip-text animate-[word-rise_420ms_ease-out]"
                    >
                      {activeWord}
                    </span>
                  </span>
                  before revenue slips quietly out the door.
                </h1>

                <p className="max-w-2xl text-lg leading-8 text-slate-600 sm:text-xl">
                  Customer Revenue Intelligence helps growing businesses turn customer data into revenue clarity, branch-level signals, comparison snapshots, and customer actions your team can actually follow.
                </p>
                <p className="max-w-2xl text-base leading-7 text-slate-500 sm:text-lg">
                  From customer data to revenue. From hidden patterns to income in motion. Your data, your rhythm, your revenue made visible.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <Link
                  to="/register"
                  className="inline-flex items-center justify-center rounded-full bg-[linear-gradient(135deg,#111827_0%,#0f766e_50%,#c2410c_100%)] px-6 py-3 text-base font-semibold text-white shadow-[0_20px_45px_rgba(15,23,42,0.2)] transition hover:translate-y-[-1px]"
                >
                  Start your 14-day trial
                </Link>
                <Link
                  to="/login"
                  className="inline-flex items-center justify-center rounded-full border border-slate-300/80 bg-slate-50/88 px-6 py-3 text-base font-semibold text-slate-700 shadow-[0_12px_28px_rgba(15,23,42,0.06)] transition hover:border-cyan-300 hover:bg-white hover:text-slate-900"
                >
                  Sign in to your dashboard
                </Link>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                {outcomes.map((item) => (
                  <div
                    key={item.label}
                    className="rounded-3xl border border-white/80 bg-white/75 p-5 shadow-[0_20px_50px_rgba(15,23,42,0.08)] backdrop-blur"
                  >
                    <p className="text-2xl font-black tracking-tight text-slate-950">{item.value}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{item.label}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className="absolute left-8 top-8 h-28 w-28 rounded-full bg-orange-300/40 blur-3xl" />
              <div className="absolute bottom-8 right-8 h-32 w-32 rounded-full bg-cyan-300/40 blur-3xl" />

              <div className="relative overflow-hidden rounded-[36px] border border-slate-200/80 bg-[linear-gradient(145deg,#0f172a_0%,#1e293b_58%,#7c2d12_100%)] p-6 text-white shadow-[0_35px_140px_rgba(15,23,42,0.28)] lg:p-7">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.28em] text-orange-200">Product preview</p>
                    <h2 className="mt-3 max-w-sm text-3xl font-black tracking-tight">A real operating view for customer data, revenue risk, and branch action.</h2>
                  </div>
                  <div className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-cyan-100">
                    Live product
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setSelectedScreenshot(screenshots[0])}
                  className="group mt-8 block w-full overflow-hidden rounded-[28px] border border-white/10 bg-slate-950/20 p-2 text-left transition hover:scale-[1.015]"
                >
                  <div className="overflow-hidden rounded-[22px] border border-white/10">
                    <img
                      src={screenshots[0].src}
                      alt={screenshots[0].title}
                      className="h-auto w-full object-cover shadow-[0_24px_60px_rgba(15,23,42,0.35)] transition duration-500 group-hover:scale-[1.03]"
                    />
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3 px-1">
                    <div>
                      <p className="text-sm font-semibold text-white">{screenshots[0].title}</p>
                      <p className="mt-1 text-sm leading-6 text-slate-300">Open the full view and inspect the live workflow.</p>
                    </div>
                    <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-cyan-100">
                      Open
                    </span>
                  </div>
                </button>

                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  {screenshots.slice(1).map((shot) => (
                    <button
                      key={shot.src}
                      type="button"
                      onClick={() => setSelectedScreenshot(shot)}
                      className="group rounded-[24px] border border-white/10 bg-white/8 p-3 text-left backdrop-blur-sm transition hover:scale-[1.02]"
                    >
                      <div className="overflow-hidden rounded-[18px] border border-white/10">
                        <img
                          src={shot.src}
                          alt={shot.title}
                          className="h-auto w-full object-cover transition duration-500 group-hover:scale-[1.04]"
                        />
                      </div>
                      <p className="mt-3 text-sm font-semibold text-white">{shot.title}</p>
                      <p className="mt-1 text-sm leading-6 text-slate-300">{shot.description}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section id="product" className="mt-20 rounded-[34px] border border-white/85 bg-white/80 p-6 shadow-[0_22px_70px_rgba(15,23,42,0.08)] backdrop-blur lg:p-8">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-700">Product Screens</p>
                <h2 className="mt-3 text-3xl font-black tracking-tight text-slate-950">See how customer data turns into revenue clarity, branch focus, and follow-up action.</h2>
              </div>
              <p className="max-w-2xl text-sm leading-7 text-slate-600">
                Open any screen for a closer look. Each view is built to move from raw customer records to visible revenue signals, focused teams, and concrete next steps.
              </p>
            </div>

            <div className="mt-10 grid gap-6 lg:grid-cols-3">
              {screenshots.map((shot, index) => (
                <button
                  key={shot.src}
                  type="button"
                  onClick={() => setSelectedScreenshot(shot)}
                  className="group rounded-[28px] border border-slate-200/80 bg-slate-50/80 p-4 text-left shadow-[0_14px_35px_rgba(15,23,42,0.06)] transition duration-300 hover:scale-[1.02] hover:shadow-[0_22px_50px_rgba(15,23,42,0.12)]"
                >
                  <div className="overflow-hidden rounded-[20px] border border-slate-200 bg-white">
                    <img src={shot.src} alt={shot.title} className="h-auto w-full object-cover transition duration-500 group-hover:scale-[1.04]" />
                  </div>
                  <div className="mt-4 flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-700">0{index + 1}</p>
                      <h3 className="mt-2 text-xl font-black tracking-tight text-slate-950">{shot.title}</h3>
                    </div>
                    <span className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-slate-700 transition group-hover:border-cyan-400 group-hover:text-cyan-700">
                      Open
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-7 text-slate-600">{shot.description}</p>
                </button>
              ))}
            </div>
          </section>

          <section className="mt-20 grid gap-6 lg:grid-cols-3">
            {differentiators.map((item, index) => (
              <article
                key={item.title}
                className="rounded-[30px] border border-white/85 bg-white/80 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur [animation:card-rise_500ms_ease-out]"
                style={{ animationDelay: `${index * 120}ms` }}
              >
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-700">0{index + 1}</p>
                <h3 className="mt-4 text-2xl font-black tracking-tight text-slate-950">{item.title}</h3>
                <p className="mt-4 text-sm leading-7 text-slate-600">{item.description}</p>
              </article>
            ))}
          </section>

          <section className="mt-20 grid gap-8 lg:grid-cols-[0.92fr_1.08fr]">
            <div className="rounded-[34px] border border-slate-200/80 bg-slate-950 p-7 text-white shadow-[0_30px_120px_rgba(15,23,42,0.22)]">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-orange-200">Why teams switch</p>
              <h2 className="mt-4 text-3xl font-black tracking-tight">Spreadsheets show what happened. This shows where customer data becomes revenue action.</h2>
              <p className="mt-4 max-w-xl text-sm leading-7 text-slate-300">
                Owners, branch managers, and platform admins need one operating view. Customer Revenue Intelligence turns raw customer records into prioritized action without asking your team to decode the patterns manually.
              </p>
            </div>

            <div className="grid gap-4">
              {proofPoints.map((item) => (
                <div
                  key={item}
                  className="rounded-[28px] border border-white/80 bg-white/80 p-5 shadow-[0_16px_40px_rgba(15,23,42,0.08)] backdrop-blur"
                >
                  <div className="flex items-start gap-4">
                    <div className="mt-1 h-10 w-10 flex-none rounded-2xl bg-[linear-gradient(135deg,#fb923c_0%,#06b6d4_100%)]" />
                    <p className="text-base leading-7 text-slate-700">{item}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section id="pricing" className="mt-20 rounded-[36px] border border-white/80 bg-white/82 p-8 shadow-[0_30px_100px_rgba(15,23,42,0.12)] backdrop-blur lg:p-10">
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-700">Pricing</p>
              <h2 className="mt-4 text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">Choose the plan that fits your business, then start with a 14-day free trial.</h2>
              <p className="mt-4 text-sm leading-7 text-slate-600 sm:text-base">
                Start with a guided setup, give your team initial training, and move into a pricing tier built around customer visibility, revenue focus, and practical follow-up.
              </p>
            </div>

            <div className="mt-10 grid gap-6 lg:grid-cols-2">
              {plans.map((plan, index) => (
                <article
                  key={plan.name}
                  className={`rounded-[30px] border p-7 shadow-[0_18px_50px_rgba(15,23,42,0.08)] ${
                    index === 1
                      ? 'border-slate-900 bg-[linear-gradient(145deg,#0f172a_0%,#164e63_48%,#9a3412_100%)] text-white'
                      : 'border-white/80 bg-white text-slate-900'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className={`text-sm font-semibold uppercase tracking-[0.22em] ${index === 1 ? 'text-cyan-100' : 'text-cyan-700'}`}>
                        {plan.name}
                      </p>
                      <h3 className="mt-4 text-4xl font-black tracking-tight">
                        {plan.price}
                        <span className={`ml-1 text-base font-semibold ${index === 1 ? 'text-slate-200' : 'text-slate-500'}`}>{plan.cadence}</span>
                      </h3>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${index === 1 ? 'bg-white/12 text-orange-100' : 'bg-orange-100 text-orange-700'}`}>
                      Initial training included
                    </span>
                  </div>

                  <p className={`mt-5 text-sm leading-7 ${index === 1 ? 'text-slate-200' : 'text-slate-600'}`}>{plan.description}</p>

                  <div className="mt-6 space-y-3">
                    {plan.features.map((feature) => (
                      <div key={feature} className="flex items-start gap-3">
                        <span className={`mt-1 h-2.5 w-2.5 rounded-full ${index === 1 ? 'bg-orange-300' : 'bg-cyan-600'}`} />
                        <p className={`text-sm leading-7 ${index === 1 ? 'text-slate-100' : 'text-slate-700'}`}>{feature}</p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                    <Link
                      to="/register"
                      className={`inline-flex items-center justify-center rounded-full px-5 py-3 text-sm font-semibold transition hover:translate-y-[-1px] ${
                        index === 1
                          ? 'bg-slate-50 text-slate-950 shadow-[0_12px_28px_rgba(15,23,42,0.18)] hover:bg-white'
                          : 'bg-[linear-gradient(135deg,#111827_0%,#0f766e_50%,#c2410c_100%)] text-white'
                      }`}
                    >
                      Start your 14-day free trial
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="mt-20 rounded-[36px] border border-white/80 bg-[linear-gradient(135deg,rgba(15,23,42,0.96)_0%,rgba(21,94,117,0.94)_50%,rgba(194,65,12,0.88)_100%)] p-8 text-white shadow-[0_35px_120px_rgba(15,23,42,0.24)] lg:flex lg:items-center lg:justify-between lg:gap-10">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-orange-200">Start smarter growth</p>
              <h2 className="mt-4 text-3xl font-black tracking-tight sm:text-4xl">Give every business one clear system that turns customer data into revenue decisions.</h2>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-200">
                Launch with a 14-day trial, upload your existing customer history, and move from scattered reports to one disciplined system for revenue visibility and follow-up action.
              </p>
            </div>

            <div className="mt-6 flex flex-col gap-3 sm:flex-row lg:mt-0 lg:flex-col">
              <Link
                to="/register"
                className="inline-flex items-center justify-center rounded-full bg-slate-50 px-6 py-3 text-base font-semibold text-slate-900 shadow-[0_12px_28px_rgba(15,23,42,0.18)] transition hover:bg-white"
              >
                Create an account
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center justify-center rounded-full border border-white/30 bg-white/14 px-6 py-3 text-base font-semibold text-white transition hover:bg-white/20"
              >
                Sign in
              </Link>
            </div>
          </section>

          <section id="contact" className="mt-20 rounded-[36px] border border-white/80 bg-white/82 p-8 shadow-[0_24px_80px_rgba(15,23,42,0.08)] backdrop-blur lg:p-10">
            <div className="grid gap-10 lg:grid-cols-[0.95fr_1.05fr]">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-700">Contact</p>
                <h2 className="mt-4 text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">Stay close to the team behind the system.</h2>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600 sm:text-base">
                  Ask about setup, pricing, onboarding, or the right plan for your business. You can also subscribe for product updates and launch news.
                </p>

                <div className="mt-8 space-y-4">
                  <div className="rounded-[24px] border border-slate-200 bg-slate-50/80 p-5">
                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Email</p>
                    <a href="mailto:transeffex@gmail.com" className="mt-2 block text-lg font-semibold text-slate-950 hover:text-cyan-700">
                      transeffex@gmail.com
                    </a>
                  </div>
                  <div className="rounded-[24px] border border-slate-200 bg-slate-50/80 p-5">
                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Phone</p>
                    <a href="tel:0781290496" className="mt-2 block text-lg font-semibold text-slate-950 hover:text-cyan-700">
                      0781290496
                    </a>
                  </div>
                </div>
              </div>

              <div className="space-y-6">
                <div className="rounded-[28px] border border-slate-200 bg-slate-50/80 p-6">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-700">Subscribe</p>
                  <h3 className="mt-3 text-2xl font-black tracking-tight text-slate-950">Get updates in your inbox.</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-600">
                    Subscribe and your email will be prepared for delivery to transeffex@gmail.com so the team can add you to updates.
                  </p>

                  <form onSubmit={handleSubscribe} className="mt-6 flex flex-col gap-3 sm:flex-row">
                    <input
                      type="email"
                      value={subscriberEmail}
                      onChange={(event) => setSubscriberEmail(event.target.value)}
                      placeholder="name@business.com"
                      className="w-full rounded-full border border-slate-300 bg-white px-5 py-3 text-sm text-slate-900 outline-none transition focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100"
                    />
                    <button
                      type="submit"
                      className="inline-flex items-center justify-center rounded-full bg-[linear-gradient(135deg,#111827_0%,#0f766e_50%,#c2410c_100%)] px-5 py-3 text-sm font-semibold text-white transition hover:translate-y-[-1px]"
                    >
                      Subscribe
                    </button>
                  </form>
                </div>

                <div className="rounded-[28px] border border-slate-200 bg-slate-950 p-6 text-white">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-orange-200">Social</p>
                  <h3 className="mt-3 text-2xl font-black tracking-tight">Follow the product as it grows.</h3>
                  <div className="mt-6 flex flex-wrap gap-3">
                    <a href="https://www.linkedin.com/mynetwork/grow/" className="rounded-full border border-white/12 bg-white/8 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/14">
                      LinkedIn
                    </a>
                    <a href="https://www.instagram.com/transeffex/" className="rounded-full border border-white/12 bg-white/8 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/14">
                      Instagram
                    </a>
                    <a href="https://x.com/transeffex" className="rounded-full border border-white/12 bg-white/8 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/14">
                      X
                    </a>

                    <a href="https://www.tiktok.com/@transeffexsolution" className="rounded-full border border-white/12 bg-white/8 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/14">
                      Tiktok
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </main>
      </div>

      {selectedScreenshot ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/85 px-4 py-8 backdrop-blur-sm"
          onClick={() => setSelectedScreenshot(null)}
        >
          <div
            className="w-full max-w-6xl rounded-[30px] border border-white/10 bg-slate-900/95 p-4 shadow-[0_35px_120px_rgba(15,23,42,0.5)] lg:p-6"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-200">Product Screen</p>
                <h3 className="mt-2 text-2xl font-black tracking-tight text-white">{selectedScreenshot.title}</h3>
                <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-300">{selectedScreenshot.description}</p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedScreenshot(null)}
                className="rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/16"
              >
                Close
              </button>
            </div>

            <div className="overflow-hidden rounded-[24px] border border-white/10 bg-slate-950">
              <img src={selectedScreenshot.src} alt={selectedScreenshot.title} className="h-auto w-full object-contain" />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}