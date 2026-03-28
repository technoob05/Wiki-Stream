import { useRef, useState, useEffect, useMemo, Suspense } from 'react';
import { Canvas, useFrame, useThree, useLoader } from '@react-three/fiber';
import { Stars, Html, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ExternalLink, RefreshCw, MapPin, Wind, BookOpen, Globe2, Satellite, AlertTriangle, Sun, Map } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

// Primary: vivid Blue Marble from three-globe (known correct colors)
// Bump: 4K elevation from jsDelivr for extra terrain detail
const EARTH_DAY   = 'https://unpkg.com/three-globe@2.41.12/example/img/earth-blue-marble.jpg';
const EARTH_NIGHT = 'https://unpkg.com/three-globe@2.41.12/example/img/earth-night.jpg';
const EARTH_TOPO  = 'https://cdn.jsdelivr.net/gh/turban/webgl-earth@master/images/elev_bump_4k.jpg';
const EARTH_CLOUDS= 'https://cdn.jsdelivr.net/gh/turban/webgl-earth@master/images/fair_clouds_4k.png';

interface GeoMarker {
  lat: number; lon: number; user: string; title: string;
  action: string; score: number; region: string;
}

interface EarthquakeFeature {
  mag: number; place: string; lat: number; lon: number; time: number; depth: number;
}

interface ISSData {
  lat: number; lon: number; altitude: number; velocity: number;
}

const latLonToVec3 = (lat: number, lon: number, r: number): [number, number, number] => {
  const phi   = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return [-(r * Math.sin(phi) * Math.cos(theta)), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta)];
};

// ── Weather code → label ──
const weatherLabel = (code: number): string => {
  if (code === 0)  return '☀️ Clear sky';
  if (code <= 3)   return '⛅ Partly cloudy';
  if (code <= 48)  return '🌫️ Foggy';
  if (code <= 55)  return '🌦️ Drizzle';
  if (code <= 67)  return '🌧️ Rain';
  if (code <= 77)  return '❄️ Snow';
  if (code <= 82)  return '🌦️ Showers';
  if (code <= 99)  return '⛈️ Thunderstorm';
  return '🌍 Unknown';
};

