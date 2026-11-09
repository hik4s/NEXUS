import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const root = fileURLToPath(new URL('../../', import.meta.url));
const database = process.env.NEXUS_TEST_DATABASE_URL || '';
if (!database.startsWith('postgresql+psycopg://') || !new URL(database.replace('+psycopg', '')).pathname.startsWith('/nexus_e2e')) throw new Error('Set NEXUS_TEST_DATABASE_URL to a disposable PostgreSQL database named nexus_e2e…');
if ((process.env.NEXUS_DEMO_PASSWORD || '').length < 12) throw new Error('Set a dedicated NEXUS_DEMO_PASSWORD (12+ characters)');
const env = { ...process.env, DATABASE_URL: database, APP_ENV: 'test', APP_PROFILE: 'portfolio',
  PUBLIC_REGISTRATION_ENABLED: 'false', REDIS_ENABLED: 'false',
  SECRET_KEY: 'dedicated-e2e-only-secret-not-for-production-2026',
  CORS_ORIGINS: 'http://127.0.0.1:5180', TRUSTED_HOSTS: '127.0.0.1,localhost,testserver' };
const python = process.env.NEXUS_PYTHON || 'python';
function launch(args) { return spawn(python, args, { cwd: join(root, 'backend'), env, stdio: 'inherit', windowsHide: true }); }
async function run(args) { await new Promise((resolve, reject) => { const child = launch(args); child.on('error', reject); child.on('exit', code => code === 0 ? resolve() : reject(new Error('Demo setup failed'))); }); }
await run(['-m', 'alembic', 'upgrade', 'head']);
await run([join(root, 'scripts', 'seed_demo.py'), '--confirm-demo']);
const api = launch(['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8811']);
for (const signal of ['SIGTERM', 'SIGINT']) process.on(signal, () => { api.kill(); process.exit(0); });
api.on('exit', code => process.exit(code || 0));
