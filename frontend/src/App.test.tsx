import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import type { RunResult } from './types'

const capabilities = {
  mode: 'local', generation_enabled: true, code_execution_enabled: true,
  model_load_on_first_run: true, no_data_leaves_process: true,
  persistence_enabled: false, telemetry_enabled: false,
  max_problem_characters: 2000, max_prompt_tokens: 2048,
  prompt_version: 'confirmatory-algebra-to-code-v2', backend_version: '0.1.0.dev0',
}
const status = {
  state: 'ready', adapter_verification: 'verified', verification_state: 'ready',
  load_state: 'loaded', retry_available: true, reason_code: '', request_busy: false,
  message: 'ready', model: 'CodeLlama-7B-Instruct + AlgAlpaca v2 QLoRA', base_model: 'base',
  base_revision: '22cb240e', adapter_hash: 'a56735e268a5',
}
const failedStatus = {
  ...status,
  state: 'verification_failed', adapter_verification: 'failed', verification_state: 'failed',
  load_state: 'not_loaded', reason_code: 'adapter_weight_hash_mismatch',
  message: 'private /home/person/cache Traceback should not render',
}
const examples = [{ id: 'linear', category: 'Linear equation', title: 'Ticket total', problem: 'Solve 2x + 1 = 7.' }]
const evaluation = {
  base: { correct: 17, total: 100 }, original_adapter: { correct: 39, total: 100 },
  v2_automated: { correct: 59, total: 100 }, v2_manual: { correct: 71, total: 100 },
  original_executable: 61, v2_executable: 85, scorer_false_negatives: 12,
  original_only: 11, v2_only: 31, both_correct: 28, both_incorrect: 30,
  protocol: 'Deterministic one-call, no-repair confirmatory protocol',
  limitation: 'Project-specific fixture.', documentation: '/project-docs/evaluation',
}
const documents = [{ id: 'evaluation', title: 'Evaluation methods', href: '/project-docs/evaluation' }]

const completed: RunResult = {
  status: 'completed', message: 'Execution completed',
  program: { code: 'print("ANSWER:", 3)', language: 'Python', uses_sympy: false, extraction_type: 'raw_python', sha256: 'abc', normalization: [], generated_token_count: 8 },
  output: { stdout: 'ANSWER: 3\n', stderr: '', parsed_value: '3', display_value: '3', display_kind: 'exact', error_summary: '', observable_status: 'observable', execution_status: 'ok', exit_status: 0, timed_out: false, output_truncated: false },
  pipeline: ['response','extraction','syntax','policy','execution','observable','parsed'].map((id) => ({ id, label: id, state: 'passed', detail: '' })),
  details: { raw_response: 'print("ANSWER:", 3)', raw_response_sha256: 'raw', syntax_result: 'passed', policy_result: 'passed', blocked_rule_category: '', policy_violations: [], prompt_version: 'v2', model_revision: 'rev', adapter_hash: 'hash', prompt_token_count: 100, completion_token_count: 8, stopping_reason: 'eos', generation_seconds: 1, execution_seconds: 0.1 },
  summary: { status: 'Completed', model: 'adapter', total_seconds: 1.1, request_seconds: 1.2, prompt_token_count: 100, completion_token_count: 8 },
}

function response(body: unknown, ok = true, statusCode = ok ? 200 : 500) {
  return Promise.resolve({ ok, status: statusCode, json: () => Promise.resolve(body) } as Response)
}

function installFetch(runResult: RunResult = completed) {
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    if (url.includes('capabilities')) return response(capabilities)
    if (url.includes('model-status')) return response(status)
    if (url.includes('/api/model/verify')) return response(status)
    if (url.includes('examples')) return response({ examples })
    if (url.includes('evaluation-summary')) return response(evaluation)
    if (url.includes('documentation')) return response({ documents })
    if (url.includes('validate')) return response({ valid: true, message: 'within limit', token_count: 100 })
    if (url.includes('/api/run')) return response(runResult)
    return response({}, false)
  }))
}

beforeEach(() => {
  vi.stubEnv('VITE_PUBLIC_DEMO', 'false')
  window.history.replaceState({}, '', '/')
  window.localStorage.clear()
  installFetch()
})

async function runProblem() {
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Problem statement'), 'Solve x + 2 = 5.')
  await user.click(screen.getByRole('button', { name: 'Generate and run' }))
  return user
}

