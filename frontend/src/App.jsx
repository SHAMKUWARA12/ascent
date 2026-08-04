import { useState, useEffect } from 'react'
import axios from 'axios'

function App() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios.get('http://localhost:8000/health')
      .then(res => {
        setStatus(res.data)
        setLoading(false)
      })
      .catch(err => {
        setStatus({ error: 'Backend not reachable' })
        setLoading(false)
      })
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-lg p-10 max-w-md w-full text-center">

        <h1 className="text-3xl font-semibold text-blue-900 mb-2">
          ASCENT
        </h1>

        <p className="text-gray-500 text-sm mb-8">
          AI-Powered M.Tech Admission Prediction
          and Recommendation System
        </p>

        <div className="bg-gray-50 rounded-xl p-4 mb-6">
          <p className="text-xs text-gray-400 uppercase tracking-widest mb-2">
            Backend Status
          </p>
          {loading ? (
            <p className="text-gray-400 text-sm">Checking...</p>
          ) : status?.status === 'healthy' ? (
            <p className="text-green-600 font-medium">
              ✅ Backend is running
            </p>
          ) : (
            <p className="text-red-500 font-medium">
              ❌ Backend not reachable
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3 text-left">
          <div className="bg-blue-50 rounded-xl p-3">
            <p className="text-xs text-blue-400 mb-1">Frontend</p>
            <p className="text-sm font-medium text-blue-800">
              React + Vite
            </p>
          </div>
          <div className="bg-blue-50 rounded-xl p-3">
            <p className="text-xs text-blue-400 mb-1">Backend</p>
            <p className="text-sm font-medium text-blue-800">
              Python FastAPI
            </p>
          </div>
          <div className="bg-blue-50 rounded-xl p-3">
            <p className="text-xs text-blue-400 mb-1">Database</p>
            <p className="text-sm font-medium text-blue-800">
              MongoDB
            </p>
          </div>
          <div className="bg-blue-50 rounded-xl p-3">
            <p className="text-xs text-blue-400 mb-1">ML Model</p>
            <p className="text-sm font-medium text-blue-800">
              TensorFlow
            </p>
          </div>
        </div>

        <p className="text-xs text-gray-300 mt-8">
          NIT Silchar · Dept. of CSE · Ayush Shamkuwar
        </p>

      </div>
    </div>
  )
}

export default App