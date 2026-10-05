import hashlib
import json
import sqlite3
import time
import uuid

from .errors import AppError


class JobStore:
    def __init__(self, settings):
        self.capacity = settings.queue_capacity
        self.retention_seconds = settings.retention_seconds
        self.settings = settings
        self.root = settings.data_dir.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = self.root / 'jobs.sqlite3'
        with self.connect() as database:
            database.execute('''CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE, request_hash TEXT NOT NULL,
                state TEXT NOT NULL, record TEXT NOT NULL)''')
            database.execute('CREATE TABLE IF NOT EXISTS request_budgets (owner TEXT NOT NULL, window INTEGER NOT NULL, count INTEGER NOT NULL, PRIMARY KEY(owner,window))')

    def consume_request(self,owner):
        window=int(time.time()//60)
        with self.connect() as database:
            database.execute('BEGIN IMMEDIATE')
            database.execute('DELETE FROM request_budgets WHERE window<?',(window-1,))
            row=database.execute('SELECT count FROM request_budgets WHERE owner=? AND window=?',(owner,window)).fetchone()
            if row and row['count']>=self.settings.requests_per_minute:
                raise AppError(429,'REQUEST_RATE_LIMIT','Too many requests. Try again in one minute.')
            database.execute('INSERT INTO request_budgets VALUES (?,?,1) ON CONFLICT(owner,window) DO UPDATE SET count=count+1',(owner,window))

    def connect(self):
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def get(self, job_id):
        with self.connect() as database:
            row = database.execute('SELECT record FROM jobs WHERE id=?', (job_id,)).fetchone()
        if not row:
            raise AppError(404, 'JOB_NOT_FOUND', 'This job does not exist.')
        return json.loads(row['record'])

    def contains(self, job_id):
        with self.connect() as database:
            return database.execute('SELECT 1 FROM jobs WHERE id=?', (job_id,)).fetchone() is not None

    def by_request_key(self, key):
        with self.connect() as database:
            row = database.execute('SELECT record FROM jobs WHERE idempotency_key=?', (key,)).fetchone()
        if not row:
            raise AppError(404, 'SUBMISSION_NOT_FOUND', 'No accepted job has this request key.')
        return json.loads(row['record'])

    def pending(self):
        with self.connect() as database:
            rows = database.execute("SELECT record FROM jobs WHERE state IN ('queued','processing') OR json_extract(record,'$.upstream_active')=1 ORDER BY rowid").fetchall()
        return [json.loads(row['record']) for row in rows]

    def expired(self):
        with self.connect() as database:
            rows = database.execute("""SELECT record FROM jobs WHERE state IN ('complete','failed')
                AND json_extract(record,'$.upstream_active')=0
                AND json_extract(record,'$.assets_expired')=0
                AND json_extract(record,'$.expires_at')<=?""", (time.time(),)).fetchall()
        return [json.loads(row['record']) for row in rows]

    def save(self, record):
        with self.connect() as database:
            database.execute('UPDATE jobs SET state=?,record=? WHERE id=?',
                             (record['state'], json.dumps(record), record['id']))

    def directory(self, job_id):
        return self.root / 'jobs' / str(uuid.UUID(job_id))

    def validate_inputs(self, record):
        directory = self.directory(record['id'])
        if directory.is_symlink():
            raise AppError(409, 'INPUT_UNAVAILABLE', 'The stored job input location changed.')
        for role in record['manifest']['images']:
            file = directory / f'{role}.png'
            if (not file.is_file() or not file.resolve().is_relative_to(directory.resolve())
                    or hashlib.sha256(file.read_bytes()).hexdigest() != record['manifest']['images'][role]['sha256']):
                raise AppError(409, 'INPUT_UNAVAILABLE', 'A stored job image is missing or changed. Upload the images again.')

    def validate_result(self,record):
        directory=self.directory(record['id']);file=directory/'result.png'
        try:
            valid=(not directory.is_symlink() and file.is_file() and not file.is_symlink()
                   and file.resolve().is_relative_to(directory.resolve())
                   and hashlib.sha256(file.read_bytes()).hexdigest()==record['manifest'].get('result_sha256'))
        except OSError:valid=False
        if not valid:raise AppError(409,'RESULT_UNAVAILABLE','The stored preview is missing or changed. Generate another preview.')

    def reconcile_queued_files(self):
        for record in self.pending():
            if record['state'] != 'queued' or record['upstream_active']:
                continue
            try:
                self.validate_inputs(record)
            except (AppError, OSError):
                record.update(state='failed', stage='failed', expires_at=time.time() + self.retention_seconds,
                              error={'code': 'INPUT_UNAVAILABLE', 'message': 'A stored job image is missing or changed. Upload the images again.'})
                self.save(record)

    def enqueue(self, category, seed, images, key, manifest,owner_id='local'):
        fingerprint={'category': category, 'seed': seed,
            'mode':manifest.get('mode','single_reference'),'outer_category':manifest.get('outer_category'),
            'image_order':manifest.get('image_order',['person','garment']),
            'images': [image['original_sha256'] for image in images]}
        if manifest.get('protect_regions'):fingerprint['protect_regions']=True
        if manifest.get('source_has_bag'):fingerprint['source_has_bag']=True
        request_hash = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()
        with self.connect() as database:
            database.execute('BEGIN IMMEDIATE')
            if key:
                existing = database.execute('SELECT * FROM jobs WHERE idempotency_key=?', (key,)).fetchone()
                if existing:
                    if existing['request_hash'] != request_hash:
                        raise AppError(409, 'IDEMPOTENCY_CONFLICT', 'This request key already belongs to different inputs.')
                    return json.loads(existing['record'])
            count = database.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('queued','processing') OR json_extract(record,'$.upstream_active')=1").fetchone()[0]
            if count >= self.capacity:
                raise AppError(429, 'QUEUE_FULL', 'The local generation queue is full. Try again after a job finishes.')
            if self.settings.deployment_mode=='hosted':
                since=int(time.time()//86400)*86400
                total,user_count=database.execute("SELECT COUNT(*),COALESCE(SUM(json_extract(record,'$.owner_id')=?),0) FROM jobs WHERE json_extract(record,'$.created_at')>=?",(owner_id,since)).fetchone()
                if total>=self.settings.daily_total_generations or user_count>=self.settings.daily_user_generations:
                    raise AppError(429,'DAILY_GENERATION_LIMIT','The daily generation limit is reached. Try again after 00:00 UTC.')
            job_id = str(uuid.uuid4())
            directory = self.root / 'jobs' / job_id
            directory.mkdir(parents=True)
            for role, image in zip(manifest.get('image_order',('person', 'garment')), images):
                (directory / f'{role}.png').write_bytes(image['bytes'])
            record = {'id': job_id, 'state': 'queued', 'stage': 'waiting', 'category': category,
                      'owner_id':owner_id,
                      'seed': seed, 'created_at': time.time(), 'expires_at': None,
                      'assets_expired': False, 'submission': 'not_started', 'error': None,
                      'upstream_active': False,
                      'manifest': manifest}
            (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2))
            database.execute('INSERT INTO jobs VALUES (?,?,?,?,?)',
                             (job_id, key, request_hash, 'queued', json.dumps(record)))
        return record


def public_job(record):
    return {key: record[key] for key in ('id', 'state', 'stage', 'category', 'seed',
        'created_at', 'expires_at', 'assets_expired', 'error', 'manifest', 'upstream_active')}
