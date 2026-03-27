import { useRef, useState, useEffect, useMemo } from 'react';
import { Canvas, useFrame, useLoader } from '@react-three/fiber';
import { Stars, Html, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

// NASA / Natural Earth textures via CDN
const EARTH_TEXTURE = 'https://unpkg.com/three-globe@2.41.12/example/img/earth-night.jpg';
const EARTH_TOPO = 'https://unpkg.com/three-globe@2.41.12/example/img/earth-topology.png';

interface GeoMarker {
  lat: number;
  lon: number;
  user: string;
  title: string;
  action: string;
  score: number;
  region: string;
}

const latLonToVec3 = (lat: number, lon: number, radius: number): [number, number, number] => {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return [
    -(radius * Math.sin(phi) * Math.cos(theta)),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  ];
};

// ── Threat Marker ──
const ThreatMarker = ({ marker, radius, onClick }: { marker: GeoMarker; radius: number; onClick?: (marker: GeoMarker) => void }) => {
  const pos = useMemo(() => latLonToVec3(marker.lat, marker.lon, radius + 0.02), [marker, radius]);
  const beamEnd = useMemo(() => latLonToVec3(marker.lat, marker.lon, radius + 0.45), [marker, radius]);
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
      (ringRef.current.material as THREE.MeshBasicMaterial).opacity = Math.max(0, 0.4 - s * 0.12);
    }
  });

  const color = marker.action === 'BLOCK' ? '#ef4444' : marker.action === 'FLAG' ? '#f97316' : '#facc15';

  const lookAt = useMemo(() => {
    const normal = new THREE.Vector3(...pos).normalize();
    const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
    const e = new THREE.Euler().setFromQuaternion(q);
    return [e.x, e.y, e.z] as [number, number, number];
  }, [pos]);

  return (
    <group>
      {/* Marker dot */}
      <mesh ref={ref} position={pos}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
        onClick={() => onClick?.(marker)}
      >
        <sphereGeometry args={[0.035, 8, 8]} />
        <meshBasicMaterial color={color} />
      </mesh>

      {/* Beam line */}
      <line>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[new Float32Array([...pos, ...beamEnd]), 3]} />
        </bufferGeometry>
        <lineBasicMaterial color={color} transparent opacity={0.35} />
      </line>

      {/* Pulsing ring on surface */}
      <mesh ref={ringRef} position={pos} rotation={lookAt}>
        <ringGeometry args={[0.05, 0.08, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.4} side={THREE.DoubleSide} />
      </mesh>

      {/* BLOCK extra glow */}
      {marker.action === 'BLOCK' && (
        <mesh position={pos}>
          <sphereGeometry args={[0.1, 12, 12]} />
          <meshBasicMaterial color={color} transparent opacity={0.1} />
        </mesh>
      )}

      {/* Tooltip */}
      {hovered && (
        <Html position={beamEnd} center>
          <div className="bg-black/95 border border-white/20 rounded-lg px-3 py-2 text-xs whitespace-nowrap pointer-events-none shadow-xl backdrop-blur-sm">
            <div className={`font-bold ${marker.action === 'BLOCK' ? 'text-red-400' : marker.action === 'FLAG' ? 'text-orange-400' : 'text-yellow-400'}`}>
              {marker.action} — {marker.score.toFixed(1)}%
            </div>
            <div className="text-white font-medium">{marker.title.slice(0, 40)}{marker.title.length > 40 ? '…' : ''}</div>
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
    const result: { start: [number, number, number]; end: [number, number, number] }[] = [];
    Object.values(userEdits).forEach(edits => {
      if (edits.length < 2) return;
      for (let i = 0; i < edits.length - 1 && i < 3; i++) {
        result.push({
          start: latLonToVec3(edits[i].lat, edits[i].lon, radius + 0.02),
          end: latLonToVec3(edits[i + 1].lat, edits[i + 1].lon, radius + 0.02),
        });
      }
    });
    return result.slice(0, 25);
  }, [markers, radius]);

  return (
    <>
      {arcs.map((arc, i) => {
        const mid = new THREE.Vector3(
          (arc.start[0] + arc.end[0]) / 2,
          (arc.start[1] + arc.end[1]) / 2,
          (arc.start[2] + arc.end[2]) / 2,
        ).normalize().multiplyScalar(radius + 0.7);
        const curve = new THREE.QuadraticBezierCurve3(
          new THREE.Vector3(...arc.start), mid, new THREE.Vector3(...arc.end),
        );
        const geometry = new THREE.BufferGeometry().setFromPoints(curve.getPoints(20));
        return (
          <line key={i}>
            <primitive object={geometry} attach="geometry" />
            <lineBasicMaterial color="#06b6d4" transparent opacity={0.18} />
          </line>
        );
      })}
    </>
  );
};

