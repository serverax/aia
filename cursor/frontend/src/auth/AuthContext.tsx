import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'

import { login as apiLogin, decodeUser, type AuthUser } from './authApi'
import { clearToken, getToken, setToken } from './tokenStore'

interface AuthState {
  user: AuthUser | null
  isAuthenticated: boolean
  error: string | null
  loading: boolean
  signIn: (username: string, password: string) => Promise<void>
  signOut: () => void
}

const AuthCtx = createContext<AuthState | null>(null)

function safeDecode(token: string): AuthUser | null {
  try {
    return decodeUser(token)
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  // Rehydrate from an existing token (e.g. page refresh in the same tab).
  const [user, setUser] = useState<AuthUser | null>(() => {
    const t = getToken()
    return t ? safeDecode(t) : null
  })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const signIn = useCallback(async (username: string, password: string) => {
    setLoading(true)
    setError(null)
    try {
      const result = await apiLogin(username, password)
      setToken(result.token)
      setUser(result.user)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Login failed')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const signOut = useCallback(() => {
    clearToken()
    setUser(null)
  }, [])

  return (
    <AuthCtx.Provider
      value={{ user, isAuthenticated: user !== null, error, loading, signIn, signOut }}
    >
      {children}
    </AuthCtx.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx)
  if (!ctx) {
    throw new Error('useAuth must be used within an <AuthProvider>')
  }
  return ctx
}
