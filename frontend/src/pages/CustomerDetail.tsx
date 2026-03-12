import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { customerAPI } from '../services/api'

type CustomerTransactionSummary = {
  id: number
  product_name: string
  amount: number
  quantity: number
  purchase_date: string
  category: string | null
}

type CustomerPredictionSummary = {
  reference_date: string
  segment: string
  churn_probability: number
  recency: number
  frequency: number
  monetary: number
}

type CustomerDetailResponse = {
  id: number
  customer_id: string
  name: string | null
  phone: string | null
  email: string | null
  business_id: number
  last_purchase_date: string | null
  total_spent: number
  total_purchases: number
  current_prediction: CustomerPredictionSummary | null
  recent_transactions: CustomerTransactionSummary[]
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

const formatDateTime = (value: string) =>
  new Date(value).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })

const formatCurrency = (value: number) =>
  value.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })

const formatPercent = (value: number) => `${Math.round(value * 100)}%`

const formatSegmentLabel = (value: string) => value.replace('_', ' ')

const segmentStyles: Record<string, string> = {
  churned: 'border-rose-200 bg-rose-50 text-rose-800',
  at_risk: 'border-amber-200 bg-amber-50 text-amber-800',
  active: 'border-sky-200 bg-sky-50 text-sky-800',
  loyal: 'border-emerald-200 bg-emerald-50 text-emerald-800',
}

