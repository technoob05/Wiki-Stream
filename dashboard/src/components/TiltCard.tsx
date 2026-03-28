import { useRef, useState } from 'react';

interface TiltCardProps {
  children: React.ReactNode;
  className?: string;
  intensity?: number;
  glare?: boolean;
}

export const TiltCard: React.FC<TiltCardProps> = ({ children, className = '', intensity = 10, glare = true }) => {
  const ref = useRef<HTMLDivElement>(null);
  const [style, setStyle] = useState<React.CSSProperties>({});
  const [glareStyle, setGlareStyle] = useState<React.CSSProperties>({ opacity: 0 });

  const handleMove = (e: React.MouseEvent) => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    const rotateX = (y - 0.5) * -intensity;
    const rotateY = (x - 0.5) * intensity;

    setStyle({
      transform: `perspective(600px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`,
      transition: 'transform 0.1s ease-out',
    });

    if (glare) {
      const angle = Math.atan2(y - 0.5, x - 0.5) * (180 / Math.PI) + 90;
      setGlareStyle({
        opacity: 0.1,
        background: `linear-gradient(${angle}deg, rgba(255,255,255,0.15), transparent 60%)`,
      });
    }
  };

  const handleLeave = () => {
    setStyle({ transform: 'perspective(600px) rotateX(0) rotateY(0) scale3d(1,1,1)', transition: 'transform 0.4s ease-out' });
    setGlareStyle({ opacity: 0 });
  };

  return (
    <div
      ref={ref}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      className={`relative overflow-hidden ${className}`}
      style={style}
    >
      {children}
      {glare && <div className="absolute inset-0 pointer-events-none rounded-inherit" style={glareStyle} />}
    </div>
  );
};
