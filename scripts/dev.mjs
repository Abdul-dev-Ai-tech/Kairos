import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawn } from 'node:child_process';
const candidates = [process.env.PYTHON_BIN, '.venv/bin/python', '.venv/Scripts/python.exe', '../.venv/bin/python'].filter(Boolean);
const python = candidates.find(path => existsSync(path)) || 'python3';
const child = spawn(python.includes('/') || python.includes('\\') ? resolve(python) : python,
  ['manage.py', 'runserver', '0.0.0.0:4173', '--noreload'], {stdio: 'inherit', env: process.env});
child.on('error', error => { console.error(error.message); process.exit(1); });
child.on('exit', code => process.exit(code || 0));
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
