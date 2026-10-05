import os
import math
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_dir: Path = ROOT / '.local/app'
    comfy_url: str = 'http://127.0.0.1:8188'
    max_image_bytes: int = 10 * 1024 * 1024
    max_image_pixels: int = 16_000_000
    quality_manifest: Path = ROOT / 'evaluation/summary_category_reference_v4.json'
    feature_manifest: Path = ROOT / 'evaluation/feature_quality.json'
    protection_manifest: Path = ROOT / 'evaluation/summary_semantic_guarded_v5.json'
    protection_python: str = ''
    protection_model_dir: Path = ROOT / '.local/models/segformer_b2_clothes'
    queue_capacity: int = 5
    poll_seconds: float = 1.0
    deadline_seconds: float = 1800.0
    comfy_input_dir: Path = ROOT / '.local/input'
    comfy_output_dir: Path = ROOT / '.local/output'
    retention_seconds: float = 86400.0
    cleanup_interval_seconds: float = 60.0
    saved_look_capacity: int = 20
    saved_look_bytes: int = 256 * 1024 * 1024
    deployment_mode: str = 'local'
    public_origin: str = ''
    oidc_issuer: str = ''
    oidc_audience: str = ''
    oidc_jwks_url: str = ''
    daily_user_generations: int = 10
    daily_total_generations: int = 20
    requests_per_minute: int = 120
    allowed_origins: tuple[str, ...] = ('http://127.0.0.1:5173', 'http://localhost:5173')

    def __post_init__(self):
        if self.deployment_mode not in ('local','hosted'): raise ValueError('Unknown deployment mode')
        if self.deployment_mode == 'hosted':
            for name in ('public_origin','oidc_issuer','oidc_jwks_url'):
                value = urlparse(getattr(self,name))
                if value.scheme!='https' or not value.hostname or value.username or value.password or value.query or value.fragment:
                    raise ValueError('Hosted identity and public URLs require HTTPS without credentials/query/fragment')
            if urlparse(self.public_origin).path or not self.oidc_audience:
                raise ValueError('Hosted mode requires a public origin and OIDC audience')
        parsed = urlparse(self.comfy_url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('ComfyUI URL must be an HTTP(S) service URL without embedded credentials/query/fragment')
        for field in ('max_image_bytes', 'max_image_pixels', 'queue_capacity', 'poll_seconds',
                      'deadline_seconds', 'retention_seconds', 'cleanup_interval_seconds', 'saved_look_capacity', 'saved_look_bytes', 'daily_user_generations', 'daily_total_generations', 'requests_per_minute'):
            value = getattr(self, field)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(field + ' must be a finite positive number')
        for origin in self.allowed_origins:
            value = urlparse(origin)
            if (value.scheme not in ('http', 'https') or value.hostname not in ('localhost', '127.0.0.1', '::1')
                    or value.path or value.query or value.fragment or value.username or value.password):
                raise ValueError('Additional local origins must be loopback HTTP(S) origins')

    @classmethod
    def from_env(cls):
        fields = {'data_dir': Path, 'comfy_url': str, 'quality_manifest': Path, 'feature_manifest':Path,
                  'protection_manifest':Path,'protection_python':str,'protection_model_dir':Path,
                  'comfy_input_dir': Path, 'comfy_output_dir': Path,
                  'max_image_bytes': int, 'max_image_pixels': int, 'queue_capacity': int,
                  'poll_seconds': float, 'deadline_seconds': float,
                  'retention_seconds': float, 'cleanup_interval_seconds': float,
                  'saved_look_capacity': int, 'saved_look_bytes': int,
                  'deployment_mode': str, 'public_origin': str, 'oidc_issuer': str,
                  'oidc_audience': str, 'oidc_jwks_url': str,
                  'daily_user_generations': int, 'daily_total_generations': int,
                  'requests_per_minute': int,
                  'allowed_origins': lambda value: tuple(v.strip() for v in value.split(',') if v.strip())}
        values = {field: convert(os.environ['COMFYFITTER_' + field.upper()])
                  for field, convert in fields.items() if 'COMFYFITTER_' + field.upper() in os.environ}
        return cls(**values)
