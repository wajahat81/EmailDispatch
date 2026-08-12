import React, { useState, useEffect } from 'react';
import { LogOut, Plus, ShieldCheck, User as UserIcon, RefreshCw, MessageSquare } from 'lucide-react';
import EmailModal from './EmailModal';

export default function Dashboard({ auth, setAuth }) {
  const [logs, setLogs] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const { user, access_token } = auth;

  const fetchLogs = async () => {
    try {
      const res = await fetch('/api/emails', {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      if (res.ok) {
        setLogs(await res.json());
      }
    } catch (err) {
      console.error('Failed to fetch logs', err);
    }
  };

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      const res = await fetch('/api/emails/sync', {
        method: 'POST',
        headers: { Authorization: `Bearer ${access_token}` },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.synced > 0) alert(`Successfully synced ${data.synced} new replies!`);
        fetchLogs();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSyncing(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setAuth(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      <header className="bg-white border-b border-blue-100 shadow-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">

          <div className="flex items-center gap-6">
            {/* Logo Placeholder */}
            <img
              src="/logo.png"
              alt="Logo"
              className="h-8 w-auto object-contain"
              onError={(e) => e.target.style.display = 'none'}
            />

            <div className="h-6 w-px bg-slate-200 hidden sm:block"></div>

            <div className="flex items-center gap-3">
              <div className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 capitalize tracking-wide
                ${user.role === 'admin' ? 'bg-indigo-50 text-indigo-700' : 'bg-blue-50 text-blue-700'}
              `}>
                {user.role === 'admin' ? <ShieldCheck className="w-4 h-4" /> : <UserIcon className="w-4 h-4" />}
                {user.role}
              </div>
              <span className="text-sm font-medium text-slate-600 hidden sm:block">
                Welcome, {user.name}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Sync Button (Available to both Admins and Employees) */}
            <button
              onClick={handleSync}
              disabled={isSyncing}
              className="flex items-center gap-2 bg-white border border-slate-200 text-slate-700 px-4 py-2 rounded-xl text-sm font-medium hover:bg-slate-50 transition-all duration-200 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${isSyncing ? 'animate-spin text-blue-500' : ''}`} />
              <span className="hidden sm:inline">{isSyncing ? 'Syncing...' : 'Sync Replies'}</span>
            </button>

            {/* Compose Button */}
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-blue-500 text-white px-4 py-2 rounded-xl text-sm font-medium hover:shadow-lg hover:shadow-blue-500/25 active:scale-95 transition-all duration-200"
            >
              <Plus className="h-4 w-4" />
              <span className="hidden sm:inline">Compose Email</span>
            </button>

            <button
              onClick={handleLogout}
              className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all duration-200"
              title="Logout"
            >
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="bg-white rounded-2xl shadow-[0_2px_12px_rgb(0,0,0,0.03)] border border-blue-50 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50/50 border-b border-slate-100 text-slate-500">
                <tr>
                  <th className="px-6 py-4 font-medium">Date</th>
                  <th className="px-6 py-4 font-medium">Title</th>
                  {/* Sender column only visible to Admins */}
                  {user.role === 'admin' && <th className="px-6 py-4 font-medium">Sender</th>}
                  <th className="px-6 py-4 font-medium">Receiver Response</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={user.role === 'admin' ? 4 : 3} className="px-6 py-12 text-center text-slate-400">
                      <div className="flex flex-col items-center justify-center">
                        <div className="h-12 w-12 bg-blue-50 rounded-full flex items-center justify-center mb-3">
                          <MessageSquare className="h-5 w-5 text-blue-400" />
                        </div>
                        <p>No emails or responses yet.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-blue-50/40 transition-colors duration-150 group align-top">
                      <td className="px-6 py-4 text-slate-500 whitespace-nowrap">
                        {new Date(log.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                      </td>

                      <td className="px-6 py-4 font-medium text-slate-800">{log.title}</td>

                      {/* Sender details only visible to Admins */}
                      {user.role === 'admin' && (
                        <td className="px-6 py-4">
                          <div className="text-slate-800 font-medium">{log.sender_name}</div>
                          <div className="text-slate-400 text-xs mt-0.5">{log.sender_original_email}</div>
                        </td>
                      )}

                      {/* Response Column */}
                      <td className="px-6 py-4">
                        {log.response_text ? (
                          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-slate-700 text-xs whitespace-pre-wrap max-h-32 overflow-y-auto">
                            <div className="flex items-center gap-1.5 font-semibold text-blue-600 mb-1.5">
                              <MessageSquare className="h-3.5 w-3.5" /> Reply Received
                            </div>
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
          </div>
        </div>
      </main>

      {isModalOpen && (
        <EmailModal
          token={access_token}
          userRole={user.role}
          onClose={() => setIsModalOpen(false)}
          onSuccess={() => {
            setIsModalOpen(false);
            fetchLogs();
          }}
        />
      )}
    </div>
  );
}