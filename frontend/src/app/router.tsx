import { Navigate, Route, Routes } from 'react-router-dom'
import { LoginPage } from '@/features/auth'
import { EventsDashboardPage, EventDetailPage } from '@/features/events'
import { JoinPage } from '@/features/enrollment'
import { ProtectedRoute } from './ProtectedRoute'

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/events" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/events"
        element={
          <ProtectedRoute>
            <EventsDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/events/:id"
        element={
          <ProtectedRoute>
            <EventDetailPage />
          </ProtectedRoute>
        }
      />
      <Route path="/join/:token" element={<JoinPage />} />
    </Routes>
  )
}