export default function CustomerDetail() {
  const { customerId } = useParams()
  const [customer, setCustomer] = useState<CustomerDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const loadCustomer = async () => {
      try {
        setLoading(true)
        setError('')

        if (!customerId) {
          setError('Customer id is missing.')
          return
        }

        const response = await customerAPI.getDetail(customerId)
        setCustomer(response.data)
      } catch (error) {
        console.error('Failed to load customer detail:', error)
        setError('Failed to load customer detail.')
      } finally {
        setLoading(false)
      }
    }

    loadCustomer()
  }, [customerId])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,#f8fafc_0%,#e2e8f0_100%)] px-4">
        <div className="rounded-[28px] border border-slate-200 bg-white px-8 py-6 shadow-[0_20px_60px_rgba(15,23,42,0.10)]">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Customer Detail</p>
          <p className="mt-3 text-lg font-black text-slate-900">Loading customer detail...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[linear-gradient(180deg,#f8fafc_0%,#eef2f7_100%)] p-8">
        <div className="mx-auto max-w-5xl rounded-[28px] border border-rose-200 bg-white p-8 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
          <p className="text-rose-700">{error}</p>
          <Link
            to="/dashboard"
            className="mt-4 inline-flex items-center rounded-full bg-[linear-gradient(135deg,#0f172a_0%,#155e75_55%,#0f766e_100%)] px-4 py-2 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(15,23,42,0.12)] transition hover:translate-y-[-1px]"
          >
            Back to dashboard
          </Link>
        </div>
      </div>
    )
  }

  if (!customer) {
    return null
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.12),_transparent_22%),radial-gradient(circle_at_top_right,_rgba(16,185,129,0.10),_transparent_18%),linear-gradient(180deg,_#f8fafc_0%,_#eef2f7_100%)] p-8">
      <div className="mx-auto max-w-7xl space-y-8">
        <section className="overflow-hidden rounded-[32px] border border-slate-200/80 bg-[linear-gradient(140deg,#0f172a_0%,#132c44_48%,#164e63_100%)] text-white shadow-[0_32px_120px_rgba(15,23,42,0.24)]">
          <div className="grid gap-6 px-6 py-8 lg:grid-cols-[1.1fr_0.9fr] lg:px-8">
            <div>
              <Link
                to="/dashboard"
                className="inline-flex items-center rounded-full border border-cyan-200/20 bg-[linear-gradient(135deg,rgba(34,211,238,0.22),rgba(255,255,255,0.12))] px-4 py-2 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(15,23,42,0.14)] transition hover:bg-[linear-gradient(135deg,rgba(34,211,238,0.28),rgba(255,255,255,0.16))]"
              >
                Back to dashboard
              </Link>

              <p className="mt-5 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-200">
                Customer Action Workspace
              </p>
              <h1 className="mt-4 text-4xl font-black tracking-tight text-white">
                {customer.name || customer.customer_id}
              </h1>
              <p className="mt-2 text-sm text-slate-200">Identifier: {customer.customer_id}</p>

              <div className="mt-6 flex flex-wrap items-center gap-3">
                <span
                  className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${
                    customer.current_prediction
                      ? segmentStyles[customer.current_prediction.segment] ?? 'border-white/15 bg-white/10 text-white'
                      : 'border-white/15 bg-white/10 text-white'
                  }`}
                >
                  {customer.current_prediction
                    ? formatSegmentLabel(customer.current_prediction.segment)
                    : 'No current snapshot'}
                </span>

                {customer.current_prediction && (
                  <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-white">
                    Churn risk {formatPercent(customer.current_prediction.churn_probability)}
                  </span>
                )}
              </div>

              <p className="mt-6 max-w-2xl text-sm leading-7 text-slate-200">
                This page combines customer identity, contact options, the current risk snapshot, and recent transaction history so the business can decide what to do next for one customer.
              </p>
            </div>

            <aside className="rounded-[28px] border border-white/10 bg-white/10 p-5 backdrop-blur">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-300">Customer summary</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-300">Lifetime spend</p>
                  <p className="mt-2 text-2xl font-black text-white">{formatCurrency(customer.total_spent)}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-300">Purchase count</p>
                  <p className="mt-2 text-2xl font-black text-white">{customer.total_purchases}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/10 p-4 sm:col-span-2">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-300">Last purchase date</p>
                  <p className="mt-2 text-sm font-semibold text-white">{formatDate(customer.last_purchase_date)}</p>
                </div>
              </div>
            </aside>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
          <aside className="space-y-6">
            <div className="rounded-[28px] border border-slate-200/80 bg-white p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Contact Channels</p>
              <h2 className="mt-2 text-2xl font-black text-slate-950">How the business can reach this customer</h2>

              <div className="mt-5 space-y-3">
                <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Phone</p>
                  <p className="mt-2 text-sm font-semibold text-slate-900">{customer.phone || 'Not available'}</p>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Email</p>
                  <p className="mt-2 text-sm font-semibold text-slate-900">{customer.email || 'Not available'}</p>
                </div>
              </div>
            </div>

            <div className="rounded-[28px] border border-slate-200/80 bg-white p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">How To Read The Score</p>
              <h2 className="mt-2 text-2xl font-black text-slate-950">Why this snapshot matters</h2>
              <div className="mt-5 space-y-4 text-sm leading-6 text-slate-600">
                <p>
                  Recency tells you how long it has been since the last purchase. Frequency tells you how often this customer bought inside the scoring window. Monetary tells you how much value they generated in that same window.
                </p>
                <p>
                  The segment is the business-facing label created from those metrics. It is easier for owners to act on a segment like at risk or loyal than on raw RFM numbers alone.
                </p>
              </div>
            </div>
          </aside>

          <div className="space-y-6">
            <section className="rounded-[28px] border border-slate-200/80 bg-white p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Current Snapshot</p>
              <h2 className="mt-2 text-2xl font-black text-slate-950">Stored risk and behavior metrics</h2>

              {!customer.current_prediction ? (
                <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
                  No current prediction snapshot has been stored for this customer yet.
                </div>
              ) : (
                <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Snapshot date</p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">
                      {formatDate(customer.current_prediction.reference_date)}
                    </p>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Recency</p>
                    <p className="mt-2 text-2xl font-black text-slate-900">{customer.current_prediction.recency}</p>
                    <p className="text-sm text-slate-600">Days since last purchase</p>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Frequency</p>
                    <p className="mt-2 text-2xl font-black text-slate-900">{customer.current_prediction.frequency}</p>
                    <p className="text-sm text-slate-600">Purchases in window</p>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Monetary</p>
                    <p className="mt-2 text-2xl font-black text-slate-900">{formatCurrency(customer.current_prediction.monetary)}</p>
                    <p className="text-sm text-slate-600">Spend in window</p>
                  </div>
                </div>
              )}
            </section>

            <section className="rounded-[28px] border border-slate-200/80 bg-white p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Transaction Timeline</p>
                  <h2 className="mt-2 text-2xl font-black text-slate-950">Recent transactions</h2>
                </div>
                <p className="text-sm text-slate-600">The most recent transactions help explain the current segment and spend pattern.</p>
              </div>

              <div className="mt-6 space-y-3">
                {customer.recent_transactions.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
                    No recent transactions found.
                  </div>
                ) : (
                  customer.recent_transactions.map((transaction) => (
                    <div
                      key={transaction.id}
                      className="flex flex-col gap-3 rounded-[24px] border border-slate-200 bg-slate-50/80 p-5 md:flex-row md:items-start md:justify-between"
                    >
                      <div>
                        <p className="text-base font-semibold text-slate-900">{transaction.product_name}</p>
                        <p className="mt-1 text-sm text-slate-500">{formatDateTime(transaction.purchase_date)}</p>
                        {transaction.category && (
                          <p className="mt-2 text-sm text-slate-600">Category: {transaction.category}</p>
                        )}
                      </div>

                      <div className="grid gap-3 text-sm text-slate-700 md:min-w-[240px] md:grid-cols-1">
                        <div className="rounded-2xl border border-slate-200 bg-white p-4">
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Quantity</p>
                          <p className="mt-2 font-semibold text-slate-900">{transaction.quantity}</p>
                        </div>
                        <div className="rounded-2xl border border-slate-200 bg-white p-4">
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Amount</p>
                          <p className="mt-2 font-semibold text-slate-900">{formatCurrency(transaction.amount)}</p>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>
        </section>
      </div>
    </div>
  )
}