import { useState, type FormEvent } from 'react'

import { useAuth } from '../../auth/AuthContext'

export function LoginPage() {
  const { signIn, error, loading } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    try {
      await signIn(username, password)
    } catch {
      /* error surfaced via auth context `error` */
    }
  }

  return (
    <main className="login-page" style={{ maxWidth: 360, margin: '10vh auto', padding: 24 }}>
      <h1>AIA — Sign in</h1>
      <form onSubmit={onSubmit} aria-label="login">
        <label style={{ display: 'block', marginBottom: 8 }}>
          Username
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label style={{ display: 'block', marginBottom: 8 }}>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      {error ? (
        <div role="alert" style={{ color: '#b91c1c', marginTop: 12 }}>
          {error}
        </div>
      ) : null}
    </main>
  )
}

export default LoginPage
