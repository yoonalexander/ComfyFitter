import { useEffect, useState } from 'react'
import { json, message, photo, type Job } from './api'
import { useObjectURL } from './Upload'
type Look = {id:string;name:string;category:string;created_at:number}
type Library = {looks:Look[];used_bytes:number;max_bytes:number;max_looks:number}
export default function SavedLooks({job,expired,hosted=false}:{job:Job|null;expired:boolean;hosted?:boolean}) {
  const location=hosted?'privately on the application server':'on this device'
  const [library,setLibrary]=useState<Library|null>(null),[selected,setSelected]=useState<Look|null>(null)
  const [name,setName]=useState(''),[consent,setConsent]=useState(false),[busy,setBusy]=useState(false)
  const [error,setError]=useState(''),[notice,setNotice]=useState('')
  const [source,setSource]=useState<Blob|null>(null),[result,setResult]=useState<Blob|null>(null)
  const sourceURL=useObjectURL(source),resultURL=useObjectURL(result)
  async function load(){setLibrary(await json<Library>('/api/looks'))}
  useEffect(()=>{void load().catch(e=>setError(message(e)))},[])
  useEffect(()=>{
    const controller=new AbortController();setSource(null);setResult(null)
    if(selected) Promise.all([photo(`/api/looks/${selected.id}/inputs/person`,controller.signal),photo(`/api/looks/${selected.id}/result`,controller.signal)])
      .then(([a,b])=>{if(!controller.signal.aborted){setSource(a);setResult(b)}}).catch(e=>{if(!controller.signal.aborted)setError(message(e))})
    return()=>controller.abort()
  },[selected])
  async function save(){
    if(!job||!consent)return
    setBusy(true);setError('');setNotice('')
    try{
      const look=await json<Look>('/api/looks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({job_id:job.id,name:name.trim(),consent:true})})
      await load();setSelected(look);setName('');setConsent(false);setNotice(`Look saved ${location} until you delete it.`)
    }catch(e){setError(message(e))}finally{setBusy(false)}
  }
  async function erase(){
    if(!selected)return
    setBusy(true);setError('');setNotice('')
    try{
      const response=await fetch(`/api/looks/${selected.id}`,{method:'DELETE',cache:'no-store'})
      if(!response.ok){const body=await response.json();throw new Error(body.error?.message??'The saved look could not be deleted.')}
      setSelected(null);await load();setNotice('Saved look and stored photos deleted. Downloaded copies remain under your control.')
    }catch(e){setError(e instanceof Error?e.message:message(e))}finally{setBusy(false)}
  }
  return <section className="saved-looks" aria-labelledby="saved-heading"><div className="panel-heading"><h2 id="saved-heading">Keep a look</h2><span className="utility">Optional · {hosted?'private storage':'on this device'}</span></div>
    <p className="form-help">Saved looks keep copies of your original photo, all garment references and preview after temporary jobs expire. They stay until you delete them.</p>
    {job?.state==='complete'&&!expired&&<div className="save-form"><label className="field-label" htmlFor="look-name">Look name</label><input id="look-name" value={name} maxLength={80} onChange={e=>setName(e.target.value)} placeholder="For example, denim day" disabled={busy}/>
      <label className="consent-label"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)} disabled={busy}/>Keep copies of these photos {location} until I delete this look.</label>
      <button className="secondary-button" onClick={()=>void save()} disabled={busy||!consent||!name.trim()}>Save this look</button></div>}
    {error&&<p className="job-error" role="alert">{error}</p>}{notice&&<p className="notice" role="status">{notice}</p>}
    {library&&<p className="library-size">{library.looks.length}/{library.max_looks} saved looks · {(library.used_bytes/1048576).toFixed(1)}/{Math.floor(library.max_bytes/1048576)} MiB</p>}
    {!library?.looks.length?<p className="form-help">No saved looks yet. Saving is always your choice.</p>:<><label className="field-label" htmlFor="saved-look">Saved looks</label><select id="saved-look" value={selected?.id??''} disabled={busy} onChange={e=>{setSelected(library.looks.find(l=>l.id===e.target.value)??null);setError('')}}><option value="">Choose a saved look</option>{library.looks.map(l=><option key={l.id} value={l.id}>{l.name}</option>)}</select></>}
    {selected&&<div className="saved-detail"><h3>{selected.name}</h3><p className="form-help">{selected.category} · saved {new Date(selected.created_at*1000).toLocaleDateString()}</p><div className="saved-comparison">{sourceURL&&<figure><img src={sourceURL} alt={'Original photo for '+selected.name}/><figcaption>Original</figcaption></figure>}{resultURL&&<figure><img src={resultURL} alt={'Saved preview for '+selected.name}/><figcaption>Preview</figcaption></figure>}</div>
      <div className="result-actions">{resultURL&&<a className="secondary-button" href={`/api/looks/${selected.id}/result`} download={`comfyfitter-look-${selected.id}.png`}>Download saved preview</a>}<button className="text-button delete-button" disabled={busy} onClick={()=>void erase()}>Delete saved look and photos</button></div></div>}
  </section>
}