// ── Earth Globe ──
const EarthGlobe = ({ markers, onMarkerClick }: { markers: GeoMarker[]; onMarkerClick?: (m: GeoMarker) => void }) => {
  const groupRef = useRef<THREE.Group>(null);
  const isDragging = useRef(false);
  const RADIUS = 2.5;

  // Load real NASA textures
  const earthMap = useLoader(THREE.TextureLoader, EARTH_TEXTURE);
  const topoMap = useLoader(THREE.TextureLoader, EARTH_TOPO);

  useFrame(() => {
    if (groupRef.current && !isDragging.current) {
      groupRef.current.rotation.y += 0.0006;
    }
  });

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.15} />
      <directionalLight position={[5, 3, 5]} intensity={2} color="#ffffff" />
      <pointLight position={[-10, -5, -10]} intensity={0.5} color="#06b6d4" />

      {/* Stars */}
      <Stars radius={120} depth={60} count={6000} factor={3} saturation={0} fade speed={0.4} />

      <group ref={groupRef}>
        {/* Earth sphere with NASA texture */}
        <mesh>
          <sphereGeometry args={[RADIUS, 128, 128]} />
          <meshStandardMaterial
            map={earthMap}
            bumpMap={topoMap}
            bumpScale={0.03}
            roughness={0.7}
            metalness={0.05}
            emissiveMap={earthMap}
            emissive={new THREE.Color('#ffffff')}
            emissiveIntensity={0.6}
          />
        </mesh>

        {/* Atmosphere glow - inner */}
        <mesh>
          <sphereGeometry args={[RADIUS + 0.04, 64, 64]} />
          <meshBasicMaterial color="#4dc9f6" transparent opacity={0.06} side={THREE.BackSide} />
        </mesh>

        {/* Atmosphere glow - outer */}
        <mesh>
          <sphereGeometry args={[RADIUS + 0.18, 64, 64]} />
          <meshBasicMaterial color="#06b6d4" transparent opacity={0.03} side={THREE.BackSide} />
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
        rotateSpeed={0.5}
        onStart={() => { isDragging.current = true; }}
        onEnd={() => { isDragging.current = false; }}
      />
    </>
  );
};

// ── Loading fallback ──
const GlobeLoader = () => (
  <mesh>
    <sphereGeometry args={[2.5, 32, 32]} />
    <meshBasicMaterial color="#0a1628" wireframe transparent opacity={0.3} />
  </mesh>
);

// ── Main GlobeView ──
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
    <div className="w-full h-full min-h-[400px] relative bg-[#030712]">
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
          <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">Breakdown</span>
          {[
            { label: 'BLOCK', color: 'bg-red-500', textColor: 'text-red-400', count: blockCount },
            { label: 'FLAG', color: 'bg-orange-500', textColor: 'text-orange-400', count: flagCount },
            { label: 'REVIEW', color: 'bg-yellow-500', textColor: 'text-yellow-400', count: reviewCount },
          ].map(item => (
            <div key={item.label} className="flex items-center gap-2">
              <div className={`w-2.5 h-2.5 rounded-full ${item.color}`} />
              <span className={`text-xs ${item.textColor} font-bold`}>{item.label}</span>
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

      {/* Zoom hint */}
      <div className="absolute bottom-4 right-4 z-10 text-[10px] text-gray-600 font-mono bg-black/40 backdrop-blur-sm px-2 py-1 rounded">
        Scroll to zoom · Drag to rotate
      </div>

      <Canvas camera={{ position: [0, 0, 6.5], fov: 45 }} gl={{ antialias: true, alpha: true }}>
        <Suspense fallback={<GlobeLoader />}>
          <EarthGlobe markers={filteredMarkers} onMarkerClick={onThreatClick ? (m) => onThreatClick(m.user, m.title) : undefined} />
        </Suspense>
      </Canvas>
    </div>
  );
};

// Need Suspense for useLoader
import { Suspense } from 'react';
