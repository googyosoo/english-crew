import React from 'react';
import { CheckIcon } from '../common/Icons';

const BOT_NAMES = {
  coordinator: '코디봇',
  assessment: '평가봇',
  curriculum: '교육과정봇',
  lesson: '수업봇',
  record: '기록봇'
};

export default function ReportCard({ message, onSelectDeliverable, onRetryRequest }) {
  const meta = message.metadata || {};
  const tasks = meta.tasks || [];
  const reports = message.reports || [];
  const items = tasks.length > 0 ? tasks : reports;
  const summary = message.content || meta.summary || '작업이 완료되었습니다.';
  const hasFailures = meta.has_failures || items.some(t => t.status === 'failed');

  return (
    <div className="flex items-start gap-3 my-3">
      <div className={`w-8 h-8 rounded-full border flex items-center justify-center shrink-0 text-sm ${
        hasFailures ? 'bg-rose-100 border-rose-200' : 'bg-emerald-100 border-emerald-200'
      }`}>
        {hasFailures ? '⚠️' : '📊'}
      </div>
      <div className="flex-1 max-w-[85%]">
        <div className="flex items-center gap-2 mb-1 text-xs text-slate-500">
          <span className="font-semibold text-slate-800">{message.sender || '코디봇'}</span>
          <span>{message.time || message.created_at?.slice(11, 16)}</span>
        </div>

        <div className={`bg-white border shadow-sm rounded-card p-4 text-slate-800 ${
          hasFailures ? 'border-rose-200' : 'border-slate-200'
        }`}>
          <div className="flex items-center gap-2 pb-2 mb-3 border-b border-slate-100">
            <span className={`w-5 h-5 rounded-full flex items-center justify-center ${
              hasFailures ? 'bg-rose-100 text-rose-600' : 'bg-emerald-100 text-emerald-600'
            }`}>
              {hasFailures ? '!' : <CheckIcon className="w-3.5 h-3.5" />}
            </span>
            <span className="text-sm font-bold text-slate-900">
              {message.title || (hasFailures ? '작업 실패 보고' : '작업 보고')}
            </span>
          </div>

          <div className="space-y-2 mb-3">
            {items.map((item, idx) => {
              const rawBot = item.bot_id || item.bot;
              const botDisplayName = BOT_NAMES[rawBot] || item.botName || rawBot || '평가봇';
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
                    <span className="font-medium text-slate-800 shrink-0">@{botDisplayName}</span>
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

          {/* Rule 3: Retry button for failed tasks */}
          {hasFailures && onRetryRequest && (
            <div className="pt-3 mt-2 border-t border-slate-150 flex items-center justify-end">
              <button
                type="button"
                onClick={() => onRetryRequest(meta.teacher_content || '실패한 과업 재실행 요청')}
                className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
              >
                <span>실패 과업 재시도</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
