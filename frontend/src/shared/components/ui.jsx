import { levelStyle } from '../../core/utils/risk';

export function Panel({ title, right, children, className = '' }) {
  return (
    <section className={`card p-4 ${className}`}>
      {(title || right) && (
        <header className="mb-3 flex items-center justify-between gap-3">
          <h3 className="label">{title}</h3>
          {right}
        </header>
      )}
      {children}
    </section>
  );
}

export function Badge({ level = 'IDLE', children }) {
  const s = levelStyle(level);
  return <span className={`rounded border px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider ${s.text} ${s.bg} ${s.border}`}>{children ?? level}</span>;
}

export function Stat({ label, value, unit, level, className = '' }) {
  const s = levelStyle(level);
  return (
    <div className={`panel-2 p-3 ${className}`}>
      <div className="label">{label}</div>
      <div className={`mt-1 font-mono text-xl font-semibold ${level ? s.text : 'text-slate-100'}`}>
        {value}{unit && <span className="ml-1 text-xs font-normal text-slate-500">{unit}</span>}
      </div>
    </div>
  );
}

export function PageHeader({ stage, kicker, title, subtitle, right }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className="label flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-accent" />{kicker}{stage && <span className="text-slate-600">· STAGE {stage}</span>}</div>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-white">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-slate-400">{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

export function Empty({ children = 'Run an investigation to see data here.' }) {
  return <div className="panel-2 border-dashed p-6 text-center text-sm text-slate-500">{children}</div>;
}

export function Dot({ level = 'LOW' }) {
  return <span className="inline-block h-2 w-2 rounded-full" style={{ background: levelStyle(level).hex }} />;
}
