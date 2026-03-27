import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { ChevronUp, ChevronDown, ChevronLeft, ChevronRight, Filter, Columns, Download } from 'lucide-react';

interface DataTableProps {
  threats: any[];
  onSelect: (threat: any) => void;
  onExport?: () => void;
}

type SortField = 'score' | 'ds_belief' | 'action' | 'user' | 'title' | 'anomaly' | 'reputation' | 'domain' | 'timestamp';
type SortDir = 'asc' | 'desc';

const ACTION_ORDER: Record<string, number> = { BLOCK: 0, FLAG: 1, REVIEW: 2, SAFE: 3 };
const PAGE_SIZES = [25, 50, 100];

export const DataTable: React.FC<DataTableProps> = ({ threats, onSelect, onExport }) => {
  const [sortField, setSortField] = useState<SortField>('score');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [filterAction, setFilterAction] = useState<string>('ALL');
  const [filterDomain, setFilterDomain] = useState<string>('ALL');
  const [search, setSearch] = useState('');
  const [visibleCols, setVisibleCols] = useState({
    action: true, score: true, user: true, title: true, ds_belief: true,
    anomaly: true, reputation: true, llm: true, domain: true, timestamp: true,
  });
  const [showColPicker, setShowColPicker] = useState(false);

  const domains = useMemo(() => [...new Set(threats.map(t => t.domain || 'unknown'))], [threats]);

  const filtered = useMemo(() => {
    let result = threats;
    if (filterAction !== 'ALL') result = result.filter(t => t.action === filterAction);
    if (filterDomain !== 'ALL') result = result.filter(t => (t.domain || 'unknown') === filterDomain);
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(t => t.user?.toLowerCase().includes(q) || t.title?.toLowerCase().includes(q));
    }
    return result;
  }, [threats, filterAction, filterDomain, search]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case 'score': cmp = (a.score || 0) - (b.score || 0); break;
        case 'ds_belief': cmp = (a.ds_belief || 0) - (b.ds_belief || 0); break;
        case 'action': cmp = (ACTION_ORDER[a.action] ?? 9) - (ACTION_ORDER[b.action] ?? 9); break;
        case 'user': cmp = (a.user || '').localeCompare(b.user || ''); break;
        case 'title': cmp = (a.title || '').localeCompare(b.title || ''); break;
        case 'anomaly': cmp = (a.signals?.anomaly || 0) - (b.signals?.anomaly || 0); break;
        case 'reputation': cmp = (a.signals?.reputation || 0) - (b.signals?.reputation || 0); break;
        case 'domain': cmp = (a.domain || '').localeCompare(b.domain || ''); break;
        case 'timestamp': cmp = Number(a.timestamp || 0) - Number(b.timestamp || 0); break;
      }
      return sortDir === 'desc' ? -cmp : cmp;
    });
  }, [filtered, sortField, sortDir]);

  const totalPages = Math.ceil(sorted.length / pageSize);
  const paged = sorted.slice(page * pageSize, (page + 1) * pageSize);

  const toggleSort = (field: SortField) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('desc'); }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ChevronDown size={10} className="text-gray-700" />;
    return sortDir === 'desc' ? <ChevronDown size={10} className="text-cyan-400" /> : <ChevronUp size={10} className="text-cyan-400" />;
  };

  const actionColor: Record<string, string> = {
    BLOCK: 'text-red-400 bg-red-500/10 border-red-500/30',
    FLAG: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
    REVIEW: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
    SAFE: 'text-green-400 bg-green-500/10 border-green-500/30',
  };

  const exportCSV = () => {
    const headers = ['Action', 'Score', 'User', 'Title', 'DS Belief', 'Anomaly', 'Reputation', 'LLM', 'Domain'];
    const rows = sorted.map(t => [
      t.action, t.score?.toFixed(1), t.user, `"${t.title}"`, (t.ds_belief * 100).toFixed(1),
      t.signals?.anomaly?.toFixed(1), t.signals?.reputation?.toFixed(1), t.signals?.llm || '', t.domain || '',
    ]);
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `wikistream_threats_${new Date().toISOString().slice(0, 10)}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="px-6 py-3 border-b border-white/5 flex items-center gap-3 shrink-0 flex-wrap">
        <input
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(0); }}
          placeholder="Filter by user or article..."
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-gray-300 placeholder:text-gray-600 focus:outline-none search-glow w-52"
        />

        <div className="flex items-center gap-1.5">
          <Filter size={12} className="text-gray-500" />
          <select
            value={filterAction}
            onChange={e => { setFilterAction(e.target.value); setPage(0); }}
            className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none"
          >
            <option value="ALL">All Actions</option>
            <option value="BLOCK">BLOCK</option>
            <option value="FLAG">FLAG</option>
            <option value="REVIEW">REVIEW</option>
            <option value="SAFE">SAFE</option>
          </select>
          <select
            value={filterDomain}
            onChange={e => { setFilterDomain(e.target.value); setPage(0); }}
            className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none"
          >
            <option value="ALL">All Domains</option>
            {domains.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>

        <div className="flex-1" />

        <span className="text-[10px] text-gray-500 font-mono">{sorted.length} results</span>

        <div className="relative">
          <button onClick={() => setShowColPicker(!showColPicker)} className="p-1.5 bg-white/5 hover:bg-white/10 rounded-lg border border-white/10 transition-colors" title="Toggle columns">
            <Columns size={12} className="text-gray-400" />
          </button>
          {showColPicker && (
            <div className="absolute right-0 top-full mt-1 bg-[#0f0f13] border border-white/10 rounded-lg p-2 z-20 min-w-[140px]">
              {Object.entries(visibleCols).map(([key, visible]) => (
                <label key={key} className="flex items-center gap-2 py-1 px-1 text-xs text-gray-400 hover:text-white cursor-pointer">
                  <input type="checkbox" checked={visible} onChange={() => setVisibleCols(v => ({ ...v, [key]: !v[key] }))} className="accent-cyan-500" />
                  {key.toUpperCase()}
                </label>
              ))}
            </div>
          )}
        </div>

        <button onClick={exportCSV} className="p-1.5 bg-white/5 hover:bg-white/10 rounded-lg border border-white/10 transition-colors" title="Export CSV">
          <Download size={12} className="text-gray-400" />
        </button>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 z-10 bg-[#0a0a0c]">
            <tr className="border-b border-white/5">
              {visibleCols.action && <th onClick={() => toggleSort('action')} className="px-3 py-2.5 text-left text-[10px] text-gray-500 font-bold uppercase cursor-pointer hover:text-gray-300 select-none"><div className="flex items-center gap-1">Action<SortIcon field="action" /></div></th>}
              {visibleCols.score && <th onClick={() => toggleSort('score')} className="px-3 py-2.5 text-right text-[10px] text-gray-500 font-bold uppercase cursor-pointer hover:text-gray-300 select-none"><div className="flex items-center justify-end gap-1">Score<SortIcon field="score" /></div></th>}
              {visibleCols.user && <th onClick={() => toggleSort('user')} className="px-3 py-2.5 text-left text-[10px] text-gray-500 font-bold uppercase cursor-pointer hover:text-gray-300 select-none"><div className="flex items-center gap-1">User<SortIcon field="user" /></div></th>}
              {visibleCols.title && <th onClick={() => toggleSort('title')} className="px-3 py-2.5 text-left text-[10px] text-gray-500 font-bold uppercase cursor-pointer hover:text-gray-300 select-none"><div className="flex items-center gap-1">Article<SortIcon field="title" /></div></th>}
              {visibleCols.ds_belief && <th onClick={() => toggleSort('ds_belief')} className="px-3 py-2.5 text-right text-[10px] text-gray-500 font-bold uppercase cursor-pointer hover:text-gray-300 select-none"><div className="flex items-center justify-end gap-1">Belief<SortIcon field="ds_belief" /></div></th>}
              {visibleCols.anomaly && <th onClick={() => toggleSort('anomaly')} className="px-3 py-2.5 text-right text-[10px] text-gray-500 font-bold uppercase cursor-pointer hover:text-gray-300 select-none"><div className="flex items-center justify-end gap-1">Anomaly<SortIcon field="anomaly" /></div></th>}
              {visibleCols.reputation && <th onClick={() => toggleSort('reputation')} className="px-3 py-2.5 text-right text-[10px] text-gray-500 font-bold uppercase cursor-pointer hover:text-gray-300 select-none"><div className="flex items-center justify-end gap-1">Repute<SortIcon field="reputation" /></div></th>}
              {visibleCols.llm && <th className="px-3 py-2.5 text-left text-[10px] text-gray-500 font-bold uppercase">LLM</th>}
              {visibleCols.domain && <th onClick={() => toggleSort('domain')} className="px-3 py-2.5 text-left text-[10px] text-gray-500 font-bold uppercase cursor-pointer hover:text-gray-300 select-none"><div className="flex items-center gap-1">Domain<SortIcon field="domain" /></div></th>}
              {visibleCols.timestamp && <th onClick={() => toggleSort('timestamp')} className="px-3 py-2.5 text-right text-[10px] text-gray-500 font-bold uppercase cursor-pointer hover:text-gray-300 select-none"><div className="flex items-center justify-end gap-1">Time<SortIcon field="timestamp" /></div></th>}
            </tr>
          </thead>
          <tbody>
            {paged.map((t, i) => (
              <motion.tr
                key={`${t.user}-${t.title}-${i}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: Math.min(i * 0.01, 0.3) }}
                onClick={() => onSelect(t)}
                className="border-b border-white/[0.03] hover:bg-white/[0.03] cursor-pointer transition-colors group"
              >
                {visibleCols.action && <td className="px-3 py-2"><span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${actionColor[t.action] || 'text-gray-400'}`}>{t.action}</span></td>}
                {visibleCols.score && <td className="px-3 py-2 text-right font-mono font-bold" style={{ color: t.score > 70 ? '#ef4444' : t.score > 40 ? '#f97316' : t.score > 20 ? '#facc15' : '#22c55e' }}>{t.score?.toFixed(1)}</td>}
                {visibleCols.user && <td className="px-3 py-2 text-blue-400 font-mono truncate max-w-[120px]">{t.user}</td>}
                {visibleCols.title && <td className="px-3 py-2 text-gray-300 truncate max-w-[200px] group-hover:text-white">{t.title}</td>}
                {visibleCols.ds_belief && <td className="px-3 py-2 text-right font-mono text-green-400">{((t.ds_belief || 0) * 100).toFixed(0)}%</td>}
                {visibleCols.anomaly && <td className="px-3 py-2 text-right font-mono text-yellow-400">{t.signals?.anomaly?.toFixed(0) || '-'}%</td>}
                {visibleCols.reputation && <td className="px-3 py-2 text-right font-mono text-blue-400">{t.signals?.reputation?.toFixed(0) || '-'}%</td>}
                {visibleCols.llm && <td className="px-3 py-2"><span className={`text-[10px] font-bold ${t.signals?.llm === 'VANDALISM' ? 'text-red-400' : t.signals?.llm === 'SUSPICIOUS' ? 'text-orange-400' : 'text-gray-500'}`}>{t.signals?.llm || '-'}</span></td>}
                {visibleCols.domain && <td className="px-3 py-2 text-gray-500 text-[10px] font-mono">{t.domain || '-'}</td>}
                {visibleCols.timestamp && <td className="px-3 py-2 text-right text-gray-500 text-[10px] font-mono">{t.timestamp ? new Date(Number(t.timestamp) * 1000).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : '-'}</td>}
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="px-6 py-2.5 border-t border-white/5 flex items-center justify-between shrink-0 bg-[#0a0a0c]">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-500">Rows:</span>
          {PAGE_SIZES.map(s => (
            <button
              key={s}
              onClick={() => { setPageSize(s); setPage(0); }}
              className={`px-2 py-0.5 rounded text-[10px] font-mono ${pageSize === s ? 'bg-cyan-500/15 text-cyan-400' : 'text-gray-500 hover:text-gray-300'}`}
            >
              {s}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-500 font-mono">
            {page * pageSize + 1}-{Math.min((page + 1) * pageSize, sorted.length)} of {sorted.length}
          </span>
          <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} className="p-1 rounded hover:bg-white/10 disabled:opacity-30">
            <ChevronLeft size={14} className="text-gray-400" />
          </button>
          <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1} className="p-1 rounded hover:bg-white/10 disabled:opacity-30">
            <ChevronRight size={14} className="text-gray-400" />
          </button>
        </div>
      </div>
    </div>
  );
};
