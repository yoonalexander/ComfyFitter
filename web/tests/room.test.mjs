import {test} from 'node:test'
import assert from 'node:assert/strict'
import handler, {roomURL} from '../api/room.mjs'
test('only an HTTPS protected-tunnel origin is a valid destination',()=>{
  assert.equal(roomURL('https://private-room.trycloudflare.com/'),'https://private-room.trycloudflare.com')
  for(const url of [undefined,'','http://room.trycloudflare.com','https://evil.example','https://room.trycloudflare.com.evil.example','https://room.trycloudflare.com:8443','https://user:password@room.trycloudflare.com','https://room.trycloudflare.com/path','https://room.trycloudflare.com/?token=secret','https://room.trycloudflare.com/#secret']) assert.equal(roomURL(url),null)
})
test('missing connection is explicit and never redirects to localhost',()=>{
  const prior=process.env.COMFYFITTER_PRIVATE_URL
  delete process.env.COMFYFITTER_PRIVATE_URL
  const response={headers:{},setHeader(k,v){this.headers[k]=v},status(n){this.code=n;return this},json(v){this.body=v}}
  handler({method:'GET'},response)
  assert.deepEqual(response.body,{url:null,available:false})
  assert.equal(response.headers['Cache-Control'],'no-store')
  if(prior!==undefined) process.env.COMFYFITTER_PRIVATE_URL=prior
})
