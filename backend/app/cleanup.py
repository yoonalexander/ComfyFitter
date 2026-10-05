import hashlib
import shutil
import time
import uuid

from .errors import AppError


class Cleanup:
    def __init__(self, store, settings):
        self.store, self.settings = store, settings

    def delete(self, record):
        if record['state'] in ('queued', 'processing') or record['upstream_active']:
            raise AppError(409, 'JOB_ACTIVE', 'Images cannot be deleted while GPU work may still be active.')
        if record['assets_expired']:
            return record
        job_id = record['id']
        assets = record['manifest'].get('upstream_assets', [])
        for asset in assets:
            root = (self.settings.comfy_input_dir if asset['type'] == 'input' else self.settings.comfy_output_dir).resolve()
            filename = asset['filename']
            target = (root / filename).resolve()
            if ('/' in filename or '\\' in filename or not filename.startswith(f'cf_{job_id}_')
                    or not target.is_relative_to(root) or target == root):
                raise AppError(409, 'ASSET_OWNERSHIP_UNPROVEN', 'An asset location does not belong to this job.')
            if target.exists():
                if hashlib.sha256(target.read_bytes()).hexdigest() != asset['sha256']:
                    raise AppError(409, 'ASSET_CHANGED', 'An image service asset changed; it was preserved for inspection.')
                target.unlink()
        directory = self.store.directory(job_id)
        resolved = directory.resolve()
        owned_root = (self.store.root / 'jobs').resolve()
        if not resolved.is_relative_to(owned_root) or resolved == owned_root or directory.is_symlink():
            raise AppError(409, 'ASSET_OWNERSHIP_UNPROVEN', 'The job directory is outside application storage.')
        if directory.exists():
            if any(not child.resolve().is_relative_to(resolved) for child in directory.rglob('*')):
                raise AppError(409, 'ASSET_OWNERSHIP_UNPROVEN', 'The job directory contains an external link.')
            shutil.rmtree(directory)
        record.update(assets_expired=True, expires_at=time.time(), manifest={})
        self.store.save(record)
        return record

    def sweep(self):
        for record in self.store.expired():
            try:
                self.delete(record)
            except (AppError, OSError):
                # Keep the row eligible for a later retry; never silently claim deletion.
                record['cleanup_error'] = 'Some owned assets could not be deleted; cleanup will retry.'
                self.store.save(record)
        self.remove_orphans()

    def remove_orphans(self):
        root = (self.store.root / 'jobs').resolve()
        if not root.exists():
            return
        for directory in root.iterdir():
            try:
                job_id = str(uuid.UUID(directory.name))
                if (directory.name != job_id or not directory.is_dir() or directory.is_symlink()
                        or not directory.resolve().is_relative_to(root) or self.store.contains(job_id)):
                    continue
                children = list(directory.rglob('*'))
                if any(not child.resolve().is_relative_to(directory.resolve()) for child in children):
                    continue
                newest = max(path.stat().st_mtime for path in [directory, *children])
                if time.time() - newest > self.settings.retention_seconds:
                    # Validated UUID, absent from the durable queue, aged and wholly contained.
                    shutil.rmtree(directory)
            except (OSError, ValueError):
                continue
