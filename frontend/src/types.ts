export type RouteId = 'workbench' | 'examples' | 'evaluation' | 'documentation' | 'about'
export type Theme = 'light' | 'dark'

export interface Capabilities {
  mode: 'local' | 'hosted'
  generation_enabled: boolean
  code_execution_enabled: boolean
  model_load_on_first_run: boolean
  no_data_leaves_process: boolean
  persistence_enabled: boolean
  telemetry_enabled: boolean
  max_problem_characters: number
  max_prompt_tokens: number
  prompt_version: string
  backend_version: string
}

export interface ModelStatus {
  state: 'not_loaded' | 'loading' | 'ready' | 'verification_failed' | 'unavailable'
  adapter_verification: 'not_checked' | 'checking' | 'verified' | 'failed'
  verification_state: 'unconfigured' | 'verifying' | 'ready' | 'failed'
  load_state: 'not_loaded' | 'loading' | 'loaded' | 'load_failed'
  retry_available: boolean
  reason_code: string
  request_busy: boolean
  message: string
  model: string
  base_model: string
  base_revision: string
  adapter_hash: string
}

export interface ExampleItem {
  id: string
  category: string
  title: string
  problem: string
}

export type StageState = 'pending' | 'active' | 'passed' | 'warning' | 'failed' | 'not_reached'
export interface PipelineStage { id: string; label: string; state: StageState; detail: string }

export interface RunResult {
  status: 'completed' | 'completed_with_warning' | 'blocked' | 'failed'
  message: string
  program: {
    code: string
    language: 'Python'
    uses_sympy: boolean
    extraction_type: string
    sha256: string
    normalization: string[]
    generated_token_count: number
  }
  output: {
    stdout: string
    stderr: string
    parsed_value: string
    display_value: string
    display_kind: 'exact' | 'approximate' | 'none'
    error_summary: string
    observable_status: string
    execution_status: string
    exit_status: number | null
    timed_out: boolean
    output_truncated: boolean
  }
  pipeline: PipelineStage[]
  details: {
    raw_response: string
    raw_response_sha256: string
    syntax_result: string
    policy_result: string
    blocked_rule_category: string
    policy_violations: string[]
    prompt_version: string
    model_revision: string
    adapter_hash: string
    prompt_token_count: number
    completion_token_count: number
    stopping_reason: string
    generation_seconds: number
    execution_seconds: number
  }
  summary: {
    status: string
    model: string
    total_seconds: number
    request_seconds: number
    prompt_token_count: number
    completion_token_count: number
  }
}

export interface EvaluationSummary {
  base: { correct: number; total: number }
  original_adapter: { correct: number; total: number }
  v2_automated: { correct: number; total: number }
  v2_manual: { correct: number; total: number }
  original_executable: number
  v2_executable: number
  scorer_false_negatives: number
  original_only: number
  v2_only: number
  both_correct: number
  both_incorrect: number
  protocol: string
  limitation: string
  documentation: string
}

export interface DocumentationItem { id: string; title: string; href: string }