describe('branding, routes, and copy', () => {
  it('uses the approved brand, browser title, and header status', async () => {
    render(<App />)
    expect(await screen.findByText('AlgAlpaca')).toBeInTheDocument()
    expect(screen.getByText('Local algebra-to-Python workbench')).toBeInTheDocument()
    expect(screen.getByRole('status', { name: 'Adapter status: Model ready' })).toBeInTheDocument()
    expect(document.title).toBe('AlgAlpaca')
    expect(document.body).not.toHaveTextContent('Generate. Inspect. Execute.')
  })

  it('renders every approved route title and description', async () => {
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Workspace' })).toBeInTheDocument()
    expect(screen.getByText('Enter an algebra problem and generate a Python program.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Examples' }))
    expect(screen.getByText('Choose a problem to open in the workspace.')).toBeInTheDocument()
    expect(screen.getByText('These examples are separate from the project’s evaluation set.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Evaluation' }))
    expect(screen.getByText('Automated correctness: 17/100 base, 39/100 original adapter, and 59/100 v2. V2’s separate manual mathematical review counted 71/100.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Documentation' }))
    expect(screen.getByText('Architecture, evaluation, limitations, history, licensing, and model details.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'About' }))
    expect(screen.getByRole('heading', { name: 'About AlgAlpaca' })).toBeInTheDocument()
    expect(screen.getByText('AlgAlpaca generates Python programs for algebra problems using a Code Llama adapter.')).toBeInTheDocument()
  })

  it('keeps every verified evaluation value and narrow interpretation', async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText('Workspace')
    await user.click(screen.getByRole('button', { name: 'Evaluation' }))
    for (const value of ['17/100', '39/100', '59/100', '71/100', '61/100', '85/100', '12']) expect(screen.getByText(value)).toBeInTheDocument()
    for (const value of ['31 v2-only', '11 original-only', '28 both correct', '30 both incorrect']) expect(screen.getByText(value)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'What these results mean' })).toBeInTheDocument()
    expect(screen.getByText('These project-specific results do not measure performance on other datasets or algebra tasks.')).toBeInTheDocument()
  })

  it('uses the approved About cards and disclaimer', async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText('Workspace')
    await user.click(screen.getByRole('button', { name: 'About' }))
    for (const heading of ['Adapter model', 'Generated programs', 'Local execution']) expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument()
    expect(screen.getByText('AlgAlpaca is the application name and is not related to the Stanford Alpaca model.')).toBeInTheDocument()
  })
})

describe('Workspace naming and repository link', () => {
  it('uses Workspace in ordinary labels and route actions', async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findByRole('heading', { name: 'Workspace' })
    expect(screen.getByRole('button', { name: 'AlgAlpaca workspace' })).toBeInTheDocument()
    expect(document.body).not.toHaveTextContent(/\bWorkbench\b/)
    await user.click(screen.getByRole('button', { name: 'Examples' }))
    expect(screen.getByRole('button', { name: /Open in Workspace/ })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'About' }))
    expect(screen.getByRole('button', { name: /Go to Workspace/ })).toBeInTheDocument()
  })

  it('places one safe GitHub link at the bottom of desktop and mobile navigation', async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText('Workspace')
    const link = screen.getByRole('link', { name: 'GitHub repository (opens in a new tab)' })
    expect(link).toHaveAttribute('href', 'https://github.com/bhkaushik14/AlgAlpaca')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'))
    const sidebar = screen.getByRole('complementary', { name: 'Primary navigation' })
    expect(sidebar.lastElementChild).toBe(link)
    await user.click(screen.getByRole('button', { name: 'Open navigation' }))
    expect(sidebar).toHaveClass('sidebar-open')
    expect(within(sidebar).getByRole('link', { name: 'GitHub repository (opens in a new tab)' })).toBe(link)
    expect(screen.queryByText('Local Mode')).not.toBeInTheDocument()
  })
})

