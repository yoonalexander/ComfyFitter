"""Separate coat-only refinement; earlier outfit evidence remains reproducible."""
import json
from .outfits import OutfitReferences
from .references import outfit_prompt
from .settings import ROOT
from .workflow import sha


def coat_outfit_prompt(category, outer_category):
    if (category, outer_category) != ('shirt', 'coat'):
        raise ValueError('This refinement evaluates shirt and coat only')
    return outfit_prompt(category, outer_category) + (
        ' Wear the inner shirt TUCKED INTO the EXISTING lower-body garment from image1. '
        'Keep that original lower garment, its waistband, skirt or trouser shape, color and hem intact. '
        'The shirt ends at the original waist; its hem must not replace a skirt or expose additional bare legs. '
        'The open outer coat may naturally cover part of the original lower garment, '
        'but the lower garment must remain visible through the coat opening wherever it was visible in image1. '
        'Copy the outer coat collar orientation from image3: a folded pointed collar remains folded down, '
        'and an upright collar remains upright only if image3 shows it. '
        'Keep the inner collar separate from the outer collar; copy only the closures and cuffs shown in each reference. '
        'Preserve the exact original arm, elbow, wrist and hand positions AND their original visibility. '
        'Hands in pockets stay in pockets; crossed arms stay crossed; held objects stay held by the same hands. '
        'Retain only accessories and objects already present in image1; invent no new props, cuff straps or pockets. '
        'Keep the original person, lower clothing and scene as fixed constraints; edit only the upper garments.'
    )


class CoatOutfitReferences(OutfitReferences):
    def __init__(self, settings, workflow):
        super().__init__(settings, workflow)
        try:
            report = json.loads(settings.feature_manifest.read_text())
            row = report['modes']['two_garment']
            if row.get('experiment') != 'two_garment_v3':
                return
            self.modes.pop('two_garment', None)
            counts = row.get('counts', {}).get('shirt+coat', {})
            if (workflow.supported and report['baseline_quality_sha256'] == workflow.quality_sha256
                    and report['implementation_sha256'] == sha(ROOT / 'backend/app/references.py')
                    and row.get('outfit_implementation_sha256') == sha(ROOT / 'backend/app/outfits.py')
                    and row.get('coat_refinement_sha256') == sha(ROOT / 'backend/app/coat_outfits.py')
                    and row.get('status') == 'passed' and row.get('reviewed') == 8
                    and row.get('preservation_noninferior') is True and row.get('all_combinations_passed') is True
                    and row.get('verified_total_inputs') == 3 and row.get('combinations') == ['shirt+coat']
                    and set(row.get('counts', {})) == {'shirt+coat'}
                    and counts.get('expected') == 8 and type(counts.get('passed')) is int and 7 <= counts['passed'] <= 8):
                self.modes['two_garment'] = row
                self.report_hash = sha(settings.feature_manifest)
        except (OSError, ValueError, TypeError, KeyError):
            pass

    def plan(self, category, uploads, outer_category):
        plan = super().plan(category, uploads, outer_category)
        if plan['mode'] == 'two_garment' and self.modes['two_garment'].get('experiment') == 'two_garment_v3':
            plan['prompt'] = coat_outfit_prompt(category, outer_category)
            plan['coat_refinement_sha256'] = sha(ROOT / 'backend/app/coat_outfits.py')
        return plan
