import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  getRecommendations,
  getChoiceFilingPart1,
  getChoiceFilingPart2
} from '../services/api'

// ---------- NIT Card ----------
function NITCard({ nit, rank }) {
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState(false)

  const bucketColor = {
    Safe: 'bg-green-50 border-green-200',
    Target: 'bg-amber-50 border-amber-200',
    Ambitious: 'bg-red-50 border-red-200'
  }

  const probColor = {
    Safe: 'text-green-700',
    Target: 'text-amber-700',
    Ambitious: 'text-red-600'
  }

  const bucketBadge = {
    Safe: 'bg-green-100 text-green-700',
    Target: 'bg-amber-100 text-amber-700',
    Ambitious: 'bg-red-100 text-red-600'
  }

  return (
    <div
      className={`border rounded-2xl p-4 mb-3 ${bucketColor[nit.bucket]} cursor-pointer hover:shadow-md transition-shadow`}
      onClick={() => navigate(`/nit/${nit.nit_code}`)}
    >

      {/* Top row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="text-xs font-bold text-gray-400 w-5 mt-1">
            #{rank}
          </span>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold text-gray-900 text-sm">
                {nit.nit_name}
              </h3>
              <p className="text-xs text-blue-600 font-medium mt-0.5">
                {nit.branch} — {nit.branch_full}
              </p>
              {nit.home_state && (
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">
                  🏠 Home State
                </span>
              )}
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${bucketBadge[nit.bucket]}`}>
                {nit.bucket}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              {nit.location} · NIRF #{nit.nirf_rank}
            </p>
          </div>
        </div>

        <div className="text-right flex-shrink-0">
          <p className={`text-lg font-bold ${probColor[nit.bucket]}`}>
            {nit.admission_probability}%
          </p>
          <p className="text-xs text-gray-400">probability</p>
        </div>
      </div>

      {/* Score info */}
      <div className="flex gap-4 mt-3 px-8">
        <div>
          <p className="text-xs text-gray-400">Predicted Closing</p>
          <p className="text-sm font-semibold text-gray-800">
            {nit.predicted_closing_score}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-400">Your Score</p>
          <p className="text-sm font-semibold text-gray-800">
            {nit.your_score}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-400">Sentiment</p>
          <p className="text-sm font-semibold text-gray-800">
            {nit.sentiment_score}/10
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-400">Total Score</p>
          <p className="text-sm font-semibold text-gray-800">
            {nit.total_score}/100
          </p>
        </div>
      </div>

      {/* Expand button */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-blue-600 hover:underline mt-3 px-8"
      >
        {expanded ? 'Hide breakdown ▲' : 'View score breakdown ▼'}
      </button>

      {/* Score breakdown */}
      {expanded && (
        <div className="mt-3 px-8 grid grid-cols-3 gap-2">
          {Object.entries(nit.score_breakdown).map(([key, val]) => (
            <div key={key} className="bg-white rounded-xl p-2 text-center">
              <p className="text-xs text-gray-400 capitalize">
                {key.replace('_', ' ')}
              </p>
              <p className="text-sm font-semibold text-gray-800">{val}</p>
            </div>
          ))}
        </div>
      )}

    </div>
  )
}

// ── Shared list renderer ──────────────────────────────────

function renderList(list) {
  return (
    <>
      {list.important_note && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 mb-3 text-xs text-amber-800">
          ⚠️ {list.important_note}
        </div>
      )}

      <div className="flex flex-col gap-1 mb-3">
        {(list.preferences || []).map(p => (
          <div
            key={p.preference_no}
            className="flex items-center gap-3 py-2 px-3 rounded-xl hover:bg-gray-50"
          >
            <span className="text-xs font-bold text-gray-400 w-6 flex-shrink-0">
              {p.preference_no}
            </span>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-medium text-gray-800">
                {p.nit_name}
              </span>
              <span className="text-xs text-gray-400 ml-2">
                {p.branch} · {p.category}
              </span>
            </div>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0 ${
              p.bucket === 'Safe'
                ? 'bg-green-100 text-green-700'
                : p.bucket === 'Target'
                ? 'bg-amber-100 text-amber-700'
                : 'bg-red-100 text-red-600'
            }`}>
              {p.probability}%
            </span>
          </div>
        ))}
      </div>

      {list.why_this_order && (
        <p className="text-xs text-gray-400 leading-relaxed">
          {list.why_this_order}
        </p>
      )}
    </>
  )
}


// ---------- Choice Filing List ----------
function ChoiceFilingList({ token }) {
  const [activePart, setActivePart] = useState('part1')
  const [list, setList] = useState(null)
  const [loading, setLoading] = useState(false)
  const [currentAllocation, setCurrentAllocation] = useState('')
  const [gotSeat, setGotSeat] = useState(null)
  const [frozenAt, setFrozenAt] = useState(null)

  // ── API calls ────────────────────────────────────────────

  const fetchPart1 = async () => {
    setLoading(true)
    setList(null)
    try {
      const res = await getChoiceFilingPart1(token)
      setList(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const fetchPart2 = async () => {
    setLoading(true)
    setList(null)
    try {
      const res = await getChoiceFilingPart2(
        token,
        currentAllocation || 'No seat'
      )
      setList(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const copyList = () => {
    if (!list) return
    const text = (list.preferences || [])
      .map(p =>
        `${p.preference_no}. ${p.nit_name} | ${p.branch} | ${p.category} (${p.probability}%)`
      )
      .join('\n')
    navigator.clipboard.writeText(text)
    alert('Choice filing list copied!')
  }

  // ── Tab switching ────────────────────────────────────────

  const switchPart = (part) => {
    if (frozenAt === 'part2' && part === 'part3') return
    setActivePart(part)
    setList(null)
    setCurrentAllocation('')
    setGotSeat(null)
  }

  // ── Tab disabled check ───────────────────────────────────

  const isTabDisabled = (part) => {
    if (frozenAt === 'part2' && part === 'part3') return true
    return false
  }

  // ── NIT + Branch dropdowns (reused in Part 2 and Part 3) ─

  const NITOptions = [
    'NIT Silchar', 'NIT Rourkela', 'NIT Trichy',
    'NIT Warangal', 'NIT Calicut'
  ]

  const BranchOptions = [
    'CSE', 'AI', 'DS', 'IT',
    'ML', 'CY', 'SE', 'DE', 'IS', 'HCI'
  ]

  const AllocationDropdowns = () => (
    <div className="flex gap-2">
      <select
        value={currentAllocation.split('—')[0]?.trim() || ''}
        onChange={e => {
          const nit = e.target.value
          const branch = currentAllocation.split('—')[1]?.trim() || ''
          setCurrentAllocation(branch ? `${nit} — ${branch}` : nit)
        }}
        className="flex-1 border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-blue-400 bg-white"
      >
        <option value="">Select NIT</option>
        {NITOptions.map(n => (
          <option key={n} value={n}>{n}</option>
        ))}
      </select>
      <select
        value={currentAllocation.split('—')[1]?.trim() || ''}
        onChange={e => {
          const nit = currentAllocation.split('—')[0]?.trim() || ''
          setCurrentAllocation(`${nit} — ${e.target.value}`)
        }}
        className="flex-1 border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-blue-400 bg-white"
      >
        <option value="">Select Branch</option>
        {BranchOptions.map(b => (
          <option key={b} value={b}>{b}</option>
        ))}
      </select>
    </div>
  )

  // ── Congrats message ─────────────────────────────────────

  const CongratsMessage = ({ frozenPart }) => (
    <div className="bg-green-50 border border-green-200 rounded-xl p-5 text-center mt-2">
      <p className="text-3xl mb-2">🎉</p>
      <p className="font-semibold text-green-800 mb-2">
        Congratulations!
      </p>
      <p className="text-sm text-green-700 leading-relaxed">
        You froze your seat in{' '}
        {frozenPart === 'part2'
          ? 'Special Rounds'
          : 'National Round'}.
        Your admission is confirmed.
        {frozenPart === 'part2'
          ? ' National Round is now locked for you.'
          : ''}
      </p>
      <p className="text-xs text-green-600 mt-3">
        Report to your allotted institute as per
        their admission schedule.
      </p>
    </div>
  )

  // ── Render list ──────────────────────────────────────────

  const renderList = (data) => (
    <>
      {data.important_note && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 mb-3 text-xs text-amber-800">
          ⚠️ {data.important_note}
        </div>
      )}
      <div className="flex flex-col gap-1 mb-3">
        {(data.preferences || []).map(p => (
          <div
            key={p.preference_no}
            className="flex items-center gap-3 py-2 px-3 rounded-xl hover:bg-gray-50"
          >
            <span className="text-xs font-bold text-gray-400 w-6 flex-shrink-0">
              {p.preference_no}
            </span>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-medium text-gray-800">
                {p.nit_name}
              </span>
              <span className="text-xs text-gray-400 ml-2">
                {p.branch} · {p.category}
              </span>
            </div>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0 ${
              p.bucket === 'Safe'
                ? 'bg-green-100 text-green-700'
                : p.bucket === 'Target'
                ? 'bg-amber-100 text-amber-700'
                : 'bg-red-100 text-red-600'
            }`}>
              {p.probability}%
            </span>
          </div>
        ))}
      </div>
      {data.why_this_order && (
        <p className="text-xs text-gray-400 leading-relaxed">
          {data.why_this_order}
        </p>
      )}
    </>
  )

  // ════════════════════════════════════════════════════════
  // RENDER
  // ════════════════════════════════════════════════════════

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5">

      {/* ── Part tabs ── */}
      <div className="flex gap-2 mb-5">
        {[
          { id: 'part1', label: 'Part 1', sub: 'Regular Rounds R1 R2 R3' },
          { id: 'part2', label: 'Part 2', sub: 'Special Rounds SR1 SR2' },
          { id: 'part3', label: 'Part 3', sub: 'National Round NR1' },
        ].map(p => {
          const disabled = isTabDisabled(p.id)
          return (
            <button
              key={p.id}
              onClick={() => switchPart(p.id)}
              disabled={disabled}
              className={`flex-1 py-2.5 rounded-xl border text-left px-3 transition-all ${
                disabled
                  ? 'bg-gray-100 border-gray-200 cursor-not-allowed opacity-50'
                  : activePart === p.id
                  ? 'bg-blue-900 border-blue-900'
                  : 'bg-white border-gray-200 hover:border-blue-300'
              }`}
            >
              <p className={`text-sm font-semibold ${
                disabled
                  ? 'text-gray-400'
                  : activePart === p.id ? 'text-white' : 'text-gray-800'
              }`}>
                {p.label} {disabled ? '🔒' : ''}
              </p>
              <p className={`text-xs mt-0.5 ${
                disabled
                  ? 'text-gray-400'
                  : activePart === p.id ? 'text-blue-200' : 'text-gray-400'
              }`}>
                {disabled ? 'Locked — seat frozen' : p.sub}
              </p>
            </button>
          )
        })}
      </div>

      {/* ════════════════════════════════════════════════════
          PART 1 — Regular Rounds
          Simple: just generate the list.
          No frozen checkbox here.
          Student has not started counselling yet.
      ════════════════════════════════════════════════════ */}
      {activePart === 'part1' && (
        <>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="font-semibold text-gray-900 text-sm">
                Part 1 Preference List
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Submit ONCE before Round 1.
                Valid for R1, R2, and R3.
              </p>
            </div>
            <div className="flex gap-2">
              {!list && (
                <button
                  onClick={fetchPart1}
                  disabled={loading}
                  className="bg-blue-900 text-white text-xs px-3 py-2 rounded-xl hover:bg-blue-800 disabled:opacity-50"
                >
                  {loading ? 'Generating...' : 'Generate List'}
                </button>
              )}
              {list && (
                <button
                  onClick={copyList}
                  className="bg-green-700 text-white text-xs px-3 py-2 rounded-xl hover:bg-green-600"
                >
                  Copy List
                </button>
              )}
            </div>
          </div>
          {list && renderList(list)}
        </>
      )}

      {/* ════════════════════════════════════════════════════
          PART 2 — Special Rounds
          Ask: Got seat in Regular Rounds? Yes / No / Frozen
      ════════════════════════════════════════════════════ */}
      {activePart === 'part2' && (
        <>
          <h2 className="font-semibold text-gray-900 text-sm mb-1">
            Part 2 Preference List
          </h2>
          <p className="text-xs text-gray-400 mb-3">
            Submit a NEW list before Special Round 1.
            Different from Part 1.
          </p>

          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 mb-4 text-xs text-amber-800">
            <p className="font-medium mb-1">⚠️ Note on accuracy</p>
            <p>
              Part 2 list uses the same scoring engine as Part 1
              with dummy data. In Phase 2, real CCMT round results
              and remaining seat matrix will generate a more
              accurate Part 2 list.
            </p>
          </div>

          {/* Seat status question */}
          {!frozenAt && (
            <div className="mb-4">
              <label className="text-xs font-medium text-gray-700 mb-2 block">
                What is your situation after Regular Rounds?
              </label>
              <div className="flex flex-col gap-2">
                {[
                  {
                    id: 'Yes',
                    label: 'I got a seat and want to upgrade',
                    sub: 'Allotted in R1, R2, or R3 — trying for better in Special Rounds'
                  },
                  {
                    id: 'No',
                    label: 'I did not get any seat',
                    sub: 'Registering fresh for Special Rounds'
                  },
                  {
                    id: 'Frozen',
                    label: 'I already froze my seat in Regular Rounds',
                    sub: 'Satisfied with current seat — no further action needed'
                  }
                ].map(opt => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => {
                      setGotSeat(opt.id)
                      setCurrentAllocation('')
                      setList(null)
                      if (opt.id === 'Frozen') {
                        setFrozenAt('part2')
                      }
                    }}
                    className={`w-full py-3 px-4 rounded-xl border text-left transition-all ${
                      gotSeat === opt.id
                        ? 'bg-blue-900 border-blue-900'
                        : 'bg-white border-gray-200 hover:border-blue-300'
                    }`}
                  >
                    <p className={`text-sm font-medium ${
                      gotSeat === opt.id ? 'text-white' : 'text-gray-800'
                    }`}>
                      {opt.label}
                    </p>
                    <p className={`text-xs mt-0.5 ${
                      gotSeat === opt.id ? 'text-blue-200' : 'text-gray-400'
                    }`}>
                      {opt.sub}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Frozen in Part 2 */}
          {frozenAt === 'part2' && (
            <>
              <CongratsMessage frozenPart="part2" />
              <button
                onClick={() => {
                  setFrozenAt(null)
                  setGotSeat(null)
                }}
                className="w-full mt-3 text-xs text-gray-400 hover:text-gray-600 py-2"
              >
                Undo — I have not frozen yet
              </button>
            </>
          )}

          {/* No seat */}
          {gotSeat === 'No' && !frozenAt && !list && (
            <div className="flex flex-col gap-3">
              <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-xs text-red-700">
                <p className="font-medium mb-1">
                  No seat from Regular Rounds
                </p>
                <p>
                  You can still participate in Special Rounds.
                  The system will generate a full list based on
                  your profile and GATE score.
                </p>
              </div>
              <button
                onClick={() => {
                  setCurrentAllocation('No seat')
                  fetchPart2()
                }}
                disabled={loading}
                className="bg-blue-900 text-white text-sm px-4 py-2.5 rounded-xl hover:bg-blue-800 disabled:opacity-50 font-medium"
              >
                {loading ? 'Generating...' : 'Generate Part 2 List'}
              </button>
            </div>
          )}

          {/* Got seat — show dropdowns */}
          {gotSeat === 'Yes' && !frozenAt && !list && (
            <div className="flex flex-col gap-3">
              <div>
                <label className="text-xs font-medium text-gray-700 mb-1 block">
                  Your current allocation from Regular Rounds
                </label>
                <AllocationDropdowns />
                <p className="text-xs text-gray-400 mt-1">
                  Select the NIT and branch allotted in Round 3
                </p>
              </div>
              <button
                onClick={fetchPart2}
                disabled={
                  loading ||
                  !currentAllocation.includes('—') ||
                  !currentAllocation.split('—')[1]?.trim()
                }
                className="bg-blue-900 text-white text-sm px-4 py-2.5 rounded-xl hover:bg-blue-800 disabled:opacity-50 font-medium"
              >
                {loading ? 'Generating...' : 'Generate Part 2 List'}
              </button>
            </div>
          )}

          {/* Generated list */}
          {list && !frozenAt && (
            <>
              <div className="flex items-center justify-between mb-3">
                <div className="bg-gray-50 rounded-xl px-3 py-2 text-xs text-gray-600">
                  {currentAllocation === 'No seat'
                    ? 'Fresh registration for Special Rounds'
                    : <>Current: <strong>{currentAllocation}</strong></>
                  }
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setList(null)
                      setCurrentAllocation('')
                      setGotSeat(null)
                    }}
                    className="text-xs text-gray-400 hover:text-gray-600 px-2"
                  >
                    Reset
                  </button>
                  <button
                    onClick={copyList}
                    className="bg-green-700 text-white text-xs px-3 py-2 rounded-xl hover:bg-green-600"
                  >
                    Copy List
                  </button>
                </div>
              </div>
              {renderList(list)}
            </>
          )}
        </>
      )}

      {/* ════════════════════════════════════════════════════
          PART 3 — National Round
          Ask: Got seat? / No seat? / Already frozen?
      ════════════════════════════════════════════════════ */}
      {activePart === 'part3' && (
        <>
          <h2 className="font-semibold text-gray-900 text-sm mb-1">
            Part 3 Preference List
          </h2>
          <p className="text-xs text-gray-400 mb-3">
            Final round of CCMT counselling.
            Last chance to get or upgrade your seat.
          </p>

          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 mb-4 text-xs text-amber-800">
            <p className="font-medium mb-1">⚠️ Note on accuracy</p>
            <p>
              Part 3 list uses the same scoring engine as Part 1
              with dummy data. In Phase 2, real-time data will
              generate a more accurate National Round list.
            </p>
          </div>

          {/* Seat status question */}
          {!frozenAt && (
            <div className="mb-4">
              <label className="text-xs font-medium text-gray-700 mb-2 block">
                What is your current situation?
              </label>
              <div className="flex flex-col gap-2">
                {[
                  {
                    id: 'has_seat',
                    label: 'I have a seat and want to upgrade',
                    sub: 'Got a seat in Part 1 or Part 2 — trying for better in National Round'
                  },
                  {
                    id: 'no_seat',
                    label: 'I do not have a seat yet',
                    sub: 'Registering fresh for National Round'
                  },
                  {
                    id: 'frozen',
                    label: 'I already froze my seat',
                    sub: 'Confirmed seat from Part 1 or Part 2 — no further action needed'
                  }
                ].map(opt => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => {
                      setGotSeat(opt.id)
                      setCurrentAllocation('')
                      setList(null)
                      if (opt.id === 'frozen') {
                        setFrozenAt('part3')
                      }
                    }}
                    className={`w-full py-3 px-4 rounded-xl border text-left transition-all ${
                      gotSeat === opt.id
                        ? 'bg-blue-900 border-blue-900'
                        : 'bg-white border-gray-200 hover:border-blue-300'
                    }`}
                  >
                    <p className={`text-sm font-medium ${
                      gotSeat === opt.id ? 'text-white' : 'text-gray-800'
                    }`}>
                      {opt.label}
                    </p>
                    <p className={`text-xs mt-0.5 ${
                      gotSeat === opt.id ? 'text-blue-200' : 'text-gray-400'
                    }`}>
                      {opt.sub}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Frozen in Part 3 */}
          {frozenAt === 'part3' && (
            <>
              <CongratsMessage frozenPart="part3" />
              <button
                onClick={() => {
                  setFrozenAt(null)
                  setGotSeat(null)
                }}
                className="w-full mt-3 text-xs text-gray-400 hover:text-gray-600 py-2"
              >
                Undo — I have not frozen yet
              </button>
            </>
          )}

          {/* No seat */}
          {gotSeat === 'no_seat' && !frozenAt && !list && (
            <div className="flex flex-col gap-3">
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-800">
                <p className="font-medium mb-1">Fresh registration</p>
                <p>
                  You are registering fresh for National Round.
                  The system will generate a full list based on
                  your profile and GATE score.
                </p>
              </div>
              <button
                onClick={() => {
                  setCurrentAllocation('No seat')
                  fetchPart2()
                }}
                disabled={loading}
                className="bg-blue-900 text-white text-sm px-4 py-2.5 rounded-xl hover:bg-blue-800 disabled:opacity-50 font-medium"
              >
                {loading ? 'Generating...' : 'Generate Part 3 List'}
              </button>
            </div>
          )}

          {/* Has seat */}
          {gotSeat === 'has_seat' && !frozenAt && !list && (
            <div className="flex flex-col gap-3">
              <div>
                <label className="text-xs font-medium text-gray-700 mb-1 block">
                  Your current allocation
                </label>
                <AllocationDropdowns />
                <p className="text-xs text-gray-400 mt-1">
                  Select your current NIT and branch
                </p>
              </div>
              <button
                onClick={fetchPart2}
                disabled={
                  loading ||
                  !currentAllocation.includes('—') ||
                  !currentAllocation.split('—')[1]?.trim()
                }
                className="bg-blue-900 text-white text-sm px-4 py-2.5 rounded-xl hover:bg-blue-800 disabled:opacity-50 font-medium"
              >
                {loading ? 'Generating...' : 'Generate Part 3 List'}
              </button>
            </div>
          )}

          {/* Generated list */}
          {list && !frozenAt && (
            <>
              <div className="flex items-center justify-between mb-3">
                <div className="bg-gray-50 rounded-xl px-3 py-2 text-xs text-gray-600">
                  {currentAllocation === 'No seat'
                    ? 'Fresh registration for National Round'
                    : <>Current: <strong>{currentAllocation}</strong></>
                  }
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setList(null)
                      setCurrentAllocation('')
                      setGotSeat(null)
                    }}
                    className="text-xs text-gray-400 hover:text-gray-600 px-2"
                  >
                    Reset
                  </button>
                  <button
                    onClick={copyList}
                    className="bg-green-700 text-white text-xs px-3 py-2 rounded-xl hover:bg-green-600"
                  >
                    Copy List
                  </button>
                </div>
              </div>
              {renderList(list)}
            </>
          )}
        </>
      )}

    </div>
  )
}

