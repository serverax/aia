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
