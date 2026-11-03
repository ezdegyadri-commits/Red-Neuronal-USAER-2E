/**
 * Cliente API desacoplado para Next.js con soporte para prefetching y caché TanStack.
 */
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    'Content-Type': 'application/json',
    ...(typeof window !== 'undefined' ? { 'X-User-Account': localStorage.getItem('usaer_user') || 'docente.apoyo@usaer2e.edu.mx' } : {}),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    cache: 'no-store', // TanStack Query gestiona el caché en cliente
  });

  if (!res.ok) {
    throw new Error(`API Error ${res.status}: ${res.statusText}`);
  }

  return res.json();
}

