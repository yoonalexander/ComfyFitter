import assert from 'node:assert/strict'
import test from 'node:test'
import {readFile} from 'node:fs/promises'
import {stripTypeScriptTypes} from 'node:module'

const source=await readFile(new URL('../src/api.ts',import.meta.url),'utf8')
const js=stripTypeScriptTypes(source,{mode:'transform'})
const {json,message,ApiError}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'))

test('an authentication HTML page is classified as a connection failure',async()=>{
  const previous=globalThis.fetch
  globalThis.fetch=async()=>new Response('<html>Sign in</html>',{headers:{'Content-Type':'text/html'}})
  try {await assert.rejects(json('/api/health'),error=>error instanceof ApiError && error.code==='CONNECTION_REOPEN_REQUIRED')}
  finally {globalThis.fetch=previous}
})
test('network failure gives an action instead of telling the user to keep waiting',()=>{
  assert.match(message(new TypeError('Failed to fetch')),/Reconnect local services/)
  assert.doesNotMatch(message(new TypeError('Failed to fetch')),/Keep this page open/)
})
test('image validation instructions are retained',()=>{
  assert.equal(message(new Error('Choose a PNG, JPEG or WebP photo.')),'Choose a PNG, JPEG or WebP photo.')
})
test('successful health JSON is parsed',async()=>{
  const previous=globalThis.fetch
  globalThis.fetch=async()=>Response.json({application:'comfyfitter',comfyui:{ready:true}})
  try {assert.equal((await json('/api/health')).comfyui.ready,true)}
  finally {globalThis.fetch=previous}
})
