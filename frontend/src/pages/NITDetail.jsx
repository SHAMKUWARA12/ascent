import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import axios from 'axios'

const API_BASE = 'http://localhost:8000/api/v1'

export default function NITDetail() {
  const { nit_code } = useParams()
  const { student } = useAuth()
  const navigate = useNavigate()

  const [nit, setNit] = useState(null)
  const [selectedBranch, setSelectedBranch] = useState(null)
  const [history, setHistory] = useState(null)
  const [loading, setLoading] = useState(true)
  const [historyLoading, setHistoryLoading] = useState(false)

  const category = student?.category || 'OBC'

  useEffect(() => {
    fetchNit()
  }, [nit_code])

  useEffect(() => {
    if (selectedBranch) fetchHistory(selectedBranch)
  }, [selectedBranch])

  const fetchNit = async () => {
    try {
      const res = await axios.get(`${API_BASE}/nits/${nit_code}`)
      setNit(res.data)
      const programs = res.data.mtech_programs || []
      if (programs.length > 0) {
        setSelectedBranch(programs[0].short_name)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const fetchHistory = async (branch) => {
    setHistoryLoading(true)
    try {
      const res = await axios.get(
        `${API_BASE}/nits/${nit_code}/cutoff-history`,
        { params: { branch, category } }
      )
      setHistory(res.data)
    } catch (err) {
      console.error(err)
      setHistory(null)
    } finally {
      setHistoryLoading(false)
    }
  }

  const getSentimentLabel = (score) => {
    if (score >= 8.5) return { label: 'Excellent', color: 'text-green-700' }
    if (score >= 7.5) return { label: 'Good', color: 'text-blue-700' }
    if (score >= 6.0) return { label: 'Average', color: 'text-amber-700' }
    return { label: 'Poor', color: 'text-red-600' }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-900 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!nit) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-400 mb-4">NIT not found</p>
          <button onClick={() => navigate('/dashboard')}
            className="bg-blue-900 text-white px-6 py-2 rounded-xl text-sm">
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  const sentiment = nit.sentiment
  const sentLabel = sentiment ? getSentimentLabel(sentiment.overall_score) : null

  return (
    <div className="min-h-screen bg-gray-50">

      <div className="bg-blue-900 text-white px-6 py-6">
        <button onClick={() => navigate('/dashboard')}
          className="text-blue-300 text-sm mb-3 hover:text-white">
          ← Back to Dashboard
        </button>
        <h1 className="text-2xl font-bold mb-1">{nit.name}</h1>
        <p className="text-blue-200 text-sm">
          {nit.location} · NIRF #{nit.nirf_rank}
        </p>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-6">

        {/* Basic Info */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
          <h2 className="font-semibold text-gray-800 mb-4">Basic Information</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-400 mb-1">Location</p>
              <p className="font-medium text-gray-800">{nit.location}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Region</p>
              <p className="font-medium text-gray-800">{nit.region}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">NIRF Rank</p>
              <p className="font-medium text-gray-800">
                #{nit.nirf_rank}
                <span className="text-xs text-amber-600 ml-1">
                  (approximate — real NIRF scraping pending)
                </span>
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Data Source</p>
              <p className="font-medium text-gray-800 text-xs">
                {nit.data_source}
              </p>
            </div>
          </div>
        </div>

        {/* M.Tech Programs */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
          <h2 className="font-semibold text-gray-800 mb-4">
            M.Tech Programmes (from verified CCMT records)
          </h2>
          {(nit.mtech_programs || []).map((prog, i) => (
            <button
              key={i}
              onClick={() => setSelectedBranch(prog.short_name)}
              className={`w-full text-left border rounded-xl p-4 mb-3 transition-all ${
                selectedBranch === prog.short_name
                  ? 'border-blue-400 bg-blue-50'
                  : 'border-gray-100 hover:border-gray-200'
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-gray-800 text-sm">
                    {prog.official_name}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    GATE Papers: {prog.gate_papers?.join(', ')} ·
                    {' '}{prog.historical_record_count} historical records
                  </p>
                </div>
                <span className="bg-blue-100 text-blue-700 text-xs px-2 py-1 rounded-lg font-medium">
                  {prog.short_name}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-3 mt-3 text-xs text-gray-400">
                <div>Seats: not yet scraped</div>
                <div>Fee/Year: not yet scraped</div>
                <div>Hostel: not yet scraped</div>
              </div>
            </button>
          ))}
        </div>

        {/* Round-wise + Historical (real data) */}
        {selectedBranch && (
          <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
            <h2 className="font-semibold text-gray-800 mb-1">
              Closing Scores — {selectedBranch} ({category} category)
            </h2>
            <p className="text-xs text-gray-400 mb-4">
              Real CCMT data, all rounds, per year
            </p>

            {historyLoading && (
              <p className="text-gray-400 text-sm">Loading...</p>
            )}

            {!historyLoading && history && history.round_wise_records?.length > 0 && (
              <>
                <div className="overflow-x-auto mb-4">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100">
                        <th className="text-left py-2 text-xs text-gray-400 font-medium">Year</th>
                        <th className="text-left py-2 text-xs text-gray-400 font-medium">Round</th>
                        <th className="text-left py-2 text-xs text-gray-400 font-medium">Min Score</th>
                        <th className="text-left py-2 text-xs text-gray-400 font-medium">Max Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.round_wise_records.map((r, i) => (
                        <tr key={i} className="border-b border-gray-50">
                          <td className="py-2 font-medium text-gray-800">{r.year}</td>
                          <td className="py-2 text-gray-600">{r.round}</td>
                          <td className="py-2 font-semibold text-blue-900">{r.min_score}</td>
                          <td className="py-2 text-gray-500">{r.max_score}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <p className="text-xs text-gray-400 mb-2">
                  Final closing score per year (lowest across all rounds — represents
                  the actual cutoff by the end of that year's counselling):
                </p>
                <div className="flex gap-3 flex-wrap">
                  {history.yearly_final_closing.map((h, i) => (
                    <div key={i} className="bg-blue-50 rounded-xl p-3 text-center min-w-16">
                      <p className="text-xs text-blue-400 mb-1">{h.year}</p>
                      <p className="font-bold text-blue-900">{h.closing_score}</p>
                    </div>
                  ))}
                </div>
              </>
            )}

            {!historyLoading && (!history || history.round_wise_records?.length === 0) && (
              <p className="text-gray-400 text-sm">
                No historical data available for this branch/category combination.
              </p>
            )}
          </div>
        )}

        {/* Sentiment */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-semibold text-gray-800">Student Sentiment</h2>
              {sentiment && (
                <p className="text-xs text-gray-400 mt-0.5">
                  Based on {sentiment.posts_analysed} real posts
                  (PaGaLGuY + YouTube)
                </p>
              )}
            </div>
            {sentiment && (
              <div className="text-right">
                <p className="text-2xl font-bold text-gray-800">
                  {sentiment.overall_score}<span className="text-sm text-gray-400">/10</span>
                </p>
                <p className={`text-xs font-semibold ${sentLabel.color}`}>{sentLabel.label}</p>
              </div>
            )}
          </div>

          {sentiment ? (
            <div className="flex flex-col gap-3">
              {[
                { label: 'Placements', score: sentiment.placement_score },
                { label: 'Campus Life', score: sentiment.campus_score },
                { label: 'Faculty', score: sentiment.faculty_score },
              ].map((item, i) => (
                <div key={i}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-500">{item.label}</span>
                    <span className="font-medium text-gray-800">{item.score}/10</span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-900 rounded-full"
                      style={{ width: `${item.score * 10}%` }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">No sentiment data available</p>
          )}
        </div>

        <button onClick={() => navigate('/dashboard')}
          className="w-full bg-gray-100 text-gray-700 py-3 rounded-xl text-sm font-medium hover:bg-gray-200">
          Back to Dashboard
        </button>

      </div>
    </div>
  )
}