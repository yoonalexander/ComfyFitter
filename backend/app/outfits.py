"""Independently versioned outfit refinement; single/reference evidence stays pinned."""
from .references import References, outfit_prompt
from .settings import ROOT
from .workflow import sha


def refined_outfit_prompt(category, outer_category):
    return outfit_prompt(category, outer_category) + (
        ' Keep the exact collar architecture of EACH reference independently. '
        'If the outer reference has a narrow upright stand collar, keep that narrow stand collar; '
        'do not replace it with a folded pointed shirt collar or lapels. '
        'The inner shirt collar must remain separate, inside the outer collar. '
        'Match each reference pocket placement and closure; invent no additional pockets. '
        'Treat image1 as a pose and preservation constraint: keep the original arms, elbows, wrists '
        'and hands at exactly their original positions. Preserve contact with objects already held, '
        'including any stems, bouquet or wheat; do not drop arms, hide hands or leave held objects floating. '
        'Keep the original lower-body clothing, including a visible skirt, shorts or trousers, '
        'in its original color and shape wherever it is not naturally covered by the outer garment. '
        'Do not extend the inner shirt hem to erase the skirt, shorten the skirt, expose new bare legs, '
        'or replace lower clothing with the inner shirt. Preserve existing bags and straps. '
        'Only replace the upper garments with the two supplied references; do not reconstruct the person or scene.'
    )


class OutfitReferences(References):
    def __init__(self, settings, workflow):
        super().__init__(settings, workflow)
        row = self.modes.get('two_garment')
        if row and row.get('outfit_implementation_sha256') != sha(ROOT / 'backend/app/outfits.py'):
            self.modes.pop('two_garment')

    def plan(self, category, uploads, outer_category):
        plan = super().plan(category, uploads, outer_category)
        if plan['mode'] == 'two_garment':
            plan['prompt'] = refined_outfit_prompt(category, outer_category)
            plan['outfit_implementation_sha256'] = sha(ROOT / 'backend/app/outfits.py')
        return plan
