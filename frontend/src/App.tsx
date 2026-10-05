import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, hash, inputPath, json, message, photo, resultPath, validatePhoto } from './api'
import type { Category, Health, Job } from './api'
import Upload, { useObjectURL } from './Upload'
import SavedLooks from './SavedLooks'
import { desktopAPI } from './desktop'

const IDS = 'comfyfitter.temporaryJobs.v1', ACTIVE = 'comfyfitter.activeJob.v1', PENDING = 'comfyfitter.pending.v1'
const labels: Record<Category,string> = {shirt:'Shirt',hoodie:'Hoodie',jacket:'Jacket',coat:'Coat'}
type ExtraRole = 'back' | 'side' | 'detail' | 'outer'
type Mode = 'one' | 'views' | 'outfit'
const extraRoles: ExtraRole[] = ['back','side','detail','outer']
const viewRoles: ExtraRole[] = ['back','side','detail']
const blankExtras = (): Record<ExtraRole,File | null> => ({back:null,side:null,detail:null,outer:null})
type Request = { key: string; category: Category; seed: number; personHash: string; garmentHash: string; mode?: Mode; outerCategory?: Category; extraHashes?: Partial<Record<ExtraRole,string>>; protectRegions?:boolean; sourceHasBag?:boolean }
const uuid = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i
function read<T>(key: string, fallback: T): T { try { return JSON.parse(localStorage.getItem(key) ?? 'null') ?? fallback } catch { return fallback } }
function write(key: string, value: unknown) { try { localStorage.setItem(key,JSON.stringify(value)) } catch { /* Work still continues in this tab. */ } }
function remove(key: string) { try { localStorage.removeItem(key) } catch { /* Restricted browser storage. */ } }
function initialIds() { const value = read<unknown>(IDS,[]); return Array.isArray(value) ? value.filter((id): id is string => typeof id === 'string' && uuid.test(id)).slice(0,20) : [] }
function initialPending() {
  const value = read<Request | null>(PENDING,null)
  if (!value || typeof value!=='object' || typeof value.key!=='string' || !uuid.test(value.key) || !(value.category in labels) || !Number.isSafeInteger(value.seed) || value.seed<0 || !/^[a-f0-9]{64}$/.test(value.personHash) || !/^[a-f0-9]{64}$/.test(value.garmentHash)) return null
  if (value.mode && !['one','views','outfit'].includes(value.mode) || value.outerCategory && !(value.outerCategory in labels)) return null
  if (value.extraHashes && (typeof value.extraHashes!=='object' || Object.entries(value.extraHashes).some(([role,checksum]) => !extraRoles.includes(role as ExtraRole) || !/^[a-f0-9]{64}$/.test(checksum)))) return null
  if (value.protectRegions!==undefined && typeof value.protectRegions!=='boolean') return null
  if (value.sourceHasBag!==undefined && typeof value.sourceHasBag!=='boolean') return null
  return value
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null), [serviceError,setServiceError] = useState('')
  const [pollError,setPollError] = useState('')
  const [desktop,setDesktop] = useState(!!desktopAPI()), [repairing,setRepairing] = useState(false)
  const [connectionRevision,setConnectionRevision] = useState(0)
  const [ids,setIds] = useState(initialIds)
  const [jobId,setJobId] = useState<string | null>(() => { const id = read<string | null>(ACTIVE,null); return id && uuid.test(id) ? id : null })
  const [job,setJob] = useState<Job | null>(null), [pending,setPending] = useState(initialPending)
  const [person,setPerson] = useState<File | null>(null), [garment,setGarment] = useState<File | null>(null)
  const [extras,setExtras] = useState(blankExtras), [extraErrors,setExtraErrors] = useState<Partial<Record<ExtraRole,string>>>({})
  const [mode,setMode] = useState<Mode>(() => initialPending()?.mode ?? 'one'), [outerCategory,setOuterCategory] = useState<Category>(() => initialPending()?.outerCategory ?? 'jacket')
  const [protectRegions,setProtectRegions] = useState(() => initialPending()?.protectRegions ?? false)
  const [sourceHasBag,setSourceHasBag] = useState(() => initialPending()?.sourceHasBag ?? false)
  const [category,setCategory] = useState<Category | ''>(() => initialPending()?.category ?? ''), [busy,setBusy] = useState(false), [error,setError] = useState('')
  const [fileErrors,setFileErrors] = useState({person:'',garment:''})
  const [result,setResult] = useState<Blob | null>(null), [comparison,setComparison] = useState(50)
  const [now,setNow] = useState(Date.now()), [notice,setNotice] = useState('')
  const personURL = useObjectURL(person), resultURL = useObjectURL(result)
  const submitting = useRef(false), selection = useRef(jobId)
  const reportedReady = useRef(false)
  const pickSequence = useRef({person:0,garment:0})
  const extraSequence = useRef({back:0,side:0,detail:0,outer:0})
  const active = !!job && (job.state === 'queued' || job.state === 'processing' || job.upstream_active)
  const expired = !!job && (job.assets_expired || !!job.expires_at && job.expires_at * 1000 <= now)
  const ready = !!health?.comfyui.ready && !!health.supported_categories.length && !serviceError
  const views = health?.reference_modes?.multi_reference, outfits = health?.reference_modes?.two_garment
  const categories = (health?.supported_categories ?? []).filter(value => mode==='one' || mode==='views' && views?.categories.includes(value) || mode==='outfit' && outfits?.combinations.some(pair => pair.startsWith(value+'+')))
  const permittedViews = viewRoles.filter(role => (views?.reference_roles?.[category as Category] ?? viewRoles).includes(role))
  const outerChoices = (['jacket','coat'] as Category[]).filter(value => outfits?.combinations.includes(category+'+'+value))
  const modeReady = ready && categories.includes(category as Category) && (mode!=='outfit' || !!extras.outer && outerChoices.includes(outerCategory)) && (!protectRegions || mode==='one' && !!health?.spatial_protection_available)
  const protectionFallback = job?.manifest.protect_regions===true && typeof job.manifest.protection==='object' && job.manifest.protection!==null && (job.manifest.protection as {applied?:boolean}).applied===false

  function select(id: string | null) { selection.current = id; setJobId(id); if (id) write(ACTIVE,id); else remove(ACTIVE) }
  function accept(snapshot: Job) {
    select(snapshot.id); setJob(snapshot); setResult(null); setError(''); setNotice('')
    setIds(current => { const next = [snapshot.id,...current.filter(id => id !== snapshot.id)].slice(0,20); write(IDS,next); return next })
    setPending(null); remove(PENDING)
  }

  useEffect(() => {
    const connected = () => setDesktop(!!desktopAPI())
    window.addEventListener('pywebviewready',connected)
    connected()
    return () => window.removeEventListener('pywebviewready',connected)
  }, [])

  useEffect(() => {
    if (desktop && health?.comfyui.ready && !serviceError && !reportedReady.current) {
      reportedReady.current=true
      void desktopAPI()?.ready().catch(() => { reportedReady.current=false })
    }
  }, [desktop,health,serviceError])

  async function repairConnection() {
    if (repairing) return
    setRepairing(true)
    try {
      const result = await desktopAPI()?.repair()
      if (result && result.state!=='ready') setServiceError(result.message)
      else { setServiceError(''); setConnectionRevision(value => value+1) }
    } catch { setServiceError('The desktop connection was interrupted. Close and reopen ComfyFitter.') }
    finally { setRepairing(false) }
  }

  useEffect(() => {
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>
    async function poll() {
      try {
        const value = await json<Health>('/api/health',{signal:AbortSignal.any([controller.signal,AbortSignal.timeout(10000)])})
        if (controller.signal.aborted) return
        setHealth(value); setServiceError('')
        setCategory(current => current && value.supported_categories.includes(current) ? current : value.supported_categories[0] ?? '')
      } catch (problem) { if (!controller.signal.aborted) setServiceError(message(problem)) }
      if (!controller.signal.aborted) timer = setTimeout(poll,5000)
    }
    void poll(); return () => { controller.abort(); clearTimeout(timer) }
  }, [connectionRevision])

  useEffect(() => {
    if (!jobId) return
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>
    async function poll() {
      let delay = 1500
      try {
        const value = await json<Job>(`/api/try-on/${jobId}`,{signal:controller.signal})
        if (controller.signal.aborted || selection.current !== jobId) return
        setJob(value); setPollError('')
        if (value.assets_expired) { setPerson(null); setGarment(null); setExtras(blankExtras()); setResult(null) }
        if (!value.upstream_active && value.state !== 'queued' && value.state !== 'processing') delay = 15000
      } catch (problem) {
        if (controller.signal.aborted) return
        if (problem instanceof ApiError && problem.status === 404) {
          setNotice('This preview is no longer available. Upload photos for a new preview.'); select(null); setJob(null)
        } else setPollError(message(problem))
      }
      if (!controller.signal.aborted) timer = setTimeout(poll,delay)
    }
    void poll(); return () => { controller.abort(); clearTimeout(timer) }
  }, [jobId])

  useEffect(() => {
    if (!jobId) return
    const controller = new AbortController()
    async function restore() {
      try {
        const [source,reference,snapshot] = await Promise.all([photo(inputPath(jobId!,'person'),controller.signal),photo(inputPath(jobId!,'garment'),controller.signal),json<Job>(`/api/try-on/${jobId}`,{signal:controller.signal})])
        const restored = blankExtras()
        const roles = Array.isArray(snapshot.manifest.image_order) ? snapshot.manifest.image_order.filter((role): role is ExtraRole => extraRoles.includes(role as ExtraRole)) : []
        await Promise.all(roles.map(async role => { restored[role] = new File([await photo(inputPath(jobId!,role),controller.signal)],`${role} reference.png`,{type:'image/png'}) }))
        if (controller.signal.aborted || selection.current !== jobId) return
        setPerson(new File([source],'Your photo.png',{type:'image/png'})); setGarment(new File([reference],'Garment reference.png',{type:'image/png'}))
        setExtras(restored); setCategory(snapshot.category)
        setMode(snapshot.manifest.mode==='two_garment'?'outfit':snapshot.manifest.mode==='multi_reference'?'views':'one')
        setProtectRegions(snapshot.manifest.protect_regions===true)
        setSourceHasBag(snapshot.manifest.source_has_bag===true)
        if (typeof snapshot.manifest.outer_category==='string' && snapshot.manifest.outer_category in labels) setOuterCategory(snapshot.manifest.outer_category as Category)
      } catch (problem) { if (!controller.signal.aborted) setError(message(problem)) }
    }
    void restore(); return () => controller.abort()
  }, [jobId])

  useEffect(() => {
    setResult(null)
    if (!jobId || job?.state !== 'complete' || job.assets_expired) return
    const controller = new AbortController()
    photo(resultPath(jobId),controller.signal).then(blob => {
      if (!controller.signal.aborted && selection.current === jobId) setResult(blob)
    }).catch(problem => { if (!controller.signal.aborted) setError(message(problem)) })
    return () => controller.abort()
  }, [jobId,job?.state,job?.assets_expired])

  useEffect(() => {
    if (!pending) return
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>
    async function recover() {
      try {
        const found = await json<Job>(`/api/submissions/${pending!.key}`,{signal:controller.signal})
        if (!controller.signal.aborted) accept(found)
        return
      } catch (problem) {
        if (controller.signal.aborted) return
        if (!(problem instanceof ApiError && problem.status === 404)) setError(message(problem))
      }
      if (!controller.signal.aborted) timer = setTimeout(recover,2000)
    }
    void recover(); return () => { controller.abort(); clearTimeout(timer) }
  }, [pending])

  useEffect(() => { const timer = setInterval(() => setNow(Date.now()),1000); return () => clearInterval(timer) }, [])

  async function pick(role: 'person' | 'garment', file: File) {
    const sequence = ++pickSequence.current[role]
    try {
      await validatePhoto(file)
      if (pending && await hash(file) !== (role === 'person' ? pending.personHash : pending.garmentHash))
        throw new Error('Re-select the same photo to recover the unconfirmed submission.')
      if (sequence !== pickSequence.current[role]) return
      if (jobId && !active) { select(null); setJob(null); setResult(null) }
      if (role === 'person') { setPerson(file); if (!pending) setSourceHasBag(false) } else setGarment(file)
      setFileErrors(current => ({...current,[role]:''})); setError(''); setNotice('')
    } catch (problem) { if (sequence === pickSequence.current[role]) setFileErrors(current => ({...current,[role]:problem instanceof Error ? problem.message : 'Choose another photo.'})) }
  }

  async function generate(event?: FormEvent, retryCategory?: Category, previousSeed?: number) {
    event?.preventDefault()
    if (submitting.current || !person || !garment || (!category && !pending) || active || (!modeReady && !pending)) return
    submitting.current = true; setBusy(true); setError(''); setNotice('')
    let request = pending
    try {
      if (!request) {
        let seed = crypto.getRandomValues(new Uint32Array(1))[0]
        if (seed === previousSeed) seed = (seed + 1) >>> 0
        const extraHashes: Partial<Record<ExtraRole,string>> = {}
        for (const role of mode==='views'?permittedViews:mode==='outfit'?['outer'] as ExtraRole[]:[]) if (extras[role]) extraHashes[role] = await hash(extras[role]!)
        request = {key:crypto.randomUUID(),category:retryCategory ?? category as Category,seed,
          personHash:await hash(person),garmentHash:await hash(garment),mode,extraHashes,outerCategory:mode==='outfit'?outerCategory:undefined,protectRegions:mode==='one'&&protectRegions,sourceHasBag:mode==='outfit'&&outfits?.validated_source_bag_options?sourceHasBag:undefined}
        setPending(request); write(PENDING,request)
      }
      const body = new FormData(); body.set('person',person); body.set('garment',garment)
      body.set('category',request.category); body.set('seed',String(request.seed))
      if (await hash(person)!==request.personHash || await hash(garment)!==request.garmentHash) throw new Error('Re-select the same photos to recover this submission.')
      for (const role of extraRoles) if (request.extraHashes?.[role]) {
        if (!extras[role] || await hash(extras[role]!)!==request.extraHashes[role]) throw new Error(`Re-select the same ${role} reference to recover this submission.`)
        body.set(role,extras[role]!)
      }
      if (request.outerCategory) body.set('outer_category',request.outerCategory)
      body.set('protect_regions',String(request.protectRegions ?? false))
      if (request.sourceHasBag!==undefined) body.set('source_has_bag',String(request.sourceHasBag))
      const value = await json<Job>('/api/try-on',{method:'POST',body,headers:{'Idempotency-Key':request.key},signal:AbortSignal.timeout(30000)})
      accept(value)
    } catch (problem) {
      setError(message(problem))
      if (request && problem instanceof ApiError && problem.status < 500) {
        try { accept(await json<Job>(`/api/submissions/${request.key}`)) }
        catch (lookup) { if (lookup instanceof ApiError && lookup.status === 404) { setPending(null); remove(PENDING) } }
      }
    } finally { submitting.current = false; setBusy(false) }
  }

  async function retry() {
    if (!job || active || expired || !modeReady || pending) return
    setCategory(job.category)
    await generate(undefined,job.category,job.seed)
  }

  function removePhoto(role: 'person' | 'garment') {
    ++pickSequence.current[role]
    if (jobId && !active) { select(null); setJob(null); setResult(null); setPollError('') }
    if (role === 'person') { setPerson(null); setSourceHasBag(false) } else setGarment(null)
    setFileErrors(current => ({...current,[role]:''}))
  }

  async function pickExtra(role: ExtraRole, file: File) {
    const sequence = ++extraSequence.current[role]
    try {
      await validatePhoto(file)
      if (pending && await hash(file)!==pending.extraHashes?.[role]) throw new Error('Re-select the same reference to recover the unconfirmed submission.')
      if (sequence!==extraSequence.current[role]) return
      if (jobId && !active) { select(null); setJob(null); setResult(null) }
      setExtras(current => ({...current,[role]:file})); setExtraErrors(current => ({...current,[role]:''})); setError(''); setNotice('')
    } catch (problem) { if (sequence===extraSequence.current[role]) setExtraErrors(current => ({...current,[role]:problem instanceof Error?problem.message:'Choose another photo.'})) }
  }
  function removeExtra(role: ExtraRole) {
    ++extraSequence.current[role]
    if (jobId && !active) { select(null); setJob(null); setResult(null) }
    setExtras(current => ({...current,[role]:null})); setExtraErrors(current => ({...current,[role]:''}))
  }
  function changeMode(next: Mode) {
    if (jobId && !active) { select(null); setJob(null); setResult(null) }
    extraRoles.forEach(role => ++extraSequence.current[role]); setExtras(blankExtras()); setExtraErrors({}); setMode(next); setProtectRegions(false)
    const available = (health?.supported_categories ?? []).filter(value => next==='one' || next==='views' && views?.categories.includes(value) || next==='outfit' && outfits?.combinations.some(pair => pair.startsWith(value+'+')))
    const selected = available.includes(category as Category)?category:available[0] ?? ''
    setCategory(selected)
    const outer = next==='outfit' ? outfits?.combinations.find(pair => pair.startsWith(selected+'+'))?.split('+')[1] : undefined
    if (outer) setOuterCategory(outer as Category)
  }
  function changeCategory(next: Category) {
    if (jobId && !active) { select(null); setJob(null); setResult(null) }
    extraRoles.forEach(role => ++extraSequence.current[role]); setExtras(blankExtras()); setExtraErrors({}); setCategory(next)
    if (mode==='outfit') { const outer=outfits?.combinations.find(pair=>pair.startsWith(next+'+'))?.split('+')[1]; if (outer) setOuterCategory(outer as Category) }
  }

  async function deletePreview() {
    if (!job || active) return
    setBusy(true); setError('')
    try {
      const value = await json<Job>(`/api/try-on/${job.id}`,{method:'DELETE'})
      setJob(value); setPerson(null); setGarment(null); setExtras(blankExtras()); setResult(null)
      setNotice('Preview images deleted. Downloaded copies remain wherever you saved them.')
    } catch (problem) { setError(message(problem)) } finally { setBusy(false) }
  }
  function newPreview() { pickSequence.current.person++; pickSequence.current.garment++; extraRoles.forEach(role => ++extraSequence.current[role]); select(null); setJob(null); setPerson(null); setGarment(null); setExtras(blankExtras()); setExtraErrors({}); setMode('one'); setProtectRegions(false); setResult(null); setError(''); setNotice(''); setFileErrors({person:'',garment:''}) }
  const badge = serviceError ? 'Application offline' : !health ? 'Checking services' : health.comfyui.ready ? 'Image service ready' : health.comfyui.reachable ? 'Image service setup needed' : 'Image service offline'
  const status = job?.state === 'queued' ? 'Waiting to start' : job?.state === 'processing' ? job.stage === 'protecting_source' ? 'Preserving the original photo' : job.stage === 'reconciling_submission' ? 'Recovering submission' : 'Creating your preview' : job?.state === 'failed' ? job.upstream_active ? 'Taking longer; still tracking' : 'Preview could not be created' : job?.state === 'complete' ? 'Your preview' : 'Your fitting room'

  return <div className="app-shell">
    <header className="app-header"><a href="/" className="brand" aria-label="ComfyFitter home"><span className="brand-tag" aria-hidden="true">CF</span><span>ComfyFitter<small>{health?.deployment_mode==='hosted'?'Private fitting room':'Local fitting room'}</small></span></a>
      <div className={'service-badge ' + (health?.comfyui.ready && !serviceError ? 'is-ready' : '')}><span aria-hidden="true" className="status-dot" />{badge}</div></header>
    <main><div className="workspace-heading"><div><p className="eyebrow">A different garment. Still you.</p><h1>Try a new look.</h1><p className="intro">Pair your photo with a garment reference to create a visual preview.</p></div>
      <button type="button" className="secondary-button" disabled={active || busy || !!pending} onClick={newPreview}>New preview <span aria-hidden="true">↗</span></button></div>
      {(error || serviceError || pollError) && <div className="alert" role="alert">{error || serviceError || pollError}</div>}
      {(serviceError || health && !health.comfyui.ready) && <div className="connection-recovery">
        <p>{desktop ? 'Restore the local services to continue. Running previews and saved looks are preserved.' : 'Open the ComfyFitter desktop shortcut to start the local services. Waiting here does not start them.'}</p>
        {desktop && <button type="button" className="secondary-button" disabled={repairing} onClick={() => void repairConnection()}>{repairing ? 'Starting local services…' : 'Reconnect local services'}</button>}
      </div>}
      {notice && <p className="notice" role="status">{notice}</p>}
      {health && !health.comfyui.ready && <div className="setup-note"><strong>{badge}.</strong> {health.comfyui.error?.message}
        {!!(health.comfyui.error?.missing_models?.length || health.comfyui.error?.missing_nodes?.length) && <details><summary>Setup details</summary><p>{[...health.comfyui.error.missing_nodes ?? [],...health.comfyui.error.missing_models ?? []].join(', ')}</p></details>}</div>}
      <div className="workspace-grid"><form className="input-panel" onSubmit={generate}>
        <div className="panel-heading"><h2>The pairing</h2><span className="utility">{2+extraRoles.filter(role => !!extras[role]).length} photos</span></div>
        {(views || outfits || mode!=='one') && <><label className="field-label" htmlFor="reference-mode">Reference options</label><select id="reference-mode" value={mode} disabled={active || busy || !!pending} onChange={event => changeMode(event.target.value as Mode)}><option value="one">One garment reference</option>{(views || mode==='views') && <option value="views">More views of one garment</option>}{(outfits || mode==='outfit') && <option value="outfit">Two layered garments</option>}</select></>}
        <div className="upload-pair"><Upload role="person" file={person} disabled={active || busy} error={fileErrors.person} onFile={file => void pick('person',file)} onRemove={() => removePhoto('person')} />
          <Upload role="garment" file={garment} disabled={active || busy} error={fileErrors.garment} onFile={file => void pick('garment',file)} onRemove={() => removePhoto('garment')} /></div>
        <label className="field-label" htmlFor="category">{mode==='outfit'?'Inner garment category':'Garment category'}</label><select id="category" value={pending?.category ?? category} disabled={active || busy || !!pending || !categories.length} onChange={event => changeCategory(event.target.value as Category)} aria-describedby="category-help">
          {pending && !categories.includes(pending.category) && <option value={pending.category}>{labels[pending.category]}</option>}
          {!pending && !categories.length && <option value="">No validated categories yet</option>}{categories.map(value => <option key={value} value={value}>{labels[value]}</option>)}</select>
        <p id="category-help" className="form-help">{health?.supported_categories.length ? 'Only categories checked for this workflow are offered.' : 'Generation becomes available after garment categories finish validation.'}</p>
        {mode==='views' && <><p className="form-help">Start with the front reference above. Add available views of that same garment. Keep each view in its labeled slot.</p><div className="extra-references">{permittedViews.map(role => <Upload key={role} role="garment" title={`${role[0].toUpperCase()+role.slice(1)} reference`} file={extras[role]} disabled={active || busy} error={extraErrors[role] ?? ''} onFile={file => void pickExtra(role,file)} onRemove={() => removeExtra(role)} />)}</div></>}
        {mode==='outfit' && <><label className="field-label" htmlFor="outer-category">Outer garment category</label><select id="outer-category" value={pending?.outerCategory ?? outerCategory} disabled={active || busy || !!pending} onChange={event => setOuterCategory(event.target.value as Category)}>{outerChoices.map(value => <option key={value} value={value}>{labels[value]}</option>)}</select><p className="form-help">The first reference is the inner garment. Add the outer garment to wear open over it.</p><Upload role="garment" title="Outer garment reference" file={extras.outer} disabled={active || busy} error={extraErrors.outer ?? ''} onFile={file => void pickExtra('outer',file)} onRemove={() => removeExtra('outer')} /></>}
        {mode==='outfit' && outfits?.validated_source_bag_options && <div className="protection-choice"><label><input type="checkbox" checked={pending?.sourceHasBag ?? sourceHasBag} disabled={active || busy || !!pending} onChange={event => setSourceHasBag(event.target.checked)} /> My photo includes a bag or backpack</label><p className="form-help">Keep its visible straps over the new coat. Leave unchecked when your photo has no bag.</p></div>}
        {mode==='one' && (health?.spatial_protection_available || protectRegions) && <div className="protection-choice"><label><input type="checkbox" checked={protectRegions} disabled={active || busy || !!pending || !health?.spatial_protection_available} onChange={event => setProtectRegions(event.target.checked)} /> Preserve regions outside the changed garment</label><p className="form-help">When a boundary is uncertain, keep the standard preview.</p></div>}
        {pending && <p className="pending-note" role="status">Checking an unconfirmed submission. Keep the same photos; a retry uses the original request key.</p>}
        <button type="submit" className="primary-button" disabled={busy || active || !person || !garment || (!modeReady && !pending)}>{busy ? 'Sending photos…' : pending ? 'Retry submission' : 'Generate preview'}<span aria-hidden="true">↗</span></button>
        <p className="privacy-note"><span aria-hidden="true">⌂</span> {health?.deployment_mode==='hosted'?'Images are stored privately on the application server.':'Images stay on this device.'} Temporary job images are deleted 24 hours after completion or failure. Downloads remain under your control.</p>
      </form><section className="result-panel" aria-labelledby="preview-heading">
        <div className="panel-heading"><div><p className="eyebrow">The preview</p><h2 id="preview-heading">{expired ? 'Preview expired or deleted' : status}</h2></div>{job && <span className="utility">{job.id.slice(0,8)}</span>}</div>
        <div className={'comparison-stage ' + (active ? 'is-working' : '')}>
          {personURL && !expired ? <img className="comparison-image" src={personURL} alt="Original photo" /> : <div className="empty-preview"><div className="fitting-outline" aria-hidden="true"><span /></div><h3>Make room for a new look.</h3><p>Add your photo and a garment.<br />Your preview will appear here.</p></div>}
          {resultURL && !expired && <><div className="after-layer" style={{clipPath:`inset(0 ${100-comparison}% 0 0)`}}><img className="comparison-image" src={resultURL} alt="Generated garment preview" /></div><div className="comparison-divider" style={{left:`${comparison}%`}} aria-hidden="true"><span>↔</span></div><span className="image-label after-label">Preview</span><span className="image-label before-label">Original</span></>}
          {active && <div className="working-label" role="status"><span className="working-dot" aria-hidden="true" />{status}<small>You can refresh this page. Your job continues.</small></div>}
        </div>
        {resultURL && !expired && <div className="comparison-control"><label htmlFor="comparison">Move the slider to compare</label><input id="comparison" type="range" min="0" max="100" value={comparison} onChange={event => setComparison(Number(event.target.value))} aria-valuetext={`${comparison}% preview revealed`} /></div>}
        {job?.error && <p className="job-error" role="alert">{job.error.message}</p>}
        {job?.state==='complete' && protectionFallback && <p className="notice" role="status">Source protection kept the standard preview for this photo.</p>}
        <div className="result-actions">{resultURL && job && !expired && !busy ? <a className="primary-button" href={resultPath(job.id)} download={`comfyfitter-${job.id}.png`}>Download preview <span aria-hidden="true">↓</span></a> : <button type="button" className="primary-button" disabled>Download preview <span aria-hidden="true">↓</span></button>}
          <button type="button" className="secondary-button" disabled={!job || active || expired || busy || !person || !garment || !modeReady || !!pending} onClick={() => void retry()}>Try another seed</button>
          <button type="button" className="text-button delete-button" disabled={!job || active || expired || busy} onClick={() => void deletePreview()}>Delete preview</button></div>
        <p className="preview-caption">{job?.expires_at && !expired ? `Available until ${new Date(job.expires_at*1000).toLocaleString()}. ` : ''}Visual preview only. It does not predict clothing size or physical fit.</p>
      </section></div>
      {ids.length > 0 && <div className="temporary-jobs"><label htmlFor="temporary-jobs">Temporary previews on this browser</label><select id="temporary-jobs" value={jobId ?? ''} disabled={busy || !!pending} onChange={event => { select(event.target.value || null); setJob(null); setResult(null); setPerson(null); setGarment(null); setError('') }}><option value="">Choose a preview</option>{ids.map(id => <option key={id} value={id}>Preview {id.slice(0,8)}</option>)}</select><span>Job links only; photos are not saved in browser storage.</span></div>}
      <SavedLooks job={job} expired={expired} hosted={health?.deployment_mode==='hosted'}/>
    </main><footer><span>ComfyFitter</span><span>{health?.deployment_mode==='hosted'?'Private images.':'Local images.'} A little possibility.</span></footer>
  </div>
}
