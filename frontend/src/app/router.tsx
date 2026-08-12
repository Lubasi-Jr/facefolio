import { Navigate, Route, Routes } from 'react-router-dom'
import { LoginPage } from '@/features/auth'
import { EventsDashboardPage, EventDetailPage } from '@/features/events'
import { JoinPage } from '@/features/enrollment'
import { AppLayout } from '@/components/layouts/AppLayout'
import { ProtectedRoute } from './ProtectedRoute'

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/join/:token" element={<JoinPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/events" replace />} />
        <Route path="/events" element={<EventsDashboardPage />} />
        <Route path="/events/:id" element={<EventDetailPage />} />
      </Route>
    </Routes>
  )
}
