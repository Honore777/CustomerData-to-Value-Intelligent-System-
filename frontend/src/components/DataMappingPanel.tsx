import { useEffect, useMemo, useState } from 'react'
import {
  businessAPI,
  type BusinessConfigResponse,
  type ColumnMapping,
  type IdentityStrategy,
  type MappingPreviewResponse,
} from '../services/api'

type DataMappingPanelProps = {
  businessId: number
  onMappingSaved?: () => Promise<void> | void
}

const DATE_FORMAT_OPTIONS = [
  '%Y-%m-%d',
  '%d/%m/%Y',
  '%m/%d/%Y',
  '%d-%m-%Y',
]

const OPTIONAL_SELECT_VALUE = '__none__'

function normalizeMappingForPreview(
  preview: MappingPreviewResponse,
  config: BusinessConfigResponse | null,
): ColumnMapping {
  const currentMapping = config?.column_mapping
  const chooseColumn = (value: string | null | undefined, fallback: string | null | undefined) => {
    if (value && preview.columns.includes(value)) {
      return value
    }
    return fallback ?? null
  }

  return {
    uses_locations: currentMapping?.uses_locations ?? preview.suggested_mapping.uses_locations,
    identity_strategy: currentMapping?.identity_strategy ?? preview.suggested_mapping.identity_strategy,
    agreed_identifier_label:
      currentMapping?.agreed_identifier_label ?? preview.suggested_mapping.agreed_identifier_label ?? 'Customer ID',
    customer_id_column: chooseColumn(currentMapping?.customer_id_column, preview.suggested_mapping.customer_id_column),
    customer_name_column: chooseColumn(currentMapping?.customer_name_column, preview.suggested_mapping.customer_name_column),
    phone_column: chooseColumn(currentMapping?.phone_column, preview.suggested_mapping.phone_column),
    location_code_column: chooseColumn(currentMapping?.location_code_column, preview.suggested_mapping.location_code_column),
    date_column: chooseColumn(currentMapping?.date_column, preview.suggested_mapping.date_column) ?? '',
    amount_column: chooseColumn(currentMapping?.amount_column, preview.suggested_mapping.amount_column) ?? '',
    product_column: chooseColumn(currentMapping?.product_column, preview.suggested_mapping.product_column) ?? '',
    date_format: config?.date_format ?? '%Y-%m-%d',
  }
}

function toSelectValue(value: string | null | undefined): string {
  return value ?? OPTIONAL_SELECT_VALUE
}

function fromSelectValue(value: string): string | null {
  return value === OPTIONAL_SELECT_VALUE ? null : value
}

