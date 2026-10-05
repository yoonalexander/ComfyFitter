import hashlib
import json

from .errors import AppError
from .settings import ROOT

CATEGORIES = ('shirt', 'hoodie', 'jacket', 'coat')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Workflow:
    def __init__(self, settings):
        self.config = json.loads((ROOT / 'backend/workflow.json').read_text())
        self.graph_path = ROOT / self.config['graph']
        if sha(self.graph_path) != self.config['graph_sha256']:
            raise ValueError('Configured workflow graph changed; revalidate before enabling it')
        self.graph = json.loads(self.graph_path.read_text())
        required = {'person_node':('LoadImage','image'),'garment_node':('LoadImage','image'),
                    'prompt_node':('TextEncodeQwenImage21','prompt'),'sampler_node':('KSampler','seed'),
                    'output_node':('SaveImageAdvanced','filename_prefix')}
        for role,(kind,input_name) in required.items():
            node=self.graph.get(self.config.get(role))
            if not isinstance(node,dict) or node.get('class_type')!=kind or input_name not in node.get('inputs',{}):
                raise ValueError('Configured workflow mapping differs from the validated graph: '+role)
        self.prompts = {role: (ROOT / value).read_text() for role, value in self.config['prompts'].items()}
        self.prompt_hashes = {role: sha(ROOT / value) for role, value in self.config['prompts'].items()}
        self.supported = []
        self.quality_sha256 = None
        try:
            report = json.loads(settings.quality_manifest.read_text())
            valid = (report.get('status') == 'passed' and report.get('quality_gate_passed') is True
                     and report.get('expected') == report.get('recorded') == 40
                     and report.get('scored', 0) + report.get('inference_failures', 0) == 40
                     and report.get('passed', 0) >= 32
                     and report.get('prompt_hashes') == self.prompt_hashes
                     and report.get('workflow_template_sha256') == self.config['graph_sha256']
                     and report.get('environment_sha256') == sha(ROOT / 'evaluation/environment.json')
                     and all(report.get('categories', {}).get(c, {}).get('passed', 0) >= 8
                             for c in CATEGORIES)
                     and set(report.get('validated_categories', [])) == set(CATEGORIES))
            if valid:
                self.supported = list(CATEGORIES)
                self.quality_sha256 = sha(settings.quality_manifest)
        except (OSError, ValueError, TypeError):
            pass

    def prompt(self, category):
        if category not in CATEGORIES:
            raise AppError(422, 'INVALID_CATEGORY', 'Choose shirt, hoodie, jacket or coat.')
        if category not in self.supported:
            raise AppError(503, 'QUALITY_NOT_VALIDATED', 'No validated workflow is available for this category.')
        role = 'outerwear' if category in ('coat', 'jacket') else 'upper_body'
        if category=='jacket' and 'jacket' in self.prompts:role='jacket'
        return self.prompts[role].format(garment_type=category)
