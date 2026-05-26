import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Download, ArrowLeft, AlertTriangle, Pill, FileText } from 'lucide-react';
import { reportsApi } from '../lib/api';

const severityColors: Record<string, string> = {
  low: 'text-green-600 bg-green-50',
  moderate: 'text-yellow-600 bg-yellow-50',
  high: 'text-red-600 bg-red-50',
  critical: 'text-red-800 bg-red-100',
};

export default function ReportViewerPage() {
  const { id } = useParams<{ id: string }>();
  const { data: report, isLoading } = useQuery({
    queryKey: ['report', id],
    queryFn: () => reportsApi.get(Number(id)).then((r) => r.data),
    enabled: !!id,
  });

  if (isLoading) return <div className="p-8 text-slate-500">Loading report...</div>;
  if (!report) return <div className="p-8 text-red-500">Report not found</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <Link to="/reports" className="flex items-center gap-2 text-primary-600 text-sm mb-6 hover:underline">
        <ArrowLeft className="w-4 h-4" /> Back to Reports
      </Link>

      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <div className="p-6 border-b bg-slate-50">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h1 className="text-2xl font-bold break-words" title={report.title}>
                {report.title}
              </h1>
              <p className="text-slate-500 text-sm mt-1">
                {report.report_type.toUpperCase()} · {new Date(report.created_at).toLocaleString()}
              </p>
            </div>
            {report.severity && (
              <span className={`shrink-0 px-3 py-1 rounded-full text-sm font-medium whitespace-nowrap ${severityColors[report.severity] || ''}`}>
                {report.severity.toUpperCase()}
              </span>
            )}
          </div>
          {report.generated_pdf_url && (
            <a
              href={report.generated_pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700"
            >
              <Download className="w-4 h-4" /> Download PDF Report
            </a>
          )}
        </div>

        <div className="p-6 space-y-6">
          <Section title="AI Summary" icon={FileText}>
            <p className="text-slate-700 leading-relaxed">{report.ai_summary || 'No summary available'}</p>
          </Section>

          {report.ai_findings && (
            <Section title="Key Findings" icon={AlertTriangle}>
              <ul className="space-y-2">
                {((report.ai_findings as { findings?: string[] }).findings || []).map((f, i) => (
                  <li key={i} className="flex gap-2 text-slate-700">
                    <span className="text-primary-500">•</span> {f}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {report.medicines && report.medicines.length > 0 && (
            <Section title="Medicines" icon={Pill}>
              <div className="grid sm:grid-cols-2 gap-3">
                {report.medicines.map((m, i) => (
                  <div key={i} className="p-3 bg-slate-50 rounded-lg">
                    <p className="font-medium">{m.name}</p>
                    {m.dosage && <p className="text-sm text-slate-500">Dosage: {m.dosage}</p>}
                    {m.frequency && <p className="text-sm text-slate-500">Frequency: {m.frequency}</p>}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {report.conditions && report.conditions.length > 0 && (
            <Section title="Conditions Identified">
              <div className="flex flex-wrap gap-2">
                {report.conditions.map((c) => (
                   <span key={c} className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm">{c}</span>
                ))}
              </div>
            </Section>
          )}

          {report.recommendations && report.recommendations.length > 0 && (
            <Section title="Recommendations">
              <ul className="space-y-2">
                {report.recommendations.map((r, i) => (
                  <li key={i} className="text-slate-700 flex gap-2">
                    <span className="text-green-500 font-bold">{i + 1}.</span> {r}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {report.historical_comparison && (
            <Section title="Historical Comparison">
              <p className="text-slate-700">
                {(report.historical_comparison as { summary?: string }).summary ||
                  JSON.stringify(report.historical_comparison)}
              </p>
            </Section>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ title, icon: Icon, children }: { title: string; icon?: React.ElementType; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="font-semibold text-lg mb-3 flex items-center gap-2">
        {Icon && <Icon className="w-5 h-5 text-primary-600" />}
        {title}
      </h2>
      {children}
    </div>
  );
}

