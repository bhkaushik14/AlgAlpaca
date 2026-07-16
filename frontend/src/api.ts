import type {
  Capabilities,
  DocumentationItem,
  EvaluationSummary,
  ExampleItem,
  ModelStatus,
  RunResult,
} from './types'

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    let detail = 'The local request could not be completed.'
    try {
      const body = (await response.json()) as {
        detail?: string | { message?: string; reason_code?: string }
      }
      if (typeof body.detail === 'string') detail = body.detail
      else if (body.detail?.message) detail = body.detail.message
    } catch {
      // Keep the public-safe fallback.
    }
    throw new ApiError(detail, response.status)
  }
  return response.json() as Promise<T>
}

const jsonRequest = (problem: string): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ problem }),
})

export const api = {
  capabilities: () => request<Capabilities>('/api/capabilities'),
  modelStatus: () => request<ModelStatus>('/api/model-status'),
  verifyModel: () => request<ModelStatus>('/api/model/verify', { method: 'POST' }),
  examples: async () => (await request<{ examples: ExampleItem[] }>('/api/examples')).examples,
  evaluation: () => request<EvaluationSummary>('/api/evaluation-summary'),
  documentation: async () =>
    (await request<{ documents: DocumentationItem[] }>('/api/documentation')).documents,
  validate: (problem: string) =>
    request<{ valid: boolean; message: string; token_count: number | null }>(
      '/api/validate',
      jsonRequest(problem),
    ),
  run: (problem: string) => request<RunResult>('/api/run', jsonRequest(problem)),
}
