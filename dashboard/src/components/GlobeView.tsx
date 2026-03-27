import { useRef, useState, useEffect, useMemo, useCallback } from 'react';
import { Canvas, useFrame, useLoader, useThree } from '@react-three/fiber';
import { Stars, Html, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

interface GeoMarker {
  lat: number;
  lon: number;
  user: string;
  title: string;
  action: string;
  score: number;
  region: string;
}

// Convert lat/lon to 3D position on sphere
const latLonToVec3 = (lat: number, lon: number, radius: number): [number, number, number] => {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return [
    -(radius * Math.sin(phi) * Math.cos(theta)),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  ];
};

// ── Generate Earth Texture Procedurally ──
// Draws simplified continent outlines on a canvas texture
const createEarthTexture = (): THREE.CanvasTexture => {
  const w = 2048, h = 1024;
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d')!;

  // Ocean background — dark blue-black
  ctx.fillStyle = '#080d14';
  ctx.fillRect(0, 0, w, h);

  // Grid lines
  ctx.strokeStyle = 'rgba(6, 182, 212, 0.06)';
  ctx.lineWidth = 0.5;
  for (let lat = -80; lat <= 80; lat += 20) {
    const y = (90 - lat) / 180 * h;
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
  }
  for (let lon = -180; lon <= 180; lon += 30) {
    const x = (lon + 180) / 360 * w;
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
  }

  // Helper: draw polygon from lat/lon coords
  const drawLand = (coords: [number, number][], fill: string, stroke: string) => {
    ctx.beginPath();
    coords.forEach(([lon, lat], i) => {
      const x = (lon + 180) / 360 * w;
      const y = (90 - lat) / 180 * h;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 1;
    ctx.stroke();
  };

  const landFill = 'rgba(6, 182, 212, 0.08)';
  const landStroke = 'rgba(6, 182, 212, 0.25)';

  // Simplified continent outlines (major landmasses)
  // North America
  drawLand([
    [-130, 55], [-125, 60], [-110, 65], [-95, 70], [-80, 72], [-65, 65],
    [-55, 50], [-65, 45], [-70, 42], [-75, 35], [-80, 30], [-85, 25],
    [-90, 20], [-100, 18], [-105, 22], [-110, 30], [-115, 33], [-120, 37],
    [-125, 42], [-125, 48], [-130, 55],
  ], landFill, landStroke);

  // Central America + Mexico
  drawLand([
    [-100, 18], [-95, 18], [-90, 15], [-85, 12], [-80, 8], [-78, 8],
    [-80, 10], [-85, 15], [-90, 20], [-100, 18],
  ], landFill, landStroke);

  // South America
  drawLand([
    [-80, 10], [-75, 10], [-60, 5], [-50, 0], [-45, -3], [-35, -5],
    [-35, -10], [-37, -15], [-40, -22], [-48, -28], [-55, -33], [-58, -38],
    [-65, -42], [-68, -48], [-70, -55], [-73, -50], [-72, -42], [-70, -35],
    [-70, -25], [-75, -15], [-78, -5], [-80, 0], [-80, 10],
  ], landFill, landStroke);

  // Europe
  drawLand([
    [-10, 37], [-5, 36], [0, 38], [5, 43], [3, 47], [-2, 48], [-5, 48],
    [-8, 43], [0, 50], [5, 52], [10, 54], [15, 55], [20, 55], [25, 58],
    [30, 60], [30, 70], [25, 70], [18, 68], [10, 63], [5, 58], [0, 52],
    [-5, 50], [-10, 44], [-10, 37],
  ], landFill, landStroke);

  // Africa
  drawLand([
    [-15, 30], [-5, 35], [10, 37], [15, 33], [25, 32], [32, 30],
    [35, 28], [40, 12], [50, 10], [45, 0], [42, -5], [40, -12],
    [35, -22], [30, -30], [28, -33], [20, -35], [15, -28], [12, -18],
    [10, -5], [8, 5], [0, 5], [-5, 5], [-10, 8], [-17, 12],
    [-17, 18], [-15, 22], [-15, 30],
  ], landFill, landStroke);

  // Asia (simplified)
  drawLand([
    [30, 60], [40, 55], [50, 45], [55, 40], [60, 38], [65, 35],
    [70, 25], [75, 15], [80, 10], [78, 20], [80, 28], [90, 25],
    [88, 22], [95, 18], [100, 15], [105, 10], [110, 20], [115, 22],
    [120, 25], [125, 30], [130, 35], [135, 35], [140, 38], [142, 45],
    [135, 50], [130, 48], [120, 52], [110, 50], [100, 52], [90, 55],
    [80, 58], [70, 60], [60, 65], [50, 65], [40, 62], [30, 60],
  ], landFill, landStroke);

  // India
  drawLand([
    [68, 30], [70, 25], [72, 20], [76, 12], [78, 8], [80, 12],
    [82, 15], [85, 20], [88, 22], [88, 25], [85, 28], [78, 30],
    [72, 32], [68, 30],
  ], landFill, landStroke);

  // Southeast Asia
  drawLand([
    [100, 22], [105, 18], [108, 14], [108, 10], [105, 5], [102, 2],
    [100, 5], [98, 10], [98, 15], [100, 22],
  ], landFill, landStroke);

  // Japan
  drawLand([
    [130, 31], [132, 33], [135, 35], [137, 37], [140, 40], [142, 43],
    [145, 44], [145, 42], [142, 38], [138, 35], [134, 33], [130, 31],
  ], landFill, landStroke);

  // Australia
  drawLand([
    [115, -20], [120, -15], [130, -12], [140, -12], [148, -15],
    [152, -22], [153, -28], [150, -33], [145, -38], [138, -35],
    [135, -33], [130, -30], [120, -33], [115, -30], [113, -25],
    [115, -20],
  ], landFill, landStroke);

  // Indonesia (simplified)
  drawLand([
    [95, 5], [100, 2], [105, -2], [110, -5], [115, -8], [120, -8],
    [125, -5], [130, -3], [135, -5], [140, -6], [140, -3], [135, 0],
    [128, 0], [120, -2], [115, -5], [110, 0], [105, 3], [100, 5], [95, 5],
  ], landFill, landStroke);

  // Greenland
  drawLand([
    [-55, 60], [-45, 60], [-20, 65], [-18, 72], [-20, 78], [-30, 82],
    [-45, 82], [-55, 78], [-58, 72], [-55, 65], [-55, 60],
  ], landFill, landStroke);

  // UK/Ireland
  drawLand([[-8, 50], [-5, 52], [-3, 55], [-2, 58], [0, 58], [2, 55], [2, 52], [0, 50], [-5, 50], [-8, 50]], landFill, landStroke);
  drawLand([[-10, 52], [-8, 54], [-6, 54], [-6, 52], [-10, 52]], landFill, landStroke);

  // New Zealand
  drawLand([[168, -35], [173, -37], [178, -42], [175, -46], [170, -45], [168, -42], [168, -35]], landFill, landStroke);

  // Add a subtle glow along coastlines
  ctx.shadowColor = 'rgba(6, 182, 212, 0.3)';
  ctx.shadowBlur = 8;

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
};

// ── Threat Marker Component ──
const ThreatMarker = ({ marker, radius, onClick }: { marker: GeoMarker; radius: number; onClick?: (marker: GeoMarker) => void }) => {
  const pos = useMemo(() => latLonToVec3(marker.lat, marker.lon, radius + 0.02), [marker, radius]);
  const beamEnd = useMemo(() => latLonToVec3(marker.lat, marker.lon, radius + 0.5), [marker, radius]);
  const ref = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  useFrame((state) => {
    if (ref.current) {
      const scale = 1 + Math.sin(state.clock.elapsedTime * 3 + marker.lat) * 0.3;
      ref.current.scale.setScalar(scale);
    }
    if (ringRef.current) {
      const s = 1 + Math.sin(state.clock.elapsedTime * 2 + marker.lon) * 0.5;
      ringRef.current.scale.setScalar(s);
      (ringRef.current.material as THREE.MeshBasicMaterial).opacity = 0.3 - s * 0.1;
    }
  });

  const color = marker.action === 'BLOCK' ? '#ef4444' : marker.action === 'FLAG' ? '#f97316' : '#facc15';

  // Calculate normal direction for ring orientation
  const normal = useMemo(() => {
    const v = new THREE.Vector3(...pos).normalize();
    return v;
  }, [pos]);

  const lookAt = useMemo(() => {
    const q = new THREE.Quaternion();
    q.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
    const e = new THREE.Euler().setFromQuaternion(q);
    return [e.x, e.y, e.z] as [number, number, number];
  }, [normal]);

  return (
    <group>
      {/* Marker dot */}
      <mesh ref={ref} position={pos}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
        onClick={() => onClick?.(marker)}
      >
        <sphereGeometry args={[0.04, 8, 8]} />
        <meshBasicMaterial color={color} />
      </mesh>

      {/* Beam line from surface */}
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[new Float32Array([...pos, ...beamEnd]), 3]}
          />
        </bufferGeometry>
        <lineBasicMaterial color={color} transparent opacity={0.3} />
      </line>

      {/* Pulsing ring on surface */}
      <mesh ref={ringRef} position={pos} rotation={lookAt}>
        <ringGeometry args={[0.06, 0.1, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.3} side={THREE.DoubleSide} />
      </mesh>

      {/* Outer glow sphere */}
      {marker.action === 'BLOCK' && (
        <mesh position={pos}>
          <sphereGeometry args={[0.12, 12, 12]} />
          <meshBasicMaterial color={color} transparent opacity={0.08} />
        </mesh>
      )}

      {/* Tooltip on hover */}
      {hovered && (
        <Html position={beamEnd} center>
          <div className="bg-black/95 border border-white/20 rounded-lg px-3 py-2 text-xs whitespace-nowrap pointer-events-none shadow-xl backdrop-blur-sm">
            <div className={`font-bold ${marker.action === 'BLOCK' ? 'text-red-400' : marker.action === 'FLAG' ? 'text-orange-400' : 'text-yellow-400'}`}>
              {marker.action} — {marker.score.toFixed(1)}%
            </div>
            <div className="text-white font-medium">{marker.title.slice(0, 40)}{marker.title.length > 40 ? '...' : ''}</div>
            <div className="text-gray-400">{marker.user} · {marker.region}</div>
          </div>
        </Html>
      )}
    </group>
  );
};

// ── Arc connections between threats from same user ──
const ThreatArcs = ({ markers, radius }: { markers: GeoMarker[]; radius: number }) => {
  const arcs = useMemo(() => {
    const userEdits: Record<string, GeoMarker[]> = {};
    markers.forEach(m => {
      if (!userEdits[m.user]) userEdits[m.user] = [];
      userEdits[m.user].push(m);
    });

    const result: { start: [number, number, number]; end: [number, number, number]; color: string }[] = [];
    Object.values(userEdits).forEach(edits => {
      if (edits.length < 2) return;
      for (let i = 0; i < edits.length - 1 && i < 3; i++) {
        result.push({
          start: latLonToVec3(edits[i].lat, edits[i].lon, radius + 0.02),
          end: latLonToVec3(edits[i + 1].lat, edits[i + 1].lon, radius + 0.02),
          color: '#06b6d4',
        });
      }
    });
    return result.slice(0, 30); // Limit for performance
  }, [markers, radius]);

  return (
    <>
      {arcs.map((arc, i) => {
        // Create curved arc via midpoint elevated above surface
        const mid = new THREE.Vector3(
          (arc.start[0] + arc.end[0]) / 2,
          (arc.start[1] + arc.end[1]) / 2,
          (arc.start[2] + arc.end[2]) / 2,
        );
        mid.normalize().multiplyScalar(radius + 0.8);

        const curve = new THREE.QuadraticBezierCurve3(
          new THREE.Vector3(...arc.start),
          mid,
          new THREE.Vector3(...arc.end),
        );
        const points = curve.getPoints(20);
        const geometry = new THREE.BufferGeometry().setFromPoints(points);

        return (
          <line key={i}>
            <primitive object={geometry} attach="geometry" />
            <lineBasicMaterial color={arc.color} transparent opacity={0.15} />
          </line>
        );
      })}
    </>
  );
};

// ── Globe Component ──
const Globe = ({ markers, onMarkerClick }: { markers: GeoMarker[]; onMarkerClick?: (m: GeoMarker) => void }) => {
  const meshRef = useRef<THREE.Group>(null);
  const isDragging = useRef(false);
  const earthTexture = useMemo(() => createEarthTexture(), []);
  const RADIUS = 2.5;

  useFrame(() => {
    if (meshRef.current && !isDragging.current) {
      meshRef.current.rotation.y += 0.0008;
    }
  });

  return (
    <>
      <ambientLight intensity={0.3} />
      <directionalLight position={[5, 3, 5]} intensity={1.2} color="#e0f0ff" />
      <pointLight position={[-8, -5, -8]} intensity={0.4} color="#06b6d4" />
      <Stars radius={100} depth={50} count={5000} factor={3} saturation={0} fade speed={0.5} />

      <group ref={meshRef}>
        {/* Earth sphere with texture */}
        <mesh>
          <sphereGeometry args={[RADIUS, 96, 96]} />
          <meshStandardMaterial
            map={earthTexture}
            roughness={0.9}
            metalness={0.1}
          />
        </mesh>

        {/* Atmosphere glow — outer shell */}
        <mesh>
          <sphereGeometry args={[RADIUS + 0.05, 64, 64]} />
          <meshBasicMaterial
            color="#06b6d4"
            transparent
            opacity={0.04}
            side={THREE.BackSide}
          />
        </mesh>

        {/* Second atmosphere layer */}
        <mesh>
          <sphereGeometry args={[RADIUS + 0.15, 48, 48]} />
          <meshBasicMaterial
            color="#06b6d4"
            transparent
            opacity={0.02}
            side={THREE.BackSide}
          />
        </mesh>

        {/* Threat markers */}
        {markers.map((m, i) => (
          <ThreatMarker key={`${m.user}-${m.title}-${i}`} marker={m} radius={RADIUS} onClick={onMarkerClick} />
        ))}

        {/* Arc connections */}
        <ThreatArcs markers={markers} radius={RADIUS} />
      </group>

      <OrbitControls
        enableZoom={true}
        enablePan={false}
        minDistance={4}
        maxDistance={12}
        zoomSpeed={0.5}
        onStart={() => { isDragging.current = true; }}
        onEnd={() => { isDragging.current = false; }}
      />
    </>
  );
};

// ── GlobeView Wrapper ──
export const GlobeView: React.FC<{ onThreatClick?: (user: string, title: string) => void; safeCount?: number }> = ({ onThreatClick, safeCount: safeProp }) => {
  const [markers, setMarkers] = useState<GeoMarker[]>([]);
  const [legendOpen, setLegendOpen] = useState(false);
  const [showBlock, setShowBlock] = useState(true);
  const [showFlag, setShowFlag] = useState(true);
  const [showReview, setShowReview] = useState(false);

  useEffect(() => {
    const fetchGeo = () => {
      axios.get(`${API_BASE}/geo/threats`)
        .then(res => setMarkers(res.data.markers || []))
        .catch(() => {});
    };
    fetchGeo();
    const interval = setInterval(fetchGeo, 10000);
    return () => clearInterval(interval);
  }, []);

  const blockCount = markers.filter(m => m.action === 'BLOCK').length;
  const flagCount = markers.filter(m => m.action === 'FLAG').length;
  const reviewCount = markers.filter(m => m.action === 'REVIEW').length;
  const safeCount = safeProp ?? 0;
  const regions = [...new Set(markers.map(m => m.region))];
  const filteredMarkers = markers.filter(m =>
    (m.action === 'BLOCK' && showBlock) || (m.action === 'FLAG' && showFlag) || (m.action === 'REVIEW' && showReview)
  );

  return (
    <div className="w-full h-full min-h-[400px] relative">
      {/* Filter buttons */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 flex gap-2">
        <button
          onClick={() => setShowBlock(!showBlock)}
          className={`px-3 py-1.5 rounded-lg text-[10px] font-bold border transition-all ${
            showBlock ? 'bg-red-500/20 text-red-400 border-red-500/40' : 'bg-white/5 text-gray-600 border-white/10'
          }`}
        >
          BLOCK ({blockCount})
        </button>
        <button
          onClick={() => setShowFlag(!showFlag)}
          className={`px-3 py-1.5 rounded-lg text-[10px] font-bold border transition-all ${
            showFlag ? 'bg-orange-500/20 text-orange-400 border-orange-500/40' : 'bg-white/5 text-gray-600 border-white/10'
          }`}
        >
          FLAG ({flagCount})
        </button>
        <button
          onClick={() => setShowReview(!showReview)}
          className={`px-3 py-1.5 rounded-lg text-[10px] font-bold border transition-all ${
            showReview ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40' : 'bg-white/5 text-gray-600 border-white/10'
          }`}
        >
          REVIEW ({reviewCount})
        </button>
        <div className="px-3 py-1.5 rounded-lg text-[10px] font-bold border bg-green-500/20 text-green-400 border-green-500/40">
          SAFE ({markers.length > 0 ? safeCount : 0})
        </div>
      </div>

      {/* Threat Radar label */}
      <div
        className="absolute top-4 left-4 z-10 bg-black/60 backdrop-blur-md px-4 py-3 rounded-lg border border-white/10 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={() => setLegendOpen(!legendOpen)}
      >
        <h3 className="text-sm font-mono text-cyan-400 uppercase tracking-widest font-bold">Threat Radar</h3>
        <p className="text-xs text-gray-400 mt-0.5">
          {markers.length > 0
            ? `${filteredMarkers.length} threats across ${regions.length} regions`
            : 'Scanning...'}
        </p>
      </div>

      {/* Legend popup */}
      {legendOpen && markers.length > 0 && (
        <div className="absolute top-20 left-4 z-10 bg-black/90 backdrop-blur-md px-4 py-3 rounded-lg border border-white/10 space-y-2 min-w-[180px]">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">Breakdown</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500" />
            <span className="text-xs text-red-400 font-bold">BLOCK</span>
            <span className="text-xs text-gray-400 ml-auto">{blockCount}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-orange-500" />
            <span className="text-xs text-orange-400 font-bold">FLAG</span>
            <span className="text-xs text-gray-400 ml-auto">{flagCount}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500" />
            <span className="text-xs text-yellow-400 font-bold">REVIEW</span>
            <span className="text-xs text-gray-400 ml-auto">{reviewCount}</span>
          </div>
          <div className="border-t border-white/10 pt-2 mt-2">
            <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-1">Regions</div>
            {regions.map((r, i) => (
              <div key={i} className="text-[10px] text-gray-400">{r} ({markers.filter(m => m.region === r).length})</div>
            ))}
          </div>
        </div>
      )}

      {/* Zoom hint */}
      <div className="absolute bottom-4 right-4 z-10 text-[10px] text-gray-600 font-mono bg-black/40 backdrop-blur-sm px-2 py-1 rounded">
        Scroll to zoom · Drag to rotate
      </div>

      <Canvas camera={{ position: [0, 0, 7], fov: 45 }} gl={{ antialias: true }}>
        <Globe markers={filteredMarkers} onMarkerClick={onThreatClick ? (m) => onThreatClick(m.user, m.title) : undefined} />
      </Canvas>
    </div>
  );
};
