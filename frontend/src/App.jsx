import React, { useState, useEffect } from 'react';
import Login from './components/Login';
import Dashboard from './components/Dashboard';

export default function App() {
  const [auth, setAuth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('user');

    if (token && user) {
      setAuth({ access_token: token, user: JSON.parse(user) });
    }
    setLoading(false);
  }, []);

  if (loading) return null;

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
      {!auth ? (
        <Login setAuth={setAuth} />
      ) : (
        <Dashboard auth={auth} setAuth={setAuth} />
      )}
    </div>
  );
}