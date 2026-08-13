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

// ---------- Advisor ----------
export const getAdvisor = (token, current, target) =>
  API.post(
    `/advisor?token=${token}&current_allocation=${current}&target_nit=${target}`
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