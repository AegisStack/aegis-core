'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Policy } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { formatDate } from '@/lib/utils'
import { useCustomer } from '@/app/providers'

const DEFAULT_POLICY = `version: 1
agent_role: your-agent
customer_id: acme-corp

rules:
  - tool: example_tool
    allow:
      - param: { lte: 100 }
    deny:
      - param: { gt: 100 }

defaults:
  unmatched_tool: deny
  unmatched_param: escalate
`

// ─── Policy Editor ────────────────────────────────────────────────────────────

function PolicyEditor({ initialPolicy, onSave, isSaving }: {
  initialPolicy?: Policy
  onSave: (yaml: string, description: string) => Promise<void>
  isSaving: boolean
}) {
  const [yaml, setYaml] = useState(initialPolicy?.policy_yaml || DEFAULT_POLICY)
  const [description, setDescription] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'edit' | 'preview'>('edit')

  const validateYaml = (yamlText: string) => {
    if (!yamlText.includes('version:')) {
      setValidationError('Missing required field: version')
      return false
    }
    if (!yamlText.includes('rules:')) {
      setValidationError('Missing required field: rules')
      return false
    }
    setValidationError(null)
    return true
  }

  const handleSave = async () => {
    if (validateYaml(yaml)) {
      await onSave(yaml, description)
    }
  }

  const parseYamlForPreview = () => {
    try {
      const lines = yaml.split('\n')
      const rules: any[] = []
      let currentRule: any = null
      for (const line of lines) {
        if (line.trim().startsWith('- tool:')) {
          if (currentRule) rules.push(currentRule)
          currentRule = { tool: line.split(':')[1].trim(), conditions: [] }
        } else if (currentRule && (line.includes('allow:') || line.includes('deny:') || line.includes('escalate:'))) {
          currentRule.conditions.push(line.trim().replace(':', ''))
        }
      }
      if (currentRule) rules.push(currentRule)
      return rules
    } catch {
      return []
    }
  }

  const previewRules = parseYamlForPreview()

  return (
    <div className="space-y-4">
      <Tabs value={activeTab} className="w-full">
        <TabsList className="w-full">
          <TabsTrigger active={activeTab === 'edit'} onClick={() => setActiveTab('edit')} className="flex-1">
            Edit YAML
          </TabsTrigger>
          <TabsTrigger active={activeTab === 'preview'} onClick={() => setActiveTab('preview')} className="flex-1">
            Preview Rules
          </TabsTrigger>
        </TabsList>

        <TabsContent value="edit">
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Policy YAML</label>
              <textarea
                className="w-full mt-2 p-3 border rounded-md font-mono text-sm min-h-[400px]"
                value={yaml}
                onChange={(e) => { setYaml(e.target.value); validateYaml(e.target.value) }}
                placeholder="Enter your policy YAML..."
              />
              {validationError && (
                <p className="text-sm text-destructive mt-2">{validationError}</p>
              )}
            </div>
            <div>
              <label className="text-sm font-medium">Version Description (optional)</label>
              <input
                type="text"
                className="w-full mt-2 p-3 border rounded-md text-sm"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g., Increased refund threshold to $500"
              />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="preview">
          <Card>
            <CardHeader>
              <CardTitle>Policy Rules Preview</CardTitle>
              <CardDescription>Parsed rules from YAML</CardDescription>
            </CardHeader>
            <CardContent>
              {previewRules.length === 0 ? (
                <p className="text-sm text-muted-foreground">No valid rules found</p>
              ) : (
                <div className="space-y-4">
                  {previewRules.map((rule, index) => (
                    <div key={index} className="p-4 border rounded-lg">
                      <h4 className="font-mono font-semibold mb-2">{rule.tool}</h4>
                      <div className="flex flex-wrap gap-2">
                        {rule.conditions.map((condition: string, idx: number) => (
                          <Badge
                            key={idx}
                            variant={
                              condition.includes('allow') ? 'success'
                              : condition.includes('deny') ? 'destructive'
                              : 'warning'
                            }
                          >
                            {condition}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <div className="flex justify-end space-x-2">
        <Button variant="outline" onClick={() => setYaml(DEFAULT_POLICY)} disabled={isSaving}>
          Reset to Template
        </Button>
        <Button onClick={handleSave} disabled={isSaving || !!validationError}>
          {isSaving ? 'Saving...' : 'Save Policy'}
        </Button>
      </div>
    </div>
  )
}

// ─── Assign to Agent inline form ──────────────────────────────────────────────

function AssignPolicyForm({
  policy,
  agents,
  onAssign,
  onCancel,
  isAssigning,
}: {
  policy: Policy
  agents: string[]
  onAssign: (targetAgentId: string) => void
  onCancel: () => void
  isAssigning: boolean
}) {
  const otherAgents = agents.filter((a) => a !== policy.agent_id)
  const [targetAgent, setTargetAgent] = useState(otherAgents[0] ?? '')
  const [customAgent, setCustomAgent] = useState('')
  const [useCustom, setUseCustom] = useState(otherAgents.length === 0)

  const finalTarget = useCustom ? customAgent.trim() : targetAgent

  return (
    <div className="mt-3 pt-3 border-t space-y-3">
      <p className="text-sm font-medium text-muted-foreground">Assign this policy to:</p>

      {!useCustom && otherAgents.length > 0 && (
        <select
          className="w-full p-2 border rounded-md text-sm"
          value={targetAgent}
          onChange={(e) => setTargetAgent(e.target.value)}
        >
          {otherAgents.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
      )}

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id={`custom-agent-${policy.policy_id}`}
          checked={useCustom}
          onChange={(e) => setUseCustom(e.target.checked)}
          className="rounded"
        />
        <label htmlFor={`custom-agent-${policy.policy_id}`} className="text-sm">
          Enter agent ID manually
        </label>
      </div>

      {useCustom && (
        <input
          type="text"
          className="w-full p-2 border rounded-md text-sm"
          value={customAgent}
          onChange={(e) => setCustomAgent(e.target.value)}
          placeholder="e.g., new-agent"
        />
      )}

      <div className="flex gap-2">
        <Button
          size="sm"
          onClick={() => onAssign(finalTarget)}
          disabled={isAssigning || !finalTarget}
        >
          {isAssigning ? 'Assigning…' : 'Confirm Assign'}
        </Button>
        <Button size="sm" variant="outline" onClick={onCancel} disabled={isAssigning}>
          Cancel
        </Button>
      </div>
    </div>
  )
}

// ─── Policy History ───────────────────────────────────────────────────────────

function PolicyHistory({
  policies,
  agents,
  onActivate,
  onAssign,
  assigningPolicyId,
}: {
  policies: Policy[]
  agents: string[]
  onActivate: (policyId: string) => void
  onAssign: (policyId: string, targetAgentId: string) => void
  assigningPolicyId: string | null
}) {
  const [expandedAssign, setExpandedAssign] = useState<string | null>(null)
  const [expandedYaml, setExpandedYaml] = useState<string | null>(null)

  const toggleYaml = (policyId: string) =>
    setExpandedYaml((prev) => (prev === policyId ? null : policyId))

  return (
    <div className="space-y-3">
      {policies.map((policy) => (
        <Card key={policy.policy_id} className={policy.is_active ? 'border-primary' : ''}>
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="font-semibold">Version {policy.version}</span>
                  {policy.is_active && <Badge variant="success">Active</Badge>}
                </div>
                {policy.description && (
                  <p className="text-sm text-muted-foreground mb-2">{policy.description}</p>
                )}
                <div className="text-xs text-muted-foreground space-y-1">
                  <p>Created: {formatDate(policy.created_at)}</p>
                  {policy.created_by && <p>By: {policy.created_by}</p>}
                  <p className="font-mono">Hash: {policy.policy_hash?.substring(0, 12) ?? 'N/A'}…</p>
                </div>
              </div>

              <div className="flex flex-col gap-2 ml-4 items-end">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => toggleYaml(policy.policy_id)}
                >
                  {expandedYaml === policy.policy_id ? 'Hide Policy' : 'View Policy'}
                </Button>
                {!policy.is_active && (
                  <Button size="sm" variant="outline" onClick={() => onActivate(policy.policy_id)}>
                    Rollback
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    setExpandedAssign(expandedAssign === policy.policy_id ? null : policy.policy_id)
                  }
                >
                  Assign to Agent
                </Button>
              </div>
            </div>

            {expandedYaml === policy.policy_id && (
              <div className="mt-4 pt-4 border-t">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    Policy YAML — Version {policy.version}
                  </p>
                  <button
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                    onClick={() => {
                      navigator.clipboard.writeText(policy.policy_yaml)
                    }}
                  >
                    Copy
                  </button>
                </div>
                <pre className="bg-muted rounded-md p-4 text-xs font-mono overflow-x-auto whitespace-pre leading-relaxed max-h-96 overflow-y-auto">
                  {policy.policy_yaml}
                </pre>
              </div>
            )}

            {expandedAssign === policy.policy_id && (
              <AssignPolicyForm
                policy={policy}
                agents={agents}
                isAssigning={assigningPolicyId === policy.policy_id}
                onAssign={(targetAgentId) => {
                  onAssign(policy.policy_id, targetAgentId)
                  setExpandedAssign(null)
                }}
                onCancel={() => setExpandedAssign(null)}
              />
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// ─── Agent Overview Card ──────────────────────────────────────────────────────

function AgentOverviewCard({
  agentId,
  activePolicy,
  onManage,
}: {
  agentId: string
  activePolicy?: Policy
  onManage: () => void
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="font-mono text-base">{agentId}</CardTitle>
          {activePolicy ? (
            <Badge variant="success">Active v{activePolicy.version}</Badge>
          ) : (
            <Badge variant="secondary">No Policy</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {activePolicy ? (
          <div className="text-xs text-muted-foreground space-y-1">
            <p>Updated: {formatDate(activePolicy.created_at)}</p>
            {activePolicy.created_by && <p>By: {activePolicy.created_by}</p>}
            {activePolicy.description && (
              <p className="truncate">{activePolicy.description}</p>
            )}
            <p className="font-mono">Hash: {activePolicy.policy_hash?.substring(0, 12) ?? 'N/A'}…</p>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No active policy assigned.</p>
        )}
        <Button size="sm" className="w-full" onClick={onManage}>
          Manage Policies
        </Button>
      </CardContent>
    </Card>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function PoliciesPage() {
  const { customerId } = useCustomer()
  const [selectedAgent, setSelectedAgent] = useState('billing-agent')
  const [showEditor, setShowEditor] = useState(false)
  const [pageTab, setPageTab] = useState<'overview' | 'manage'>('overview')
  const [assigningPolicyId, setAssigningPolicyId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: agents = [] } = useQuery({
    queryKey: ['agents', customerId],
    queryFn: () => api.getAgents(customerId),
  })

  // All active policies across every agent (used for overview)
  const { data: allActivePolicies = [] } = useQuery({
    queryKey: ['policies', customerId, 'all-active'],
    queryFn: () => api.getPolicies({ customer_id: customerId, include_inactive: false }),
    enabled: pageTab === 'overview',
  })

  const { data: policies, isLoading } = useQuery({
    queryKey: ['policies', customerId, selectedAgent],
    queryFn: () =>
      api.getPolicies({ customer_id: customerId, agent_id: selectedAgent, include_inactive: true }),
    enabled: pageTab === 'manage',
  })

  const createMutation = useMutation({
    mutationFn: (data: { yaml: string; description: string }) =>
      api.createPolicy({
        customer_id: customerId,
        agent_id: selectedAgent,
        policy_yaml: data.yaml,
        description: data.description,
        created_by: `admin@${customerId}`,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] })
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      setShowEditor(false)
    },
  })

  const activateMutation = useMutation({
    mutationFn: (policyId: string) => api.activatePolicy(policyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['policies'] }),
  })

  const assignMutation = useMutation({
    mutationFn: ({ policyId, targetAgentId }: { policyId: string; targetAgentId: string }) =>
      api.assignPolicy(policyId, {
        target_agent_id: targetAgentId,
        created_by: `admin@${customerId}`,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] })
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      setAssigningPolicyId(null)
    },
    onError: () => setAssigningPolicyId(null),
  })

  const handleSave = async (yaml: string, description: string) => {
    await createMutation.mutateAsync({ yaml, description })
  }

  const handleAssign = (policyId: string, targetAgentId: string) => {
    setAssigningPolicyId(policyId)
    assignMutation.mutate({ policyId, targetAgentId })
  }

  const handleManageAgent = (agentId: string) => {
    setSelectedAgent(agentId)
    setShowEditor(false)
    setPageTab('manage')
  }

  const activePolicy = policies?.find((p) => p.is_active)

  // Merge agents from DB with any that appear only in allActivePolicies
  const allAgentIds = Array.from(
    new Set([...agents, ...allActivePolicies.map((p) => p.agent_id)])
  ).sort()

  const activePolicyByAgent = Object.fromEntries(
    allActivePolicies.map((p) => [p.agent_id, p])
  )

  return (
    <div className="min-h-screen bg-background">
      <main className="container mx-auto px-4 py-8 space-y-6">
        {/* Page-level tabs */}
        <Tabs value={pageTab} className="w-full">
          <TabsList>
            <TabsTrigger
              active={pageTab === 'overview'}
              onClick={() => setPageTab('overview')}
            >
              Agent Overview
            </TabsTrigger>
            <TabsTrigger
              active={pageTab === 'manage'}
              onClick={() => setPageTab('manage')}
            >
              Manage Policies
            </TabsTrigger>
          </TabsList>

          {/* ── Overview Tab ── */}
          <TabsContent value="overview">
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold">All Agents</h2>
                <p className="text-sm text-muted-foreground">
                  Active policy status for every agent in your account.
                </p>
              </div>

              {allAgentIds.length === 0 ? (
                <Card>
                  <CardContent className="py-12 text-center text-muted-foreground">
                    No agents found. Create a policy to register an agent.
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {allAgentIds.map((agentId) => (
                    <AgentOverviewCard
                      key={agentId}
                      agentId={agentId}
                      activePolicy={activePolicyByAgent[agentId]}
                      onManage={() => handleManageAgent(agentId)}
                    />
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          {/* ── Manage Tab ── */}
          <TabsContent value="manage">
            <div className="grid gap-6 lg:grid-cols-3">
              {/* Sidebar */}
              <Card className="lg:col-span-1">
                <CardHeader>
                  <CardTitle>Agent Selection</CardTitle>
                  <CardDescription>Choose an agent to manage policies</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-sm font-medium">Agent ID</label>
                    <select
                      className="w-full mt-2 p-2 border rounded-md"
                      value={selectedAgent}
                      onChange={(e) => {
                        setSelectedAgent(e.target.value)
                        setShowEditor(false)
                      }}
                    >
                      {/* Always show the selected agent even if not in list yet */}
                      {Array.from(new Set([...agents, selectedAgent])).sort().map((a) => (
                        <option key={a} value={a}>{a}</option>
                      ))}
                    </select>
                  </div>

                  {activePolicy && (
                    <div className="pt-4 border-t">
                      <h4 className="text-sm font-semibold mb-2">Active Policy</h4>
                      <div className="text-sm space-y-1">
                        <p>Version: {activePolicy.version}</p>
                        <p className="text-muted-foreground">
                          Updated: {formatDate(activePolicy.created_at)}
                        </p>
                      </div>
                    </div>
                  )}

                  <Button className="w-full" onClick={() => setShowEditor(!showEditor)}>
                    {showEditor ? 'View History' : 'Create New Version'}
                  </Button>
                </CardContent>
              </Card>

              {/* Main Content */}
              <div className="lg:col-span-2">
                {showEditor ? (
                  <Card>
                    <CardHeader>
                      <CardTitle>Policy Editor</CardTitle>
                      <CardDescription>Edit YAML policy for {selectedAgent}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <PolicyEditor
                        initialPolicy={activePolicy}
                        onSave={handleSave}
                        isSaving={createMutation.isPending}
                      />
                    </CardContent>
                  </Card>
                ) : (
                  <Card>
                    <CardHeader>
                      <CardTitle>Version History</CardTitle>
                      <CardDescription>All policy versions for {selectedAgent}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      {isLoading && (
                        <p className="text-center text-muted-foreground">Loading policies…</p>
                      )}
                      {!isLoading && policies && policies.length === 0 && (
                        <p className="text-center text-muted-foreground">
                          No policies found. Create one to get started.
                        </p>
                      )}
                      {!isLoading && policies && policies.length > 0 && (
                        <PolicyHistory
                          policies={policies}
                          agents={Array.from(new Set([...agents, selectedAgent])).sort()}
                          onActivate={(id) => activateMutation.mutate(id)}
                          onAssign={handleAssign}
                          assigningPolicyId={assigningPolicyId}
                        />
                      )}
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
