export type Category = 'shirt' | 'hoodie' | 'jacket' | 'coat'
export type Health = { app: string; deployment_mode?: 'local' | 'hosted'; spatial_protection_available?:boolean; comfyui: { ready: boolean; reachable: boolean;
  error: { code: string; message: string; missing_nodes?: string[]; missing_models?: string[] } | null };
  supported_categories: Category[]; reference_modes?: {
    multi_reference?: {categories:Category[];verified_total_inputs:number;reference_roles?:Partial<Record<Category,string[]>>};
    two_garment?: {combinations:string[];verified_total_inputs:number;validated_source_bag_options?:boolean[]} } }
export type Job = { id: string; state: 'queued' | 'processing' | 'complete' | 'failed'; stage: string;
  category: Category; seed: number; created_at: number; expires_at: number | null;
  assets_expired: boolean; upstream_active: boolean; error: {code: string; message: string} | null;
  manifest: { deadline_exceeded?: boolean; [key: string]: unknown } }
export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message) }
}

async function response(path: string, options: RequestInit = {}) {
  const result = await fetch(path, { cache: 'no-store', credentials: 'same-origin', ...options,
    headers: {Accept:'application/json', ...options.headers} })
  if (!result.ok) {
    const body = await result.json().catch(() => ({}))
    throw new ApiError(result.status, body.error?.code ?? 'REQUEST_FAILED',
      body.error?.message ?? (typeof body.detail === 'string' ? body.detail : 'The request could not be completed.'))
  }
  return result
}
export async function json<T>(path: string, options: RequestInit = {}): Promise<T> {
  return (await response(path, options)).json()
}
export async function photo(path: string, signal?: AbortSignal): Promise<Blob> {
  const result = await response(path, { signal })
  return result.blob()
}
export const inputPath = (id: string, role: 'person' | 'garment' | 'back' | 'side' | 'detail' | 'outer') => `/api/try-on/${encodeURIComponent(id)}/inputs/${role}`
export const resultPath = (id: string) => `/api/try-on/${encodeURIComponent(id)}/result`

export async function validatePhoto(file: File): Promise<void> {
  if (file.size > 10 * 1024 * 1024) throw new Error('Choose a photo no larger than 10 MiB.')
  const head = new Uint8Array(await file.slice(0,12).arrayBuffer())
  const png = head[0] === 137 && head[1] === 80 && head[2] === 78 && head[3] === 71
  const jpeg = head[0] === 255 && head[1] === 216 && head[2] === 255
  const text = new TextDecoder().decode(head)
  if (!png && !jpeg && !(text.startsWith('RIFF') && text.slice(8,12) === 'WEBP'))
    throw new Error('Choose a PNG, JPEG or WebP photo.')
  let image: ImageBitmap
  try { image = await createImageBitmap(file) } catch { throw new Error('This photo could not be opened. Choose another file.') }
  const pixels = image.width * image.height
  image.close()
  if (pixels > 16_000_000) throw new Error('Choose a photo with at most 16 million pixels.')
}
export async function hash(file: File) {
  const bytes = await crypto.subtle.digest('SHA-256', await file.arrayBuffer())
  return Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2,'0')).join('')
}
export function message(error: unknown) {
  return error instanceof ApiError ? error.message : 'The application could not be reached. Keep this page open and check the connection.'
}
