import { Check, Clipboard, Code2 } from 'lucide-react'
import { Highlight, themes } from 'prism-react-renderer'
import { useState } from 'react'
import type { DisplayResult } from '../types'

interface Props {
  result: DisplayResult | null
  running: boolean
  error: string
  publicDemo?: boolean
}

function resultState(result: DisplayResult | null, running: boolean, error: string) {
  if (running) return { label: 'Generating', detail: 'The local request is in progress.' }
  if (error) return { label: 'Failed', detail: '' }
  if (!result) return { label: 'Ready', detail: '' }
  if (result.status === 'blocked') return { label: 'Blocked', detail: '' }
  if (result.output.timed_out) return { label: 'Timed out', detail: '' }
  if (result.output.execution_status !== 'ok') return { label: 'Failed', detail: '' }
  if (!result.output.stdout) return { label: 'Completed with no output', detail: '' }
  return { label: 'Completed', detail: '' }
}

function outputText(result: DisplayResult) {
  if (result.status === 'blocked') return 'The program did not run because it was blocked by the safety policy.'
  if (result.output.timed_out) return 'The program timed out.'
  if (result.details.syntax_result === 'failed') return 'The generated program contains invalid Python syntax.'
  if (result.output.execution_status !== 'ok') return 'The program exited with an error.'
  if (result.output.display_kind !== 'none' && result.output.display_value) return result.output.display_value
  return 'The program produced no output.'
}

export function CodePanel({ result, running, error, publicDemo = false }: Props) {
  const [copied, setCopied] = useState(false)
  const code = result?.program.code ?? ''
  const state = resultState(result, running, error)
  const copy = async () => {
    if (!code) return
    await navigator.clipboard.writeText(code)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1200)
  }

  return (
    <section className="card program-card primary-workbench-card" aria-labelledby="program-heading" data-primary-card="true">
      <div className="card-heading program-heading-row">
        <div>
          <h2 id="program-heading">Generated Program</h2>
          <div className={`compact-run-status status-${state.label.toLowerCase().replaceAll(' ', '-')}`} role="status" aria-live="polite">
            <span className="status-dot" aria-hidden="true" />
            <strong>{state.label}</strong>
            {state.detail && <span>{state.detail}</span>}
          </div>
        </div>
        <div className="program-actions">
          <span className="language-badge"><Code2 aria-hidden="true" /> Python</span>
          {result?.program.uses_sympy && <span className="secondary-badge">SymPy</span>}
          <button className="compact-button dark-button" onClick={copy} disabled={!code} aria-label="Copy generated program">
            {copied ? <Check aria-hidden="true" /> : <Clipboard aria-hidden="true" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>
      <div className="code-surface" tabIndex={0} aria-label="Read-only generated Python program">
        {code ? (
          <Highlight theme={themes.vsDark} code={code} language="python">
            {({ className, style, tokens, getLineProps, getTokenProps }) => (
              <pre className={className} style={{ ...style, background: 'transparent' }}>
                {tokens.map((line, lineIndex) => (
                  <div key={lineIndex} {...getLineProps({ line })} className="code-line">
                    <span className="line-number" aria-hidden="true">{lineIndex + 1}</span>
                    <span className="line-content">
                      {line.map((token, tokenIndex) => <span key={tokenIndex} {...getTokenProps({ token })} />)}
                    </span>
                  </div>
                ))}
              </pre>
            )}
          </Highlight>
        ) : (
          <div className="code-empty">
            <Code2 aria-hidden="true" />
            <strong>{publicDemo ? 'Recorded code will appear here.' : 'Generated code will appear here.'}</strong>
            <span>{publicDemo ? 'Try an evaluated example to view its Python program.' : 'Run an algebra problem to view the Python program.'}</span>
          </div>
        )}
      </div>
      {result && (
        <section className="program-output" aria-labelledby="program-output-heading">
          <h3 id="program-output-heading">
            {result.output.display_kind === 'approximate' && result.output.execution_status === 'ok'
              ? 'Approximate result'
              : result.output.display_kind === 'exact' && result.output.execution_status === 'ok'
                ? 'Result'
                : 'Program output'}
          </h3>
          <pre tabIndex={0} aria-label="Program result">{outputText(result)}</pre>
          {result.output.display_kind === 'approximate' && result.output.execution_status === 'ok' && (
            <details className="compact-details">
              <summary>Exact program output</summary>
              <pre tabIndex={0} aria-label="Bounded exact program standard output">{result.output.stdout}</pre>
            </details>
          )}
          {result.details.syntax_result !== 'failed' && !result.output.timed_out && result.output.execution_status !== 'ok' && result.status !== 'blocked' && result.output.error_summary && (
            <details className="compact-details error-details">
              <summary>Error details</summary>
              <p>{result.output.error_summary}</p>
            </details>
          )}
        </section>
      )}
    </section>
  )
}
