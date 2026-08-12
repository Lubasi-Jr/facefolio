import { useState } from 'react'
import type React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { Card } from '@/components/ui/Card'
import { Label } from '@/components/ui/Label'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'

type Status = 'idle' | 'submitting' | 'sent' | 'error'

export function LoginPage() {
  const { session, loading, signInWithOtp } = useAuth()
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<Status>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  // Already signed in — nothing to do here.
  if (!loading && session) {
    return <Navigate to="/events" replace />
  }

  const handleSubmit: React.SubmitEventHandler<HTMLFormElement> = async (event) => {
    event.preventDefault()
    setStatus('submitting')
    setErrorMessage('')
    try {
      await signInWithOtp(email)
      setStatus('sent')
    } catch (error) {
      setStatus('error')
      setErrorMessage(
        error instanceof Error ? error.message : 'Something went wrong. Try again.',
      )
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <h1 className="font-heading text-h1 text-text-primary">Log in</h1>
        <p className="mt-2 text-body text-text-secondary">
          Enter your email and we&apos;ll send you a link to sign in.
        </p>

        {status === 'sent' ? (
          <div className="mt-8 rounded-interactive bg-success-bg px-4 py-3 text-body text-success">
            Check your email for a sign-in link.
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-4" noValidate>
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                required
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                disabled={status === 'submitting'}
              />
            </div>

            {status === 'error' && (
              <div className="rounded-interactive bg-danger-bg px-4 py-3 text-small text-danger">
                {errorMessage}
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              fullWidth
              isLoading={status === 'submitting'}
            >
              Send magic link
            </Button>
          </form>
        )}
      </Card>
    </div>
  )
}
