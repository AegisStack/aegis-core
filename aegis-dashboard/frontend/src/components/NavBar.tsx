'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState, useEffect } from 'react'
import { useCustomer } from '@/app/providers'
import { LayoutDashboard, ScrollText, AlertTriangle, Shield, ChevronsLeft, ChevronsRight, Search } from 'lucide-react'

const KNOWN_CUSTOMERS = ['acme-corp', 'beta-corp', 'test_customer']

const NAV_LINKS = [
  { href: '/',            label: 'Overview',    icon: LayoutDashboard },
  { href: '/audit',       label: 'Audit Log',   icon: ScrollText },
  { href: '/explore',     label: 'Log Explorer', icon: Search },
  { href: '/escalations', label: 'Escalations', icon: AlertTriangle },
  { href: '/policies',    label: 'Policies',    icon: Shield },
]

const STORAGE_KEY = 'aegis_sidebar_collapsed'

export function NavBar() {
  const pathname = usePathname()
  const { customerId, setCustomerId } = useCustomer()
  const [custom, setCustom] = useState('')
  const [showInput, setShowInput] = useState(false)
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'true') setCollapsed(true)
  }, [])

  function toggleCollapsed() {
    const next = !collapsed
    setCollapsed(next)
    localStorage.setItem(STORAGE_KEY, String(next))
  }

  function handleSelectChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value
    if (val === '__custom__') {
      setShowInput(true)
    } else {
      setShowInput(false)
      setCustomerId(val)
    }
  }

  function handleCustomSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (custom.trim()) {
      setCustomerId(custom.trim())
      setShowInput(false)
      setCustom('')
    }
  }

  return (
    <aside
      className={`flex flex-col border-r bg-card h-screen sticky top-0 transition-all duration-200 ${
        collapsed ? 'w-14' : 'w-56'
      }`}
    >
      {/* Brand */}
      <div className="flex items-center gap-2 px-3 py-4 border-b min-h-[56px]">
        <span className="text-xl">⚔️</span>
        {!collapsed && (
          <span className="font-bold text-lg tracking-tight whitespace-nowrap">
            Aegis
          </span>
        )}
      </div>

      {/* Nav links */}
      <nav className="flex-1 flex flex-col gap-1 p-2">
        {NAV_LINKS.map(({ href, label, icon: Icon }) => {
          const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              }`}
            >
              <Icon size={18} className="shrink-0" />
              {!collapsed && <span>{label}</span>}
            </Link>
          )
        })}
      </nav>

      {/* Customer switcher */}
      <div className="border-t p-2 space-y-2">
        {!collapsed && (
          <>
            <span className="text-xs text-muted-foreground px-1">Customer</span>
            {showInput ? (
              <form onSubmit={handleCustomSubmit} className="flex flex-col gap-1">
                <input
                  autoFocus
                  value={custom}
                  onChange={(e) => setCustom(e.target.value)}
                  placeholder="customer-id"
                  className="border rounded px-2 py-1 text-sm w-full bg-background"
                />
                <div className="flex gap-1">
                  <button
                    type="submit"
                    className="flex-1 text-xs px-2 py-1 rounded bg-primary text-primary-foreground"
                  >
                    Go
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowInput(false)}
                    className="text-xs px-2 py-1 rounded border"
                  >
                    ✕
                  </button>
                </div>
              </form>
            ) : (
              <select
                value={KNOWN_CUSTOMERS.includes(customerId) ? customerId : '__custom__'}
                onChange={handleSelectChange}
                className="border rounded px-2 py-1 text-sm w-full bg-background"
              >
                {KNOWN_CUSTOMERS.map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
                {!KNOWN_CUSTOMERS.includes(customerId) && (
                  <option value={customerId}>{customerId}</option>
                )}
                <option value="__custom__">+ Enter custom…</option>
              </select>
            )}
          </>
        )}

        {/* Collapse toggle */}
        <button
          onClick={toggleCollapsed}
          className="flex items-center justify-center w-full py-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronsRight size={16} /> : <ChevronsLeft size={16} />}
        </button>
      </div>
    </aside>
  )
}
