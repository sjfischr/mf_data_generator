import { useEffect, useState } from 'react';
import { getDownloadLinks } from '@/services/api';
import type { DownloadResponse } from '@/services/api';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  jobId: string;
  onReset: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DownloadLinks({ jobId, onReset }: Props) {
  const [data, setData] = useState<DownloadResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchLinks() {
      try {
        const response = await getDownloadLinks(jobId);
        if (!cancelled) setData(response);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : 'Failed to retrieve download links.',
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchLinks();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  // -- loading state --------------------------------------------------------

  if (loading) {
    return (
      <div className="mx-auto max-w-xl text-center">
        <div className="card flex flex-col items-center gap-4 py-12">
          <svg
            className="h-8 w-8 animate-spin text-brand-600"
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
          <p className="text-sm text-slate-500">Loading download links...</p>
        </div>
      </div>
    );
  }

  // -- error state ----------------------------------------------------------

  if (error || !data) {
    return (
      <div className="mx-auto max-w-xl text-center">
        <div className="card py-12">
          <p className="mb-4 text-sm text-red-600">
            {error ?? 'Failed to load download links.'}
          </p>
          <button onClick={onReset} className="btn-primary">
            Go Back
          </button>
        </div>
      </div>
    );
  }

  // -- success --------------------------------------------------------------

  const { urls } = data;

  const files: FileEntry[] = [
    {
      label: 'Appraisal Report',
      type: 'DOCX',
      url: urls.appraisal,
      icon: 'document',
    },
    {
      label: 'Rent Roll',
      type: 'XLSX',
      url: urls.rent_roll,
      icon: 'table',
    },
    ...urls.t12_files.map((url, i) => ({
      label: `T-12 Statement ${i + 1}`,
      type: 'XLSX' as const,
      url,
      icon: 'chart' as IconKind,
    })),
    {
      label: 'Complete Package',
      type: 'ZIP',
      url: urls.complete_package,
      icon: 'archive',
    },
  ];

  return (
    <div className="mx-auto max-w-2xl">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-green-100">
          <svg
            className="h-7 w-7 text-green-600"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
            />
          </svg>
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">
          Appraisal Complete
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Your synthetic appraisal package is ready. Download the files below.
        </p>
      </div>

      {/* Download grid */}
      <div className="card">
        <div className="grid gap-3 sm:grid-cols-2">
          {files.map((file, i) => (
            <a
              key={i}
              href={file.url}
              download
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3.5 transition-all hover:border-brand-300 hover:bg-brand-50 hover:shadow-sm"
            >
              <FileIcon kind={file.icon} />
              <div className="flex-1 min-w-0">
                <p className="truncate text-sm font-medium text-slate-800 group-hover:text-brand-700">
                  {file.label}
                </p>
                <p className="text-xs text-slate-400">{file.type}</p>
              </div>
              <svg
                className="h-4 w-4 flex-shrink-0 text-slate-400 transition-colors group-hover:text-brand-500"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
                />
              </svg>
            </a>
          ))}
        </div>

        {/* Divider + reset */}
        <hr className="my-6 border-slate-200" />

        <div className="flex items-center justify-center gap-4">
          <p className="text-xs text-slate-400">
            Job ID: <span className="font-mono">{jobId}</span>
          </p>
          <button onClick={onReset} className="btn-secondary text-xs">
            <svg
              className="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182"
              />
            </svg>
            Generate Another
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// File entry type & icon helper
// ---------------------------------------------------------------------------

type IconKind = 'document' | 'table' | 'chart' | 'archive';

interface FileEntry {
  label: string;
  type: string;
  url: string;
  icon: IconKind;
}

function FileIcon({ kind }: { kind: IconKind }) {
  const base =
    'flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg';

  switch (kind) {
    case 'document':
      return (
        <span className={`${base} bg-blue-100 text-blue-600`}>
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
            />
          </svg>
        </span>
      );
    case 'table':
      return (
        <span className={`${base} bg-emerald-100 text-emerald-600`}>
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0 1 12 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M12 12v-1.5c0-.621-.504-1.125-1.125-1.125M12 12c0-.621.504-1.125 1.125-1.125m-2.25 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 13.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 13.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125m0 1.5v-1.5m0 0c0-.621.504-1.125 1.125-1.125m0 0c.621 0 1.125.504 1.125 1.125m-2.25 0c-.621 0-1.125.504-1.125 1.125v1.5"
            />
          </svg>
        </span>
      );
    case 'chart':
      return (
        <span className={`${base} bg-amber-100 text-amber-600`}>
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z"
            />
          </svg>
        </span>
      );
    case 'archive':
      return (
        <span className={`${base} bg-purple-100 text-purple-600`}>
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m20.25 7.5-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z"
            />
          </svg>
        </span>
      );
  }
}
