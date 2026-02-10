const normalizeToken = (raw: string) => raw.replace(/^bearer\s+/i, '').trim()

const parseError = async (response: Response, fallback: string) => {
  const payload = (await response.json().catch(() => ({}))) as { detail?: string }
  return payload?.detail || fallback
}

const getToken = () => {
  const raw = localStorage.getItem('access_token') || ''
  return normalizeToken(raw)
}

export const createChatSession = async (): Promise<void> => {
  const token = getToken()
  if (!token) {
    throw new Error('访问需要登录')
  }

  const response = await fetch('/chat/session', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    credentials: 'include',
  })

  if (!response.ok) {
    throw new Error(await parseError(response, '访问需要登录'))
  }
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
