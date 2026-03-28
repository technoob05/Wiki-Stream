/**
 * Wiki-Stream API — Node.js implementation
 * Embedded directly into Vite dev server as middleware.
 * No Python backend needed. Just `npm run dev`.
 */

import fs from 'fs';
import path from 'path';
import { parse } from 'csv-parse/sync';
import { exec } from 'child_process';
import type { Plugin } from 'vite';

// ── Paths (relative to project root) ──
const EXPERIMENTS_DIR = path.resolve(__dirname, '..', 'experiments');
const DATA_DIR = path.join(EXPERIMENTS_DIR, 'data');
const REPORT_DIR = path.join(EXPERIMENTS_DIR, 'reports');
const PIPELINE_SCRIPT = path.join(EXPERIMENTS_DIR, '00_pipeline_manager.py');
const MASTER_FILE = path.join(REPORT_DIR, 'intelligence_master.json');
const REPORT_FILE = path.join(REPORT_DIR, 'final_forensic_report.md');

// ── Seeded random for deterministic geo markers ──
function seededRandom(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

// ── Domain → geo regions ──
const DOMAIN_GEO: Record<string, { lat: number; lon: number; label: string }[]> = {
  'en.wikipedia.org': [
    { lat: 40.0, lon: -95.0, label: 'North America' },
    { lat: 51.5, lon: -0.1, label: 'Europe' },
    { lat: 35.7, lon: 139.7, label: 'East Asia' },
    { lat: -33.9, lon: 151.2, label: 'Oceania' },
    { lat: 28.6, lon: 77.2, label: 'South Asia' },
  ],
  'vi.wikipedia.org': [
    { lat: 21.0, lon: 105.8, label: 'Vietnam' },
  ],
};

// ── Helper: read JSON file ──
function readJSON(filePath: string): any {
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
}

// ── Helper: find CSV files recursively ──
function globCSV(dir: string, pattern: string): string[] {
  const results: string[] = [];
  if (!fs.existsSync(dir)) return results;
  const walk = (d: string) => {
    for (const entry of fs.readdirSync(d, { withFileTypes: true })) {
      const full = path.join(d, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.name.endsWith(pattern)) results.push(full);
    }
  };
  walk(dir);
  return results;
}

// ── Vite Plugin: API Middleware ──
export function apiPlugin(): Plugin {
  return {
    name: 'wikistream-api',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        // Only handle /api routes
        if (!req.url?.startsWith('/api')) return next();

        const url = new URL(req.url, 'http://localhost');
        res.setHeader('Content-Type', 'application/json');
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', '*');

        if (req.method === 'OPTIONS') {
          res.statusCode = 204;
          return res.end();
        }

        try {
          // ── GET /api/status ──
          if (url.pathname === '/api/status' && req.method === 'GET') {
            const exists = fs.existsSync(MASTER_FILE);
            return res.end(JSON.stringify({
              status: 'online',
              has_reports: exists,
              last_updated: exists ? fs.statSync(MASTER_FILE).mtimeMs / 1000 : null,
            }));
          }

          // ── GET /api/threats ──
          if (url.pathname === '/api/threats' && req.method === 'GET') {
            if (!fs.existsSync(MASTER_FILE)) {
              res.statusCode = 404;
              return res.end(JSON.stringify({ detail: 'Intelligence report not found. Run the pipeline first.' }));
            }
            const data = fs.readFileSync(MASTER_FILE, 'utf-8');
            return res.end(data);
          }

          // ── GET /api/geo/threats ──
          if (url.pathname === '/api/geo/threats' && req.method === 'GET') {
            if (!fs.existsSync(MASTER_FILE)) {
              res.statusCode = 404;
              return res.end(JSON.stringify({ detail: 'No data' }));
            }
            const data = readJSON(MASTER_FILE);
            const rand = seededRandom(42);
            const markers: any[] = [];

            for (const v of (data.all_verdicts || [])) {
              if (!['BLOCK', 'FLAG', 'REVIEW'].includes(v.action)) continue;
              const domain = v.domain || 'en.wikipedia.org';
              const regions = DOMAIN_GEO[domain] || DOMAIN_GEO['en.wikipedia.org'];
              const region = regions[Math.floor(rand() * regions.length)];
              markers.push({
                lat: region.lat + (rand() * 16 - 8),
                lon: region.lon + (rand() * 16 - 8),
                user: v.user,
                title: v.title,
                action: v.action,
                score: v.score,
                region: region.label,
              });
            }
            return res.end(JSON.stringify({ markers, total: markers.length }));
          }

          // ── GET /api/edits/detail?user=X&title=Y ──
          if (url.pathname === '/api/edits/detail' && req.method === 'GET') {
            const user = url.searchParams.get('user');
            const title = url.searchParams.get('title');
            if (!user || !title) {
              res.statusCode = 400;
              return res.end(JSON.stringify({ detail: 'user and title required' }));
            }

            const csvFiles = globCSV(DATA_DIR, '_attributed.csv');
            const found: any[] = [];
            for (const file of csvFiles) {
              try {
                const content = fs.readFileSync(file, 'utf-8');
                const records = parse(content, { columns: true, skip_empty_lines: true });
                for (const row of records) {
                  if (row.user === user && row.title === title) found.push(row);
                }
              } catch { /* skip */ }
            }

            if (found.length === 0) {
              res.statusCode = 404;
              return res.end(JSON.stringify({ detail: 'Edit forensic data not found.' }));
            }
            return res.end(JSON.stringify(found[found.length - 1]));
          }

          // ── GET /api/reports/master ──
          if (url.pathname === '/api/reports/master' && req.method === 'GET') {
            if (!fs.existsSync(REPORT_FILE)) {
              res.statusCode = 404;
              return res.end(JSON.stringify({ detail: 'Forensic report not found.' }));
            }
            const content = fs.readFileSync(REPORT_FILE, 'utf-8');
            return res.end(JSON.stringify({ content }));
          }

          // ── POST /api/pipeline/run ──
          if (url.pathname === '/api/pipeline/run' && req.method === 'POST') {
            exec(`python "${PIPELINE_SCRIPT}"`, { cwd: EXPERIMENTS_DIR });
            return res.end(JSON.stringify({ message: 'Pipeline started in background.' }));
          }

          // Unknown API route
          res.statusCode = 404;
          return res.end(JSON.stringify({ detail: 'Not found' }));

        } catch (err: any) {
          res.statusCode = 500;
          return res.end(JSON.stringify({ detail: err.message }));
        }
      });
    },
  };
}
