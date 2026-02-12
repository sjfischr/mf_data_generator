import { useState, useCallback } from 'react';
import PropertyForm from '@/components/PropertyForm';
import GenerationProgress from '@/components/GenerationProgress';
import DownloadLinks from '@/components/DownloadLinks';
import type { GenerateRequest, GenerateResponse } from '@/services/api';
import { generateAppraisal, getLuckyProperty } from '@/services/api';

// ---------------------------------------------------------------------------
// Application state machine
// ---------------------------------------------------------------------------

type AppState =
  | { view: 'form' }
  | { view: 'processing'; jobId: string }
  | { view: 'complete'; jobId: string }
  | { view: 'error'; message: string };

// ---------------------------------------------------------------------------
// App component
// ---------------------------------------------------------------------------

export default function App() {
  const [state, setState] = useState<AppState>({ view: 'form' });

  // -- handlers -------------------------------------------------------------

  const handleSubmit = useCallback(async (data: GenerateRequest) => {
    try {
      const response: GenerateResponse = await generateAppraisal(data);
      setState({ view: 'processing', jobId: response.job_id });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'An unexpected error occurred.';
      setState({ view: 'error', message });
    }
  }, []);

  const handleLucky = useCallback(async () => {
    try {
      const luckyData = await getLuckyProperty();
      const response: GenerateResponse = await generateAppraisal({
        property_name: luckyData.property_name,
        address: luckyData.address,
        city: luckyData.city,
        state: luckyData.state,
        units: luckyData.units,
        year_built: luckyData.year_built,
        property_type: luckyData.property_type,
      });
      setState({ view: 'processing', jobId: response.job_id });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'An unexpected error occurred.';
      setState({ view: 'error', message });
    }
  }, []);

  const handleComplete = useCallback((jobId: string) => {
    setState({ view: 'complete', jobId });
  }, []);

  const handleError = useCallback((message: string) => {
    setState({ view: 'error', message });
  }, []);

  const handleReset = useCallback(() => {
    setState({ view: 'form' });
  }, []);

  // -- render ---------------------------------------------------------------

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-4xl items-center gap-3 px-4 py-4 sm:px-6 lg:px-8">
          {/* Icon */}
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600 shadow-sm">
            <svg
              className="h-5 w-5 text-white"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3H21m-3.75 3H21"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-slate-900 sm:text-xl">
              Smaug: The Synthetic Multifamily Appraisal/Underwriting Generator
            </h1>
            <p className="hidden text-xs text-slate-500 sm:block">
              AI-powered multifamily appraisal and underwriting packages
            </p>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
        {state.view === 'form' && (
          <div className="fade-in space-y-6">
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <img
                src="/smaug-hero.jpg"
                alt="Smaug-inspired dragon mascot overlooking a multifamily tower"
                className="h-56 w-full object-cover sm:h-72"
              />
              <div className="px-4 py-3 sm:px-6">
                <p className="text-sm text-slate-600">
                  Meet Smaug: your AI co-pilot for synthetic multifamily
                  appraisal and underwriting packages.
                </p>
              </div>
            </div>
            <PropertyForm onSubmit={handleSubmit} onLucky={handleLucky} />
          </div>
        )}

        {state.view === 'processing' && (
          <div className="fade-in">
            <GenerationProgress
              jobId={state.jobId}
              onComplete={handleComplete}
              onError={handleError}
            />
          </div>
        )}

        {state.view === 'complete' && (
          <div className="fade-in">
            <DownloadLinks jobId={state.jobId} onReset={handleReset} />
          </div>
        )}

        {state.view === 'error' && (
          <div className="fade-in">
            <div className="card mx-auto max-w-lg text-center">
              {/* Error icon */}
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-red-100">
                <svg
                  className="h-7 w-7 text-red-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
                  />
                </svg>
              </div>
              <h2 className="mb-2 text-lg font-semibold text-slate-900">
                Generation Failed
              </h2>
              <p className="mb-6 text-sm text-slate-600">{state.message}</p>
              <button onClick={handleReset} className="btn-primary">
                Try Again
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-200 bg-white/60 py-4">
        <p className="text-center text-xs text-slate-400">
          Smaug &mdash; The Synthetic Multifamily Appraisal/Underwriting Generator &mdash; For demonstration &amp;
          development purposes only.
        </p>
      </footer>
    </div>
  );
}
