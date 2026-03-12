import axios from 'axios'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import BusinessConfigPanel from '../components/BusinessConfigPanel'
import CSVUploadDialog from '../components/CSVUploadDialog'
import {
  authAPI,
  type CustomerSegment,
  dashboardAPI,
  type DashboardLocationOption,
  type DashboardMetricsResponse,
  type DashboardRecommendationsResponse,
  type SnapshotComparisonResponse,
  type VipConcentrationResponse,
} from '../services/api'
import { useAuthStore } from '../stores/authStore'

type ComparisonPeriod = 'month' | 'quarter'

type ComparisonOffset = 1 | 2

const formatDate = (value: string | null) => {
  if (!value) {
    return 'No data yet'
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

const formatSignedValue = (value: number, formatter: (input: number) => string = (input) => input.toLocaleString()) => {
  if (value === 0) {
    return formatter(0)
  }

  return `${value > 0 ? '+' : '-'}${formatter(Math.abs(value))}`
}

const extractApiDetail = (error: unknown, fallback: string) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail

    if (typeof detail === 'string') {
      return detail
    }
  }

  return fallback
}

const formatSegmentLabel = (segment: string) => segment.replace('_', ' ')

const formatComparisonDepthLabel = (value: ComparisonOffset) =>
  value === 1 ? 'Previous month' : 'Two months back'

const segmentDescriptions: Record<CustomerSegment, string> = {
  churned: 'Recovery worklist for customers who are already beyond the healthy purchase threshold.',
  at_risk: 'Priority follow-up list for customers whose behavior is weakening right now.',
  active: 'Healthy customers who still need nurturing before they become truly loyal.',
  loyal: 'Best customers to protect, learn from, and use for retention and upsell strategy.',
}

const segmentOrder: CustomerSegment[] = ['churned', 'at_risk', 'active', 'loyal']

const segmentStyles: Record<string, string> = {
  churned: 'bg-rose-100 text-rose-700',
  at_risk: 'bg-amber-100 text-amber-800',
  active: 'bg-sky-100 text-sky-700',
  loyal: 'bg-emerald-100 text-emerald-700',
}

