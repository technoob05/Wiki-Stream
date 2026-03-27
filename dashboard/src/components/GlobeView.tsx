import { useRef, useState, useEffect, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sphere, MeshDistortMaterial, Stars, Html, OrbitControls } from '@react-three/drei';
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

const ThreatMarker = ({ marker, radius, onClick }: { marker: GeoMarker; radius: number; onClick?: (marker: GeoMarker) => void }) => {
  const pos = useMemo(() => latLonToVec3(marker.lat, marker.lon, radius), [marker, radius]);
  const beamEnd = useMemo(() => latLonToVec3(marker.lat, marker.lon, radius + 0.6), [marker, radius]);
  const ref = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  useFrame((state) => {
    if (ref.current) {
      // Pulse effect
      const scale = 1 + Math.sin(state.clock.elapsedTime * 3 + marker.lat) * 0.3;
      ref.current.scale.setScalar(scale);
    }
  });

  const color = marker.action === 'BLOCK' ? '#ef4444' : marker.action === 'FLAG' ? '#f97316' : '#facc15';

  return (
    <group>
      {/* Marker dot */}
      <mesh ref={ref} position={pos}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
        onClick={() => onClick?.(marker)}
      >
        <sphereGeometry args={[0.06, 8, 8]} />
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
        <lineBasicMaterial color={color} transparent opacity={0.4} />
      </line>

      {/* Glow ring */}
      <mesh position={pos} rotation={[Math.random() * Math.PI, Math.random() * Math.PI, 0]}>
        <ringGeometry args={[0.08, 0.12, 16]} />
        <meshBasicMaterial color={color} transparent opacity={0.3} side={THREE.DoubleSide} />
      </mesh>

      {/* Tooltip on hover */}
      {hovered && (
        <Html position={beamEnd} center>
          <div className="bg-black/90 border border-white/20 rounded-lg px-3 py-2 text-xs whitespace-nowrap pointer-events-none">
            <div className={`font-bold ${marker.action === 'BLOCK' ? 'text-red-400' : marker.action === 'FLAG' ? 'text-orange-400' : 'text-yellow-400'}`}>
              {marker.action} — {marker.score.toFixed(1)}%
            </div>
            <div className="text-white">{marker.title.slice(0, 35)}</div>
            <div className="text-gray-400">{marker.user} · {marker.region}</div>
          </div>
        </Html>
      )}
    </group>
  );
};

const Globe = ({ markers, onMarkerClick }: { markers: GeoMarker[]; onMarkerClick?: (m: GeoMarker) => void }) => {
  const meshRef = useRef<THREE.Group>(null);
  const isDragging = useRef(false);

  useFrame(() => {
    if (meshRef.current && !isDragging.current) {
      meshRef.current.rotation.y += 0.001;
    }
  });

  return (
    <>
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1.5} color="#00f0ff" />
      <Stars radius={100} depth={50} count={3000} factor={4} saturation={0} fade speed={1} />

      <group ref={meshRef}>
        {/* Wireframe globe */}
        <mesh>
          <sphereGeometry args={[2.5, 64, 64]} />
          <meshPhongMaterial
            color="#0a0a0c"
            emissive="#00f0ff"
            emissiveIntensity={0.1}
            wireframe
            transparent
            opacity={0.25}
          />
        </mesh>

        {/* Internal core */}
        <Sphere args={[2.4, 32, 32]}>
          <meshBasicMaterial color="#001820" transparent opacity={0.6} />
        </Sphere>

        {/* Threat markers on globe surface */}
        {markers.map((m, i) => (
          <ThreatMarker key={`${m.user}-${i}`} marker={m} radius={2.5} onClick={onMarkerClick} />
        ))}
      </group>

      {/* Distorted energy overlay */}
      <mesh rotation={[0, 0, Math.PI / 4]}>
        <sphereGeometry args={[2.6, 64, 64]} />
        <MeshDistortMaterial
          color="#00f0ff"
          speed={3}
          distort={0.15}
          transparent
          opacity={0.04}
        />
      </mesh>

      <OrbitControls
        enableZoom={false}
        enablePan={false}
        onStart={() => { isDragging.current = true; }}
        onEnd={() => { isDragging.current = false; }}
      />
    </>
  );
};

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

      {/* Threat Radar label — click to toggle legend */}
      <div
        className="absolute top-4 left-4 z-10 bg-black/40 backdrop-blur-md px-4 py-3 rounded-lg border border-white/10 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={() => setLegendOpen(!legendOpen)}
      >
        <h3 className="text-sm font-mono text-cyan-400 uppercase tracking-widest font-bold">Threat Radar</h3>
        <p className="text-xs text-gray-400 mt-0.5">
          {markers.length > 0
            ? `${markers.length} threats across ${regions.length} regions`
            : 'Scanning...'}
        </p>
      </div>

      {/* Legend popup — shows on click */}
      {legendOpen && markers.length > 0 && (
        <div className="absolute top-20 left-4 z-10 bg-black/80 backdrop-blur-md px-4 py-3 rounded-lg border border-white/10 space-y-2 min-w-[180px]">
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
          <div className="border-t border-white/10 pt-2 mt-2">
            <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-1">Regions</div>
            {regions.map((r, i) => (
              <div key={i} className="text-[10px] text-gray-400">{r} ({markers.filter(m => m.region === r).length})</div>
            ))}
          </div>
        </div>
      )}

      <Canvas camera={{ position: [0, 0, 7], fov: 50 }}>
        <Globe markers={filteredMarkers} onMarkerClick={onThreatClick ? (m) => onThreatClick(m.user, m.title) : undefined} />
      </Canvas>
    </div>
  );
};
