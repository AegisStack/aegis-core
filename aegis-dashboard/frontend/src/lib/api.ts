/**
 * API Client for Aegis Dashboard Backend
 */

import axios, { AxiosInstance } from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
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
  version: number
  is_active: boolean
  created_at: string
  created_by?: string
  description?: string
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
