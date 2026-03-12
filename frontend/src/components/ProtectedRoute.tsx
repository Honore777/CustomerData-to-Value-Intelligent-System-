import { Navigate } from 'react-router-dom'
import React from 'react'

/*
CONCEPT:
- This component wraps pages that require login
- If authenticated, it renders the protected page
- If not authenticated, it redirects to /login
*/

type ProtectedRouteProps = {
  isAuthenticated: boolean
  children: React.ReactNode
}

export default function ProtectedRoute({
  isAuthenticated,
  children,
}: ProtectedRouteProps) {
  /*
  If user is not authenticated:
  - immediately redirect to login
  - replace=true prevents weird back-button history
  */
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  /*
  If authenticated:
  - render the protected content
  */
  return <>{children}</>
}