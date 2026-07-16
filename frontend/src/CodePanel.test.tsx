import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { CodePanel } from './components/CodePanel'
import type { RunResult } from './types'

const result: RunResult = {
  status: 'failed',
  message: 'Execution did not complete successfully',
  program: {
    code: 'print(1 / 0)', language: 'Python', uses_sympy: false,
    extraction_type: 'raw_python', sha256: 'code', normalization: [], generated_token_count: 5,
  },
  output: {
    stdout: '', stderr: 'bounded internal stderr', parsed_value: '', display_value: '',
    display_kind: 'none', error_summary: 'ZeroDivisionError: division by zero',
    observable_status: 'not_run', execution_status: 'nonzero_exit', exit_status: 1,
    timed_out: false, output_truncated: false,
  },
  pipeline: [],
  details: {
    raw_response: 'print(1 / 0)', raw_response_sha256: 'raw', syntax_result: 'passed',
    policy_result: 'passed', blocked_rule_category: '', policy_violations: [], prompt_version: 'v2',
    model_revision: 'revision', adapter_hash: 'hash', prompt_token_count: 10,
    completion_token_count: 5, stopping_reason: 'eos', generation_seconds: 1, execution_seconds: 0.1,
  },
  summary: {
    status: 'Failed', model: 'adapter', total_seconds: 1.1, request_seconds: 1.2,
    prompt_token_count: 10, completion_token_count: 5,
  },
}

describe('failed generated programs', () => {
  it('retains code, enables Copy, and keeps safe error details collapsed', async () => {
    const user = userEvent.setup()
    render(<CodePanel result={result} running={false} error="" />)
    expect(screen.getByText('The program exited with an error.')).toBeInTheDocument()
    const copy = screen.getByRole('button', { name: 'Copy generated program' })
    expect(copy).toBeEnabled()
    await user.click(copy)
    expect(await navigator.clipboard.readText()).toBe('print(1 / 0)')
    const summary = screen.getByText('Error details')
    const details = summary.closest('details')!
    expect(details).not.toHaveAttribute('open')
    expect(within(details).getByText('ZeroDivisionError: division by zero')).toBeInTheDocument()
    expect(document.body).not.toHaveTextContent('bounded internal stderr')
  })

  it('keeps syntax, timeout, and policy outcomes distinct', () => {
    const syntax = {
      ...result,
      output: { ...result.output, execution_status: 'not_run', error_summary: 'The generated program contains invalid Python syntax.' },
      details: { ...result.details, syntax_result: 'failed' },
    } as RunResult
    const { rerender } = render(<CodePanel result={syntax} running={false} error="" />)
    expect(screen.getByText('The generated program contains invalid Python syntax.')).toBeInTheDocument()
    rerender(<CodePanel result={{ ...result, output: { ...result.output, timed_out: true, execution_status: 'timeout', error_summary: '' } }} running={false} error="" />)
    expect(screen.getByText('The program timed out.')).toBeInTheDocument()
    rerender(<CodePanel result={{ ...result, status: 'blocked', output: { ...result.output, execution_status: 'not_run', error_summary: '' } }} running={false} error="" />)
    expect(screen.getByText('The program did not run because it was blocked by the safety policy.')).toBeInTheDocument()
  })
})

describe('numeric result presentation', () => {
  it('shows an approximation and retains exact stdout in a collapsed disclosure', () => {
    const approximate: RunResult = {
      ...result,
      status: 'completed',
      output: {
        ...result.output,
        stdout: `ANSWER: ${CUBIC_EXACT}`,
        parsed_value: CUBIC_EXACT,
        display_value: '[-3.750]',
        display_kind: 'approximate',
        error_summary: '',
        observable_status: 'observable',
        execution_status: 'ok',
        exit_status: 0,
      },
      details: { ...result.details, syntax_result: 'passed' },
    }
    render(<CodePanel result={approximate} running={false} error="" />)
    expect(screen.getByRole('heading', { name: 'Approximate result' })).toBeInTheDocument()
    expect(screen.getByText('[-3.750]')).toBeInTheDocument()
    const details = screen.getByText('Exact program output').closest('details')!
    expect(details).not.toHaveAttribute('open')
    expect(within(details).getByText(`ANSWER: ${CUBIC_EXACT}`)).toBeInTheDocument()
  })
})

const CUBIC_EXACT = 'unchanged exact symbolic stdout'
