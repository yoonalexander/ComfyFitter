const button=document.querySelector('#open-room'),status=document.querySelector('#connection')
fetch('/api/room',{cache:'no-store'}).then(async response=>{
  if(!response.ok)throw new Error('offline')
  const room=await response.json()
  if(room.available&&typeof room.url==='string'&&/^https:\/\/[a-z0-9-]+\.trycloudflare\.com$/.test(room.url)){
    button.href=room.url;button.removeAttribute('aria-disabled');button.textContent='Open private fitting room ↗'
    status.textContent='Email sign-in required. Available while your GPU PC is running.'
  }else if(room.paused){
    button.textContent='Web access paused';status.textContent='ComfyFitter is being improved as a desktop app first. Use the ComfyFitter shortcut on your Windows PC.'
    document.querySelector('#room-heading').textContent='Your desktop fitting room.'
    const details=document.querySelector('.details').children
    details[0].textContent='Open the ComfyFitter shortcut on your Windows desktop. The app starts its local services and runs image generation on your GPU.'
    details[1].textContent='Your photos stay on your PC. This is a visual preview for personal evaluation; it does not predict clothing size or physical fit.'
  }else{
    button.textContent='Connection pending';status.textContent='The private fitting room connection is being set up. Image generation is not available here yet.'
  }
}).catch(()=>{button.textContent='Connection unavailable';status.textContent='The fitting room connection could not be loaded. Refresh this page to try again.'})
