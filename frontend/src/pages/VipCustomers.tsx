import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { dashboardAPI, type VipConcentrationResponse } from '../services/api'

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

const segmentStyles: Record<string, string> = {
  churned: 'bg-rose-100 text-rose-700',
  at_risk: 'bg-amber-100 text-amber-800',
  active: 'bg-sky-100 text-sky-700',
  loyal: 'bg-emerald-100 text-emerald-700',
}

export default function VipCustomers() {
  const [searchParams] = useSearchParams()
  const [data, setData] = useState<VipConcentrationResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const selectedLocationId = searchParams.get('locationId')
  const locationId = selectedLocationId ? Number(selectedLocationId) : undefined

  useEffect(() => {
    const loadVipCustomers = async () => {
      try {
        setLoading(true)
        setError('')

        const response = await dashboardAPI.getVipConcentration(locationId, 0.2, 500)
        setData(response.data)
      } catch (loadError) {
        console.error('Failed to load VIP members:', loadError)
        setError('Failed to load VIP members for this scope.')
      } finally {
        setLoading(false)
      }
    }

    loadVipCustomers()
  }, [locationId])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,#f8fafc_0%,#e2e8f0_100%)] px-4">
        <div className="rounded-[28px] border border-slate-200 bg-white px-8 py-6 shadow-[0_20px_60px_rgba(15,23,42,0.10)]">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
            VIP Members
          </p>
          <p className="mt-3 text-lg font-black text-slate-900">Loading the VIP customer list...</p>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[linear-gradient(180deg,#f8fafc_0%,#eef2f7_100%)] px-4 py-8 md:px-8">
        <div className="mx-auto max-w-5xl rounded-[28px] border border-rose-200 bg-white p-8 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-700">VIP members</p>
          <p className="mt-3 text-lg font-black text-slate-900">{error || 'VIP data is unavailable.'}</p>
          <Link
            to={selectedLocationId ? `/dashboard?locationId=${selectedLocationId}` : '/dashboard'}
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
                VIP Members
              </p>
              <h1 className="mt-4 max-w-3xl text-4xl font-black tracking-tight text-white">
                The customers who carry the highest share of current-window revenue.
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-200">
                This list shows the top {Math.round(data.vip_share_threshold * 100)}% of customers by current-window monetary value in the latest stored snapshot.
              </p>
            </div>

            <aside className="rounded-[28px] border border-white/10 bg-white/10 p-5 backdrop-blur">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-300">VIP summary</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
                <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-300">Reference date</p>
                  <p className="mt-2 text-lg font-black text-white">{formatDate(data.current_reference_date)}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-300">VIP revenue share</p>
                  <p className="mt-2 text-3xl font-black text-white">{formatPercent(data.vip_revenue_share)}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-300">VIP customers</p>
                  <p className="mt-2 text-2xl font-black text-white">{data.vip_customer_count.toLocaleString()}</p>
                </div>
              </div>
            </aside>
          </div>
        </section>

        <section className="rounded-[28px] border border-slate-200/80 bg-white p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">VIP Worklist</p>
              <h2 className="mt-2 text-2xl font-black text-slate-950">All VIP members in the current scope</h2>
            </div>
            <p className="text-sm text-slate-600">Use this list to decide how to protect high-value customers and who needs proactive attention.</p>
          </div>

          <div className="mt-6 space-y-4">
            {data.top_customers.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
                No VIP members are available yet for this scope.
              </div>
            ) : (
              data.top_customers.map((customer) => (
                <article
                  key={`${customer.customer_id}-${customer.location_code}`}
                  className="rounded-[24px] border border-slate-200 bg-slate-50/80 p-5"
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${segmentStyles[customer.segment] ?? 'bg-slate-100 text-slate-700'}`}>
                          {formatSegmentLabel(customer.segment)}
                        </span>
                        <span className="text-sm text-slate-600">{customer.location_name} ({customer.location_code})</span>
                      </div>

                      <h3 className="mt-3 text-lg font-black text-slate-900">
                        {customer.customer_name || customer.customer_id}
                      </h3>
                      <p className="mt-1 text-sm text-slate-600">Identifier: {customer.customer_id}</p>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2 lg:min-w-[340px]">
                      <div className="rounded-2xl border border-slate-200 bg-white p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Current-window value</p>
                        <p className="mt-2 text-sm font-semibold text-slate-900">{formatCurrency(customer.monetary)}</p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-white p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Churn risk</p>
                        <p className="mt-2 text-sm font-semibold text-slate-900">{formatPercent(customer.churn_probability)}</p>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-slate-600">
                    <span>Total spent: {formatCurrency(customer.total_spent)}</span>
                    <span>Purchases: {customer.total_purchases}</span>
                    <span>Phone: {customer.phone || 'Not available'}</span>
                    <span>Email: {customer.email || 'Not available'}</span>
                  </div>

                  <Link
                    to={`/customers/${customer.customer_id}`}
                    className="mt-4 inline-flex items-center rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
                  >
                    Open customer detail
                  </Link>
                </article>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  )
}