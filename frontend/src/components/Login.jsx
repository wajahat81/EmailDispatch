import React, { useState } from 'react';
import { Mail, Lock } from 'lucide-react';

export default function Login({ setAuth }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      
      if (res.ok) {
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        setAuth(data);
      } else {
        setError(data.detail || 'Login failed');
      }
    } catch (err) {
      setError('Network error occurred.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-blue-50 via-white to-blue-100 font-sans">
      <div className="max-w-sm w-full bg-white/80 backdrop-blur-md rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-blue-100 p-8 transition-all">
        
        <div className="flex justify-center mb-6">
          <img 
  src="/logo.png" 
  alt="Superwise Logo" 
  className="h-24 w-auto mx-auto mb-1" 
            onError={(e) => {
              e.target.style.display = 'none';
              e.target.insertAdjacentHTML('afterend', '<div class="h-12 w-12 bg-blue-100 rounded-xl flex items-center justify-center text-blue-600 font-bold text-xl">L</div>');
            }}
          />
        </div>

        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-center mt-0">
  Superwise Telecoms
</h2>
          <p className="text-sm text-slate-500 mt-2">Please Enter your credentials</p>
        </div>

        {error && (
          <div className="mb-5 p-3 text-sm text-red-700 bg-red-50 rounded-xl border border-red-100 animate-in fade-in slide-in-from-top-2">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Email</label>
            <div className="relative group">
              <Mail className="absolute left-3.5 top-2.5 h-4 w-4 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
              <input
                type="email"
                required
                className="w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 focus:bg-white transition-all duration-200"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Password</label>
            <div className="relative group">
              <Lock className="absolute left-3.5 top-2.5 h-4 w-4 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
              <input
                type="password"
                required
                className="w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 focus:bg-white transition-all duration-200"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-600 to-blue-500 text-white font-medium py-2.5 rounded-xl hover:from-blue-700 hover:to-blue-600 hover:shadow-lg hover:shadow-blue-500/25 active:scale-[0.98] transition-all duration-200 disabled:opacity-70 mt-2"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}