describe('simplified Workbench', () => {

  it('keeps the live validation and inference request path when public-demo mode is disabled', async () => {
    render(<App />)
    await runProblem()
    const requestedUrls = vi.mocked(fetch).mock.calls.map(([url]) => String(url))
    expect(requestedUrls.some((url) => url.includes('/api/validate'))).toBe(true)
    expect(requestedUrls.some((url) => url.includes('/api/run'))).toBe(true)
  })
  it('renders exactly two primary cards with the required controls', async () => {
    render(<App />)
    const textarea = await screen.findByLabelText('Problem statement')
    const cards = document.querySelectorAll('[data-primary-card="true"]')
    expect(cards).toHaveLength(2)
    expect(within(cards[0] as HTMLElement).getByRole('heading', { name: 'Algebra Problem' })).toBeInTheDocument()
    expect(textarea).toBeInTheDocument()
    expect(within(cards[0] as HTMLElement).getByLabelText('Load an example problem')).toBeInTheDocument()
    expect(within(cards[0] as HTMLElement).getByRole('button', { name: 'Clear' })).toBeInTheDocument()
    expect(within(cards[0] as HTMLElement).getByRole('button', { name: 'Generate and run' })).toBeInTheDocument()
    expect(within(cards[1] as HTMLElement).getByRole('heading', { name: 'Generated Program' })).toBeInTheDocument()
    expect(within(cards[1] as HTMLElement).getByRole('button', { name: 'Copy generated program' })).toBeInTheDocument()
  })

  it('removes crowded surfaces and keeps output hidden before a run', async () => {
    render(<App />)
    await screen.findByLabelText('Problem statement')
    const removed = ['Observable Output', 'Pipeline', 'Advanced Details', 'Run details', 'Developer details', 'Bounded raw model response', 'Local Mode', 'Problem Preview', 'Parsed Output', 'Parsed Mathematical Value']
    for (const text of removed) expect(screen.queryByText(text, { exact: false })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Program output' })).not.toBeInTheDocument()
    expect(document.querySelector('.step-badge')).not.toBeInTheDocument()
    expect(document.querySelector('.run-summary')).not.toBeInTheDocument()
  })

  it('shows exact stdout and code inside the Generated Program card', async () => {
    render(<App />)
    const user = await runProblem()
    const card = screen.getByRole('heading', { name: 'Generated Program' }).closest('section')!
    expect(await within(card).findByLabelText('Program result')).toHaveTextContent('3')
    expect(within(card).queryByText('ANSWER: 3')).not.toBeInTheDocument()
    expect(within(card).getByText('print')).toBeInTheDocument()
    expect(within(card).getByRole('heading', { name: 'Result' })).toBeInTheDocument()
    expect(within(card).getByText('Completed')).toBeInTheDocument()
    await user.click(within(card).getByRole('button', { name: 'Copy generated program' }))
    expect(await navigator.clipboard.readText()).toBe('print("ANSWER:", 3)')
    expect(document.body.textContent).not.toMatch(/Correct answer|Verified solution|Final answer|Interpreted Solution|Mathematically correct|Equivalent to expected answer/i)
  })

  it.each([
    [{ output: { ...completed.output, stdout: '', display_value: '', display_kind: 'none' } }, 'The program produced no output.', 'Completed with no output'],
    [{ status: 'blocked', output: { ...completed.output, stdout: '', display_value: '', display_kind: 'none', execution_status: 'not_run' } }, 'The program did not run because it was blocked by the safety policy.', 'Blocked'],
    [{ output: { ...completed.output, stdout: '', display_value: '', display_kind: 'none', timed_out: true, execution_status: 'timed_out' } }, 'The program timed out.', 'Timed out'],
    [{ status: 'failed', output: { ...completed.output, stdout: '', display_value: '', display_kind: 'none', error_summary: 'ZeroDivisionError: division by zero', execution_status: 'nonzero_exit', exit_status: 1 } }, 'The program exited with an error.', 'Failed'],
  ])('renders clear output state %#', async (changes, message, stateLabel) => {
    const runResult = { ...completed, ...changes, output: { ...completed.output, ...(changes.output ?? {}) } } as RunResult
    installFetch(runResult)
    render(<App />)
    await runProblem()
    expect(await screen.findByText(message)).toBeInTheDocument()
    expect(screen.getByText(stateLabel)).toBeInTheDocument()
  })

  it('supports themes, examples, keyboard generation, and mobile navigation controls', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Switch to dark theme' }))
    expect(window.localStorage.getItem('algebra-theme')).toBe('dark')
    await user.click(screen.getByRole('button', { name: 'Open navigation' }))
    expect(screen.getAllByRole('button', { name: 'Close navigation' })).toHaveLength(2)
    await user.click(screen.getAllByRole('button', { name: 'Close navigation' })[0])
    await user.selectOptions(screen.getByLabelText('Load an example problem'), 'linear')
    expect(screen.getByLabelText('Problem statement')).toHaveValue('Solve 2x + 1 = 7.')
    await user.keyboard('{Control>}{Enter}{/Control}')
    expect(await screen.findByLabelText('Program result')).toHaveTextContent('3')
  })
})

