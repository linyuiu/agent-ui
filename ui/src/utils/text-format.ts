export const formatIsoDateTime = (value: string) => {
  if (!value) return ''
  return value.replace('T', ' ').replace('Z', '')
}

export const parseCommaSeparated = (value: string) => {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}
