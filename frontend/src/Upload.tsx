import { useEffect, useId, useState } from 'react'

export function useObjectURL(blob: Blob | null) {
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => {
    if (!blob) { setUrl(null); return }
    const next = URL.createObjectURL(blob)
    setUrl(next)
    return () => URL.revokeObjectURL(next)
  }, [blob])
  return url
}

export default function Upload({role, file, disabled, error, onFile, onRemove,title:customTitle}: {
  role: 'person' | 'garment'; file: File | null; disabled: boolean; error: string;
  onFile: (file: File) => void; onRemove: () => void; title?:string
}) {
  const id = useId(), url = useObjectURL(file)
  const title = customTitle ?? (role === 'person' ? 'Your photo' : 'Garment reference')
  return <fieldset className="upload-slot" disabled={disabled}>
    <legend>{title}</legend>
    <label className={'upload-zone ' + (file ? 'has-photo' : '')} htmlFor={id}
      onDragOver={event => event.preventDefault()} onDrop={event => {
        event.preventDefault(); if (!disabled && event.dataTransfer.files[0]) onFile(event.dataTransfer.files[0])
      }}>
      <input id={id} className="sr-only" type="file" accept="image/png,image/jpeg,image/webp"
        aria-label={title}
        aria-describedby={id + '-help ' + id + '-error'} onChange={event => {
          const selected = event.target.files?.[0]; if (selected) onFile(selected); event.target.value = ''
        }} />
      {url ? <img src={url} alt={role === 'person' ? 'Your selected photo' : 'Selected garment reference'} /> :
        <span className="upload-invitation"><span aria-hidden="true" className="upload-mark">+</span>
          <strong>Choose {role === 'person' ? 'a photo' : 'a garment'}</strong><span>or drop it here</span></span>}
      {file && <span className="replace-photo">Replace photo</span>}
    </label>
    <div className="file-caption"><span title={file?.name}>{file?.name ?? 'PNG, JPEG or WebP · up to 10 MiB'}</span>
      {file && <button type="button" className="text-button" onClick={onRemove} aria-label={'Remove ' + title.toLowerCase()}>Remove</button>}</div>
    <p id={id + '-help'} className="upload-help">{role === 'person' ?
      'Use a clear photo with your upper body visible. Keep the pose natural.' :
      'Show one garment clearly, including its collar, sleeves and details.'}</p>
    {error && <p id={id + '-error'} className="field-error" role="alert">{error}</p>}
  </fieldset>
}
