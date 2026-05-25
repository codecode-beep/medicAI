import { useQuery } from '@tanstack/react-query';
import { Clock, Pill, Activity } from 'lucide-react';
import { reportsApi } from '../lib/api';

export default function TimelinePage() {
  const { data, isLoading } = useQuery({
    queryKey: ['timeline'],
    queryFn: () => reportsApi.timeline().then((r) => r.data),
  });

  if (isLoading) return <div className="p-8 text-slate-500">Loading timeline...</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Medical Timeline</h1>
      <p className="text-slate-500 mb-8">Your chronological medical history</p>

      {data?.medicines && data.medicines.length > 0 && (
        <div className="mb-8 bg-white rounded-xl border p-6">
          <h2 className="font-semibold flex items-center gap-2 mb-4">
            <Pill className="w-5 h-5 text-primary-600" /> Active Medications
          </h2>
          <div className="grid sm:grid-cols-2 gap-3">
            {data.medicines.map((m: { name: string; dosage?: string; frequency?: string }, i: number) => (
              <div key={i} className="p-3 bg-slate-50 rounded-lg">
                <p className="font-medium">{m.name}</p>
                {m.dosage && <p className="text-sm text-slate-500">{m.dosage}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {data?.conditions && data.conditions.length > 0 && (
        <div className="mb-8 flex flex-wrap gap-2">
          {data.conditions.map((c: string) => (
            <span key={c} className="px-3 py-1 bg-red-50 text-red-700 rounded-full text-sm flex items-center gap-1">
              <Activity className="w-3 h-3" /> {c}
            </span>
          ))}
        </div>
      )}

      <div className="relative">
        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-slate-200" />
        <div className="space-y-6">
          {data?.events?.map((event: {
            id: number; title: string; event_type: string; description?: string;
            event_date: string; conditions?: string[]; medicines?: Array<{ name: string }>;
          }) => (
            <div key={event.id} className="relative pl-16">
              <div className="absolute left-4 w-5 h-5 bg-primary-600 rounded-full border-4 border-white shadow" />
              <div className="bg-white rounded-xl border p-5 shadow-sm">
                <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
                  <Clock className="w-3 h-3" />
                  {new Date(event.event_date).toLocaleDateString()}
                  <span className="px-2 py-0.5 bg-slate-100 rounded">{event.event_type}</span>
                </div>
                <h3 className="font-semibold">{event.title}</h3>
                {event.description && <p className="text-sm text-slate-600 mt-2">{event.description}</p>}
              </div>
            </div>
          ))}
        </div>
        {!data?.events?.length && (
          <p className="text-center text-slate-400 py-16">No medical history events yet.</p>
        )}
      </div>
    </div>
  );
}

