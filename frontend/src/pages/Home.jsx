import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Home() {
  const { student } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50">

      {/* Hero */}
      <div className="bg-blue-900 text-white py-20 px-6 text-center">
        <h1 className="text-4xl font-bold mb-4">
          Find the Right NIT for Your M.Tech
        </h1>
        <p className="text-blue-200 text-lg mb-2">
          Free · Score-Based · Data-Driven
        </p>
        <p className="text-blue-300 text-sm mb-8">
          AI-Powered Prediction and Recommendation System
        </p>

        {student ? (
          <Link
            to="/dashboard"
            className="bg-white text-blue-900 font-semibold px-8 py-3 rounded-xl hover:bg-blue-50"
          >
            Go to Dashboard
          </Link>
        ) : (
          <Link
            to="/signup"
            className="bg-white text-blue-900 font-semibold px-8 py-3 rounded-xl hover:bg-blue-50"
          >
            Get Started — It is Free
          </Link>
        )}
      </div>

      {/* Features */}
      <div className="max-w-4xl mx-auto py-16 px-6">
        <h2 className="text-2xl font-semibold text-center text-gray-800 mb-10">
          Why ASCENT?
        </h2>

        <div className="grid grid-cols-2 gap-6">
          {[
            {
              title: "31 NITs Covered",
              desc: "All NITs across India for GATE CSE and DA papers"
            },
            {
              title: "Score-Based (Not Rank)",
              desc: "CCMT uses GATE Score — so do we. No other free tool does this."
            },
            {
              title: "Three-Part Choice Filing",
              desc: "Separate optimised lists for Regular, Special, and National rounds"
            },
            {
              title: "Lock / Float / Slide Advisor",
              desc: "Data-driven advice after every round result"
            },
            {
              title: "Home State Advantage",
              desc: "Automatically detects your home state NIT quota advantage"
            },
            {
              title: "5 Years of CCMT Data",
              desc: "Predictions based on 2021–2025 historical cutoff scores"
            }
          ].map((f, i) => (
            <div key={i} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
              <h3 className="font-semibold text-blue-900 mb-1">{f.title}</h3>
              <p className="text-gray-500 text-sm">{f.desc}</p>
            </div>
          ))}
        </div>

        {/* How it works */}
        <h2 className="text-2xl font-semibold text-center text-gray-800 mt-16 mb-8">
          How It Works
        </h2>

        <div className="flex flex-col gap-4">
          {[
            "Enter your GATE Score, category, domicile and preferences",
            "ASCENT filters NITs with verified M.Tech programmes for your GATE paper",
            "Get Safe, Target and Ambitious NIT recommendations with probabilities",
            "Download your ready-to-submit choice filing list for each counselling part",
            "Get Lock, Float or Slide advice after every round result"
          ].map((step, i) => (
            <div key={i} className="flex items-start gap-4 bg-white rounded-xl p-4 border border-gray-100">
              <span className="bg-blue-900 text-white text-sm font-bold w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0">
                {i + 1}
              </span>
              <p className="text-gray-700 text-sm">{step}</p>
            </div>
          ))}
        </div>

        {!student && (
          <div className="text-center mt-12">
            <Link
              to="/signup"
              className="bg-blue-900 text-white font-semibold px-8 py-3 rounded-xl hover:bg-blue-800"
            >
              Sign Up Free
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}