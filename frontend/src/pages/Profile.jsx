import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  saveGATEDetails,
  savePersonalDetails,
  saveBranchPreferences,
  saveLocationPreferences,
  saveConstraints,
  getProfile
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
  const [fetching, setFetching] = useState(true)
  const [error, setError] = useState('')
  const [homeNIT, setHomeNIT] = useState('')
  const [isEditing, setIsEditing] = useState(false)

  // Form states — pre-filled with defaults
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

  // ---------- Load existing profile on mount ----------
  useEffect(() => {
    loadExistingProfile()
  }, [])

  const loadExistingProfile = async () => {
    try {
      const res = await getProfile(token)
      const p = res.data

      if (p.profile_complete) {
        setIsEditing(true)
      }

      // Pre-fill GATE details
      if (p.gate_score) {
        setGate({
          gate_score: p.gate_score ?? '',
          gate_year: p.gate_year ?? 2026,
          gate_air: p.gate_air ?? '',
          category: p.category ?? 'OBC'
        })
      }

      // Pre-fill personal details
      if (p.gender) {
        setPersonal({
          gender: p.gender ?? 'Male',
          pwd_status: p.pwd_status ?? false,
          domicile_state: p.domicile_state ?? ''
        })
      }

      // Pre-fill branch preferences
      if (p.branch_priorities) {
        setBranches({
          priorities: p.branch_priorities ?? ['CSE'],
          any_branch: p.any_branch ?? false
        })
      }

      // Pre-fill location
      if (p.preferred_region) {
        setLocation({
          preferred_region: p.preferred_region ?? 'Any',
          states_to_avoid: p.states_to_avoid ?? []
        })
      }

      // Pre-fill constraints
      if (p.risk_appetite) {
        setConstraints({
          risk_appetite: p.risk_appetite ?? 'Moderate',
          mtech_goal: p.mtech_goal ?? 'Industry',
          fee_budget: p.fee_budget ?? 150000,
          hostel_needed: p.hostel_needed ?? true,
          has_backlogs: p.has_backlogs ?? false,
          btec_cgpa: p.btec_cgpa ?? ''
        })
      }

      // Set home NIT if exists
      if (p.home_state_nit) {
        setHomeNIT(p.home_state_nit)
      }

    } catch (err) {
      console.error('Could not load profile', err)
    } finally {
      setFetching(false)
    }
  }

  // ---------- Branch toggle ----------
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

  // ---------- Step submit ----------
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
          setStep(step+1)
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

  // ---------- Loading state ----------
  if (fetching) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-900 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-400 text-sm">Loading your profile...</p>
        </div>
      </div>
    )
  }

  // ---------- Render ----------
  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-lg mx-auto">

        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-blue-900 mb-1">
            {isEditing ? 'Edit Your Profile' : 'Complete Your Profile'}
          </h1>
          <p className="text-gray-400 text-sm">
            Step {step + 1} of {STEPS.length} — {STEPS[step]}
          </p>
          {isEditing && (
            <p className="text-xs text-green-600 mt-1">
              ✅ Your existing data is pre-filled — just change what you need
            </p>
          )}
        </div>

        {/* Progress bar */}
        <div className="flex gap-2 mb-8">
          {STEPS.map((s, i) => (
            <div
              key={i}
              onClick={() => i < step && setStep(i)}
              className={`h-1.5 flex-1 rounded-full transition-all ${
                i <= step ? 'bg-blue-900' : 'bg-gray-200'
              } ${i < step ? 'cursor-pointer hover:bg-blue-700' : ''}`}
            />
          ))}
        </div>

        {/* Step tabs — click to jump back */}
        {isEditing && (
          <div className="flex gap-1 mb-6 flex-wrap">
            {STEPS.map((s, i) => (
              <button
                key={i}
                onClick={() => setStep(i)}
                className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all ${
                  step === i
                    ? 'bg-blue-900 text-white'
                    : 'bg-white text-gray-500 border border-gray-200 hover:border-blue-300'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        )}

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

          {/* ---------- Step 1: Personal ---------- */}
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
                <select
                  value={personal.domicile_state}
                  onChange={e => {
                    const state = e.target.value
                    setPersonal({...personal, domicile_state: state})

                    // Auto-detect home state NIT immediately
                    const mapping = {
                      "Andhra Pradesh":   "NIT Andhra Pradesh",
                      "Assam":            "NIT Silchar",
                      "Bihar":            "NIT Patna",
                      "Chhattisgarh":     "NIT Raipur",
                      "Delhi":            "NIT Delhi",
                      "Goa":              "NIT Goa",
                      "Gujarat":          "NIT Surat",
                      "Haryana":          "NIT Kurukshetra",
                      "Himachal Pradesh": "NIT Hamirpur",
                      "Jharkhand":        "NIT Jamshedpur",
                      "Karnataka":        "NIT Surathkal",
                      "Kerala":           "NIT Calicut",
                      "Madhya Pradesh":   "NIT Bhopal",
                      "Maharashtra":      "NIT Nagpur",
                      "Manipur":          "NIT Manipur",
                      "Meghalaya":        "NIT Meghalaya",
                      "Mizoram":          "NIT Mizoram",
                      "Nagaland":         "NIT Nagaland",
                      "Odisha":           "NIT Rourkela",
                      "Punjab":           "NIT Jalandhar",
                      "Rajasthan":        "NIT Jaipur",
                      "Sikkim":           "NIT Sikkim",
                      "Tamil Nadu":       "NIT Trichy",
                      "Telangana":        "NIT Warangal",
                      "Tripura":          "NIT Agartala",
                      "Uttar Pradesh":    "NIT Allahabad",
                      "Uttarakhand":      "NIT Uttarakhand",
                      "West Bengal":      "NIT Durgapur",
                    }

                    const detected = mapping[state] || null
                    setHomeNIT(detected || '')
                  }}
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400 bg-white"
                >
                  <option value="">Select your state</option>
                  <option value="Andhra Pradesh">Andhra Pradesh</option>
                  <option value="Assam">Assam</option>
                  <option value="Bihar">Bihar</option>
                  <option value="Chhattisgarh">Chhattisgarh</option>
                  <option value="Delhi">Delhi</option>
                  <option value="Goa">Goa</option>
                  <option value="Gujarat">Gujarat</option>
                  <option value="Haryana">Haryana</option>
                  <option value="Himachal Pradesh">Himachal Pradesh</option>
                  <option value="Jharkhand">Jharkhand</option>
                  <option value="Karnataka">Karnataka</option>
                  <option value="Kerala">Kerala</option>
                  <option value="Madhya Pradesh">Madhya Pradesh</option>
                  <option value="Maharashtra">Maharashtra</option>
                  <option value="Manipur">Manipur</option>
                  <option value="Meghalaya">Meghalaya</option>
                  <option value="Mizoram">Mizoram</option>
                  <option value="Nagaland">Nagaland</option>
                  <option value="Odisha">Odisha</option>
                  <option value="Punjab">Punjab</option>
                  <option value="Rajasthan">Rajasthan</option>
                  <option value="Sikkim">Sikkim</option>
                  <option value="Tamil Nadu">Tamil Nadu</option>
                  <option value="Telangana">Telangana</option>
                  <option value="Tripura">Tripura</option>
                  <option value="Uttar Pradesh">Uttar Pradesh</option>
                  <option value="Uttarakhand">Uttarakhand</option>
                  <option value="West Bengal">West Bengal</option>
                </select>
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
                  🏠 Home state NIT — <strong>{homeNIT}</strong>
                </div>
              )}
            </div>
          )}

          {/* ---------- Step 2: Branch ---------- */}
          {step === 2 && (
            <div className="flex flex-col gap-4">
              <h2 className="font-semibold text-gray-800 mb-2">
                Branch Preferences
              </h2>
              <p className="text-sm text-gray-400">
                Select all branches you want.
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

          {/* Navigation */}
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
                ? isEditing ? 'Save Changes' : 'Complete Profile'
                : 'Next'}
            </button>
          </div>

        </div>

        {/* Cancel button when editing */}
        {isEditing && (
          <button
            onClick={() => navigate('/profile-view')}
            className="w-full text-gray-400 text-sm mt-4 hover:text-gray-600"
          >
            Cancel — go back to profile
          </button>
        )}

      </div>
    </div>
  )
}