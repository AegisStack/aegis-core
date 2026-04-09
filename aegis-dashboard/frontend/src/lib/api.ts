/**
 * API Client for Aegis Dashboard Backend
 */

import axios, { AxiosInstance } from 'axios'
import { getAccessToken } from './auth'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth interceptor
apiClient.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Types
export interface AuditRecord {
  record_id: string
  timestamp: string
  customer_id?: string
  agent_id: string
  session_id?: string
  policy_version: string
  tool_name: string
  params: Record<string, any>
  outcome: 'allow' | 'deny' | 'escalate'
  matched_rule: string
  reason: string
  escalation_id?: string
  resolved_by?: string
  resolution?: string
  resolution_timestamp?: string
  execution_result?: any
  execution_error?: string
  latency_ms?: number
}

export interface MetricsSummary {
  total_calls: number
  allows: number
  denies: number
  escalations: number
  top_tools: Array<{
    tool: string
    count: number
    deny_rate: number
  }>
  top_denied_rules: Array<{
    rule: string
    count: number
  }>
  latency: {
    avg: number
    max: number
  }
}

export interface Policy {
  policy_id: string
  customer_id: string
  agent_id: string
  policy_yaml: string
  policy_hash: string
  version: number
  is_active: boolean
  created_at: string
  created_by?: string
  description?: string
}

export interface TimeseriesBucket {
  time: string
  total: number
  allows: number
  denies: number
  escalations: number
  avg_latency: number
  p95_latency: number
  p99_latency: number
}

export interface TimeseriesResponse {
  interval: string
  buckets: TimeseriesBucket[]
}

export interface Escalation {
  escalation_id: string
  record_id: string
  customer_id?: string
  agent_id: string
  tool_name: string
  params: Record<string, any>
  reason: string
  status: 'pending' | 'approved' | 'denied' | 'expired'
  resolved_by?: string
  resolution_timestamp?: string
  created_at: string
  expires_at: string
}

// API functions
export const api = {
  // Authentication
  async register(data: {
    email: string
    password: string
    full_name: string
    customer_id: string
  }): Promise<{ access_token: string; token_type: string; user: any }> {
    const response = await apiClient.post('/api/v1/auth/register', data)
    return response.data
  },

  async login(data: {
    email: string
    password: string
  }): Promise<{ access_token: string; token_type: string; user: any }> {
    const response = await apiClient.post('/api/v1/auth/login', data)
    return response.data
  },

  async logout(): Promise<void> {
    await apiClient.post('/api/v1/auth/logout')
  },

  async getCurrentUser(): Promise<any> {
    const response = await apiClient.get('/api/v1/auth/me')
    return response.data
  },

  // Audit records
  async getAuditRecords(params: {
    customer_id?: string
    agent_id?: string
    tool_name?: string
    outcome?: string
    start_time?: string
    end_time?: string
    limit?: number
    offset?: number
  }): Promise<AuditRecord[]> {
    const response = await apiClient.get('/api/v1/audit', { params })
    return response.data
  },

  async getAuditRecord(recordId: string): Promise<AuditRecord> {
    const response = await apiClient.get(`/api/v1/audit/${recordId}`)
    return response.data
  },

  // Metrics
  async getMetricsSummary(params: {
    customer_id: string
    period?: '1d' | '7d' | '30d'
  }): Promise<MetricsSummary> {
    const response = await apiClient.get('/api/v1/metrics/summary', { params })
    return response.data
  },

  // Explore (drill-down detail)
  async getExplore(params: {
    customer_id: string
    start: string
    end: string
    outcome?: string
    agent_id?: string
  }): Promise<{
    window: { start: string; end: string; outcome_filter: string | null }
    summary: {
      total: number
      allows: number
      denies: number
      escalations: number
      avg_latency: number
      p95_latency: number
      p99_latency: number
    }
    agents: Array<{
      agent_id: string
      total: number
      allows: number
      denies: number
      escalations: number
      deny_rate: number
      avg_latency: number
    }>
    tools: Array<{
      tool_name: string
      total: number
      allows: number
      denies: number
      escalations: number
      deny_rate: number
      avg_latency: number
    }>
  }> {
    const response = await apiClient.get('/api/v1/metrics/explore', { params })
    return response.data
  },

  // Timeseries
  async getTimeseries(params: {
    customer_id: string
    start: string
    end: string
    interval?: string
    agent_id?: string
    tool_name?: string
  }): Promise<TimeseriesResponse> {
    const response = await apiClient.get('/api/v1/metrics/timeseries', { params })
    return response.data
  },

  // Policies
  async getPolicies(params: {
    customer_id: string
    agent_id?: string
    include_inactive?: boolean
  }): Promise<Policy[]> {
    const response = await apiClient.get('/api/v1/policies', { params })
    return response.data
  },

  async getPolicy(policyId: string): Promise<Policy> {
    const response = await apiClient.get(`/api/v1/policies/${policyId}`)
    return response.data
  },

  async createPolicy(data: {
    customer_id: string
    agent_id: string
    policy_yaml: string
    description?: string
    created_by?: string
  }): Promise<Policy> {
    const response = await apiClient.post('/api/v1/policies', data)
    return response.data
  },

  async activatePolicy(policyId: string): Promise<Policy> {
    const response = await apiClient.post(`/api/v1/policies/${policyId}/activate`)
    return response.data
  },

  async assignPolicy(
    policyId: string,
    data: { target_agent_id: string; description?: string; created_by?: string }
  ): Promise<Policy> {
    const response = await apiClient.post(`/api/v1/policies/${policyId}/assign`, data)
    return response.data
  },

  async getAgents(customerId: string): Promise<string[]> {
    const response = await apiClient.get('/api/v1/agents', {
      params: { customer_id: customerId },
    })
    return response.data
  },

  // Escalations
  async getEscalations(params: {
    customer_id?: string
    agent_id?: string
    status?: string
  }): Promise<Escalation[]> {
    const response = await apiClient.get('/api/v1/escalations', { params })
    return response.data
  },

  async getEscalation(escalationId: string): Promise<Escalation> {
    const response = await apiClient.get(`/api/v1/escalations/${escalationId}`)
    return response.data
  },

  async resolveEscalation(
    escalationId: string,
    data: {
      resolution: 'approved' | 'denied'
      resolved_by: string
    }
  ): Promise<Escalation> {
    const response = await apiClient.post(
      `/api/v1/escalations/${escalationId}/resolve`,
      data
    )
    return response.data
  },
}

export default api
