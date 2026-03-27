import { useState } from 'react';
import { Share2, Camera, Check, Link2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ShareButtonProps {
  data: any;
  addToast: (msg: string, type: 'info' | 'success' | 'threat') => void;
}

export const ShareButton: React.FC<ShareButtonProps> = ({ data, addToast }) => {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const shareText = () => {
    const dist = data?.distribution || {};
    const text = `Wiki-Stream Intelligence Report\n` +
      `Total: ${data?.total || 0} edits analyzed\n` +
      `BLOCK: ${dist['BLOCK'] || 0} | FLAG: ${dist['FLAG'] || 0} | REVIEW: ${dist['REVIEW'] || 0} | SAFE: ${dist['SAFE'] || 0}\n` +
      `AI Confidence: ${data?.statistics?.avg_uncertainty != null ? Math.round((1 - data.statistics.avg_uncertainty) * 100) : 'N/A'}%\n` +
      `Powered by Wiki-Stream Intelligence Dashboard`;
    return text;
  };

  const copyLink = () => {
    navigator.clipboard.writeText(shareText());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    addToast('Report summary copied to clipboard', 'success');
    setOpen(false);
  };

  const takeScreenshot = async () => {
    try {
      const main = document.querySelector('main');
      if (!main) return;
      // Use native browser screenshot prompt
      addToast('Use Ctrl+Shift+S or your OS screenshot tool to capture', 'info');
      setOpen(false);
    } catch {
      addToast('Screenshot not available', 'info');
    }
  };

  const shareNative = async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: 'Wiki-Stream Intelligence', text: shareText() });
      } catch {}
    } else {
      copyLink();
    }
    setOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-cyan-400 transition-all border border-white/5"
        title="Share"
      >
        <Share2 size={14} />
      </button>

      <AnimatePresence>
        {open && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setOpen(false)} className="fixed inset-0 z-[100]" />
            <motion.div
              initial={{ opacity: 0, y: -4, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -4, scale: 0.95 }}
              className="absolute right-0 top-full mt-2 w-[200px] bg-[#0f0f13] border border-white/10 rounded-xl shadow-2xl py-1.5 z-[101]"
            >
              <button onClick={copyLink} className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-gray-400 hover:bg-white/5 hover:text-white transition-colors">
                {copied ? <Check size={13} className="text-green-400" /> : <Link2 size={13} />}
                {copied ? 'Copied!' : 'Copy Summary'}
              </button>
              <button onClick={takeScreenshot} className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-gray-400 hover:bg-white/5 hover:text-white transition-colors">
                <Camera size={13} /> Screenshot Tip
              </button>
              {typeof navigator.share === 'function' && (
                <button onClick={shareNative} className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-gray-400 hover:bg-white/5 hover:text-white transition-colors">
                  <Share2 size={13} /> Share...
                </button>
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};
