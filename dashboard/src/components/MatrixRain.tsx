import { useRef, useEffect } from 'react';

export const MatrixRain: React.FC<{ className?: string }> = ({ className }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const parent = canvas.parentElement;
    if (!parent) return;

    canvas.width = parent.clientWidth;
    canvas.height = parent.clientHeight;

    const chars = 'ABCDEF0123456789ΣΩΔΛΠαβγδ₀₁₂₃⟨⟩∫∑∏√∞≈≠∈∉⊂⊃∪∩'.split('');
    const fontSize = 10;
    const columns = Math.floor(canvas.width / fontSize);
    const drops: number[] = Array(columns).fill(1).map(() => Math.random() * -50);

    let animId: number;
    const draw = () => {
      ctx.fillStyle = 'rgba(3, 7, 18, 0.15)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.font = `${fontSize}px monospace`;

      for (let i = 0; i < drops.length; i++) {
        const char = chars[Math.floor(Math.random() * chars.length)];
        const x = i * fontSize;
        const y = drops[i] * fontSize;

        // Head character — bright
        ctx.fillStyle = `rgba(6, 182, 212, ${0.6 + Math.random() * 0.4})`;
        ctx.fillText(char, x, y);

        // Trail — dimmer
        if (drops[i] > 1) {
          ctx.fillStyle = `rgba(6, 182, 212, 0.1)`;
          ctx.fillText(chars[Math.floor(Math.random() * chars.length)], x, y - fontSize);
        }

        if (y > canvas.height && Math.random() > 0.98) {
          drops[i] = 0;
        }
        drops[i] += 0.5 + Math.random() * 0.5;
      }

      animId = requestAnimationFrame(draw);
    };

    animId = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animId);
  }, []);

  return <canvas ref={canvasRef} className={`absolute inset-0 pointer-events-none opacity-30 ${className || ''}`} />;
};
