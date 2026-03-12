import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import SegmentCustomers from './pages/SegmentCustomers'
import VipCustomers from './pages/VipCustomers'
import LandingPage from './pages/LandingPage'
import ProtectedRoute from './components/ProtectedRoute'
import PublicOnlyRoute from './components/PublicOnlyRoute'
import AdminRoute from './components/AdminRoute'
import { authAPI } from './services/api'
import { useAuthStore } from './stores/authStore'
import CustomerDetail from './pages/CustomerDetail'
import AdminBusinesses from './pages/AdminBusinesses'

function App() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const checkingAuth = useAuthStore((state) => state.checkingAuth)
  const user = useAuthStore((state) => state.user)
  const setAuthenticated = useAuthStore((state) => state.setAuthenticated)
  const setCheckingAuth = useAuthStore((state) => state.setCheckingAuth)
  const setUser = useAuthStore((state) => state.setUser)
  const clearAuth = useAuthStore((state) => state.clearAuth)

  useEffect(() => {
    const checkSession = async () => {
      try {
        const response = await authAPI.getMe()
        setUser(response.data)
        setAuthenticated(true)
      } catch (error) {
        clearAuth()
      } finally {
        setCheckingAuth(false)
      }
    }

    checkSession()
  }, [setAuthenticated, setCheckingAuth, setUser, clearAuth])

  if (checkingAuth) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center">
        <div className="rounded-xl bg-white px-6 py-4 shadow-sm">
          <p className="text-slate-700 font-medium">Checking session...</p>
        </div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            <PublicOnlyRoute isAuthenticated={isAuthenticated}>
              <LandingPage />
            </PublicOnlyRoute>
          }
        />

        <Route
          path="/login"
          element={
            <PublicOnlyRoute isAuthenticated={isAuthenticated}>
              <Login />
            </PublicOnlyRoute>
          }
        />

        <Route
          path="/register"
          element={
            <PublicOnlyRoute isAuthenticated={isAuthenticated}>
              <Register />
            </PublicOnlyRoute>
          }
        />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/segments/:segment"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <SegmentCustomers />
            </ProtectedRoute>
          }
        />
        <Route
          path="/vip-members"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <VipCustomers />
            </ProtectedRoute>
          }
        />
        <Route path='/customers/:customerId'
        element={
          <ProtectedRoute isAuthenticated={isAuthenticated}>
            <CustomerDetail/>
          </ProtectedRoute>
        }
        />
        <Route
          path="/admin/businesses"
          element={
            <AdminRoute isAuthenticated={isAuthenticated}>
              <AdminBusinesses />
            </AdminRoute>
          }
        />

        <Route path="*" element={<Navigate to={isAuthenticated ? (user?.is_platform_admin ? '/admin/businesses' : '/dashboard') : '/'} replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App