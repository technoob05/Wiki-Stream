/**
 * prepare-static-data.mjs
 * Run once: node scripts/prepare-static-data.mjs
 * Reads experiments/reports/intelligence_master.json and outputs
 * two slim static files into dashboard/public/data/ that Vercel
 * can serve without any local filesystem or Python pipeline.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..', '..');

const MASTER = path.join(ROOT, 'experiments', 'reports', 'intelligence_master.json');
const OUT_DIR = path.join(__dirname, '..', 'public', 'data');

// ── Domain fallback geo regions (same as api.ts) ──
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
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

if (!fs.existsSync(MASTER)) {
  console.error('❌ intelligence_master.json not found at:', MASTER);
  process.exit(1);
}

console.log('📖 Reading intelligence_master.json …');
const master = JSON.parse(fs.readFileSync(MASTER, 'utf-8'));

// ── 1. threats.json — dashboard stats + top 50 threats ──
const threats = {
  timestamp:    master.timestamp,
  total:        master.total,
  distribution: master.distribution,
  statistics:   master.statistics,
  methodology:  master.methodology,
  top_threats:  master.top_threats,   // full 50 records, all fields
};

// ── 2. geo_markers.json — pre-computed markers for globe ──
const rand = seededRandom(42);
const allVerdicts = master.all_verdicts || [];
const markers = [];
let safeAdded = 0;

for (const v of allVerdicts) {
  if (v.action === 'SAFE') {
    if (safeAdded >= 60) continue;
    safeAdded++;
  } else if (!['BLOCK', 'FLAG', 'REVIEW'].includes(v.action)) {
    continue;
  }
  const domain = v.domain || 'en.wikipedia.org';
  const regions = DOMAIN_GEO[domain] || DOMAIN_GEO['en.wikipedia.org'];
  const region = regions[Math.floor(rand() * regions.length)];
  markers.push({
    lat:    region.lat + (rand() * 16 - 8),
    lon:    region.lon + (rand() * 16 - 8),
    user:   v.user,
    title:  v.title,
    action: v.action,
    score:  v.score,
    region: region.label,
  });
}

// ── Write output ──
fs.mkdirSync(OUT_DIR, { recursive: true });

const threatsPath = path.join(OUT_DIR, 'threats.json');
const geoPath     = path.join(OUT_DIR, 'geo_markers.json');

fs.writeFileSync(threatsPath, JSON.stringify(threats));
fs.writeFileSync(geoPath, JSON.stringify({ markers, total: markers.length }));

const kb = (p) => (fs.statSync(p).size / 1024).toFixed(0) + ' KB';
console.log(`✅ threats.json     → ${kb(threatsPath)}`);
console.log(`✅ geo_markers.json → ${kb(geoPath)}`);
console.log(`   ${markers.length} geo markers (${markers.filter(m=>m.action==='BLOCK').length} BLOCK, ${markers.filter(m=>m.action==='FLAG').length} FLAG, ${markers.filter(m=>m.action==='REVIEW').length} REVIEW, ${markers.filter(m=>m.action==='SAFE').length} SAFE)`);
console.log('\nDone! Commit dashboard/public/data/ to deploy with static data.');
