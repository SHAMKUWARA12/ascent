import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getAdvisor } from '../services/api'

const BRANCH_OPTIONS = [
  { code: 'CSE', name: 'Computer Science & Engineering' },
  { code: 'AI',  name: 'Artificial Intelligence' },
  { code: 'DS',  name: 'Data Science & Engineering' },
  { code: 'IT',  name: 'Information Technology' },
  { code: 'ML',  name: 'Machine Learning' },
  { code: 'CY',  name: 'Cyber Security' },
  { code: 'SE',  name: 'Software Engineering' },
  { code: 'DE',  name: 'Data Engineering' },
  { code: 'IS',  name: 'Information Security' },
  { code: 'HCI', name: 'Human Computer Interaction' },
]

const NIT_OPTIONS = [
  'NIT Silchar', 'NIT Rourkela', 'NIT Trichy',
  'NIT Warangal', 'NIT Calicut'
]

export default function Advisor() {
  const { token } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    current_nit: '',
    current_branch: '',
    target_nit: '',
    target_branch: ''
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const res = await getAdvisor(
        token,
        form.current_nit,
        form.current_branch,
        form.target_nit,
        form.target_branch
      )
      setResult(res.data)
    } catch (err) {
      setError(
        err.response?.data?.detail || 'Something went wrong. Try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  const isSameNIT = form.current_nit &&
    form.target_nit &&
    form.current_nit === form.target_nit

  const recColor = {
    FLOAT: 'bg-green-50 border-green-200',
    LOCK:  'bg-amber-50 border-amber-200',
    SLIDE: 'bg-blue-50  border-blue-200'
  }

  const recTextColor = {
    FLOAT: 'text-green-700',
    LOCK:  'text-amber-700',
    SLIDE: 'text-blue-700'
  }

  const riskBadge = {
    'LOW':       'bg-green-100 text-green-700',
    'MEDIUM':    'bg-amber-100 text-amber-700',
    'HIGH':      'bg-red-100   text-red-600',
    'VERY HIGH': 'bg-red-200   text-red-700'
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-xl mx-auto">

        <button
          onClick={() => navigate('/dashboard')}
          className="text-blue-600 text-sm mb-4 hover:underline"
        >
          ← Back to Dashboard
        </button>

        <h1 className="text-2xl font-bold text-blue-900 mb-1">
          Lock / Float / Slide Advisor
        </h1>
        <p className="text-gray-400 text-sm mb-2">
          Enter your current allocation and your target to get
          a data-driven recommendation.
        </p>

        {/* Explanation */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 mb-6 text-xs text-blue-800">
          <p className="font-semibold mb-1">What do these mean?</p>
          <p><strong>LOCK</strong> — Accept current seat and exit counselling</p>
          <p><strong>FLOAT</strong> — Keep current seat and try for a better NIT</p>
          <p><strong>SLIDE</strong> — Try for a better branch at the SAME NIT
            (releases current branch — risky)</p>
        </div>

        {/* Form */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-6">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">

            {/* Current allocation */}
            <div>
              <p className="text-sm font-semibold text-gray-700 mb-3">
                Current Allocation
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">
                    NIT
                  </label>
                  <select
                    value={form.current_nit}
                    onChange={e => setForm({...form, current_nit: e.target.value})}
                    required
                    className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-blue-400 bg-white"
                  >
                    <option value="">Select NIT</option>
                    {NIT_OPTIONS.map(n => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">
                    Branch
                  </label>
                  <select
                    value={form.current_branch}
                    onChange={e => setForm({...form, current_branch: e.target.value})}
                    required
                    className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-blue-400 bg-white"
                  >
                    <option value="">Select Branch</option>
                    {BRANCH_OPTIONS.map(b => (
                      <option key={b.code} value={b.code}>{b.code}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Divider */}
            <div className="flex items-center gap-3">
              <div className="flex-1 h-px bg-gray-100" />
              <span className="text-xs text-gray-400">wants to upgrade to</span>
              <div className="flex-1 h-px bg-gray-100" />
            </div>

            {/* Target */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-semibold text-gray-700">
                  Target
                </p>
                {isSameNIT && (
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">
                    Same NIT → SLIDE scenario
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">
                    Target NIT
                  </label>
                  <select
                    value={form.target_nit}
                    onChange={e => setForm({...form, target_nit: e.target.value})}
                    required
                    className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-blue-400 bg-white"
                  >
                    <option value="">Select NIT</option>
                    {NIT_OPTIONS.map(n => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">
                    Target Branch
                  </label>
                  <select
                    value={form.target_branch}
                    onChange={e => setForm({...form, target_branch: e.target.value})}
                    className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-blue-400 bg-white"
                  >
                    <option value="">Any branch</option>
                    {BRANCH_OPTIONS.map(b => (
                      <option key={b.code} value={b.code}>{b.code}</option>
                    ))}
                  </select>
                </div>
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
              className="bg-blue-900 text-white font-semibold py-2.5 rounded-xl hover:bg-blue-800 disabled:opacity-50 text-sm"
            >
              {loading ? 'Analysing...' : 'Get Recommendation'}
            </button>

          </form>
        </div>

        {/* Result */}
        {result && (
          <div className="flex flex-col gap-4">

            <div className={`border rounded-2xl p-5 ${recColor[result.recommendation] || 'bg-gray-50 border-gray-200'}`}>
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold text-gray-800">
                  Recommendation
                </h2>
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${riskBadge[result.risk_level] || 'bg-gray-100 text-gray-600'}`}>
                  Risk: {result.risk_level}
                </span>
              </div>

              <p className={`text-3xl font-bold mb-2 ${recTextColor[result.recommendation] || 'text-gray-800'}`}>
                {result.recommendation}
              </p>

              <p className="text-sm text-gray-600 leading-relaxed">
                {result.reason}
              </p>

              <div className="mt-4 grid grid-cols-3 gap-3">
                <div className="bg-white rounded-xl p-3 text-center">
                  <p className="text-xs text-gray-400 mb-1">Current</p>
                  <p className="font-semibold text-gray-800 text-xs">
                    {result.current_allocation}
                  </p>
                  <p className="text-xs text-blue-600 font-medium">
                    {result.current_branch}
                  </p>
                </div>
                <div className="bg-white rounded-xl p-3 text-center">
                  <p className="text-xs text-gray-400 mb-1">Target</p>
                  <p className="font-semibold text-gray-800 text-xs">
                    {result.target_nit}
                  </p>
                  <p className="text-xs text-blue-600 font-medium">
                    {result.target_branch || 'Best available'}
                  </p>
                </div>
                <div className="bg-white rounded-xl p-3 text-center">
                  <p className="text-xs text-gray-400 mb-1">Probability</p>
                  <p className="font-bold text-gray-800 text-lg">
                    {result.target_probability}%
                  </p>
                </div>
              </div>

              {result.same_nit && (
                <div className="mt-3 bg-blue-100 rounded-xl px-3 py-2 text-xs text-blue-800">
                  Same NIT detected — this is a SLIDE scenario (branch upgrade within same NIT)
                </div>
              )}
            </div>

            {/* Options */}
            <div className="bg-white rounded-2xl border border-gray-100 p-5">
              <h2 className="font-semibold text-gray-800 mb-4">
                All Options Explained
              </h2>
              {Object.entries(result.options || {}).map(([key, val]) => (
                <div
                  key={key}
                  className={`rounded-xl p-4 mb-3 border ${
                    key === result.recommendation
                      ? 'border-blue-200 bg-blue-50'
                      : 'border-gray-100 bg-gray-50'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`font-bold text-sm ${
                      key === result.recommendation
                        ? 'text-blue-900'
                        : 'text-gray-500'
                    }`}>
                      {key}
                    </span>
                    {key === result.recommendation && (
                      <span className="text-xs bg-blue-900 text-white px-2 py-0.5 rounded-full">
                        Recommended
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mb-2">
                    {val.description}
                  </p>
                  <div className="flex gap-4">
                    <div className="flex-1">
                      <p className="text-xs text-green-600 font-medium">Pro</p>
                      <p className="text-xs text-gray-600">{val.pro}</p>
                    </div>
                    <div className="flex-1">
                      <p className="text-xs text-red-500 font-medium">Con</p>
                      <p className="text-xs text-gray-600">{val.con}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

          </div>
        )}
      </div>
    </div>
  )
}