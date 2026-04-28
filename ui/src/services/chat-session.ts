const parseError = async (response: Response, fallback: string) => {
  const payload = (await response.json().catch(() => ({}))) as { detail?: string }
  return payload?.detail || fallback
}

const syncSessionHeaders = (response: Response) => {
  const expiresAt = response.headers.get('x-session-expires-at')
  if (expiresAt) {
    localStorage.setItem('session_expires_at', expiresAt)
  }
}

export const createChatSession = async (): Promise<void> => {
  const response = await fetch('/chat/session', {
    method: 'POST',
    credentials: 'include',
  })

  if (!response.ok) {
    throw new Error(await parseError(response, '访问需要登录'))
  }
  syncSessionHeaders(response)
}

export const clearChatSession = async (): Promise<void> => {
  try {
    await fetch('/chat/session', {
      method: 'DELETE',
      credentials: 'include',
    })
  } catch {
    // ignore
  }
}
