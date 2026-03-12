import axios from 'axios'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { adminAPI, authAPI, type AdminBusinessSummary, type AdminBusinessUpdatePayload, type AdminReminderResponse } from '../services/api'
import { useAuthStore } from '../stores/authStore'

type StatusFilter = 'all' | 'trial' | 'active' | 'past_due' | 'cancelled'

type EditFormState = {
  name: string
  email: string
  phone: string
  country: string
  subscription_status: string
  trial_started_at: string
  trial_ends_at: string
  billing_due_date: string
  monthly_price: string
  is_active: boolean
}

const statusStyles: Record<string, string> = {
  trial: 'bg-amber-100 text-amber-800',
  active: 'bg-emerald-100 text-emerald-700',
  past_due: 'bg-rose-100 text-rose-700',
  cancelled: 'bg-slate-200 text-slate-700',
}

const formatDate = (value: string | null) => {
  if (!value) {
    return 'Not set'
  }

  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

const formatDateTime = (value: string | null) => {
  if (!value) {
    return 'Never'
  }

  return new Date(value).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const toDateInput = (value: string | null) => (value ? value.slice(0, 10) : '')

const toEditFormState = (business: AdminBusinessSummary): EditFormState => ({
  name: business.name,
  email: business.email,
  phone: business.phone ?? '',
  country: business.country,
  subscription_status: business.subscription_status,
  trial_started_at: toDateInput(business.trial_started_at),
  trial_ends_at: toDateInput(business.trial_ends_at),
  billing_due_date: toDateInput(business.billing_due_date),
  monthly_price: business.monthly_price == null ? '' : String(business.monthly_price),
  is_active: business.is_active,
})

const extractApiDetail = (error: unknown, fallback: string) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      return detail
    }
  }

  return fallback
}

