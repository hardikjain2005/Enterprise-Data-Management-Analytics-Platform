import { useCallback, useEffect, useState } from 'react'
import { apiGet, errorMessage } from './client'

// Small data-fetching hook: re-fetches whenever the path or params change.
export function useApi(path, params) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const key = JSON.stringify(params || {})

  const load = useCallback(() => {
    if (!path) return
    setLoading(true)
    setError(null)
    apiGet(path, params)
      .then(setData)
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, key])

  useEffect(load, [load])
  return { data, loading, error, reload: load }
}