// ── Location Info Panel ──
interface LocationInfo {
  place?: string; country?: string; countryCode?: string;
  weather?: { temp: number; windspeed: number; weathercode: number };
  nearbyArticles?: { title: string; lat: number; lon: number; dist: number }[];
}
const LocationInfoPanel: React.FC<{
  latLon: { lat: number; lon: number };
  onClose: () => void;
  onArticle: (title: string) => void;
}> = ({ latLon, onClose, onArticle }) => {
  const [info, setInfo] = useState<LocationInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setInfo(null);
    axios.get(`${API_BASE}/location/info?lat=${latLon.lat.toFixed(4)}&lon=${latLon.lon.toFixed(4)}`)
      .then(r => { setInfo(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [latLon.lat, latLon.lon]);

  const lat = latLon.lat, lon = latLon.lon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 12, scale: 0.96 }}
      transition={{ duration: 0.18 }}
      className="absolute bottom-16 right-4 z-20 w-72 max-w-[calc(100vw-2rem)] bg-black/92 backdrop-blur-2xl border border-white/10 rounded-2xl overflow-hidden shadow-[0_20px_60px_rgba(0,0,0,0.6)]"
    >
      <div className="px-4 py-3 border-b border-white/5 flex items-start justify-between bg-cyan-500/5">
        <div>
          <div className="text-[9px] text-cyan-400 font-mono uppercase tracking-widest flex items-center gap-1.5">
            <Globe2 size={9} /> Location Intel
          </div>
          <div className="text-xs text-white font-bold mt-0.5 font-mono">
            {Math.abs(lat).toFixed(3)}°{lat >= 0 ? 'N' : 'S'} · {Math.abs(lon).toFixed(3)}°{lon >= 0 ? 'E' : 'W'}
          </div>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-white/10 rounded-lg transition-colors mt-0.5">
          <X size={13} className="text-gray-500" />
        </button>
      </div>
      {loading ? (
        <div className="px-4 py-8 flex flex-col items-center gap-2 text-xs text-gray-600">
          <RefreshCw size={14} className="animate-spin text-cyan-500" />
          <span>Scanning location...</span>
        </div>
      ) : !info ? (
        <div className="px-4 py-8 text-xs text-gray-600 text-center">No data for this location</div>
      ) : (
        <div className="p-4 space-y-3">
          {(info.place || info.country) && (
            <div className="flex items-start gap-2.5">
              <MapPin size={13} className="text-cyan-400 mt-0.5 shrink-0" />
              <div>
                {info.place && <div className="text-xs text-white font-semibold">{info.place}</div>}
                {info.country && (
                  <div className="text-[11px] text-gray-400 flex items-center gap-1 mt-0.5">
                    {info.countryCode && (
                      <span className="font-mono text-[9px] bg-white/8 px-1.5 py-0.5 rounded text-gray-500">{info.countryCode}</span>
                    )}
                    {info.country}
                  </div>
                )}
              </div>
            </div>
          )}
          {info.weather && (
            <div className="bg-white/4 rounded-xl px-3 py-2.5 flex items-center justify-between border border-white/5">
              <div className="flex items-center gap-2">
                <span className="text-base">{weatherLabel(info.weather.weathercode).split(' ')[0]}</span>
                <div>
                  <div className="text-[11px] text-gray-300">{weatherLabel(info.weather.weathercode).slice(2)}</div>
                  <div className="flex items-center gap-1 text-[9px] text-gray-600 mt-0.5">
                    <Wind size={8} /> {info.weather.windspeed} km/h
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-xl font-bold text-white">{info.weather.temp}°</div>
                <div className="text-[9px] text-gray-600">Celsius</div>
              </div>
            </div>
          )}
          {info.nearbyArticles && info.nearbyArticles.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <BookOpen size={10} className="text-purple-400" />
                <span className="text-[9px] text-gray-600 uppercase tracking-widest font-bold">Nearby Wikipedia</span>
              </div>
              <div className="space-y-0.5">
                {info.nearbyArticles.map((a, i) => (
                  <button
                    key={i}
                    onClick={() => onArticle(a.title)}
                    className="w-full text-left px-2.5 py-1.5 rounded-lg hover:bg-cyan-500/10 transition-colors flex items-center justify-between group"
                  >
                    <span className="text-[11px] text-gray-300 group-hover:text-cyan-300 transition-colors truncate pr-2">{a.title}</span>
                    <span className="text-[9px] text-gray-600 shrink-0 font-mono">{a.dist < 1000 ? `${a.dist}m` : `${(a.dist/1000).toFixed(0)}km`}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
};

// ── Article Preview Panel ──
interface ArticlePreview {
  title: string; extract: string; thumbnail?: string;
  url: string; description?: string;
}
const ArticlePreviewPanel: React.FC<{
  title: string;
  onClose: () => void;
  onBack?: () => void;
}> = ({ title, onClose, onBack }) => {
  const [preview, setPreview] = useState<ArticlePreview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setPreview(null);
    axios.get(`${API_BASE}/article/preview?title=${encodeURIComponent(title)}`)
      .then(r => { setPreview(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [title]);

  return (
    <motion.div
      initial={{ opacity: 0, x: 10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 10 }}
      transition={{ duration: 0.18 }}
      className="absolute bottom-16 right-4 z-20 w-72 max-w-[calc(100vw-2rem)] bg-black/92 backdrop-blur-2xl border border-white/10 rounded-2xl overflow-hidden shadow-[0_20px_60px_rgba(0,0,0,0.6)]"
    >
      <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between bg-purple-500/5">
        <div className="flex items-center gap-2">
          {onBack && (
            <button onClick={onBack} className="p-1 hover:bg-white/10 rounded-lg transition-colors">
              <span className="text-gray-500 text-xs">←</span>
            </button>
          )}
          <div className="text-[9px] text-purple-400 font-mono uppercase tracking-widest">Wikipedia</div>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-white/10 rounded-lg transition-colors">
          <X size={13} className="text-gray-500" />
        </button>
      </div>
      {loading ? (
        <div className="px-4 py-8 flex justify-center">
          <RefreshCw size={14} className="animate-spin text-purple-400" />
        </div>
      ) : !preview ? (
        <div className="px-4 py-8 text-xs text-gray-600 text-center">Article not found</div>
      ) : (
        <div>
          {preview.thumbnail && (
            <div className="relative">
              <img src={preview.thumbnail} alt={preview.title} className="w-full h-36 object-cover" />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
            </div>
          )}
          <div className="p-4">
            <h4 className="text-sm font-bold text-white leading-tight">{preview.title}</h4>
            {preview.description && (
              <p className="text-[10px] text-purple-300/70 mt-0.5 italic">{preview.description}</p>
            )}
            <p className="text-[11px] text-gray-400 leading-relaxed mt-2 line-clamp-5">{preview.extract}</p>
            <a
              href={preview.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-flex items-center gap-1.5 text-[10px] text-cyan-400 hover:text-cyan-300 transition-colors"
            >
              <ExternalLink size={10} /> Open on Wikipedia
            </a>
          </div>
        </div>
      )}
    </motion.div>
  );
};

// ── Threat Marker ──
const ThreatMarker = ({ marker, radius, onClick }: { marker: GeoMarker; radius: number; onClick?: (marker: GeoMarker) => void }) => {
  const pos     = useMemo(() => latLonToVec3(marker.lat, marker.lon, radius + 0.02), [marker, radius]);
  const beamEnd = useMemo(() => latLonToVec3(marker.lat, marker.lon, radius + 0.45), [marker, radius]);
  const ref     = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const beamPos = useMemo(() => new Float32Array([...pos, ...beamEnd]), [pos, beamEnd]);

  useFrame((state) => {
    if (ref.current) ref.current.scale.setScalar(1 + Math.sin(state.clock.elapsedTime * 3 + marker.lat) * 0.3);
    if (ringRef.current) {
      const s = 1 + Math.sin(state.clock.elapsedTime * 2 + marker.lon) * 0.5;
      ringRef.current.scale.setScalar(s);
      (ringRef.current.material as THREE.MeshBasicMaterial).opacity = Math.max(0, 0.4 - s * 0.12);
    }
  });

  const color = marker.action === 'BLOCK' ? '#ef4444' : marker.action === 'FLAG' ? '#f97316' : marker.action === 'SAFE' ? '#22c55e' : '#facc15';
  const lookAt = useMemo(() => {
    const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,0,1), new THREE.Vector3(...pos).normalize());
    const e = new THREE.Euler().setFromQuaternion(q);
    return [e.x, e.y, e.z] as [number, number, number];
  }, [pos]);

  return (
    <group>
      <mesh ref={ref} position={pos}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
        onClick={(e) => { e.stopPropagation(); onClick?.(marker); }}
      >
        <sphereGeometry args={[0.035, 8, 8]} />
        <meshBasicMaterial color={color} />
      </mesh>
      <line>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[beamPos, 3]} />
        </bufferGeometry>
        <lineBasicMaterial color={color} transparent opacity={0.35} />
      </line>
      <mesh ref={ringRef} position={pos} rotation={lookAt}>
        <ringGeometry args={[0.05, 0.08, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.4} side={THREE.DoubleSide} />
      </mesh>
      {marker.action === 'BLOCK' && (
        <mesh position={pos}>
          <sphereGeometry args={[0.1, 12, 12]} />
          <meshBasicMaterial color={color} transparent opacity={0.1} />
        </mesh>
      )}
      {hovered && (
        <Html position={beamEnd} center>
          <div className="bg-black/95 border border-white/20 rounded-lg px-3 py-2 text-xs whitespace-nowrap pointer-events-none shadow-xl backdrop-blur-sm">
            <div className={`font-bold ${marker.action === 'BLOCK' ? 'text-red-400' : marker.action === 'FLAG' ? 'text-orange-400' : marker.action === 'SAFE' ? 'text-green-400' : 'text-yellow-400'}`}>
              {marker.action} — {marker.score.toFixed(1)}%
            </div>
            <div className="text-white font-medium">{marker.title.slice(0,40)}{marker.title.length > 40 ? '…' : ''}</div>
            <div className="text-gray-400">{marker.user} · {marker.region}</div>
            <div className="text-[9px] text-gray-600 mt-1">Click to explore article</div>
          </div>
        </Html>
      )}
    </group>
  );
};

// ── Animated arc with flowing particle ──
const AnimatedArc = ({ start, end, radius, index }: { start: [number,number,number]; end: [number,number,number]; radius: number; index: number }) => {
  const particleRef = useRef<THREE.Mesh>(null);
  const mid = useMemo(() => new THREE.Vector3((start[0]+end[0])/2,(start[1]+end[1])/2,(start[2]+end[2])/2).normalize().multiplyScalar(radius+0.7), [start,end,radius]);
  const curve = useMemo(() => new THREE.QuadraticBezierCurve3(new THREE.Vector3(...start), mid, new THREE.Vector3(...end)), [start,mid,end]);
  const geometry = useMemo(() => new THREE.BufferGeometry().setFromPoints(curve.getPoints(24)), [curve]);
  useFrame((state) => {
    if (particleRef.current) particleRef.current.position.copy(curve.getPoint(((state.clock.elapsedTime * 0.3 + index * 0.15) % 1)));
  });
  return (
    <group>
      <line><primitive object={geometry} attach="geometry" /><lineBasicMaterial color="#06b6d4" transparent opacity={0.15} /></line>
      <mesh ref={particleRef}><sphereGeometry args={[0.025,6,6]} /><meshBasicMaterial color="#22d3ee" /></mesh>
    </group>
  );
};

// ── Arc connections ──
const ThreatArcs = ({ markers, radius }: { markers: GeoMarker[]; radius: number }) => {
  const arcs = useMemo(() => {
    const byUser: Record<string, GeoMarker[]> = {};
    markers.forEach(m => { if (!byUser[m.user]) byUser[m.user]=[]; byUser[m.user].push(m); });
    const res: { start: [number,number,number]; end: [number,number,number] }[] = [];
    Object.values(byUser).forEach(edits => {
      if (edits.length < 2) return;
      for (let i=0; i<edits.length-1 && i<3; i++)
        res.push({ start: latLonToVec3(edits[i].lat,edits[i].lon,radius+0.02), end: latLonToVec3(edits[i+1].lat,edits[i+1].lon,radius+0.02) });
    });
    return res.slice(0,20);
  }, [markers, radius]);
  return <>{arcs.map((a,i) => <AnimatedArc key={i} start={a.start} end={a.end} radius={radius} index={i} />)}</>;
};

// ── Cloud layer ──
const CloudLayer = ({ radius }: { radius: number }) => {
  const cloudRef = useRef<THREE.Mesh>(null);
  const [cloudMap, setCloudMap] = useState<THREE.Texture | null>(null);
  useEffect(() => { new THREE.TextureLoader().load(EARTH_CLOUDS, t => setCloudMap(t)); }, []);
  useFrame(() => { if (cloudRef.current) cloudRef.current.rotation.y += 0.0001; });
  if (!cloudMap) return null;
  return (
    <mesh ref={cloudRef}>
      <sphereGeometry args={[radius+0.06, 96, 96]} />
      <meshStandardMaterial map={cloudMap} transparent opacity={0.2} depthWrite={false} side={THREE.DoubleSide} />
    </mesh>
  );
};

// ── Hover ring ──
const GlobeHoverRing = ({ position }: { position: THREE.Vector3 }) => {
  const r1 = useRef<THREE.Mesh>(null), r2 = useRef<THREE.Mesh>(null), r3 = useRef<THREE.Mesh>(null);
  const quaternion = useMemo(() => new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,1,0), position.clone().normalize()), [position]);
  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (r1.current) { r1.current.scale.setScalar(1+Math.sin(t*5)*0.25); (r1.current.material as THREE.MeshBasicMaterial).opacity = 0.35+Math.sin(t*5)*0.15; }
    if (r2.current) { r2.current.scale.setScalar(1+Math.sin(t*5+1.2)*0.35); (r2.current.material as THREE.MeshBasicMaterial).opacity = 0.2+Math.sin(t*5+1.2)*0.1; }
    if (r3.current) r3.current.rotation.z += 0.02;
  });
  return (
    <group position={position} quaternion={quaternion}>
      <mesh ref={r1}><ringGeometry args={[0.06,0.09,32]} /><meshBasicMaterial color="#22d3ee" transparent opacity={0.4} side={THREE.DoubleSide} depthWrite={false} /></mesh>
      <mesh ref={r2}><ringGeometry args={[0.12,0.16,32]} /><meshBasicMaterial color="#06b6d4" transparent opacity={0.2} side={THREE.DoubleSide} depthWrite={false} /></mesh>
      <mesh ref={r3}><ringGeometry args={[0.19,0.205,24]} /><meshBasicMaterial color="#a78bfa" transparent opacity={0.25} side={THREE.DoubleSide} depthWrite={false} /></mesh>
      <mesh><sphereGeometry args={[0.014,8,8]} /><meshBasicMaterial color="#67e8f9" /></mesh>
    </group>
  );
};

// ── Day / Night Terminator Shader ──
const DayNightOverlay = ({ radius }: { radius: number }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const shaderMat = useMemo(() => new THREE.ShaderMaterial({
    uniforms: { uSunDir: { value: new THREE.Vector3(1, 0, 0) } },
    vertexShader: `
      varying vec3 vNormal;
      void main() {
        vNormal = normal;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 uSunDir;
      varying vec3 vNormal;
      void main() {
        float d = dot(normalize(vNormal), normalize(uSunDir));
        float shadow = smoothstep(-0.15, 0.15, -d);
        gl_FragColor = vec4(0.0, 0.0, 0.04, shadow * 0.45);
      }
    `,
    transparent: true,
    depthWrite: false,
    side: THREE.FrontSide,
  }), []);

  useFrame(() => {
    if (!meshRef.current) return;
    const now = new Date();
    const utcHour = now.getUTCHours() + now.getUTCMinutes() / 60 + now.getUTCSeconds() / 3600;
    // Sun longitude: noon UTC at ~0°, midnight at 180°
    const solarAngle = ((utcHour / 24) * Math.PI * 2) - Math.PI;
    const startOfYear = new Date(Date.UTC(now.getUTCFullYear(), 0, 1));
    const dayOfYear = Math.ceil((now.getTime() - startOfYear.getTime()) / 86400000);
    const decl = 23.45 * Math.sin(((dayOfYear - 80) / 365) * Math.PI * 2) * (Math.PI / 180);
    // Sun world direction
    const sunWorld = new THREE.Vector3(
      Math.cos(decl) * Math.cos(solarAngle),
      Math.sin(decl),
      Math.cos(decl) * Math.sin(solarAngle)
    );
    // Transform to group-local space (undo Y rotation of parent group)
    const groupRotY = meshRef.current.parent?.rotation.y ?? 0;
    sunWorld.applyAxisAngle(new THREE.Vector3(0, 1, 0), -groupRotY);
    shaderMat.uniforms.uSunDir.value.copy(sunWorld);
  });

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[radius + 0.015, 64, 64]} />
      <primitive object={shaderMat} attach="material" />
    </mesh>
  );
};

// ── ISS Marker ──
const ISSMarker = ({ iss, trail, radius }: { iss: ISSData; trail: ISSData[]; radius: number }) => {
  const ISS_R = radius + 0.28;
  const pos = useMemo(() => latLonToVec3(iss.lat, iss.lon, ISS_R), [iss.lat, iss.lon, ISS_R]);
  const surfacePos = useMemo(() => latLonToVec3(iss.lat, iss.lon, radius + 0.02), [iss.lat, iss.lon, radius]);
  const ref = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const linePoints = useMemo(() => new Float32Array([...pos, ...surfacePos]), [pos, surfacePos]);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (ref.current) ref.current.scale.setScalar(1 + Math.sin(t * 5) * 0.25);
    if (glowRef.current) {
      (glowRef.current.material as THREE.MeshBasicMaterial).opacity = 0.08 + Math.sin(t * 3) * 0.04;
    }
  });

  return (
    <group>
      {/* Orbital trail */}
      {trail.map((p, i) => {
        const tp = latLonToVec3(p.lat, p.lon, ISS_R);
        return (
          <mesh key={i} position={tp}>
            <sphereGeometry args={[0.01, 4, 4]} />
            <meshBasicMaterial color="#fde68a" transparent opacity={(i + 1) / trail.length * 0.45} />
          </mesh>
        );
      })}
      {/* Main ISS dot */}
      <mesh ref={ref} position={pos}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true); }}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[0.042, 8, 8]} />
        <meshBasicMaterial color="#facc15" />
      </mesh>
      {/* Outer glow */}
      <mesh ref={glowRef} position={pos}>
        <sphereGeometry args={[0.09, 8, 8]} />
        <meshBasicMaterial color="#fef08a" transparent opacity={0.12} />
      </mesh>
      {/* Sub-orbital line */}
      <line>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[linePoints, 3]} />
        </bufferGeometry>
        <lineBasicMaterial color="#facc15" transparent opacity={0.18} />
      </line>
      {/* Shadow dot on Earth's surface */}
      <mesh position={surfacePos}>
        <circleGeometry args={[0.025, 12]} />
        <meshBasicMaterial color="#fde68a" transparent opacity={0.25} />
      </mesh>
      {hovered && (
        <Html position={[pos[0], pos[1] + 0.35, pos[2]]} center>
          <div className="bg-black/95 border border-yellow-500/40 rounded-xl px-3 py-2.5 text-xs whitespace-nowrap pointer-events-none shadow-2xl backdrop-blur-sm">
            <div className="text-yellow-400 font-bold flex items-center gap-1.5 mb-1">
              🛸 ISS — International Space Station
            </div>
            <div className="text-gray-300">{Math.abs(iss.lat).toFixed(2)}°{iss.lat>=0?'N':'S'} · {Math.abs(iss.lon).toFixed(2)}°{iss.lon>=0?'E':'W'}</div>
            <div className="text-gray-500 mt-0.5 flex gap-3">
              <span>Alt: <span className="text-yellow-300">{iss.altitude.toFixed(0)} km</span></span>
              <span>Speed: <span className="text-yellow-300">{iss.velocity.toFixed(0)} km/h</span></span>
            </div>
          </div>
        </Html>
      )}
    </group>
  );
};

