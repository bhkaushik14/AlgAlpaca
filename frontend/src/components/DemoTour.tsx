import { ArrowLeft, ArrowRight, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { RouteId } from '../types'

type Spotlight = { left: number; top: number; right: number; bottom: number }

const steps = [
  {
    target: 'example-select',
    title: 'Pick an example',
    body: 'Open the menu and choose “Simplification: Simplify radicals.”',
    hint: 'Choose an example to continue',
  },
  {
    target: 'problem-preview',
    title: 'See the math clearly',
    body: 'This box shows symbols like √ instead of sqrt. The original problem stays in the box below.',
    hint: 'Next',
  },
  {
    target: 'run-button',
    title: 'View the saved result',
    body: 'This public demo shows a saved result from AlgAlpaca. It does not run new code here.',
    hint: 'Click “View recorded result”',
  },
  {
    target: 'code-surface',
    title: 'See the Python code',
    body: 'This is the Python program AlgAlpaca wrote for the problem. The colors make it easier to read.',
    hint: 'Next: see the answer',
  },
  {
    target: 'program-output',
    title: 'See the answer',
    body: 'The answer uses math symbols, like 4√2. Open “Raw result” to see the exact saved text.',
    hint: 'Next: see the scores',
  },
  {
    target: 'evaluation-metrics',
    title: 'See how it did',
    body: 'Out of 100 problems, the base model scored 17, the first version 39, and V2 59 in the automatic check. A separate human review counted 71 for V2.',
    hint: 'Finish tour',
  },
] as const

interface Props {
  step: number | null
  route: RouteId
  setStep: (step: number) => void
  navigate: (route: RouteId) => void
  close: () => void
}

export function DemoTour({ step, route, setStep, navigate, close }: Props) {
  const [spotlight, setSpotlight] = useState<Spotlight | null>(null)

  useEffect(() => {
    if (step === null) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [step, close])

  useEffect(() => {
    if (step === null) return
    const target = document.querySelector<HTMLElement>(`[data-tour="${steps[step].target}"]`)
    if (!target) return
    const update = () => {
      const rect = target.getBoundingClientRect()
      const padding = 7
      setSpotlight({
        left: Math.max(5, rect.left - padding),
        top: Math.max(5, rect.top - padding),
        right: Math.min(window.innerWidth - 5, rect.right + padding),
        bottom: Math.min(window.innerHeight - 5, rect.bottom + padding),
      })
    }
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    target.scrollIntoView?.({ block: 'center', behavior: reducedMotion ? 'instant' : 'smooth' })
    const frame = window.requestAnimationFrame(update)
    const settle = window.setTimeout(update, reducedMotion ? 0 : 350)
    window.addEventListener('resize', update)
    window.addEventListener('scroll', update, true)
    return () => {
      window.cancelAnimationFrame(frame)
      window.clearTimeout(settle)
      window.removeEventListener('resize', update)
      window.removeEventListener('scroll', update, true)
    }
  }, [step, route])

  if (step === null || !spotlight) return null
  const current = steps[step]
  const width = Math.min(328, window.innerWidth - 32)
  const spaceRight = window.innerWidth - spotlight.right
  const spaceLeft = spotlight.left
  const left = spaceRight >= width + 24
    ? spotlight.right + 15
    : spaceLeft >= width + 24
      ? spotlight.left - width - 15
      : Math.max(16, Math.min(spotlight.left, window.innerWidth - width - 16))
  const beside = spaceRight >= width + 24 || spaceLeft >= width + 24
  const top = beside
    ? Math.max(68, Math.min(spotlight.top, window.innerHeight - 222))
    : spotlight.bottom + 214 < window.innerHeight
      ? spotlight.bottom + 14
      : Math.max(68, spotlight.top - 210)

  const back = () => {
    if (step === 5) navigate('workbench')
    setSpotlight(null)
    setStep(Math.max(0, step - 1))
  }
  const next = () => {
    if (step === 4) {
      navigate('evaluation')
      setSpotlight(null)
      setStep(5)
    } else if (step === 5) close()
    else {
      setSpotlight(null)
      setStep(step + 1)
    }
  }

  return (
    <div className="demo-tour" aria-label="Guided AlgAlpaca tour">
      <div className="tour-shade" style={{ inset: `0 0 auto 0`, height: spotlight.top }} aria-hidden="true" />
      <div className="tour-shade" style={{ top: spotlight.top, left: 0, width: spotlight.left, height: spotlight.bottom - spotlight.top }} aria-hidden="true" />
      <div className="tour-shade" style={{ top: spotlight.top, left: spotlight.right, right: 0, height: spotlight.bottom - spotlight.top }} aria-hidden="true" />
      <div className="tour-shade" style={{ top: spotlight.bottom, bottom: 0, left: 0, right: 0 }} aria-hidden="true" />
      <div className="tour-spotlight" style={{ left: spotlight.left, top: spotlight.top, width: spotlight.right - spotlight.left, height: spotlight.bottom - spotlight.top }} aria-hidden="true" />
      <button className="tour-skip" onClick={close}>Skip tour <X aria-hidden="true" /></button>
      <section className="tour-card" style={{ left, top, width }} aria-live="polite">
        <div className="tour-card-top"><span>ALGALPACA TOUR</span><span>{String(step + 1).padStart(2, '0')} / {String(steps.length).padStart(2, '0')}</span></div>
        <h2>{current.title}</h2>
        <p>{current.body}</p>
        <div className="tour-controls">
          {step > 0 && <button className="tour-back" onClick={back}><ArrowLeft aria-hidden="true" /> Back</button>}
          {step === 0 || step === 2
            ? <span className="tour-hint">{current.hint}</span>
            : <button className="tour-next" onClick={next}>{current.hint} <ArrowRight aria-hidden="true" /></button>}
        </div>
      </section>
    </div>
  )
}
