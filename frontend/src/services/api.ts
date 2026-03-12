import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

const currentHostname =
  typeof window !== 'undefined' ? window.location.hostname : 'localhost'

const apiBaseUrl =
  import.meta.env.VITE_API_URL || `http://${currentHostname}:8000/api`

const API = axios.create({
  baseURL: apiBaseUrl,
  withCredentials: true,
})

API.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const requestUrl = error.config?.url as string | undefined
    const isAuthRoute = typeof requestUrl === 'string' && requestUrl.startsWith('/auth/')

    if (status === 401 && !isAuthRoute) {
      // When the backend rejects the cookie, the frontend should stop pretending
      // the user is still logged in. Clearing the auth store and redirecting to
      // login avoids a blank or confusing dashboard state.
      useAuthStore.getState().clearAuth()

      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    }

    return Promise.reject(error)
  }
)

export const authAPI = {
  signup: (
    email: string,
    password: string,
    businessName: string,
    country: string,
    phone?: string,
    locations?: any
  ) =>
    API.post<AuthResponse>('/auth/signup', {
      email,
      password,
      business_name: businessName,
      country,
      phone,
      locations,
    }),

  login: (email: string, password: string) =>
    API.post<AuthResponse>('/auth/login', { email, password }),

  getMe: () =>
    API.get<AuthUser>('/auth/me'),

  logout: () => API.post('/auth/logout'),
}

export const dashboardAPI = {
  getMetrics: (locationId?: number) =>
    API.get<DashboardMetricsResponse>('/dashboard/metrics', {
      params: locationId ? { location_id: locationId } : {},
    }),

  getRecommendations: (locationId?: number, limit: number = 20) =>
    API.get<DashboardRecommendationsResponse>('/dashboard/recommendations', {
      params: {
        ...(locationId ? { location_id: locationId } : {}),
        limit,
      },
    }),
  
    getLocations:()=>
      API.get<{ locations: DashboardLocationOption[] }>('/dashboard/locations'),

  getSegmentCustomers: (segment: CustomerSegment, locationId?: number, limit: number = 100) =>
    API.get<SegmentCustomersResponse>(`/dashboard/segments/${segment}/customers`, {
      params: {
        ...(locationId ? { location_id: locationId } : {}),
        limit,
      },
    }),

  getComparison: (
    period: 'month' | 'quarter' = 'month',
    locationId?: number,
    snapshotOffset: number = 1
  ) =>
    API.get<SnapshotComparisonResponse>('/dashboard/comparison', {
      params: {
        period,
        snapshot_offset: snapshotOffset,
        ...(locationId ? { location_id: locationId } : {}),
      },
    }),

  getVipConcentration: (
    locationId?: number,
    vipShareThreshold: number = 0.2,
    limit: number = 10
  ) =>
    API.get<VipConcentrationResponse>('/dashboard/vip-concentration', {
      params: {
        ...(locationId ? { location_id: locationId } : {}),
        vip_share_threshold: vipShareThreshold,
        limit,
      },
    }),
}

export const customerAPI={
  getDetail: (customerId:string)=>
    API.get(`/customers/${customerId}`),
}

export const adminAPI = {
  getBusinesses: () => API.get<AdminBusinessesResponse>('/admin/businesses'),

  updateBusiness: (businessId: number, payload: AdminBusinessUpdatePayload) =>
    API.patch<AdminBusinessSummary>(`/admin/businesses/${businessId}`, payload),

  sendPaymentReminder: (businessId: number) =>
    API.post<AdminReminderResponse>(`/admin/businesses/${businessId}/payment-reminder`),

  deleteBusiness: (businessId: number) =>
    API.delete<{ message: string }>(`/admin/businesses/${businessId}`),
}


export type AuthUser = {
  id: number
  email: string
  business_id: number | null
  role: string
  assigned_location_ids: number[] | null
  is_platform_admin: boolean
  is_active: boolean
  created_at: string
}

export type AuthResponse = {
  message: string
  user: AuthUser
}


export type IdentityStrategy = 'customer_id' | 'customer_name' | 'customer_name_phone'
export type CustomerSegment = 'churned' | 'at_risk' | 'active' | 'loyal'

export type ColumnMapping = {
  uses_locations: boolean
  identity_strategy: IdentityStrategy
  agreed_identifier_label: string | null
  customer_id_column: string | null
  customer_name_column: string | null
  phone_column: string | null
  email_column: string | null
  location_code_column: string | null
  date_column: string
  amount_column: string
  product_column: string
  date_format: string
}

export type DashboardMetricsResponse = {
  current_reference_date: string
  scoring_window_start: string
  scoring_window_end: string
  first_transaction_date: string | null
  last_transaction_date: string | null
  total_customers: number
  total_revenue: number
  revenue_at_risk: number
  avg_customer_value: number
  segment_summary: Array<{
    segment: CustomerSegment
    count: number
    total_at_risk_value: number
    avg_monetary: number
  }>
  top_products: Array<{
    product_name: string
    total_quantity_sold: number
    total_revenue: number
    times_purchased: number
  }>
}

export type DashboardRecommendationsResponse = {
  churned_count: number
  at_risk_count: number
  recommendations: Array<{
    customer_id: string
    segment: CustomerSegment
    churn_probability: number
    recommended_action: string
    urgency: string
    reasoning: string
  }>
}

