import { Badge, Empty, PageHeader, Panel } from '../../shared/components/ui';
import { useInvestigation } from '../../store/InvestigationContext';
import { SRC_LABEL } from '../dispatch/constants';

const INFO = {
  air_quality: 'Ground-sensor particulates (PM2.5, PM10, NO₂, O₃) with a 24 h baseline.',
  fire: 'Satellite thermal hotspots (VIIRS) with fire radiative power.',
  weather: 'Surface wind, gusts, temperature, humidity and precipitation.',
  earthquake: 'USGS seismic events near the target (context only).',
  geo: 'Nearby critical infrastructure from OpenStreetMap / Geoapify.',
};

export default function SourcesPage() {
  const { S, d } = useInvestigation();
  const list = S.sources?.sources || [];
  return (
    <div className="space-y-4">
      <PageHeader kicker={`${S.sources?.total_sources ?? 0} APIS // ${d.mode.toUpperCase()} MODE`} stage="07" title="Data Sources & Feeds" />
      {!list.length ? <Empty>Backend offline — no sources to list.</Empty> : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {list.map((s) => { const ev = d.ev[s.kind || s.id]; return (
            <Panel key={s.id} title={SRC_LABEL[s.kind] || s.id} right={<Badge level={ev ? (ev.status === 'ok' ? 'LOW' : 'CRITICAL') : 'IDLE'}>{ev ? ev.status.toUpperCase() : 'READY'}</Badge>}>
              <p className="text-sm text-slate-400">{INFO[s.kind] || INFO[s.id]}</p>
              <div className="mt-3 font-mono text-[11px] text-slate-500">id: {s.id} · mode: {s.mode}{s.is_mvp ? ' · MVP' : ''}{ev ? ` · data: ${ev.data_mode}` : ''}</div>
            </Panel>); })}
        </div>
      )}
    </div>
  );
}
