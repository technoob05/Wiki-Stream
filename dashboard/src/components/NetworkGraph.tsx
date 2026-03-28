import { useRef, useMemo, useEffect, useState, useCallback } from 'react';
import { ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

interface NetworkGraphProps {
  threats: any[];
  onNodeClick?: (user: string, title: string) => void;
}

interface Node {
  id: string;
  type: 'user' | 'article';
  label: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  action?: string;
  score?: number;
  connections: number;
}

interface Edge {
  source: string;
  target: string;
  action: string;
  score: number;
}

const actionColor: Record<string, string> = {
  BLOCK: '#ef4444',
  FLAG: '#f97316',
  REVIEW: '#facc15',
  SAFE: '#22c55e',
};

export const NetworkGraph: React.FC<NetworkGraphProps> = ({ threats, onNodeClick }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [hoveredNode, setHoveredNode] = useState<Node | null>(null);
  const [dragging, setDragging] = useState(false);
  const nodesRef = useRef<Node[]>([]);
  const edgesRef = useRef<Edge[]>([]);
  const animRef = useRef<number>(0);

  // Build graph data
  const { nodes: initialNodes, edges } = useMemo(() => {
    const nodeMap = new Map<string, Node>();
    const edgeList: Edge[] = [];

    // Take top threats for visualization
    const subset = threats.slice(0, 80);

    subset.forEach(t => {
      const userId = `user:${t.user}`;
      const artId = `art:${t.title}`;

      if (!nodeMap.has(userId)) {
        nodeMap.set(userId, {
          id: userId, type: 'user', label: t.user,
          x: Math.random() * 600 + 100, y: Math.random() * 400 + 50,
          vx: 0, vy: 0, connections: 0,
        });
      }
      if (!nodeMap.has(artId)) {
        nodeMap.set(artId, {
          id: artId, type: 'article', label: t.title,
          x: Math.random() * 600 + 100, y: Math.random() * 400 + 50,
          vx: 0, vy: 0, action: t.action, score: t.score, connections: 0,
        });
      }

      nodeMap.get(userId)!.connections++;
      nodeMap.get(artId)!.connections++;

      edgeList.push({ source: userId, target: artId, action: t.action, score: t.score });
    });

    return { nodes: Array.from(nodeMap.values()), edges: edgeList };
  }, [threats]);

  useEffect(() => {
    nodesRef.current = initialNodes.map(n => ({ ...n }));
    edgesRef.current = edges;
  }, [initialNodes, edges]);

  // Force-directed simulation
  useEffect(() => {
    const simulate = () => {
      const nodes = nodesRef.current;
      const edges = edgesRef.current;
      if (!nodes.length) return;

      const nodeMap = new Map(nodes.map(n => [n.id, n]));

      // Repulsion
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j];
          const dx = b.x - a.x, dy = b.y - a.y;
          const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
          const force = 800 / (dist * dist);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          a.vx -= fx; a.vy -= fy;
          b.vx += fx; b.vy += fy;
        }
      }

      // Attraction (edges)
      edges.forEach(e => {
        const a = nodeMap.get(e.source);
        const b = nodeMap.get(e.target);
        if (!a || !b) return;
        const dx = b.x - a.x, dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const force = (dist - 100) * 0.01;
        const fx = (dx / Math.max(dist, 1)) * force;
        const fy = (dy / Math.max(dist, 1)) * force;
        a.vx += fx; a.vy += fy;
        b.vx -= fx; b.vy -= fy;
      });

      // Center gravity
      const cx = 400, cy = 250;
      nodes.forEach(n => {
        n.vx += (cx - n.x) * 0.001;
        n.vy += (cy - n.y) * 0.001;
        n.vx *= 0.9;
        n.vy *= 0.9;
        n.x += n.vx;
        n.y += n.vy;
      });

      // Draw
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);
      ctx.save();
      ctx.translate(pan.x + w / 2, pan.y + h / 2);
      ctx.scale(zoom, zoom);
      ctx.translate(-w / 2, -h / 2);

      // Draw edges
      edges.forEach(e => {
        const a = nodeMap.get(e.source);
        const b = nodeMap.get(e.target);
        if (!a || !b) return;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = actionColor[e.action] || '#333';
        ctx.globalAlpha = 0.15;
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.globalAlpha = 1;
      });

      // Draw nodes
      nodes.forEach(n => {
        const radius = n.type === 'user'
          ? 4 + Math.min(n.connections * 2, 10)
          : 3 + Math.min(n.connections, 6);

        ctx.beginPath();
        ctx.arc(n.x, n.y, radius, 0, Math.PI * 2);

        if (n.type === 'user') {
          ctx.fillStyle = '#3b82f6';
          ctx.globalAlpha = 0.8;
        } else {
          ctx.fillStyle = actionColor[n.action || 'SAFE'] || '#22c55e';
          ctx.globalAlpha = 0.7;
        }
        ctx.fill();
        ctx.globalAlpha = 1;

        // Glow for high-score
        if (n.score && n.score > 60) {
          ctx.beginPath();
          ctx.arc(n.x, n.y, radius + 4, 0, Math.PI * 2);
          ctx.strokeStyle = actionColor[n.action || 'SAFE'] || '#ef4444';
          ctx.globalAlpha = 0.3;
          ctx.lineWidth = 2;
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      });

      ctx.restore();
      animRef.current = requestAnimationFrame(simulate);
    };

    animRef.current = requestAnimationFrame(simulate);
    return () => cancelAnimationFrame(animRef.current);
  }, [zoom, pan]);

  // Mouse events
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left - pan.x - canvas.width / 2) / zoom + canvas.width / 2;
    const my = (e.clientY - rect.top - pan.y - canvas.height / 2) / zoom + canvas.height / 2;

    if (dragging) {
      setPan(p => ({ x: p.x + e.movementX, y: p.y + e.movementY }));
      return;
    }

    let found: Node | null = null;
    for (const n of nodesRef.current) {
      const dx = n.x - mx, dy = n.y - my;
      const r = n.type === 'user' ? 14 : 10;
      if (dx * dx + dy * dy < r * r) { found = n; break; }
    }
    setHoveredNode(found);
    canvas.style.cursor = found ? 'pointer' : dragging ? 'grabbing' : 'grab';
  }, [zoom, pan, dragging]);

  const handleClick = useCallback(() => {
    if (hoveredNode && onNodeClick) {
      if (hoveredNode.type === 'article') {
        const threat = threats.find((t: any) => t.title === hoveredNode.label);
        if (threat) onNodeClick(threat.user, threat.title);
      }
    }
  }, [hoveredNode, onNodeClick, threats]);

  // Resize
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const resize = () => {
      const parent = canvas.parentElement;
      if (parent) {
        canvas.width = parent.clientWidth;
        canvas.height = parent.clientHeight;
      }
    };
    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  return (
    <div className="relative w-full h-full">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        onMouseMove={handleMouseMove}
        onMouseDown={() => setDragging(true)}
        onMouseUp={() => setDragging(false)}
        onMouseLeave={() => setDragging(false)}
        onClick={handleClick}
      />

      {/* Controls */}
      <div className="absolute top-4 right-4 flex flex-col gap-1">
        <button onClick={() => setZoom(z => Math.min(z * 1.3, 4))} className="p-1.5 bg-black/60 hover:bg-white/10 rounded-lg border border-white/10 transition-colors">
          <ZoomIn size={14} className="text-gray-400" />
        </button>
        <button onClick={() => setZoom(z => Math.max(z / 1.3, 0.3))} className="p-1.5 bg-black/60 hover:bg-white/10 rounded-lg border border-white/10 transition-colors">
          <ZoomOut size={14} className="text-gray-400" />
        </button>
        <button onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }} className="p-1.5 bg-black/60 hover:bg-white/10 rounded-lg border border-white/10 transition-colors">
          <RotateCcw size={14} className="text-gray-400" />
        </button>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-black/60 backdrop-blur-sm rounded-lg border border-white/10 px-3 py-2 space-y-1">
        <div className="text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1">Network Legend</div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-blue-500" />
          <span className="text-[10px] text-gray-400">User</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <span className="text-[10px] text-gray-400">BLOCK</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-orange-500" />
          <span className="text-[10px] text-gray-400">FLAG</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-[10px] text-gray-400">SAFE</span>
        </div>
        <div className="text-[9px] text-gray-600 mt-1">Drag to pan, scroll to zoom</div>
      </div>

      {/* Hover tooltip */}
      {hoveredNode && (
        <div className="absolute top-4 left-4 bg-black/90 border border-white/10 rounded-lg px-3 py-2 pointer-events-none">
          <div className="text-[10px] text-gray-500 uppercase tracking-widest">{hoveredNode.type}</div>
          <div className="text-sm text-white font-bold truncate max-w-[200px]">{hoveredNode.label}</div>
          <div className="text-[10px] text-gray-400">{hoveredNode.connections} connections</div>
          {hoveredNode.score != null && (
            <div className="text-[10px] font-mono" style={{ color: actionColor[hoveredNode.action || 'SAFE'] }}>
              {hoveredNode.action} — {hoveredNode.score.toFixed(1)}%
            </div>
          )}
        </div>
      )}

      {/* Stats */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-black/60 backdrop-blur-sm rounded-lg border border-white/10 px-4 py-2 flex gap-6">
        <div className="text-center">
          <div className="text-[9px] text-gray-500 uppercase">Users</div>
          <div className="text-sm text-blue-400 font-mono font-bold">
            {nodesRef.current.filter(n => n.type === 'user').length}
          </div>
        </div>
        <div className="text-center">
          <div className="text-[9px] text-gray-500 uppercase">Articles</div>
          <div className="text-sm text-cyan-400 font-mono font-bold">
            {nodesRef.current.filter(n => n.type === 'article').length}
          </div>
        </div>
        <div className="text-center">
          <div className="text-[9px] text-gray-500 uppercase">Edges</div>
          <div className="text-sm text-gray-400 font-mono font-bold">{edgesRef.current.length}</div>
        </div>
      </div>
    </div>
  );
};
