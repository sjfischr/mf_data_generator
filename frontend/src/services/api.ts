const API_BASE = import.meta.env.VITE_API_URL || '/api';

// ---------------------------------------------------------------------------
// Request / Response interfaces
// ---------------------------------------------------------------------------

export interface GenerateRequest {
  address: string;
  city: string;
  state: string;
  units: number;
  year_built: number;
  property_type: 'garden-style' | 'mid-rise' | 'high-rise';
}

export interface GenerateResponse {
  job_id: string;
  status: string;
}

export interface StatusResponse {
  job_id: string;
  status: 'pending' | 'running' | 'succeeded' | 'failed';
  progress: number;
  current_step?: string;
  steps?: StepInfo[];
  error?: string;
}

export interface StepInfo {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
}

export interface DownloadResponse {
  status: string;
  urls: {
    appraisal: string;
    rent_roll: string;
    t12_files: string[];
    complete_package: string;
  };
}

// ---------------------------------------------------------------------------
// Error class
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...options.headers,
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      body = await response.text();
    }
    throw new ApiError(
      `Request failed: ${response.status} ${response.statusText}`,
      response.status,
      body,
    );
  }

  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Public API functions
// ---------------------------------------------------------------------------

/**
 * Submit a new appraisal generation job.
 */
export async function generateAppraisal(
  data: GenerateRequest,
): Promise<GenerateResponse> {
  return request<GenerateResponse>('/generate', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Poll for job status & progress.
 */
export async function getStatus(jobId: string): Promise<StatusResponse> {
  return request<StatusResponse>(`/status/${encodeURIComponent(jobId)}`);
}

/**
 * Retrieve download URLs for a completed job.
 */
export async function getDownloadLinks(
  jobId: string,
): Promise<DownloadResponse> {
  return request<DownloadResponse>(`/download/${encodeURIComponent(jobId)}`);
}
