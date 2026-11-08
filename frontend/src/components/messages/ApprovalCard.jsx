import React, { useState } from 'react';
import { CheckIcon, CrossIcon } from '../common/Icons';

export default function ApprovalCard({ message, onApprovalDecision }) {
  const meta = message.metadata || {};
  const approvalId = meta.approval_id || message.approvalId || message.id;
  const initialStatus = meta.status || message.status || 'pending';
  const question = message.content || message.question || '결재 요청 사항을 확인하고 승인해 주십시오.';

  const [status, setStatus] = useState(initialStatus);
  const [rejecting, setRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [loading, setLoading] = useState(false);

  const handleApprove = async () => {
    setLoading(true);
    try {
      if (onApprovalDecision) {
        await onApprovalDecision(approvalId, 'approved', '');
      }
      setStatus('approved');
    } catch (e) {
      alert(`승인 처리 중 오류: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmReject = async () => {
    const reason = rejectReason.trim() || '수행평가 채점 기준과 문항 배점을 다시 검토해 주세요.';
    setLoading(true);
    try {
      if (onApprovalDecision) {
        await onApprovalDecision(approvalId, 'rejected', reason);
      }
      setStatus('rejected');
      setRejecting(false);
    } catch (e) {
      alert(`반려 처리 중 오류: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-start gap-3 my-3">
      <div className="w-8 h-8 rounded-full bg-purple-100 border border-purple-200 flex items-center justify-center shrink-0 text-sm">
        ⚖️
      </div>
      <div className="flex-1 max-w-[85%]">
        <div className="flex items-center gap-2 mb-1 text-xs text-slate-500">
          <span className="font-semibold text-slate-800">{message.sender || '코디봇'}</span>
          <span>{message.time || message.created_at?.slice(11, 16)}</span>
        </div>

        <div className="bg-white border-2 border-indigo-200 shadow-sm rounded-card p-4 text-slate-800">
          <div className="text-xs font-semibold text-indigo-600 tracking-wider mb-1">
            결재 요청
          </div>
          <p className="text-sm font-bold text-slate-900 leading-snug mb-3">
            {question}
          </p>

          {/* 검사 결과 요약 섹션 (Phase 4-0c) */}
          {(() => {
            const tasks = meta.tasks || [];
            const checkTasks = tasks.filter(t => t.check_info);
            if (checkTasks.length === 0) return null;

            const totalIssues = checkTasks.reduce((acc, t) => acc + (t.check_info.passed ? 0 : (t.check_info.issues?.length || 1)), 0);
            const allPassed = totalIssues === 0;
            const hasRetry = checkTasks.some(t => t.check_info.retry_occurred);

            return (
              <div className="mb-4 p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-700">산출물 품질 검사 결과:</span>
                  <div className="flex items-center gap-1.5">
                    {hasRetry && (
                      <span className="px-2 py-0.5 text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-200 rounded">
                        1차 실패 후 재생성 완료
                      </span>
                    )}
                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded border ${
                      allPassed
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                        : 'bg-amber-50 text-amber-700 border-amber-300'
                    }`}>
                      {allPassed ? '전체 검사 통과' : `경고 ${totalIssues}건`}
                    </span>
                  </div>
                </div>

                <div className="space-y-1 pt-1 border-t border-slate-200/60">
                  {checkTasks.map((t, idx) => {
                    const ci = t.check_info;
                    return (
                      <div key={t.task_id || t.id || idx} className="flex items-start justify-between text-[11px] text-slate-600">
                        <span className="truncate max-w-[70%]">
                          @{t.bot_id || '팀원봇'} - {t.title || '과업'}
                        </span>
                        <span className={ci.passed ? 'text-emerald-600 font-medium' : 'text-amber-600 font-semibold'}>
                          {ci.passed ? (ci.retry_occurred ? '통과 (재생성됨)' : '통과') : `수정 필요 (${ci.issues?.length || 0}건)`}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })()}

          {status === 'pending' && !rejecting && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleApprove}
                disabled={loading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-medium rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
              >
                <CheckIcon className="w-3.5 h-3.5" />
                {loading ? '처리 중...' : '승인'}
              </button>
              <button
                type="button"
                onClick={() => setRejecting(true)}
                disabled={loading}
                className="px-4 py-2 bg-white hover:bg-slate-50 disabled:opacity-50 text-slate-700 border border-slate-300 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5"
              >
                <CrossIcon className="w-3.5 h-3.5" />
                반려
              </button>
            </div>
          )}

          {status === 'pending' && rejecting && (
            <div className="space-y-2 pt-2 border-t border-slate-150">
              <input
                type="text"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="반려 사유를 입력하세요 (예: 문항 난이도 및 루브릭 4단계 보완)"
                className="w-full text-xs p-2 border border-slate-300 rounded focus:outline-none focus:border-indigo-500"
              />
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleConfirmReject}
                  disabled={loading}
                  className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-medium rounded shadow-sm"
                >
                  {loading ? '반려 처리 중...' : '반려 확정 및 재디스패치'}
                </button>
                <button
                  type="button"
                  onClick={() => setRejecting(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded"
                >
                  취소
                </button>
              </div>
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
              반려됨 (재디스패치 진행)
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