// ── Earthquake Dot ──
const EarthquakeDot = ({ lat, lon, mag, place, radius }: {
  lat: number; lon: number; mag: number; place: string; radius: number;
}) => {
  const pos = useMemo(() => latLonToVec3(lat, lon, radius + 0.02), [lat, lon, radius]);
  const ringRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  const size = Math.max(0.022, (mag - 4.5) * 0.024);
  const color = mag >= 7 ? '#ef4444' : mag >= 6 ? '#f97316' : '#facc15';

  const lookAt = useMemo(() => {
    const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,0,1), new THREE.Vector3(...pos).normalize());
    const e = new THREE.Euler().setFromQuaternion(q);
    return [e.x, e.y, e.z] as [number, number, number];
  }, [pos]);

  useFrame((state) => {
    if (ringRef.current) {
      const s = 1 + Math.sin(state.clock.elapsedTime * 1.5 + lat) * 0.4;
      ringRef.current.scale.setScalar(s);
      (ringRef.current.material as THREE.MeshBasicMaterial).opacity = Math.max(0, 0.3 - s * 0.08);
    }
  });

  return (
    <group>
      <mesh position={pos}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true); }}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[size, 8, 8]} />
        <meshBasicMaterial color={color} />
      </mesh>
      {/* Ripple ring */}
      <mesh ref={ringRef} position={pos} rotation={lookAt}>
        <ringGeometry args={[size * 1.8, size * 2.5, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.3} side={THREE.DoubleSide} />
      </mesh>
      {/* Glow */}
      <mesh position={pos}>
        <sphereGeometry args={[size * 2.8, 8, 8]} />
        <meshBasicMaterial color={color} transparent opacity={0.06} />
      </mesh>
      {hovered && (
        <Html position={[pos[0], pos[1] + 0.25, pos[2]]} center>
          <div className="bg-black/95 border border-orange-500/30 rounded-xl px-3 py-2 text-xs whitespace-nowrap pointer-events-none shadow-xl backdrop-blur-sm">
            <div className={`font-bold mb-0.5 ${mag >= 7 ? 'text-red-400' : mag >= 6 ? 'text-orange-400' : 'text-yellow-400'}`}>
              M{mag.toFixed(1)} Earthquake
            </div>
            <div className="text-gray-300 max-w-[200px] whitespace-normal leading-tight">{place}</div>
          </div>
        </Html>
      )}
    </group>
  );
};

