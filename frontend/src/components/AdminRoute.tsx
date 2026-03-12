import React from 'react'
import { Navigate } from 'react-router-dom'

import { useAuthStore } from '../stores/authStore'

type AdminRouteProps = {
  isAuthenticated: boolean
  children: React.ReactNode
}

export default function AdminRoute({ isAuthenticated, children }: AdminRouteProps) {
  const user = useAuthStore((state) => state.user)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (!user?.is_platform_admin) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}