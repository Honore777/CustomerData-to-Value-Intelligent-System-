import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { authAPI } from '../services/api'
import { useAuthStore } from '../stores/authStore'

/*
REGISTER PAGE CONCEPTS APPLIED HERE:

1. Controlled components:
   - every input is tied to React state

2. Async submission:
   - user submits form
   - we call backend
   - backend creates business + owner + default location

3. UX states:
   - loading disables form while request is running
   - error shows backend or validation problems
*/


export default function Register() {
  // Form state: each field has its own state

  const setAuthenticated=useAuthStore((state)=>state.setAuthenticated)
const setUser=useAuthStore((state)=>state.setUser)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [businessName, setBusinessName] = useState('')
  const [country, setCountry] = useState('Rwanda')
  const [phone, setPhone] = useState('')

  // UI state
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const navigate = useNavigate()

  /*
  FORM SUBMISSION PATTERN TO MEMORIZE:
  1. stop browser refresh
  2. clear old error
  3. validate fields
  4. start loading
  5. call API
  6. redirect on success
  7. show error on failure
  8. stop loading
  */

  
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Basic validation before talking to backend
    if (!email.trim() || !password.trim() || !businessName.trim()) {
      setError('Please fill in all required fields')
      return
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    try {
      setLoading(true)

      // Backend expects: email, password, business_name, country, optional phone
      const response = await authAPI.signup(
        email,
        password,
        businessName,
        country,
        phone
      )

      console.log('Signup success:', response.data)
       setUser(response.data.user)
      setAuthenticated(true)
     

      // Cookie is already set by backend
      // so we can move user forward immediately
      navigate(response.data.user.is_platform_admin ? '/admin/businesses' : '/dashboard')
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || 'Registration failed'
      setError(errorMessage)
      console.error('Registration error:', errorMessage)
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
          <h1 className="mt-4 text-3xl font-black tracking-tight text-slate-950">
            Create Your Account
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Start turning customer data into visible revenue action
          </p>
        </div>

        {error && (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 p-3">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-4">
          <div>
            <label
              htmlFor="businessName"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
              Business Name
            </label>
            <input
              id="businessName"
              type="text"
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              placeholder="Northwind Trading"
              disabled={loading}
              className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-slate-900 outline-none focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100 disabled:bg-slate-100"
            />
          </div>

          <div>
            <label
              htmlFor="email"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
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
            <label
              htmlFor="country"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
              Country
            </label>
            <select
              id="country"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              disabled={loading}
              className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-slate-900 outline-none focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100 disabled:bg-slate-100"
            >
              <option value="Rwanda">Rwanda</option>
              <option value="Uganda">Uganda</option>
              <option value="Kenya">Kenya</option>
              <option value="Nigeria">Nigeria</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 characters"
              disabled={loading}
              className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-slate-900 outline-none focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100 disabled:bg-slate-100"
            />
          </div>

          <div>
            <label
              htmlFor="phone"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
              Business phone (optional)
            </label>
            <input
              id="phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="0781234567"
              disabled={loading}
              className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-slate-900 outline-none focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100 disabled:bg-slate-100"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-full bg-[linear-gradient(135deg,#111827_0%,#0f766e_55%,#c2410c_100%)] px-4 py-3 font-semibold text-white transition hover:translate-y-[-1px] disabled:bg-slate-400"
          >
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-slate-600">
          Already have an account?{' '}
          <Link
            to="/login"
            className="font-semibold text-cyan-700 hover:text-cyan-800"
          >
            Login here
          </Link>
        </div>
      </div>
    </div>
  )
}