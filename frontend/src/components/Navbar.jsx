import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { student, logoutUser } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logoutUser()
    navigate('/login')
  }

  return (
    <nav className="bg-blue-900 text-white px-6 py-3 flex items-center justify-between">

      <Link to="/" className="text-lg font-semibold tracking-tight">
        ASCENT
      </Link>

      <div className="flex items-center gap-6 text-sm">
        {student ? (
          <>
            <Link to="/dashboard" className="hover:text-blue-200">
              Dashboard
            </Link>
            <Link to="/profile-view" className="hover:text-blue-200">
              My Profile
            </Link>
            <span className="text-blue-300">
              {student.full_name}
            </span>
            <button
              onClick={handleLogout}
              className="bg-blue-700 hover:bg-blue-600 px-3 py-1 rounded-lg"
            >
              Logout
            </button>
          </>
        ) : (
          <>
            <Link to="/login" className="hover:text-blue-200">
              Login
            </Link>
            <Link
              to="/signup"
              className="bg-white text-blue-900 font-medium px-3 py-1 rounded-lg hover:bg-blue-100"
            >
              Sign Up Free
            </Link>
          </>
        )}
      </div>

    </nav>
  )
}