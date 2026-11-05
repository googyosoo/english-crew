import React, { useState } from 'react';
import {
  ArtifactIcon,
  ContextIcon,
  RoutineIcon,
  ShieldIcon,
  FolderIcon,
  CheckIcon
} from './common/Icons';

export default function RightPanel({
  channel,
  contextNote,
  routines,
  deliverable
}) {
  const [activeTab, setActiveTab] = useState('deliverable'); // 'deliverable' | 'context' | 'routine'

  // Determine working directory path based on channel type and unit
  const getWorkspacePath = () => {
    if (channel.type === 'all' || channel.id === 'general') {
      return 'data/workspaces/_공통/';
    }
    const safeCourse = (channel.name || '').replace(/\s+/g, '_');
    const safeUnit = (channel.unit || '1과').replace(/\s+/g, '_');
    return `data/workspaces/${safeCourse}/${safeUnit}`;
  };
  const workspacePath = getWorkspacePath();

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

      {/* Tab Content Area (Scrollable) */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Tab 1: 산출물 미리보기 */}
        {activeTab === 'deliverable' && (
          <div>
            {deliverable ? (
              <div className="space-y-3">
                <div className="pb-2 border-b border-slate-150">
                  <span className="text-[10px] font-semibold tracking-wider text-indigo-600 uppercase bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                    최신 산출물 미리보기
                  </span>
                  <h3 className="text-sm font-bold text-slate-900 mt-2">
                    {deliverable.title}
                  </h3>
                  <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-2">
                    <span>작성: @{deliverable.bot}</span>
                    <span>·</span>
                    <span>검토: @{deliverable.reviewer}</span>
                  </div>
                </div>

                {/* Formatted Content */}
                <div className="bg-slate-50 p-3 rounded-card border border-slate-200 text-xs text-slate-700 space-y-3 leading-relaxed">
                  <div>
                    <h4 className="font-bold text-slate-900 mb-1">연계 성취기준</h4>
                    <ul className="list-disc list-inside space-y-1 text-slate-600">
                      {deliverable.standards.map((std, i) => (
                        <li key={i} className="text-[11px] leading-snug">{std}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="pt-2 border-t border-slate-200">
                    <h4 className="font-bold text-slate-900 mb-1">문항 및 루브릭 개요</h4>
                    <div className="whitespace-pre-wrap font-mono text-[11px] bg-white p-2.5 rounded border border-slate-200 text-slate-800 max-h-64 overflow-y-auto">
                      {deliverable.content}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-64 flex flex-col items-center justify-center text-center p-6 border-2 border-dashed border-slate-200 rounded-card text-slate-400">
                <ArtifactIcon className="w-8 h-8 mb-2 text-slate-300" />
                <p className="text-xs font-medium text-slate-600">선택된 산출물이 없습니다</p>
                <p className="text-[11px] text-slate-400 mt-1">
                  채널에서 작업을 요청하면 생성된 산출물 미리보기가 여기에 표시됩니다.
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