export default function AdminBusinesses() {
  const navigate = useNavigate()
  const clearAuth = useAuthStore((state) => state.clearAuth)
  const user = useAuthStore((state) => state.user)

  const [businesses, setBusinesses] = useState<AdminBusinessSummary[]>([])
  const [selectedBusiness, setSelectedBusiness] = useState<AdminBusinessSummary | null>(null)
  const [formState, setFormState] = useState<EditFormState | null>(null)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const [reminderPreview, setReminderPreview] = useState<AdminReminderResponse | null>(null)

  const filteredBusinesses = useMemo(() => {
    if (statusFilter === 'all') {
      return businesses
    }

    return businesses.filter((business) => business.subscription_status === statusFilter)
  }, [businesses, statusFilter])

  const loadBusinesses = async () => {
    try {
      setIsLoading(true)
      setError('')

      const response = await adminAPI.getBusinesses()
      setBusinesses(response.data.businesses)

      if (selectedBusiness) {
        const nextSelectedBusiness = response.data.businesses.find((business) => business.id === selectedBusiness.id) ?? null
        setSelectedBusiness(nextSelectedBusiness)
        setFormState(nextSelectedBusiness ? toEditFormState(nextSelectedBusiness) : null)
      }
    } catch (loadError) {
      setError(extractApiDetail(loadError, 'Failed to load businesses.'))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadBusinesses()
  }, [])

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

  const openEditor = (business: AdminBusinessSummary) => {
    setSelectedBusiness(business)
    setFormState(toEditFormState(business))
    setReminderPreview(null)
  }

  const handleFieldChange = (field: keyof EditFormState, value: string | boolean) => {
    setFormState((currentState) => {
      if (!currentState) {
        return currentState
      }

      return {
        ...currentState,
        [field]: value,
      }
    })
  }

  const handleSave = async () => {
    if (!selectedBusiness || !formState) {
      return
    }

    const payload: AdminBusinessUpdatePayload = {
      name: formState.name,
      email: formState.email,
      phone: formState.phone || null,
      country: formState.country,
      subscription_status: formState.subscription_status,
      trial_started_at: formState.trial_started_at || null,
      trial_ends_at: formState.trial_ends_at || null,
      billing_due_date: formState.billing_due_date || null,
      monthly_price: formState.monthly_price ? Number(formState.monthly_price) : null,
      is_active: formState.is_active,
    }

    try {
      setIsSaving(true)
      setError('')

      await adminAPI.updateBusiness(selectedBusiness.id, payload)
      await loadBusinesses()
    } catch (saveError) {
      setError(extractApiDetail(saveError, 'Failed to save business changes.'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleQuickToggle = async (business: AdminBusinessSummary) => {
    try {
      await adminAPI.updateBusiness(business.id, { is_active: !business.is_active })
      await loadBusinesses()
    } catch (toggleError) {
      setError(extractApiDetail(toggleError, 'Failed to update business status.'))
    }
  }

  const handleSendReminder = async (business: AdminBusinessSummary) => {
    try {
      setError('')
      const response = await adminAPI.sendPaymentReminder(business.id)
      setReminderPreview(response.data)
      await loadBusinesses()
    } catch (reminderError) {
      setError(extractApiDetail(reminderError, 'Failed to generate reminder.'))
    }
  }

  const handleDelete = async (business: AdminBusinessSummary) => {
    const confirmed = window.confirm(`Delete ${business.name}? This removes the business and its users permanently.`)

    if (!confirmed) {
      return
    }

    try {
      setError('')
      await adminAPI.deleteBusiness(business.id)

      if (selectedBusiness?.id === business.id) {
        setSelectedBusiness(null)
        setFormState(null)
      }

      await loadBusinesses()
    } catch (deleteError) {
      setError(extractApiDetail(deleteError, 'Failed to delete business.'))
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(249,115,22,0.10),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(2,132,199,0.12),_transparent_24%),linear-gradient(180deg,_#f8fafc_0%,_#e2e8f0_100%)] px-4 py-6 md:px-8">
      <div className="mx-auto max-w-7xl space-y-8">
        <section className="rounded-[32px] border border-slate-200/80 bg-[linear-gradient(135deg,#111827_0%,#1f2937_52%,#7c2d12_100%)] p-6 text-white shadow-[0_30px_120px_rgba(15,23,42,0.22)] lg:p-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-orange-200">Platform Admin</p>
              <h1 className="mt-4 max-w-3xl text-4xl font-black tracking-tight">Business activation, trial timing, and payment follow-up in one place.</h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-200">
                Logged in as {user?.email}. Review trial expiry, payment due dates, reminder history, and business lifecycle controls without entering each tenant dashboard.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Link
                to="/dashboard"
                className="rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/20"
              >
                Open dashboard
              </Link>
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/20"
              >
                Logout
              </button>
            </div>
          </div>
        </section>

        {error && (
          <div className="rounded-[24px] border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700 shadow-sm">
            {error}
          </div>
        )}

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-6">
            <div className="flex flex-col gap-4 rounded-[28px] border border-white/70 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)] lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Business Portfolio</p>
                <h2 className="mt-2 text-2xl font-black text-slate-950">Operational status across all businesses</h2>
              </div>

              <div className="inline-flex flex-wrap rounded-full border border-slate-200 bg-slate-50 p-1">
                {(['all', 'trial', 'active', 'past_due', 'cancelled'] as StatusFilter[]).map((filter) => (
                  <button
                    key={filter}
                    type="button"
                    onClick={() => setStatusFilter(filter)}
                    className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                      statusFilter === filter ? 'bg-slate-950 text-white' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {filter === 'all' ? 'All' : filter.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            {isLoading ? (
              <div className="rounded-[28px] border border-white/70 bg-white/90 p-6 text-sm text-slate-600 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
                Loading businesses...
              </div>
            ) : filteredBusinesses.length === 0 ? (
              <div className="rounded-[28px] border border-dashed border-slate-300 bg-white/80 p-6 text-sm text-slate-600">
                No businesses match this filter yet.
              </div>
            ) : (
              <div className="grid gap-4">
                {filteredBusinesses.map((business) => (
                  <article
                    key={business.id}
                    className="rounded-[28px] border border-white/70 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]"
                  >
                    <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <div className="flex flex-wrap items-center gap-3">
                          <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${statusStyles[business.subscription_status] ?? 'bg-slate-100 text-slate-700'}`}>
                            {business.subscription_status.replace('_', ' ')}
                          </span>
                          <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${business.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}`}>
                            {business.is_active ? 'Active' : 'Inactive'}
                          </span>
                          {business.needs_payment_reminder && (
                            <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-orange-700">
                              Reminder due
                            </span>
                          )}
                        </div>

                        <h3 className="mt-4 text-2xl font-black text-slate-950">{business.name}</h3>
                        <p className="mt-1 text-sm text-slate-600">{business.email} • {business.country}</p>
                        <p className="mt-1 text-sm text-slate-500">Registered {formatDate(business.created_at)}</p>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-2 lg:min-w-[340px]">
                        <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Trial ends</p>
                          <p className="mt-2 text-sm font-semibold text-slate-900">{formatDate(business.trial_ends_at)}</p>
                          <p className="mt-1 text-xs text-slate-500">
                            {business.days_until_trial_end == null ? 'No trial set' : `${business.days_until_trial_end} days remaining`}
                          </p>
                        </div>
                        <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Billing due</p>
                          <p className="mt-2 text-sm font-semibold text-slate-900">{formatDate(business.billing_due_date)}</p>
                          <p className="mt-1 text-xs text-slate-500">
                            {business.days_until_billing_due == null ? 'No due date set' : `${business.days_until_billing_due} days remaining`}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="mt-5 grid gap-3 md:grid-cols-4">
                      <div className="rounded-2xl border border-slate-200 bg-white p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Locations</p>
                        <p className="mt-2 text-xl font-black text-slate-900">{business.total_locations}</p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-white p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Users</p>
                        <p className="mt-2 text-xl font-black text-slate-900">{business.total_users}</p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-white p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Monthly price</p>
                        <p className="mt-2 text-xl font-black text-slate-900">
                          {business.monthly_price == null ? 'Not set' : business.monthly_price.toLocaleString()}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-white p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Last reminder</p>
                        <p className="mt-2 text-sm font-semibold text-slate-900">{formatDateTime(business.last_payment_reminder_sent_at)}</p>
                      </div>
                    </div>

                    <div className="mt-5 flex flex-wrap gap-3">
                      <button
                        type="button"
                        onClick={() => openEditor(business)}
                        className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
                      >
                        Edit business
                      </button>
                      <button
                        type="button"
                        onClick={() => handleQuickToggle(business)}
                        className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400"
                      >
                        {business.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleSendReminder(business)}
                        className="rounded-full border border-orange-300 bg-orange-50 px-4 py-2 text-sm font-semibold text-orange-700 transition hover:border-orange-400"
                      >
                        Send reminder draft
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(business)}
                        className="rounded-full border border-rose-300 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-700 transition hover:border-rose-400"
                      >
                        Delete business
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-6">
            <section className="rounded-[28px] border border-white/70 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Business Editor</p>
              <h2 className="mt-2 text-2xl font-black text-slate-950">Adjust trial and billing details</h2>

              {selectedBusiness && formState ? (
                <div className="mt-5 space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <label className="text-sm font-medium text-slate-700">
                      Name
                      <input
                        value={formState.name}
                        onChange={(event) => handleFieldChange('name', event.target.value)}
                        className="mt-2 block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-900 outline-none focus:border-slate-400"
                      />
                    </label>
                    <label className="text-sm font-medium text-slate-700">
                      Email
                      <input
                        value={formState.email}
                        onChange={(event) => handleFieldChange('email', event.target.value)}
                        className="mt-2 block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-900 outline-none focus:border-slate-400"
                      />
                    </label>
                    <label className="text-sm font-medium text-slate-700">
                      Phone
                      <input
                        value={formState.phone}
                        onChange={(event) => handleFieldChange('phone', event.target.value)}
                        className="mt-2 block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-900 outline-none focus:border-slate-400"
                      />
                    </label>
                    <label className="text-sm font-medium text-slate-700">
                      Country
                      <input
                        value={formState.country}
                        onChange={(event) => handleFieldChange('country', event.target.value)}
                        className="mt-2 block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-900 outline-none focus:border-slate-400"
                      />
                    </label>
                    <label className="text-sm font-medium text-slate-700">
                      Subscription status
                      <select
                        value={formState.subscription_status}
                        onChange={(event) => handleFieldChange('subscription_status', event.target.value)}
                        className="mt-2 block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-900 outline-none focus:border-slate-400"
                      >
                        <option value="trial">trial</option>
                        <option value="active">active</option>
                        <option value="past_due">past_due</option>
                        <option value="cancelled">cancelled</option>
                      </select>
                    </label>
                    <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm font-medium text-slate-700">
                      <input
                        type="checkbox"
                        checked={formState.is_active}
                        onChange={(event) => handleFieldChange('is_active', event.target.checked)}
                        className="h-4 w-4 rounded border-slate-300"
                      />
                      Business active
                    </label>
                    <label className="text-sm font-medium text-slate-700">
                      Trial start
                      <input
                        type="date"
                        value={formState.trial_started_at}
                        onChange={(event) => handleFieldChange('trial_started_at', event.target.value)}
                        className="mt-2 block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-900 outline-none focus:border-slate-400"
                      />
                    </label>
                    <label className="text-sm font-medium text-slate-700">
                      Trial end
                      <input
                        type="date"
                        value={formState.trial_ends_at}
                        onChange={(event) => handleFieldChange('trial_ends_at', event.target.value)}
                        className="mt-2 block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-900 outline-none focus:border-slate-400"
                      />
                    </label>
                    <label className="text-sm font-medium text-slate-700">
                      Billing due date
                      <input
                        type="date"
                        value={formState.billing_due_date}
                        onChange={(event) => handleFieldChange('billing_due_date', event.target.value)}
                        className="mt-2 block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-900 outline-none focus:border-slate-400"
                      />
                    </label>
                    <label className="text-sm font-medium text-slate-700">
                      Monthly price
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={formState.monthly_price}
                        onChange={(event) => handleFieldChange('monthly_price', event.target.value)}
                        className="mt-2 block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-900 outline-none focus:border-slate-400"
                      />
                    </label>
                  </div>

                  <button
                    type="button"
                    onClick={handleSave}
                    disabled={isSaving}
                    className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:bg-slate-400"
                  >
                    {isSaving ? 'Saving...' : 'Save changes'}
                  </button>
                </div>
              ) : (
                <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
                  Select a business card to edit trial dates, billing due dates, and activation status.
                </div>
              )}
            </section>

            <section className="rounded-[28px] border border-white/70 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Reminder Preview</p>
              <h2 className="mt-2 text-2xl font-black text-slate-950">Communication scaffold</h2>

              {reminderPreview ? (
                <div className="mt-5 space-y-4">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Recipient</p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">{reminderPreview.recipient_email}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Subject</p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">{reminderPreview.subject}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Message</p>
                    <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-700">{reminderPreview.message}</p>
                  </div>
                  <p className="text-xs text-slate-500">Generated {formatDateTime(reminderPreview.sent_at)}</p>
                </div>
              ) : (
                <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
                  Generate a reminder from any business card to preview the payment or trial follow-up message and stamp the last reminder time.
                </div>
              )}
            </section>
          </div>
        </section>
      </div>
    </div>
  )
}