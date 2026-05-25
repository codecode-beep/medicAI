import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FileText, GitCompare } from 'lucide-react';
import { uploadApi, reportsApi } from '../lib/api';

export default function ReportsPage() {
  const [compareMode, setCompareMode] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);
  const [comparison, setComparison] = useState<Record<string, unknown> | null>(null);

  const { data } = useQuery({
    queryKey: ['reports'],
    queryFn: () => uploadApi.listReports().then((r) => r.data),
  });

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  };

  const handleCompare = async () => {
    if (selected.length !== 2) return;
    const { data: result } = await reportsApi.compare(selected[0], selected[1]);
    setComparison(result.comparison);
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Medical Reports</h1>
          <p className="text-slate-500">
            {data?.total || 0} report{data?.total === 1 ? '' : 's'} — quick analyses and saved history
          </p>
        </div>
        <button
          onClick={() => { setCompareMode(!compareMode); setSelected([]); setComparison(null); }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
            compareMode ? 'bg-primary-600 text-white' : 'border hover:bg-slate-50'
          }`}
        >
          <GitCompare className="w-4 h-4" /> Compare Reports
        </button>
      </div>

      {compareMode && selected.length === 2 && (
        <button
          onClick={handleCompare}
          className="mb-4 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700"
        >
          Compare Selected Reports
        </button>
      )}

      {comparison && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-xl">
          <h3 className="font-semibold mb-2">Comparison Result</h3>
          <p className="text-sm text-slate-700">{(comparison as { summary?: string }).summary}</p>
        </div>
      )}

      <div className="grid sm:grid-cols-2 gap-4">
        {data?.reports?.map((r) => (
          <div
            key={r.id}
            className={`bg-white rounded-xl border p-5 transition-shadow hover:shadow-md ${
              compareMode && selected.includes(r.id) ? 'ring-2 ring-primary-500' : ''
            }`}
            onClick={() => compareMode && toggleSelect(r.id)}
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-primary-50 rounded-xl flex items-center justify-center">
                <FileText className="w-6 h-6 text-primary-600" />
              </div>
                <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold">{r.title}</h3>
                  {r.is_saved ? (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">In history</span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">Quick only</span>
                  )}
                </div>
                <p className="text-sm text-slate-500 mt-1">{new Date(r.created_at).toLocaleDateString()}</p>
                <p className="text-sm text-slate-600 mt-2 line-clamp-2">{r.ai_summary}</p>
                {!compareMode && (
                  <Link to={`/reports/${r.id}`} className="text-primary-600 text-sm mt-3 inline-block hover:underline">
                    View Report →
                  </Link>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {!data?.reports?.length && (
        <p className="text-center text-slate-400 py-16">
          No reports yet. Upload from the Dashboard — enable &quot;Save to Medical History&quot; to add items to Timeline.
        </p>
      )}
    </div>
  );
}

