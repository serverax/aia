import { type ReactNode } from 'react'

import { useAuth } from '../../auth/AuthContext'
import { LoginPage } from './LoginPage'

/**
 * Renders its children only when authenticated; otherwise the login page.
 * This guards every page (dashboard, approvals, editor, admin) behind login
 * without requiring a router — the app currently navigates by state.
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <>{children}</> : <LoginPage />
}

export default AuthGate
