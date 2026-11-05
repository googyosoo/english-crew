import React, { useState } from 'react';
import { CheckIcon, CrossIcon } from '../common/Icons';

export default function ApprovalCard({ message, onStatusChange }) {
  const [status, setStatus] = useState(message.status || 'pending');

  const handleApprove = () => {
    setStatus('approved');
    if (onStatusChange) onStatusChange(message.id, 'approved');
  };

  const handleReject = () => {
    setStatus('rejected');
    if (onStatusChange) onStatusChange(message.id, 'rejected');
  };

  return (
    <div className="flex items-start gap-3 my-3">
      <div className="w-8 h-8 rounded-full bg-purple-100 border border-purple-200 flex items-center justify-center shrink-0 text-sm">
        ⚖️
      </div>
      <div className="flex-1 max-w-[85%]">
        <div className="flex items-center gap-2 mb-1 text-xs text-slate-500">
          <span className="font-semibold text-slate-800">{message.sender || '코디봇'}</span>
          <span>{message.time}</span>
        </div>

        <div className="bg-white border-2 border-indigo-200 shadow-sm rounded-card p-4 text-slate-800">
          <div className="text-xs font-semibold text-indigo-600 tracking-wider mb-1">
            결재 요청
          </div>
          <p className="text-sm font-bold text-slate-900 leading-snug mb-4">
            {message.question}
          </p>

          {status === 'pending' && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleApprove}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
              >
                <CheckIcon className="w-3.5 h-3.5" />
                승인
              </button>
              <button
                type="button"
                onClick={handleReject}
                className="px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5"
              >
                <CrossIcon className="w-3.5 h-3.5" />
                반려
              </button>
            </div>
          )}

          {status === 'approved' && (
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-semibold rounded-lg">
              <CheckIcon className="w-4 h-4 text-emerald-600" />
              승인됨 (final/ 저장 완료)
            </div>
          )}

          {status === 'rejected' && (
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold rounded-lg">
              <CrossIcon className="w-4 h-4 text-rose-600" />
              반려됨 (재검토 요청)
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
