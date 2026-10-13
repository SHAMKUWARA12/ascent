import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getAdvisor, getChoiceFilingPart1, getChoiceFilingPart2, getAllNits } from '../services/api'

const ROUND_OPTIONS = [
  { value: '1', label: 'Round 1 (R1) — Regular', part: 1 },
  { value: '2', label: 'Round 2 (R2) — Regular', part: 1 },
  { value: '3', label: 'Round 3 (R3) — Regular', part: 1 },
  { value: '4', label: 'Special Round 1 (SR1)', part: 2 },
  { value: '5', label: 'Special Round 2 (SR2)', part: 2 },
  { value: '6', label: 'National Spot Round (NR1)', part: 3 },
]

export default function Advisor() {
  const { token } = useAuth()
  const navigate  = useNavigate()

  // Step state
  const [step, setStep] = useState(1)
  // step 1 = select round
  // step 2 = select current allocation (shows pref no.)
  // step 3 = select target + get recommendation

  // Round
  const [selectedRound,   setSelectedRound]   = useState('')
  const [partNumber,      setPartNumber]       = useState(null)

  // Preference list for selected round
  const [prefList,        setPrefList]         = useState([])
  const [prefListLoading, setPrefListLoading]  = useState(false)

  // Current allocation
  const [currentNIT,    setCurrentNIT]    = useState('')
  const [currentBranch, setCurrentBranch] = useState('')
  const [currentPrefNo, setCurrentPrefNo] = useState(null)

  // Target
  const [targetNIT,    setTargetNIT]    = useState('')
  const [targetBranch, setTargetBranch] = useState('Any branch')

  // Available target options (filtered from pref list)
  const [targetNITOptions,    setTargetNITOptions]    = useState([])
  const [targetBranchOptions, setTargetBranchOptions] = useState([])

  // Result
  const [result,    setResult]    = useState(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState('')
  const [showList,  setShowList]  = useState(false)

  // NIT + branch master list for dropdowns
  const [nitList,       setNitList]       = useState([])
  const [branchOptions, setBranchOptions] = useState([])

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

  // ── Step 1: Round selected ─────────────────────────────
  const handleRoundSelect = async (roundValue) => {
    setSelectedRound(roundValue)
    setResult(null)
    setCurrentNIT('')
    setCurrentBranch('')
    setCurrentPrefNo(null)
    setTargetNIT('')
    setTargetBranch('Any branch')
    setError('')

    const roundObj = ROUND_OPTIONS.find(r => r.value === roundValue)
    if (!roundObj) return

    const part = roundObj.part
    setPartNumber(part)

    // Fetch the preference list for this part
    setPrefListLoading(true)
    try {
      let res
      if (part === 1) {
        res = await getChoiceFilingPart1(token)
      } else {
        // Part 2 and 3 use same list for now
        // Future: differentiate logic per part
        res = await getChoiceFilingPart1(token)
      }
      setPrefList(res.data.preferences || [])
      setStep(2)
    } catch (err) {
      setError('Could not load preference list. Please complete your profile first.')
    } finally {
      setPrefListLoading(false)
    }
  }

  // ── Step 2: Current NIT selected ──────────────────────
  const handleCurrentNITChange = (nit) => {
    setCurrentNIT(nit)
    setCurrentBranch('')
    setCurrentPrefNo(null)
    setTargetNIT('')
    setTargetBranch('Any branch')
    setResult(null)
  }

  // ── Step 2: Current Branch selected ───────────────────
  const handleCurrentBranchChange = (branch) => {
    setCurrentBranch(branch)
    setResult(null)

    // Find preference number in the list
    const match = prefList.find(
      p =>
        p.nit_name.toLowerCase() === currentNIT.toLowerCase() &&
        p.branch.toUpperCase() === branch.toUpperCase()
    )

    if (match) {
      setCurrentPrefNo(match.preference_no)

      // Target options = only entries ABOVE this preference number
      // i.e. better options the student hasn't reached yet
      const betterOptions = prefList.filter(
        p => p.preference_no < match.preference_no
      )

      // Unique NIT names from better options
      const nitSet = [...new Set(betterOptions.map(p => p.nit_name))].sort()
      setTargetNITOptions(nitSet)

      // Reset targets
      setTargetNIT('')
      setTargetBranch('Any branch')
      setStep(3)
    } else {
      // Current allocation not found in list — allow manual entry
      setCurrentPrefNo(null)
      setTargetNITOptions(nitList)
      setStep(3)
    }
  }

  // ── Step 3: Target NIT selected ───────────────────────
  const handleTargetNITChange = (nit) => {
    setTargetNIT(nit)
    setTargetBranch('Any branch')

    // Target branch options = branches for this NIT in the
    // better options list, excluding current branch if same NIT
    const betterOptions = prefList.filter(
      p => currentPrefNo
        ? p.preference_no < currentPrefNo
        : true
    )
    const branchesForNIT = betterOptions
      .filter(p => p.nit_name.toLowerCase() === nit.toLowerCase())
      .map(p => p.branch)

    if (branchesForNIT.length > 0) {
      // Only show branches from preference list for this NIT
      const filtered = branchOptions.filter(
        b =>
          branchesForNIT.includes(b.code) &&
          // Exclude same NIT + same branch as current
          !(nit.toLowerCase() === currentNIT.toLowerCase() &&
            b.code.toUpperCase() === currentBranch.toUpperCase())
      )
      setTargetBranchOptions(filtered)
    } else {
      // Fallback: all branches except current if same NIT
      const filtered = branchOptions.filter(
        b => !(
          nit.toLowerCase() === currentNIT.toLowerCase() &&
          b.code.toUpperCase() === currentBranch.toUpperCase()
        )
      )
      setTargetBranchOptions(filtered)
    }
  }

  // ── Get recommendation ─────────────────────────────────
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

  const roundLabel = ROUND_OPTIONS.find(r => r.value === selectedRound)?.label || ''
  const partLabel  = partNumber === 1
    ? 'Part 1 — Regular Rounds'
    : partNumber === 2
    ? 'Part 2 — Special Rounds'
    : partNumber === 3
    ? 'Part 3 — National Spot Round'
    : ''

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
          Enter your current allocation and target to get
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
          </p>
        </div>

        {/* Step 1: Round selector */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
          <p className="text-sm font-semibold text-gray-700 mb-1">
            Step 1 — Which round did you receive this allotment in?
          </p>
          <p className="text-xs text-gray-400 mb-3">
            Rounds 1-3 use your Part 1 list.
            Special Rounds 1-2 use your Part 2 list.
            National Spot Round uses your Part 3 list.
          </p>
          <select
            value={selectedRound}
            onChange={e => handleRoundSelect(e.target.value)}
            className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm bg-white focus:outline-none focus:border-blue-400"
          >
            <option value="">Select the round</option>
            {ROUND_OPTIONS.map(r => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>

          {prefListLoading && (
            <p className="text-xs text-gray-400 mt-2">
              Loading your preference list...
            </p>
          )}

          {selectedRound && partLabel && !prefListLoading && (
            <div className="mt-3 bg-blue-50 rounded-xl px-4 py-2.5">
              <p className="text-xs text-blue-700 font-medium">
                ✓ Using your {partLabel} preference list
                ({prefList.length} options)
              </p>
            </div>
          )}
        </div>

        {/* Step 2: Current allocation */}
        {step >= 2 && (
          <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
            <p className="text-sm font-semibold text-gray-700 mb-3">
              Step 2 — Your current allotment
            </p>
            <div className="flex gap-3 mb-3">
              <select
                value={currentNIT}
                onChange={e => handleCurrentNITChange(e.target.value)}
                className="flex-1 border border-gray-200 rounded-xl px-3 py-2.5 text-sm bg-white focus:outline-none focus:border-blue-400"
              >
                <option value="">Select NIT</option>
                {nitList.map(n => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
              <select
                value={currentBranch}
                onChange={e => handleCurrentBranchChange(e.target.value)}
                disabled={!currentNIT}
                className="flex-1 border border-gray-200 rounded-xl px-3 py-2.5 text-sm bg-white focus:outline-none focus:border-blue-400 disabled:opacity-40"
              >
                <option value="">Select Branch</option>
                {branchOptions.map(b => (
                  <option key={b.code} value={b.code}>
                    {b.code}
                  </option>
                ))}
              </select>
            </div>

            {/* Show preference number once current allocation found */}
            {currentNIT && currentBranch && (
              <div className={`rounded-xl px-4 py-3 ${
                currentPrefNo
                  ? 'bg-green-50 border border-green-200'
                  : 'bg-amber-50 border border-amber-200'
              }`}>
                {currentPrefNo ? (
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-green-600 font-medium">
                        ✓ Found in your {partLabel} list
                      </p>
                      <p className="text-sm text-green-800 mt-0.5">
                        {currentNIT} — {currentBranch}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-green-600">
                        Preference No.
                      </p>
                      <p className="text-2xl font-black text-green-700">
                        #{currentPrefNo}
                      </p>
                      <p className="text-xs text-green-600">
                        of {prefList.length}
                      </p>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-amber-700">
                    ⚠️ This combination was not found in your
                    generated list for this round. You can still
                    proceed — the advisor will work with available data.
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Step 3: Target + recommendation */}
        {step >= 3 && currentBranch && (
          <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
            <p className="text-sm font-semibold text-gray-700 mb-1">
              Step 3 — Where do you want to upgrade?
            </p>
            {currentPrefNo && (
              <p className="text-xs text-gray-400 mb-3">
                Only showing options ranked above preference
                #{currentPrefNo} in your {partLabel} list.
              </p>
            )}
            <div className="flex gap-3 mb-4">
              <select
                value={targetNIT}
                onChange={e => handleTargetNITChange(e.target.value)}
                className="flex-1 border border-gray-200 rounded-xl px-3 py-2.5 text-sm bg-white focus:outline-none focus:border-blue-400"
              >
                <option value="">Target NIT</option>
                {targetNITOptions.map(n => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
              <select
                value={targetBranch}
                onChange={e => setTargetBranch(e.target.value)}
                disabled={!targetNIT}
                className="flex-1 border border-gray-200 rounded-xl px-3 py-2.5 text-sm bg-white focus:outline-none focus:border-blue-400 disabled:opacity-40"
              >
                <option value="Any branch">Any branch</option>
                {targetBranchOptions.map(b => (
                  <option key={b.code} value={b.code}>
                    {b.code}
                  </option>
                ))}
              </select>
            </div>

            {error && (
              <p className="text-red-500 text-sm mb-3">{error}</p>
            )}

            <button
              onClick={handleSubmit}
              disabled={loading || !targetNIT}
              className="w-full bg-blue-900 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-800 disabled:opacity-50"
            >
              {loading ? 'Analysing...' : 'Get Recommendation'}
            </button>
          </div>
        )}

        {/* Result */}
        {result && (
          <>
            {/* Round context banner */}
            <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-2.5 mb-4">
              <p className="text-xs text-blue-700 font-medium">
                Advice for {roundLabel} · {partLabel} preference list
              </p>
            </div>

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
              <div className="grid grid-cols-3 gap-3 text-center mb-3">
                <div className="bg-white bg-opacity-60 rounded-xl p-3">
                  <p className="text-xs opacity-50 mb-1">Current</p>
                  <p className="font-semibold text-sm">
                    {currentBranch}
                  </p>
                  <p className="text-xs opacity-50">
                    {result.current_nirf_display}
                  </p>
                  {result.current_pref_no && (
                    <p className="text-xs font-bold mt-1">
                      Pref #{result.current_pref_no}
                    </p>
                  )}
                </div>
                <div className="bg-white bg-opacity-60 rounded-xl p-3">
                  <p className="text-xs opacity-50 mb-1">Target</p>
                  <p className="font-semibold text-sm">
                    {targetBranch === 'Any branch'
                      ? 'Any'
                      : targetBranch}
                  </p>
                  <p className="text-xs opacity-50">
                    {result.target_nirf_display}
                  </p>
                  {result.target_pref_no && (
                    <p className="text-xs font-bold mt-1">
                      Pref #{result.target_pref_no}
                    </p>
                  )}
                </div>
                <div className="bg-white bg-opacity-60 rounded-xl p-3">
                  <p className="text-xs opacity-50 mb-1">Probability</p>
                  <p className="font-bold text-lg">
                    {result.probability}%
                  </p>
                </div>
              </div>
            </div>

            {/* Better preferences button */}
            {result.better_preferences?.length > 0 && (
              <button
                onClick={() => setShowList(!showList)}
                className="w-full bg-white border border-blue-200 text-blue-800 py-3 rounded-xl font-semibold text-sm hover:bg-blue-50 mb-4"
              >
                {showList
                  ? 'Hide list'
                  : `View ${result.better_preferences.length} options ranked above your current seat`
                }
              </button>
            )}

            {/* Better preferences table */}
            {showList && result.better_preferences?.length > 0 && (
              <div className="bg-white rounded-2xl border border-gray-100 p-4 mb-4">
                <p className="text-sm font-semibold text-gray-800 mb-1">
                  Options ranked above preference #{result.current_pref_no}
                </p>
                <p className="text-xs text-gray-400 mb-3">
                  From your {partLabel} list · {roundLabel}.
                  CCMT will try to allot these first before
                  reaching your current seat.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-100">
                        <th className="text-left py-2 text-gray-400 font-medium">#</th>
                        <th className="text-left py-2 text-gray-400 font-medium">NIT</th>
                        <th className="text-left py-2 text-gray-400 font-medium">Branch</th>
                        <th className="text-left py-2 text-gray-400 font-medium">Prob</th>
                        <th className="text-left py-2 text-gray-400 font-medium">Bucket</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.better_preferences.map((p, i) => (
                        <tr key={i} className="border-b border-gray-50">
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
                {Object.entries(result.all_options).map(([key, opt]) => (
                  <div
                    key={key}
                    className={`rounded-xl border p-4 mb-3 ${
                      result.recommendation === key
                        ? 'border-blue-300 bg-blue-50'
                        : 'border-gray-100 bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
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
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}