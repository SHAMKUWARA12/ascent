import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(
    localStorage.getItem('ascent_token') || null
  )
  const [student, setStudent] = useState(
    JSON.parse(localStorage.getItem('ascent_student') || 'null')
  )

  const loginUser = (token, studentData) => {
    localStorage.setItem('ascent_token', token)
    localStorage.setItem('ascent_student', JSON.stringify(studentData))
    setToken(token)
    setStudent(studentData)
  }

  const logoutUser = () => {
    localStorage.removeItem('ascent_token')
    localStorage.removeItem('ascent_student')
    setToken(null)
    setStudent(null)
  }

  return (
    <AuthContext.Provider value={{ token, student, loginUser, logoutUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)