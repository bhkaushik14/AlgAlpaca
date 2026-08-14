import { publicDemoCases } from './publicDemoData.generated'
import type {
  Capabilities,
  DisplayResult,
  DocumentationItem,
  EvaluationSummary,
  ExampleItem,
  ModelStatus,
} from './types'

export const PUBLIC_DEMO_NOTICE = 'This public demo uses real outputs from the evaluated AlgAlpaca model'
export const PUBLIC_DEMO_UNSUPPORTED_MESSAGE = 'This public demo includes recorded results for evaluated examples. Choose one from “Try an example” to continue.'

export const isPublicDemoMode = () => import.meta.env.VITE_PUBLIC_DEMO === 'true'

export const publicDemoCapabilities: Capabilities = {
  mode: 'hosted',
  generation_enabled: false,
  code_execution_enabled: false,
  model_load_on_first_run: false,
  no_data_leaves_process: true,
  persistence_enabled: false,
  telemetry_enabled: false,
  max_problem_characters: 2000,
  max_prompt_tokens: 2048,
  prompt_version: 'confirmatory-algebra-to-code-v2',
  backend_version: 'static-public-demo',
}

export const publicDemoModelStatus: ModelStatus = {
  state: 'ready',
  adapter_verification: 'verified',
  verification_state: 'ready',
  load_state: 'not_loaded',
  retry_available: false,
  reason_code: '',
  request_busy: false,
  message: 'Recorded evaluation outputs are ready.',
  model: 'CodeLlama-7B-Instruct + AlgAlpaca v2 QLoRA',
  base_model: 'codellama/CodeLlama-7b-Instruct-hf',
  base_revision: '22cb240e0292b0b5ab4c17ccd97aa3a2f799cbed',
  adapter_hash: 'a56735e268a5',
}

export const publicDemoExamples: ExampleItem[] = publicDemoCases.map(({ id, category, title, problem }) => ({
  id,
  category,
  title,
  problem,
}))

export const publicDemoEvaluation: EvaluationSummary = {
  base: { correct: 17, total: 100 },
  original_adapter: { correct: 39, total: 100 },
  v2_automated: { correct: 59, total: 100 },
  v2_manual: { correct: 71, total: 100 },
  original_executable: 61,
  v2_executable: 85,
  scorer_false_negatives: 12,
  original_only: 11,
  v2_only: 31,
  both_correct: 28,
  both_incorrect: 30,
  protocol: 'Deterministic one-call, no-repair confirmatory protocol',
  limitation: 'Project-specific fixture; v2 still requires mathematical and code review.',
  documentation: 'https://github.com/bhkaushik14/AlgAlpaca/blob/main/evaluation/README.md',
}

export const publicDemoDocuments: DocumentationItem[] = [
  { id: 'evaluation', title: 'Evaluation methods', href: 'https://github.com/bhkaushik14/AlgAlpaca/blob/main/evaluation/README.md' },
  { id: 'architecture', title: 'Architecture', href: 'https://github.com/bhkaushik14/AlgAlpaca/blob/main/docs/architecture.md' },
  { id: 'history', title: 'History', href: 'https://github.com/bhkaushik14/AlgAlpaca/blob/main/docs/history.md' },
  { id: 'limitations', title: 'Limitations', href: 'https://github.com/bhkaushik14/AlgAlpaca/blob/main/docs/limitations.md' },
  { id: 'licensing', title: 'Licensing', href: 'https://github.com/bhkaushik14/AlgAlpaca/blob/main/docs/licensing.md' },
  { id: 'model-card', title: 'Model card', href: 'https://github.com/bhkaushik14/AlgAlpaca/blob/main/MODEL_CARD.md' },
]

const normalizeProblem = (problem: string) => problem.trim().replace(/\s+/g, ' ')

export function publicDemoResultFor(problem: string): DisplayResult | null {
  const normalized = normalizeProblem(problem)
  const recorded = publicDemoCases.find((item) => normalizeProblem(item.problem) === normalized)
  if (!recorded) return null

  return {
    status: 'completed',
    program: {
      code: recorded.extracted_code,
      language: 'Python',
      uses_sympy: /(?:from|import)\s+sympy/.test(recorded.extracted_code),
    },
    output: {
      stdout: recorded.stdout,
      display_value: recorded.parsed_answer,
      display_kind: recorded.parsed_answer ? 'exact' : 'none',
      error_summary: '',
      execution_status: recorded.execution_status,
      timed_out: false,
    },
    details: { syntax_result: recorded.syntax_status },
  }
}
