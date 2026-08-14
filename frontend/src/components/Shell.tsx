import {
  BookOpen,
  Boxes,
  Code2,
  FlaskConical,
  ExternalLink,
  Info,
  Menu,
  Moon,
  Sun,
  X,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'
import type { ModelStatus, RouteId, Theme } from '../types'

const navigation = [
  { id: 'workbench' as const, label: 'Workspace', icon: Code2 },
  { id: 'examples' as const, label: 'Examples', icon: Boxes },
  { id: 'evaluation' as const, label: 'Evaluation', icon: FlaskConical },
  { id: 'documentation' as const, label: 'Documentation', icon: BookOpen },
  { id: 'about' as const, label: 'About', icon: Info },
]

interface Props {
  route: RouteId
  navigate: (route: RouteId) => void
  theme: Theme
  toggleTheme: () => void
  modelStatus: ModelStatus | null
  running: boolean
  publicDemo: boolean
  children: ReactNode
}

export function Shell({ route, navigate, theme, toggleTheme, modelStatus, running, publicDemo, children }: Props) {
  const [menuOpen, setMenuOpen] = useState(false)
  const state = modelStatus?.state ?? 'not_loaded'
  const stateLabel = publicDemo
    ? 'Recorded demo'
    : running
    ? 'Generating'
    : !modelStatus || modelStatus.verification_state === 'verifying'
    ? 'Checking adapter'
    : modelStatus.verification_state === 'failed' || modelStatus.load_state === 'load_failed'
      ? 'Adapter unavailable'
      : modelStatus.verification_state !== 'ready'
        ? 'Adapter not configured'
        : modelStatus.load_state === 'loading'
          ? 'Loading model'
          : modelStatus.load_state === 'loaded'
            ? 'Model ready'
            : 'Adapter ready'

  const select = (id: RouteId) => {
    navigate(id)
    setMenuOpen(false)
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="icon-button menu-toggle" onClick={() => setMenuOpen(!menuOpen)} aria-label={menuOpen ? 'Close navigation' : 'Open navigation'}>
          {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
        </button>
        <button className="brand" onClick={() => select('workbench')} aria-label="AlgAlpaca workspace">
          <span className="alpha-logo" aria-hidden="true">α</span>
          <span className="brand-copy">
            <strong>AlgAlpaca</strong>
            <small>{publicDemo ? 'Algebra-to-Python workbench' : 'Local algebra-to-Python workbench'}</small>
          </span>
        </button>
        <div className="topbar-actions">
          <span className={`model-chip model-${state}`} aria-label={publicDemo ? 'Demo status: Recorded outputs' : `Adapter status: ${stateLabel}`} role="status">
            <span className="status-dot" aria-hidden="true" />
            <span className="model-chip-state">{stateLabel}</span>
          </span>
          <button className="icon-button" onClick={toggleTheme} aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}>
            {theme === 'light' ? <Moon aria-hidden="true" /> : <Sun aria-hidden="true" />}
          </button>
        </div>
      </header>

      <aside className={`sidebar ${menuOpen ? 'sidebar-open' : ''}`} aria-label="Primary navigation">
        <nav>
          {navigation.map(({ id, label, icon: Icon }) => (
            <button key={id} className={route === id ? 'nav-item active' : 'nav-item'} onClick={() => select(id)} aria-current={route === id ? 'page' : undefined}>
              <Icon aria-hidden="true" />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <a
          className="github-link"
          href="https://github.com/bhkaushik14/AlgAlpaca"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="GitHub repository (opens in a new tab)"
        >
          <ExternalLink aria-hidden="true" />
          <span>GitHub</span>
        </a>
      </aside>

      {menuOpen && <button className="nav-scrim" onClick={() => setMenuOpen(false)} aria-label="Close navigation" />}
      <main className="main-content" id="main-content">{children}</main>
    </div>
  )
}
