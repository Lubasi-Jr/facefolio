import { Outlet } from 'react-router-dom'

// Lighter than AppLayout on purpose: guests aren't authenticated hosts, so
// there's no nav, no account chrome, no sign-out — just the wordmark.
export function GuestLayout() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b border-border">
        <div className="max-w-md mx-auto px-4 sm:px-6 py-4">
          <span className="font-heading text-h2 text-primary">FaceFolio</span>
        </div>
      </header>
      <main className="flex-1 flex items-center justify-center px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
