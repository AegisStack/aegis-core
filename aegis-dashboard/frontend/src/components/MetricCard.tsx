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
                <defs>
                  <linearGradient id={`spark-${sparklineKey}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={color.includes('green') ? '#1DB954' : color.includes('red') ? '#E5473B' : color.includes('yellow') ? '#F5A623' : '#4B87F5'} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={color.includes('green') ? '#1DB954' : color.includes('red') ? '#E5473B' : color.includes('yellow') ? '#F5A623' : '#4B87F5'} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="v"
                  stroke={color.includes('green') ? '#1DB954' : color.includes('red') ? '#E5473B' : color.includes('yellow') ? '#F5A623' : '#4B87F5'}
                  fill={`url(#spark-${sparklineKey})`}
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
