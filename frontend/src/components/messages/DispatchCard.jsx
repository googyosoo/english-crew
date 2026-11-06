import React from 'react';
import { CheckIcon } from '../common/Icons';

export default function DispatchCard({ message, onSelectDeliverable }) {
  const meta = message.metadata || {};
  const tasks = meta.tasks || message.tasks || [];
  const title = meta.title || message.title || '디스패치';
  const summary = message.content || meta.summary || '과업 분해 실행 계획';

  return (
    <div className="flex items-start gap-3 my-3">
      <div className="w-8 h-8 rounded-full bg-indigo-100 border border-indigo-200 flex items-center justify-center shrink-0 text-sm">
        🎯
      </div>
      <div className="flex-1 max-w-[85%]">
        <div className="flex items-center gap-2 mb-1 text-xs text-slate-500">
          <span className="font-semibold text-slate-800">{message.sender || '코디봇'}</span>
          <span>{message.time || message.created_at?.slice(11, 16)}</span>
        </div>

        <div className="bg-white border border-slate-200 shadow-sm rounded-card p-4 text-slate-800">
          <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-100">
            <span className="text-sm font-bold text-slate-900 tracking-tight">
              {title}
            </span>
            <span className="text-xs text-slate-400">{summary}</span>
          </div>

          <div className="space-y-2">
            {tasks.map((task, idx) => (
              <div
                key={task.id || idx}
                onClick={() => onSelectDeliverable && onSelectDeliverable(task)}
                className={`flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-150 text-sm transition-all ${
                  onSelectDeliverable ? 'cursor-pointer hover:bg-indigo-50/50 hover:border-indigo-200' : ''
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 text-xs ${
                    task.status === 'done'
                      ? 'bg-emerald-100 text-emerald-600'
                      : task.status === 'failed'
                      ? 'bg-rose-100 text-rose-600'
                      : 'bg-indigo-100 text-indigo-600'
                  }`}>
                    {task.status === 'done' ? <CheckIcon className="w-3.5 h-3.5" /> : '✓'}
                  </span>
                  <span className="font-medium text-slate-800 truncate">{task.title}</span>
                  <span className="text-slate-400">→</span>
                  <span className="text-indigo-600 font-semibold shrink-0">@{task.bot || task.bot_id || task.botName}</span>
                </div>
                <div className="text-xs text-slate-500 bg-white px-2.5 py-1 rounded border border-slate-200 shrink-0 ml-2">
                  {task.deliverable}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
