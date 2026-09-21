'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getAccessToken } from '@/lib/auth'

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    const onLoginPage = window.location.pathname === '/login'
    if (onLoginPage || getAccessToken()) {
      setChecked(true)
    } else {
      router.replace('/login')
    }
  }, [router])

  if (!checked) return null

  return <>{children}</>
}
