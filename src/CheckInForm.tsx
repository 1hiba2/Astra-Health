import { useState, type FormEvent } from 'react'

type Measurement = {label: string; unit: string; minimum: number; maximum: number}
const examples: Record<string, number> = {heart:72, systolic:120, diastolic:80, temperature:36.8, oxygen:98, sleep:7.5}
const increments: Record<string, number> = {temperature:0.1, sleep:0.5}

export function CheckInForm({metrics, submit, busy, error}: {
  metrics: Record<string, Measurement>
  submit: (event: FormEvent<HTMLFormElement>) => Promise<void>
  busy: boolean
  error: string
}) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.keys(metrics).map(key => [key, String(examples[key] ?? '')])))
  const [confirmed, setConfirmed] = useState<Record<string, boolean>>({})
  const pending = Object.keys(examples).filter(key => key in metrics && !confirmed[key]).length

  function update(key: string, value: string) {
    setValues(previous => ({...previous, [key]: value}))
    setConfirmed(previous => ({...previous, [key]: true}))
  }

  return <form onSubmit={event => {
    if (pending || busy) { event.preventDefault(); return }
    void submit(event)
  }}>
    <p className="quiet">Confirm, edit, or clear each example. Examples are illustrative only and have no clinical validation. Input ranges validate data entry. Health alerts are evaluated separately after saving.</p>
    <fieldset disabled={busy} className="form-grid">
      {Object.entries(metrics).map(([key, metric]) => {
        const value = values[key]
        const example = key in examples && !confirmed[key]
        const increment = increments[key] ?? 1
        function adjust(direction: number) {
          const current = value === '' ? (examples[key] ?? metric.minimum) : Number(value)
          const next = Math.min(metric.maximum, Math.max(metric.minimum, current + direction * increment))
          if (value !== '' && next === current) return
          update(key, String(Number(next.toFixed(10))))
        }
        return <div key={key} className="measurement-field">
          <label htmlFor={'check-'+key}>{metric.label} ({metric.unit})</label>
          <div className="stepper">
            <button type="button" className="button secondary" aria-label={'Decrease '+metric.label} onClick={()=>adjust(-1)}>−</button>
            <input id={'check-'+key} name={key} type="number" step="any" min={metric.minimum} max={metric.maximum}
              value={value} onChange={event=>update(key,event.currentTarget.value)}/>
            <button type="button" className="button secondary" aria-label={'Increase '+metric.label} onClick={()=>adjust(1)}>+</button>
          </div>
          <div className="measurement-actions">
            {example && <button type="button" className="auth-link" aria-label={'Confirm '+metric.label} onClick={()=>update(key,value)}>Confirm example</button>}
            {value !== '' && <button type="button" className="auth-link" aria-label={'Clear '+metric.label} onClick={()=>update(key,'')}>Clear</button>}
          </div>
        </div>
      })}
      <label>Well-being<textarea name="wellbeing" maxLength={500}/></label>
      <label>Symptoms<textarea name="symptoms" maxLength={500}/></label>
    </fieldset>
    {error && <p className="error" role="alert">{error}</p>}
    {pending > 0 && <p className="quiet" role="status">{pending} example {pending === 1 ? 'needs' : 'need'} review.</p>}
    <button className="button primary" disabled={busy || pending > 0}>{busy?'Saving…':'Save check-in'}</button>
  </form>
}
