export default function TopBar() {
  return (
    <header className="sticky top-0 z-20 h-12 border-b border-border bg-bg/85 backdrop-blur-md flex items-center px-6 gap-2">
      <Pill dot="bg-good" label="Market open · NSE" />
      <Pill label="BSE 500 ▲ 0.42%" />
      <Pill label="India VIX 14.2" />
      <div className="ml-auto text-[11.5px] text-mute">pistol v0.1 · localhost</div>
    </header>
  );
}

function Pill({ dot, label }: { dot?: string; label: string }) {
  return (
    <div className="h-7 px-2.5 inline-flex items-center gap-1.5 rounded-full bg-panel border border-border text-[11.5px] text-ink/90">
      {dot && <span className={"w-1.5 h-1.5 rounded-full " + dot} />}
      <span>{label}</span>
    </div>
  );
}
