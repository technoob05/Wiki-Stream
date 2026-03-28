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
import https from 'https';

// ── Paths (relative to project root) ──
const EXPERIMENTS_DIR = path.resolve(__dirname, '..', 'experiments');
const DATA_DIR = path.join(EXPERIMENTS_DIR, 'data');
const REPORT_DIR = path.join(EXPERIMENTS_DIR, 'reports');
const PIPELINE_SCRIPT = path.join(EXPERIMENTS_DIR, '00_pipeline_manager.py');
const MASTER_FILE = path.join(REPORT_DIR, 'intelligence_master.json');
const REPORT_FILE = path.join(REPORT_DIR, 'final_forensic_report.md');

// ── In-memory coordinate cache (TTL = 10 min) ──
const COORD_CACHE_TTL = 10 * 60 * 1000;
const coordCache = new Map<string, { lat: number; lon: number } | null>();
let coordCacheTimestamp = 0;

// ── Earthquake cache ──
let earthquakeCache: any = null;
let earthquakeCacheTime = 0;
const EARTHQUAKE_CACHE_TTL = 10 * 60 * 1000;

// ── Fetch Wikipedia article coordinates ──
async function fetchWikiCoords(titles: string[]): Promise<Map<string, { lat: number; lon: number }>> {
  const result = new Map<string, { lat: number; lon: number }>();
  if (titles.length === 0) return result;

  const BATCH_SIZE = 50;
  for (let i = 0; i < titles.length; i += BATCH_SIZE) {
    const batch = titles.slice(i, i + BATCH_SIZE);
    const encodedTitles = batch.map(t => encodeURIComponent(t)).join('|');
    const apiUrl = `https://en.wikipedia.org/w/api.php?action=query&titles=${encodedTitles}&prop=coordinates&format=json&redirects=1`;

    await new Promise<void>((resolve) => {
      const req = https.get(apiUrl, {
        headers: { 'User-Agent': 'WikiStream-Dashboard/2.0 (educational)' },
      }, (res) => {
        let body = '';
        res.on('data', (chunk: Buffer) => { body += chunk.toString(); });
        res.on('end', () => {
          try {
            const json = JSON.parse(body);
            const pages = json?.query?.pages || {};
            for (const page of Object.values(pages) as any[]) {
              if (page.coordinates && page.coordinates.length > 0) {
                const coord = page.coordinates[0];
                result.set(page.title, { lat: coord.lat, lon: coord.lon });
              }
            }
          } catch { /* ignore parse errors */ }
          resolve();
        });
        res.on('error', () => resolve());
      });
      req.on('error', () => resolve());
      req.setTimeout(5000, () => { req.destroy(); resolve(); });
    });
  }
  return result;
}

