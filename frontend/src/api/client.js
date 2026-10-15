import axios from 'axios'

// All requests go to /api; in development Vite proxies that to FastAPI (vite.config.js).
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
})

// Drop empty filter values so the URL only contains filters the user actually set.
const cleanParams = (params = {}) =>
  Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined))

// FastAPI returns errors as { detail: "..." } (or a list for validation errors).
export function errorMessage(error) {
  const detail = error?.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join(', ')
  return detail || error?.message || 'Something went wrong'
}

export const apiGet = (path, params) => api.get(path, { params: cleanParams(params) }).then((r) => r.data)
export const apiPost = (path, body) => api.post(path, body).then((r) => r.data)
export const apiPatch = (path, body) => api.patch(path, body).then((r) => r.data)
