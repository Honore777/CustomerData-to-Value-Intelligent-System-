import { Navigate } from 'react-router-dom'
import React from 'react'

type PublicOnlyRouteProps = {
  isAuthenticated: boolean
  children: React.ReactNode
}

/*
CONCEPT:
- This wrapper is the opposite of ProtectedRoute
- It is only for pages like login and register
- If user is already logged in, redirect to dashboard
- If user is not logged in, allow page to render
*/

export default function PublicOnlyRoute({
  isAuthenticated,
  children,
}: PublicOnlyRouteProps) {
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}