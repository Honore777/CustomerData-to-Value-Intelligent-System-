import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import {
  dashboardAPI,
  type CustomerSegment,
  type SegmentCustomersResponse,
} from '../services/api'

const allowedSegments: CustomerSegment[] = ['churned', 'at_risk', 'active', 'loyal']

const segmentDescriptions: Record<CustomerSegment, string> = {
  churned: 'Customers who have already fallen beyond the healthy activity threshold and need recovery attention.',
  at_risk: 'Customers showing warning signs now, where timely action can still protect revenue.',
  active: 'Customers buying within a healthy rhythm, but not yet in the strongest loyalty tier.',
  loyal: 'Customers with the strongest current relationship and the best base for retention and upsell.',
}

const segmentStyles: Record<CustomerSegment, string> = {
  churned: 'border-rose-200 bg-rose-50 text-rose-800',
  at_risk: 'border-amber-200 bg-amber-50 text-amber-800',
  active: 'border-sky-200 bg-sky-50 text-sky-800',
  loyal: 'border-emerald-200 bg-emerald-50 text-emerald-800',
}

const urgencyStyles: Record<string, string> = {
  immediate: 'bg-rose-100 text-rose-700',
  high: 'bg-amber-100 text-amber-800',
  medium: 'bg-sky-100 text-sky-700',
  low: 'bg-emerald-100 text-emerald-700',
}

const formatDate = (value: string | null) => {
  if (!value) {
    return 'Not available'
  }

  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

const formatCurrency = (value: number) =>
  value.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })

const formatPercent = (value: number) => `${Math.round(value * 100)}%`

const formatSegmentLabel = (segment: string) => segment.replace('_', ' ')

