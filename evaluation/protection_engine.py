"""Pinned CPU parser and the same declared conservative mask/guard used by the study."""
import hashlib,importlib.metadata,json
from pathlib import Path
import numpy as np
from PIL import Image
from semantic_constraints import semantic_mask
from boundary_guard import safe_mask
from protected_regions import constrain
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
class Engine:
    def __init__(self,model_directory):
        manifest=json.loads((ROOT/'evaluation/segmentation_environment.json').read_text())
        for row in manifest['files']:
            file=model_directory/row['file']
            if file.is_symlink() or not file.is_file() or sha(file)!=row['sha256']:raise ValueError('Pinned CPU parser file changed')
        for name,version in manifest['packages'].items():
            if importlib.metadata.version(name)!=version:raise ValueError('Pinned CPU parser runtime changed: '+name)
        import torch
        from transformers import SegformerImageProcessor,SegformerForSemanticSegmentation
        torch.set_num_threads(1);self.torch=torch
        self.processor=SegformerImageProcessor.from_pretrained(model_directory,local_files_only=True)
        self.model=SegformerForSemanticSegmentation.from_pretrained(model_directory,local_files_only=True,use_safetensors=True).to('cpu').eval()
    def segment(self,image):
        with self.torch.inference_mode():
            logits=self.model(**self.processor(images=image,return_tensors='pt')).logits
            resized=self.torch.nn.functional.interpolate(logits,size=image.size[::-1],mode='bilinear',align_corners=False)
            return resized.argmax(dim=1)[0].cpu().numpy().astype(np.uint8)
    def apply(self,source,generated,category):
        source=source.convert('RGB').resize(generated.size,Image.Resampling.LANCZOS);generated=generated.convert('RGB')
        src_labels=self.segment(source);gen_labels=self.segment(generated);fallback=None;boundary=None
        try:mask=semantic_mask(src_labels,gen_labels,policy='occlusion_v3',category=category)
        except ValueError as error:mask=Image.new('L',generated.size,255);fallback=str(error)
        if fallback is None:mask,fallback,boundary=safe_mask(source,generated,mask,src_labels)
        final=generated if fallback else constrain(source,generated,mask)
        protected=np.asarray(mask)==0
        metrics=dict(applied=fallback is None,fallback_reason=fallback,boundary_guard=boundary,
            raw_protected_pixels_changed=int(np.count_nonzero(np.any(np.asarray(source)!=np.asarray(generated),axis=2)&protected)),
            protected_pixels_changed=int(np.count_nonzero(np.any(np.asarray(source)!=np.asarray(final),axis=2)&protected)))
        return final,mask,metrics