const EarthquakeMarkers = ({ quakes, radius }: { quakes: EarthquakeFeature[]; radius: number }) => (
  <>
    {quakes.map((q, i) => (
      <EarthquakeDot key={i} lat={q.lat} lon={q.lon} mag={q.mag} place={q.place} radius={radius} />
    ))}
  </>
);


// ── Earth Globe ──
const EarthGlobe = ({
  markers, onMarkerClick, onCursorMove, onGlobeClick,
  earthquakes, issPosition, issTrail,
  showQuakes, showISS, showDayNight,
}: {
  markers: GeoMarker[];
  onMarkerClick?: (m: GeoMarker) => void;
  onCursorMove?: (pos: { lat: number; lon: number } | null) => void;
  onGlobeClick?: (lat: number, lon: number) => void;
  earthquakes: EarthquakeFeature[];
  issPosition: ISSData | null;
  issTrail: ISSData[];
  showQuakes: boolean;
  showISS: boolean;
  showDayNight: boolean;
}) => {
  const groupRef = useRef<THREE.Group>(null);
  const isDragging = useRef(false);
  const justDragged = useRef(false);
  const RADIUS = 2.5;
  const [hoverPos, setHoverPos] = useState<THREE.Vector3 | null>(null);

  // useLoader suspends until textures are ready — same behavior as original working code
  const dayMap   = useLoader(THREE.TextureLoader, EARTH_DAY);
  const nightMap = useLoader(THREE.TextureLoader, EARTH_NIGHT);
  const topoMap  = useLoader(THREE.TextureLoader, EARTH_TOPO);
  const { gl } = useThree();

  // Apply max anisotropy for sharper texture at any zoom/angle
  useEffect(() => {
    const maxAniso = gl.capabilities.getMaxAnisotropy();
    [dayMap, nightMap, topoMap].forEach(t => {
      t.anisotropy = maxAniso;
      t.minFilter = THREE.LinearMipmapLinearFilter;
      t.magFilter = THREE.LinearFilter;
      t.needsUpdate = true;
    });
  }, [dayMap, nightMap, topoMap, gl]);

  useFrame(() => {
    if (groupRef.current && !isDragging.current) groupRef.current.rotation.y += 0.0006;
  });

  return (
    <>
      <ambientLight intensity={1.0} />
      <directionalLight position={[5,3,5]} intensity={3} color="#ffffff" />
      <directionalLight position={[-5,-2,-5]} intensity={1} color="#4dc9f6" />
      <pointLight position={[0,8,0]} intensity={0.8} color="#ffffff" />
      <Stars radius={120} depth={60} count={6000} factor={3} saturation={0} fade speed={0.4} />

      <group ref={groupRef}>
        {/* Earth sphere */}
        <mesh
          onPointerMove={(e) => {
            e.stopPropagation();
            if (e.uv) {
              const lat = (e.uv.y - 0.5) * 180;
              const lon = (e.uv.x - 0.5) * 360;
              onCursorMove?.({ lat, lon });
            }
            setHoverPos(e.point.clone().normalize().multiplyScalar(RADIUS + 0.01));
          }}
          onPointerLeave={() => { setHoverPos(null); onCursorMove?.(null); }}
          onClick={(e) => {
            e.stopPropagation();
            if (justDragged.current) return;
            if (e.uv) {
              const lat = (e.uv.y - 0.5) * 180;
              const lon = (e.uv.x - 0.5) * 360;
              onGlobeClick?.(lat, lon);
            }
          }}
        >
          <sphereGeometry args={[RADIUS, 256, 256]} />
          <meshStandardMaterial
            map={dayMap}
            bumpMap={topoMap} bumpScale={0.05}
            roughness={0.8} metalness={0.0}
            emissiveMap={nightMap}
            emissive={new THREE.Color('#ffddaa')} emissiveIntensity={1.5}
          />
        </mesh>

        {/* Atmosphere layers */}
        <mesh><sphereGeometry args={[RADIUS+0.04,64,64]} /><meshBasicMaterial color="#7dd3fc" transparent opacity={0.06} side={THREE.BackSide} /></mesh>
        <mesh><sphereGeometry args={[RADIUS+0.12,64,64]} /><meshBasicMaterial color="#38bdf8" transparent opacity={0.04} side={THREE.BackSide} /></mesh>
        <mesh><sphereGeometry args={[RADIUS+0.30,48,48]} /><meshBasicMaterial color="#0ea5e9" transparent opacity={0.02} side={THREE.BackSide} /></mesh>
        <mesh><sphereGeometry args={[RADIUS+0.55,32,32]} /><meshBasicMaterial color="#0284c7" transparent opacity={0.008} side={THREE.BackSide} /></mesh>

        <CloudLayer radius={RADIUS} />

        {/* Day/Night terminator */}
        {showDayNight && <DayNightOverlay radius={RADIUS} />}

        {/* Threat markers + arcs */}
        {markers.map((m, i) => (
          <ThreatMarker key={`${m.user}-${m.title}-${i}`} marker={m} radius={RADIUS} onClick={onMarkerClick} />
        ))}
        <ThreatArcs markers={markers} radius={RADIUS} />

        {/* Earthquake markers */}
        {showQuakes && <EarthquakeMarkers quakes={earthquakes} radius={RADIUS} />}

        {/* ISS tracker */}
        {showISS && issPosition && <ISSMarker iss={issPosition} trail={issTrail} radius={RADIUS} />}
      </group>

      {hoverPos && <GlobeHoverRing position={hoverPos} />}

      <OrbitControls
        enableZoom enablePan={false} minDistance={4} maxDistance={12}
        zoomSpeed={0.5} rotateSpeed={0.5}
        onStart={() => { isDragging.current = true; }}
        onEnd={() => {
          isDragging.current = false;
          justDragged.current = true;
          setTimeout(() => { justDragged.current = false; }, 120);
        }}
      />
    </>
  );
};

