// Pure helpers deciding when the backend auth token must (not) be attached,
// and when a 401 may redirect to the admin login. No side effects: easy to test.

// Public backend endpoints: never send a token, never redirect to login.
// Paths are relative to the API base (e.g. '/bookings/'), trailing slash ignored.
const PUBLIC_RULES = [
  { method: 'POST', test: (p) => p === '/bookings' },
  { method: 'POST', test: (p) => p === '/contacts' },
  { method: 'GET', test: (p) => p === '/gallery/public' },
  { method: 'GET', test: (p) => p === '/settings/comunas-lejanas' },
  { method: 'POST', test: (p) => p === '/payments/create-preference' },
  { method: 'GET', test: (p) => p.startsWith('/payments/status/') },
]

const normalizePath = (url = '') => {
  let path = String(url).split('?')[0].split('#')[0]
  // Strip scheme/host and the /api prefix if a full URL was given
  path = path.replace(/^https?:\/\/[^/]+/i, '').replace(/^\/api(?=\/)/, '')
  if (!path.startsWith('/')) path = `/${path}`
  return path.length > 1 ? path.replace(/\/+$/, '') : path
}

export const isPublicRequest = (method, url) => {
  const m = String(method || 'get').toUpperCase()
  const path = normalizePath(url)
  return PUBLIC_RULES.some((r) => r.method === m && r.test(path))
}

// Only redirect to the admin login when the user is inside the admin panel.
export const shouldRedirectToLogin = (pathname = '') =>
  pathname === '/admin' || pathname.startsWith('/admin/')