// ---------- Main Dashboard ----------
export default function Dashboard() {
  const { token, student } = useAuth()
  const navigate = useNavigate()

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('recommendations')

  useEffect(() => {
    fetchRecommendations()
  }, [])

  const fetchRecommendations = async () => {
    setLoading(true)
    try {
      const res = await getRecommendations(token)
      setData(res.data)
    } catch (err) {
      setError(
        err.response?.data?.detail || 'Failed to load recommendations.'
      )
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-900 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-400 text-sm">
            Analysing NITs for your profile...
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-4">{error}</p>
          <button
            onClick={() => navigate('/profile')}
            className="bg-blue-900 text-white px-6 py-2 rounded-xl text-sm"
          >
            Complete Profile First
          </button>
        </div>
      </div>
    )
  }

  const allNITs = [
    ...(data?.safe || []),
    ...(data?.target || []),
    ...(data?.ambitious || [])
  ]

  return (
    <div className="min-h-screen bg-gray-50">

      {/* Header */}
      <div className="bg-blue-900 text-white px-6 py-6">
        <h1 className="text-xl font-semibold mb-1">
          Welcome, {data?.student?.name?.split(' ')[0]}!
        </h1>
        <p className="text-blue-200 text-sm">
          GATE Score: {data?.student?.gate_score} ·
          Category: {data?.student?.category} ·
          Domicile: {data?.student?.domicile}
        </p>
        <div className="flex gap-4 mt-4 text-sm">
          <div className="bg-blue-800 rounded-xl px-4 py-2 text-center">
            <p className="text-blue-300 text-xs">Total Eligible</p>
            <p className="font-bold text-lg">{data?.total_eligible}</p>
          </div>
          <div className="bg-blue-800 rounded-xl px-4 py-2 text-center">
            <p className="text-blue-300 text-xs">Safe</p>
            <p className="font-bold text-lg text-green-300">
              {data?.safe?.length}
            </p>
          </div>
          <div className="bg-blue-800 rounded-xl px-4 py-2 text-center">
            <p className="text-blue-300 text-xs">Target</p>
            <p className="font-bold text-lg text-amber-300">
              {data?.target?.length}
            </p>
          </div>
          <div className="bg-blue-800 rounded-xl px-4 py-2 text-center">
            <p className="text-blue-300 text-xs">Ambitious</p>
            <p className="font-bold text-lg text-red-300">
              {data?.ambitious?.length}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-100 px-6">
        <div className="flex gap-6">
          {[
            { id: 'recommendations', label: 'Recommendations' },
            { id: 'choice-filing', label: 'Choice Filing' },
            { id: 'advisor', label: 'Lock/Float/Slide' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-3 text-sm font-medium border-b-2 transition-all ${
                activeTab === tab.id
                  ? 'border-blue-900 text-blue-900'
                  : 'border-transparent text-gray-400 hover:text-gray-600'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-3xl mx-auto px-4 py-6">

        {/* Recommendations Tab */}
        {activeTab === 'recommendations' && (
          <div>
            {data?.safe?.length > 0 && (
              <div className="mb-6">
                <h2 className="text-sm font-semibold text-green-700 uppercase tracking-widest mb-3">
                  🟢 Safe Choices
                </h2>
                {data.safe.map((nit, i) => (
                  <NITCard key={nit.nit_code} nit={nit} rank={i + 1} />
                ))}
              </div>
            )}

            {data?.target?.length > 0 && (
              <div className="mb-6">
                <h2 className="text-sm font-semibold text-amber-700 uppercase tracking-widest mb-3">
                  🟡 Target Choices
                </h2>
                {data.target.map((nit, i) => (
                  <NITCard
                    key={nit.nit_code}
                    nit={nit}
                    rank={data.safe.length + i + 1}
                  />
                ))}
              </div>
            )}

            {data?.ambitious?.length > 0 && (
              <div className="mb-6">
                <h2 className="text-sm font-semibold text-red-600 uppercase tracking-widest mb-3">
                  🔴 Ambitious Choices
                </h2>
                {data.ambitious.map((nit, i) => (
                  <NITCard
                    key={nit.nit_code}
                    nit={nit}
                    rank={data.safe.length + data.target.length + i + 1}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Choice Filing Tab */}
        {activeTab === 'choice-filing' && (
          <ChoiceFilingList token={token} />
        )}

        {/* Advisor Tab */}
        {activeTab === 'advisor' && (
          <div className="bg-white rounded-2xl border border-gray-100 p-6 text-center">
            <h2 className="font-semibold text-gray-800 mb-2">
              Lock / Float / Slide Advisor
            </h2>
            <p className="text-gray-400 text-sm mb-4">
              Got a round result? Get data-driven advice on
              what to do next.
            </p>
            <button
              onClick={() => navigate('/advisor')}
              className="bg-blue-900 text-white px-6 py-2.5 rounded-xl text-sm font-medium hover:bg-blue-800"
            >
              Open Advisor
            </button>
          </div>
        )}

      </div>
    </div>
  )
}