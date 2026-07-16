import { useEffect, useRef, useState } from 'react'
import { api, ApiError } from './api'
import { Shell } from './components/Shell'
import { Workbench } from './components/Workbench'
import { AboutView, DocumentationView, EvaluationView, ExamplesView, LoadingView } from './components/Views'
import type { Capabilities, DocumentationItem, EvaluationSummary, ExampleItem, ModelStatus, RouteId, RunResult, Theme } from './types'

const routes: RouteId[] = ['workbench', 'examples', 'evaluation', 'documentation', 'about']
const alreadyRunningMessage = 'Another local request is running; wait for it to finish.'

function routeFromPath(): RouteId {
  const candidate = window.location.pathname.split('/').filter(Boolean)[0] as RouteId | undefined
  return candidate && routes.includes(candidate) ? candidate : 'workbench'
}

function initialTheme(): Theme {
  const stored = window.localStorage.getItem('algebra-theme')
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export default function App() {
  const [route, setRoute] = useState<RouteId>(routeFromPath)
  const [theme, setTheme] = useState<Theme>(initialTheme)
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null)
  const [examples, setExamples] = useState<ExampleItem[]>([])
  const [evaluation, setEvaluation] = useState<EvaluationSummary | null>(null)
  const [documents, setDocuments] = useState<DocumentationItem[]>([])
  const [problem, setProblem] = useState('')
  const [bootError, setBootError] = useState('')
  const [result, setResult] = useState<RunResult | null>(null)
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState('')
  const [runNotice, setRunNotice] = useState('')
  const [inputError, setInputError] = useState('')
  const runActive = useRef(false)

  const refreshRuntime = async () => {
    const [nextCapabilities, nextStatus] = await Promise.all([api.capabilities(), api.modelStatus()])
    setCapabilities(nextCapabilities)
    setModelStatus(nextStatus)
  }

  const submitProblem = async (submittedProblem: string) => {
    if (runActive.current) return
    runActive.current = true
    setRunning(true)
    setResult(null)
    setRunError('')
    setRunNotice('')
    setInputError('')
    try {
      const checked = await api.validate(submittedProblem)
      if (!checked.valid) {
        setInputError('This problem is too long. Shorten it before generating.')
        return
      }
      const next = await api.run(submittedProblem)
      setResult(next)
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409 && caught.message === alreadyRunningMessage) {
        setRunNotice('Another local request is running. Try again after it finishes.')
      } else {
        setRunError(caught instanceof Error ? caught.message : 'The local request could not be completed.')
      }
    } finally {
      runActive.current = false
      setRunning(false)
      try {
        await refreshRuntime()
      } catch {
        // A completed submission remains visible even if the status refresh fails.
      }
    }
  }

  const resetRun = () => {
    if (runActive.current) return
    setResult(null)
    setRunError('')
    setRunNotice('')
    setInputError('')
  }

  useEffect(() => {
    document.title = 'AlgAlpaca'
    document.documentElement.dataset.theme = theme
    document.documentElement.style.colorScheme = theme
    window.localStorage.setItem('algebra-theme', theme)
  }, [theme])

  useEffect(() => {
    const pop = () => setRoute(routeFromPath())
    window.addEventListener('popstate', pop)
    return () => window.removeEventListener('popstate', pop)
  }, [])

  useEffect(() => {
    void Promise.all([api.capabilities(), api.modelStatus(), api.examples(), api.evaluation(), api.documentation()])
      .then(([nextCapabilities, nextStatus, nextExamples, nextEvaluation, nextDocuments]) => {
        setCapabilities(nextCapabilities)
        setModelStatus(nextStatus)
        setExamples(nextExamples)
        setEvaluation(nextEvaluation)
        setDocuments(nextDocuments)
      })
      .catch(() => setBootError('The local API is unavailable. Start the FastAPI service on 127.0.0.1.'))
  }, [])

  const navigate = (next: RouteId) => {
    if (next !== route) window.history.pushState({}, '', next === 'workbench' ? '/' : `/${next}`)
    setRoute(next)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const useExample = (nextProblem: string) => {
    if (runActive.current) return
    setProblem(nextProblem)
    setInputError('')
    navigate('workbench')
  }

  let view
  if (!capabilities || !modelStatus) view = <LoadingView label="Connecting to the local pipeline…" />
  else if (route === 'workbench') view = (
    <Workbench
      capabilities={capabilities}
      modelStatus={modelStatus}
      examples={examples}
      problem={problem}
      setProblem={setProblem}
      refreshRuntime={refreshRuntime}
      result={result}
      running={running}
      error={runError}
      notice={runNotice}
      inputError={inputError}
      setInputError={setInputError}
      submitProblem={submitProblem}
      resetRun={resetRun}
    />
  )
  else if (route === 'examples') view = <ExamplesView examples={examples} onUseExample={useExample} />
  else if (route === 'evaluation') view = <EvaluationView summary={evaluation} />
  else if (route === 'documentation') view = <DocumentationView documents={documents} />
  else view = <AboutView navigate={navigate} />

  return (
    <Shell route={route} navigate={navigate} theme={theme} toggleTheme={() => setTheme(theme === 'light' ? 'dark' : 'light')} modelStatus={modelStatus} running={running}>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      {bootError && <div className="error-banner boot-error" role="alert">{bootError}</div>}
      {view}
    </Shell>
  )
}
