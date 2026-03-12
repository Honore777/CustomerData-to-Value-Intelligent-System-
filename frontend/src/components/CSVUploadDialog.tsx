import axios from 'axios'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  businessAPI,
  type BusinessConfigResponse,
  type ColumnMapping,
  type MappingPreviewResponse,
  type UploadResponse,
} from '../services/api'

type CSVUploadDialogProps = {
  businessId: number
  onUploadSuccess: () => Promise<void> | void
}

type ReferenceDateMode = 'latest' | 'custom'

const formatDate = (value: string) =>
  new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })

const optionalMappingFields = new Set(['phone_column', 'email_column', 'location_code_column'])

const mappingFieldLabels: Partial<Record<keyof ColumnMapping, string>> = {
  customer_id_column: 'customer ID column',
  customer_name_column: 'customer name column',
  phone_column: 'phone column',
  email_column: 'email column',
  location_code_column: 'location or branch column',
  date_column: 'purchase date column',
  amount_column: 'amount column',
  product_column: 'product column',
}

const identityStrategyDescriptions: Record<ColumnMapping['identity_strategy'], string> = {
  customer_id:
    'Best when the business has a stable identifier such as a loyalty number, member ID, or recorded phone-based ID.',
  customer_name:
    'Useful when the owner tracks customers by name but does not maintain a formal customer code.',
  customer_name_phone:
    'Strong fallback for businesses that know customers by name and usually record a phone number during sales.',
}

const formatFieldList = (fields: string[]) => {
  if (fields.length <= 1) {
    return fields.join('')
  }

  if (fields.length === 2) {
    return `${fields[0]} and ${fields[1]}`
  }

  return `${fields.slice(0, -1).join(', ')}, and ${fields.at(-1)}`
}

const getMappingFieldLabel = (field: string) => mappingFieldLabels[field as keyof ColumnMapping] ?? field

const getRequiredFieldsForStrategy = (
  strategy: ColumnMapping['identity_strategy'],
  usesLocations: boolean
) => {
  const required: Array<keyof ColumnMapping> = ['date_column', 'amount_column', 'product_column']

  if (strategy === 'customer_id') {
    required.push('customer_id_column')
  }

  if (strategy === 'customer_name') {
    required.push('customer_name_column')
  }

  if (strategy === 'customer_name_phone') {
    required.push('customer_name_column', 'phone_column')
  }

  if (usesLocations) {
    required.push('location_code_column')
  }

  return required
}

const extractApiErrorMessage = (error: unknown, fallback: string) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail

    if (typeof detail === 'string') {
      return detail
    }
  }

  return fallback
}

const resolveIdentityStrategy = (
  previewResponse: MappingPreviewResponse,
  currentConfig: BusinessConfigResponse | null
): ColumnMapping['identity_strategy'] => {
  const savedMapping = currentConfig?.column_mapping

  if (!savedMapping) {
    return previewResponse.suggested_mapping.identity_strategy
  }

  const availableColumns = new Set(previewResponse.columns)
  const savedRequiredFields = getRequiredFieldsForStrategy(
    savedMapping.identity_strategy,
    savedMapping.uses_locations
  )

  const savedStrategyIsStillAvailable = savedRequiredFields.every((field) => {
    const value = savedMapping[field]
    return typeof value === 'string' && availableColumns.has(value)
  })

  return savedStrategyIsStillAvailable
    ? savedMapping.identity_strategy
    : previewResponse.suggested_mapping.identity_strategy
}

const resolveMappedColumn = (
  field: keyof ColumnMapping,
  previewResponse: MappingPreviewResponse,
  currentConfig: BusinessConfigResponse | null
) => {
  const availableColumns = new Set(previewResponse.columns)
  const savedValue = currentConfig?.column_mapping[field]
  const suggestedValue = previewResponse.suggested_mapping[field]

  if (typeof savedValue === 'string' && availableColumns.has(savedValue)) {
    return savedValue
  }

  if (typeof suggestedValue === 'string' && availableColumns.has(suggestedValue)) {
    return suggestedValue
  }

  return null
}

