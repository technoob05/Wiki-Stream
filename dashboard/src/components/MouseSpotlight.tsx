import { useEffect, useState } from 'react';

export const MouseSpotlight: React.FC = () => {
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const move = (e: MouseEvent) => {
      setPos({ x: e.clientX, y: e.clientY });
      setVisible(true);
    };
    const leave = () => setVisible(false);
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseleave', leave);
    return () => { window.removeEventListener('mousemove', move); window.removeEventListener('mouseleave', leave); };
  }, []);

  if (!visible) return null;

  return (
    <div
      className="fixed pointer-events-none z-[9990] rounded-full mix-blend-soft-light"
      style={{
        width: 400,
        height: 400,
        left: pos.x - 200,
        top: pos.y - 200,
        background: 'radial-gradient(circle, rgba(6,182,212,0.06) 0%, transparent 70%)',
        transition: 'left 0.1s ease-out, top 0.1s ease-out',
      }}
    />
  );
};
