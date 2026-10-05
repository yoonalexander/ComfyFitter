"""Fetch the licensed benchmark inputs and enforce the recorded hashes."""
import hashlib
import json
import urllib.request
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'assets_manifest.json').read_text())
    for asset in manifest['assets']:
        path = root / asset['path']
        if path.is_file():
            raw = path.read_bytes()
        else:
            request = urllib.request.Request(asset['download_url'], headers={'User-Agent': 'ComfyFitterEvaluation/1.0'})
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
        if hashlib.sha256(raw).hexdigest() != asset['sha256']:
            raise RuntimeError('Source changed or local input was modified: ' + asset['path'])
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        print('Verified: ' + asset['path'])


if __name__ == '__main__':
    main()
