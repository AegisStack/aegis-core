/**
 * Shared test rendering helper - wraps a component with the same
 * QueryClientProvider + CustomerContext the real app provides, so
 * components using useQuery/useCustomer work in tests without needing the
 * full <Providers> (which reads localStorage and can't be pointed at a
 * specific customerId per test).
 */

import { ReactElement } from 'react'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CustomerContext } from '@/app/providers'

export function renderWithProviders(
  ui: ReactElement,
  { customerId = 'test-customer' }: { customerId?: string } = {}
) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <CustomerContext.Provider value={{ customerId, setCustomerId: jest.fn() }}>
        {ui}
      </CustomerContext.Provider>
    </QueryClientProvider>
  )
}
