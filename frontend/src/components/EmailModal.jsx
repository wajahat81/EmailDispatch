import React, { useState } from 'react';
import { X, Send } from 'lucide-react';

export default function EmailModal({ token, userRole, onClose, onSuccess }) {
  const [title, setTitle] = useState('');
  const [comments, setComments] = useState('');
  const [loading, setLoading] = useState(false);

  const senderEmail = 'nabeel@superwise.site';
  const receiverEmail = 'claims@mjvlaw.co.uk';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const baseUrl = import.meta.env.VITE_API_URL || '';
      const res = await fetch(`${baseUrl}/api/emails/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title, comments }),
      });
      if (res.ok) {
        onSuccess();
      } else {
        alert('Failed to send email');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/30 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl border border-blue-100 w-full max-w-lg overflow-hidden transform transition-all animate-in zoom-in-95 duration-200">
        
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-white">
          <h2 className="text-lg font-bold text-slate-800">Compose Email</h2>
          <button 
            onClick={onClose} 
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          
          {userRole === 'admin' && (
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Routing From</label>
                <input
                  type="text"
                  disabled
                  value={senderEmail}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-500 cursor-not-allowed"
                />
              </div>
              <div className="flex-1">
                <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Routing To</label>
                <input
                  type="text"
                  disabled
                  value={receiverEmail}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-500 cursor-not-allowed"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Subject</label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Weekly Report Updates"
              className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 focus:bg-white transition-all duration-200"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Message Body</label>
            <textarea
              required
              rows={5}
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              placeholder="Enter the details here..."
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 focus:bg-white transition-all duration-200 resize-none leading-relaxed"
            />
          </div>

          <div className="pt-4 flex justify-end gap-3 border-t border-slate-100 mt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 hover:text-slate-900 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-500 rounded-xl hover:from-blue-700 hover:to-blue-600 hover:shadow-md hover:shadow-blue-500/25 active:scale-95 transition-all duration-200 disabled:opacity-70"
            >
              {loading ? (
                'Sending...'
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Send
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}