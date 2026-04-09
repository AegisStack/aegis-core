'use client'

import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AreaChart, Area, ResponsiveContainer } from 'recharts'
import type { TimeseriesBucket } from '@/lib/api'

interface MetricCardProps {
  title: string
  value: number
  subtitle: string
  color: string
  sparklineData: TimeseriesBucket[]
  sparklineKey: 'total' | 'allows' | 'denies' | 'escalations'
  drillDownOutcome?: string
  startTime?: string
  endTime?: string
}

export function MetricCard({
  title,
  value,
  subtitle,
  color,
  sparklineData,
  sparklineKey,
  drillDownOutcome,
  startTime,
  endTime,
}: MetricCardProps) {
  const router = useRouter()

  const handleClick = () => {
    const params = new URLSearchParams()
    if (drillDownOutcome) params.set('outcome', drillDownOutcome)
    if (startTime) params.set('start', startTime)
    if (endTime) params.set('end', endTime)
    if (params.toString()) {
      router.push(`/explore?${params.toString()}`)
    }
  }

  const data = sparklineData.map((b) => ({ v: b[sparklineKey] }))

  return (
    <Card
      className="cursor-pointer hover:shadow-md transition-shadow"
      onClick={handleClick}
    >
      <CardHeader className="pb-2">
        <CardDescription>{title}</CardDescription>
        <CardTitle className={`text-4xl ${color}`}>
          {value.toLocaleString()}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground mb-2">{subtitle}</p>
        {data.length > 1 && (
          <div className="h-10">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
                <Area
                  type="monotone"
                  dataKey="v"
                  stroke={color.includes('green') ? '#22c55e' : color.includes('red') ? '#ef4444' : color.includes('yellow') ? '#f59e0b' : '#3b82f6'}
                  fill={color.includes('green') ? '#22c55e' : color.includes('red') ? '#ef4444' : color.includes('yellow') ? '#f59e0b' : '#3b82f6'}
                  fillOpacity={0.2}
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
