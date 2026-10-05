import {test} from 'node:test'
import assert from 'node:assert/strict'
import handler, {roomURL} from '../api/room.mjs'
test('only an HTTPS protected-tunnel origin is a valid destination',()=>{
  assert.equal(roomURL('https://private-room.trycloudflare.com/'),'https://private-room.trycloudflare.com')
  for(const url of [undefined,'','http://room.trycloudflare.com','https://evil.example','https://room.trycloudflare.com.evil.example','https://room.trycloudflare.com:8443','https://user:password@room.trycloudflare.com','https://room.trycloudflare.com/path','https://room.trycloudflare.com/?token=secret','https://room.trycloudflare.com/#secret']) assert.equal(roomURL(url),null)
})
test('missing connection is explicit and never redirects to localhost',()=>{
  const prior=process.env.COMFYFITTER_PRIVATE_URL
  const enabled=process.env.COMFYFITTER_WEB_ENABLED
  process.env.COMFYFITTER_WEB_ENABLED='true'
  delete process.env.COMFYFITTER_PRIVATE_URL
  const response={headers:{},setHeader(k,v){this.headers[k]=v},status(n){this.code=n;return this},json(v){this.body=v}}
  handler({method:'GET'},response)
  assert.deepEqual(response.body,{url:null,available:false})
  assert.equal(response.headers['Cache-Control'],'no-store')
  if(prior!==undefined) process.env.COMFYFITTER_PRIVATE_URL=prior
  if(enabled===undefined)delete process.env.COMFYFITTER_WEB_ENABLED
  else process.env.COMFYFITTER_WEB_ENABLED=enabled
})

test('web access defaults to paused even if an old tunnel URL remains configured',()=>{
  const prior=process.env.COMFYFITTER_PRIVATE_URL,enabled=process.env.COMFYFITTER_WEB_ENABLED
  process.env.COMFYFITTER_PRIVATE_URL='https://old-room.trycloudflare.com'
  delete process.env.COMFYFITTER_WEB_ENABLED
  const response={setHeader(){},status(){return this},json(v){this.body=v}}
  handler({method:'GET'},response)
  assert.deepEqual(response.body,{url:null,available:false,paused:true})
  if(prior===undefined)delete process.env.COMFYFITTER_PRIVATE_URL
  else process.env.COMFYFITTER_PRIVATE_URL=prior
  if(enabled!==undefined)process.env.COMFYFITTER_WEB_ENABLED=enabled
})
