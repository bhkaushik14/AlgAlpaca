import { AlertTriangle, ChevronDown, Eraser, Info, Play, RotateCcw } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { PUBLIC_DEMO_NOTICE } from '../publicDemo'
import type { Capabilities, DisplayResult, ExampleItem, ModelStatus } from '../types'
import { CodePanel } from './CodePanel'

interface Props {
  capabilities: Capabilities
  modelStatus: ModelStatus
  examples: ExampleItem[]
  problem: string
  setProblem: (value: string) => void
  refreshRuntime: () => Promise<void>
  result: DisplayResult | null
  running: boolean
  error: string
  notice: string
  inputError: string
  setInputError: (value: string) => void
  submitProblem: (problem: string) => Promise<void>
  resetRun: () => void
  publicDemo: boolean
}

const reasonLabels: Record<string, string> = {
  adapter_path_not_configured: 'Adapter path is not configured',
  adapter_directory_unavailable: 'Adapter directory is unavailable',
  adapter_weight_missing: 'Adapter file was not found',
  adapter_config_missing: 'Adapter configuration was not found',
  adapter_weight_size_mismatch: 'Adapter weight size did not match',
  adapter_config_size_mismatch: 'Adapter configuration size did not match',
  adapter_weight_hash_mismatch: 'Adapter weight hash did not match',
  adapter_config_hash_mismatch: 'Adapter config hash did not match',
  base_revision_unavailable: 'Required base-model revision is unavailable',
  model_load_failed: 'Model loading failed',
}

