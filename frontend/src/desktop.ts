type DesktopStatus = {state:'starting' | 'ready' | 'error'; message:string}
type DesktopAPI = {repair:()=>Promise<DesktopStatus>; ready:()=>Promise<boolean>}
declare global { interface Window { pywebview?: {api: DesktopAPI} } }

export function desktopAPI() {
  return location.origin==='http://127.0.0.1:8000' ? window.pywebview?.api : undefined
}
