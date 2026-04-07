'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LiveFeed } from '@/components/LiveFeed'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line
} from 'recharts'

// For demo purposes, using a hardcoded customer_id
// In production, this would come from auth context
const DEMO_CUSTOMER_ID = 'acme-corp'

export default function DashboardPage() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['metrics', DEMO_CUSTOMER_ID],
    queryFn: () => api.getMetricsSummary({ customer_id: DEMO_CUSTOMER_ID, period: '7d' }),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Loading dashboard...</div>
      </div>
    )
  }

  const outcomeData = [
    { name: 'Allowed', value: metrics?.allows || 0, fill: '#10b981' },
    { name: 'Denied', value: metrics?.denies || 0, fill: '#ef4444' },
    { name: 'Escalated', value: metrics?.escalations || 0, fill: '#f59e0b' },
  ]

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold">Aegis Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Policy enforcement observability for {DEMO_CUSTOMER_ID}
          </p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 space-y-8">
        {/* Metrics Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Calls</CardDescription>
              <CardTitle className="text-4xl">{metrics?.total_calls.toLocaleString()}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">Last 7 days</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Allowed</CardDescription>
              <CardTitle className="text-4xl text-green-600">
                {metrics?.allows.toLocaleString()}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                {metrics?.total_calls
                  ? ((metrics.allows / metrics.total_calls) * 100).toFixed(1)
                  : 0}
                % of total
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Denied</CardDescription>
              <CardTitle className="text-4xl text-red-600">
                {metrics?.denies.toLocaleString()}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                {metrics?.total_calls
                  ? ((metrics.denies / metrics.total_calls) * 100).toFixed(1)
                  : 0}
                % of total
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Escalations</CardDescription>
              <CardTitle className="text-4xl text-yellow-600">
                {metrics?.escalations.toLocaleString()}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                {metrics?.total_calls
                  ? ((metrics.escalations / metrics.total_calls) * 100).toFixed(1)
                  : 0}
                % of total
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Charts */}
        <div className="grid gap-4 md:grid-cols-2">
          {/* Outcome Distribution */}
          <Card>
            <CardHeader>
              <CardTitle>Outcome Distribution</CardTitle>
              <CardDescription>Policy enforcement outcomes (last 7 days)</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={outcomeData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Top Tools */}
          <Card>
            <CardHeader>
              <CardTitle>Top Tools</CardTitle>
              <CardDescription>Most frequently called tools</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={metrics?.top_tools || []} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis dataKey="tool" type="category" width={100} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Top Denied Rules */}
        <Card>
          <CardHeader>
            <CardTitle>Top Denied Rules</CardTitle>
            <CardDescription>Rules that most frequently deny tool calls</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {metrics?.top_denied_rules.map((rule, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <Badge variant="destructive">{rule.count}</Badge>
                    <code className="text-sm">{rule.rule}</code>
                  </div>
                </div>
              ))}
              {(!metrics?.top_denied_rules || metrics.top_denied_rules.length === 0) && (
                <p className="text-sm text-muted-foreground">No denied rules in this period</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Latency Stats and Live Feed */}
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Policy Evaluation Latency</CardTitle>
              <CardDescription>Performance metrics</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-sm text-muted-foreground">Average Latency</p>
                  <p className="text-2xl font-bold">{metrics?.latency.avg.toFixed(2)}ms</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Max Latency</p>
                  <p className="text-2xl font-bold">{metrics?.latency.max.toFixed(2)}ms</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <LiveFeed customerId={DEMO_CUSTOMER_ID} maxItems={5} />
        </div>
      </main>
    </div>
  )
}
