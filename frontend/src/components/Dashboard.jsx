import React, { useState, useEffect, useRef } from 'react';
import { LogOut, Plus, ShieldCheck, User as UserIcon, MessageSquare, UserPlus, Edit2, Trash2, Search, Calendar, XCircle, KeyRound } from 'lucide-react';
import EmailModal from './EmailModal';
import AddUserModal from './AddUserModal';
import EditUserModal from './EditUserModal';
import ConfirmModal from './ConfirmModal';
import ChangePasswordModal from './ChangePasswordModal';

export default function Dashboard({ auth, setAuth }) {
  const { user, access_token } = auth;
  
  const [activeTab, setActiveTab] = useState('emails'); 
  const [logs, setLogs] = useState([]);
  const [usersList, setUsersList] = useState([]);
  
  const [filterDate, setFilterDate] = useState('');
  const [filterSender, setFilterSender] = useState('');
  
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);
  const [isAddUserModalOpen, setIsAddUserModalOpen] = useState(false);
  const [isChangePasswordOpen, setIsChangePasswordOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [confirmAction, setConfirmAction] = useState(null); 
  const [page, setPage] = useState(0);
  const pageSize = 20;

  // --- 15-MINUTE INACTIVITY TRACKER ---
  const timeoutRef = useRef(null);

  const handleInactivityLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setAuth(null);
  };

  const resetTimer = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    
    timeoutRef.current = setTimeout(() => {
      handleInactivityLogout();
    }, 15 * 60 * 1000); 
  };

  useEffect(() => {
    const activityEvents = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];
    
    activityEvents.forEach(event => window.addEventListener(event, resetTimer));
    
    resetTimer();

    return () => {
      activityEvents.forEach(event => window.removeEventListener(event, resetTimer));
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);
  // ------------------------------------

  const fetchLogs = async () => {
    try {
      const baseUrl = import.meta.env.VITE_API_URL || '';
      const offset = page * pageSize;
      const res = await fetch(`${baseUrl}/api/emails?limit=${pageSize}&offset=${offset}`, { 
        headers: { Authorization: `Bearer ${access_token}` } 
      });
      if (res.ok) setLogs(await res.json());
    } catch (err) { console.error('Failed to fetch logs', err); }
  };

  useEffect(() => {
    if (activeTab === 'emails') {
      fetchLogs();
    } else {
      fetchUsers();
    }
  }, [activeTab, page]); 

  const fetchUsers = async () => {
    if (user.role !== 'admin') return;
    try {
      const baseUrl = import.meta.env.VITE_API_URL || '';
      const res = await fetch(`${baseUrl}/api/admin/users`, { headers: { Authorization: `Bearer ${access_token}` } });
      if (res.ok) setUsersList(await res.json());
    } catch (err) { console.error('Failed to fetch users', err); }
  };

  useEffect(() => {
    if (activeTab === 'emails') {
      fetchLogs();
    } else {
      fetchUsers();
    }
  }, [activeTab]);

  useEffect(() => {
    const intervalId = setInterval(() => {
      if (activeTab === 'emails') fetchLogs();
    }, 5000);
    return () => clearInterval(intervalId);
  }, [activeTab]);

  const handleLogout = () => {
    setConfirmAction({
      title: 'Confirm Logout',
      message: 'Are you sure you want to securely log out of your session?',
      isDestructive: true,
      onConfirm: () => {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setAuth(null);
      }
    });
  };

  const handleDeleteUser = (userId, userName) => {
    setConfirmAction({
      title: 'Delete User',
      message: `Are you sure you want to permanently delete ${userName}? All their associated emails will also be deleted. This cannot be undone.`,
      isDestructive: true,
      onConfirm: async () => {
        try {
          const baseUrl = import.meta.env.VITE_API_URL || '';
          await fetch(`${baseUrl}/api/admin/users/${userId}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${access_token}` }
          });
          setConfirmAction(null);
          fetchUsers(); 
        } catch (err) {
          alert('Failed to delete user.');
        }
      }
    });
  };

  const filteredLogs = logs.filter((log) => {
    let matchesDate = true;
    let matchesSender = true;

    if (filterDate) {
      const logDate = new Date(log.created_at).toISOString().split('T')[0];
      matchesDate = logDate === filterDate;
    }

    if (filterSender && user.role === 'admin') {
      matchesSender = log.sender_name.toLowerCase().includes(filterSender.toLowerCase());
    }

    return matchesDate && matchesSender;
  });

  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      <header className="bg-white border-b border-blue-100 shadow-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          
          <div className="flex items-center gap-6">
            <div className="flex flex-col justify-center">
              <img src="/logo.png" alt="Logo" className="h-8 w-auto object-contain" onError={(e) => e.target.style.display = 'none'} />
              <span className="text-[10px] font-semibold text-slate-400 tracking-wider uppercase mt-0.5">
                Superwise International
              </span>
            </div>

            <div className="hidden sm:flex items-center gap-2 pl-1">
              <div className="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center">
                <UserIcon className="w-4 h-4 text-blue-600" />
              </div>
              <div className="leading-tight">
                <div className="text-sm font-semibold text-slate-800">{user.name}</div>
                <div className="text-[11px] text-slate-400 capitalize">{user.role}</div>
              </div>
              <button
                onClick={() => setIsChangePasswordOpen(true)}
                className="ml-1 p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                title="Change Password"
              >
                <KeyRound className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="h-6 w-px bg-slate-200 hidden sm:block"></div>
            
            {user.role === 'admin' ? (
              <div className="flex gap-2">
                <button 
                  onClick={() => setActiveTab('emails')}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${activeTab === 'emails' ? 'bg-blue-50 text-blue-700' : 'text-slate-500 hover:bg-slate-50'}`}
                >
                  Email Logs
                </button>
                <button 
                  onClick={() => setActiveTab('users')}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${activeTab === 'users' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-500 hover:bg-slate-50'}`}
                >
                  Manage Users
                </button>
              </div>
            ) : (
              <div className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-xs font-semibold flex items-center gap-1.5"><UserIcon className="w-4 h-4" /> Employee Dashboard</div>
            )}
          </div>

          <div className="flex items-center gap-3">
            {activeTab === 'users' && user.role === 'admin' ? (
              <button onClick={() => setIsAddUserModalOpen(true)} className="flex items-center gap-2 bg-white border border-slate-200 text-slate-700 px-4 py-2 rounded-xl text-sm font-medium hover:bg-slate-50 transition-all">
                <UserPlus className="h-4 w-4 text-indigo-500" />
                <span className="hidden sm:inline">Add User</span>
              </button>
            ) : (
              <button onClick={() => setIsEmailModalOpen(true)} className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-blue-500 text-white px-4 py-2 rounded-xl text-sm font-medium hover:shadow-lg transition-all active:scale-95">
                <Plus className="h-4 w-4" />
                <span className="hidden sm:inline">Compose Email</span>
              </button>
            )}
            
            <button onClick={handleLogout} className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all" title="Logout">
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        
        {activeTab === 'emails' && (
          <div className="space-y-4">
            
            {user.role === 'admin' && (
              <div className="bg-white p-4 rounded-2xl shadow-sm border border-blue-50 flex flex-wrap gap-4 items-end animate-in fade-in">
                
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1.5 uppercase tracking-wider">Date</label>
                  <div className="relative group">
                    <Calendar className="absolute left-3 top-2.5 h-4 w-4 text-slate-400 group-focus-within:text-blue-500" />
                    <input
                      type="date"
                      value={filterDate}
                      onChange={(e) => setFilterDate(e.target.value)}
                      className="pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:bg-white transition-all text-slate-700"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1.5 uppercase tracking-wider">Sender Name</label>
                  <div className="relative group">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400 group-focus-within:text-blue-500" />
                    <input
                      type="text"
                      placeholder="e.g. John Doe"
                      value={filterSender}
                      onChange={(e) => setFilterSender(e.target.value)}
                      className="pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:bg-white transition-all w-60 text-slate-700"
                    />
                  </div>
                </div>

                {(filterDate || filterSender) && (
                  <button
                    onClick={() => { setFilterDate(''); setFilterSender(''); }}
                    className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-slate-500 bg-slate-100 hover:bg-slate-200 hover:text-slate-700 rounded-xl transition-colors h-[38px]"
                  >
                    <XCircle className="w-4 h-4" />
                    Clear Filters
                  </button>
                )}
              </div>
            )}

            <div className="bg-white rounded-2xl shadow-sm border border-blue-50 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50/50 border-b border-slate-100 text-slate-500">
                    <tr>
                      <th className="px-6 py-4 font-medium">Date</th>
                      <th className="px-6 py-4 font-medium">Subject</th>
                      {user.role === 'admin' && <th className="px-6 py-4 font-medium">Sender</th>}
                      <th className="px-6 py-4 font-medium">Receiver Response</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredLogs.length === 0 ? (
                      <tr>
                        <td colSpan={user.role === 'admin' ? 4 : 3} className="px-6 py-12 text-center text-slate-400">
                          {logs.length > 0 ? 'No emails match your current filters.' : 'No emails yet.'}
                        </td>
                      </tr>
                    ) : (
                      filteredLogs.map((log) => (
                        <tr key={log.id} className="hover:bg-blue-50/40 align-top">
                          <td className="px-6 py-4 text-slate-500">{new Date(log.created_at).toLocaleDateString()}</td>
                          <td className="px-6 py-4 font-medium">{log.title}</td>
                          {user.role === 'admin' && (
                            <td className="px-6 py-4">
                              <div className="font-medium text-slate-800">{log.sender_name}</div>
                              <div className="text-xs text-slate-400">{log.sender_original_email}</div>
                            </td>
                          )}
                          <td className="px-6 py-4">
                            {log.response_text ? (
                              <div className="bg-slate-50 p-3 rounded-lg border text-xs whitespace-pre-wrap max-h-32 overflow-y-auto">
                                {log.response_text}
                              </div>
                            ) : (
                              <span className="text-slate-400 italic text-xs">Waiting for reply...</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
                <div className="flex items-center justify-between px-2 pt-4">
              <button
                onClick={() => setPage((prev) => Math.max(prev - 1, 0))}
                disabled={page === 0}
                className="px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 disabled:opacity-40 transition-colors"
              >
                Previous
              </button>
              <span className="text-sm text-slate-500 font-medium">Page {page + 1}</span>
              <button
                onClick={() => setPage((prev) => prev + 1)}
                disabled={logs.length < pageSize}
                className="px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 disabled:opacity-40 transition-colors"
              >
                Next
              </button>
            </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'users' && user.role === 'admin' && (
          <div className="bg-white rounded-2xl shadow-sm border border-indigo-50 overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50/50 border-b border-slate-100 text-slate-500">
                <tr>
                  <th className="px-6 py-4 font-medium">Full Name</th>
                  <th className="px-6 py-4 font-medium">Email Address</th>
                  <th className="px-6 py-4 font-medium">System Role</th>
                  <th className="px-6 py-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {usersList.map((u) => (
                  <tr key={u.id} className="hover:bg-indigo-50/30 transition-colors">
                    <td className="px-6 py-4 font-medium text-slate-800">{u.name}</td>
                    <td className="px-6 py-4 text-slate-500">{u.email}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-md text-xs font-semibold capitalize
                        ${u.role === 'admin' ? 'bg-indigo-50 text-indigo-700' : 'bg-blue-50 text-blue-700'}`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 flex justify-end gap-2">
                      {u.id !== user.id ? (
                        <>
                          <button onClick={() => setEditingUser(u)} className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Edit User">
                            <Edit2 className="w-4 h-4" />
                          </button>
                          
                          <button onClick={() => handleDeleteUser(u.id, u.name)} className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="Delete User">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </>
                      ) : (
                        <span className="text-xs font-medium text-slate-400 bg-slate-100 px-2.5 py-1 rounded-md flex items-center">
                          Current User
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

      </main>

      {isEmailModalOpen && (
        <EmailModal token={access_token} userRole={user.role} onClose={() => setIsEmailModalOpen(false)} onSuccess={() => { setIsEmailModalOpen(false); fetchLogs(); }} />
      )}

      {isAddUserModalOpen && (
        <AddUserModal token={access_token} onClose={() => setIsAddUserModalOpen(false)} setConfirmAction={setConfirmAction} onSuccess={() => { setIsAddUserModalOpen(false); setConfirmAction(null); fetchUsers(); }} />
      )}

      {editingUser && (
        <EditUserModal token={access_token} userToEdit={editingUser} onClose={() => setEditingUser(null)} setConfirmAction={setConfirmAction} onSuccess={() => { setEditingUser(null); setConfirmAction(null); fetchUsers(); }} />
      )}

      {isChangePasswordOpen && (
        <ChangePasswordModal token={access_token} onClose={() => setIsChangePasswordOpen(false)} />
      )}

      {confirmAction && (
        <ConfirmModal
          title={confirmAction.title}
          message={confirmAction.message}
          isDestructive={confirmAction.isDestructive}
          onConfirm={confirmAction.onConfirm}
          onCancel={() => setConfirmAction(null)}
        />
      )}
    </div>

  );
}