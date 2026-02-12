import { useEffect, useRef, useState, useCallback } from 'react';
import { getStatus } from '@/services/api';
import type { StatusResponse, StepInfo } from '@/services/api';

// ---------------------------------------------------------------------------
// Default step list (used when the API doesn't supply steps)
// ---------------------------------------------------------------------------

const DEFAULT_STEPS: StepInfo[] = [
  { name: 'Validating property data', status: 'pending' },
  { name: 'Generating rent roll', status: 'pending' },
  { name: 'Building T-12 operating statements', status: 'pending' },
  { name: 'Composing appraisal narrative', status: 'pending' },
  { name: 'Compiling final package', status: 'pending' },
];

function deriveSteps(progress: number): StepInfo[] {
  return DEFAULT_STEPS.map((step, i) => {
    const threshold = ((i + 1) / DEFAULT_STEPS.length) * 100;
    const prevThreshold = (i / DEFAULT_STEPS.length) * 100;
    if (progress >= threshold) return { ...step, status: 'completed' };
    if (progress > prevThreshold) return { ...step, status: 'running' };
    return { ...step, status: 'pending' };
  });
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  jobId: string;
  onComplete: (jobId: string) => void;
  onError: (message: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function GenerationProgress({
  jobId,
  onComplete,
  onError,
}: Props) {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const startTime = useRef(Date.now());
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const completedRef = useRef(false);

  // -- elapsed timer --------------------------------------------------------

  useEffect(() => {
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime.current) / 1000));
    }, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // -- polling --------------------------------------------------------------

  const poll = useCallback(async () => {
    if (completedRef.current) return;
    try {
      const data = await getStatus(jobId);
      setStatus(data);

      if (data.status === 'succeeded') {
        completedRef.current = true;
        if (intervalRef.current) clearInterval(intervalRef.current);
        onComplete(jobId);
      } else if (data.status === 'failed') {
        completedRef.current = true;
        if (intervalRef.current) clearInterval(intervalRef.current);
        onError(data.error || 'The generation job failed. Please try again.');
      }
    } catch (err) {
      // Swallow transient network errors -- keep polling
      console.error('Polling error:', err);
    }
  }, [jobId, onComplete, onError]);

  useEffect(() => {
    // Initial fetch immediately
    poll();
    intervalRef.current = setInterval(poll, 5000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [poll]);

  // -- derived data ---------------------------------------------------------

  const progress = status?.progress ?? 0;
  const currentStep = status?.current_step ?? 'Initializing...';
  const steps: StepInfo[] = status?.steps ?? deriveSteps(progress);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  // -- render ---------------------------------------------------------------

  return (
    <div className="mx-auto max-w-xl">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-brand-100">
          <svg
            className="h-7 w-7 animate-spin text-brand-600"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
            />
          </svg>
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">
          Generating Your Appraisal
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          This typically takes 2 -- 5 minutes. Please keep this page open.
        </p>
      </div>

      {/* Card */}
      <div className="card space-y-6">
        {/* Progress bar */}
        <div>
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="font-medium text-slate-700">
              {currentStep}
            </span>
            <span className="tabular-nums text-slate-500">
              {Math.round(progress)}%
            </span>
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-slate-200">
            <div
              className="progress-bar-fill h-full rounded-full bg-gradient-to-r from-brand-500 to-brand-600 transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Step list */}
        <ul className="space-y-3">
          {steps.map((step, i) => (
            <li key={i} className="flex items-start gap-3 text-sm">
              <StepIcon status={step.status} />
              <span
                className={
                  step.status === 'completed'
                    ? 'text-slate-500 line-through'
                    : step.status === 'running'
                      ? 'font-medium text-brand-700'
                      : 'text-slate-400'
                }
              >
                {step.name}
              </span>
            </li>
          ))}
        </ul>

        {/* Elapsed time */}
        <div className="flex items-center justify-center gap-2 rounded-lg bg-slate-50 px-4 py-2.5 text-sm text-slate-500">
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
            />
          </svg>
          <span>
            Elapsed time:{' '}
            <span className="font-medium tabular-nums text-slate-700">
              {formatTime(elapsed)}
            </span>
          </span>
        </div>

        {/* Job ID */}
        <p className="text-center text-xs text-slate-400">
          Job ID: <span className="font-mono">{jobId}</span>
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step icon helper
// ---------------------------------------------------------------------------

function StepIcon({ status }: { status: StepInfo['status'] }) {
  if (status === 'completed') {
    return (
      <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-green-100 text-green-600">
        <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
            clipRule="evenodd"
          />
        </svg>
      </span>
    );
  }

  if (status === 'running') {
    return (
      <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center">
        <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-brand-500" />
      </span>
    );
  }

  if (status === 'failed') {
    return (
      <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-red-100 text-red-500">
        <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </span>
    );
  }

  // pending
  return (
    <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center">
      <span className="h-2 w-2 rounded-full bg-slate-300" />
    </span>
  );
}
