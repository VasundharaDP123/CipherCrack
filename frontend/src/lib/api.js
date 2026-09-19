const getApiBase = () => '/api'

async function request(path, options = {}) {
  const baseUrl = getApiBase()
  let response
  try {
    response = await fetch(`${baseUrl}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
  } catch (err) {
    response = await fetch(`/api${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
  }
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error || `${response.status} ${response.statusText}`)
  return body
}

const post = (path, payload) =>
  request(path, { method: 'POST', body: JSON.stringify(payload) })

export const api = {
  health: () => request('/health'),
  catalogue: () => request('/catalogue'),

  encrypt: (payload) => post('/encrypt', payload),
  decrypt: (payload) => post('/decrypt', payload),
  randomKey: (cipher) => request(`/random-key/${cipher}`),

  identify: (payload) => post('/identify', payload),
  clusters: (limit = 600) => request(`/identify/clusters?limit=${limit}`),
  identifierMetrics: () => request('/identify/metrics'),

  crack: (payload) => post('/crack', payload),
  arenaRun: (payload) => post('/arena/run', payload),
  arenaResults: (limit = 40) => request(`/arena/results?limit=${limit}`),

  playgroundSample: (payload) => post('/playground/sample', payload),
  playgroundCompare: (payload) => post('/playground/compare', payload),

  leaderboard: () => request('/leaderboard'),
  addScore: (payload) => post('/leaderboard', payload),
  newChallenge: (difficulty) => request(`/challenge/new?difficulty=${difficulty}`),
}
