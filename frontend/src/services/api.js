import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('hata_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401) {
      sessionStorage.removeItem('hata_token')
      window.dispatchEvent(new Event('hata-unauthorized'))
    }
    const message = err?.response?.data?.detail || err.message || 'Unknown error'
    return Promise.reject(new Error(message))
  }
)

// --- Auth ---
export const login = (usernameOrPassword, password) => {
  // Support both login(password) for legacy callers and login(username, password)
  const payload = password !== undefined
    ? { username: usernameOrPassword, password }
    : { password: usernameOrPassword }
  return api.post('/auth/login', payload).then(r => r.data)
}
export const register = (payload) => api.post('/auth/register', payload).then(r => r.data)
export const getMe = () => api.get('/auth/me').then(r => r.data)
export const updateProfile = (payload) => api.put('/auth/me', payload).then(r => r.data)
export const listUsers = () => api.get('/auth/users').then(r => r.data)
export const logout = () => api.post('/auth/logout').then(r => r.data).catch(() => {})

// --- Scans ---
export const uploadScan = (file, onProgress) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/scans/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress,
  }).then(r => r.data)
}
export const startScan = (scanId) => api.post(`/scans/${scanId}/start`).then(r => r.data)
export const getScan = (scanId) => api.get(`/scans/${scanId}`).then(r => r.data)
export const listScans = (params) => api.get('/scans', { params }).then(r => r.data)
export const getScanReport = (scanId) => api.get(`/scans/${scanId}/report`).then(r => r.data)
export const getPdfReportUrl = (scanId) => `${import.meta.env.VITE_API_BASE_URL || '/api'}/scans/${scanId}/report/pdf`

// PDF download must go through axios (not a plain <a href>) so the auth
// token is attached - a bare link would otherwise get a 401 now that
// every API route requires login.
export const downloadPdfReport = async (scanId, filename) => {
  const response = await api.get(`/scans/${scanId}/report/pdf`, { responseType: 'blob' })
  const blobUrl = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
  const link = document.createElement('a')
  link.href = blobUrl
  link.setAttribute('download', filename || `HATA_Report_${scanId}.pdf`)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(blobUrl)
}

// --- Dashboard ---
export const getDashboardStats = () => api.get('/dashboard/stats').then(r => r.data)

// --- Emails ---
export const getEmailStatus = () => api.get('/emails/status').then(r => r.data)
export const getOAuthUrl = () => api.get('/emails/oauth-url').then(r => r.data)
export const disconnectEmail = () => api.post('/emails/disconnect').then(r => r.data)
export const startMonitoring = (interval_seconds) => api.post('/emails/start-monitoring', { interval_seconds }).then(r => r.data)
export const stopMonitoring = () => api.post('/emails/stop-monitoring').then(r => r.data)
export const syncNow = () => api.post('/emails/sync-now').then(r => r.data)

// --- Quarantine ---
export const listQuarantine = () => api.get('/quarantine').then(r => r.data)
export const deleteQuarantineItem = (id) => api.delete(`/quarantine/${id}`, { data: { confirm: true } }).then(r => r.data)
export const restoreQuarantineItem = (id) => api.post(`/quarantine/${id}/restore`, { confirm: true }).then(r => r.data)

// --- Notifications ---
export const listNotifications = () => api.get('/notifications').then(r => r.data)
export const markNotificationRead = (id) => api.post(`/notifications/${id}/read`).then(r => r.data)
export const markAllNotificationsRead = () => api.post('/notifications/read-all').then(r => r.data)

// --- Settings ---
export const getSettings = () => api.get('/settings').then(r => r.data)
export const updateSettings = (payload) => api.post('/settings', payload).then(r => r.data)

// --- Threat Intelligence ---
export const getThreatIntel = () => api.get('/threat-intel').then(r => r.data)

// --- Demo ---
export const seedDemoData = () => api.post('/demo/seed').then(r => r.data)
export const clearDemoData = () => api.delete('/demo/clear').then(r => r.data)

export default api