export default function SegmentCustomers() {
  const { segment } = useParams()
  const [searchParams] = useSearchParams()
  const [data, setData] = useState<SegmentCustomersResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const selectedLocationId = searchParams.get('locationId')
  const locationId = selectedLocationId ? Number(selectedLocationId) : undefined

  const segmentKey = useMemo(() => {
    if (segment && allowedSegments.includes(segment as CustomerSegment)) {
      return segment as CustomerSegment
    }

    return null
  }, [segment])

  useEffect(() => {
    const loadSegmentCustomers = async () => {
      if (!segmentKey) {
        setError('Unknown segment requested.')
        setLoading(false)
        return
      }

      try {
        setLoading(true)
        setError('')

        const response = await dashboardAPI.getSegmentCustomers(segmentKey, locationId)
        setData(response.data)
      } catch (loadError) {
        console.error('Failed to load segment customers:', loadError)
        setError('Failed to load the segment customer list for this scope.')
      } finally {
        setLoading(false)
      }
    }

    loadSegmentCustomers()
  }, [segmentKey, locationId])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,#f8fafc_0%,#e2e8f0_100%)] px-4">
        <div className="rounded-[28px] border border-slate-200 bg-white px-8 py-6 shadow-[0_20px_60px_rgba(15,23,42,0.10)]">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
            Segment Worklist
          </p>
          <p className="mt-3 text-lg font-black text-slate-900">Loading the current customer snapshot...</p>
        </div>
      </div>
    )
  }

  if (error || !segmentKey || !data) {
    return (
      <div className="min-h-screen bg-[linear-gradient(180deg,#f8fafc_0%,#eef2f7_100%)] px-4 py-8 md:px-8">
        <div className="mx-auto max-w-5xl rounded-[28px] border border-rose-200 bg-white p-8 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-700">Segment view</p>
          <p className="mt-3 text-lg font-black text-slate-900">{error || 'Segment data is unavailable.'}</p>
          <Link
            to="/dashboard"
            className="mt-6 inline-flex items-center rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            Back to dashboard
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.12),_transparent_22%),radial-gradient(circle_at_top_right,_rgba(16,185,129,0.10),_transparent_18%),linear-gradient(180deg,_#f8fafc_0%,_#eef2f7_100%)] px-4 py-6 md:px-8">
      <div className="mx-auto max-w-7xl space-y-8">
        <section className="overflow-hidden rounded-[32px] border border-slate-200/80 bg-[linear-gradient(140deg,#0f172a_0%,#132c44_48%,#164e63_100%)] text-white shadow-[0_32px_120px_rgba(15,23,42,0.24)]">
          <div className="grid gap-6 px-6 py-8 lg:grid-cols-[1.15fr_0.85fr] lg:px-8">
            <div>
              <Link
                to={selectedLocationId ? `/dashboard?locationId=${selectedLocationId}` : '/dashboard'}
                className="inline-flex items-center rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/20"
              >
                Back to dashboard
              </Link>
              <p className="mt-5 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-200">
                Segment Worklist
              </p>
              <h1 className="mt-4 max-w-3xl text-4xl font-black tracking-tight text-white">
                {formatSegmentLabel(data.segment)} customers in the current scored snapshot.
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-200">
                {segmentDescriptions[data.segment]}
              </p>
            </div>

            <aside className={`rounded-[28px] border p-5 ${segmentStyles[data.segment]}`}>
              <p className="text-xs font-semibold uppercase tracking-[0.2em]">Current scope</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
                <div className="rounded-2xl bg-white/80 p-4 text-slate-900">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Reference date</p>
                  <p className="mt-2 text-lg font-black">{formatDate(data.current_reference_date)}</p>
                </div>
                <div className="rounded-2xl bg-white/80 p-4 text-slate-900">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Customers in segment</p>
                  <p className="mt-2 text-3xl font-black">{data.total_customers.toLocaleString()}</p>
                </div>
              </div>
            </aside>
          </div>
        </section>

        <section className="grid gap-6 2xl:grid-cols-[0.75fr_1.25fr]">
          <aside className="rounded-[28px] border border-slate-200/80 bg-white p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">How This Page Works</p>
            <h2 className="mt-2 text-2xl font-black text-slate-950">From dashboard overview to customer action</h2>
            <div className="mt-5 space-y-4 text-sm leading-6 text-slate-600">
              <p>
                The dashboard answers which segment needs attention. This page answers which exact customers sit inside that segment right now.
              </p>
              <p>
                Every row comes from the latest stored prediction snapshot, not from a live recalculation, so the worklist matches the numbers shown on the dashboard card.
              </p>
              <p>
                The action text is generated from the same snapshot metrics: segment, churn probability, recency, frequency, and monetary value.
              </p>
            </div>
          </aside>

          <section className="rounded-[28px] border border-slate-200/80 bg-white p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Customer Worklist</p>
                <h2 className="mt-2 text-2xl font-black text-slate-950">Customers ordered by current urgency</h2>
              </div>
              <p className="text-sm text-slate-600">Highest churn risk and strongest monetary value appear first.</p>
            </div>

            <div className="mt-6 space-y-4">
              {data.customers.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
                  No customers are currently stored in this segment for the selected scope.
                </div>
              ) : (
                data.customers.map((customer) => (
                  <article
                    key={`${customer.customer_id}-${customer.location_id}`}
                    className="rounded-[24px] border border-slate-200 bg-slate-50/80 p-5"
                  >
                    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_220px] xl:items-start">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-3">
                          <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${segmentStyles[customer.segment]}`}>
                            {formatSegmentLabel(customer.segment)}
                          </span>
                          <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${urgencyStyles[customer.urgency] ?? 'bg-slate-100 text-slate-700'}`}>
                            {customer.urgency}
                          </span>
                          <span className="text-sm text-slate-600">Churn risk: {formatPercent(customer.churn_probability)}</span>
                        </div>

                        <h3 className="mt-4 text-xl font-black text-slate-900">
                          {customer.customer_name || customer.customer_id}
                        </h3>
                        <p className="mt-1 text-sm text-slate-600">Identifier: {customer.customer_id}</p>

                        <div className="mt-4 grid gap-3 sm:grid-cols-2 2xl:grid-cols-4">
                          <div className="rounded-2xl border border-slate-200 bg-white p-4">
                            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Location</p>
                            <p className="mt-2 text-sm font-semibold text-slate-900">{customer.location_name}</p>
                            <p className="text-sm text-slate-600">{customer.location_code}</p>
                          </div>

                          <div className="rounded-2xl border border-slate-200 bg-white p-4">
                            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Monetary value</p>
                            <p className="mt-2 break-words text-sm font-semibold text-slate-900">{formatCurrency(customer.monetary)}</p>
                            <p className="text-sm text-slate-600">Current-window spend</p>
                          </div>

                          <div className="rounded-2xl border border-slate-200 bg-white p-4">
                            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Recency</p>
                            <p className="mt-2 text-sm font-semibold text-slate-900">{customer.recency} days</p>
                            <p className="text-sm text-slate-600">Last purchase: {formatDate(customer.last_purchase_date)}</p>
                          </div>

                          <div className="rounded-2xl border border-slate-200 bg-white p-4">
                            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Frequency</p>
                            <p className="mt-2 text-sm font-semibold text-slate-900">{customer.frequency}</p>
                            <p className="text-sm text-slate-600">Purchases in scoring window</p>
                          </div>
                        </div>

                        <div className="mt-4 grid gap-3 xl:grid-cols-2">
                          <div className="rounded-2xl border border-slate-200 bg-white p-4">
                            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Contact options</p>
                            <p className="mt-2 text-sm text-slate-700">Phone: {customer.phone || 'Not available'}</p>
                            <p className="text-sm text-slate-700">Email: {customer.email || 'Not available'}</p>
                          </div>

                          <div className="rounded-2xl border border-slate-200 bg-white p-4">
                            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Lifetime value</p>
                            <p className="mt-2 text-sm font-semibold text-slate-900">{formatCurrency(customer.total_spent)}</p>
                            <p className="text-sm text-slate-600">Lifetime purchases: {customer.total_purchases}</p>
                          </div>
                        </div>

                        <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Recommended action</p>
                          <p className="mt-2 text-sm font-semibold text-slate-900">{customer.recommended_action}</p>
                          <p className="mt-2 text-sm leading-6 text-slate-600">{customer.reasoning}</p>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-slate-200 bg-white p-4 xl:self-start">
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Next view</p>
                        <p className="mt-2 text-sm text-slate-700">
                          Open the customer page for transaction history and detailed review.
                        </p>
                        <Link
                          to={`/customers/${customer.customer_id}`}
                          className="mt-4 inline-flex items-center rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
                        >
                          Open customer detail
                        </Link>
                      </div>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>
        </section>
      </div>
    </div>
  )
}