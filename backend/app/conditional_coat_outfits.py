"""Apply bag preservation only when the person photo actually includes a bag."""
import json
from .bag_coat_outfits import BagCoatReferences, bag_coat_prompt
from .coat_outfits import coat_outfit_prompt
from .errors import AppError
from .settings import ROOT
from .workflow import sha


def conditional_coat_prompt(category, outer_category, source_has_bag=False):
    if type(source_has_bag) is not bool:
        raise ValueError('Source bag choice must be boolean')
    if source_has_bag:
        return bag_coat_prompt(category, outer_category)
    return coat_outfit_prompt(category, outer_category) + (
        ' Match the inner shirt front closures and collar opening to image2; '
        'do not copy image1\'s original neckline onto the supplied inner shirt.'
    )


class ConditionalCoatReferences(BagCoatReferences):
    def __init__(self, settings, workflow):
        super().__init__(settings, workflow)
        try:
            report=json.loads(settings.feature_manifest.read_text());row=report['modes']['two_garment']
            if row.get('experiment')!='two_garment_v5':
                return
            self.modes.pop('two_garment',None)
            counts=row.get('counts',{}).get('shirt+coat',{})
            bindings={'implementation_sha256':'references.py','outfit_implementation_sha256':'outfits.py',
                      'coat_refinement_sha256':'coat_outfits.py','bag_refinement_sha256':'bag_coat_outfits.py',
                      'conditional_refinement_sha256':'conditional_coat_outfits.py'}
            if (workflow.supported and report['baseline_quality_sha256']==workflow.quality_sha256
                    and all((report if key=='implementation_sha256' else row).get(key)==sha(ROOT/'backend/app'/filename) for key,filename in bindings.items())
                    and row.get('status')=='passed' and row.get('reviewed')==8
                    and row.get('preservation_noninferior') is True and row.get('all_combinations_passed') is True
                    and row.get('verified_total_inputs')==3 and row.get('combinations')==['shirt+coat']
                    and row.get('validated_source_bag_options')==[False,True]
                    and all(type(option) is bool for option in row['validated_source_bag_options'])
                    and set(row.get('counts',{}))=={'shirt+coat'} and counts.get('expected')==8
                    and type(counts.get('passed')) is int and 7<=counts['passed']<=8):
                self.modes['two_garment']=row;self.report_hash=sha(settings.feature_manifest)
        except (OSError,ValueError,TypeError,KeyError):
            pass

    def plan(self,category,uploads,outer_category,source_has_bag=False):
        plan=super().plan(category,uploads,outer_category)
        qualified=plan['mode']=='two_garment' and self.modes['two_garment'].get('experiment')=='two_garment_v5'
        if source_has_bag and not qualified:
            raise AppError(422,'BAG_OPTION_UNSUPPORTED','The bag choice is available only for the qualified shirt-and-coat preview.')
        if qualified:
            plan.update(prompt=conditional_coat_prompt(category,outer_category,source_has_bag),source_has_bag=source_has_bag,
                        coat_refinement_sha256=sha(ROOT/'backend/app/coat_outfits.py'),
                        bag_refinement_sha256=sha(ROOT/'backend/app/bag_coat_outfits.py'),
                        conditional_refinement_sha256=sha(ROOT/'backend/app/conditional_coat_outfits.py'))
        return plan
