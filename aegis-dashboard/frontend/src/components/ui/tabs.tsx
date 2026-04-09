import * as React from "react"
import { cn } from "@/lib/utils"

// Context so TabsContent can read the active value set on Tabs
interface TabsContextValue {
  value?: string
}
const TabsContext = React.createContext<TabsContextValue>({})

interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: string
}

const Tabs = React.forwardRef<HTMLDivElement, TabsProps>(
  ({ className, value, ...props }, ref) => (
    <TabsContext.Provider value={{ value }}>
      <div ref={ref} className={cn("w-full", className)} {...props} />
    </TabsContext.Provider>
  )
)
Tabs.displayName = "Tabs"

const TabsList = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground",
      className
    )}
    {...props}
  />
))
TabsList.displayName = "TabsList"

const TabsTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }
>(({ className, active, ...props }, ref) => (
  <button
    ref={ref}
    className={cn(
      "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
      active
        ? "bg-background text-foreground shadow-sm"
        : "text-muted-foreground hover:bg-background/50",
      className
    )}
    {...props}
  />
))
TabsTrigger.displayName = "TabsTrigger"

interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string
}

const TabsContent = React.forwardRef<HTMLDivElement, TabsContentProps>(
  ({ className, value, ...props }, ref) => {
    const { value: activeValue } = React.useContext(TabsContext)

    // When a Tabs parent is present with an explicit value, only render the
    // matching panel. If Tabs has no value (uncontrolled usage) always render.
    if (activeValue !== undefined && value !== activeValue) return null

    return (
      <div ref={ref} className={cn("mt-2", className)} {...props} />
    )
  }
)
TabsContent.displayName = "TabsContent"

export { Tabs, TabsList, TabsTrigger, TabsContent }
