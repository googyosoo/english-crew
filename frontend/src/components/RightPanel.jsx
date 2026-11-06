import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  ArtifactIcon,
  ContextIcon,
  RoutineIcon,
  ShieldIcon,
  FolderIcon,
  CheckIcon
} from './common/Icons';

const BOT_NAMES = {
  coordinator: '코디봇',
  assessment: '평가봇',
  curriculum: '교육과정봇',
  lesson: '수업봇',
  record: '기록봇'
};

export default function RightPanel({
  channel,
  contextNote,
  routines,
  deliverable,
  workspaceDir
}) {
  const [activeTab, setActiveTab] = useState('deliverable');

  const workspacePath = workspaceDir || channel?.workspace_dir || (
    channel?.type === 'all' || channel?.id === 'general'
      ? 'data/workspaces/_공통/'
      : `data/workspaces/${(channel?.name || '').replace(/\s+/g, '_')}/1과`
  );

  return (
    <aside className="w-[320px] shrink-0 h-screen bg-white border-l border-slate-200 flex flex-col select-none">
      {/* Tab Navigation */}
      <div className="flex border-b border-slate-200 bg-slate-50/60 p-1.5 gap-1 shrink-0">
        <button
          type="button"
          onClick={() => setActiveTab('deliverable')}
          className={`flex-1 py-1.5 px-2 text-xs font-semibold rounded-md transition-all flex items-center justify-center gap-1.5 ${
            activeTab === 'deliverable'
              ? 'bg-white text-indigo-700 shadow-sm border border-slate-200/80'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <ArtifactIcon className="w-3.5 h-3.5" />
          <span>산출물</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('context')}
          className={`flex-1 py-1.5 px-2 text-xs font-semibold rounded-md transition-all flex items-center justify-center gap-1.5 ${
            activeTab === 'context'
              ? 'bg-white text-indigo-700 shadow-sm border border-slate-200/80'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <ContextIcon className="w-3.5 h-3.5" />
          <span>수업 맥락</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('routine')}
          className={`flex-1 py-1.5 px-2 text-xs font-semibold rounded-md transition-all flex items-center justify-center gap-1.5 ${
            activeTab === 'routine'
              ? 'bg-white text-indigo-700 shadow-sm border border-slate-200/80'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <RoutineIcon className="w-3.5 h-3.5" />
          <span>루틴</span>
        </button>
      </div>

      {/* Tab Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Tab 1: 산출물 미리보기 */}
        {activeTab === 'deliverable' && (
          <div>
            {deliverable && deliverable.content ? (
              <div className="space-y-3">
                <div className="pb-2 border-b border-slate-150">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-semibold tracking-wider text-indigo-600 uppercase bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                      산출물 미리보기
                    </span>
                    {deliverable.output_path && (
                      <span className="text-[10px] text-slate-400 font-mono truncate max-w-[140px]" title={deliverable.output_path}>
                        {deliverable.output_path}
                      </span>
                    )}
                  </div>
                  <h3 className="text-sm font-bold text-slate-900 mt-2">
                    {deliverable.title || '작업 산출물'}
                  </h3>
                  <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-2">
                    <span>작성: @{BOT_NAMES[deliverable.bot] || BOT_NAMES[deliverable.bot_id] || deliverable.bot || deliverable.bot_id || '평가봇'}</span>
                    {deliverable.status && (
                      <>
                        <span>·</span>
                        <span className={`font-medium ${deliverable.status === 'done' ? 'text-emerald-600' : 'text-amber-600'}`}>
                          {deliverable.status === 'done' ? '완료' : deliverable.status}
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* Formatted Content with ReactMarkdown */}
                <div className="bg-slate-50 p-3 rounded-card border border-slate-200 text-xs text-slate-700 leading-relaxed max-h-[520px] overflow-y-auto prose prose-sm prose-slate max-w-none">
                  <ReactMarkdown>
                    {deliverable.content}
                  </ReactMarkdown>
                </div>
              </div>
            ) : (
              <div className="h-64 flex flex-col items-center justify-center text-center p-6 border-2 border-dashed border-slate-200 rounded-card text-slate-400">
                <ArtifactIcon className="w-8 h-8 mb-2 text-slate-300" />
                <p className="text-xs font-medium text-slate-600">선택된 산출물이 없습니다</p>
                <p className="text-[11px] text-slate-400 mt-1">
                  작업 보고의 항목을 누르면 해당 마크다운 산출물이 여기에 렌더링됩니다.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: 수업 맥락 */}
        {activeTab === 'context' && contextNote && (
          <div className="space-y-3">
            <div>
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                현재 수업 맥락
              </span>
              <h3 className="text-sm font-bold text-slate-900 mt-1">
                {contextNote.course} · {contextNote.unit}
              </h3>
            </div>

            <div className="bg-slate-50 rounded-card p-3 border border-slate-200 space-y-3 text-xs">
              <div>
                <span className="font-semibold text-slate-700 block mb-1">진도 현황</span>
                <div className="text-slate-600 font-medium bg-white px-2.5 py-1.5 rounded border border-slate-200">
                  {contextNote.progress}
                </div>
              </div>

              <div>
                <span className="font-semibold text-slate-700 block mb-1">핵심 성취기준</span>
                <div className="space-y-1.5">
                  {contextNote.standards.map((std, idx) => (
                    <div key={idx} className="bg-white p-2 rounded border border-slate-200 text-slate-600 leading-snug text-[11px]">
                      {std}
                    </div>
                  ))}
                </div>
              </div>

              {contextNote.notes && (
                <div>
                  <span className="font-semibold text-slate-700 block mb-1">교과 메모</span>
                  <div className="bg-white p-2.5 rounded border border-slate-200 text-slate-600 text-[11px] leading-relaxed">
                    {contextNote.notes}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 3: 루틴 */}
        {activeTab === 'routine' && (
          <div className="space-y-3">
            <div>
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                정기 자동화 루틴 (목업)
              </span>
              <p className="text-xs text-slate-500 mt-0.5">
                지정된 주기마다 팀원봇이 작업을 자동 실행합니다.
              </p>
            </div>

            <div className="space-y-2">
              {routines.map((routine) => (
                <div
                  key={routine.id}
                  className="p-3 rounded-card bg-slate-50 border border-slate-200 hover:border-slate-300 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold text-slate-900">{routine.name}</span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
                        routine.status === '활성'
                          ? 'bg-emerald-100 text-emerald-700 border border-emerald-200'
                          : 'bg-slate-200 text-slate-600'
                      }`}
                    >
                      {routine.status}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 flex items-center justify-between">
                    <span>{routine.schedule}</span>
                    <span className="text-indigo-600 font-medium">@{routine.bot}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Bottom Fixed Cards (2 cards) */}
      <div className="p-3 border-t border-slate-200 bg-slate-50/70 space-y-2 shrink-0">
        {/* Card 1: 학생 데이터 보호 */}
        <div className="p-2.5 rounded-card bg-white border border-slate-200 shadow-sm flex items-start gap-2.5">
          <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600 shrink-0 border border-emerald-100">
            <ShieldIcon className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-slate-900">학생 데이터 보호</span>
              <span className="text-[9px] bg-emerald-100 text-emerald-700 px-1 py-0.2 rounded font-semibold">
                안전
              </span>
            </div>
            <p className="text-[11px] text-slate-500 leading-tight mt-0.5">
              실명은 로컬에만 저장, AI에는 번호로 전송
            </p>
          </div>
        </div>

        {/* Card 2: 작업 폴더 */}
        <div className="p-2.5 rounded-card bg-white border border-slate-200 shadow-sm flex items-start gap-2.5">
          <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600 shrink-0 border border-indigo-100">
            <FolderIcon className="w-4 h-4" />
          </div>
          <div className="min-w-0 flex-1">
            <span className="text-xs font-bold text-slate-900">작업 폴더</span>
            <p className="text-[11px] font-mono text-slate-600 truncate mt-0.5" title={workspacePath}>
              {workspacePath}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
