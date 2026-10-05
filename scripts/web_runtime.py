"""Start/stop the owner's protected temporary web connection without installing a service."""
import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / '.local/web'
STATE = DIRECTORY / 'processes.json'
CONFIG = DIRECTORY / 'config.json'
EXE = ROOT / '.local/tools/cloudflared.exe'
RELEASE_HASH = 'f096265ec2fcbe9bb6e2d64268db167ced3fcbb83d894bdb9e2fcdb26f2ea7e2'

def write_json(path, value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2)+'\n')
    temporary.replace(path)

def valid_email(value):
    # This shares the existing local owner's library. Never admit a domain or multiple owners.
    return bool(re.fullmatch(r'[A-Za-z0-9._+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,63}',value))

def start(email):
    if os.name!='nt': raise RuntimeError('This launcher is for the evaluated Windows GPU PC')
    if not valid_email(email): raise ValueError('Use one exact owner email, without a wildcard or recipient list')
    if STATE.exists(): raise RuntimeError('A web connection is already recorded. Stop it before starting another.')
    if not EXE.is_file() or hashlib.sha256(EXE.read_bytes()).hexdigest()!=RELEASE_HASH:
        raise RuntimeError('The verified official cloudflared 2026.9.3 executable is required')
    with httpx.Client(trust_env=False,timeout=5) as client:
        health=client.get('http://127.0.0.1:8000/api/health').json()
    if health.get('application')!='comfyfitter' or not health.get('comfyui',{}).get('ready'):
        raise RuntimeError('Start the qualified local ComfyFitter application and GPU worker first')
    DIRECTORY.mkdir(parents=True,exist_ok=True)
    private_host=secrets.token_hex(32)+'.localhost'
    write_json(CONFIG,{'private_host':private_host,'public_origin':'','upstream':'http://127.0.0.1:8000'})
    empty_config=DIRECTORY/'cloudflared.yaml'
    empty_config.write_text('{}\n')
    environment=os.environ.copy()
    for key in list(environment):
        if key.startswith('TUNNEL_'): environment.pop(key)
    environment['COMFYFITTER_WEB_CONFIG']=str(CONFIG)
    flags=subprocess.CREATE_NO_WINDOW
    gateway_log=(DIRECTORY/'gateway.log').open('w')
    tunnel_log=(DIRECTORY/'tunnel.log').open('w')
    gateway=None;tunnel=None
    try:
        gateway=subprocess.Popen([sys.executable,'-m','uvicorn','scripts.web_gateway:application','--factory',
            '--host','127.0.0.1','--port','8001','--workers','1','--no-access-log','--no-proxy-headers'],
            cwd=ROOT,env=environment,stdout=gateway_log,stderr=gateway_log,creationflags=flags)
        with httpx.Client(trust_env=False,timeout=2) as client:
            for i in range(60):
                if gateway.poll() is not None: raise RuntimeError('Private gateway startup failed; no tunnel was started')
                try:
                    result=client.get('http://127.0.0.1:8001/api/health',headers={'Host':private_host})
                    if result.status_code==503 and result.json()['error']['code']=='CONNECTION_PENDING':break
                except httpx.HTTPError:pass
                time.sleep(.25)
            else: raise RuntimeError('Private gateway readiness was not confirmed')
        tunnel=subprocess.Popen([str(EXE),'tunnel','--config',str(empty_config),'--no-autoupdate',
            '--protocol','http2','--metrics','127.0.0.1:20242','--url','http://127.0.0.1:8001',
            '--http-host-header',private_host,'--allowed-mail',email],cwd=ROOT,env=environment,
            stdout=tunnel_log,stderr=tunnel_log,creationflags=flags)
        for i in range(180):
            if tunnel.poll() is not None: raise RuntimeError('Protected tunnel startup failed; the gateway will be stopped')
            logs=(DIRECTORY/'tunnel.log').read_text(errors='replace')
            found=re.search(r'https://([a-z0-9-]+\.trycloudflare\.com)',logs)
            protected=('Your protected quick Tunnel has been created!' in logs
                       and 'Authentication: One-Time PIN (using Cloudflare Access)' in logs
                       and 'Allowed recipients: 1 address' in logs)
            if found and protected and 'Registered tunnel connection' in logs:break
            time.sleep(.5)
        else:raise RuntimeError('A registered tunnel with exactly one email rule was not confirmed; connection stopped')
        origin=found.group(0)
        write_json(CONFIG,{'private_host':private_host,'public_origin':origin,'upstream':'http://127.0.0.1:8000'})
        write_json(STATE,{'gateway_pid':gateway.pid,'tunnel_pid':tunnel.pid,'python':sys.executable,
                         'cloudflared':str(EXE),'url':origin,'email_protection':True,'allowed_addresses':1,
                         'application_pid':health.get('process_id'),'created_at':time.time()})
        print('Protected private fitting room: '+origin)
        print('Exactly one owner email is allowed. The PC must remain on. No paid service was created.')
    except BaseException:
        for process in [tunnel,gateway]:
            if process is not None and process.poll() is None:process.terminate()
        write_json(CONFIG,{'private_host':private_host,'public_origin':'','upstream':'http://127.0.0.1:8000'})
        raise
    finally:
        gateway_log.close();tunnel_log.close()

def stop():
    if not STATE.exists():print('No launcher-owned web connection is recorded.');return
    state=json.loads(STATE.read_text())
    # Verify the live process path and command before terminating; preserve a reused PID.
    for role in ['tunnel','gateway']:
        pid=int(state[role+'_pid'])
        script=f'Get-CimInstance Win32_Process -Filter "ProcessId={pid}" | Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress'
        result=subprocess.run(['powershell.exe','-NoProfile','-Command',script],capture_output=True,text=True,check=True)
        if not result.stdout.strip():continue
        live=json.loads(result.stdout)
        expected=state['cloudflared' if role=='tunnel' else 'python']
        expected_marker='--allowed-mail' if role=='tunnel' else 'scripts.web_gateway:application'
        if (Path(live.get('ExecutablePath') or '').resolve()!=Path(expected).resolve()
                or expected_marker not in (live.get('CommandLine') or '')):
            raise RuntimeError('Recorded process ownership no longer matches; it was preserved')
        subprocess.run(['powershell.exe','-NoProfile','-Command',f'Stop-Process -Id {pid}'],check=True,capture_output=True)
    config=json.loads(CONFIG.read_text());config['public_origin']='';write_json(CONFIG,config)
    STATE.unlink()
    print('Protected web connection stopped. Local ComfyFitter and ComfyUI remain running.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start','stop'])
    parser.add_argument('--allowed-email')
    args=parser.parse_args()
    if args.action=='start':
        if not args.allowed_email:parser.error('start requires --allowed-email for exactly one owner')
        start(args.allowed_email)
    else:stop()
