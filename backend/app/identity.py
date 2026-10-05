"""Verify gateway ID tokens; never trust an unverified user/email header."""
import asyncio,hashlib,time,uuid,logging
import httpx,jwt
from starlette.responses import JSONResponse
from .errors import AppError

class Identity:
    def __init__(self,settings,transport=None):
        self.settings=settings;self.keys={};self.fetched=0;self.lock=asyncio.Lock()
        self.client=httpx.AsyncClient(timeout=5,transport=transport) if settings.deployment_mode=='hosted' else None
    async def close(self):
        if self.client:await self.client.aclose()
    async def user(self,authorization):
        if self.settings.deployment_mode=='local':return 'local'
        try:
            if not authorization.startswith('Bearer ') or len(authorization)>16384:raise ValueError()
            token=authorization[7:];header=jwt.get_unverified_header(token)
            kid=header.get('kid')
            if header.get('alg')!='RS256' or not isinstance(kid,str) or len(kid)>128:raise ValueError()
            if not self.keys or time.monotonic()-self.fetched>600 or kid not in self.keys and time.monotonic()-self.fetched>60:
                async with self.lock:
                    if not self.keys or time.monotonic()-self.fetched>60:
                        response=await self.client.get(self.settings.oidc_jwks_url);response.raise_for_status()
                        if len(response.content)>262144:raise ValueError()
                        raw=response.json()['keys'];keys={}
                        if not isinstance(raw,list) or len(raw)>100:raise ValueError()
                        for item in raw:
                            if (item.get('kty')=='RSA' and item.get('use','sig')=='sig' and item.get('alg','RS256')=='RS256'
                                    and isinstance(item.get('kid'),str)):
                                key=jwt.PyJWK.from_dict(item,algorithm='RS256').key
                                if key.key_size<2048 or item['kid'] in keys:raise ValueError()
                                keys[item['kid']]=key
                        self.keys=keys;self.fetched=time.monotonic()
            claims=jwt.decode(token,self.keys[kid],algorithms=['RS256'],issuer=self.settings.oidc_issuer,
                audience=self.settings.oidc_audience,options={'require':['exp','iat','iss','aud','sub']})
            if not isinstance(claims['sub'],str) or not claims['sub'] or len(claims['sub'])>512:raise ValueError()
            return hashlib.sha256((claims['iss']+'\0'+claims['sub']).encode()).hexdigest()
        except httpx.HTTPError as error:
            raise AppError(503,'IDENTITY_UNAVAILABLE','Sign-in could not be verified. Try again shortly.') from error
        except (jwt.PyJWTError,ValueError,KeyError,TypeError,AttributeError) as error:
            raise AppError(401,'AUTH_REQUIRED','Sign in through the application gateway to continue.') from error

class IdentityAccess:
    def __init__(self,app,identity):self.app=app;self.identity=identity
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        started=time.monotonic();request_id=str(uuid.uuid4());status=500
        headers={k.decode('latin1').lower():v.decode('latin1') for k,v in scope['headers']}
        try:
            if scope['path'].startswith('/api/') and scope['path']!='/api/health':
                user=await self.identity.user(headers.get('authorization',''))
                if self.identity.settings.deployment_mode=='hosted':self.identity.store.consume_request(user)
                scope.setdefault('state',{})['user_id']=user
            async def traced(message):
                nonlocal status
                if message['type']=='http.response.start':
                    status=message['status'];message['headers'].append((b'x-request-id',request_id.encode()))
                await send(message)
            await self.app(scope,receive,traced)
        except AppError as error:
            status=error.status
            await JSONResponse(status_code=status,content={'error':{'code':error.code,'message':error.message}},headers={'X-Request-ID':request_id})(scope,receive,send)
        finally:
            if scope['path'].startswith('/api/'):
                logging.getLogger('comfyfitter.requests').info('request id=%s status=%s duration_ms=%.1f',request_id,status,(time.monotonic()-started)*1000)

def user_id(request):return getattr(request.state,'user_id','local')
def scoped_key(request,key):
    if not key:return None
    # Preserve local request keys created before hosted authentication existed.
    return key if user_id(request)=='local' else hashlib.sha256((user_id(request)+'\0'+key).encode()).hexdigest()
def owned(record,request,code='JOB_NOT_FOUND'):
    if record.get('owner_id','local')!=user_id(request):raise AppError(404,code,'This item does not exist.')
    return record