// ── Loading fallback ──
const GlobeLoader = () => (
  <mesh><sphereGeometry args={[2.5,32,32]} /><meshBasicMaterial color="#0a1628" wireframe transparent opacity={0.3} /></mesh>
);

// ── Flat Map View (2D equirectangular — enhanced) ──
const FlatMapView: React.FC<{
  markers: GeoMarker[];
  issPosition: ISSData | null;
  issTrail: ISSData[];
  earthquakes: EarthquakeFeature[];
  showISS: boolean;
  showQuakes: boolean;
  onMarkerClick?: (m: GeoMarker) => void;
  onMapClick?: (lat: number, lon: number) => void;
  onCursorMove?: (pos: { lat: number; lon: number } | null) => void;
}> = ({ markers, issPosition, issTrail, earthquakes, showISS, showQuakes, onMarkerClick, onMapClick, onCursorMove }) => {
  const [cursor, setCursor] = useState<{ x: number; y: number } | null>(null);

  const toXY = (lat: number, lon: number) => ({
    x: (lon + 180) / 360 * 100,
    y: (90 - lat) / 180 * 100,
  });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const fx = (e.clientX - rect.left) / rect.width;
    const fy = (e.clientY - rect.top) / rect.height;
    setCursor({ x: fx * 100, y: fy * 100 });
    onCursorMove?.({ lat: 90 - fy * 180, lon: fx * 360 - 180 });
  };

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const fx = (e.clientX - rect.left) / rect.width;
    const fy = (e.clientY - rect.top) / rect.height;
    onMapClick?.(90 - fy * 180, fx * 360 - 180);
  };

  const LAT_LINES = [-60, -30, 0, 30, 60];
  const LON_LINES = [-150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150];

  return (
    <div
      className="w-full h-full relative overflow-hidden cursor-none select-none"
      style={{ backgroundImage: `url(${EARTH_DAY})`, backgroundSize: '100% 100%' }}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => { setCursor(null); onCursorMove?.(null); }}
      onClick={handleClick}
    >
      {/* Base dark tint */}
      <div className="absolute inset-0 pointer-events-none" style={{ background: 'rgba(0,4,18,0.42)' }} />

      {/* Vignette — dark edges for immersion */}
      <div className="absolute inset-0 pointer-events-none" style={{
        background: 'radial-gradient(ellipse 92% 92% at 50% 50%, transparent 38%, rgba(0,0,15,0.82) 100%)'
      }} />

      {/* Animated radar sweep */}
      <div className="fm-sweep" />

      {/* Latitude grid */}
      {LAT_LINES.map(lat => {
        const y = (90 - lat) / 180 * 100;
        const isEq = lat === 0;
        return (
          <div key={lat} className="absolute w-full pointer-events-none" style={{
            top: `${y}%`,
            borderTop: `1px solid rgba(6,182,212,${isEq ? 0.55 : 0.18})`,
            boxShadow: isEq ? '0 0 6px rgba(6,182,212,0.12)' : undefined,
          }}>
            <span className="absolute left-2 px-1 py-px text-[9px] font-mono rounded"
              style={{ color: 'rgba(6,182,212,0.8)', background: 'rgba(0,0,0,0.55)', transform: 'translateY(-100%)' }}>
              {lat > 0 ? '+' : ''}{lat}°
            </span>
          </div>
        );
      })}

      {/* Longitude grid */}
      {LON_LINES.map(lon => {
        const x = (lon + 180) / 360 * 100;
        const isPM = lon === 0;
        return (
          <div key={lon} className="absolute h-full pointer-events-none" style={{
            left: `${x}%`, top: 0,
            borderLeft: `1px solid rgba(6,182,212,${isPM ? 0.55 : 0.18})`,
            boxShadow: isPM ? '0 0 6px rgba(6,182,212,0.12)' : undefined,
          }}>
            <span className="absolute bottom-2 px-1 py-px text-[8px] font-mono rounded"
              style={{ color: 'rgba(6,182,212,0.7)', background: 'rgba(0,0,0,0.55)', transform: 'translateX(-50%)' }}>
              {lon}°
            </span>
          </div>
        );
      })}

      {/* Tropic of Cancer / Capricorn */}
      {[23.5, -23.5].map(lat => (
        <div key={lat} className="absolute w-full pointer-events-none" style={{
          top: `${(90 - lat) / 180 * 100}%`,
          borderTop: '1px dashed rgba(251,191,36,0.25)',
        }}>
          <span className="absolute right-2 text-[8px] font-mono" style={{ color: 'rgba(251,191,36,0.5)', transform: 'translateY(-100%)' }}>
            {lat > 0 ? 'Tropic of Cancer' : 'Tropic of Capricorn'}
          </span>
        </div>
      ))}

      {/* Corner HUD brackets */}
      {(['tl','tr','bl','br'] as const).map(c => (
        <div key={c} className={`absolute pointer-events-none fm-bracket`} style={{
          width: 30, height: 30,
          top: c.startsWith('t') ? 10 : undefined,
          bottom: c.startsWith('b') ? 10 : undefined,
          left: c.endsWith('l') ? 10 : undefined,
          right: c.endsWith('r') ? 10 : undefined,
          borderTop:    c.startsWith('t') ? '2px solid rgba(6,182,212,0.6)' : undefined,
          borderBottom: c.startsWith('b') ? '2px solid rgba(6,182,212,0.6)' : undefined,
          borderLeft:   c.endsWith('l')   ? '2px solid rgba(6,182,212,0.6)' : undefined,
          borderRight:  c.endsWith('r')   ? '2px solid rgba(6,182,212,0.6)' : undefined,
        }} />
      ))}

      {/* ISS orbital trail */}
      {showISS && issTrail.map((p, i) => {
        const { x, y } = toXY(p.lat, p.lon);
        const ratio = (i + 1) / issTrail.length;
        return (
          <div key={i} className="absolute pointer-events-none" style={{
            left: `${x}%`, top: `${y}%`,
            transform: 'translate(-50%,-50%)',
            width: 4 + ratio * 2, height: 4 + ratio * 2,
            borderRadius: '50%',
            background: '#fde68a',
            opacity: ratio * 0.6,
            boxShadow: `0 0 ${ratio * 6}px rgba(253,230,138,${ratio * 0.5})`,
          }} />
        );
      })}

      {/* ISS live beacon */}
      {showISS && issPosition && (() => {
        const { x, y } = toXY(issPosition.lat, issPosition.lon);
        return (
          <div className="absolute z-20 pointer-events-none"
            style={{ left: `${x}%`, top: `${y}%`, transform: 'translate(-50%,-50%)' }}>
            <div className="fm-pulse-ring" style={{ width: 22, height: 22, top: -11, left: -11, border: '1px solid rgba(250,204,21,0.7)', animationDuration: '2s' }} />
            <div className="fm-pulse-ring" style={{ width: 22, height: 22, top: -11, left: -11, border: '1px solid rgba(250,204,21,0.4)', animationDuration: '2s', animationDelay: '1s' }} />
            <div className="fm-iss-core" style={{
              position: 'absolute', width: 12, height: 12, borderRadius: '50%',
              background: '#facc15', top: -6, left: -6,
            }} />
            <div className="absolute whitespace-nowrap font-mono font-bold text-[9px] tracking-widest"
              style={{ top: -22, left: '50%', transform: 'translateX(-50%)', color: '#fde68a', textShadow: '0 0 10px rgba(250,204,21,0.9)' }}>
              ◆ ISS
            </div>
            <div className="absolute whitespace-nowrap font-mono text-[8px]"
              style={{ top: 10, left: '50%', transform: 'translateX(-50%)', color: 'rgba(253,230,138,0.6)' }}>
              {issPosition.altitude.toFixed(0)}km
            </div>
          </div>
        );
      })()}

      {/* Earthquake markers */}
      {showQuakes && earthquakes.map((q, i) => {
        const { x, y } = toXY(q.lat, q.lon);
        const color = q.mag >= 7 ? '#ef4444' : q.mag >= 6 ? '#f97316' : '#facc15';
        const sz = Math.max(8, (q.mag - 4.5) * 5.5);
        const delay = (i * 137) % 2000;
        return (
          <div key={i} className="absolute group z-10"
            style={{ left: `${x}%`, top: `${y}%`, transform: 'translate(-50%,-50%)' }}>
            <div className="fm-pulse-ring" style={{
              width: sz * 2.4, height: sz * 2.4, top: -sz * 1.2, left: -sz * 1.2,
              border: `1px solid ${color}`, animationDuration: '2.8s', animationDelay: `${delay}ms`,
            }} />
            <div style={{
              position: 'absolute', width: sz, height: sz, borderRadius: '50%',
              background: color, top: -sz/2, left: -sz/2,
              boxShadow: `0 0 ${sz * 1.5}px ${color}90, 0 0 ${sz * 3}px ${color}30`,
            }} />
            <div className="absolute opacity-0 group-hover:opacity-100 transition-all duration-150 pointer-events-none z-50"
              style={{ bottom: sz/2 + 8, left: '50%', transform: 'translateX(-50%)' }}>
              <div className="bg-black/95 border border-orange-500/40 rounded-xl px-3 py-2 text-[9px] whitespace-nowrap shadow-2xl backdrop-blur-sm">
                <div className="font-bold text-orange-400 mb-0.5">M{q.mag.toFixed(1)} Earthquake</div>
                <div className="text-gray-300 max-w-[200px] whitespace-normal leading-tight">{q.place}</div>
                <div className="text-gray-600 mt-0.5">Depth: {q.depth.toFixed(0)} km</div>
              </div>
            </div>
          </div>
        );
      })}

      {/* Threat markers */}
      {markers.map((m, i) => {
        const { x, y } = toXY(m.lat, m.lon);
        const color = m.action === 'BLOCK' ? '#ef4444' : m.action === 'FLAG' ? '#f97316' : m.action === 'SAFE' ? '#22c55e' : '#facc15';
        const delay = (i * 73) % 3000;
        return (
          <div key={i} className="absolute group z-10 cursor-pointer"
            style={{ left: `${x}%`, top: `${y}%`, transform: 'translate(-50%,-50%)' }}
            onClick={(e) => { e.stopPropagation(); onMarkerClick?.(m); }}>
            <div className="fm-pulse-ring" style={{
              width: 14, height: 14, top: -7, left: -7,
              border: `1px solid ${color}`,
              animationDuration: '2.2s', animationDelay: `${delay}ms`,
            }} />
            <div style={{
              position: 'absolute', width: 8, height: 8, borderRadius: '50%',
              background: color, top: -4, left: -4,
              boxShadow: `0 0 8px ${color}, 0 0 16px ${color}50`,
              transition: 'transform 0.2s',
            }} className="group-hover:scale-150" />
            <div className="absolute opacity-0 group-hover:opacity-100 transition-all duration-150 pointer-events-none z-50"
              style={{ bottom: 10, left: '50%', transform: 'translateX(-50%)' }}>
              <div className="bg-black/95 border border-white/15 rounded-xl px-2.5 py-2 text-[9px] whitespace-nowrap shadow-2xl backdrop-blur-sm">
                <div className="font-bold mb-0.5" style={{ color }}>{m.action} — {m.score.toFixed(0)}%</div>
                <div className="text-white">{m.title.slice(0, 36)}{m.title.length > 36 ? '…' : ''}</div>
                <div className="text-gray-500 mt-0.5">{m.user} · {m.region}</div>
              </div>
            </div>
          </div>
        );
      })}

      {/* Custom crosshair cursor */}
      {cursor && (
        <div className="absolute pointer-events-none z-30"
          style={{ left: `${cursor.x}%`, top: `${cursor.y}%` }}>
          {/* H left arm */}
          <div style={{ position:'absolute', top:-0.5, left:-28, width:22, height:1, background:'rgba(6,182,212,0.85)' }} />
          {/* H right arm */}
          <div style={{ position:'absolute', top:-0.5, left:6, width:22, height:1, background:'rgba(6,182,212,0.85)' }} />
          {/* V top arm */}
          <div style={{ position:'absolute', left:-0.5, top:-28, height:22, width:1, background:'rgba(6,182,212,0.85)' }} />
          {/* V bottom arm */}
          <div style={{ position:'absolute', left:-0.5, top:6, height:22, width:1, background:'rgba(6,182,212,0.85)' }} />
          {/* Center ring */}
          <div style={{
            position:'absolute', width:8, height:8, borderRadius:'50%',
            border:'1.5px solid rgba(6,182,212,0.95)',
            top:-4, left:-4,
            boxShadow:'0 0 6px rgba(6,182,212,0.4)',
          }} />
        </div>
      )}

      {/* Bottom projection label */}
      <div className="absolute bottom-2 left-1/2 -translate-x-1/2 text-[8px] text-cyan-500/35 font-mono tracking-[0.25em] pointer-events-none uppercase">
        Equirectangular · WGS84 · Real-time
      </div>
    </div>
  );
};

