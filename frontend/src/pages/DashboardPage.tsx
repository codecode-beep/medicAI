import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Activity, AlertTriangle, Pill, FileText, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import FileUpload from '../components/FileUpload';
import { uploadApi } from '../lib/api';
import { useAppStore } from '../store';

const severityColors: Record<string, string> = {
  low: 'bg-green-100 text-green-700',
  moderate: 'bg-yellow-100 text-yellow-700',
  high: 'bg-red-100 text-red-700',
  critical: 'bg-red-200 text-red-900',
};

export default function DashboardPage() {
  const { saveToHistory, toggleSaveToHistory } = useAppStore();
  const [lastResult, setLastResult] = useState<{ report_id?: number; message: string } | null>(null);
  const queryClient = useQueryClient();

  const { data: reportsData } = useQuery({
    queryKey: ['reports'],
    queryFn: () => uploadApi.listReports().then((r) => r.data),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadApi.analyze(file, saveToHistory).then((r) => r.data),
    onSuccess: (data) => {
      setLastResult(data);
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      if (saveToHistory) {
        queryClient.invalidateQueries({ queryKey: ['timeline'] });
      }
    },
  });

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-slate-500">Upload and analyze medical documents with AI</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-lg">Upload Medical File</h2>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={saveToHistory}
                  onChange={toggleSaveToHistory}
                  className="rounded border-slate-300 text-primary-600"
                />
                Save to Medical History
              </label>
            </div>
            <FileUpload onUpload={(f) => uploadMutation.mutate(f)} isLoading={uploadMutation.isPending} />
            {lastResult && (
              <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
                {lastResult.message}
                {lastResult.report_id && (
                  <Link to={`/reports/${lastResult.report_id}`} className="ml-2 underline font-medium">
                    View Report →
                  </Link>
                )}
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl shadow-sm border p-6">
            <h2 className="font-semibold text-lg mb-4">Recent Analyses</h2>
            {reportsData?.reports?.length ? (
              <div className="space-y-3">
                {reportsData.reports.slice(0, 5).map((r) => (
                  <Link
                    key={r.id}
                    to={`/reports/${r.id}`}
                    className="flex items-center gap-4 p-3 rounded-lg hover:bg-slate-50 border"
                  >
                    <div className="w-10 h-10 bg-primary-50 rounded-lg flex items-center justify-center">
                      <FileText className="w-5 h-5 text-primary-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate" title={r.title}>{r.title}</p>
                      <p className="text-sm text-slate-500">{new Date(r.created_at).toLocaleString()}</p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      {r.is_saved ? (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">Saved</span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">Quick</span>
                      )}
                      {r.severity && (
                        <span className={`text-xs px-2 py-1 rounded-full ${severityColors[r.severity] || 'bg-slate-100'}`}>
                          {r.severity}
                        </span>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-slate-400 text-sm">No analyses yet. Upload a medical file to get started.</p>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-gradient-to-br from-primary-600 to-primary-800 text-white rounded-xl p-6">
            <Sparkles className="w-8 h-8 mb-3" />
            <h3 className="font-semibold text-lg">AI Insights</h3>
            <p className="text-blue-100 text-sm mt-2">
              {reportsData?.total
                ? `${reportsData.total} analysis${reportsData.total === 1 ? '' : 'es'} on record`
                : 'Upload your first report to get personalized AI insights'}
            </p>
          </div>

          {reportsData?.reports?.[0] && (
            <>
              <InsightCard
                icon={Activity}
                title="Latest Finding"
                value={reportsData.reports[0].ai_summary?.slice(0, 80) + '...' || 'N/A'}
              />
              {reportsData.reports[0].severity && (
                <InsightCard
                  icon={AlertTriangle}
                  title="Severity"
                  value={reportsData.reports[0].severity.toUpperCase()}
                />
              )}
              {reportsData.reports[0].medicines && reportsData.reports[0].medicines.length > 0 && (
                <InsightCard
                  icon={Pill}
                  title="Medicines"
                  value={reportsData.reports[0].medicines.map((m) => m.name).join(', ')}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function InsightCard({ icon: Icon, title, value }: { icon: React.ElementType; title: string; value: string }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-4 h-4 text-primary-600" />
        <span className="text-sm font-medium text-slate-600">{title}</span>
      </div>
      <p className="text-sm text-slate-800">{value}</p>
    </div>
  );
}
