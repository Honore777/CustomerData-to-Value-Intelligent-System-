import { useEffect, useState, type FormEvent } from 'react'
import { businessAPI, type BusinessConfigResponse } from '../services/api'

type BusinessConfigPanelProps = {
  businessId: number
  onConfigSaved?: () => Promise<void> | void
}

type ConfigFormState = {
  referencePeriodDays: string
  recencyThresholdDays: string
  frequencyThreshold: string
  monetaryThreshold: string
}

const formatDate = (value: string | null) => {
  if (!value) {
    return 'Not available yet'
  }

  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export default function BusinessConfigPanel({
  businessId,
  onConfigSaved,
}: BusinessConfigPanelProps) {
  const [form, setForm] = useState<ConfigFormState>({
    referencePeriodDays: '',
    recencyThresholdDays: '',
    frequencyThreshold: '',
    monetaryThreshold: '',
  })
  const [businessConfig, setBusinessConfig] = useState<BusinessConfigResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const applyConfigToForm = (config: BusinessConfigResponse) => {
    setBusinessConfig(config)
    setForm({
      referencePeriodDays: String(config.reference_period_days),
      recencyThresholdDays: String(config.recency_threshold_days),
      frequencyThreshold: String(config.frequency_threshold),
      monetaryThreshold: String(config.monetary_threshold),
    })
  }

  useEffect(() => {
    const loadBusinessConfig = async () => {
      try {
        setIsLoading(true)
        setError('')
        setSuccessMessage('')

        const response = await businessAPI.getBusinessConfig(businessId)
        applyConfigToForm(response.data)
      } catch (loadError) {
        console.error('Failed to load business config:', loadError)
        setError('Failed to load business retention settings.')
      } finally {
        setIsLoading(false)
      }
    }

    loadBusinessConfig()
  }, [businessId])

  const handleChange = (field: keyof ConfigFormState, value: string) => {
    setForm((current) => ({
      ...current,
      [field]: value,
    }))
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const referencePeriodDays = Number(form.referencePeriodDays)
    const recencyThresholdDays = Number(form.recencyThresholdDays)
    const frequencyThreshold = Number(form.frequencyThreshold)
    const monetaryThreshold = Number(form.monetaryThreshold)

    if (
      !Number.isFinite(referencePeriodDays) ||
      !Number.isFinite(recencyThresholdDays) ||
      !Number.isFinite(frequencyThreshold) ||
      !Number.isFinite(monetaryThreshold)
    ) {
      setError('All retention settings must be valid numbers.')
      return
    }

    if (
      referencePeriodDays <= 0 ||
      recencyThresholdDays <= 0 ||
      frequencyThreshold <= 0 ||
      monetaryThreshold < 0
    ) {
      setError('Use positive values. Monetary threshold may be zero, but not negative.')
      return
    }

    try {
      setIsSaving(true)
      setError('')
      setSuccessMessage('')

      const response = await businessAPI.updateBusinessConfig(businessId, {
        reference_period_days: referencePeriodDays,
        recency_threshold_days: recencyThresholdDays,
        frequency_threshold: frequencyThreshold,
        monetary_threshold: monetaryThreshold,
      })

      applyConfigToForm(response.data)
      setSuccessMessage(
        'Retention rules saved. Stored snapshots were refreshed from existing transaction history.'
      )

      await onConfigSaved?.()
    } catch (saveError) {
      console.error('Failed to save business config:', saveError)
      setError('Failed to save retention rules. Try again after confirming the backend is running.')
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return (
      <section className="rounded-[28px] border border-slate-200/80 bg-white p-6 shadow-[0_18px_45px_rgba(15,23,42,0.08)]">
        <p className="text-sm font-medium text-slate-600">Loading business retention settings...</p>
      </section>
    )
  }

  return (
    <section className="overflow-hidden rounded-[28px] border border-slate-200/80 bg-white shadow-[0_24px_60px_rgba(15,23,42,0.12)]">
      <div className="border-b border-slate-200 bg-[linear-gradient(135deg,#fffaf0_0%,#eef6ff_52%,#e0f2fe_100%)] px-6 py-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-700">
              Retention Rules
            </p>
            <h2 className="mt-2 text-2xl font-black text-slate-900">Scoring window and thresholds</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              These settings define the active scoring window and what this business considers risky behavior.
              Saving them re-scores stored snapshots from the transaction history already in the database.
            </p>
          </div>

          <div className="rounded-2xl border border-white/80 bg-white/80 px-4 py-3 text-sm text-slate-700 backdrop-blur">
            <p className="font-semibold text-slate-900">Latest snapshot</p>
            <p>{formatDate(businessConfig?.latest_snapshot_date ?? null)}</p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 px-6 py-6 xl:grid-cols-[1.15fr_0.85fr]">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
              <span className="block text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                Reference Period
              </span>
              <input
                type="number"
                min="1"
                value={form.referencePeriodDays}
                onChange={(event) => handleChange('referencePeriodDays', event.target.value)}
                className="mt-3 block w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-lg font-semibold text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
              />
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Number of days included in the lookback window before each snapshot date.
              </p>
            </label>

            <label className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
              <span className="block text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                Recency Threshold
              </span>
              <input
                type="number"
                min="1"
                value={form.recencyThresholdDays}
                onChange={(event) => handleChange('recencyThresholdDays', event.target.value)}
                className="mt-3 block w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-lg font-semibold text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
              />
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Days without a purchase before the customer starts to look inactive.
              </p>
            </label>

            <label className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
              <span className="block text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                Frequency Threshold
              </span>
              <input
                type="number"
                min="1"
                value={form.frequencyThreshold}
                onChange={(event) => handleChange('frequencyThreshold', event.target.value)}
                className="mt-3 block w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-lg font-semibold text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
              />
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Minimum purchases within the window before a customer looks engaged.
              </p>
            </label>

            <label className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
              <span className="block text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                Monetary Threshold
              </span>
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.monetaryThreshold}
                onChange={(event) => handleChange('monetaryThreshold', event.target.value)}
                className="mt-3 block w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-lg font-semibold text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
              />
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Minimum recent spend before the customer looks financially healthy.
              </p>
            </label>
          </div>

          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm leading-6 text-amber-900">
            The scoring window always runs from
            <span className="mx-1 font-semibold">reference date minus reference period</span>
            to the reference date itself. This is the window the current churn score uses.
          </div>

          <button
            type="submit"
            disabled={isSaving}
            className="inline-flex items-center justify-center rounded-full bg-slate-950 px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {isSaving ? 'Saving and rescoring...' : 'Save rules and refresh snapshots'}
          </button>

          {error && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700">
              {error}
            </div>
          )}

          {successMessage && (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-700">
              {successMessage}
            </div>
          )}
        </form>

        <aside className="space-y-4 rounded-[24px] border border-slate-200 bg-slate-950 p-5 text-white shadow-[0_20px_45px_rgba(15,23,42,0.22)]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300">
              Data Coverage
            </p>
            <h3 className="mt-2 text-xl font-black">What the system already knows</h3>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Available data range</p>
              <p className="mt-2 text-sm font-semibold text-white">{formatDate(businessConfig?.first_transaction_date ?? null)}</p>
              <p className="text-sm text-slate-300">to {formatDate(businessConfig?.last_transaction_date ?? null)}</p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Latest snapshot</p>
              <p className="mt-2 text-sm font-semibold text-white">{formatDate(businessConfig?.latest_snapshot_date ?? null)}</p>
              <p className="text-sm text-slate-300">Current scored reference date</p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Customer records</p>
              <p className="mt-2 text-2xl font-black text-white">{(businessConfig?.total_customers ?? 0).toLocaleString()}</p>
              <p className="text-sm text-slate-300">Profiles resolved from uploads</p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Transactions stored</p>
              <p className="mt-2 text-2xl font-black text-white">{(businessConfig?.total_transactions ?? 0).toLocaleString()}</p>
              <p className="text-sm text-slate-300">
                Across {(businessConfig?.active_locations_count ?? 0).toLocaleString()} active locations
              </p>
            </div>
          </div>
        </aside>
      </div>
    </section>
  )
}