export type SnapshotComparisonResponse = {
  period: 'month' | 'quarter'
  snapshot_offset: number
  current_reference_date: string
  previous_reference_date: string
  current_total_customers: number
  previous_total_customers: number
  total_customers_delta: number
  current_window_revenue: number
  previous_window_revenue: number
  window_revenue_delta: number
  current_revenue_at_risk: number
  previous_revenue_at_risk: number
  revenue_at_risk_delta: number
  improved_customers: number
  worsened_customers: number
  unchanged_customers: number
  recovered_customers: number
  slipped_customers: number
  segment_changes: Array<{
    segment: CustomerSegment
    current_count: number
    previous_count: number
    delta: number
  }>
}

export type VipConcentrationResponse = {
  current_reference_date: string
  total_customers: number
  vip_customer_count: number
  vip_share_threshold: number
  vip_revenue: number
  total_revenue: number
  vip_revenue_share: number
  non_vip_revenue: number
  top_customers: Array<{
    customer_id: string
    customer_name: string | null
    phone: string | null
    email: string | null
    segment: CustomerSegment
    location_name: string
    location_code: string
    churn_probability: number
    monetary: number
    total_spent: number
    total_purchases: number
  }>
}

export type AdminBusinessSummary = {
  id: number
  name: string
  email: string
  phone: string | null
  country: string
  currency: string
  is_active: boolean
  subscription_status: string
  trial_started_at: string | null
  trial_ends_at: string | null
  billing_due_date: string | null
  last_payment_reminder_sent_at: string | null
  monthly_price: number | null
  created_at: string
  updated_at: string
  total_locations: number
  total_users: number
  days_until_trial_end: number | null
  days_until_billing_due: number | null
  needs_payment_reminder: boolean
}

export type AdminBusinessesResponse = {
  businesses: AdminBusinessSummary[]
}

export type AdminBusinessUpdatePayload = {
  name?: string
  email?: string
  phone?: string | null
  country?: string
  is_active?: boolean
  subscription_status?: string
  trial_started_at?: string | null
  trial_ends_at?: string | null
  billing_due_date?: string | null
  monthly_price?: number | null
}

export type AdminReminderResponse = {
  business_id: number
  recipient_email: string
  subject: string
  message: string
  sent_at: string
}

export type SegmentCustomersResponse = {
  segment: CustomerSegment
  current_reference_date: string
  total_customers: number
  customers: Array<{
    customer_id: string
    customer_name: string | null
    phone: string | null
    email: string | null
    location_id: number
    location_name: string
    location_code: string
    reference_date: string
    segment: CustomerSegment
    churn_probability: number
    recency: number
    frequency: number
    monetary: number
    total_spent: number
    total_purchases: number
    last_purchase_date: string | null
    recommended_action: string
    urgency: string
    reasoning: string
  }>
}

export type DashboardLocationOption = {
  id: number
  location_code: string
  name: string
}

export type MappingPreviewResponse = {
  file_name: string
  columns: string[]
  sample_rows: Record<string, string | number | null>[]
  suggested_mapping: Omit<ColumnMapping, 'date_format'>
  missing_fields: string[]
}

export type BusinessDataSummary = {
  first_transaction_date: string | null
  last_transaction_date: string | null
  latest_snapshot_date: string | null
  active_locations_count: number
  total_customers: number
  total_transactions: number
}

export type BusinessConfigResponse = BusinessDataSummary & {
  id: number
  name: string
  email: string
  country: string
  reference_period_days: number
  recency_threshold_days: number
  frequency_threshold: number
  monetary_threshold: number
  date_format: string
  column_mapping: Omit<ColumnMapping, 'date_format'>
}

type UpdateBusinessConfigPayload = {
  reference_period_days?: number
  recency_threshold_days?: number
  frequency_threshold?: number
  monetary_threshold?: number
}

export type UploadResponse = BusinessDataSummary & {
  message: string
  status: string
  reference_date: string
  upload_start_date: string
  upload_end_date: string
  scoring_window_start: string
  scoring_window_end: string
  total_transactions_uploaded: number
  total_customers: number
  recommendations_count: number
  scoring_engine: string
  scoring_version: string | null
}

export const businessAPI = {
  getBusinessConfig: (businessId: number) =>
    API.get<BusinessConfigResponse>(`/businesses/${businessId}`),

  previewColumns: (businessId: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    return API.post<MappingPreviewResponse>(`/businesses/${businessId}/preview-columns`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  configureColumns: (businessId: number, mapping: ColumnMapping) =>
    API.post<BusinessConfigResponse>(`/businesses/${businessId}/configure-columns`, {
      mapping,
    }),

  updateBusinessConfig: (
    businessId: number,
    config: UpdateBusinessConfigPayload
  ) =>
    API.put<BusinessConfigResponse>(`/businesses/${businessId}/update-config`, null, {
      params: config,
    }),

  uploadCSV: (businessId: number, file: File, referenceDate?: string) => {
    const formData = new FormData()
    formData.append('file', file)

    return API.post<UploadResponse>(`/businesses/${businessId}/upload-csv`, formData, {
      params: referenceDate ? { reference_date: referenceDate } : {},
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
}


export default API