// ── Main GlobeView ──
export const GlobeView: React.FC<{ onThreatClick?: (user: string, title: string) => void; safeCount?: number }> = ({ onThreatClick, safeCount: safeProp }) => {
  const [markers,      setMarkers]      = useState<GeoMarker[]>([]);
  const [legendOpen,   setLegendOpen]   = useState(false);
  const [cursorLatLon, setCursorLatLon] = useState<{ lat: number; lon: number } | null>(null);
  const [showBlock,    setShowBlock]    = useState(true);
  const [showFlag,     setShowFlag]     = useState(true);
  const [showReview,   setShowReview]   = useState(false);
  const [showSafe,     setShowSafe]     = useState(false);

  // New layers
  const [issPosition, setIssPosition] = useState<ISSData | null>(null);
  const [issTrail,    setIssTrail]    = useState<ISSData[]>([]);
  const [earthquakes, setEarthquakes] = useState<EarthquakeFeature[]>([]);
  const [showISS,     setShowISS]     = useState(true);
  const [showQuakes,  setShowQuakes]  = useState(true);
  const [showDayNight,setShowDayNight]= useState(false);
  const [viewMode,    setViewMode]    = useState<'globe' | 'map'>('globe');

  // Panel state
  const [locationClick,    setLocationClick]    = useState<{ lat: number; lon: number } | null>(null);
  const [articleToPreview, setArticleToPreview] = useState<string | null>(null);
  const prevLocation = useRef<{ lat: number; lon: number } | null>(null);

  // Fetch geo threats
  useEffect(() => {
    const fetchGeo = () => {
      axios.get(`${API_BASE}/geo/threats`).then(r => setMarkers(r.data.markers || [])).catch(() => {});
    };
    fetchGeo();
    const iv = setInterval(fetchGeo, 30000);
    return () => clearInterval(iv);
  }, []);

  // Poll ISS every 5 seconds
  useEffect(() => {
    const fetchISS = () => {
      axios.get(`${API_BASE}/iss`).then(r => {
        const d = r.data;
        if (d && typeof d.latitude === 'number') {
          const pos: ISSData = { lat: d.latitude, lon: d.longitude, altitude: d.altitude, velocity: d.velocity };
          setIssPosition(pos);
          setIssTrail(prev => [...prev.slice(-29), pos]);
        }
      }).catch(() => {});
    };
    fetchISS();
    const iv = setInterval(fetchISS, 5000);
    return () => clearInterval(iv);
  }, []);

  // Fetch earthquakes on mount + refresh hourly
  useEffect(() => {
    const fetchQuakes = () => {
      axios.get(`${API_BASE}/earthquakes`).then(r => {
        const features = (r.data.features || []) as any[];
        setEarthquakes(features.map((f: any) => ({
          mag: f.properties.mag,
          place: f.properties.place,
          lat: f.geometry.coordinates[1],
          lon: f.geometry.coordinates[0],
          depth: f.geometry.coordinates[2],
          time: f.properties.time,
        })).filter((q: EarthquakeFeature) => q.mag >= 5));
      }).catch(() => {});
    };
    fetchQuakes();
    const iv = setInterval(fetchQuakes, 3600000);
    return () => clearInterval(iv);
  }, []);

  const blockCount   = markers.filter(m => m.action === 'BLOCK').length;
  const flagCount    = markers.filter(m => m.action === 'FLAG').length;
  const reviewCount  = markers.filter(m => m.action === 'REVIEW').length;
  const safeGeoCount = markers.filter(m => m.action === 'SAFE').length;
  const safeCount    = safeProp ?? 0;
  const regions      = [...new Set(markers.map(m => m.region))];
  const filteredMarkers = markers.filter(m =>
    (m.action === 'BLOCK' && showBlock) || (m.action === 'FLAG' && showFlag) ||
    (m.action === 'REVIEW' && showReview) || (m.action === 'SAFE' && showSafe)
  );

  const handleGlobeClick = (lat: number, lon: number) => {
    setLocationClick({ lat, lon });
    setArticleToPreview(null);
    prevLocation.current = { lat, lon };
  };

  const handleMarkerClick = (m: GeoMarker) => {
    setArticleToPreview(m.title);
    prevLocation.current = null;
    onThreatClick?.(m.user, m.title);
  };

  const closePanel = () => {
    setLocationClick(null);
    setArticleToPreview(null);
  };

  return (
    <div className="w-full h-full min-h-[400px] relative bg-[#030712]">

      {/* Threat Radar label — compact on mobile */}
      <div
        className="absolute top-4 left-4 z-10 bg-black/60 backdrop-blur-md px-2.5 sm:px-4 py-1.5 sm:py-3 rounded-lg border border-white/10 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={() => setLegendOpen(!legendOpen)}
      >
        <h3 className="text-[10px] sm:text-sm font-mono text-cyan-400 uppercase tracking-widest font-bold">Threat Radar</h3>
        <p className="text-[9px] sm:text-xs text-gray-400 mt-0.5">
          {markers.length > 0 ? `${filteredMarkers.length} threats · ${regions.length} regions` : 'Scanning...'}
        </p>
        <p className="hidden sm:block text-[9px] text-gray-600 mt-0.5">Click globe to explore location</p>
      </div>

      {/* Threat filter buttons — left-aligned below label on mobile, centered on sm+ */}
      <div className="absolute top-[3.75rem] sm:top-4 left-4 sm:left-1/2 sm:-translate-x-1/2 z-10 flex gap-1 sm:gap-2 flex-wrap">
        {[
          { action: 'BLOCK',  count: blockCount,   show: showBlock,  set: setShowBlock,  active: 'bg-red-500/20 text-red-400 border-red-500/40' },
          { action: 'FLAG',   count: flagCount,    show: showFlag,   set: setShowFlag,   active: 'bg-orange-500/20 text-orange-400 border-orange-500/40' },
          { action: 'REVIEW', count: reviewCount,  show: showReview, set: setShowReview, active: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40' },
          { action: 'SAFE',   count: safeGeoCount > 0 ? safeGeoCount : safeCount, show: showSafe, set: setShowSafe, active: 'bg-green-500/20 text-green-400 border-green-500/40' },
        ].map(({ action, count, show, set, active }) => (
          <button key={action} onClick={() => set(!show)}
            className={`px-1.5 sm:px-3 py-1 sm:py-1.5 rounded-lg text-[9px] sm:text-[10px] font-bold border transition-all ${show ? active : 'bg-white/5 text-gray-600 border-white/10'}`}
          >
            {action} ({count})
          </button>
        ))}
      </div>

      {/* Layer toggle buttons — icon-only on mobile */}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-1.5">
        {/* View mode toggle */}
        <button
          onClick={() => { setViewMode(v => v === 'globe' ? 'map' : 'globe'); closePanel(); }}
          className="flex items-center justify-center gap-1.5 p-1.5 sm:px-2.5 sm:py-1.5 rounded-lg text-[10px] font-bold border transition-all bg-cyan-500/15 text-cyan-300 border-cyan-500/40 hover:bg-cyan-500/25 mb-0.5"
          title={viewMode === 'globe' ? 'Flat Map' : '3D Globe'}
        >
          {viewMode === 'globe' ? <><Map size={10} /><span className="hidden sm:inline"> FLAT MAP</span></> : <><Globe2 size={10} /><span className="hidden sm:inline"> 3D GLOBE</span></>}
        </button>
        <button
          onClick={() => setShowISS(!showISS)}
          className={`flex items-center justify-center gap-1.5 p-1.5 sm:px-2.5 sm:py-1.5 rounded-lg text-[10px] font-bold border transition-all ${
            showISS ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40' : 'bg-white/5 text-gray-600 border-white/10'
          }`}
          title="ISS Live"
        >
          <Satellite size={10} />
          <span className="hidden sm:inline">ISS LIVE</span>
          {showISS && issPosition && (
            <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse inline-block" />
          )}
        </button>
        <button
          onClick={() => setShowQuakes(!showQuakes)}
          className={`flex items-center justify-center gap-1.5 p-1.5 sm:px-2.5 sm:py-1.5 rounded-lg text-[10px] font-bold border transition-all ${
            showQuakes ? 'bg-orange-500/20 text-orange-400 border-orange-500/40' : 'bg-white/5 text-gray-600 border-white/10'
          }`}
          title={`Earthquakes (${earthquakes.length})`}
        >
          <AlertTriangle size={10} />
          <span className="hidden sm:inline">QUAKES ({earthquakes.length})</span>
        </button>
        {viewMode === 'globe' && (
          <button
            onClick={() => setShowDayNight(!showDayNight)}
            className={`flex items-center justify-center gap-1.5 p-1.5 sm:px-2.5 sm:py-1.5 rounded-lg text-[10px] font-bold border transition-all ${
              showDayNight ? 'bg-indigo-500/20 text-indigo-400 border-indigo-500/40' : 'bg-white/5 text-gray-600 border-white/10'
            }`}
            title="Day/Night"
          >
            <Sun size={10} />
            <span className="hidden sm:inline">DAY/NIGHT</span>
          </button>
        )}
      </div>

      {/* Legend popup */}
      {legendOpen && markers.length > 0 && (
        <div className="absolute top-24 left-4 z-10 bg-black/90 backdrop-blur-md px-4 py-3 rounded-lg border border-white/10 space-y-2 min-w-[180px]">
          <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">Breakdown</span>
          {[
            { label: 'BLOCK',  color: 'bg-red-500',    text: 'text-red-400',    count: blockCount  },
            { label: 'FLAG',   color: 'bg-orange-500', text: 'text-orange-400', count: flagCount   },
            { label: 'REVIEW', color: 'bg-yellow-500', text: 'text-yellow-400', count: reviewCount },
          ].map(item => (
            <div key={item.label} className="flex items-center gap-2">
              <div className={`w-2.5 h-2.5 rounded-full ${item.color}`} />
              <span className={`text-xs ${item.text} font-bold`}>{item.label}</span>
              <span className="text-xs text-gray-400 ml-auto">{item.count}</span>
            </div>
          ))}
          <div className="border-t border-white/10 pt-2 mt-2">
            <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-1">Regions</div>
            {regions.map((r, i) => (
              <div key={i} className="text-[10px] text-gray-400">{r} ({markers.filter(m => m.region === r).length})</div>
            ))}
          </div>
        </div>
      )}

      {/* Coordinate display — hidden on mobile */}
      <div className="hidden sm:flex absolute bottom-4 right-4 z-10 font-mono bg-black/50 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-white/5 flex-col items-end gap-0.5">
        {cursorLatLon ? (
          <>
            <span className="text-[10px] text-cyan-400">
              {cursorLatLon.lat >= 0 ? '+' : ''}{cursorLatLon.lat.toFixed(2)}° / {cursorLatLon.lon >= 0 ? '+' : ''}{cursorLatLon.lon.toFixed(2)}°
            </span>
            <span className="text-[9px] text-gray-600">
              {cursorLatLon.lat >= 0 ? 'N' : 'S'} {Math.abs(cursorLatLon.lat).toFixed(2)}° · {cursorLatLon.lon >= 0 ? 'E' : 'W'} {Math.abs(cursorLatLon.lon).toFixed(2)}°
            </span>
          </>
        ) : (
          <span className="text-[10px] text-gray-600">
            {viewMode === 'globe' ? 'Scroll to zoom · Drag to rotate · Click to explore' : 'Move cursor to read coordinates · Click to explore'}
          </span>
        )}
      </div>

      {/* ISS status badge */}
      {showISS && issPosition && (
        <div className="absolute bottom-4 left-4 z-10 bg-black/60 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-yellow-500/20 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
          <span className="text-[9px] font-mono text-yellow-400">ISS</span>
          <span className="text-[9px] text-gray-500 font-mono">
            {Math.abs(issPosition.lat).toFixed(1)}°{issPosition.lat>=0?'N':'S'} {Math.abs(issPosition.lon).toFixed(1)}°{issPosition.lon>=0?'E':'W'}
          </span>
        </div>
      )}

      {/* Overlaid panels */}
      <AnimatePresence>
        {articleToPreview && (
          <ArticlePreviewPanel
            key={`article-${articleToPreview}`}
            title={articleToPreview}
            onClose={closePanel}
            onBack={prevLocation.current ? () => { setArticleToPreview(null); setLocationClick(prevLocation.current); } : undefined}
          />
        )}
        {locationClick && !articleToPreview && (
          <LocationInfoPanel
            key={`loc-${locationClick.lat}-${locationClick.lon}`}
            latLon={locationClick}
            onClose={closePanel}
            onArticle={(title) => setArticleToPreview(title)}
          />
        )}
      </AnimatePresence>

      {viewMode === 'globe' ? (
        <Canvas camera={{ position: [0,0,6.5], fov: 45 }} gl={{ antialias: true, alpha: true }}>
          <Suspense fallback={<GlobeLoader />}>
            <EarthGlobe
              markers={filteredMarkers}
              onMarkerClick={handleMarkerClick}
              onCursorMove={setCursorLatLon}
              onGlobeClick={handleGlobeClick}
              earthquakes={earthquakes}
              issPosition={issPosition}
              issTrail={issTrail}
              showQuakes={showQuakes}
              showISS={showISS}
              showDayNight={showDayNight}
            />
          </Suspense>
        </Canvas>
      ) : (
        <FlatMapView
          markers={filteredMarkers}
          issPosition={issPosition}
          issTrail={issTrail}
          earthquakes={earthquakes}
          showISS={showISS}
          showQuakes={showQuakes}
          onMarkerClick={handleMarkerClick}
          onMapClick={handleGlobeClick}
          onCursorMove={setCursorLatLon}
        />
      )}
    </div>
  );
};
