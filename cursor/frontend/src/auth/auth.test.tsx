import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { AuthGate } from '../components/auth/AuthGate'
import { AuthProvider } from './AuthContext'
import { login } from './authApi'
import { authHeader, clearToken, getToken, setToken } from './tokenStore'

// Build a JWT-shaped token whose payload decodes to the given sub/scopes.
function makeToken(sub: string, scopes: string[]): string {
  const b64u = (o: unknown) =>
    btoa(JSON.stringify(o)).replace(/\+/g, '-').replace(/\//g, '_')
  return `${b64u({ alg: 'HS256', typ: 'JWT' })}.${b64u({ sub, scopes })}.sig`
}

function okTokenResponse(sub: string, scopes: string[]) {
  return new Response(JSON.stringify({ access_token: makeToken(sub, scopes), token_type: 'bearer' }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  clearToken()
  vi.restoreAllMocks()
})

describe('tokenStore', () => {
  test('set/get/clear + authHeader', () => {
    expect(getToken()).toBeNull()
    expect(authHeader()).toEqual({})
    setToken('abc.def.ghi')
    expect(getToken()).toBe('abc.def.ghi')
    expect(authHeader()).toEqual({ Authorization: 'Bearer abc.def.ghi' })
    clearToken()
    expect(getToken()).toBeNull()
  })
})

describe('authApi.login', () => {
  test('success returns token + decoded user', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => okTokenResponse('admin', ['admin', 'items'])))
    const result = await login('admin', 'pw')
    expect(result.user.username).toBe('admin')
    expect(result.user.scopes).toContain('admin')
  })

  test('401 raises an honest error (no fake success)', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('unauthorized', { status: 401 })))
    await expect(login('admin', 'wrong')).rejects.toThrow(/invalid username or password/i)
  })
})

describe('AuthGate journey', () => {
  test('blocks → login → protected content → logout blocks again', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => okTokenResponse('analyst', ['items'])))
    const user = userEvent.setup()

    render(
      <AuthProvider>
        <AuthGate>
          <div>SECRET DASHBOARD</div>
        </AuthGate>
      </AuthProvider>,
    )

    // Unauthenticated: login form shown, protected content hidden.
    expect(screen.getByRole('form', { name: 'login' })).toBeInTheDocument()
    expect(screen.queryByText('SECRET DASHBOARD')).not.toBeInTheDocument()

    // Real login flow.
    await user.type(screen.getByLabelText(/username/i), 'analyst')
    await user.type(screen.getByLabelText(/password/i), 'analyst-dev-pass')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    // Protected content now visible.
    expect(await screen.findByText('SECRET DASHBOARD')).toBeInTheDocument()
    expect(getToken()).not.toBeNull()
  })

  test('wrong password shows an error and stays blocked', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('unauthorized', { status: 401 })))
    const user = userEvent.setup()
    render(
      <AuthProvider>
        <AuthGate>
          <div>SECRET DASHBOARD</div>
        </AuthGate>
      </AuthProvider>,
    )
    await user.type(screen.getByLabelText(/username/i), 'analyst')
    await user.type(screen.getByLabelText(/password/i), 'nope')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid username or password/i)
    expect(screen.queryByText('SECRET DASHBOARD')).not.toBeInTheDocument()
  })
})

describe('AuthGate rejects malformed tokens (R-6)', () => {
  /*
   * AuthProvider rehydrates from sessionStorage on mount. `decodeUser` will
   * throw on any token that isn't a parseable JWT payload; `safeDecode`
   * wraps that in a try/catch and returns null on failure. The resulting
   * user is null, so AuthGate must render LoginPage, not the children.
   * Tests here pre-seed sessionStorage BEFORE render so we exercise the
   * rehydrate path, not the live signIn path.
   */

  test('garbage token in sessionStorage -> AuthGate blocks, no protected content', () => {
    setToken('not-even-a-jwt')
    render(
      <AuthProvider>
        <AuthGate>
          <div>SECRET DASHBOARD</div>
        </AuthGate>
      </AuthProvider>,
    )
    expect(screen.getByRole('form', { name: 'login' })).toBeInTheDocument()
    expect(screen.queryByText('SECRET DASHBOARD')).not.toBeInTheDocument()
  })

  test('three-segment token with non-base64 payload -> AuthGate blocks', () => {
    // Looks JWT-shaped but the payload segment is not valid base64; atob throws.
    setToken('header.@@@not-base64@@@.sig')
    render(
      <AuthProvider>
        <AuthGate>
          <div>SECRET DASHBOARD</div>
        </AuthGate>
      </AuthProvider>,
    )
    expect(screen.getByRole('form', { name: 'login' })).toBeInTheDocument()
    expect(screen.queryByText('SECRET DASHBOARD')).not.toBeInTheDocument()
  })

  test('three-segment token whose payload is base64 of non-JSON -> AuthGate blocks', () => {
    // btoa('not-json') = 'bm90LWpzb24='. Decodes cleanly; JSON.parse throws.
    setToken('header.bm90LWpzb24=.sig')
    render(
      <AuthProvider>
        <AuthGate>
          <div>SECRET DASHBOARD</div>
        </AuthGate>
      </AuthProvider>,
    )
    expect(screen.getByRole('form', { name: 'login' })).toBeInTheDocument()
    expect(screen.queryByText('SECRET DASHBOARD')).not.toBeInTheDocument()
  })

  test('no token at all -> AuthGate blocks (baseline)', () => {
    // clearToken in afterEach handles cleanup; this asserts the default case
    // explicitly so a future refactor to AuthProvider's initial useState can't
    // silently break the "no token = not authenticated" contract.
    clearToken()
    render(
      <AuthProvider>
        <AuthGate>
          <div>SECRET DASHBOARD</div>
        </AuthGate>
      </AuthProvider>,
    )
    expect(screen.getByRole('form', { name: 'login' })).toBeInTheDocument()
    expect(screen.queryByText('SECRET DASHBOARD')).not.toBeInTheDocument()
  })
})
