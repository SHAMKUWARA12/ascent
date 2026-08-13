import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { getProfile } from '../services/api'
import { useNavigate } from 'react-router-dom'

export default function ProfileView() {
  const { token } = useAuth()
  const navigate = useNavigate()
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchProfile()
  }, [])

  const fetchProfile = async () => {
    try {
      const res = await getProfile(token)
      setProfile(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-900 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400">Profile not found</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-2xl mx-auto">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-blue-900">
              My Profile
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              {profile.profile_complete
                ? '✅ Profile complete'
                : '⚠️ Profile incomplete'}
            </p>
          </div>
          <button
            onClick={() => navigate('/profile')}
            className="bg-blue-900 text-white text-sm px-4 py-2 rounded-xl hover:bg-blue-800"
          >
            Edit Profile
          </button>
        </div>

        {/* GATE Details */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
          <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span className="w-6 h-6 bg-blue-100 text-blue-700 rounded-full text-xs flex items-center justify-center font-bold">1</span>
            GATE Details
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-400 mb-1">GATE Score</p>
              <p className="font-semibold text-gray-800">
                {profile.gate_score ?? '—'} / 1000
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">GATE Year</p>
              <p className="font-semibold text-gray-800">
                {profile.gate_year ?? '—'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">GATE AIR</p>
              <p className="font-semibold text-gray-800">
                {profile.gate_air ?? 'Not provided'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Category</p>
              <p className="font-semibold text-gray-800">
                {profile.category ?? '—'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">GATE Paper</p>
              <p className="font-semibold text-gray-800">
                {profile.gate_paper ?? '—'}
              </p>
            </div>
          </div>
        </div>

        {/* Personal Details */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
          <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span className="w-6 h-6 bg-blue-100 text-blue-700 rounded-full text-xs flex items-center justify-center font-bold">2</span>
            Personal Details
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-400 mb-1">Full Name</p>
              <p className="font-semibold text-gray-800">
                {profile.full_name ?? '—'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Gender</p>
              <p className="font-semibold text-gray-800">
                {profile.gender ?? '—'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Domicile State</p>
              <p className="font-semibold text-gray-800">
                {profile.domicile_state ?? '—'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">PwD Status</p>
              <p className="font-semibold text-gray-800">
                {profile.pwd_status ? 'Yes' : 'No'}
              </p>
            </div>
            {profile.home_state_nit && (
              <div className="col-span-2">
                <p className="text-xs text-gray-400 mb-1">Home State NIT</p>
                <p className="font-semibold text-green-700">
                  🏠 {profile.home_state_nit}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Branch Preferences */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
          <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span className="w-6 h-6 bg-blue-100 text-blue-700 rounded-full text-xs flex items-center justify-center font-bold">3</span>
            Branch Preferences
          </h2>
          <div className="flex flex-wrap gap-2">
            {(profile.branch_priorities ?? []).map((branch, i) => (
              <span
                key={branch}
                className="bg-blue-50 text-blue-800 text-sm px-3 py-1 rounded-full font-medium"
              >
                {i + 1}. {branch}
              </span>
            ))}
            {(!profile.branch_priorities || profile.branch_priorities.length === 0) && (
              <p className="text-gray-400 text-sm">Not set</p>
            )}
          </div>
          {profile.any_branch && (
            <p className="text-xs text-gray-400 mt-2">
              Any branch is acceptable
            </p>
          )}
        </div>

        {/* Location Preferences */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
          <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span className="w-6 h-6 bg-blue-100 text-blue-700 rounded-full text-xs flex items-center justify-center font-bold">4</span>
            Location Preferences
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-400 mb-1">Preferred Region</p>
              <p className="font-semibold text-gray-800">
                {profile.preferred_region ?? '—'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">States to Avoid</p>
              <p className="font-semibold text-gray-800">
                {profile.states_to_avoid?.length > 0
                  ? profile.states_to_avoid.join(', ')
                  : 'None'}
              </p>
            </div>
          </div>
        </div>

        {/* Constraints */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
          <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span className="w-6 h-6 bg-blue-100 text-blue-700 rounded-full text-xs flex items-center justify-center font-bold">5</span>
            Preferences and Constraints
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-400 mb-1">Risk Appetite</p>
              <p className="font-semibold text-gray-800">
                {profile.risk_appetite ?? '—'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">M.Tech Goal</p>
              <p className="font-semibold text-gray-800">
                {profile.mtech_goal ?? '—'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Fee Budget</p>
              <p className="font-semibold text-gray-800">
                Rs {profile.fee_budget?.toLocaleString() ?? '—'} / year
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">B.Tech CGPA</p>
              <p className="font-semibold text-gray-800">
                {profile.btec_cgpa ?? 'Not provided'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Hostel Needed</p>
              <p className="font-semibold text-gray-800">
                {profile.hostel_needed ? 'Yes' : 'No'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Backlogs</p>
              <p className="font-semibold text-gray-800">
                {profile.has_backlogs ? 'Yes' : 'No'}
              </p>
            </div>
          </div>
        </div>

        {/* Back to Dashboard */}
        <button
          onClick={() => navigate('/dashboard')}
          className="w-full bg-gray-100 text-gray-700 py-3 rounded-xl text-sm font-medium hover:bg-gray-200 mt-2"
        >
          Back to Dashboard
        </button>

      </div>
    </div>
  )
}