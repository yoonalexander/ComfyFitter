"""Start local services without replacing a running process or resubmitting work."""
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
APP_URL = 'http://127.0.0.1:8000'
WORKER_URL = 'http://127.0.0.1:8188'


def port_open(port):
    with socket.socket() as connection:
        connection.settimeout(.5)
        return connection.connect_ex(('127.0.0.1', port)) == 0


class Services:
    def __init__(self, root=ROOT, timeout=240, sleep=time.sleep, clock=time.monotonic):
        self.root = Path(root)
        self.timeout, self.sleep, self.clock = timeout, sleep, clock
        self.lock = threading.Lock()
        self.state = {'state': 'starting', 'message': 'Starting your local fitting room…'}
        self.processes = {}

    def status(self):
        return dict(self.state)

    def health(self):
        try:
            with httpx.Client(trust_env=False, timeout=4) as client:
                response = client.get(APP_URL + '/api/health')
                response.raise_for_status()
                health = response.json()
        except (httpx.HTTPError, ValueError):
            return None
        if not isinstance(health, dict) or health.get('application') != 'comfyfitter' or health.get('deployment_mode') != 'local':
            raise RuntimeError('Port 8000 belongs to another application or hosted configuration. It was left running.')
        if not isinstance(health.get('comfyui'), dict):
            raise RuntimeError('The local application returned an invalid readiness response. Reopen ComfyFitter after checking the logs.')
        return health

    def launch(self, role, command, cwd, environment):
        previous = self.processes.get(role)
        if previous is not None and previous.poll() is None:
            return previous
        logs = self.root / '.local/logs'
        logs.mkdir(parents=True, exist_ok=True)
        with (logs / ('desktop-' + role + '.log')).open('a') as log:
            process = subprocess.Popen(command, cwd=cwd, env=environment, stdout=log, stderr=log,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
        self.processes[role] = process
        return process

    def worker_root(self):
        config = self.root / '.local/desktop/config.json'
        settings = json.loads(config.read_text(encoding='utf-8-sig')) if config.exists() else {}
        fallback = Path(os.environ.get('LOCALAPPDATA', '')) / 'Comfy-Desktop/ComfyUI-Installs/ComfyUi/ComfyUI'
        root = Path(settings.get('comfy_root', fallback)).resolve()
        if not (root / 'main.py').is_file() or not (root / '.venv/Scripts/python.exe').is_file():
            raise RuntimeError('The existing ComfyUI installation is missing. Set its folder with Setup-ComfyFitterDesktop.ps1 -ComfyRoot. No models were downloaded.')
        return root

    def worker_matches(self):
        # An occupied port is reusable only when it belongs to this workspace's isolated worker.
        command = ('$workerPid=(Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction Stop | '
                   'Select-Object -First 1).OwningProcess; Get-CimInstance Win32_Process '
                   '-Filter "ProcessId=$workerPid" | Select-Object CommandLine | ConvertTo-Json -Compress')
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command], capture_output=True,
                                text=True, timeout=10, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        process = json.loads(result.stdout)
        line = process.get('CommandLine', '')
        return ('main.py' in line and '--listen 127.0.0.1' in line
                and '--port 8188' in line and str(self.root / '.local/input').replace('/', '\\').lower() in line.lower())

    def ensure(self):
        if not self.lock.acquire(blocking=False):
            return self.status()
        try:
            self.state = {'state': 'starting', 'message': 'Starting your local fitting room…'}
            if not (self.root / 'frontend/dist/index.html').is_file():
                raise RuntimeError('The application build is missing. Run Setup-ComfyFitterDesktop.ps1 first.')
            worker_root = self.worker_root()
            environment = os.environ.copy()
            # Local desktop mode cannot inherit a prior hosted configuration.
            for key in list(environment):
                if key.startswith('COMFYFITTER_'):
                    environment.pop(key)
            environment['COMFYFITTER_PROTECTION_PYTHON'] = str(worker_root / '.venv/Scripts/python.exe')
            health = self.health()
            if health is None:
                if port_open(8000):
                    raise RuntimeError('Port 8000 is occupied but ComfyFitter is not responding. No process was stopped. See the local logs.')
                self.launch('application', [sys.executable, '-m', 'uvicorn', 'backend.app.main:app',
                    '--host', '127.0.0.1', '--port', '8000', '--workers', '1', '--no-access-log'], self.root, environment)
            if port_open(8188):
                if not self.worker_matches():
                    raise RuntimeError('Port 8188 belongs to a different GPU service. It was preserved. Close that service before retrying.')
            else:
                self.launch('gpu', [str(worker_root / '.venv/Scripts/python.exe'), 'main.py', '--listen', '127.0.0.1',
                    '--port', '8188', '--disable-auto-launch', '--input-directory', str(self.root / '.local/input'),
                    '--output-directory', str(self.root / '.local/output'), '--user-directory', str(self.root / '.local/user')],
                    worker_root, environment)
            self.state = {'state': 'starting', 'message': 'Starting the GPU service. The first launch can take a few minutes…'}
            deadline = self.clock() + self.timeout
            while self.clock() < deadline:
                for role, process in self.processes.items():
                    if process.poll() is not None:
                        raise RuntimeError(f'The {role} service stopped during startup. See .local/logs/desktop-{role}.log, then retry.')
                health = self.health()
                if health and health.get('comfyui', {}).get('ready'):
                    if 'application' in self.processes:
                        (self.root / '.local/application-process.json').write_text(json.dumps({
                            'processId': health['process_id'], 'launcherProcessId': self.processes['application'].pid,
                            'port': 8000, 'url': APP_URL, 'python': sys.executable,
                        }, indent=2) + '\n')
                    self.state = {'state': 'ready', 'message': 'Your local fitting room is ready.'}
                    return self.status()
                if health and health.get('comfyui', {}).get('reachable'):
                    raise RuntimeError(health['comfyui']['error']['message'])
                self.sleep(.5)
            raise RuntimeError('The GPU service is taking longer than four minutes. Check the local logs, then retry. Any running generation is preserved.')
        except (OSError, ValueError, subprocess.SubprocessError, RuntimeError) as error:
            self.state = {'state': 'error', 'message': str(error)}
            return self.status()
        finally:
            self.lock.release()
