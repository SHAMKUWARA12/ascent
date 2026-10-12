import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getAdvisor, getAllNits } from '../services/api'

export default function Advisor() {
  const { token } = useAuth()
  const navigate  = useNavigate()

  const [nitList,       setNitList]       = useState([])
  const [branchOptions, setBranchOptions] = useState([])
  const [currentNIT,    setCurrentNIT]    = useState('')
  const [currentBranch, setCurrentBranch] = useState('')
  const [targetNIT,     setTargetNIT]     = useState('')
  const [targetBranch,  setTargetBranch]  = useState('Any branch')
  const [result,        setResult]        = useState(null)
  const [loading,       setLoading]       = useState(false)
  const [error,         setError]         = useState('')
  const [showList,      setShowList]      = useState(false)

  useEffect(() => {
    fetchNitOptions()
  }, [])

  const fetchNitOptions = async () => {
    try {
      const res  = await getAllNits()
      const nits = res.data.nits

      setNitList(nits.map(n => n.name).sort())

      const branchSet = new Map()
      nits.forEach(n => {
        ;(n.mtech_programs || []).forEach(p => {
          branchSet.set(p.short_name, p.short_name_full || p.short_name)
        })
      })
      setBranchOptions(
        Array.from(branchSet, ([code, name]) => ({ code, name }))
          .sort((a, b) => a.code.localeCompare(b.code))
      )
    } catch (err) {
      console.error('Could not load NIT list', err)
    }
  }

  const handleSubmit = async () => {
    if (!currentNIT || !currentBranch || !targetNIT) {
      setError('Please select current NIT, branch, and target NIT.')
      return
    }
    setError('')
    setLoading(true)
    setResult(null)
    setShowList(false)
    try {
      const res = await getAdvisor(
        token, currentNIT, currentBranch,
        targetNIT, targetBranch
      )
      setResult(res.data)
    } catch (err) {
      setError('Something went wrong. Try again.')
    } finally {
      setLoading(false)
    }
  }

  const bucketColor = bucket => {
    if (bucket === 'Safe')      return 'text-green-600'
    if (bucket === 'Target')    return 'text-amber-600'
    if (bucket === 'Ambitious') return 'text-red-500'
    return 'text-gray-600'
  }

  const recColor = rec => {
    if (rec === 'FLOAT') return 'text-green-700 bg-green-50 border-green-200'
    if (rec === 'SLIDE') return 'text-blue-700 bg-blue-50 border-blue-200'
    return 'text-gray-800 bg-gray-50 border-gray-200'
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-blue-900 text-white px-6 py-5">
        <button
          onClick={() => navigate('/dashboard')}
          className="text-blue-300 text-sm mb-2 hover:text-white"
        >
          ← Back to Dashboard
        </button>
        <h1 className="text-xl font-bold">
          Lock / Float / Slide Advisor
        </h1>
        <p className="text-blue-200 text-sm mt-1">
          Enter your current allocation and your target to get
          a data-driven recommendation.
        </p>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6">

        {/* Definitions */}
        <div className="bg-white rounded-2xl border border-gray-100 p-4 mb-4 text-sm">
          <p className="font-semibold text-gray-700 mb-2">
            What do these mean?
          </p>
          <p className="mb-1">
            <span className="font-bold text-gray-800">LOCK</span>
            {' — '}Accept current seat and exit counselling
          </p>
          <p className="mb-1">
            <span className="font-bold text-green-700">FLOAT</span>
            {' — '}Keep current seat and try for a better NIT
          </p>
          <p>
            <span className="font-bold text-blue-700">SLIDE</span>
            {' — '}Try for a better branch at the SAME NIT
            (releases current branch — risky)
          </p>
        </div>

        {/* Form */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
          <p className="text-sm font-semibold text-gray-700 mb-3">
            Current Allocation
          </p>
          <div className="flex gap-3 mb-4">
            <select
              value={currentNIT}
              onChange={e => setCurrentNIT(e.target.value)}
              className="flex-1 border border-gray-200 rounded-xl px-3 py-2.5 text-sm bg-white focus:outline-none focus:border-blue-400"
            >
              <option value="">Select NIT</option>
              {nitList.map(n => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
            <select
              value={currentBranch}
              onChange={e => setCurrentBranch(e.target.value)}
              className="flex-1 border border-gray-200 rounded-xl px-3 py-2.5 text-sm bg-white focus:outline-none focus:border-blue-400"
            >
              <option value="">Select Branch</option>
              {branchOptions.map(b => (
                <option key={b.code} value={b.code}>{b.code}</option>
              ))}
            </select>
          </div>

          <p className="text-xs text-center text-gray-400 mb-3">
            wants to upgrade to
          </p>

          <p className="text-sm font-semibold text-gray-700 mb-3">
            Target
          </p>
          <div className="flex gap-3 mb-4">
            <select
              value={targetNIT}
              onChange={e => setTargetNIT(e.target.value)}
              className="flex-1 border border-gray-200 rounded-xl px-3 py-2.5 text-sm bg-white focus:outline-none focus:border-blue-400"
            >
              <option value="">Select NIT</option>
              {nitList.map(n => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
            <select
              value={targetBranch}
              onChange={e => setTargetBranch(e.target.value)}
              className="flex-1 border border-gray-200 rounded-xl px-3 py-2.5 text-sm bg-white focus:outline-none focus:border-blue-400"
            >
              <option value="Any branch">Any branch</option>
              {branchOptions.map(b => (
                <option key={b.code} value={b.code}>{b.code}</option>
              ))}
            </select>
          </div>

          {error && (
            <p className="text-red-500 text-sm mb-3">{error}</p>
          )}

          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full bg-blue-900 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-800 disabled:opacity-50"
          >
            {loading ? 'Analysing...' : 'Get Recommendation'}
          </button>
        </div>

        {/* Result */}
        {result && (
          <>
            {/* Main recommendation card */}
            <div className={`rounded-2xl border p-5 mb-4 ${recColor(result.recommendation)}`}>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium opacity-60">
                  Recommendation
                </p>
                <span className="text-xs font-semibold opacity-60">
                  Risk: {result.risk_level}
                </span>
              </div>
              <p className="text-4xl font-black mb-3">
                {result.recommendation}
              </p>
              <p className="text-sm leading-relaxed mb-4">
                {result.reason}
              </p>

              {/* Current vs Target vs Probability */}
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="bg-white bg-opacity-60 rounded-xl p-3">
                  <p className="text-xs opacity-50 mb-1">Current</p>
                  <p className="font-semibold text-sm">
                    {result.current_branch || currentBranch}
                  </p>
                  <p className="text-xs opacity-50">
                    {result.current_nirf_display}
                  </p>
                </div>
                <div className="bg-white bg-opacity-60 rounded-xl p-3">
                  <p className="text-xs opacity-50 mb-1">Target</p>
                  <p className="font-semibold text-sm">
                    {result.target_branch || targetBranch}
                  </p>
                  <p className="text-xs opacity-50">
                    {result.target_nirf_display}
                  </p>
                </div>
                <div className="bg-white bg-opacity-60 rounded-xl p-3">
                  <p className="text-xs opacity-50 mb-1">Probability</p>
                  <p className="font-bold text-lg">
                    {result.probability}%
                  </p>
                </div>
              </div>

              {/* Preference list positions */}
              {(result.current_pref_no || result.target_pref_no) && (
                <div className="flex gap-3 mt-3">
                  {result.current_pref_no && (
                    <div className="bg-white bg-opacity-60 rounded-xl p-3 flex-1 text-center">
                      <p className="text-xs opacity-50 mb-1">
                        Your list position (current)
                      </p>
                      <p className="font-bold text-lg">
                        #{result.current_pref_no}
                      </p>
                    </div>
                  )}
                  {result.target_pref_no && (
                    <div className="bg-white bg-opacity-60 rounded-xl p-3 flex-1 text-center">
                      <p className="text-xs opacity-50 mb-1">
                        Your list position (target)
                      </p>
                      <p className="font-bold text-lg">
                        #{result.target_pref_no}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Button to view better preferences */}
            {result.better_preferences &&
             result.better_preferences.length > 0 && (
              <button
                onClick={() => setShowList(!showList)}
                className="w-full bg-white border border-blue-200 text-blue-800 py-3 rounded-xl font-semibold text-sm hover:bg-blue-50 mb-4"
              >
                {showList
                  ? 'Hide preference list'
                  : `View ${result.better_preferences.length} options better than your current seat`
                }
              </button>
            )}

            {/* Better preferences modal/panel */}
            {showList && result.better_preferences?.length > 0 && (
              <div className="bg-white rounded-2xl border border-gray-100 p-4 mb-4">
                <p className="text-sm font-semibold text-gray-800 mb-1">
                  Options ranked higher than your current seat
                </p>
                <p className="text-xs text-gray-400 mb-3">
                  These are all the NIT+branch combinations that
                  appear ABOVE your current allocation in your
                  generated preference list. CCMT will try to allot
                  these first before reaching your current seat.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-100">
                        <th className="text-left py-2 text-gray-400 font-medium">
                          #
                        </th>
                        <th className="text-left py-2 text-gray-400 font-medium">
                          NIT
                        </th>
                        <th className="text-left py-2 text-gray-400 font-medium">
                          Branch
                        </th>
                        <th className="text-left py-2 text-gray-400 font-medium">
                          Prob
                        </th>
                        <th className="text-left py-2 text-gray-400 font-medium">
                          Bucket
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.better_preferences.map((p, i) => (
                        <tr
                          key={i}
                          className="border-b border-gray-50"
                        >
                          <td className="py-2 text-gray-400">
                            {p.preference_no}
                          </td>
                          <td className="py-2 font-medium text-gray-800">
                            {p.nit_name}
                          </td>
                          <td className="py-2 text-gray-600">
                            {p.branch}
                          </td>
                          <td className="py-2 font-semibold text-blue-800">
                            {p.probability}%
                          </td>
                          <td className={`py-2 font-semibold ${bucketColor(p.bucket)}`}>
                            {p.bucket}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* All 3 options explained */}
            {result.all_options && (
              <div className="bg-white rounded-2xl border border-gray-100 p-5">
                <p className="text-sm font-semibold text-gray-800 mb-4">
                  All Options Explained
                </p>
                {Object.entries(result.all_options).map(
                  ([key, opt]) => (
                    <div
                      key={key}
                      className={`rounded-xl border p-4 mb-3 ${
                        result.recommendation === key
                          ? 'border-blue-300 bg-blue-50'
                          : 'border-gray-100 bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-bold text-gray-800 text-sm">
                          {opt.title}
                        </p>
                        {result.recommendation === key && (
                          <span className="text-xs bg-blue-900 text-white px-2 py-0.5 rounded-full">
                            Recommended
                          </span>
                        )}
                        {opt.safe && (
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                            Safe
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-600 mb-2">
                        {opt.definition}
                      </p>
                      <p className="text-xs text-gray-500">
                        <span className="font-medium">Use when:</span>{' '}
                        {opt.use_when}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        <span className="font-medium">Risk:</span>{' '}
                        {opt.risk}
                      </p>
                    </div>
                  )
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}