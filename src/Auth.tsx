import { useState, type FormEvent } from 'react'
import { Eye, EyeOff, Orbit } from 'lucide-react'

export function Auth({submit, demo, notice}: {
  submit: (mode: string, payload: object) => Promise<void>; demo: () => void; notice: string
}) {
  const [register, setRegister] = useState(false)
  const [visible, setVisible] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function handle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true); setError('')
    try { await submit(register ? 'register' : 'login', Object.fromEntries(new FormData(event.currentTarget))) }
    catch (err) { setError((err as Error).message) }
    finally { setBusy(false) }
  }
  return <main className="auth-layout"><section className="card auth-card">
    <div className="brand"><span className="brand-icon"><Orbit size={26}/></span><span>ASTRA <strong>HEALTH</strong></span></div>
    <h1>{register ? 'Create your account' : 'Crew sign-in'}</h1>
    <p className="quiet">Access your private mission health workspace.</p>
    <form key={String(register)} onSubmit={handle}>
      {register && <label>Full name<input name="name" autoComplete="name" maxLength={100} required/></label>}
      <label>Email address<input name="email" type="email" autoComplete="email" required maxLength={254}/></label>
      <label htmlFor="astra-password">Password</label>
      <div className="password-row"><input id="astra-password" name="password" type={visible?'text':'password'} autoComplete={register?'new-password':'current-password'} minLength={register?12:undefined} maxLength={128} required/><button type="button" aria-label={visible?'Hide password':'Show password'} onClick={()=>setVisible(!visible)}>{visible?<EyeOff size={19}/>:<Eye size={19}/>}</button></div>
      {register && <><small>Use 12–128 characters.</small><label>Confirm password<input name="confirmation" type="password" autoComplete="new-password" maxLength={128} required/></label></>}
      {(error || notice) && <p className="error" role="alert">{error || notice}</p>}
      <button className="button primary" disabled={busy}>{busy?'Please wait…':register?'Create account':'Sign in'}</button>
    </form>
    <button className="auth-link" disabled={busy} onClick={()=>{setRegister(!register);setVisible(false);setError('')}}>{register?'Already have an account? Sign in':'New astronaut? Create an account'}</button>
    <button className="button secondary" disabled={busy} onClick={demo}>Enter Synthetic Demo</button>
  </section></main>
}