const requiredFieldsByIdentity = (mapping: ColumnMapping) => {
  const required = ['date_column', 'amount_column', 'product_column']

  if (mapping.identity_strategy === 'customer_id') {
    required.push('customer_id_column')
  }

  if (mapping.identity_strategy === 'customer_name') {
    required.push('customer_name_column')
  }

  if (mapping.identity_strategy === 'customer_name_phone') {
    required.push('customer_name_column', 'phone_column')
  }

  if (mapping.uses_locations) {
    required.push('location_code_column')
  }

  return required
}

export default function CSVUploadDialog({
  businessId,
  onUploadSuccess,
}: CSVUploadDialogProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [referenceDateMode, setReferenceDateMode] = useState<ReferenceDateMode>('latest')
  const [referenceDate, setReferenceDate] = useState('')
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null)
  const [preview, setPreview] = useState<MappingPreviewResponse | null>(null)
  const [mappingDraft, setMappingDraft] = useState<ColumnMapping | null>(null)
  const [businessConfig, setBusinessConfig] = useState<BusinessConfigResponse | null>(null)
  const [error, setError] = useState('')
  const [mappingMessage, setMappingMessage] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [isPreviewing, setIsPreviewing] = useState(false)
  const [isSavingMapping, setIsSavingMapping] = useState(false)
  const [fileInputKey, setFileInputKey] = useState(0)

  useEffect(() => {
    const loadBusinessConfig = async () => {
      try {
        const response = await businessAPI.getBusinessConfig(businessId)
        setBusinessConfig(response.data)
      } catch (loadError) {
        console.error('Failed to load business config for upload flow:', loadError)
      }
    }

    loadBusinessConfig()
  }, [businessId])

  const availableColumns = preview?.columns ?? []

  const mappingMissingFields = useMemo(() => {
    if (!mappingDraft) {
      return []
    }

    return requiredFieldsByIdentity(mappingDraft).filter(
      (field) => !mappingDraft[field as keyof ColumnMapping]
    )
  }, [mappingDraft])

  const buildMappingDraft = (
    previewResponse: MappingPreviewResponse,
    currentConfig: BusinessConfigResponse | null
  ): ColumnMapping => {
    const identityStrategy = resolveIdentityStrategy(previewResponse, currentConfig)
    const savedMapping = currentConfig?.column_mapping
    const usesLocations =
      savedMapping?.uses_locations &&
      typeof savedMapping.location_code_column === 'string' &&
      previewResponse.columns.includes(savedMapping.location_code_column)
        ? true
        : Boolean(previewResponse.suggested_mapping.uses_locations)

    return {
      uses_locations: usesLocations,
      identity_strategy: identityStrategy,
      agreed_identifier_label:
        savedMapping?.agreed_identifier_label ||
        previewResponse.suggested_mapping.agreed_identifier_label ||
        (identityStrategy === 'customer_id' ? 'Customer ID' : 'Customer Identity'),
      customer_id_column: resolveMappedColumn('customer_id_column', previewResponse, currentConfig),
      customer_name_column: resolveMappedColumn('customer_name_column', previewResponse, currentConfig),
      phone_column: resolveMappedColumn('phone_column', previewResponse, currentConfig),
      email_column: resolveMappedColumn('email_column', previewResponse, currentConfig),
      location_code_column: usesLocations
        ? resolveMappedColumn('location_code_column', previewResponse, currentConfig)
        : null,
      date_column:
        resolveMappedColumn('date_column', previewResponse, currentConfig) ||
        previewResponse.suggested_mapping.date_column ||
        '',
      amount_column:
        resolveMappedColumn('amount_column', previewResponse, currentConfig) ||
        previewResponse.suggested_mapping.amount_column ||
        '',
      product_column:
        resolveMappedColumn('product_column', previewResponse, currentConfig) ||
        previewResponse.suggested_mapping.product_column ||
        '',
      date_format: currentConfig?.date_format || '%Y-%m-%d',
    }
  }

  const mappingMissingFieldLabels = useMemo(
    () => mappingMissingFields.map((field) => getMappingFieldLabel(field)),
    [mappingMissingFields]
  )

  const mappingReadinessMessage = useMemo(() => {
    if (!mappingDraft) {
      return 'Preview a file to inspect columns and confirm the business vocabulary before upload.'
    }

    if (mappingMissingFieldLabels.length === 0) {
      return 'This mapping is complete for the chosen identity strategy and can be saved or uploaded.'
    }

    return `Complete ${formatFieldList(mappingMissingFieldLabels)} before this file can be scored.`
  }, [mappingDraft, mappingMissingFieldLabels])

  const handleFileSelection = (file: File | null) => {
    setSelectedFile(file)
    setPreview(null)
    setMappingDraft(null)
    setUploadResult(null)
    setError('')
    setMappingMessage('')
  }

  const handlePreview = async () => {
    if (!selectedFile) {
      setError('Choose a file first so the system can inspect its columns.')
      return
    }

    try {
      setIsPreviewing(true)
      setError('')
      setMappingMessage('Inspecting the file structure and proposing a mapping...')

      const response = await businessAPI.previewColumns(businessId, selectedFile)
      setPreview(response.data)
      setMappingDraft(buildMappingDraft(response.data, businessConfig))
      setMappingMessage('Column preview loaded. Review the mapping before upload.')
    } catch (previewError) {
      console.error('Failed to preview uploaded file:', previewError)
      setError(
        extractApiErrorMessage(
          previewError,
          'Could not preview columns. Check the file format and try again.'
        )
      )
    } finally {
      setIsPreviewing(false)
    }
  }

  const handleMappingChange = <K extends keyof ColumnMapping>(field: K, value: ColumnMapping[K]) => {
    setMappingDraft((current) => {
      if (!current) {
        return current
      }

      return {
        ...current,
        ...(field === 'uses_locations' && !value
          ? { location_code_column: null }
          : {}),
        ...(field === 'identity_strategy' && !current.agreed_identifier_label
          ? {
              agreed_identifier_label:
                value === 'customer_id' ? 'Customer ID' : 'Customer Identity',
            }
          : {}),
        [field]: value,
      }
    })

    setError('')
  }

  const saveMapping = async () => {
    if (!mappingDraft) {
      return true
    }

    if (mappingMissingFields.length > 0) {
      setError(`Complete the required mapping fields first: ${formatFieldList(mappingMissingFieldLabels)}`)
      return false
    }

    try {
      setIsSavingMapping(true)
      setError('')

      const response = await businessAPI.configureColumns(businessId, mappingDraft)
      setBusinessConfig(response.data)
      setMappingMessage(
        'Mapping saved. Future uploads will use this vocabulary unless you change it again.'
      )
      return true
    } catch (saveError) {
      console.error('Failed to save mapping:', saveError)
      setError(
        extractApiErrorMessage(
          saveError,
          'Failed to save the mapping. Check the required fields and try again.'
        )
      )
      return false
    } finally {
      setIsSavingMapping(false)
    }
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!selectedFile) {
      setError('Please choose a CSV or Excel file first.')
      return
    }

    if (referenceDateMode === 'custom' && !referenceDate) {
      setError('Choose the snapshot reference date before continuing.')
      return
    }

    try {
      setIsUploading(true)
      setError('')
      setUploadResult(null)
      setMappingMessage('Saving the mapping and uploading the file for scoring...')

      const mappingSaved = await saveMapping()
      if (!mappingSaved) {
        return
      }

      const response = await businessAPI.uploadCSV(
        businessId,
        selectedFile,
        referenceDateMode === 'custom' ? referenceDate : undefined
      )

      setUploadResult(response.data)
      setReferenceDate('')
      setReferenceDateMode('latest')
      setSelectedFile(null)
      setPreview(null)
      setMappingDraft(null)
      setFileInputKey((current) => current + 1)
      setMappingMessage('Upload completed successfully.')

      const businessResponse = await businessAPI.getBusinessConfig(businessId)
      setBusinessConfig(businessResponse.data)

      await onUploadSuccess()
    } catch (uploadError) {
      console.error('CSV upload failed:', uploadError)
      setError(
        extractApiErrorMessage(
          uploadError,
          'Upload failed. Check the file structure, mapping, and reference date.'
        )
      )
    } finally {
      setIsUploading(false)
    }
  }

  const renderColumnSelect = (
    field: keyof ColumnMapping,
    label: string,
    description: string
  ) => {
    if (!mappingDraft) {
      return null
    }

    const value = mappingDraft[field]
    const isOptional = optionalMappingFields.has(field)

    return (
      <label className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
        <span className="block text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
          {label}
        </span>
        <select
          value={typeof value === 'string' ? value : ''}
          onChange={(event) =>
            handleMappingChange(
              field,
              (event.target.value || null) as ColumnMapping[typeof field]
            )
          }
          className="mt-3 block w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
        >
          <option value="">{isOptional ? 'Optional field' : 'Choose a column'}</option>
          {availableColumns.map((column) => (
            <option key={`${field}-${column}`} value={column}>
              {column}
            </option>
          ))}
        </select>
        <p className="mt-3 text-sm leading-6 text-slate-600">{description}</p>
      </label>
    )
  }

  return (
    <section className="overflow-hidden rounded-[28px] border border-slate-200/80 bg-white shadow-[0_24px_60px_rgba(15,23,42,0.12)]">
      <div className="border-b border-slate-200 bg-[linear-gradient(140deg,#0f172a_0%,#122b39_48%,#1d4ed8_100%)] px-6 py-6 text-white">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-200">
              Upload Studio
            </p>
            <h2 className="mt-2 text-2xl font-black">Flexible mapping and snapshot upload</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-200">
              Preview the file first, confirm mandatory fields, keep optional phone and email when available,
              and then score the upload against the correct reference date.
            </p>
          </div>

          <div className="rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-sm backdrop-blur">
            <p className="font-semibold text-white">Current identifier</p>
            <p className="text-slate-200">
              {businessConfig?.column_mapping.agreed_identifier_label || 'Customer ID'}
            </p>
          </div>
        </div>
      </div>

      <div className="px-4 py-6 sm:px-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid gap-6 2xl:grid-cols-[0.95fr_1.05fr]">
            <div className="min-w-0 space-y-4 rounded-[24px] border border-slate-200 bg-slate-50/70 p-4 sm:p-5">
              <div>
                <h3 className="text-lg font-black text-slate-900">1. Choose the file</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  The preview step detects columns and helps the business confirm which identifier and contact fields it actually has.
                </p>
              </div>

              <input
                key={fileInputKey}
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={(event) => handleFileSelection(event.target.files?.[0] ?? null)}
                className="block w-full rounded-2xl border border-dashed border-slate-300 bg-white px-4 py-4 text-slate-700"
              />

              <button
                type="button"
                onClick={handlePreview}
                disabled={!selectedFile || isPreviewing}
                className="inline-flex items-center justify-center rounded-full border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-800 transition hover:border-slate-400 hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isPreviewing ? 'Inspecting columns...' : 'Preview columns and mapping'}
              </button>

              <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm leading-6 text-amber-900">
                If the file is historical, leave the reference mode on automatic and the backend will use the latest date inside the file.
                Only set a custom reference date when you intentionally want a different snapshot anchor.
              </div>

              <div className="space-y-3">
                <p className="text-sm font-semibold text-slate-900">Reference date mode</p>

                <label className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4">
                  <input
                    type="radio"
                    name="referenceDateMode"
                    value="latest"
                    checked={referenceDateMode === 'latest'}
                    onChange={() => setReferenceDateMode('latest')}
                    className="mt-1"
                  />
                  <div>
                    <p className="font-semibold text-slate-900">Use the latest date inside the file</p>
                    <p className="text-sm text-slate-600">
                      Best for normal uploads. This prevents empty windows when you upload older business history.
                    </p>
                  </div>
                </label>

                <label className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4">
                  <input
                    type="radio"
                    name="referenceDateMode"
                    value="custom"
                    checked={referenceDateMode === 'custom'}
                    onChange={() => setReferenceDateMode('custom')}
                    className="mt-1"
                  />
                  <div className="w-full">
                    <p className="font-semibold text-slate-900">Set a custom reference date</p>
                    <p className="text-sm text-slate-600">
                      Use this only when you intentionally want the snapshot anchored to a different date.
                    </p>

                    {referenceDateMode === 'custom' && (
                      <input
                        type="date"
                        value={referenceDate}
                        onChange={(event) => setReferenceDate(event.target.value)}
                        className="mt-3 block w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
                      />
                    )}
                  </div>
                </label>
              </div>
            </div>

            <div className="min-w-0 space-y-4 rounded-[24px] border border-slate-200 bg-white p-4 sm:p-5">
              <div>
                <h3 className="text-lg font-black text-slate-900">2. Confirm the mapping</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Mandatory fields drive scoring. Optional fields such as phone and email stay nullable and only support customer follow-up.
                </p>
              </div>

              <div
                className={`rounded-2xl border px-4 py-4 text-sm leading-6 ${
                  mappingDraft && mappingMissingFieldLabels.length === 0
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                    : 'border-slate-200 bg-slate-50 text-slate-700'
                }`}
              >
                <p className="font-semibold text-slate-900">
                  {mappingDraft ? 'Mapping readiness' : 'Before you upload'}
                </p>
                <p className="mt-1">{mappingReadinessMessage}</p>
              </div>

              {!mappingDraft ? (
                <div className="space-y-4 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-600">
                  <p>
                    Preview a file first to edit the mapping. The saved business vocabulary will still be used if you upload without opening the preview.
                  </p>

                  {businessConfig && (
                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="rounded-2xl border border-slate-200 bg-white p-4">
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                          Saved identity strategy
                        </p>
                        <p className="mt-2 text-sm font-semibold text-slate-900">
                          {businessConfig.column_mapping.identity_strategy.replaceAll('_', ' ')}
                        </p>
                        <p className="mt-1 text-sm text-slate-600">
                          {businessConfig.column_mapping.agreed_identifier_label || 'Customer ID'}
                        </p>
                      </div>

                      <div className="rounded-2xl border border-slate-200 bg-white p-4">
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                          Saved date format
                        </p>
                        <p className="mt-2 text-sm font-semibold text-slate-900">
                          {businessConfig.date_format}
                        </p>
                        <p className="mt-1 text-sm text-slate-600">
                          Reused for future uploads unless you change it here.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <>
                  <div className="grid gap-3 lg:grid-cols-2 2xl:grid-cols-3">
                    <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                        Previewed file
                      </p>
                      <p className="mt-2 text-sm font-semibold text-slate-900">{preview?.file_name ?? 'Current file'}</p>
                      <p className="mt-1 text-sm text-slate-600">
                        {availableColumns.length.toLocaleString()} detected columns
                      </p>
                    </div>

                    <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                        Identity logic
                      </p>
                      <p className="mt-2 text-sm font-semibold text-slate-900">
                        {mappingDraft.identity_strategy.replaceAll('_', ' ')}
                      </p>
                      <p className="mt-1 text-sm text-slate-600">
                        {identityStrategyDescriptions[mappingDraft.identity_strategy]}
                      </p>
                    </div>

                    <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                        Current status
                      </p>
                      <p className="mt-2 text-sm font-semibold text-slate-900">
                        {mappingMissingFieldLabels.length === 0 ? 'Ready to save or upload' : 'Needs attention'}
                      </p>
                      <p className="mt-1 text-sm text-slate-600">
                        {mappingMissingFieldLabels.length === 0
                          ? 'All required fields are mapped for this file.'
                          : `Missing ${formatFieldList(mappingMissingFieldLabels)}.`}
                      </p>
                    </div>
                  </div>

                  <div className="grid gap-4 xl:grid-cols-2">
                    <label className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4 md:col-span-2">
                      <span className="block text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                        Identifier label shown to the business
                      </span>
                      <input
                        type="text"
                        value={mappingDraft.agreed_identifier_label ?? ''}
                        onChange={(event) => handleMappingChange('agreed_identifier_label', event.target.value)}
                        className="mt-3 block w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
                        placeholder="Customer ID"
                      />
                      <p className="mt-3 text-sm leading-6 text-slate-600">
                        This is the label the business sees when reviewing the chosen customer identifier strategy.
                      </p>
                    </label>

                    <label className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                      <span className="block text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                        Identity strategy
                      </span>
                      <select
                        value={mappingDraft.identity_strategy}
                        onChange={(event) =>
                          handleMappingChange(
                            'identity_strategy',
                            event.target.value as ColumnMapping['identity_strategy']
                          )
                        }
                        className="mt-3 block w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
                      >
                        <option value="customer_id">Dedicated customer ID</option>
                        <option value="customer_name">Customer name only</option>
                        <option value="customer_name_phone">Customer name and phone</option>
                      </select>
                      <p className="mt-3 text-sm leading-6 text-slate-600">
                        {identityStrategyDescriptions[mappingDraft.identity_strategy]}
                      </p>
                    </label>

                    <label className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                      <span className="block text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                        Date format
                      </span>
                      <input
                        type="text"
                        value={mappingDraft.date_format}
                        onChange={(event) => handleMappingChange('date_format', event.target.value)}
                        className="mt-3 block w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
                        placeholder="%Y-%m-%d"
                      />
                    </label>
                  </div>

                  <label className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                    <input
                      type="checkbox"
                      checked={mappingDraft.uses_locations}
                      onChange={(event) => handleMappingChange('uses_locations', event.target.checked)}
                      className="mt-1"
                    />
                    <div>
                      <p className="font-semibold text-slate-900">This file contains branch or location information</p>
                      <p className="text-sm text-slate-600">
                        Leave this off for single-location businesses so the system uses one synthetic main location.
                      </p>
                    </div>
                  </label>

                  <div className="grid gap-4 lg:grid-cols-2">
                    {renderColumnSelect('customer_id_column', 'Customer ID column', 'Use this when the business has a stable customer identifier.')}
                    {renderColumnSelect('customer_name_column', 'Customer name column', 'Useful for owner-managed businesses that know customers by name.')}
                    {renderColumnSelect('phone_column', 'Phone column', 'Optional contact field. Also used when identity strategy is name plus phone.')}
                    {renderColumnSelect('email_column', 'Email column', 'Optional contact field for later outreach. It never blocks scoring when absent.')}
                    {renderColumnSelect('location_code_column', 'Location or branch column', 'Optional unless this file contains multiple branches.')}
                    {renderColumnSelect('date_column', 'Purchase date column', 'Mandatory field for the snapshot timeline.')}
                    {renderColumnSelect('amount_column', 'Amount column', 'Mandatory field for monetary value and revenue at risk.')}
                    {renderColumnSelect('product_column', 'Product column', 'Mandatory field for product-level dashboard insight.')}
                  </div>

                  {preview && preview.sample_rows.length > 0 && (
                    <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <p className="text-sm font-semibold text-slate-900">Sample rows</p>
                          <p className="text-sm text-slate-600">Use these examples to confirm the mapping visually.</p>
                        </div>

                        {mappingMissingFieldLabels.length > 0 && (
                          <p className="rounded-full bg-rose-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-rose-700">
                            Missing: {formatFieldList(mappingMissingFieldLabels)}
                          </p>
                        )}
                      </div>

                      <div className="mt-4 overflow-x-auto rounded-2xl border border-slate-200 bg-white">
                        <table className="min-w-full text-left text-sm">
                          <thead>
                            <tr className="border-b border-slate-200 text-slate-500">
                              {preview.columns.map((column) => (
                                <th key={column} className="px-3 py-2 font-semibold">
                                  {column}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {preview.sample_rows.map((row, index) => (
                              <tr key={`sample-${index}`} className="border-b border-slate-100 align-top">
                                {preview.columns.map((column) => (
                                  <td key={`${index}-${column}`} className="px-3 py-2 text-slate-700">
                                    {String(row[column] ?? '')}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={saveMapping}
                    disabled={isSavingMapping}
                    className="inline-flex items-center justify-center rounded-full border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-800 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isSavingMapping ? 'Saving mapping...' : 'Save mapping only'}
                  </button>
                </>
              )}
            </div>
          </div>

          <button
            type="submit"
            disabled={isUploading}
            className="inline-flex items-center justify-center rounded-full bg-slate-950 px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {isUploading ? 'Uploading and scoring...' : 'Upload file and run scoring'}
          </button>
        </form>

        {error && (
          <div className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700">
            {error}
          </div>
        )}

        {mappingMessage && !error && (
          <div className="mt-5 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-4 text-sm text-sky-700">
            {mappingMessage}
          </div>
        )}

        {uploadResult && (
          <div className="mt-6 rounded-[24px] border border-emerald-200 bg-[linear-gradient(140deg,#ecfdf5_0%,#f0fdf4_100%)] p-5 shadow-[0_16px_40px_rgba(16,185,129,0.12)]">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">
                  Upload complete
                </p>
                <h3 className="mt-2 text-xl font-black text-emerald-950">Snapshot stored successfully</h3>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-emerald-900">{uploadResult.message}</p>
              </div>

              <div className="rounded-2xl border border-emerald-200 bg-white/90 px-4 py-3 text-sm text-emerald-900">
                <p className="font-semibold">Scoring engine</p>
                <p>
                  {uploadResult.scoring_engine}
                  {uploadResult.scoring_version ? ` · ${uploadResult.scoring_version}` : ''}
                </p>
              </div>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Reference date</p>
                <p className="mt-2 text-lg font-black text-slate-900">{formatDate(uploadResult.reference_date)}</p>
              </div>

              <div className="rounded-2xl bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Uploaded data range</p>
                <p className="mt-2 text-sm font-semibold text-slate-900">{formatDate(uploadResult.upload_start_date)}</p>
                <p className="text-sm text-slate-600">to {formatDate(uploadResult.upload_end_date)}</p>
              </div>

              <div className="rounded-2xl bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Scoring window</p>
                <p className="mt-2 text-sm font-semibold text-slate-900">{formatDate(uploadResult.scoring_window_start)}</p>
                <p className="text-sm text-slate-600">to {formatDate(uploadResult.scoring_window_end)}</p>
              </div>

              <div className="rounded-2xl bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Transactions</p>
                <p className="mt-2 text-2xl font-black text-slate-900">
                  {uploadResult.total_transactions_uploaded.toLocaleString()}
                </p>
              </div>
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Customers scored</p>
                <p className="mt-2 text-2xl font-black text-slate-900">
                  {uploadResult.total_customers.toLocaleString()}
                </p>
              </div>

              <div className="rounded-2xl bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Recommendations created</p>
                <p className="mt-2 text-2xl font-black text-slate-900">
                  {uploadResult.recommendations_count.toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}