"""Fail closed on weight/node/runtime drift before starting private inference."""
import hashlib,json,os,sys
from pathlib import Path
import torch
manifest=json.loads(Path('/opt/environment.json').read_text())
if not torch.cuda.is_available() or torch.cuda.device_count()!=1:raise RuntimeError('Exactly one CUDA GPU must be provisioned')
if torch.__version__!=manifest['packages']['torch']:raise RuntimeError('Torch differs from evaluated runtime')
node=Path('/opt/ComfyUI/custom_nodes/ComfyUI-GGUF/nodes.py')
if hashlib.sha256(node.read_bytes()).hexdigest()!=manifest['custom_nodes'][0]['nodes_py_sha256']:raise RuntimeError('Custom node differs')
for model in manifest['models']:
    found=list(Path('/models').rglob(model['file']))
    if len(found)!=1 or found[0].is_symlink():raise RuntimeError('Expected one regular provisioned model: '+model['file'])
    checksum=hashlib.sha256()
    with found[0].open('rb') as file:
        for block in iter(lambda:file.read(8*1024*1024),b''):checksum.update(block)
    if checksum.hexdigest()!=model['sha256']:raise RuntimeError('Model checksum differs: '+model['file'])
os.execv(sys.executable,[sys.executable,'/opt/ComfyUI/main.py','--listen','0.0.0.0','--port','8188',
    '--input-directory','/srv/comfy/input','--output-directory','/srv/comfy/output','--user-directory','/srv/comfy/user',
    '--extra-model-paths-config','/opt/extra_model_paths.yaml','--disable-auto-launch','--lowvram',
    '--reserve-vram','0.5','--verbose','ERROR','--log-stdout'])
