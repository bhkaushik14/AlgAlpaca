import { ArrowRight, BookOpen, ExternalLink, FlaskConical, Layers3, ShieldCheck } from 'lucide-react'
import type { DocumentationItem, EvaluationSummary, ExampleItem, RouteId } from '../types'

export function ExamplesView({ examples, onUseExample }: { examples: ExampleItem[]; onUseExample: (problem: string) => void }) {
  return (
    <div className="standard-view">
      <header className="page-intro"><h1>Examples</h1><p>Choose a problem to open in the workspace.</p></header>
      <div className="example-grid">
        {examples.map((example) => (
          <article className="card example-card" key={example.id}>
            <span className="category-label">{example.category}</span>
            <h2>{example.title}</h2>
            <p>{example.problem}</p>
            <button className="text-button" onClick={() => onUseExample(example.problem)}>Open in Workspace <ArrowRight aria-hidden="true" /></button>
          </article>
        ))}
      </div>
      <p className="route-note">These examples are separate from the project’s evaluation set.</p>
    </div>
  )
}

export function EvaluationView({ summary }: { summary: EvaluationSummary | null }) {
  if (!summary) return <LoadingView label="Loading evaluation summary…" />
  const metrics = [
    ['Base', `${summary.base.correct}/${summary.base.total}`],
    ['Adapter', `${summary.adapter.correct}/${summary.adapter.total}`],
    ['Adapter-only', summary.adapter_only],
    ['Base-only', summary.base_only],
    ['Both correct', summary.both_correct],
    ['Both incorrect', summary.both_incorrect],
  ]
  return (
    <div className="standard-view evaluation-view">
      <header className="page-intro"><h1>Evaluation</h1><p>The adapter solved 39 of 100 cases. The base model solved 17.</p></header>
      <div className="metric-grid">{metrics.map(([label, value]) => <article className="metric-card" key={label}><span>{label}</span><strong>{value}</strong></article>)}</div>
      <section className="card limitation-callout">
        <div className="limitation-figure"><strong>{summary.adapter_failed}/100</strong><span>adapter cases failed</span></div>
        <div><h2>What these results mean</h2><p>These results apply only to the project’s 100-case evaluation and documented protocol.</p><p>The results do not measure performance on other datasets or algebra tasks.</p><a href={summary.documentation} target="_blank" rel="noreferrer">Detailed evaluation documentation <ExternalLink aria-hidden="true" /></a></div>
      </section>
      <section className="card protocol-card"><h2>Paired accounting</h2><div className="paired-bar" aria-label="Paired outcomes"><span style={{ flex: summary.adapter_only }} className="bar-adapter">{summary.adapter_only} adapter-only</span><span style={{ flex: summary.base_only }} className="bar-base">{summary.base_only} base-only</span><span style={{ flex: summary.both_correct }} className="bar-both">{summary.both_correct} both correct</span><span style={{ flex: summary.both_incorrect }} className="bar-neither">{summary.both_incorrect} both incorrect</span></div></section>
    </div>
  )
}

export function DocumentationView({ documents }: { documents: DocumentationItem[] }) {
  const descriptions: Record<string, string> = {
    evaluation: 'Fixture, scoring, compact results, and limitations.',
    architecture: 'Local interface, inference pipeline, and execution boundary.',
    history: 'Research reconstruction and reproducibility boundaries.',
    limitations: 'Failure modes and appropriate interpretation.',
    licensing: 'Code Llama, adapter, and third-party obligations.',
    'model-card': 'Model details, intended use, evaluation, and safety.',
  }
  return (
    <div className="standard-view"><header className="page-intro"><h1>Documentation</h1><p>Architecture, evaluation, limitations, history, licensing, and model details.</p></header><div className="docs-grid">{documents.map((doc) => <a className="card doc-card" key={doc.id} href={doc.href} target="_blank" rel="noreferrer"><BookOpen aria-hidden="true" /><div><h2>{doc.title}</h2><p>{descriptions[doc.id] ?? 'Project documentation.'}</p></div><ExternalLink aria-hidden="true" /></a>)}</div></div>
  )
}

export function AboutView({ navigate }: { navigate: (route: RouteId) => void }) {
  return (
    <div className="standard-view about-view">
      <header className="page-intro"><h1>About AlgAlpaca</h1><p>AlgAlpaca generates Python programs for algebra problems using a Code Llama adapter.</p></header>
      <div className="about-grid">
        <article className="card"><Layers3 aria-hidden="true" /><h2>Adapter model</h2><p>Uses a PEFT adapter with the CodeLlama-7B-Instruct base model.</p></article>
        <article className="card"><FlaskConical aria-hidden="true" /><h2>Generated programs</h2><p>Shows the Python program produced for each algebra problem.</p></article>
        <article className="card"><ShieldCheck aria-hidden="true" /><h2>Local execution</h2><p>Runs generated programs in a restricted local research sandbox.</p></article>
      </div>
      <p className="about-disclaimer">AlgAlpaca is the application name and is not related to the Stanford Alpaca model.</p>
      <button className="primary-action inline-action" onClick={() => navigate('workbench')}>Go to Workspace <ArrowRight aria-hidden="true" /></button>
    </div>
  )
}

export function LoadingView({ label }: { label: string }) {
  return <div className="loading-view" role="status"><span className="loading-ring" aria-hidden="true" />{label}</div>
}