// ── Generic HTTPS GET → parsed JSON (5s timeout) ──
function fetchUrl(url: string): Promise<any> {
  return new Promise((resolve) => {
    const req = https.get(url, {
      headers: { 'User-Agent': 'WikiStream-Dashboard/2.0 (educational)' },
    }, (res) => {
      let body = '';
      res.on('data', (c: Buffer) => { body += c.toString(); });
      res.on('end', () => { try { resolve(JSON.parse(body)); } catch { resolve(null); } });
      res.on('error', () => resolve(null));
    });
    req.on('error', () => resolve(null));
    req.setTimeout(5000, () => { req.destroy(); resolve(null); });
  });
}

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
              res.end(JSON.stringify({ detail: 'No data' }));
              return;
            }
            (async () => {
              const data = readJSON(MASTER_FILE);
              const rand = seededRandom(42);
              const allVerdicts: any[] = data.all_verdicts || [];

              // Refresh coordinate cache if stale or empty
              if (Date.now() - coordCacheTimestamp > COORD_CACHE_TTL || coordCache.size === 0) {
                const uniqueTitles = [...new Set(allVerdicts.map((v: any) => v.title as string))].slice(0, 150);
                const fetched = await fetchWikiCoords(uniqueTitles);
                coordCache.clear();
                for (const title of uniqueTitles) {
                  coordCache.set(title, fetched.get(title) ?? null);
                }
                coordCacheTimestamp = Date.now();
              }

              const markers: any[] = [];
              let safeAdded = 0;
              for (const v of allVerdicts) {
                // Cap SAFE markers at 60 to avoid overloading the globe
                if (v.action === 'SAFE') {
                  if (safeAdded >= 60) continue;
                  safeAdded++;
                } else if (!['BLOCK', 'FLAG', 'REVIEW'].includes(v.action)) {
                  continue;
                }

                const cached = coordCache.get(v.title);
                if (cached) {
                  // Use real Wikipedia article coordinates + tiny ±2° jitter
                  markers.push({
                    lat: cached.lat + (rand() * 4 - 2),
                    lon: cached.lon + (rand() * 4 - 2),
                    user: v.user,
                    title: v.title,
                    action: v.action,
                    score: v.score,
                    region: 'Article Location',
                  });
                } else {
                  // Fall back to domain-based regional random logic
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
              }
              res.end(JSON.stringify({ markers, total: markers.length }));
            })().catch((err: any) => {
              res.statusCode = 500;
              res.end(JSON.stringify({ detail: err.message }));
            });
            return;
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
                const records = parse(content, { columns: true, skip_empty_lines: true }) as Record<string, string>[];
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

          // ── GET /api/location/info?lat=X&lon=Y ──
          // Aggregates: Nominatim reverse geocode + Open-Meteo weather + Wikipedia nearby articles
          if (url.pathname === '/api/location/info' && req.method === 'GET') {
            const lat = parseFloat(url.searchParams.get('lat') || '');
            const lon = parseFloat(url.searchParams.get('lon') || '');
            if (isNaN(lat) || isNaN(lon)) {
              res.statusCode = 400;
              return res.end(JSON.stringify({ detail: 'lat and lon required' }));
            }
            (async () => {
              const [nominatim, weather, nearby] = await Promise.all([
                fetchUrl(`https://nominatim.openstreetmap.org/reverse?lat=${lat.toFixed(5)}&lon=${lon.toFixed(5)}&format=json&zoom=10`),
                fetchUrl(`https://api.open-meteo.com/v1/forecast?latitude=${lat.toFixed(4)}&longitude=${lon.toFixed(4)}&current_weather=true&timezone=auto`),
                fetchUrl(`https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord=${lat.toFixed(4)}|${lon.toFixed(4)}&gsradius=50000&gslimit=6&format=json`),
              ]);
              const result: any = { lat, lon };
              if (nominatim?.address) {
                const a = nominatim.address;
                result.place = a.city || a.town || a.village || a.county || a.state || nominatim.display_name?.split(',')[0] || null;
                result.country = a.country || null;
                result.countryCode = a.country_code?.toUpperCase() || null;
                result.displayName = nominatim.display_name || null;
              }
              if (weather?.current_weather) {
                result.weather = {
                  temp: Math.round(weather.current_weather.temperature),
                  windspeed: Math.round(weather.current_weather.windspeed),
                  weathercode: weather.current_weather.weathercode,
                };
              }
              if (nearby?.query?.geosearch?.length) {
                result.nearbyArticles = nearby.query.geosearch.map((a: any) => ({
                  title: a.title, lat: a.lat, lon: a.lon, dist: Math.round(a.dist),
                }));
              }
              res.end(JSON.stringify(result));
            })().catch((err: any) => {
              res.statusCode = 500;
              res.end(JSON.stringify({ detail: err.message }));
            });
            return;
          }

          // ── GET /api/article/preview?title=X ──
          // Wikipedia REST API summary: title, extract, thumbnail, URL
          if (url.pathname === '/api/article/preview' && req.method === 'GET') {
            const title = url.searchParams.get('title');
            if (!title) {
              res.statusCode = 400;
              return res.end(JSON.stringify({ detail: 'title required' }));
            }
            (async () => {
              const data = await fetchUrl(`https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}`);
              if (!data || data.type?.includes('not_found') || data.title === 'Not found.') {
                res.statusCode = 404;
                return res.end(JSON.stringify({ detail: 'Article not found' }));
              }
              res.end(JSON.stringify({
                title: data.title,
                extract: data.extract,
                thumbnail: data.thumbnail?.source || null,
                url: data.content_urls?.desktop?.page || `https://en.wikipedia.org/wiki/${encodeURIComponent(title)}`,
                coordinates: data.coordinates || null,
                description: data.description || null,
              }));
            })().catch((err: any) => {
              res.statusCode = 500;
              res.end(JSON.stringify({ detail: err.message }));
            });
            return;
          }

          // ── POST /api/pipeline/run ──
          if (url.pathname === '/api/pipeline/run' && req.method === 'POST') {
            exec(`python "${PIPELINE_SCRIPT}"`, { cwd: EXPERIMENTS_DIR });
            return res.end(JSON.stringify({ message: 'Pipeline started in background.' }));
          }

          // ── GET /api/iss ──
          // Real-time ISS position — no caching, proxied from wheretheiss.at
          if (url.pathname === '/api/iss' && req.method === 'GET') {
            (async () => {
              const data = await fetchUrl('https://api.wheretheiss.at/v1/satellites/25544');
              if (!data) { res.statusCode = 503; return res.end(JSON.stringify({ detail: 'ISS unavailable' })); }
              res.end(JSON.stringify({
                lat: data.latitude, lon: data.longitude,
                altitude: data.altitude, velocity: data.velocity,
                visibility: data.visibility, timestamp: data.timestamp,
              }));
            })().catch((err: any) => { res.statusCode = 500; res.end(JSON.stringify({ detail: err.message })); });
            return;
          }

          // ── GET /api/earthquakes ──
          // USGS significant earthquakes past month, cached 10 min
          if (url.pathname === '/api/earthquakes' && req.method === 'GET') {
            (async () => {
              if (!earthquakeCache || Date.now() - earthquakeCacheTime > EARTHQUAKE_CACHE_TTL) {
                const data = await fetchUrl('https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson');
                earthquakeCache = data;
                earthquakeCacheTime = Date.now();
              }
              if (!earthquakeCache) { res.statusCode = 503; return res.end(JSON.stringify({ detail: 'Earthquake data unavailable' })); }
              const features = earthquakeCache.features || [];
              const quakes = features.map((f: any) => ({
                lat: f.geometry.coordinates[1],
                lon: f.geometry.coordinates[0],
                depth: f.geometry.coordinates[2],
                magnitude: f.properties.mag,
                place: f.properties.place,
                time: f.properties.time,
                url: f.properties.url,
              })).filter((q: any) => q.magnitude != null);
              res.end(JSON.stringify({ quakes, total: quakes.length }));
            })().catch((err: any) => { res.statusCode = 500; res.end(JSON.stringify({ detail: err.message })); });
            return;
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