export default function DataMappingPanel({
  businessId,
  onMappingSaved,
}: DataMappingPanelProps) {
  const [config, setConfig] = useState<BusinessConfigResponse | null>(null)
  const [preview, setPreview] = useState<MappingPreviewResponse | null>(null)
  const [mappingForm, setMappingForm] = useState<ColumnMapping | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isLoadingConfig, setIsLoadingConfig] = useState(true)
  const [isPreviewing, setIsPreviewing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  useEffect(() => {
    const loadConfig = async () => {
      try {
        setIsLoadingConfig(true)
        setError('')
        const response = await businessAPI.getBusinessConfig(businessId)
        setConfig(response.data)
      } catch (loadError) {
        console.error('Failed to load mapping config:', loadError)
        setError('Failed to load current mapping. Preview a file to continue.')
      } finally {
        setIsLoadingConfig(false)
      }
    }

    loadConfig()
  }, [businessId])

  const availableColumns = preview?.columns ?? []

  const requiredIdentityFields = useMemo(() => {
    if (!mappingForm) {
      return []
    }

    if (mappingForm.identity_strategy === 'customer_id') {
      return ['customer_id_column']
    }

    if (mappingForm.identity_strategy === 'customer_name_phone') {
      return ['customer_name_column', 'phone_column']
    }

    return ['customer_name_column']
  }, [mappingForm])

  const updateMappingField = <K extends keyof ColumnMapping>(field: K, value: ColumnMapping[K]) => {
    setMappingForm((current) => (current ? { ...current, [field]: value } : current))
  }

  const handlePreview = async () => {
    if (!selectedFile) {
      setError('Choose a file first so the system can inspect the headers.')
      return
    }

    try {
      setIsPreviewing(true)
      setError('')
      setSuccessMessage('')

      const response = await businessAPI.previewColumns(businessId, selectedFile)
      setPreview(response.data)
      setMappingForm(normalizeMappingForPreview(response.data, config))
    } catch (previewError) {
      console.error('Failed to preview columns:', previewError)
      setError('Failed to preview the file. Check the file format and try again.')
    } finally {
      setIsPreviewing(false)
    }
  }

  const handleSave = async () => {
    if (!mappingForm) {
      setError('Preview a file first so the mapping form can be built from real columns.')
      return
    }

    try {
      setIsSaving(true)
      setError('')
      setSuccessMessage('')

      const response = await businessAPI.configureColumns(businessId, mappingForm)
      setConfig(response.data)
      setSuccessMessage('Column mapping saved. Future uploads will use this vocabulary automatically.')
      await onMappingSaved?.()
    } catch (saveError: any) {
      console.error('Failed to save mapping:', saveError)
      setError(saveError.response?.data?.detail || 'Failed to save mapping.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="rounded-[28px] border border-white/60 bg-white/90 p-6 shadow-[0_24px_80px_rgba(15,23,42,0.10)] backdrop-blur">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">
            Mapping Studio
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-950">Flexible data mapping</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Preview the spreadsheet headers, choose the agreed customer identifier, and keep optional
            contact fields such as phone numbers available for real follow-up work.
          </p>
        </div>

        {config && (
          <div className="rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
            <p className="font-semibold">Current identifier strategy</p>
            <p className="mt-1 capitalize">{config.column_mapping.identity_strategy.replaceAll('_', ' ')}</p>
            <p className="mt-2 text-xs text-emerald-800">
              Label: {config.column_mapping.agreed_identifier_label ?? 'Customer ID'}
            </p>
          </div>
        )}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-5">
          <label className="mb-2 block text-sm font-medium text-slate-700">Sample file for mapping preview</label>
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            className="block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-700 shadow-inner"
          />
          <p className="mt-2 text-xs leading-5 text-slate-500">
            Use any representative export from the business. We only need the headers and a few sample rows.
          </p>

          <button
            type="button"
            onClick={handlePreview}
            disabled={isPreviewing}
            className="mt-4 inline-flex items-center rounded-full bg-emerald-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {isPreviewing ? 'Inspecting file...' : 'Preview columns'}
          </button>

          {preview && (
            <div className="mt-5 space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Detected columns</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {preview.columns.map((column) => (
                    <span
                      key={column}
                      className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700"
                    >
                      {column}
                    </span>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Sample rows</p>
                  {preview.missing_fields.length > 0 && (
                    <p className="text-xs font-medium text-amber-700">
                      Missing suggestions: {preview.missing_fields.join(', ')}
                    </p>
                  )}
                </div>

                <div className="mt-3 overflow-x-auto">
                  <table className="min-w-full text-left text-xs text-slate-600">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500">
                        {preview.columns.map((column) => (
                          <th key={column} className="px-3 py-2 font-semibold">{column}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.sample_rows.map((row, index) => (
                        <tr key={index} className="border-b border-slate-100 align-top">
                          {preview.columns.map((column) => (
                            <td key={`${index}-${column}`} className="px-3 py-2">
                              {row[column] ?? '-'}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-5">
          {!mappingForm ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white/80 p-5 text-sm leading-6 text-slate-600">
              Preview a file first. Then you can choose the customer identifier strategy, map required fields,
              and save optional contact fields such as phone number.
            </div>
          ) : (
            <div className="space-y-5">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Agreed customer identifier label</label>
                <input
                  type="text"
                  value={mappingForm.agreed_identifier_label ?? ''}
                  onChange={(event) => updateMappingField('agreed_identifier_label', event.target.value)}
                  placeholder="Membership Number, Customer Code, Phone, ..."
                  className="block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-700 shadow-inner outline-none focus:border-emerald-400"
                />
                <p className="mt-2 text-xs leading-5 text-slate-500">
                  This is the business-facing name for the identifier your team agrees to use.
                </p>
              </div>

              <div>
                <p className="mb-3 text-sm font-medium text-slate-700">Identifier strategy</p>
                <div className="grid gap-3 md:grid-cols-3">
                  {([
                    ['customer_id', 'Real customer ID'],
                    ['customer_name', 'Customer name'],
                    ['customer_name_phone', 'Name + phone'],
                  ] as Array<[IdentityStrategy, string]>).map(([value, label]) => (
                    <label
                      key={value}
                      className={`rounded-2xl border px-4 py-4 text-sm transition ${
                        mappingForm.identity_strategy === value
                          ? 'border-emerald-500 bg-emerald-50 text-emerald-950'
                          : 'border-slate-200 bg-white text-slate-700'
                      }`}
                    >
                      <input
                        type="radio"
                        name="identityStrategy"
                        value={value}
                        checked={mappingForm.identity_strategy === value}
                        onChange={() => updateMappingField('identity_strategy', value)}
                        className="sr-only"
                      />
                      <p className="font-semibold">{label}</p>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={mappingForm.uses_locations}
                    onChange={(event) => updateMappingField('uses_locations', event.target.checked)}
                  />
                  This business upload includes branch or location codes
                </label>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Date column</label>
                  <select
                    value={mappingForm.date_column}
                    onChange={(event) => updateMappingField('date_column', event.target.value)}
                    className="block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-700 shadow-inner"
                  >
                    <option value="">Choose date column</option>
                    {availableColumns.map((column) => (
                      <option key={column} value={column}>{column}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Amount column</label>
                  <select
                    value={mappingForm.amount_column}
                    onChange={(event) => updateMappingField('amount_column', event.target.value)}
                    className="block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-700 shadow-inner"
                  >
                    <option value="">Choose amount column</option>
                    {availableColumns.map((column) => (
                      <option key={column} value={column}>{column}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Product column</label>
                  <select
                    value={mappingForm.product_column}
                    onChange={(event) => updateMappingField('product_column', event.target.value)}
                    className="block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-700 shadow-inner"
                  >
                    <option value="">Choose product column</option>
                    {availableColumns.map((column) => (
                      <option key={column} value={column}>{column}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Date format</label>
                  <select
                    value={mappingForm.date_format}
                    onChange={(event) => updateMappingField('date_format', event.target.value)}
                    className="block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-700 shadow-inner"
                  >
                    {DATE_FORMAT_OPTIONS.map((format) => (
                      <option key={format} value={format}>{format}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Customer ID column</label>
                  <select
                    value={toSelectValue(mappingForm.customer_id_column)}
                    onChange={(event) => updateMappingField('customer_id_column', fromSelectValue(event.target.value))}
                    className="block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-700 shadow-inner"
                  >
                    <option value={OPTIONAL_SELECT_VALUE}>Not used</option>
                    {availableColumns.map((column) => (
                      <option key={column} value={column}>{column}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Customer name column</label>
                  <select
                    value={toSelectValue(mappingForm.customer_name_column)}
                    onChange={(event) => updateMappingField('customer_name_column', fromSelectValue(event.target.value))}
                    className="block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-700 shadow-inner"
                  >
                    <option value={OPTIONAL_SELECT_VALUE}>Not used</option>
                    {availableColumns.map((column) => (
                      <option key={column} value={column}>{column}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Phone column</label>
                  <select
                    value={toSelectValue(mappingForm.phone_column)}
                    onChange={(event) => updateMappingField('phone_column', fromSelectValue(event.target.value))}
                    className="block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-700 shadow-inner"
                  >
                    <option value={OPTIONAL_SELECT_VALUE}>Not used</option>
                    {availableColumns.map((column) => (
                      <option key={column} value={column}>{column}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Location code column</label>
                  <select
                    value={toSelectValue(mappingForm.location_code_column)}
                    onChange={(event) => updateMappingField('location_code_column', fromSelectValue(event.target.value))}
                    className="block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-700 shadow-inner"
                    disabled={!mappingForm.uses_locations}
                  >
                    <option value={OPTIONAL_SELECT_VALUE}>Not used</option>
                    {availableColumns.map((column) => (
                      <option key={column} value={column}>{column}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="rounded-2xl border border-emerald-100 bg-emerald-50/80 p-4 text-sm leading-6 text-emerald-950">
                Required for the chosen strategy: {requiredIdentityFields.join(', ') || 'standard transaction fields only'}.
                Optional phone data is still valuable even when customer ID is the main identifier because it supports real outreach.
              </div>

              <button
                type="button"
                onClick={handleSave}
                disabled={isSaving}
                className="inline-flex items-center rounded-full bg-slate-950 px-6 py-3 font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                {isSaving ? 'Saving mapping...' : 'Save mapping'}
              </button>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {successMessage && (
        <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
          {successMessage}
        </div>
      )}

      {isLoadingConfig && (
        <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Loading current mapping configuration...
        </div>
      )}
    </div>
  )
}