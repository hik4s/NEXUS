import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User

@pytest.fixture
def auth(monkeypatch):
    key = ec.generate_private_key(ec.SECP256R1())
    public = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(key.public_key()))
    public.update(kid='test-key', alg='ES256')
    monkeypatch.setitem(settings.__dict__, 'AUTH_PROVIDER', 'supabase')
    monkeypatch.setitem(settings.__dict__, 'SUPABASE_URL', 'https://nexus-test.supabase.co')
    monkeypatch.setattr(jwt.PyJWKClient, 'get_signing_key_from_jwt', lambda *_: jwt.PyJWK(public))
    def token(subject=None, **changes):
        now = datetime.now(timezone.utc)
        claims = dict(sub=str(subject or uuid4()), iss='https://nexus-test.supabase.co/auth/v1',
                      aud='authenticated', role='authenticated', session_id=str(uuid4()),
                      email=f'{uuid4().hex}@example.com', is_anonymous=False, iat=now,
                      exp=now+timedelta(minutes=5), user_metadata={'full_name':'Visitante Demo','company_id':str(uuid4()),'role':'admin'})
        claims.update(changes)
        return jwt.encode(claims, key, algorithm='ES256', headers={'kid':'test-key'})
    return token

def headers(token):
    return {'Authorization':f'Bearer {token}'}

def test_first_login_private_and_idempotent(auth):
    token = auth()
    with TestClient(app) as client:
        first = client.post('/api/v1/auth/bootstrap',headers=headers(token))
        assert first.status_code == 200, first.text
        user = first.json()
        assert user['role'] == 'admin'
        assert client.post('/api/v1/auth/bootstrap',headers=headers(token)).json()['id'] == user['id']
        assert client.get('/api/v1/auth/me',headers=headers(token)).json()['id'] == user['id']
        other_token = auth()
        other = client.post('/api/v1/auth/bootstrap',headers=headers(other_token))
        assert other.status_code == 200
        assert other.json()['company_id'] != user['company_id']
        assert client.get(f"/api/v1/companies/{user['company_id']}",headers=headers(other_token)).status_code == 403

@pytest.mark.parametrize('changes',[
    {'iss':'https://other.supabase.co/auth/v1'}, {'aud':'anon'},
    {'exp':datetime.now(timezone.utc)-timedelta(minutes=1)}, {'sub':'not-a-uuid'},
    {'role':'service_role'}, {'is_anonymous':True},
])
def test_invalid_claims(auth,changes):
    with TestClient(app) as client:
        assert client.post('/api/v1/auth/bootstrap',headers=headers(auth(**changes))).status_code == 401

def test_forged_signature(auth):
    claims = jwt.decode(auth(),options={'verify_signature':False})
    forged = jwt.encode(claims,ec.generate_private_key(ec.SECP256R1()),algorithm='ES256',headers={'kid':'test-key'})
    with TestClient(app) as client:
        assert client.post('/api/v1/auth/bootstrap',headers=headers(forged)).status_code == 401

def test_external_mode_disables_legacy(auth):
    with TestClient(app) as client:
        assert client.post('/api/v1/auth/login',json={'email':'demo@example.com','password':'anything'}).status_code == 403
        assert client.post('/api/v1/auth/refresh',json={'refresh_token':'anything'}).status_code == 403

def test_concurrent_bootstrap(auth):
    token = auth()
    with TestClient(app) as client:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda _:client.post('/api/v1/auth/bootstrap',headers=headers(token)),range(2)))
        assert [r.status_code for r in responses] == [200,200], [r.text for r in responses]
        assert responses[0].json()['id'] == responses[1].json()['id']

def test_inactive_account(auth):
    token = auth()
    with TestClient(app) as client:
        response=client.post('/api/v1/auth/bootstrap',headers=headers(token))
        assert response.status_code == 200
        with SessionLocal() as db:
            user=db.scalar(select(User).where(User.email==response.json()['email']))
            user.is_active=False
            db.commit()
        assert client.post('/api/v1/auth/bootstrap',headers=headers(token)).status_code == 403
        assert client.get('/api/v1/auth/me',headers=headers(token)).status_code == 401


def test_existing_email_is_not_automatically_linked(auth,monkeypatch):
    email=f'{uuid4().hex}@example.com'
    with TestClient(app) as client:
        monkeypatch.setitem(settings.__dict__,'AUTH_PROVIDER','legacy')
        legacy=client.post('/api/v1/auth/register',json={'company_name':uuid4().hex,'company_slug':uuid4().hex,'full_name':'Legacy','email':email,'password':'LegacyStrong123!'})
        assert legacy.status_code==201
        monkeypatch.setitem(settings.__dict__,'AUTH_PROVIDER','supabase')
        response=client.post('/api/v1/auth/bootstrap',headers=headers(auth(email=email)))
        assert response.status_code==409
        with SessionLocal() as db:
            assert db.scalar(select(User).where(User.email==email)).supabase_subject is None
