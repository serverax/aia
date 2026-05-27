// Real authentication against the backend orchestrator's OAuth2 /token endpoint.
// No fake login: a wrong password returns 401 and we surface a real error.

const ORCH_BASE =
  (import.meta.env.VITE_ORCHESTRATOR_BASE_URL as string | undefined) ?? 'http://localhost:8080'

export interface AuthUser {
  username: string
  scopes: string[]
}

export interface LoginResult {
  token: string
  user: AuthUser
}

/** Decode the (unverified) JWT payload to read username + scopes for the UI.
 * Trust for access decisions still rests with the backend, which re-validates
 * the token signature on every request. */
export function decodeUser(token: string): AuthUser {
  const segment = token.split('.')[1] ?? ''
  const base64 = segment.replace(/-/g, '+').replace(/_/g, '/')
  const payload = JSON.parse(atob(base64)) as { sub?: string; scopes?: string[] }
  return { username: payload.sub ?? 'unknown', scopes: payload.scopes ?? [] }
}

export async function login(username: string, password: string): Promise<LoginResult> {
  const body = new URLSearchParams({ username, password })
  const resp = await fetch(`${ORCH_BASE}/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  if (resp.status === 401) {
    throw new Error('Invalid username or password')
  }
  if (!resp.ok) {
    throw new Error(`Login failed (HTTP ${resp.status})`)
  }
  const data = (await resp.json()) as { access_token: string; token_type: string }
  if (!data.access_token) {
    throw new Error('Login response did not include an access token')
  }
  return { token: data.access_token, user: decodeUser(data.access_token) }
}
