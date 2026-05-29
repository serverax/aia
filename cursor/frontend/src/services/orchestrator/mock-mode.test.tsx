/**
 * R-5: mock-mode production safety regression tests.
 *
 * Pins the guarantee that synthetic dashboard/approval data never reaches a
 * production build of the SPA. Three claims under test:
 *
 *   1. `services/orchestrator/client.ts` throws at module-init when
 *      `VITE_ENABLE_MOCKS=true` (or the legacy `VITE_ORCHESTRATOR_USE_MOCK=true`)
 *      under `import.meta.env.PROD`. This is the hard guarantee.
 *   2. With no mock flag set, `isMockEnabled` is false.
 *   3. `<MockModeBanner>` renders nothing when its `enabled` flag is false,
 *      and renders the warning when it is true.
 *
 * The client.ts checks happen at module-init (top-level). We exercise them
 * with dynamic imports + `vi.resetModules()` so each test gets a fresh
 * evaluation against its stubbed `import.meta.env`.
 */

import { render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import { MockModeBanner } from '../../components/Common/MockModeBanner'

beforeEach(() => {
  vi.resetModules()
})

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('orchestrator/client mock-mode safety (R-5)', () => {
  test('isMockEnabled is false when no mock env var is set', async () => {
    vi.stubEnv('VITE_ENABLE_MOCKS', '')
    vi.stubEnv('VITE_ORCHESTRATOR_USE_MOCK', '')
    vi.stubEnv('PROD', false)
    const mod = await import('./client')
    expect(mod.isMockEnabled).toBe(false)
  })

  test('module-init THROWS when VITE_ENABLE_MOCKS=true under a PROD build', async () => {
    vi.stubEnv('VITE_ENABLE_MOCKS', 'true')
    vi.stubEnv('PROD', true)
    await expect(import('./client')).rejects.toThrow(
      /Mock mode is enabled in a PRODUCTION build/i,
    )
  })

  test('legacy VITE_ORCHESTRATOR_USE_MOCK=true also throws under PROD', async () => {
    vi.stubEnv('VITE_ENABLE_MOCKS', '')
    vi.stubEnv('VITE_ORCHESTRATOR_USE_MOCK', 'true')
    vi.stubEnv('PROD', true)
    await expect(import('./client')).rejects.toThrow(
      /Mock mode is enabled in a PRODUCTION build/i,
    )
  })

  test('isMockEnabled is true when mocks enabled in dev (non-PROD)', async () => {
    vi.stubEnv('VITE_ENABLE_MOCKS', 'true')
    vi.stubEnv('PROD', false)
    const mod = await import('./client')
    expect(mod.isMockEnabled).toBe(true)
  })
})

describe('MockModeBanner (R-5)', () => {
  test('renders nothing when mock mode is off', () => {
    const { container } = render(<MockModeBanner enabled={false} />)
    expect(container).toBeEmptyDOMElement()
  })

  test('renders the warning when mock mode is on', () => {
    const { getByRole } = render(<MockModeBanner enabled={true} />)
    expect(getByRole('alert')).toHaveTextContent(/MOCK MODE/i)
  })
})
