#!/usr/bin/env node
// Optional OpenWA completion notifier. Requires Node >= 22; no third-party dependencies.
// Sends ONLY when a completed project has explicit passing verification evidence.
// Env: DEXTER_OPENWA_URL (default http://127.0.0.1:8080), DEXTER_OPENWA_TO, DEXTER_OPENWA_API_KEY (optional).
// Usage: node tools/notifications/openwa-completion.mjs path/to/completion.json
// Example JSON: {"project":"1UP Anime","status":"completed","testsPassed":true,"evidenceUrl":"https://github.com/.../pull/123"}
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const [file] = process.argv.slice(2);
if (!file) { console.error('Usage: node openwa-completion.mjs completion.json'); process.exit(2); }
const report = JSON.parse(await readFile(resolve(file), 'utf8'));
if (report.status !== 'completed' || report.testsPassed !== true || !report.evidenceUrl) {
  console.error('Not sent: project not verified completed.'); process.exit(2);
}
const to = process.env.DEXTER_OPENWA_TO;
const base = process.env.DEXTER_OPENWA_URL || 'http://127.0.0.1:8080';
if (!to || !/^\d+@c\.us$/.test(to)) { console.error('Set DEXTER_OPENWA_TO in international-number@c.us format.'); process.exit(2); }
const url = new URL('/api/messages/sendText', base);
if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Invalid URL protocol');
const content = `DEXTER HERMES: ${String(report.project || 'Proyecto')} terminado y verificado. Evidencia: ${report.evidenceUrl}`;
const headers = { 'content-type': 'application/json' };
if (process.env.DEXTER_OPENWA_API_KEY) headers['X-API-Key'] = process.env.DEXTER_OPENWA_API_KEY;
const response = await fetch(url, { method: 'POST', headers, body: JSON.stringify({ to, content, options: {} }), signal: AbortSignal.timeout(15000) });
if (!response.ok) throw new Error(`OpenWA returned HTTP ${response.status}`);
console.log('Completion notification accepted by OpenWA.');
