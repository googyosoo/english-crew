import React from 'react';
import { CheckIcon } from '../common/Icons';

export default function ReportCard({ message }) {
  return (
    <div className="flex items-start gap-3 my-3">
      <div className="w-8 h-8 rounded-full bg-emerald-100 border border-emerald-200 flex items-center justify-center shrink-0 text-sm">
        📊
      </div>
      <div className="flex-1 max-w-[85%]">
        <div className="flex items-center gap-2 mb-1 text-xs text-slate-500">
          <span className="font-semibold text-slate-800">{message.sender || '코디봇'}</span>
          <span>{message.time}</span>
        </div>

        <div className="bg-white border border-slate-200 shadow-sm rounded-card p-4 text-slate-800">
          <div className="flex items-center gap-2 pb-2 mb-3 border-b border-slate-100">
            <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">
              <CheckIcon className="w-3.5 h-3.5" />
            </span>
            <span className="text-sm font-bold text-slate-900">
              {message.title || '작업 보고'}
            </span>
          </div>

          <div className="space-y-2 mb-3">
            {message.reports && message.reports.map((report, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-150 text-sm"
              >
                <div className="flex items-center gap-2">
                  <CheckIcon className="w-4 h-4 text-emerald-600" />
                  <span className="font-medium text-slate-800">@{report.botName}</span>
                  <span className="text-slate-400">→</span>
                  <span className="text-slate-600">{report.text}</span>
                </div>
                <span className="px-2 py-0.5 text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
                  {report.count}건
                </span>
              </div>
            ))}
          </div>

          {message.note && (
            <p className="text-xs text-slate-500 pt-2 border-t border-slate-100">
              {message.note}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
