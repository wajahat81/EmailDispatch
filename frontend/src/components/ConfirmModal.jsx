import React from 'react';
import { AlertTriangle, CheckCircle2, X } from 'lucide-react';

export default function ConfirmModal({ title, message, onConfirm, onCancel, isDestructive = false }) {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-100 w-full max-w-sm overflow-hidden transform transition-all animate-in zoom-in-95 duration-200">
        
        <div className="p-6 text-center">
          <div className={`mx-auto flex h-14 w-14 items-center justify-center rounded-full mb-4
            ${isDestructive ? 'bg-red-50 text-red-500' : 'bg-blue-50 text-blue-500'}`}>
            {isDestructive ? <AlertTriangle className="h-7 w-7" /> : <CheckCircle2 className="h-7 w-7" />}
          </div>
          
          <h3 className="text-xl font-bold text-slate-800 mb-2">{title}</h3>
          <p className="text-sm text-slate-500 leading-relaxed">{message}</p>
        </div>

        <div className="px-6 py-4 bg-slate-50/50 border-t border-slate-100 flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={`flex-1 px-4 py-2.5 text-sm font-medium text-white rounded-xl shadow-sm transition-all active:scale-95
              ${isDestructive 
                ? 'bg-blue-600 hover:bg-blue-700 hover:shadow-red-500/25' 
                : 'bg-blue-600 hover:bg-blue-700 hover:shadow-blue-500/25'}`}
          >
            Yes, Confirm
          </button>
        </div>

      </div>
    </div>
  );
}