import axios from 'axios'

const API = axios.create({
  baseURL: 'http://localhost:8000/api/v1'
})

// ---------- Auth ----------
export const signup = (data) =>
  API.post('/auth/signup', data)

export const login = (data) =>
  API.post('/auth/login', data)

export const getMe = (token) =>
  API.get(`/auth/me?token=${token}`)

// ---------- Profile ----------
export const saveGATEDetails = (data, token) =>
  API.post(`/profile/gate?token=${token}`, data)

export const savePersonalDetails = (data, token) =>
  API.post(`/profile/personal?token=${token}`, data)

export const saveBranchPreferences = (data, token) =>
  API.post(`/profile/branches?token=${token}`, data)

export const saveLocationPreferences = (data, token) =>
  API.post(`/profile/location?token=${token}`, data)

export const saveConstraints = (data, token) =>
  API.post(`/profile/constraints?token=${token}`, data)

export const getProfile = (token) =>
  API.get(`/profile?token=${token}`)

// ---------- Recommendations ----------
export const getRecommendations = (token) =>
  API.get(`/recommend?token=${token}`)

// ---------- Choice Filing ----------
export const getChoiceFilingPart1 = (token) =>
  API.get(`/choice-filing/part1?token=${token}`)

export const getChoiceFilingPart2 = (token, currentAllocation) =>
  API.post(
    `/choice-filing/part2?token=${encodeURIComponent(token)}&current_allocation=${encodeURIComponent(currentAllocation)}`
  )

// ---------- Advisor ----------
export const getAdvisor = (
  token, currentNIT, currentBranch, targetNIT, targetBranch
) =>
  API.post(
    `/advisor?token=${encodeURIComponent(token)}&current_nit=${encodeURIComponent(currentNIT)}&current_branch=${encodeURIComponent(currentBranch)}&target_nit=${encodeURIComponent(targetNIT)}&target_branch=${encodeURIComponent(targetBranch)}`
  )

// ---------- Update Profile ----------
export const updateGATEDetails = (data, token) =>
  API.post(`/profile/gate?token=${token}`, data)

export const updatePersonalDetails = (data, token) =>
  API.post(`/profile/personal?token=${token}`, data)

export const updateBranchPreferences = (data, token) =>
  API.post(`/profile/branches?token=${token}`, data)

export const updateLocationPreferences = (data, token) =>
  API.post(`/profile/location?token=${token}`, data)

export const updateConstraints = (data, token) =>
  API.post(`/profile/constraints?token=${token}`, data)