export function roomURL(value) {
  try {
    const url = new URL(value)
    if (url.protocol !== 'https:' || !/^[a-z0-9-]+\.trycloudflare\.com$/.test(url.hostname)
      || url.port || url.username || url.password || url.pathname !== '/' || url.search || url.hash) return null
    return url.origin
  } catch { return null }
}

export default function handler(request, response) {
  response.setHeader('Cache-Control', 'no-store')
  if (request.method !== 'GET') {
    response.setHeader('Allow', 'GET')
    return response.status(405).json({error:'Method not allowed'})
  }
  const url = roomURL(process.env.COMFYFITTER_PRIVATE_URL)
  return response.status(200).json({url, available:!!url})
}
