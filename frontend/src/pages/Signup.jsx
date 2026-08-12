import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { signup } from '../services/api'

export default function Signup() {
  const { loginUser } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    gate_paper: 'CS'
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const res = await signup(form)
      const { token, student } = res.data
      loginUser(token, student)
      navigate('/profile')
    } catch (err) {
      setError(
        err.response?.data?.detail || 'Signup failed. Please try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 w-full max-w-md">

        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-blue-900 mb-1">
            Create your account
          </h1>
          <p className="text-gray-400 text-sm">
            Free · No credit card required
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">

          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">
              Full Name
            </label>
            <input
              type="text"
              name="full_name"
              value={form.full_name}
              onChange={handleChange}
              placeholder="Rahul Sharma"
              required
              className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">
              Email
            </label>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="rahul@example.com"
              required
              className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">
              Password
            </label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              placeholder="minimum 6 characters"
              required
              minLength={6}
              className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">
              GATE Paper
            </label>
            <div className="flex gap-3">
              {['CS', 'DA'].map(paper => (
                <button
                  key={paper}
                  type="button"
                  onClick={() => setForm({ ...form, gate_paper: paper })}
                  className={`flex-1 py-2.5 rounded-xl border text-sm font-medium transition-all ${
                    form.gate_paper === paper
                      ? 'bg-blue-900 text-white border-blue-900'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'
                  }`}
                >
                  GATE {paper}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 text-red-600 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="bg-blue-900 text-white font-semibold py-2.5 rounded-xl hover:bg-blue-800 disabled:opacity-50 mt-2"
          >
            {loading ? 'Creating account...' : 'Create Account'}
          </button>

        </form>

        {/* Footer */}
        <p className="text-center text-sm text-gray-400 mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-700 font-medium hover:underline">
            Login
          </Link>
        </p>

      </div>
    </div>
  )
}