export default function Dashboard() {
  const navigate = useNavigate()
  const clearAuth = useAuthStore((state) => state.clearAuth)
  const user = useAuthStore((state) => state.user)

  const [metrics, setMetrics] = useState<DashboardMetricsResponse | null>(null)
  const [recommendations, setRecommendations] =
    useState<DashboardRecommendationsResponse | null>(null)
  const [locations, setLocations] = useState<DashboardLocationOption[]>([])
  const [selectedLocationId, setSelectedLocationId] = useState<number | undefined>(undefined)
  const [comparisonOffset, setComparisonOffset] = useState<ComparisonOffset>(1)
  const [isInitialLoading, setIsInitialLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [comparison, setComparison] = useState<SnapshotComparisonResponse | null>(null)
  const [vipAnalysis, setVipAnalysis] = useState<VipConcentrationResponse | null>(null)
  const [comparisonNotice, setComparisonNotice] = useState('')
  const [vipNotice, setVipNotice] = useState('')

  const segmentCards = metrics
    ? segmentOrder.map((segmentKey) => {
        const summary = metrics.segment_summary.find((item) => item.segment === segmentKey)

        return {
          segment: segmentKey,
          count: summary?.count ?? 0,
          total_at_risk_value: summary?.total_at_risk_value ?? 0,
          avg_monetary: summary?.avg_monetary ?? 0,
        }
      })
    : []

  const handleLogout = async () => {
    try {
      await authAPI.logout()
    } catch (logoutError) {
      console.error('Logout request failed:', logoutError)
    } finally {
      clearAuth()
      navigate('/login')
    }
  }

  const loadDashboard = async (showFullPageLoader: boolean = false) => {
    try {
      if (showFullPageLoader) {
        setIsInitialLoading(true)
      } else {
        setIsRefreshing(true)
      }

      setError('')
      setComparisonNotice('')
      setVipNotice('')

      const [metricsResponse, recommendationsResponse, locationsResponse] = await Promise.all([
        dashboardAPI.getMetrics(selectedLocationId),
        dashboardAPI.getRecommendations(selectedLocationId),
        dashboardAPI.getLocations(),
      ])

      setMetrics(metricsResponse.data)
      setRecommendations(recommendationsResponse.data)
      setLocations(locationsResponse.data.locations)

      const [comparisonResult, vipResult] = await Promise.allSettled([
        dashboardAPI.getComparison('month', selectedLocationId, comparisonOffset),
        dashboardAPI.getVipConcentration(selectedLocationId),
      ])

      if (comparisonResult.status === 'fulfilled') {
        setComparison(comparisonResult.value.data)
      } else {
        setComparison(null)
        setComparisonNotice(
          extractApiDetail(
            comparisonResult.reason,
            'Comparison data is not available yet for this scope.'
          )
        )
      }

      if (vipResult.status === 'fulfilled') {
        setVipAnalysis(vipResult.value.data)
      } else {
        setVipAnalysis(null)
        setVipNotice(
          extractApiDetail(vipResult.reason, 'VIP concentration is not available yet for this scope.')
        )
      }
    } catch (loadError) {
      console.error('Failed to load dashboard:', loadError)
      setError('Failed to load dashboard data. Upload business transactions and score a snapshot first.')
    } finally {
      setIsInitialLoading(false)
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    loadDashboard(true)
  }, [selectedLocationId, comparisonOffset])

  if (isInitialLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,#f8fafc_0%,#e2e8f0_100%)] px-4">
        <div className="rounded-[28px] border border-slate-200 bg-white px-8 py-6 shadow-[0_20px_60px_rgba(15,23,42,0.10)]">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
            Retention Dashboard
          </p>
          <p className="mt-3 text-lg font-black text-slate-900">Loading the latest business snapshot...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.12),_transparent_25%),radial-gradient(circle_at_top_right,_rgba(16,185,129,0.10),_transparent_20%),linear-gradient(180deg,_#f8fafc_0%,_#eef2f7_100%)] px-4 py-6 md:px-8">
      <div className="mx-auto max-w-7xl space-y-8">
        <section className="overflow-hidden rounded-[32px] border border-slate-200/80 bg-[linear-gradient(140deg,#0f172a_0%,#132c44_48%,#164e63_100%)] text-white shadow-[0_32px_120px_rgba(15,23,42,0.24)]">
          <div className="grid gap-6 px-6 py-8 lg:grid-cols-[1.2fr_0.8fr] lg:px-8">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-cyan-200">
                Retention Command Center
              </p>
              <h1 className="mt-4 max-w-3xl text-4xl font-black tracking-tight text-white">
                Customer Intelligent System  built on the real data window already stored for your  business.
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-200">
                Welcome {user?.email}. This dashboard shows the current snapshot date, the scoring window behind the score,
                and the actual transaction coverage already available in the database.
              </p>

              {metrics && (
                <div className="mt-6 grid gap-3 md:grid-cols-3">
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-300">Current snapshot</p>
                    <p className="mt-2 text-lg font-black text-white">
                      {formatDate(metrics.current_reference_date)}
                    </p>
                    <p className="text-xs text-slate-300">Latest stored reference date</p>
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-300">Scoring window</p>
                    <p className="mt-2 text-sm font-semibold text-white">
                      {formatDate(metrics.scoring_window_start)}
                    </p>
                    <p className="text-xs text-slate-300">to {formatDate(metrics.scoring_window_end)}</p>
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-300">Stored data coverage</p>
                    <p className="mt-2 text-sm font-semibold text-white">
                      {formatDate(metrics.first_transaction_date)}
                    </p>
                    <p className="text-xs text-slate-300">to {formatDate(metrics.last_transaction_date)}</p>
                  </div>
                </div>
              )}

              {isRefreshing && (
                <p className="mt-5 text-sm font-medium text-cyan-200">Refreshing dashboard data...</p>
              )}
            </div>

            <aside className="rounded-[28px] border border-white/10 bg-white/10 p-5 backdrop-blur">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-300">Dashboard scope</p>
                  <h2 className="mt-2 text-xl font-black text-white">Business or branch view</h2>
                </div>

                <button
                  onClick={handleLogout}
                  className="rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/20"
                >
                  Logout
                </button>
                {user?.is_platform_admin && (
                  <Link
                    to="/admin/businesses"
                    className="rounded-full border border-orange-200/40 bg-orange-500/20 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-500/30"
                  >
                    Open admin
                  </Link>
                )}
              </div>

              <label htmlFor="location-filter" className="mt-5 block text-sm font-medium text-slate-200">
                Filter the analytics below
              </label>
              <select
                id="location-filter"
                value={selectedLocationId ?? ''}
                onChange={(event) =>
                  setSelectedLocationId(event.target.value ? Number(event.target.value) : undefined)
                }
                className="mt-3 block w-full rounded-2xl border border-white/10 bg-slate-950/60 px-4 py-3 text-white outline-none focus:border-cyan-300"
              >
                <option value="">All locations</option>
                {locations.map((location) => (
                  <option key={location.id} value={location.id}>
                    {location.name} ({location.location_code})
                  </option>
                ))}
              </select>

              {recommendations && (
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-300">Churned customers</p>
                    <p className="mt-2 text-2xl font-black text-white">{recommendations.churned_count}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-300">At risk customers</p>
                    <p className="mt-2 text-2xl font-black text-white">{recommendations.at_risk_count}</p>
                  </div>
                </div>
              )}
            </aside>
          </div>
        </section>

        {user?.business_id && (
          <section className="space-y-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                Operations Studio
              </p>
              <h2 className="mt-2 text-2xl font-black text-slate-950">
                Upload and retention rules live outside the analytics cards
              </h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                Review thresholds, confirm mapping during upload, and refresh snapshots without mixing operational controls into the analytics area.
              </p>
            </div>

            <div className="grid gap-6 xl:grid-cols-[0.88fr_1.12fr]">
              <BusinessConfigPanel
                businessId={user.business_id}
                onConfigSaved={() => loadDashboard(false)}
              />
              <CSVUploadDialog
                businessId={user.business_id}
                onUploadSuccess={() => loadDashboard(false)}
              />
            </div>
          </section>
        )}

        {error && (
          <div className="rounded-[24px] border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700 shadow-sm">
            {error}
          </div>
        )}

        {metrics && (
          <section className="space-y-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                Analytics Snapshot
              </p>
              <h2 className="mt-2 text-2xl font-black text-slate-950">Current business performance window</h2>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-[28px] border border-white/70 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
                <p className="text-sm font-medium text-slate-500">Total customers</p>
                <p className="mt-3 text-3xl font-black text-slate-900">{metrics.total_customers.toLocaleString()}</p>
              </div>

              <div className="rounded-[28px] border border-white/70 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
                <p className="text-sm font-medium text-slate-500">Total revenue</p>
                <p className="mt-3 text-3xl font-black text-slate-900">{formatCurrency(metrics.total_revenue)}</p>
              </div>

              <div className="rounded-[28px] border border-amber-200 bg-amber-50/90 p-6 shadow-[0_18px_60px_rgba(217,119,6,0.10)]">
                <p className="text-sm font-medium text-amber-700">Revenue at risk</p>
                <p className="mt-3 text-3xl font-black text-amber-700">{formatCurrency(metrics.revenue_at_risk)}</p>
              </div>

              <div className="rounded-[28px] border border-white/70 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
                <p className="text-sm font-medium text-slate-500">Average customer value</p>
                <p className="mt-3 text-3xl font-black text-slate-900">{formatCurrency(metrics.avg_customer_value)}</p>
              </div>
            </div>

            <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
              <div className="rounded-[28px] border border-white/70 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                  <div>
                    <h3 className="text-xl font-black text-slate-900">Customer segments</h3>
                    <p className="mt-2 text-sm text-slate-600">
                      The dashboard stays high level here. Open a segment card to work on the customers inside it.
                    </p>
                  </div>
                  <p className="text-sm text-slate-500">Four cards, four worklists, one stored snapshot.</p>
                </div>

                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  {segmentCards.map((segment) => (
                    <Link
                      key={segment.segment}
                      to={`/segments/${segment.segment}${selectedLocationId ? `?locationId=${selectedLocationId}` : ''}`}
                      className="group rounded-[24px] border border-slate-200 bg-slate-50/80 p-5 transition hover:-translate-y-1 hover:border-slate-300 hover:bg-white hover:shadow-[0_20px_45px_rgba(15,23,42,0.10)]"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <span
                          className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${segmentStyles[segment.segment] ?? 'bg-slate-100 text-slate-700'}`}
                        >
                          {formatSegmentLabel(segment.segment)}
                        </span>
                        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400 transition group-hover:text-slate-600">
                          Open worklist
                        </span>
                      </div>

                      <p className="mt-4 text-3xl font-black text-slate-900">
                        {segment.count.toLocaleString()}
                      </p>
                      <p className="mt-1 text-sm font-medium text-slate-600">customers in this segment</p>

                      <p className="mt-4 text-sm leading-6 text-slate-600">
                        {segmentDescriptions[segment.segment]}
                      </p>

                      <div className="mt-5 grid gap-3 sm:grid-cols-2">
                        <div className="rounded-2xl border border-slate-200 bg-white p-4">
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Average monetary</p>
                          <p className="mt-2 text-sm font-semibold text-slate-900">
                            {formatCurrency(segment.avg_monetary)}
                          </p>
                        </div>

                        <div className="rounded-2xl border border-slate-200 bg-white p-4">
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">At-risk value</p>
                          <p className="mt-2 text-sm font-semibold text-slate-900">
                            {formatCurrency(segment.total_at_risk_value)}
                          </p>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>

              <div className="rounded-[28px] border border-white/70 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
                <h3 className="text-xl font-black text-slate-900">Top products in the current window</h3>
                <div className="mt-5 space-y-3">
                  {metrics.top_products.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
                      No products have been summarized for the current scope yet.
                    </div>
                  ) : (
                    metrics.top_products.map((product) => (
                      <div
                        key={product.product_name}
                        className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="text-base font-semibold text-slate-900">{product.product_name}</p>
                            <p className="mt-1 text-sm text-slate-600">
                              {product.times_purchased.toLocaleString()} purchase events
                            </p>
                          </div>
                          <p className="text-sm font-semibold text-slate-900">
                            {formatCurrency(product.total_revenue)} revenue
                          </p>
                        </div>

                        <p className="mt-3 text-sm text-slate-600">
                          Quantity sold: {product.total_quantity_sold.toLocaleString()}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </section>
        )}

        {(vipAnalysis || comparison || vipNotice || comparisonNotice) && (
          <section className="space-y-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                  Advanced Analytics
                </p>
                <h2 className="mt-2 text-2xl font-black text-slate-950">
                  Revenue concentration and snapshot movement
                </h2>
              </div>
              <p className="text-sm text-slate-600">
                These blocks explain where the money is concentrated and whether the business is improving over time.
              </p>
            </div>

            <div className="grid gap-6 xl:grid-cols-[0.98fr_1.02fr]">
              <section className="rounded-[28px] border border-white/70 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                      VIP Concentration
                    </p>
                    <h3 className="mt-2 text-xl font-black text-slate-900">Who carries most of the current revenue</h3>
                  </div>
                  {vipAnalysis && (
                    <div className="flex items-center gap-3">
                      <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
                        Top {Math.round(vipAnalysis.vip_share_threshold * 100)}%
                      </span>
                      <Link
                        to={`/vip-members${selectedLocationId ? `?locationId=${selectedLocationId}` : ''}`}
                        className="inline-flex items-center rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-800 transition hover:border-slate-300 hover:bg-slate-50"
                      >
                        View all VIP members
                      </Link>
                    </div>
                  )}
                </div>

                {vipAnalysis ? (
                  <>
                    <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                      <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 xl:col-span-2">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Revenue concentration</p>
                        <p className="mt-2 text-3xl font-black text-slate-900">
                          {formatPercent(vipAnalysis.vip_revenue_share)}
                        </p>
                        <p className="mt-1 text-sm text-slate-600">
                          of current-window revenue comes from {vipAnalysis.vip_customer_count.toLocaleString()} customers.
                        </p>
                      </div>

                      <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">VIP revenue</p>
                        <p className="mt-2 text-lg font-black text-slate-900">{formatCurrency(vipAnalysis.vip_revenue)}</p>
                      </div>

                      <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Non-VIP revenue</p>
                        <p className="mt-2 text-lg font-black text-slate-900">{formatCurrency(vipAnalysis.non_vip_revenue)}</p>
                      </div>
                    </div>

                    <div className="mt-5 space-y-3">
                      {vipAnalysis.top_customers.map((customer) => (
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

                              <h4 className="mt-3 text-lg font-black text-slate-900">
                                {customer.customer_name || customer.customer_id}
                              </h4>
                              <p className="mt-1 text-sm text-slate-600">Identifier: {customer.customer_id}</p>
                            </div>

                            <div className="grid gap-3 sm:grid-cols-2 lg:min-w-[280px]">
                              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Window revenue</p>
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
                          </div>
                        </article>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
                    {vipNotice || 'VIP concentration is not available yet for this scope.'}
                  </div>
                )}
              </section>

              <section className="rounded-[28px] border border-white/70 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                      Snapshot Comparison
                    </p>
                    <h3 className="mt-2 text-xl font-black text-slate-900">Current versus previous upload story</h3>
                  </div>

                  <div className="inline-flex rounded-full border border-slate-200 bg-slate-50 p-1">
                    {([1, 2] as ComparisonOffset[]).map((offset) => (
                      <button
                        key={offset}
                        type="button"
                        onClick={() => setComparisonOffset(offset)}
                        className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                          comparisonOffset === offset
                            ? 'bg-slate-950 text-white'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        {formatComparisonDepthLabel(offset)}
                      </button>
                    ))}
                  </div>
                </div>

                {comparison ? (
                  <>
                    <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                      <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 xl:col-span-2">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Comparison window</p>
                        <p className="mt-2 text-sm font-semibold text-slate-900">
                          {formatDate(comparison.previous_reference_date)} to {formatDate(comparison.current_reference_date)}
                        </p>
                        <p className="mt-1 text-sm text-slate-600">
                          This compares the latest stored snapshot with the {comparison.snapshot_offset === 1 ? 'previous monthly snapshot' : 'snapshot from two uploads back'}.
                        </p>
                      </div>

                      <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Recovered customers</p>
                        <p className="mt-2 text-2xl font-black text-emerald-700">
                          {comparison.recovered_customers.toLocaleString()}
                        </p>
                      </div>
                    </div>

                    <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                      <div className="rounded-2xl border border-slate-200 bg-white p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Window revenue change</p>
                        <p className={`mt-2 text-lg font-black ${comparison.window_revenue_delta >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                          {formatSignedValue(comparison.window_revenue_delta, formatCurrency)}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-white p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Revenue at risk change</p>
                        <p className={`mt-2 text-lg font-black ${comparison.revenue_at_risk_delta <= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                          {formatSignedValue(comparison.revenue_at_risk_delta, formatCurrency)}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-white p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Improved customers</p>
                        <p className="mt-2 text-lg font-black text-emerald-700">{comparison.improved_customers.toLocaleString()}</p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-white p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Slipped customers</p>
                        <p className="mt-2 text-lg font-black text-rose-700">{comparison.slipped_customers.toLocaleString()}</p>
                      </div>
                    </div>

                    <div className="mt-5 grid gap-4 md:grid-cols-3">
                      <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Improved</p>
                        <p className="mt-2 text-2xl font-black text-emerald-700">{comparison.improved_customers}</p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Unchanged</p>
                        <p className="mt-2 text-2xl font-black text-slate-900">{comparison.unchanged_customers}</p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Worsened</p>
                        <p className="mt-2 text-2xl font-black text-rose-700">{comparison.worsened_customers}</p>
                      </div>
                    </div>

                    <div className="mt-5 space-y-3">
                      {comparison.segment_changes.map((segmentChange) => (
                        <div
                          key={segmentChange.segment}
                          className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4"
                        >
                          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                            <div className="flex items-center gap-3">
                              <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${segmentStyles[segmentChange.segment] ?? 'bg-slate-100 text-slate-700'}`}>
                                {formatSegmentLabel(segmentChange.segment)}
                              </span>
                              <span className="text-sm text-slate-600">
                                {segmentChange.previous_count.toLocaleString()} to {segmentChange.current_count.toLocaleString()} customers
                              </span>
                            </div>

                            <span className={`text-sm font-semibold ${segmentChange.delta <= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                              {formatSignedValue(segmentChange.delta)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
                    {comparisonNotice || 'Comparison data is not available yet for this scope.'}
                  </div>
                )}
              </section>
            </div>
          </section>
        )}

        {recommendations && (
          <section className="rounded-[32px] border border-slate-200/80 bg-white/90 p-6 shadow-[0_20px_70px_rgba(15,23,42,0.08)]">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                  Recommended Actions
                </p>
                <h2 className="mt-2 text-2xl font-black text-slate-950">Customers who need attention now</h2>
              </div>
              <p className="text-sm text-slate-600">
                Ordered from the stored scoring snapshot for the current dashboard scope.
              </p>
            </div>

            <div className="mt-6 space-y-4">
              {recommendations.recommendations.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
                  No intervention recommendations are available yet for this scope.
                </div>
              ) : (
                recommendations.recommendations.map((recommendation) => (
                  <article
                    key={`${recommendation.customer_id}-${recommendation.recommended_action}`}
                    className="rounded-[24px] border border-slate-200 bg-slate-50/80 p-5"
                  >
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <div className="flex flex-wrap items-center gap-3">
                          <span
                            className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${segmentStyles[recommendation.segment] ?? 'bg-slate-100 text-slate-700'}`}
                          >
                            {formatSegmentLabel(recommendation.segment)}
                          </span>
                          <span className="text-sm text-slate-600">Urgency: {recommendation.urgency}</span>
                          <span className="text-sm text-slate-600">
                            Churn risk: {formatPercent(recommendation.churn_probability)}
                          </span>
                        </div>

                        <h3 className="mt-3 text-lg font-black text-slate-900">
                          Customer {recommendation.customer_id}
                        </h3>
                        <p className="mt-2 text-sm leading-6 text-slate-700">
                          {recommendation.reasoning}
                        </p>
                      </div>

                      <div className="min-w-[220px] rounded-2xl border border-slate-200 bg-white p-4">
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                          Recommended action
                        </p>
                        <p className="mt-2 text-sm font-semibold text-slate-900">
                          {recommendation.recommended_action}
                        </p>
                        <Link
                          to={`/customers/${recommendation.customer_id}`}
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
        )}
      </div>
    </div>
  )
}
