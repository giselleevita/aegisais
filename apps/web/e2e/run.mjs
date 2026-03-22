#!/usr/bin/env node
/**
 * Skip E2E when E2E=0 (e.g. CI jobs without browsers or full stack).
 */
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')

if (process.env.E2E === '0') {
  console.log('[e2e] Skipped: E2E=0')
  process.exit(0)
}

const args = ['playwright', 'test', ...process.argv.slice(2)]
const child = spawn('npx', args, {
  cwd: root,
  stdio: 'inherit',
  shell: true,
  env: process.env,
})

child.on('exit', (code, signal) => {
  if (signal) process.exit(1)
  process.exit(code ?? 1)
})
