"""Focused bag-preservation refinement with independently bound eight-case evidence."""
import json
from .coat_outfits import CoatOutfitReferences, coat_outfit_prompt
from .settings import ROOT
from .workflow import sha


def bag_coat_prompt(category, outer_category):
    return coat_outfit_prompt(category, outer_category) + (
        ' Preserve existing backpacks, bags and their shoulder straps exactly OVER the new coat.'
        ' Match the inner shirt front closures and collar opening to image2; '
        'do not copy image1\'s original neckline onto the supplied inner shirt.'
    )


class BagCoatReferences(CoatOutfitReferences):
    def __init__(self, settings, workflow):
        super().__init__(settings, workflow)
        try:
            report = json.loads(settings.feature_manifest.read_text())
            row = report['modes']['two_garment']
            if row.get('experiment') != 'two_garment_v4':
                return
            self.modes.pop('two_garment', None)
            counts = row.get('counts', {}).get('shirt+coat', {})
            if (workflow.supported and report['baseline_quality_sha256'] == workflow.quality_sha256
                    and report['implementation_sha256'] == sha(ROOT / 'backend/app/references.py')
                    and row.get('outfit_implementation_sha256') == sha(ROOT / 'backend/app/outfits.py')
                    and row.get('coat_refinement_sha256') == sha(ROOT / 'backend/app/coat_outfits.py')
                    and row.get('bag_refinement_sha256') == sha(ROOT / 'backend/app/bag_coat_outfits.py')
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
        if plan['mode'] == 'two_garment' and self.modes['two_garment'].get('experiment') == 'two_garment_v4':
            plan['prompt'] = bag_coat_prompt(category, outer_category)
            plan['coat_refinement_sha256'] = sha(ROOT / 'backend/app/coat_outfits.py')
            plan['bag_refinement_sha256'] = sha(ROOT / 'backend/app/bag_coat_outfits.py')
        return plan
