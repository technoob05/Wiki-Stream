/**
 * prepare-static-data.mjs
 * Run once after each pipeline run: node scripts/prepare-static-data.mjs
 *
 * Outputs to dashboard/public/data/:
 *   threats.json      — dashboard stats + top 50 threats (68 KB)
 *   geo_markers.json  — globe markers with real Wikipedia article coordinates where available
 *   report.md         — forensic report markdown
 */

import fs from 'fs';
import path from 'path';
import https from 'https';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..', '..');

const MASTER  = path.join(ROOT, 'experiments', 'reports', 'intelligence_master.json');
const REPORT  = path.join(ROOT, 'experiments', 'reports', 'final_forensic_report.md');
const OUT_DIR = path.join(__dirname, '..', 'public', 'data');

// ── Domain fallback geo regions ──
const DOMAIN_GEO = {
  'en.wikipedia.org': [
    { lat: 40.0,  lon: -95.0,  label: 'North America' },
    { lat: 51.5,  lon: -0.1,   label: 'Europe' },
    { lat: 35.7,  lon: 139.7,  label: 'East Asia' },
    { lat: -33.9, lon: 151.2,  label: 'Oceania' },
    { lat: 28.6,  lon: 77.2,   label: 'South Asia' },
  ],
  'vi.wikipedia.org': [
    { lat: 21.0, lon: 105.8, label: 'Vietnam' },
  ],
};

function seededRandom(seed) {
  let s = seed;
  return () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
}

// ── Fetch Wikipedia geo coords in batches of 50 ──
function httpsGet(url) {
  return new Promise((resolve) => {
    const req = https.get(url, { headers: { 'User-Agent': 'WikiStream/2.0 (educational)' } }, (res) => {
      let body = '';
      res.on('data', c => { body += c; });
      res.on('end', () => { try { resolve(JSON.parse(body)); } catch { resolve(null); } });
      res.on('error', () => resolve(null));
    });
    req.on('error', () => resolve(null));
    req.setTimeout(8000, () => { req.destroy(); resolve(null); });
  });
}

async function fetchWikiCoords(titles) {
  const result = new Map();
  if (!titles.length) return result;
  const BATCH = 50;
  for (let i = 0; i < titles.length; i += BATCH) {
    const batch = titles.slice(i, i + BATCH);
    const encoded = batch.map(t => encodeURIComponent(t)).join('|');
    const url = `https://en.wikipedia.org/w/api.php?action=query&titles=${encoded}&prop=coordinates&format=json&redirects=1`;
    const json = await httpsGet(url);
    if (!json?.query?.pages) continue;
    for (const page of Object.values(json.query.pages)) {
      if (page.coordinates?.length > 0) {
        result.set(page.title, { lat: page.coordinates[0].lat, lon: page.coordinates[0].lon });
      }
    }
    process.stdout.write(`  coords: ${Math.min(i + BATCH, titles.length)}/${titles.length}\r`);
    // Polite delay between batches
    await new Promise(r => setTimeout(r, 200));
  }
  console.log();
  return result;
}

// ── Main ──
if (!fs.existsSync(MASTER)) {
  console.error('❌  intelligence_master.json not found at:', MASTER);
  process.exit(1);
}

console.log('📖  Reading intelligence_master.json …');
const master = JSON.parse(fs.readFileSync(MASTER, 'utf-8'));
fs.mkdirSync(OUT_DIR, { recursive: true });

// ── 1. threats.json ──
const threats = {
  timestamp:    master.timestamp,
  total:        master.total,
  distribution: master.distribution,
  statistics:   master.statistics,
  methodology:  master.methodology,
  top_threats:  master.top_threats,
};
const threatsPath = path.join(OUT_DIR, 'threats.json');
fs.writeFileSync(threatsPath, JSON.stringify(threats));
console.log(`✅  threats.json      → ${(fs.statSync(threatsPath).size / 1024).toFixed(0)} KB`);

// ── 2. geo_markers.json — with real Wikipedia coordinates ──
const allVerdicts = master.all_verdicts || [];

// Collect unique article titles from markers we'll emit
const rand = seededRandom(42);
const tempMarkers = [];
let safeAdded = 0;
for (const v of allVerdicts) {
  if (v.action === 'SAFE') { if (safeAdded >= 60) continue; safeAdded++; }
  else if (!['BLOCK', 'FLAG', 'REVIEW'].includes(v.action)) continue;
  tempMarkers.push(v);
}
const uniqueTitles = [...new Set(tempMarkers.map(v => v.title))];

console.log(`🌍  Fetching Wikipedia coordinates for ${uniqueTitles.length} unique article titles…`);
const coordMap = await fetchWikiCoords(uniqueTitles);
console.log(`   Found real coords for ${coordMap.size} / ${uniqueTitles.length} articles`);

// Reset seeded random for deterministic jitter
const rand2 = seededRandom(42);
let safeAdded2 = 0;
const markers = [];

for (const v of allVerdicts) {
  if (v.action === 'SAFE') { if (safeAdded2 >= 60) continue; safeAdded2++; }
  else if (!['BLOCK', 'FLAG', 'REVIEW'].includes(v.action)) continue;

  const realCoord = coordMap.get(v.title);
  if (realCoord) {
    // Real article coordinate + tiny ±2° jitter to avoid perfect overlap
    markers.push({
      lat:    realCoord.lat + (rand2() * 4 - 2),
      lon:    realCoord.lon + (rand2() * 4 - 2),
      user:   v.user,
      title:  v.title,
      action: v.action,
      score:  v.score,
      region: 'Article Location',
    });
  } else {
    // Domain-based regional fallback
    const domain = v.domain || 'en.wikipedia.org';
    const regions = DOMAIN_GEO[domain] || DOMAIN_GEO['en.wikipedia.org'];
    const region = regions[Math.floor(rand2() * regions.length)];
    markers.push({
      lat:    region.lat + (rand2() * 16 - 8),
      lon:    region.lon + (rand2() * 16 - 8),
      user:   v.user,
      title:  v.title,
      action: v.action,
      score:  v.score,
      region: region.label,
    });
  }
}

const geoPath = path.join(OUT_DIR, 'geo_markers.json');
fs.writeFileSync(geoPath, JSON.stringify({ markers, total: markers.length }));
const real = markers.filter(m => m.region === 'Article Location').length;
console.log(`✅  geo_markers.json  → ${(fs.statSync(geoPath).size / 1024).toFixed(0)} KB`);
console.log(`   ${markers.length} markers — ${real} with real coords, ${markers.length - real} with regional fallback`);

// ── 3. report.md ──
if (fs.existsSync(REPORT)) {
  const reportPath = path.join(OUT_DIR, 'report.md');
  fs.copyFileSync(REPORT, reportPath);
  console.log(`✅  report.md         → ${(fs.statSync(reportPath).size / 1024).toFixed(0)} KB`);
} else {
  console.warn('⚠️   final_forensic_report.md not found — skipping');
}

console.log('\n✅  Done. Commit public/data/ and redeploy to Vercel.\n');
