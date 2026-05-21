import { useState } from 'react'
import type { PolicyReference } from '../../services/editor/schemas'

interface PolicyReferenceWidgetProps {
  value: PolicyReference[]
  onChange: (value: PolicyReference[]) => void
}

interface SearchResult {
  id?: string
  title?: string
  url?: string
  jurisdiction?: string
}

const searchBaseUrl = import.meta.env.VITE_POLICY_SEARCH_URL ?? 'http://localhost:8002/search'

export function PolicyReferenceWidget({ value, onChange }: PolicyReferenceWidgetProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<PolicyReference[]>([])
  const [isSearching, setIsSearching] = useState(false)

  const searchPolicies = async () => {
    if (!query.trim()) return
    setIsSearching(true)
    try {
      const response = await fetch(`${searchBaseUrl}?query=${encodeURIComponent(query)}&top_k=5`)
      const data = (await response.json()) as SearchResult[] | { results: SearchResult[] }
      const list = Array.isArray(data) ? data : data.results
      setResults(
        (list ?? []).map((item, index) => ({
          id: item.id ?? `policy-${index}`,
          title: item.title ?? 'Untitled policy',
          url: item.url,
          jurisdiction: item.jurisdiction,
        })),
      )
    } catch {
      setResults([])
    } finally {
      setIsSearching(false)
    }
  }

  const addPolicy = (policy: PolicyReference) => {
    if (value.some((item) => item.id === policy.id)) return
    onChange([...value, policy])
  }

  const removePolicy = (id: string) => {
    onChange(value.filter((item) => item.id !== id))
  }

  return (
    <div className="policy-widget">
      <div className="policy-search">
        <input
          type="text"
          value={query}
          placeholder="Search policy references"
          onChange={(event) => setQuery(event.target.value)}
        />
        <button type="button" onClick={searchPolicies} disabled={isSearching}>
          Search
        </button>
      </div>

      <ul className="policy-list">
        {results.map((policy) => (
          <li key={policy.id}>
            <span>{policy.title}</span>
            <button type="button" onClick={() => addPolicy(policy)}>
              Insert
            </button>
          </li>
        ))}
      </ul>

      <h4>Selected References</h4>
      <ul className="policy-list">
        {value.map((policy) => (
          <li key={policy.id}>
            <span>{policy.title}</span>
            <button type="button" className="danger" onClick={() => removePolicy(policy.id)}>
              Remove
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

