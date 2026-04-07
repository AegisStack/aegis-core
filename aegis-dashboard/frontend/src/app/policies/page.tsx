'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Policy } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { formatDate } from '@/lib/utils'

const DEMO_CUSTOMER_ID = 'acme-corp'
const DEMO_USER_EMAIL = 'admin@acme-corp.com'

const DEFAULT_POLICY = `version: 1
agent_role: your-agent
customer_id: ${DEMO_CUSTOMER_ID}

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
    try {
      // Basic YAML validation - check for required fields
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
    } catch (error) {
      setValidationError('Invalid YAML syntax')
      return false
    }
  }

  const handleSave = async () => {
    if (validateYaml(yaml)) {
      await onSave(yaml, description)
    }
  }

  // Parse YAML for preview
  const parseYamlForPreview = () => {
    try {
      const lines = yaml.split('\n')
      const rules: any[] = []
      let inRules = false
      let currentRule: any = null

      for (const line of lines) {
        if (line.trim().startsWith('- tool:')) {
          if (currentRule) rules.push(currentRule)
          currentRule = { tool: line.split(':')[1].trim(), conditions: [] }
        } else if (currentRule && (line.includes('allow:') || line.includes('deny:') || line.includes('escalate:'))) {
          const action = line.trim().replace(':', '')
          currentRule.conditions.push(action)
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
          <TabsTrigger
            active={activeTab === 'edit'}
            onClick={() => setActiveTab('edit')}
            className="flex-1"
          >
            Edit YAML
          </TabsTrigger>
          <TabsTrigger
            active={activeTab === 'preview'}
            onClick={() => setActiveTab('preview')}
            className="flex-1"
          >
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
                onChange={(e) => {
                  setYaml(e.target.value)
                  validateYaml(e.target.value)
                }}
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
                              condition.includes('allow')
                                ? 'success'
                                : condition.includes('deny')
                                ? 'destructive'
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
        <Button
          variant="outline"
          onClick={() => setYaml(DEFAULT_POLICY)}
          disabled={isSaving}
        >
          Reset to Template
        </Button>
        <Button
          onClick={handleSave}
          disabled={isSaving || !!validationError}
        >
          {isSaving ? 'Saving...' : 'Save Policy'}
        </Button>
      </div>
    </div>
  )
}

function PolicyHistory({ policies, onActivate }: {
  policies: Policy[]
  onActivate: (policyId: string) => void
}) {
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
                  <p className="font-mono">Hash: {policy.policy_hash.substring(0, 12)}...</p>
                </div>
              </div>
              {!policy.is_active && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onActivate(policy.policy_id)}
                >
                  Rollback
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export default function PoliciesPage() {
  const [selectedAgent, setSelectedAgent] = useState('billing-agent')
  const [showEditor, setShowEditor] = useState(false)
  const queryClient = useQueryClient()

  const { data: policies, isLoading } = useQuery({
    queryKey: ['policies', DEMO_CUSTOMER_ID, selectedAgent],
    queryFn: () =>
      api.getPolicies({
        customer_id: DEMO_CUSTOMER_ID,
        agent_id: selectedAgent,
        include_inactive: true,
      }),
  })

  const createMutation = useMutation({
    mutationFn: (data: { yaml: string; description: string }) =>
      api.createPolicy({
        customer_id: DEMO_CUSTOMER_ID,
        agent_id: selectedAgent,
        policy_yaml: data.yaml,
        description: data.description,
        created_by: DEMO_USER_EMAIL,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] })
      setShowEditor(false)
    },
  })

  const activateMutation = useMutation({
    mutationFn: (policyId: string) => api.activatePolicy(policyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] })
    },
  })

  const handleSave = async (yaml: string, description: string) => {
    await createMutation.mutateAsync({ yaml, description })
  }

  const activePolicy = policies?.find((p) => p.is_active)

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold">Policy Management</h1>
          <p className="text-sm text-muted-foreground">
            Configure and version control your agent policies
          </p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
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
                  onChange={(e) => setSelectedAgent(e.target.value)}
                >
                  <option value="billing-agent">billing-agent</option>
                  <option value="support-agent">support-agent</option>
                  <option value="admin-agent">admin-agent</option>
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

              <Button
                className="w-full"
                onClick={() => setShowEditor(!showEditor)}
              >
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
                  <CardDescription>
                    Edit YAML policy for {selectedAgent}
                  </CardDescription>
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
                  <CardDescription>
                    All policy versions for {selectedAgent}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {isLoading && (
                    <p className="text-center text-muted-foreground">Loading policies...</p>
                  )}
                  {!isLoading && policies && policies.length === 0 && (
                    <p className="text-center text-muted-foreground">
                      No policies found. Create one to get started.
                    </p>
                  )}
                  {!isLoading && policies && policies.length > 0 && (
                    <PolicyHistory
                      policies={policies}
                      onActivate={(id) => activateMutation.mutate(id)}
                    />
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
