import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  saveGATEDetails,
  savePersonalDetails,
  saveBranchPreferences,
  saveLocationPreferences,
  saveConstraints
} from '../services/api'

const STEPS = [
  'GATE Details',
  'Personal Details',
  'Branch Preferences',
  'Location',
  'Constraints'
]

const CATEGORIES = ['UR', 'OBC', 'SC', 'ST', 'EWS']
const BRANCHES = ['CSE', 'AI', 'DS', 'IT', 'ECE', 'EE']
const REGIONS = ['East India', 'West India', 'North India', 'South India', 'Any']

export default function Profile() {
  const { token } = useAuth()
  const navigate = useNavigate()

  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [homeNIT, setHomeNIT] = useState('')

  // Form states
  const [gate, setGate] = useState({
    gate_score: '',
    gate_year: 2026,
    gate_air: '',
    category: 'OBC'
  })

  const [personal, setPersonal] = useState({
    gender: 'Male',
    pwd_status: false,
    domicile_state: ''
  })

  const [branches, setBranches] = useState({
    priorities: ['CSE'],
    any_branch: false
  })

  const [location, setLocation] = useState({
    preferred_region: 'Any',
    states_to_avoid: []
  })

  const [constraints, setConstraints] = useState({
    risk_appetite: 'Moderate',
    mtech_goal: 'Industry',
    fee_budget: 150000,
    hostel_needed: true,
    has_backlogs: false,
    btec_cgpa: ''
  })

  // ---------- Branch priority helpers ----------
  const toggleBranch = (branch) => {
    setBranches(prev => {
      if (prev.priorities.includes(branch)) {
        return {
          ...prev,
          priorities: prev.priorities.filter(b => b !== branch)
        }
      } else {
        return {
          ...prev,
          priorities: [...prev.priorities, branch]
        }
      }
    })
  }

  // ---------- Step submit handlers ----------
  const handleNext = async () => {
    setLoading(true)
    setError('')

    try {
      if (step === 0) {
        await saveGATEDetails({
          gate_score: parseFloat(gate.gate_score),
          gate_year: gate.gate_year,
          gate_air: gate.gate_air ? parseInt(gate.gate_air) : null,
          category: gate.category
        }, token)
      }

      if (step === 1) {
        const res = await savePersonalDetails(personal, token)
        if (res.data.home_state_advantage) {
          const nit = res.data.home_state_advantage.split(': ')[1]
          setHomeNIT(nit)
          setLoading(false)
          // Show message for 1.5 seconds then move to next step
          setTimeout(() => setStep(step + 1), 1500)
          return
        }
      }

      if (step === 2) {
        await saveBranchPreferences(branches, token)
      }

      if (step === 3) {
        await saveLocationPreferences(location, token)
      }

      if (step === 4) {
        await saveConstraints({
          ...constraints,
          btec_cgpa: constraints.btec_cgpa
            ? parseFloat(constraints.btec_cgpa)
            : null,
          fee_budget: parseInt(constraints.fee_budget)
        }, token)
        navigate('/dashboard')
        return
      }

      setStep(step + 1)

    } catch (err) {
      setError(
        err.response?.data?.detail || 'Something went wrong. Try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  // ---------- Render ----------
  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-lg mx-auto">

        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-blue-900 mb-1">
            Complete Your Profile
          </h1>
          <p className="text-gray-400 text-sm">
            Step {step + 1} of {STEPS.length} — {STEPS[step]}
          </p>
        </div>

        {/* Progress bar */}
        <div className="flex gap-2 mb-8">
          {STEPS.map((s, i) => (
            <div
              key={i}
              className={`h-1.5 flex-1 rounded-full transition-all ${
                i <= step ? 'bg-blue-900' : 'bg-gray-200'
              }`}
            />
          ))}
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          {/* ---------- Step 0: GATE Details ---------- */}
          {step === 0 && (
            <div className="flex flex-col gap-4">
              <h2 className="font-semibold text-gray-800 mb-2">
                Your GATE Details
              </h2>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  GATE Score (out of 1000)
                </label>
                <input
                  type="number"
                  value={gate.gate_score}
                  onChange={e => setGate({...gate, gate_score: e.target.value})}
                  placeholder="e.g. 615"
                  min="0" max="1000"
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  GATE Year
                </label>
                <input
                  type="number"
                  value={gate.gate_year}
                  onChange={e => setGate({...gate, gate_year: parseInt(e.target.value)})}
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  GATE AIR{' '}
                  <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <input
                  type="number"
                  value={gate.gate_air}
                  onChange={e => setGate({...gate, gate_air: e.target.value})}
                  placeholder="e.g. 4200"
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  Category
                </label>
                <div className="flex gap-2 flex-wrap">
                  {CATEGORIES.map(cat => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setGate({...gate, category: cat})}
                      className={`px-4 py-2 rounded-xl border text-sm font-medium transition-all ${
                        gate.category === cat
                          ? 'bg-blue-900 text-white border-blue-900'
                          : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ---------- Step 1: Personal Details ---------- */}
          {step === 1 && (
            <div className="flex flex-col gap-4">
              <h2 className="font-semibold text-gray-800 mb-2">
                Personal Details
              </h2>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  Gender
                </label>
                <div className="flex gap-3">
                  {['Male', 'Female', 'Other'].map(g => (
                    <button
                      key={g}
                      type="button"
                      onClick={() => setPersonal({...personal, gender: g})}
                      className={`flex-1 py-2.5 rounded-xl border text-sm font-medium transition-all ${
                        personal.gender === g
                          ? 'bg-blue-900 text-white border-blue-900'
                          : 'bg-white text-gray-600 border-gray-200'
                      }`}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  Domicile State
                </label>
                <input
                  type="text"
                  value={personal.domicile_state}
                  onChange={e => setPersonal({...personal, domicile_state: e.target.value})}
                  placeholder="e.g. Assam"
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
                />
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="pwd"
                  checked={personal.pwd_status}
                  onChange={e => setPersonal({...personal, pwd_status: e.target.checked})}
                  className="w-4 h-4 accent-blue-900"
                />
                <label htmlFor="pwd" className="text-sm text-gray-700">
                  Person with Disability (PwD)
                </label>
              </div>

              {homeNIT && (
                <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 text-green-700 text-sm">
                  🏠 Home state advantage detected — <strong>{homeNIT}</strong>
                </div>
              )}
            </div>
          )}

          {/* ---------- Step 2: Branch Preferences ---------- */}
          {step === 2 && (
            <div className="flex flex-col gap-4">
              <h2 className="font-semibold text-gray-800 mb-2">
                Branch Preferences
              </h2>
              <p className="text-sm text-gray-400">
                Select all branches you are interested in.
                First selected = highest priority.
              </p>

              <div className="flex gap-2 flex-wrap">
                {BRANCHES.map(branch => (
                  <button
                    key={branch}
                    type="button"
                    onClick={() => toggleBranch(branch)}
                    className={`px-4 py-2 rounded-xl border text-sm font-medium transition-all ${
                      branches.priorities.includes(branch)
                        ? 'bg-blue-900 text-white border-blue-900'
                        : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'
                    }`}
                  >
                    {branch}
                  </button>
                ))}
              </div>

              {branches.priorities.length > 0 && (
                <div className="bg-blue-50 rounded-xl p-3">
                  <p className="text-xs text-blue-400 mb-2 font-medium">
                    Your priority order:
                  </p>
                  {branches.priorities.map((b, i) => (
                    <p key={b} className="text-sm text-blue-800">
                      {i + 1}. {b}
                    </p>
                  ))}
                </div>
              )}

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="any"
                  checked={branches.any_branch}
                  onChange={e => setBranches({...branches, any_branch: e.target.checked})}
                  className="w-4 h-4 accent-blue-900"
                />
                <label htmlFor="any" className="text-sm text-gray-700">
                  Any branch is fine
                </label>
              </div>
            </div>
          )}

          {/* ---------- Step 3: Location ---------- */}
          {step === 3 && (
            <div className="flex flex-col gap-4">
              <h2 className="font-semibold text-gray-800 mb-2">
                Location Preferences
              </h2>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  Preferred Region
                </label>
                <div className="flex flex-col gap-2">
                  {REGIONS.map(region => (
                    <button
                      key={region}
                      type="button"
                      onClick={() => setLocation({...location, preferred_region: region})}
                      className={`w-full py-2.5 rounded-xl border text-sm font-medium text-left px-4 transition-all ${
                        location.preferred_region === region
                          ? 'bg-blue-900 text-white border-blue-900'
                          : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'
                      }`}
                    >
                      {region}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ---------- Step 4: Constraints ---------- */}
          {step === 4 && (
            <div className="flex flex-col gap-4">
              <h2 className="font-semibold text-gray-800 mb-2">
                Other Preferences
              </h2>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  Risk Appetite
                </label>
                <div className="flex gap-2">
                  {['Safe', 'Moderate', 'Ambitious'].map(r => (
                    <button
                      key={r}
                      type="button"
                      onClick={() => setConstraints({...constraints, risk_appetite: r})}
                      className={`flex-1 py-2.5 rounded-xl border text-sm font-medium transition-all ${
                        constraints.risk_appetite === r
                          ? 'bg-blue-900 text-white border-blue-900'
                          : 'bg-white text-gray-600 border-gray-200'
                      }`}
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  M.Tech Goal
                </label>
                <div className="flex gap-2">
                  {['Industry', 'Research', 'Undecided'].map(g => (
                    <button
                      key={g}
                      type="button"
                      onClick={() => setConstraints({...constraints, mtech_goal: g})}
                      className={`flex-1 py-2.5 rounded-xl border text-sm font-medium transition-all ${
                        constraints.mtech_goal === g
                          ? 'bg-blue-900 text-white border-blue-900'
                          : 'bg-white text-gray-600 border-gray-200'
                      }`}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  Fee Budget (per year in Rs)
                </label>
                <input
                  type="number"
                  value={constraints.fee_budget}
                  onChange={e => setConstraints({...constraints, fee_budget: e.target.value})}
                  placeholder="e.g. 150000"
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  B.Tech CGPA{' '}
                  <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <input
                  type="number"
                  value={constraints.btec_cgpa}
                  onChange={e => setConstraints({...constraints, btec_cgpa: e.target.value})}
                  placeholder="e.g. 7.8"
                  step="0.1" min="0" max="10"
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
                />
              </div>

              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="hostel"
                    checked={constraints.hostel_needed}
                    onChange={e => setConstraints({...constraints, hostel_needed: e.target.checked})}
                    className="w-4 h-4 accent-blue-900"
                  />
                  <label htmlFor="hostel" className="text-sm text-gray-700">
                    Hostel required
                  </label>
                </div>

                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="backlogs"
                    checked={constraints.has_backlogs}
                    onChange={e => setConstraints({...constraints, has_backlogs: e.target.checked})}
                    className="w-4 h-4 accent-blue-900"
                  />
                  <label htmlFor="backlogs" className="text-sm text-gray-700">
                    I have active backlogs
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 text-red-600 text-sm mt-4">
              {error}
            </div>
          )}

          {/* Navigation buttons */}
          <div className="flex gap-3 mt-6">
            {step > 0 && (
              <button
                type="button"
                onClick={() => setStep(step - 1)}
                className="flex-1 py-2.5 rounded-xl border border-gray-200 text-gray-600 text-sm font-medium hover:bg-gray-50"
              >
                Back
              </button>
            )}
            <button
              type="button"
              onClick={handleNext}
              disabled={loading}
              className="flex-1 bg-blue-900 text-white font-semibold py-2.5 rounded-xl hover:bg-blue-800 disabled:opacity-50 text-sm"
            >
              {loading
                ? 'Saving...'
                : step === STEPS.length - 1
                ? 'Complete Profile'
                : 'Next'}
            </button>
          </div>

        </div>
      </div>
    </div>
  )
}