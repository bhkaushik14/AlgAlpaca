import { AlertTriangle, Check, Circle, CircleDashed, X } from 'lucide-react'
import type { PipelineStage, StageState } from '../types'

const iconFor = (state: StageState) => {
  if (state === 'passed') return <Check aria-hidden="true" />
  if (state === 'warning') return <AlertTriangle aria-hidden="true" />
  if (state === 'failed') return <X aria-hidden="true" />
  if (state === 'active') return <CircleDashed aria-hidden="true" />
  return <Circle aria-hidden="true" />
}

export function Pipeline({ stages, running }: { stages?: PipelineStage[]; running: boolean }) {
  const defaults = [
    'Model response received', 'Code extracted', 'Python syntax validated', 'Safety policy checked',
    'Program executed', 'Observable output detected', 'Output parsed',
  ].map((label, index) => ({ id: String(index), label, state: 'pending' as const, detail: '' }))
  const displayed = stages ?? defaults

  return (
    <section className="card pipeline-card" aria-labelledby="pipeline-heading">
      <div className="card-heading step-heading">
        <span className="step-badge">4</span>
        <div>
          <h2 id="pipeline-heading">Pipeline</h2>
          <p>{running ? 'Running pipeline…' : 'Recorded stages for the latest request.'}</p>
        </div>
      </div>
      <ol className="pipeline-list">
        {displayed.map((stage, index) => (
          <li key={stage.id} className={`pipeline-stage stage-${running ? 'pending' : stage.state}`}>
            <span className="stage-icon">{iconFor(running ? 'pending' : stage.state)}</span>
            <span className="stage-index">{index + 1}</span>
            <span className="stage-label">{stage.label}</span>
            <span className="stage-state">{running ? 'Pending' : stage.state === 'not_reached' ? 'Not reached' : stage.state}</span>
            {!running && stage.detail && <span className="stage-detail">{stage.detail}</span>}
          </li>
        ))}
      </ol>
    </section>
  )
}
