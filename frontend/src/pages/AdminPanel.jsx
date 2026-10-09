import React, { useEffect, useState, useCallback } from 'react'
import { Users, Shield, Clock, Search, Trash2, Edit2, AlertCircle } from 'lucide-react'
import { listUsers, deleteUser, updateUserRole } from '../services/api.js'
import ErrorPanel from '../components/common/ErrorPanel.jsx'
import { useAuth } from '../context/AuthContext.jsx'

export default function AdminPanel() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [actionError, setActionError] = useState(null)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const data = await listUsers()
      setUsers(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleDelete = async (id, username) => {
    if (!window.confirm(`Are you sure you want to delete operator @${username}? This cannot be undone.`)) return
    setActionError(null)
    try {
      await deleteUser(id)
      setUsers(users.filter(u => u.id !== id))
    } catch (err) {
      setActionError(err.message)
    }
  }

  const handleRoleChange = async (id, currentRole) => {
    const newRole = currentRole === 'admin' ? 'analyst' : 'admin'
    if (!window.confirm(`Change role to ${newRole.toUpperCase()}?`)) return
    setActionError(null)
    try {
      const updatedUser = await updateUserRole(id, newRole)
      setUsers(users.map(u => u.id === id ? updatedUser : u))
    } catch (err) {
      setActionError(err.message)
    }
  }

  if (error) return <ErrorPanel message={error} onRetry={load} />

  const filteredUsers = users.filter(u => 
    u.username?.toLowerCase().includes(search.toLowerCase()) || 
    u.full_name?.toLowerCase().includes(search.toLowerCase()) ||
    u.role?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="glass rounded-2xl p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <Shield className="w-6 h-6 text-hata-accent" />
            <div>
              <h2 className="text-lg font-bold text-hata-text">System Administration</h2>
              <p className="text-xs text-hata-muted mt-0.5">Manage operator accounts, roles, and access</p>
            </div>
          </div>
          <div className="relative">
            <Search className="w-4 h-4 text-hata-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search operators..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="focus-ring pl-9 pr-4 py-2 bg-hata-panel2 border border-hata-border rounded-lg text-sm text-hata-text w-full sm:w-64"
            />
          </div>
        </div>

        {actionError && (
          <div className="flex items-center gap-2 text-xs text-risk-critical bg-risk-critical/10 border border-risk-critical/30 rounded-lg px-3 py-2.5 mb-4">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{actionError}</span>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center p-12 text-hata-muted">
            <Clock className="w-5 h-5 animate-spin mr-2" /> Loading operators...
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-hata-border">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-hata-panel2/50 text-xs text-hata-muted uppercase">
                <tr>
                  <th className="px-4 py-3 font-semibold">Operator</th>
                  <th className="px-4 py-3 font-semibold">Role</th>
                  <th className="px-4 py-3 font-semibold">ID</th>
                  <th className="px-4 py-3 font-semibold">Last Login</th>
                  <th className="px-4 py-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hata-border/50">
                {filteredUsers.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="px-4 py-8 text-center text-hata-muted text-xs">
                      No operators found.
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((u) => {
                    const isSelf = u.id === currentUser?.id
                    return (
                      <tr key={u.id} className={`transition-colors ${isSelf ? 'bg-hata-accent/5' : 'hover:bg-white/5'}`}>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-hata-accent/20 to-hata-accent flex items-center justify-center text-xs font-bold text-hata-bg">
                              {u.username.substring(0, 2).toUpperCase()}
                            </div>
                            <div>
                              <div className="font-semibold text-hata-text flex items-center gap-2">
                                {u.full_name}
                                {isSelf && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-hata-accent/20 text-hata-accent font-bold uppercase">You</span>}
                              </div>
                              <div className="text-[11px] text-hata-muted">@{u.username}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase border ${
                            u.role === 'admin' 
                              ? 'bg-risk-critical/10 border-risk-critical/30 text-risk-critical' 
                              : 'bg-hata-accent/15 border-hata-accent/30 text-hata-accent'
                          }`}>
                            {u.role}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-[11px] font-mono text-hata-muted">
                          {u.id}
                        </td>
                        <td className="px-4 py-3 text-xs text-hata-text">
                          {u.last_login_at ? (
                            <div className="flex flex-col">
                              <span>{new Date(u.last_login_at).toLocaleDateString()}</span>
                              <span className="text-[10px] text-hata-muted">{new Date(u.last_login_at).toLocaleTimeString()}</span>
                            </div>
                          ) : (
                            <span className="text-hata-muted italic">Never</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end gap-2">
                            <button
                              onClick={() => handleRoleChange(u.id, u.role)}
                              disabled={isSelf}
                              title={isSelf ? "Cannot change own role" : `Change role to ${u.role === 'admin' ? 'Analyst' : 'Admin'}`}
                              className="focus-ring p-1.5 rounded-md text-hata-text hover:bg-hata-accent hover:text-hata-bg transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-hata-text"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDelete(u.id, u.username)}
                              disabled={isSelf}
                              title={isSelf ? "Cannot delete own account" : "Delete Operator"}
                              className="focus-ring p-1.5 rounded-md text-risk-critical hover:bg-risk-critical hover:text-white transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-risk-critical"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
