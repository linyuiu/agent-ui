const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

type LoginKeyResponse = {
  key_id: string
  algorithm: string
  public_key_pem: string
}

type EncryptedLoginPayload = {
  encrypted_payload: string
  key_id: string
}

let cachedLoginKey: Promise<LoginKeyResponse> | null = null

const textEncoder = new TextEncoder()

const pemToArrayBuffer = (pem: string): ArrayBuffer => {
  const normalized = pem
    .replace(/-----BEGIN PUBLIC KEY-----/g, '')
    .replace(/-----END PUBLIC KEY-----/g, '')
    .replace(/\s+/g, '')
  const binary = atob(normalized)
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index)
  }
  return bytes.buffer
}

const toBase64 = (bytes: ArrayBuffer | Uint8Array): string => {
  const array = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes)
  let binary = ''
  array.forEach((item) => {
    binary += String.fromCharCode(item)
  })
  return btoa(binary)
}

const getLoginKey = async (): Promise<LoginKeyResponse> => {
  if (!cachedLoginKey) {
    cachedLoginKey = fetch(`${API_BASE}/auth/login-key`).then(async (response) => {
      if (!response.ok) {
        throw new Error('获取登录加密公钥失败')
      }
      return (await response.json()) as LoginKeyResponse
    })
  }
  return cachedLoginKey
}

export const clearCachedLoginKey = () => {
  cachedLoginKey = null
}

export const encryptLoginCredentials = async (
  account: string,
  password: string
): Promise<EncryptedLoginPayload> => {
  if (!window.crypto?.subtle) {
    throw new Error('当前浏览器不支持登录加密')
  }

  const keyPayload = await getLoginKey()
  const publicKey = await window.crypto.subtle.importKey(
    'spki',
    pemToArrayBuffer(keyPayload.public_key_pem),
    {
      name: 'RSA-OAEP',
      hash: 'SHA-256',
    },
    false,
    ['encrypt']
  )

  const aesKey = await window.crypto.subtle.generateKey(
    {
      name: 'AES-GCM',
      length: 256,
    },
    true,
    ['encrypt']
  )
  const iv = window.crypto.getRandomValues(new Uint8Array(12))
  const plaintext = textEncoder.encode(
    JSON.stringify({
      account,
      password,
    })
  )
  const ciphertext = await window.crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv,
    },
    aesKey,
    plaintext
  )
  const rawAesKey = await window.crypto.subtle.exportKey('raw', aesKey)
  const encryptedKey = await window.crypto.subtle.encrypt(
    {
      name: 'RSA-OAEP',
    },
    publicKey,
    rawAesKey
  )

  const envelope = {
    encrypted_key: toBase64(encryptedKey),
    iv: toBase64(iv),
    ciphertext: toBase64(ciphertext),
  }

  return {
    encrypted_payload: btoa(JSON.stringify(envelope)),
    key_id: keyPayload.key_id,
  }
}

