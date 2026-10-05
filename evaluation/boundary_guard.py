"""Conservative raw fallback when source protection would cut through a new collar."""
import numpy as np
from PIL import Image,ImageFilter
def safe_mask(source,generated,mask,source_labels):
    if source.size!=generated.size or source.size!=mask.size or source_labels.shape!=np.asarray(mask).shape:raise ValueError('Boundary geometry mismatch')
    values=np.asarray(mask)
    near=np.asarray(Image.fromarray((values>0).astype(np.uint8)*255).filter(ImageFilter.MaxFilter(7)))>0
    boundary=(values==0)&near&np.isin(source_labels,(2,11,14,15))
    delta=np.mean(np.abs(np.asarray(source,dtype=np.float32)-np.asarray(generated,dtype=np.float32)),axis=2)[boundary]
    metrics=dict(protected_boundary_pixels=len(delta),discontinuous_fraction=float(np.mean(delta>30)) if len(delta) else 0.,mean_rgb_delta=float(np.mean(delta)) if len(delta) else None)
    if len(delta) and metrics['discontinuous_fraction']>.15:
        return Image.new('L',generated.size,255),'Protected boundary differs strongly from the generated collar or sleeve; retain raw preview',metrics
    return mask,None,metrics
