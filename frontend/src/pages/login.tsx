import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { authAPI } from '../services/api'
import { useAuthStore } from '../stores/authStore'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const navigate = useNavigate()

  const setAuthenticated = useAuthStore((state) => state.setAuthenticated)
  const setUser = useAuthStore((state) => state.setUser)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!email.trim() || !password.trim()) {
      setError('Please enter email and password')
      return
    }

    try {
      setLoading(true)

      const response = await authAPI.login(email, password)

      /*
      response.data.user comes from backend TokenResponse
      We store it in global Zustand state
      */
      setUser(response.data.user)
      setAuthenticated(true)

      navigate(response.data.user.is_platform_admin ? '/admin/businesses' : '/dashboard')
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Login failed'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(249,115,22,0.14),_transparent_30%),radial-gradient(circle_at_top_right,_rgba(8,145,178,0.16),_transparent_24%),linear-gradient(180deg,_#fff7ed_0%,_#f8fafc_40%,_#e2e8f0_100%)] flex items-center justify-center p-4">
      <div className="w-full max-w-md rounded-[28px] border border-white/90 bg-white/90 p-8 shadow-[0_30px_90px_rgba(15,23,42,0.12)] backdrop-blur">
        <div className="mb-8 text-center">
          <Link to="/" className="text-[11px] font-semibold uppercase tracking-[0.3em] text-cyan-700">
            Customer Revenue Intelligence
          </Link>
          <h1 className="mt-4 text-3xl font-black tracking-tight text-slate-950">Welcome back</h1>
          <p className="mt-2 text-sm text-slate-600">Sign in to review customer movement, revenue concentration, and next actions.</p>
        </div>

        {error && (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 p-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label htmlFor="email" className="mb-2 block text-sm font-medium text-slate-700">
              Email Address
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="owner@business.com"
              disabled={loading}
              className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-slate-900 outline-none focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100 disabled:bg-slate-100"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-2 block text-sm font-medium text-slate-700">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              disabled={loading}
              className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-slate-900 outline-none focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100 disabled:bg-slate-100"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-full bg-[linear-gradient(135deg,#111827_0%,#0f766e_55%,#c2410c_100%)] px-4 py-3 font-semibold text-white transition hover:translate-y-[-1px] disabled:bg-slate-400"
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-slate-600">
            Don't have an account?{' '}
            <Link to="/register" className="font-semibold text-cyan-700 hover:text-cyan-800">
              Start here
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}