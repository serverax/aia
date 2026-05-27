// JWT access token storage for the SPA. sessionStorage (not localStorage) so the
// token is dropped when the tab closes. NOTE: any in-browser token store is
// readable by JS, so XSS hygiene matters; a httpOnly-cookie flow would be
// stronger but the backend /token endpoint is bearer-only today.

const KEY = 'aia_access_token'

export function getToken(): string | null {
  try {
    return sessionStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function setToken(token: string): void {
  try {
    sessionStorage.setItem(KEY, token)
  } catch {
    /* storage unavailable (private mode) — auth simply won't persist */
  }
}

export function clearToken(): void {
  try {
    sessionStorage.removeItem(KEY)
  } catch {
    /* ignore */
  }
}

export function authHeader(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

/** fetch() wrapper that attaches the bearer token (if any) to every request. */
export async function authedFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  return fetch(input, {
    ...init,
    headers: { ...(init.headers ?? {}), ...authHeader() },
  })
}
