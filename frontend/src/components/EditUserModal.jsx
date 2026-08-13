import React, { useState, useEffect } from 'react';
import { X, Save } from 'lucide-react';

export default function EditUserModal({ token, userToEdit, onClose, onSuccess, setConfirmAction }) {
  const [formData, setFormData] = useState({
    name: userToEdit.name,
    email: userToEdit.email,
    password: '', 
    role: userToEdit.role
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const executeUpdate = async () => {
    setLoading(true);
    setError('');
    try {
      const baseUrl = import.meta.env.VITE_API_URL || '';
      const res = await fetch(`${baseUrl}/api/admin/users/${userToEdit.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      });
      
      if (res.ok) {
        onSuccess();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to update user');
      }
    } catch (err) {
      setError('Network error occurred.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setConfirmAction({
      title: 'Save Changes',
      message: `Are you sure you want to update the profile for ${formData.name}?`,
      isDestructive: false,
      onConfirm: executeUpdate
    });
  };

  const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/30 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl border w-full max-w-md overflow-hidden">
        
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-bold text-slate-800">Edit User Profile</h2>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && <div className="p-3 text-sm text-red-700 bg-red-50 rounded-xl">{error}</div>}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Full Name</label>
            <input type="text" name="name" required value={formData.name} onChange={handleChange} className="w-full px-4 py-2 bg-slate-50 border rounded-xl" />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Email Address</label>
            <input type="email" name="email" required value={formData.email} onChange={handleChange} className="w-full px-4 py-2 bg-slate-50 border rounded-xl" />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">New Password <span className="text-slate-400 font-normal">(Optional)</span></label>
            <input type="password" name="password" value={formData.password} onChange={handleChange} placeholder="Leave blank to keep current" minLength={6} className="w-full px-4 py-2 bg-slate-50 border rounded-xl" />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Role</label>
            <select name="role" value={formData.role} onChange={handleChange} className="w-full px-4 py-2 bg-slate-50 border rounded-xl">
              <option value="employee">Employee</option>
              <option value="admin">Administrator</option>
            </select>
          </div>

          <div className="pt-4 flex justify-end gap-3 border-t mt-2">
            <button type="button" onClick={onClose} className="px-4 py-2.5 text-sm font-medium text-slate-600 border rounded-xl hover:bg-slate-50">Cancel</button>
            <button type="submit" disabled={loading} className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-xl hover:bg-blue-700">
              {loading ? 'Saving...' : <><Save className="w-4 h-4" /> Save Changes</>}
            </button>
          </div>
        </form>
      </div>
    </div>
    
  );
}