describe('generation state across internal navigation', () => {
  it('preserves exactly one delayed run through Examples and Evaluation navigation', async () => {
    let runCalls = 0
    let resolveRun!: (value: Response) => void
    const delayedRun = new Promise<Response>((resolve) => { resolveRun = resolve })
    const previous = vi.mocked(fetch).getMockImplementation()!
    vi.mocked(fetch).mockImplementation((input, init) => {
      if (String(input).includes('/api/run')) {
        runCalls += 1
        return delayedRun
      }
      return previous(input, init)
    })
    const user = userEvent.setup()
    render(<App />)
    const input = await screen.findByLabelText('Problem statement')
    await user.type(input, 'Solve x + 2 = 5.')
    await user.click(screen.getByRole('button', { name: 'Generate and run' }))
    await waitFor(() => expect(runCalls).toBe(1))

    await user.click(screen.getByRole('button', { name: 'Examples' }))
    expect(await screen.findByRole('heading', { name: 'Examples' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Workspace' }))
    expect(screen.getByRole('button', { name: 'Generating' })).toBeDisabled()
    expect(screen.getByLabelText('Problem statement')).toHaveValue('Solve x + 2 = 5.')
    expect(runCalls).toBe(1)

    await user.click(screen.getByRole('button', { name: 'Evaluation' }))
    expect(await screen.findByRole('heading', { name: 'Evaluation' })).toBeInTheDocument()
    resolveRun(await response(completed))
    await waitFor(() => expect(screen.getByRole('status', { name: 'Adapter status: Model ready' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Workspace' }))
    expect(await screen.findByLabelText('Program result')).toHaveTextContent('3')
    expect(screen.getByText('print')).toBeInTheDocument()
    expect(screen.getByLabelText('Problem statement')).toHaveValue('Solve x + 2 = 5.')
    expect(screen.getByRole('button', { name: 'Generate and run' })).toBeEnabled()
    expect(runCalls).toBe(1)
  })

  it('clears busy state after a delayed rejection without losing the problem', async () => {
    let rejectRun!: (reason: Error) => void
    const delayedRun = new Promise<Response>((_resolve, reject) => { rejectRun = reject })
    const previous = vi.mocked(fetch).getMockImplementation()!
    vi.mocked(fetch).mockImplementation((input, init) => String(input).includes('/api/run') ? delayedRun : previous(input, init))
    const user = userEvent.setup()
    render(<App />)
    const input = await screen.findByLabelText('Problem statement')
    await user.type(input, 'Solve x=3.')
    await user.click(screen.getByRole('button', { name: 'Generate and run' }))
    await screen.findByRole('button', { name: 'Generating' })
    await user.click(screen.getByRole('button', { name: 'Examples' }))
    rejectRun(new Error('The local request could not be completed.'))
    await waitFor(() => expect(screen.getByRole('status', { name: 'Adapter status: Model ready' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Workspace' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('The local request could not be completed.')
    expect(screen.getByRole('button', { name: 'Generate and run' })).toBeEnabled()
    expect(screen.getByLabelText('Problem statement')).toHaveValue('Solve x=3.')
  })

  it('preserves a failed generated program across navigation without a second request', async () => {
    let runCalls = 0
    let resolveRun!: (value: Response) => void
    const delayedRun = new Promise<Response>((resolve) => { resolveRun = resolve })
    const previous = vi.mocked(fetch).getMockImplementation()!
    vi.mocked(fetch).mockImplementation((input, init) => {
      if (String(input).includes('/api/run')) {
        runCalls += 1
        return delayedRun
      }
      return previous(input, init)
    })
    const failedResult: RunResult = {
      ...completed,
      status: 'failed',
      program: { ...completed.program, code: 'print(1 / 0)' },
      output: {
        ...completed.output,
        stdout: '', parsed_value: '', display_value: '', display_kind: 'none',
        error_summary: 'ZeroDivisionError: division by zero', execution_status: 'nonzero_exit',
        exit_status: 1,
      },
    }
    const user = userEvent.setup()
    render(<App />)
    await user.type(await screen.findByLabelText('Problem statement'), 'Solve x=3.')
    await user.click(screen.getByRole('button', { name: 'Generate and run' }))
    await user.click(screen.getByRole('button', { name: 'Examples' }))
    resolveRun(await response(failedResult))
    await waitFor(() => expect(screen.getByRole('status', { name: 'Adapter status: Model ready' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Workspace' }))
    expect(await screen.findByText('The program exited with an error.')).toBeInTheDocument()
    expect(screen.getByText('ZeroDivisionError: division by zero')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Copy generated program' })).toBeEnabled()
    expect(screen.getByLabelText('Problem statement')).toHaveValue('Solve x=3.')
    expect(runCalls).toBe(1)
  })

  it('treats an unrelated backend busy response as recoverable, not permanent failure', async () => {
    const previous = vi.mocked(fetch).getMockImplementation()!
    vi.mocked(fetch).mockImplementation((input, init) => String(input).includes('/api/run')
      ? response({ detail: 'Another local request is running; wait for it to finish.' }, false, 409)
      : previous(input, init))
    const user = userEvent.setup()
    render(<App />)
    await user.type(await screen.findByLabelText('Problem statement'), 'Solve x=3.')
    await user.click(screen.getByRole('button', { name: 'Generate and run' }))
    expect(await screen.findByText('Another local request is running. Try again after it finishes.')).toBeInTheDocument()
    expect(screen.getByText('Ready')).toBeInTheDocument()
    expect(screen.queryByText('Failed')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate and run' })).toBeEnabled()
  })
})

describe('silent token validation', () => {
  it('keeps successful validation silent', async () => {
    const user = userEvent.setup()
    render(<App />)
    const input = await screen.findByLabelText('Problem statement')
    await user.type(input, 'Solve x=3.')
    await user.tab()
    await waitFor(() => expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).includes('/api/validate'))).toBe(true))
    expect(document.body).not.toHaveTextContent('Input is within the prompt-token limit.')
    expect(document.body).not.toHaveTextContent('Token count will be checked before generation.')
    expect(document.body).not.toHaveTextContent('within limit')
  })

  it('rejects backend-declared over-limit input without truncation or a run call', async () => {
    let runCalls = 0
    const previous = vi.mocked(fetch).getMockImplementation()!
    vi.mocked(fetch).mockImplementation((input, init) => {
      const url = String(input)
      if (url.includes('/api/validate')) return response({ valid: false, message: 'internal token detail', token_count: 3000 })
      if (url.includes('/api/run')) { runCalls += 1; return response(completed) }
      return previous(input, init)
    })
    const user = userEvent.setup()
    render(<App />)
    const input = await screen.findByLabelText('Problem statement')
    const original = 'Solve a deliberately long symbolic expression.'
    await user.type(input, original)
    await user.click(screen.getByRole('button', { name: 'Generate and run' }))
    expect(await screen.findByText('This problem is too long. Shorten it before generating.')).toBeInTheDocument()
    expect(input).toHaveValue(original)
    expect(runCalls).toBe(0)
  })
})

describe('verification and request recovery', () => {
  it('shows safe verification recovery, preserves input, disables generation, and keeps navigation usable', async () => {
    const previous = vi.mocked(fetch).getMockImplementation()!
    vi.mocked(fetch).mockImplementation((input, init) => {
      const url = String(input)
      if (url.includes('model-status')) return response(failedStatus)
      if (url.includes('capabilities')) return response({ ...capabilities, generation_enabled: false })
      return previous(input, init)
    })
    const user = userEvent.setup()
    render(<App />)
    const input = await screen.findByLabelText('Problem statement')
    await user.type(input, 'Solve x + 1 = 2.')
    expect(screen.getByText('The adapter could not be verified.')).toBeInTheDocument()
    expect(screen.getByText('Check the local adapter configuration, then retry verification.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate and run' })).toBeDisabled()
    expect(input).toHaveValue('Solve x + 1 = 2.')
    expect(document.body.textContent).not.toMatch(/\/home\/person|Traceback/)
    await user.click(screen.getByRole('button', { name: 'Evaluation' }))
    expect(await screen.findByText('59/100')).toBeInTheDocument()
  })

  it('enables generation after a deliberate successful retry without losing input', async () => {
    let verified = false
    const previous = vi.mocked(fetch).getMockImplementation()!
    vi.mocked(fetch).mockImplementation((input, init) => {
      const url = String(input)
      if (url.includes('/api/model/verify')) { verified = true; return response(status) }
      if (url.includes('model-status')) return response(verified ? status : failedStatus)
      if (url.includes('capabilities')) return response({ ...capabilities, generation_enabled: verified })
      return previous(input, init)
    })
    const user = userEvent.setup()
    render(<App />)
    const input = await screen.findByLabelText('Problem statement')
    await user.type(input, 'Solve x + 1 = 2.')
    await user.click(screen.getByRole('button', { name: 'Retry verification' }))
    await waitFor(() => expect(screen.queryByText('The adapter could not be verified.')).not.toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Generate and run' })).toBeEnabled()
    expect(input).toHaveValue('Solve x + 1 = 2.')
  })

  it('clears the busy state after a failed request and preserves the problem', async () => {
    const previous = vi.mocked(fetch).getMockImplementation()!
    vi.mocked(fetch).mockImplementation((input, init) => String(input).includes('/api/run') ? response({ detail: 'The local request could not be completed.' }, false) : previous(input, init))
    const user = userEvent.setup()
    render(<App />)
    const input = await screen.findByLabelText('Problem statement')
    await user.type(input, 'Solve x=3.')
    await user.click(screen.getByRole('button', { name: 'Generate and run' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('The local request could not be completed.')
    expect(screen.getByRole('button', { name: 'Generate and run' })).toBeEnabled()
    expect(input).toHaveValue('Solve x=3.')
  })
})

describe('public demo mode', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_PUBLIC_DEMO', 'true')
  })

  it('loads static data and shows the exact demo notice without backend requests', async () => {
    render(<App />)
    expect(await screen.findByText('This public demo uses real outputs from the evaluated AlgAlpaca model')).toBeInTheDocument()
    expect(screen.getByText('Try an evaluated example to view AlgAlpaca’s recorded Python output.')).toBeInTheDocument()
    expect(screen.getByRole('status', { name: 'Demo status: Recorded outputs' })).toHaveTextContent('Recorded demo')
    expect(screen.getByRole('button', { name: 'View recorded result' })).toBeDisabled()
    expect(screen.getByText('Recorded code will appear here.')).toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('uses an authentic selected evaluation result without inference or execution requests', async () => {
    const user = userEvent.setup()
    render(<App />)
    const input = await screen.findByLabelText('Problem statement')
    await user.selectOptions(screen.getByLabelText('Load an example problem'), 'confirm-linear-01')
    expect(input).toHaveValue('Determine every real x satisfying 3*(2*x - 5) + 4 = 5*x + 12.')
    await user.click(screen.getByRole('button', { name: 'View recorded result' }))
    expect(await screen.findByLabelText('Program result')).toHaveTextContent('{23}')
    expect(screen.getByText('SymPy')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Copy generated program' }))
    expect(await navigator.clipboard.readText()).toBe(
      'from sympy import Eq, S, solveset, symbols\n\nx = symbols("x", real=True)\nequation = Eq(3*(2*x - (5)) + (4), 5*x + (12), evaluate=False)\nresult = solveset(equation, x, domain=S.Reals)\nprint("ANSWER:", result)',
    )
    expect(fetch).not.toHaveBeenCalled()
  })

  it('matches a user-entered retained problem while rejecting arbitrary input honestly', async () => {
    const user = userEvent.setup()
    render(<App />)
    const input = await screen.findByLabelText('Problem statement')
    await user.type(input, '  Determine every real x satisfying 3*(2*x - 5) + 4 = 5*x + 12.  ')
    await user.click(screen.getByRole('button', { name: 'View recorded result' }))
    expect(await screen.findByLabelText('Program result')).toHaveTextContent('{23}')

    await user.click(screen.getByRole('button', { name: 'Clear' }))
    await user.type(input, 'Solve my new equation.')
    await user.click(screen.getByRole('button', { name: 'View recorded result' }))
    expect(await screen.findByText('This public demo includes recorded results for evaluated examples. Choose one from “Try an example” to continue.')).toBeInTheDocument()
    expect(screen.queryByLabelText('Program result')).not.toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })
})
