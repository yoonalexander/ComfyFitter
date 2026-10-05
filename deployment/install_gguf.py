"""Install the evaluated registry release, rejecting changed archive contents."""
import hashlib,io,urllib.request,zipfile
from pathlib import Path
url='https://cdn.comfy.org/city96/ComfyUI-GGUF/1.1.10/node.zip'
archive=urllib.request.urlopen(url,timeout=60).read(8*1024*1024)
if hashlib.sha256(archive).hexdigest()!='20bf8136b42a970242e0ee7069f0ba70350184da1305c212882fd89534dd328b':raise RuntimeError('Registry archive checksum differs')
root=Path('/opt/ComfyUI/custom_nodes/ComfyUI-GGUF');root.mkdir(parents=True)
with zipfile.ZipFile(io.BytesIO(archive)) as package:
    for item in package.infolist():
        target=root/item.filename
        if not target.resolve().is_relative_to(root.resolve()):raise RuntimeError('Archive path escapes node directory')
    package.extractall(root)
if hashlib.sha256((root/'nodes.py').read_bytes()).hexdigest()!='16be3b08b13de6279fc432addc628320019fcb24963cbc6b52b248de8f06316e':raise RuntimeError('Node implementation differs')
