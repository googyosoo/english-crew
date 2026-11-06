import React from 'react';
import { CheckIcon } from '../common/Icons';

export default function ReportCard({ message, onSelectDeliverable }) {
  const meta = message.metadata || {};
  const tasks = meta.tasks || [];
  const reports = message.reports || [];
  const items = tasks.length > 0 ? tasks : reports;
  const summary = message.content || meta.summary || '작업이 완료되었습니다.';

  return (
    <div className="flex items-start gap-3 my-3">
      <div className="w-8 h-8 rounded-full bg-emerald-100 border border-emerald-200 flex items-center justify-center shrink-0 text-sm">
        📊
      </div>
      <div className="flex-1 max-w-[85%]">
        <div className="flex items-center gap-2 mb-1 text-xs text-slate-500">
          <span className="font-semibold text-slate-800">{message.sender || '코디봇'}</span>
          <span>{message.time || message.created_at?.slice(11, 16)}</span>
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
            {items.map((item, idx) => {
              const botId = item.bot_id || item.bot || item.botName;
              const title = item.title || item.text || '작업 항목';
              const isFailed = item.status === 'failed';
              const isDone = item.status === 'done';

              return (
                <div
                  key={item.task_id || item.id || idx}
                  onClick={() => onSelectDeliverable && onSelectDeliverable(item)}
                  className={`flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-150 text-sm transition-all ${
                    onSelectDeliverable ? 'cursor-pointer hover:bg-emerald-50/50 hover:border-emerald-200' : ''
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className={`w-4 h-4 rounded-full flex items-center justify-center shrink-0 text-xs ${
                      isFailed ? 'bg-rose-100 text-rose-600' : 'bg-emerald-100 text-emerald-600'
                    }`}>
                      {isFailed ? '✕' : <CheckIcon className="w-3 h-3 text-emerald-600" />}
                    </span>
                    <span className="font-medium text-slate-800 shrink-0">@{botId}</span>
                    <span className="text-slate-400">→</span>
                    <span className="text-slate-600 truncate">{title}</span>
                  </div>
                  <span className={`px-2 py-0.5 text-xs font-semibold rounded-full border shrink-0 ml-2 ${
                    isFailed
                      ? 'bg-rose-50 text-rose-700 border-rose-200'
                      : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  }`}>
                    {isFailed ? '실패' : isDone ? '완료' : '검토완료'}
                  </span>
                </div>
              );
            })}
          </div>

          {summary && (
            <p className="text-xs text-slate-600 pt-2 border-t border-slate-100 whitespace-pre-wrap leading-relaxed">
              {summary}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
