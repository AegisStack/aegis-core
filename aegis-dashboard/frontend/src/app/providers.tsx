'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createContext, useContext, useState, useEffect } from 'react'

// ── Customer context ─────────────────────────────────────────────────────────

const STORAGE_KEY = 'aegis_customer_id'
const DEFAULT_CUSTOMER = 'acme-corp'

interface CustomerContextValue {
  customerId: string
  setCustomerId: (id: string) => void
}

export const CustomerContext = createContext<CustomerContextValue>({
  customerId: DEFAULT_CUSTOMER,
  setCustomerId: () => {},
})

export function useCustomer() {
  return useContext(CustomerContext)
}

// ── Providers ────────────────────────────────────────────────────────────────

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            refetchOnWindowFocus: false,
          },
        },
      })
  )

  const [customerId, setCustomerIdState] = useState<string>(DEFAULT_CUSTOMER)

  // Persist selection across page refreshes
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) setCustomerIdState(stored)
  }, [])

  function setCustomerId(id: string) {
    setCustomerIdState(id)
    localStorage.setItem(STORAGE_KEY, id)
    // Invalidate all cached queries so pages refetch for the new customer
    queryClient.invalidateQueries()
  }

  return (
    <CustomerContext.Provider value={{ customerId, setCustomerId }}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </CustomerContext.Provider>
  )
}