export function Workbench({ capabilities, modelStatus, examples, problem, setProblem, refreshRuntime, result, running, error, notice, inputError, setInputError, submitProblem, resetRun, publicDemo }: Props) {
  const [verifying, setVerifying] = useState(false)
  const [verificationRetryError, setVerificationRetryError] = useState('')
  const textarea = useRef<HTMLTextAreaElement>(null)
  const tooLong = problem.length > capabilities.max_problem_characters
  const verificationReady = modelStatus.verification_state === 'ready'
  const verificationNeedsAttention = !verificationReady || modelStatus.load_state === 'load_failed'
  const unavailable = !verificationReady || modelStatus.load_state === 'loading'
  const canRun = Boolean(problem.trim()) && !tooLong && !inputError && !unavailable && (publicDemo || capabilities.generation_enabled) && !modelStatus.request_busy && !running && !verifying
  const actionLabel = publicDemo ? 'View recorded result' : 'Generate and run'

  const validate = async () => {
    if (publicDemo || !problem.trim() || tooLong) return
    try {
      const response = await api.validate(problem)
      setInputError(response.valid ? '' : 'This problem is too long. Shorten it before generating.')
    } catch {
      // Submission repeats authoritative validation; no success reassurance is needed.
    }
  }

  const run = () => {
    if (!canRun) return
    void submitProblem(problem)
  }

  const retryVerification = async () => {
    if (verifying || !modelStatus.retry_available) return
    setVerifying(true)
    setVerificationRetryError('')
    try {
      await api.verifyModel()
      await refreshRuntime()
    } catch (caught) {
      setVerificationRetryError(caught instanceof Error ? caught.message : 'Adapter verification could not be retried.')
      await refreshRuntime()
    } finally {
      setVerifying(false)
    }
  }

  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault()
        run()
      }
    }
    window.addEventListener('keydown', shortcut)
    return () => window.removeEventListener('keydown', shortcut)
  })

  const chooseExample = (id: string) => {
    const selected = examples.find((item) => item.id === id)
    if (selected && !running) {
      setProblem(selected.problem)
      setInputError('')
      resetRun()
      textarea.current?.focus()
    }
  }

  const reset = () => {
    if (running) return
    setProblem('')
    setInputError('')
    resetRun()
    textarea.current?.focus()
  }

  return (
    <div className="workbench-view">
      <header className="page-intro compact-intro">
        <h1>Workspace</h1>
        <p>{publicDemo ? 'Try an evaluated example to view AlgAlpaca’s recorded Python output.' : 'Enter an algebra problem and generate a Python program.'}</p>
      </header>

      <div className="workbench-grid">
        <section className="card problem-card primary-workbench-card" aria-labelledby="problem-heading" data-primary-card="true">
          <div className="card-heading">
            <div>
              <h2 id="problem-heading">Algebra Problem</h2>
              <p id="problem-help">{publicDemo ? 'Choose a retained evaluation example or enter its problem statement.' : 'Enter a problem in natural language or as an equation.'}</p>
            </div>
          </div>

          <label className="field-label" htmlFor="problem-input">Problem statement</label>
          <textarea
            ref={textarea}
            id="problem-input"
            value={problem}
            onChange={(event) => { setProblem(event.target.value); setInputError('') }}
            onBlur={() => void validate()}
            rows={10}
            maxLength={capabilities.max_problem_characters + 1}
            aria-invalid={tooLong || Boolean(inputError)}
            aria-describedby="problem-help problem-error"
            placeholder={publicDemo ? 'Choose a recorded example to begin.' : 'Example: Solve over the real numbers: 2x + 7 = 19.'}
            disabled={running}
          />
          {problem && <div className={tooLong ? 'character-count error-text' : 'character-count'}>{problem.length} / {capabilities.max_problem_characters}</div>}
          {(tooLong || inputError) && <p className="input-error" id="problem-error" role="alert">This problem is too long. Shorten it before generating.</p>}

          <div className="input-actions">
            <button className="compact-button" onClick={reset} disabled={running}><Eraser aria-hidden="true" /> Clear</button>
            <label className="select-label">
              <span className="sr-only">Load an example</span>
              <select defaultValue="" onChange={(event) => chooseExample(event.target.value)} aria-label="Load an example problem" disabled={running}>
                <option value="" disabled>{publicDemo ? 'Try an example…' : 'Choose an example…'}</option>
                {examples.map((example) => <option key={example.id} value={example.id}>{example.category}: {example.title}</option>)}
              </select>
              <ChevronDown aria-hidden="true" />
            </label>
          </div>

          {!publicDemo && verificationNeedsAttention && (
            <div className="verification-recovery" role="alert">
              <AlertTriangle aria-hidden="true" />
              <div>
                <strong>The adapter could not be verified.</strong>
                <p>Check the local adapter configuration, then retry verification.</p>
                <span>{reasonLabels[modelStatus.reason_code] ?? 'Adapter verification failed'}</span>
                <button className="compact-button retry-button" onClick={() => void retryVerification()} disabled={verifying || !modelStatus.retry_available}>
                  <RotateCcw className={verifying ? 'spin' : ''} aria-hidden="true" />
                  {verifying ? 'Verifying adapter…' : 'Retry verification'}
                </button>
                {verificationRetryError && <span>{verificationRetryError}</span>}
              </div>
            </div>
          )}

          {publicDemo
            ? <p className="safety-note public-demo-notice"><Info aria-hidden="true" />{PUBLIC_DEMO_NOTICE}</p>
            : <p className="safety-note"><AlertTriangle aria-hidden="true" />Generated code may be incorrect and runs in a restricted local sandbox.</p>}
          <button className="primary-action" onClick={run} disabled={!canRun} aria-label={running ? 'Generating' : actionLabel} aria-describedby={error || notice ? 'run-message' : undefined}>
            {running ? <RotateCcw className="spin" aria-hidden="true" /> : <Play aria-hidden="true" />}
            {running ? 'Generating…' : actionLabel}
            <kbd>⌘/Ctrl ↵</kbd>
          </button>
          {error && <div className="error-banner action-error" id="run-message" role="alert"><AlertTriangle aria-hidden="true" /><span>{error}</span></div>}
          {notice && <div className="request-notice" id="run-message" role="status"><span>{notice}</span></div>}
        </section>

        <CodePanel result={result} running={running} error={error} publicDemo={publicDemo} />
      </div>
    </div>
  )
}
