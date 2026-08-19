import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import axios from 'axios'

export default function NITDetail() {
  const { nit_code } = useParams()
  const { token } = useAuth()
  const navigate = useNavigate()
  const [nit, setNit] = useState(null)
  const [loading, setLoading] = useState(true)

  // Dummy round-wise data
  // Will be replaced by ML model later
  const roundData = {
    "NITSLR": [
      { round: "R1", predicted: 545, range: "535-555", prob: 95 },
      { round: "R2", predicted: 538, range: "528-548", prob: 96 },
      { round: "R3", predicted: 530, range: "520-540", prob: 97 },
      { round: "SR1", predicted: 522, range: "512-532", prob: 98 },
      { round: "SR2", predicted: 515, range: "505-525", prob: 99 },
    ],
    "NITRK": [
      { round: "R1", predicted: 648, range: "635-660", prob: 20 },
      { round: "R2", predicted: 635, range: "622-648", prob: 38 },
      { round: "R3", predicted: 618, range: "605-631", prob: 58 },
      { round: "SR1", predicted: 605, range: "592-618", prob: 72 },
      { round: "SR2", predicted: 595, range: "582-608", prob: 81 },
    ],
    "NITT": [
      { round: "R1", predicted: 658, range: "645-670", prob: 15 },
      { round: "R2", predicted: 645, range: "632-658", prob: 32 },
      { round: "R3", predicted: 628, range: "615-641", prob: 55 },
      { round: "SR1", predicted: 615, range: "602-628", prob: 68 },
      { round: "SR2", predicted: 605, range: "592-618", prob: 75 },
    ],
    "NITW": [
      { round: "R1", predicted: 668, range: "655-680", prob: 10 },
      { round: "R2", predicted: 655, range: "642-668", prob: 22 },
      { round: "R3", predicted: 638, range: "625-651", prob: 40 },
      { round: "SR1", predicted: 625, range: "612-638", prob: 55 },
      { round: "SR2", predicted: 615, range: "602-628", prob: 65 },
    ],
    "NITC": [
      { round: "R1", predicted: 638, range: "625-650", prob: 25 },
      { round: "R2", predicted: 625, range: "612-638", prob: 42 },
      { round: "R3", predicted: 610, range: "597-623", prob: 60 },
      { round: "SR1", predicted: 598, range: "585-611", prob: 72 },
      { round: "SR2", predicted: 588, range: "575-601", prob: 80 },
    ],
  }

  // Dummy sentiment data
  // Will be replaced by Reddit/PaGaLGuY scraper later
  const sentimentData = {
    "NITSLR": {
      overall: 7.1,
      placements: 7.0,
      campus: 7.3,
      faculty: 7.2,
      posts: 98
    },
    "NITRK": {
      overall: 8.1,
      placements: 8.5,
      campus: 7.8,
      faculty: 7.6,
      posts: 189
    },
    "NITT": {
      overall: 8.3,
      placements: 8.6,
      campus: 8.1,
      faculty: 8.0,
      posts: 245
    },
    "NITW": {
      overall: 8.4,
      placements: 8.8,
      campus: 8.2,
      faculty: 8.0,
      posts: 312
    },
    "NITC": {
      overall: 7.9,
      placements: 8.0,
      campus: 7.8,
      faculty: 7.9,
      posts: 178
    },
  }

  // Dummy historical cutoffs
  const historicalData = {
    "NITSLR": [
      { year: 2021, closing: 548 },
      { year: 2022, closing: 535 },
      { year: 2023, closing: 542 },
      { year: 2024, closing: 528 },
      { year: 2025, closing: 530 },
    ],
    "NITRK": [
      { year: 2021, closing: 608 },
      { year: 2022, closing: 615 },
      { year: 2023, closing: 601 },
      { year: 2024, closing: 618 },
      { year: 2025, closing: 622 },
    ],
    "NITT": [
      { year: 2021, closing: 618 },
      { year: 2022, closing: 625 },
      { year: 2023, closing: 611 },
      { year: 2024, closing: 628 },
      { year: 2025, closing: 632 },
    ],
    "NITW": [
      { year: 2021, closing: 628 },
      { year: 2022, closing: 635 },
      { year: 2023, closing: 621 },
      { year: 2024, closing: 638 },
      { year: 2025, closing: 641 },
    ],
    "NITC": [
      { year: 2021, closing: 598 },
      { year: 2022, closing: 605 },
      { year: 2023, closing: 591 },
      { year: 2024, closing: 608 },
      { year: 2025, closing: 612 },
    ],
  }

  useEffect(() => {
    fetchNIT()
  }, [nit_code])

  const fetchNIT = async () => {
    try {
      const res = await axios.get(
        `http://localhost:8000/api/v1/nits/${nit_code}`
      )
      setNit(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
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
          <button
            onClick={() => navigate('/dashboard')}
            className="bg-blue-900 text-white px-6 py-2 rounded-xl text-sm"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  const rounds = roundData[nit_code] || []
  const sentiment = sentimentData[nit_code] || null
  const historical = historicalData[nit_code] || []
  const sentLabel = sentiment
    ? getSentimentLabel(sentiment.overall)
    : null

  return (
    <div className="min-h-screen bg-gray-50">

      {/* Header */}
      <div className="bg-blue-900 text-white px-6 py-6">
        <button
          onClick={() => navigate('/dashboard')}
          className="text-blue-300 text-sm mb-3 hover:text-white flex items-center gap-1"
        >
          ← Back to Dashboard
        </button>
        <h1 className="text-2xl font-bold mb-1">{nit.name}</h1>
        <p className="text-blue-200 text-sm">
          {nit.location} · NIRF #{nit.nirf_rank} · Est. {nit.established}
        </p>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-6">

        {/* Basic Info */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
          <h2 className="font-semibold text-gray-800 mb-4">
            Basic Information
          </h2>
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
              <p className="font-medium text-gray-800">#{nit.nirf_rank}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Established</p>
              <p className="font-medium text-gray-800">{nit.established}</p>
            </div>
          </div>
        </div>

        {/* M.Tech Programs */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
          <h2 className="font-semibold text-gray-800 mb-4">
            M.Tech Programmes (Verified)
          </h2>
          {(nit.mtech_programs || []).map((prog, i) => (
            <div
              key={i}
              className="border border-gray-100 rounded-xl p-4 mb-3"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-gray-800 text-sm">
                    {prog.official_name}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    GATE Papers: {prog.gate_papers?.join(', ')}
                  </p>
                </div>
                <span className="bg-blue-50 text-blue-700 text-xs px-2 py-1 rounded-lg font-medium">
                  {prog.short_name}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-3 mt-3">
                <div>
                  <p className="text-xs text-gray-400">Total Seats</p>
                  <p className="font-semibold text-gray-800 text-sm">
                    {Object.values(prog.seats || {}).reduce((a, b) => a + b, 0)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Fee/Year</p>
                  <p className="font-semibold text-gray-800 text-sm">
                    Rs {prog.fee_annual?.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Hostel</p>
                  <p className="font-semibold text-gray-800 text-sm">
                    {prog.has_hostel ? 'Available' : 'Not available'}
                  </p>
                </div>
              </div>

              {/* Seat breakdown */}
              <div className="mt-3 flex gap-2 flex-wrap">
                {Object.entries(prog.seats || {}).map(([cat, seats]) => (
                  <span
                    key={cat}
                    className="text-xs bg-gray-50 text-gray-600 px-2 py-1 rounded-lg"
                  >
                    {cat}: {seats}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Round-wise Predictions */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
          <h2 className="font-semibold text-gray-800 mb-1">
            Round-wise Predicted Closing Scores
          </h2>
          <p className="text-xs text-gray-400 mb-4">
            OBC-NCL category · Based on 2021–2025 CCMT data
          </p>
          {rounds.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="text-left py-2 text-xs text-gray-400 font-medium">Round</th>
                    <th className="text-left py-2 text-xs text-gray-400 font-medium">Predicted Score</th>
                    <th className="text-left py-2 text-xs text-gray-400 font-medium">Range (95% CI)</th>
                    <th className="text-left py-2 text-xs text-gray-400 font-medium">Probability</th>
                  </tr>
                </thead>
                <tbody>
                  {rounds.map((r, i) => (
                    <tr key={i} className="border-b border-gray-50">
                      <td className="py-2.5 font-medium text-gray-800">
                        {r.round}
                      </td>
                      <td className="py-2.5 font-semibold text-blue-900">
                        {r.predicted}
                      </td>
                      <td className="py-2.5 text-gray-500 text-xs">
                        [{r.range}]
                      </td>
                      <td className="py-2.5">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                          r.prob >= 70
                            ? 'bg-green-100 text-green-700'
                            : r.prob >= 40
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-red-100 text-red-600'
                        }`}>
                          {r.prob}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-400 text-sm">
              Round-wise data not available yet
            </p>
          )}
        </div>

        {/* Historical Cutoffs */}
        <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
          <h2 className="font-semibold text-gray-800 mb-4">
            Historical Closing Scores (OBC-NCL)
          </h2>
          <div className="flex gap-3 flex-wrap">
            {historical.map((h, i) => (
              <div
                key={i}
                className="flex-1 min-w-16 bg-blue-50 rounded-xl p-3 text-center"
              >
                <p className="text-xs text-blue-400 mb-1">{h.year}</p>
                <p className="font-bold text-blue-900">{h.closing}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Sentiment Analysis */}
        {sentiment && (
          <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-4">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-semibold text-gray-800">
                  Student Sentiment
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  Based on {sentiment.posts} Reddit + PaGaLGuY posts
                </p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-gray-800">
                  {sentiment.overall}
                  <span className="text-sm text-gray-400">/10</span>
                </p>
                <p className={`text-xs font-semibold ${sentLabel.color}`}>
                  {sentLabel.label}
                </p>
              </div>
            </div>

            <div className="flex flex-col gap-3">
              {[
                { label: 'Placements', score: sentiment.placements },
                { label: 'Campus Life', score: sentiment.campus },
                { label: 'Faculty', score: sentiment.faculty },
              ].map((item, i) => (
                <div key={i}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-500">{item.label}</span>
                    <span className="font-medium text-gray-800">
                      {item.score}/10
                    </span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-900 rounded-full"
                      style={{ width: `${item.score * 10}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <p className="text-xs text-gray-400 mt-3">
              * Sentiment scores are currently placeholder values.
              Real Reddit and PaGaLGuY data will be integrated
              in the next phase.
            </p>
          </div>
        )}

        {/* Back button */}
        <button
          onClick={() => navigate('/dashboard')}
          className="w-full bg-gray-100 text-gray-700 py-3 rounded-xl text-sm font-medium hover:bg-gray-200"
        >
          Back to Dashboard
        </button>

      </div>
    </div>
  )
}