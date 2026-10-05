"""Ordered reference plans. Complex modes remain closed until their own matched gate passes."""
import copy,json
from .workflow import sha
from .errors import AppError
from .settings import ROOT
VIEWS=('back','side','detail')
ROLES=('person','garment',*VIEWS,'outer')

def multi_prompt(prompt,extras):
    views=['front',*extras]
    return prompt+'\n'+ ' '.join(f'<image{index}> is the {role} view of the SAME garment, not an additional garment.' for index,role in enumerate(views,2))+' Use the front view to determine the visible silhouette; use other views only to clarify corresponding construction, pattern and details. Do not paste a back design onto the front.'

def outfit_prompt(category,outer_category):
    return (f'Use <image1> as the edit target. Dress the foreground person in the exact {category} from <image2>, '
        f'with the exact {outer_category} from <image3> worn OPEN over it. The inner garment is a separate garment, not a texture for the outer layer. '
        'Keep both reference identities distinct: copy each collar, sleeves, seams, closures, material, color and visible detail from its own image. '
        'Show the inner garment naturally through the outer opening. Match the outer reference length. Preserve the original face, full hairstyle, pose, hands, body proportions, accessories, lighting, background and unrelated lower clothing. '
        'Respect layering and natural hair/hand occlusion; add no absent garment details or accessories.')

class References:
    def __init__(self,settings,workflow):
        self.workflow=workflow;self.modes={};self.report_hash=None
        try:
            report=json.loads(settings.feature_manifest.read_text())
            if (not workflow.supported or report['baseline_quality_sha256']!=workflow.quality_sha256
                or report['implementation_sha256']!=sha(ROOT/'backend/app/references.py')):return
            for name,row in report['modes'].items():
                if row.get('status')!='passed' or row.get('preservation_noninferior') is not True:continue
                if name=='multi_reference' and row.get('reviewed',0)>=8 and row.get('fidelity_improved') is True and row.get('verified_total_inputs')==5 and set(row.get('categories',[]))<=set(workflow.supported):self.modes[name]=row
                if name=='two_garment' and row.get('reviewed',0)>=16 and row.get('all_combinations_passed') is True and row.get('verified_total_inputs')==3 and set(row.get('combinations',[]))<= {'shirt+jacket','shirt+coat','hoodie+jacket','hoodie+coat'}:self.modes[name]=row
            self.report_hash=sha(settings.feature_manifest)
        except (OSError,ValueError,TypeError,KeyError):pass

    def plan(self,category,uploads,outer_category):
        # Base-category admission remains mandatory for every mode.
        prompt=self.workflow.prompt(category)
        roles=[role for role in ROLES if role in uploads]
        extras=[role for role in VIEWS if role in uploads]
        if 'outer' in uploads:
            if extras or not outer_category:raise AppError(422,'INVALID_REFERENCE_ROLES','Two garments require one front reference for each garment and an outer category.')
            mode='two_garment';row=self.modes.get(mode,{})
            if category+'+'+outer_category not in row.get('combinations',[]):raise AppError(503,'MODE_NOT_VALIDATED','This garment combination has not passed its quality checks.')
            prompt=outfit_prompt(category,outer_category)
        elif extras:
            if outer_category:raise AppError(422,'INVALID_REFERENCE_ROLES','An outer category requires an outer garment reference.')
            mode='multi_reference';row=self.modes.get(mode,{})
            if category not in row.get('categories',[]):raise AppError(503,'MODE_NOT_VALIDATED','Multiple references have not passed their quality checks for this category.')
            permitted=row.get('reference_roles',{}).get(category,list(VIEWS))
            if any(role not in permitted for role in extras):raise AppError(503,'MODE_NOT_VALIDATED','This reference view has not passed its quality checks for this category.')
            prompt=multi_prompt(prompt,extras)
        else:
            if outer_category:raise AppError(422,'INVALID_REFERENCE_ROLES','An outer category requires an outer garment reference.')
            mode='single_reference'
        return dict(mode=mode,image_order=roles,outer_category=outer_category,prompt=prompt,
                    feature_manifest_sha256=self.report_hash if mode!='single_reference' else None)

    @staticmethod
    def graph(template,config,uploaded):
        graph=copy.deepcopy(template)
        encoded=graph[config['prompt_node']]['inputs']
        for key in list(encoded):
            if key.startswith('images.image_'):del encoded[key]
        for index,(role,path) in enumerate(uploaded.items(),1):
            node=config[role+'_node'] if role in ('person','garment') else 'cf_reference_'+role
            if role in ('person','garment'):graph[node]['inputs']['image']=path
            else:graph[node]={'class_type':'LoadImage','inputs':{'image':path}}
            encoded['images.image_'+str(index)]=[node,0]
        return graph
