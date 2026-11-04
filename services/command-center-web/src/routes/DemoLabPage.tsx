import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";

import { useSession, useSessionActions } from "../session/SessionProvider";
import {
  compareScheduling,
  fetchTrace,
  runQualityExcursion,
  runSimulation,
  runVision,
  type QualityResponse,
  type SchedulingJob,
  type SchedulingResponse,
  type SimulationResponse,
  type SimulationState,
  type TraceResponse,
  type VisionResponse,
} from "../demoLab/demoLabClient";

const WORLD_ID = "DEMO-WORLD";

function Code({ children }: { children: ReactNode }) {
  return <code className="demo-code">{children ?? "—"}</code>;
}

function ResultMessage({ message }: { message: string | null }) {
  return message ? <p className="demo-error" role="alert">{message}</p> : null;
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try { return JSON.stringify(value); } catch { return "[okunamayan değer]"; }
}

function rounded(value: number | null | undefined, digits = 2): string {
  return value === null || value === undefined ? "—" : value.toFixed(digits);
}

function visionOutcome(outcome: string): string {
  return outcome === "DEFECT_CANDIDATES" ? "Anomali adayı bulundu" : outcome === "NO_DEFECT_CANDIDATES" ? "Anomali adayı bulunmadı" : "Değerlendirilemedi";
}

function eventLabel(kind: string): string {
  const labels: Record<string, string> = {
    LOT_RELEASED: "Lot serbest bırakıldı", LOT_QUEUED: "Lot kuyruğa alındı", DISPATCH_ACCEPTED: "İş emri kabul edildi",
    DISPATCH_STARTED: "İşleme başladı", DISPATCH_REJECTED: "İş emri reddedildi", PROCESS_COMPLETED: "Proses tamamlandı",
    INSPECTION_FAILED: "Kalite kontrolü başarısız", REWORK_REQUESTED: "Yeniden işleme istendi", LOT_COMPLETED: "Lot tamamlandı",
    EQUIPMENT_FAILED: "Makine arızalandı", EQUIPMENT_REPAIRED: "Makine onarıldı", EQUIPMENT_DEGRADED: "Makine sağlığı düştü",
    MAINTENANCE_STARTED: "Bakım başladı", MAINTENANCE_COMPLETED: "Bakım tamamlandı",
  };
  return labels[kind] ?? kind.replaceAll("_", " ");
}

type VisionSide = "clean" | "defect";

function VisionImage({ preview, result }: { preview: string; result: VisionResponse | null }) {
  return <div className="vision-stage"><div className="vision-image-frame"><img src={preview} alt="Vision inceleme girdisi" />{result?.observation.defects.map((defect) => { const x = Math.min(1, Math.max(0, defect.localization.x)); const y = Math.min(1, Math.max(0, defect.localization.y)); const width = Math.min(1 - x, Math.max(0, defect.localization.width)); const height = Math.min(1 - y, Math.max(0, defect.localization.height)); return <div className="vision-box" key={defect.defect_id} style={{ left: `${x * 100}%`, top: `${y * 100}%`, width: `${width * 100}%`, height: `${height * 100}%` }}><span>{defect.defect_id} · skor {rounded(defect.anomaly_score)}</span></div>; })}</div></div>;
}

function VisionResult({ result }: { result: VisionResponse | null }) {
  if (!result) return <p className="vision-no-result">Henüz Vision çalıştırılmadı.</p>;
  return <div className="vision-result"><strong>{visionOutcome(result.observation.outcome)}</strong><span>{result.observation.defects.length} bölge · en yüksek skor {rounded(result.observation.image_anomaly_score)}</span><small>{result.observation.review_required ? "İnsan incelemesi gerekli" : "İnsan incelemesi gerekmiyor"} · {rounded(result.observation.inference.latency_ms, 1)} ms</small><p className="vision-quality-note">{result.observation.defects.length === 0 ? "Sıfır anomali adayı otomatik kalite onayı değildir; kabul kararı için yetkili kalite değerlendirmesi gerekir." : "Bu çıktı yalnızca görüntü tabanlı anomali gözlemidir; kalite kabulü yerine geçmez."}</p></div>;
}

function VisionPanel({ expire, csrfToken }: { expire: () => void; csrfToken: string }) {
  const [files, setFiles] = useState<Record<VisionSide, File | null>>({ clean: null, defect: null });
  const [previews, setPreviews] = useState<Record<VisionSide, string | null>>({ clean: null, defect: null });
  const [results, setResults] = useState<Record<VisionSide, VisionResponse | null>>({ clean: null, defect: null });
  const [zThreshold, setZThreshold] = useState(6.5);
  const [minArea, setMinArea] = useState(24);
  const [busy, setBusy] = useState<VisionSide | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const selectFile = (side: VisionSide, next: File | undefined) => {
    if (!next) return;
    const isSupported = ["image/png", "image/jpeg", "image/jpg"].includes(next.type) || /[.]jpe?g$|[.]png$/i.test(next.name);
    if (!isSupported) return setMessage("Yalnızca PNG, JPG veya JPEG yüklenebilir.");
    setFiles((current) => ({ ...current, [side]: next }));
    setPreviews((current) => ({ ...current, [side]: URL.createObjectURL(next) }));
    setResults((current) => ({ ...current, [side]: null }));
    setMessage(null);
  };
  const inspect = async (side: VisionSide) => {
    const file = files[side];
    if (!file) return;
    setBusy(side); setMessage(null);
    try {
      const response = await runVision(file, { worldId: WORLD_ID, lotId: "DEMO-LAB-VISION", zThreshold, minArea }, csrfToken, new AbortController().signal);
      if (response.status === "unauthenticated") return expire();
      if (response.status === "error") return setMessage(`Vision çalıştırılamadı: ${response.message}`);
      setResults((current) => ({ ...current, [side]: response.value }));
    } catch (error) { setMessage(`Vision sonucu işlenemedi: ${error instanceof Error ? error.message : "beklenmeyen hata"}`); }
    finally { setBusy(null); }
  };
  return <section className="demo-panel demo-panel-wide"><div className="demo-panel-heading"><div><p className="eyebrow">01 / VISION</p><h2>Görüntü inceleme</h2></div><span className="status-badge status-good">GERÇEK PIPELINE</span></div><p className="demo-copy">JPG, JPEG veya PNG görüntüleri gerçek yerel-kontrast/MAD Vision algoritmasından geçirip, normalize koordinatlı bölgeleri görüntünün üzerinde karşılaştırın.</p><div className="demo-controls"><label><span>Z eşiği</span><input type="number" min="1" max="30" step="0.5" value={zThreshold} onChange={(event) => setZThreshold(Number(event.target.value))} /></label><label><span>Min. alan (px)</span><input type="number" min="1" max="10000" value={minArea} onChange={(event) => setMinArea(Number(event.target.value))} /></label><span className="demo-hint">Koordinat çerçevesi: IMAGE_NORMALIZED</span></div><ResultMessage message={message} /><div className="vision-compare-grid">{(["clean", "defect"] as VisionSide[]).map((side) => { const title = side === "clean" ? "Temiz görüntü" : "Kusurlu görüntü"; const runLabel = side === "clean" ? "Temiz görüntüyü çalıştır" : "Kusurlu görüntüyü çalıştır"; return <article className="vision-card" key={side}><div className="vision-card-heading"><strong>{title}</strong><label className="demo-file"><span>Görüntü seç</span><input aria-label={`${title} PNG`} type="file" accept="image/png,image/jpeg,image/jpg,.png,.jpg,.jpeg" onChange={(event) => selectFile(side, event.target.files?.[0])} /></label></div>{previews[side] ? <VisionImage preview={previews[side]!} result={results[side]} /> : <div className="demo-empty">{title} için PNG, JPG veya JPEG seçin.</div>}<VisionResult result={results[side]} /><button className="button button-primary" type="button" disabled={!files[side] || busy !== null} onClick={() => void inspect(side)}>{busy === side ? "Çalışıyor…" : runLabel}</button></article>; })}</div><div className="demo-result-grid vision-metadata"><div><span>Temiz aday</span><strong>{results.clean?.observation.defects.length ?? "—"}</strong></div><div><span>Kusurlu aday</span><strong>{results.defect?.observation.defects.length ?? "—"}</strong></div><div><span>Pipeline</span><strong>{results.defect?.observation.pipeline_identity.preprocessing_version ?? results.clean?.observation.pipeline_identity.preprocessing_version ?? "—"}</strong></div><div><span>Kalibrasyon</span><strong>{results.defect?.observation.confidence_calibration ?? results.clean?.observation.confidence_calibration ?? "—"}</strong></div></div></section>;
}

function SimulationStateCard({ title, state }: { title: string; state: SimulationState }) {
  return <div className="demo-state-card"><div className="demo-state-card-heading"><strong>{title}</strong><Code>{state.state_revision} · t={state.simulation_time}</Code></div><div className="demo-state-columns"><div><span>Lotlar</span>{state.lots.map((lot) => <div className="demo-state-row" key={lot.lot_id}><strong>{lot.lot_id}</strong><span>{lot.lifecycle} / {lot.execution_state}</span><span>{lot.held ? "HOLD" : lot.current_visit ?? "TAMAM"}</span></div>)}</div><div><span>Makineler</span>{state.machines.map((machine) => <div className="demo-state-row" key={machine.machine_id}><strong>{machine.machine_id}</strong><span>{machine.state}</span><span>{machine.health}</span></div>)}</div></div></div>;
}

function SimulationTimeline({ result }: { result: SimulationResponse }) {
  return <div className="simulation-timeline"><div className="simulation-timeline-heading"><strong>Lot ve makine ilerleyişi</strong><span>{result.run.timeline.length} gerçek operasyon olayı</span></div>{result.run.timeline.length ? result.run.timeline.map((event) => <div className="simulation-timeline-item" key={`${event.sequence}-${event.kind}`}><Code>t={event.time}</Code><span className="timeline-lane">{event.lane}</span><strong>{eventLabel(event.kind)}</strong><span>{event.lot_id ?? "—"}{event.machine_id ? ` · ${event.machine_id}` : ""}{event.route_step ? ` · ${event.route_step}` : ""}</span></div>) : <p className="vision-no-result">Bu parametrelerle yayınlanan operasyon olayı yok.</p>}</div>;
}

function SimulationGantt({ result }: { result: SimulationResponse }) {
  const bars = result.run.gantt;
  const maxTime = Math.max(
    1,
    result.run.result.simulation_time,
    ...bars.map((bar) => bar.end_time ?? bar.start_time),
  );
  const machines = Array.from(
    new Set([
      ...result.run.state.final.machines.map((machine) => machine.machine_id),
      ...bars.map((bar) => bar.machine_id),
    ]),
  ).sort();
  return <div className="simulation-gantt"><div className="simulation-timeline-heading"><strong>Gerçek olaylardan makine / lot Gantt</strong><span>{bars.length} operasyon aralığı · zaman ekseni t=0…{maxTime}</span></div>{bars.length === 0 ? <p className="vision-no-result">Bu parametrelerle başlangıç ve bitişi kanıtlanmış operasyon yok.</p> : <><div className="simulation-gantt-scale"><span>t=0</span><span>t={maxTime}</span></div>{machines.map((machineId) => <div className="simulation-gantt-row" key={machineId}><div className="simulation-gantt-label"><strong>{machineId}</strong><small>{bars.filter((bar) => bar.machine_id === machineId).length} iş</small></div><div className="simulation-gantt-track">{bars.filter((bar) => bar.machine_id === machineId).map((bar) => { const visualEnd = bar.end_time ?? maxTime; const left = `${(bar.start_time / maxTime) * 100}%`; const width = `${Math.max(((visualEnd - bar.start_time) / maxTime) * 100, 1.5)}%`; return <div className={`simulation-gantt-bar ${bar.status === "IN_PROGRESS" ? "simulation-gantt-open" : ""}`} key={`${bar.lot_id}-${bar.route_step}-${bar.start_time}`} style={{ left, width }} title={`${bar.lot_id} · ${bar.route_step} · t=${bar.start_time}–${bar.end_time ?? "bitiş yok"}`}><strong>{bar.lot_id}</strong><small>{bar.route_step} · {bar.end_time === null ? "bitiş yok" : `t=${bar.start_time}–${bar.end_time}`}</small>{bar.failure_events.map((failure) => <span className="simulation-gantt-failure" key={`${failure.sequence}-${failure.time}`} style={{ left: `${((failure.time - bar.start_time) / Math.max(visualEnd - bar.start_time, 1)) * 100}%` }} title={`Arıza: t=${failure.time}`}>!</span>)}</div>; })}</div></div>)}</>}</div>;
}

function SimulationPanel({ expire, csrfToken }: { expire: () => void; csrfToken: string }) {
  const [seed, setSeed] = useState(4242); const [horizon, setHorizon] = useState(100); const [lotCount, setLotCount] = useState(4); const [defect, setDefect] = useState(250); const [failureAt, setFailureAt] = useState(0); const [result, setResult] = useState<SimulationResponse | null>(null); const [message, setMessage] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const run = async () => { setBusy(true); setMessage(null); try { const response = await runSimulation({ seed, horizon, lot_count: lotCount, defect_per_mille: defect, failure_at: failureAt || null }, csrfToken, new AbortController().signal); if (response.status === "unauthenticated") { setMessage("Oturum süresi doldu. Yeniden giriş yapın."); expire(); return; } if (response.status === "error") { setMessage(`Simülasyon çalıştırılamadı: ${response.message}`); return; } setResult(response.value); } catch (error) { setMessage(`Simülasyon sonucu işlenemedi: ${error instanceof Error ? error.message : "beklenmeyen hata"}`); } finally { setBusy(false); } };
  return <section className="demo-panel demo-panel-wide"><div className="demo-panel-heading"><div><p className="eyebrow">02 / SİMÜLATÖR</p><h2>Üretim simülasyonu</h2></div><span className="status-badge status-neutral">GERÇEK KERNEL</span></div><p className="demo-copy">Seed, zaman ufku, lot sayısı, hata olasılığı ve makine arızasını değiştirin. Özet, gerçek operasyon olaylarından üretilen Gantt ve zaman çizelgesi birlikte gösterilir.</p><div className="demo-controls"><label><span>Seed</span><input type="number" min="0" max="2147483647" value={seed} onChange={(event) => setSeed(Number(event.target.value))} /></label><label><span>Zaman ufku</span><input type="number" min="1" max="100000" value={horizon} onChange={(event) => setHorizon(Number(event.target.value))} /></label><label><span>Lot sayısı</span><input type="number" min="1" max="20" value={lotCount} onChange={(event) => setLotCount(Number(event.target.value))} /></label><label><span>Hata ‰</span><input type="number" min="0" max="1000" value={defect} onChange={(event) => setDefect(Number(event.target.value))} /></label><label><span>Arıza tick</span><input type="number" min="0" max="100000" value={failureAt} onChange={(event) => setFailureAt(Number(event.target.value))} /></label><button className="button button-primary" type="button" disabled={busy} onClick={() => void run()}>{busy ? "Çalışıyor…" : "Simülasyonu başlat"}</button></div><ResultMessage message={message} />{result ? <><div className="demo-result-grid"><div><span>İşlenen olay</span><strong>{result.run.result.processed_events}</strong></div><div><span>Simülasyon zamanı</span><strong>t={result.run.result.simulation_time}</strong></div><div><span>Sonlanma</span><strong>{result.run.result.termination}</strong></div><div><span>Operasyon olayı</span><strong>{result.run.operational_events.length}</strong></div></div><div className="demo-state-grid"><SimulationStateCard title="Başlangıç durumu" state={result.run.state.initial} /><SimulationStateCard title="Son durum" state={result.run.state.final} /></div><SimulationGantt result={result} /><SimulationTimeline result={result} /><details className="demo-details"><summary>Teknik kayıtları aç · {result.run.records.length} kernel olayı</summary><div className="demo-event-list">{result.run.records.map((event) => <div key={`${event.sequence}-${event.event_id ?? event.kind}`}><Code>t={event.time}</Code><strong>{event.kind}</strong><span>{displayValue(event.outcome)}</span></div>)}</div><div className="demo-operational-list"><strong>Operasyonel yayın kayıtları</strong>{result.run.operational_events.map((event, index) => <div key={`${event.time}-${event.kind}-${index}`}><Code>t={event.time}</Code><strong>{event.kind}</strong><span>{displayValue(event.attributes)}</span></div>)}</div></details><details className="demo-details"><summary>Çalışma provenance ve digest</summary><p><span>Senaryo </span><Code>{displayValue(result.run.scenario)}</Code></p><p><span>Event digest </span><Code>{result.run.result.event_sequence_digest}</Code></p><p><span>State digest </span><Code>{result.run.result.final_state_digest}</Code></p></details></> : null}</section>;
}

function formatScheduleKey(value: unknown): string { if (typeof value === "string" || typeof value === "number") return String(value); if (value && typeof value === "object" && "numerator" in value && "denominator" in value) { const fraction = value as { numerator: number; denominator: number }; return fraction.denominator === 1 ? String(fraction.numerator) : `${fraction.numerator}/${fraction.denominator}`; } return displayValue(value); }
function jobSummary(job: SchedulingJob | null): string { return job ? `${job.job_id} · kuyruk ${job.queue_entry_tick} · vade ${job.due_tick} · sonraki ${job.operation_ticks} tick · rota ${job.remaining_route_ticks} tick` : "Uygun aday yok"; }

function SchedulingPanel({ expire, csrfToken }: { expire: () => void; csrfToken: string }) {
  const [seed, setSeed] = useState(4242); const [jobs, setJobs] = useState(12); const [tick, setTick] = useState(20); const [result, setResult] = useState<SchedulingResponse | null>(null); const [message, setMessage] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const run = async () => { setBusy(true); setMessage(null); try { const response = await compareScheduling({ seed, job_count: jobs, decision_tick: tick, horizon_ticks: 100 }, csrfToken, new AbortController().signal); if (response.status === "unauthenticated") return expire(); if (response.status === "error") return setMessage(`Çizelgeleme çalıştırılamadı: ${response.message}`); setResult(response.value); } catch (error) { setMessage(`Çizelgeleme sonucu işlenemedi: ${error instanceof Error ? error.message : "beklenmeyen hata"}`); } finally { setBusy(false); } };
  const candidateJobs = useMemo(() => result?.instance.jobs ?? [], [result]);
  return <section className="demo-panel demo-panel-wide"><div className="demo-panel-heading"><div><p className="eyebrow">03 / ÇİZELGELEME</p><h2>Beş algoritmanın karşılaştırması</h2></div><span className="status-badge status-neutral">GERÇEK BASELINE</span></div><p className="demo-copy">Aynı değişmez sentetik örnek üzerinde çalışan FIFO, EDD, CR, SPT ve SRPT’nin aday işlerini, gerçek öncelik anahtarlarını ve seçim gerekçelerini birlikte görün.</p><div className="demo-controls"><label><span>Seed</span><input type="number" min="0" value={seed} onChange={(event) => setSeed(Number(event.target.value))} /></label><label><span>Aday iş sayısı</span><input type="number" min="1" max="100" value={jobs} onChange={(event) => setJobs(Number(event.target.value))} /></label><label><span>Karar tick</span><input type="number" min="0" max="100000" value={tick} onChange={(event) => setTick(Number(event.target.value))} /></label><button className="button button-primary" type="button" disabled={busy} onClick={() => void run()}>{busy ? "Hesaplanıyor…" : "Karşılaştır"}</button></div><ResultMessage message={message} />{result ? <><p className="demo-provenance">{result.provenance} · <Code>{result.instance.instance_id}</Code></p><div className="schedule-candidates"><strong>Karar anındaki gerçek adaylar</strong><div className="schedule-candidate-grid">{candidateJobs.map((job) => <div className={job.dispatchable ? "candidate-card" : "candidate-card candidate-ineligible"} key={job.job_id}><strong>{job.job_id}</strong><span>Kuyruk {job.queue_entry_tick} · Vade {job.due_tick}</span><span>Sonraki operasyon {job.operation_ticks} · Kalan rota {job.remaining_route_ticks}</span><small>{job.dispatchable ? "SEÇİLEBİLİR" : "Henüz serbest değil"}</small></div>)}</div></div><div className="schedule-compare-grid">{result.results.map((item) => <article className="schedule-algorithm" key={item.baseline_id}><div className="schedule-algorithm-heading"><strong>{item.name}</strong><Code>{item.baseline_id}</Code></div><p>{item.rule_description}</p><div className="schedule-selection"><span>Seçilen iş</span><strong>{item.selected_job_id ?? "—"}</strong><small>{jobSummary(item.selected_job)}</small></div><p className="schedule-reason">{item.selection_reason}</p><div className="schedule-ranking">{item.ranking.map((ranked) => <div className={ranked.rank === 1 ? "ranking-item ranking-selected" : "ranking-item"} key={`${item.baseline_id}-${ranked.job_id}`}><span>#{ranked.rank}</span><strong>{ranked.job_id}</strong><Code>{formatScheduleKey(ranked.priority_value)}</Code></div>)}</div></article>)}</div><details className="demo-details"><summary>Örnek kimliği ve hesaplama ayrıntıları</summary><p><span>Seed </span><Code>{result.instance.seed}</Code></p><p><span>Üretici </span><Code>{result.instance.generator_version}</Code></p><p><span>Config SHA-256 </span><Code>{result.instance.config_sha256}</Code></p></details></> : null}</section>;
}

function QualityPanel({ expire, csrfToken, onTrace }: { expire: () => void; csrfToken: string; onTrace: (value: QualityResponse) => void }) {
  const [result, setResult] = useState<QualityResponse | null>(null); const [message, setMessage] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const run = async () => { setBusy(true); setMessage(null); try { const response = await runQualityExcursion(WORLD_ID, csrfToken, new AbortController().signal); if (response.status === "unauthenticated") return expire(); if (response.status === "error") return setMessage(`Kalite senaryosu çalıştırılamadı: ${response.message}`); setResult(response.value); onTrace(response.value); } catch (error) { setMessage(`Kalite sonucu işlenemedi: ${error instanceof Error ? error.message : "beklenmeyen hata"}`); } finally { setBusy(false); } };
  return <section className="demo-panel demo-panel-wide"><div className="demo-panel-heading"><div><p className="eyebrow">04 / KALİTE SAPMASI</p><h2>Hold ve sevk koruması</h2></div><span className="status-badge status-critical">GERÇEK CORE AKIŞI</span></div><p className="demo-copy">Her çalıştırmada Core sınırında yalnızca Demo Lab’e ait yeni bir lot hazırlanır. Simülatör anomalisi gerçek Core hold, Outbox, NATS, Twin ve ACTIVE_HOLD sevk reddi zincirini tetikler.</p><div className="demo-controls"><div className="demo-context"><span>Dünya</span><Code>DEMO-WORLD</Code></div><div className="demo-context"><span>Lot</span><Code>{result?.lot_id ?? "Her çalıştırmada yeni"}</Code></div><button className="button button-primary" type="button" disabled={busy} onClick={() => void run()}>{busy ? "Olay zinciri bekleniyor…" : "Kalite hatasını tetikle"}</button></div><ResultMessage message={message} />{result ? <><div className="demo-result-grid"><div><span>Senaryo lotu</span><strong>{result.lot_id}</strong></div><div><span>Core hold</span><strong>{result.core.hold.status}</strong></div><div><span>Sevk</span><strong>{result.core.dispatch.status}</strong></div><div><span>Hata kodu</span><strong>{result.core.dispatch.error_code ?? "—"}</strong></div></div><div className="trace-steps"><div className="trace-step done"><strong>Simülatör</strong><span>{result.simulator.event_type}</span><Code>{result.simulator.event_ref}</Code></div><div className="trace-step done"><strong>Core hold</strong><span>{result.core.hold.status}</span><Code>{result.core.hold.command_id}</Code></div><div className="trace-step done"><strong>PostgreSQL / Outbox</strong><span>{result.transport.outbox.publication_status}</span><Code>{result.transport.outbox.outbox_id}</Code></div><div className="trace-step done"><strong>NATS JetStream</strong><span>{result.transport.nats.stream} · bekleyen {result.transport.nats.num_ack_pending}</span><Code>{result.transport.outbox.event_id}</Code></div><div className="trace-step done"><strong>Digital Twin</strong><span>{result.twin.twin_revision?.status ?? "—"}</span><Code>{result.twin.twin_revision?.source_event_id}</Code></div><div className="trace-step critical"><strong>Dispatch</strong><span>{result.core.dispatch.status} · {result.core.dispatch.error_code}</span><Code>{result.core.dispatch.command_id}</Code></div></div><details className="demo-details"><summary>Kalite zinciri teknik kimlikleri</summary><p><span>Correlation </span><Code>{result.correlation_id}</Code></p><p><span>Simülatör digest </span><Code>{result.simulator.event_sequence_digest}</Code></p><p><span>Twin source event </span><Code>{result.twin.twin_revision?.source_event_id}</Code></p></details></> : null}</section>;
}

function TracePanel({ expire, lotId, refreshKey, onRefresh }: { expire: () => void; lotId: string | null; refreshKey: number; onRefresh: () => void }) {
  const [trace, setTrace] = useState<TraceResponse | null>(null); const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { if (!lotId) { setTrace(null); return; } const controller = new AbortController(); setMessage(null); void fetchTrace(WORLD_ID, lotId, controller.signal).then((response) => { if (response.status === "unauthenticated") return expire(); if (response.status === "error") return setMessage(response.message); if (response.status === "ok") setTrace(response.value); }); return () => controller.abort(); }, [expire, lotId, refreshKey]);
  return <section className="demo-panel demo-panel-wide"><div className="demo-panel-heading"><div><p className="eyebrow">05 / OLAY İZİ</p><h2>Gerçek olay kanıt zinciri</h2></div><button className="button button-secondary" type="button" disabled={!lotId} onClick={onRefresh}>Yenile</button></div><p className="demo-copy">Kalite senaryosunun kayıtları lot kimliğiyle izole edilir: Core → PostgreSQL Outbox → NATS JetStream → Digital Twin.</p><ResultMessage message={message} />{trace ? <><div className="demo-result-grid"><div><span>Lot hold</span><strong>{trace.core_state?.held ? "ACTIVE" : "YOK"}</strong></div><div><span>Twin</span><strong>{trace.twin.revision?.status ?? "—"}</strong></div><div><span>NATS bekleyen</span><strong>{trace.nats.num_ack_pending ?? "—"}</strong></div><div><span>Redelivery</span><strong>{trace.nats.num_redelivered ?? "—"}</strong></div></div><div className="trace-identities">{Object.entries(trace.identities).filter(([, value]) => value).map(([key, value]) => <div key={key}><span>{key}</span><Code>{value}</Code></div>)}</div><div className="trace-flow">{trace.core_showcase.timeline.map((item) => <div className="trace-flow-item" key={`${item.kind}-${item.identity ?? item.label}`}><span className="trace-flow-dot" /><div><strong>{item.label}</strong><span>{item.status} · {item.source}</span>{item.identity ? <Code>{item.identity}</Code> : null}</div></div>)}</div></> : <div className="demo-empty">{lotId ? "Olay izi okunuyor…" : "Önce kalite senaryosunu çalıştırın; yeni lotun kanıt zinciri burada görünecek."}</div>}</section>;
}

export function DemoLabPage() {
  const session = useSession(); const { expire } = useSessionActions(); const [params] = useSearchParams(); const [qualityKey, setQualityKey] = useState(0); const [traceLotId, setTraceLotId] = useState<string | null>(() => params.get("lot_id")?.trim() || null); const expireStable = useMemo(() => expire, [expire]); const csrfToken = session.status === "authenticated" ? session.session.csrf_token : "";
  return <div className="demo-lab-page"><div className="page-heading"><div><p className="eyebrow">SUNUM LAB’I · DEMO-WORLD</p><h1>Demo Lab</h1><p className="page-subtitle">Gerçek servisleri ve algoritmaları tek ekrandan çalıştırın. Her panel sonucu, kimliği ve provenans bilgisini erişilebilir tutar.</p></div><div className="demo-lab-note"><strong>Güvenlik sınırı</strong><span>Tüm işlemler kimlik doğrulamalı BFF üzerinden</span><span>AI/RCA çalışma zamanı: mevcut değil</span></div></div><div className="demo-lab-grid"><VisionPanel expire={expireStable} csrfToken={csrfToken} /><SimulationPanel expire={expireStable} csrfToken={csrfToken} /><SchedulingPanel expire={expireStable} csrfToken={csrfToken} /><QualityPanel expire={expireStable} csrfToken={csrfToken} onTrace={(value) => { setTraceLotId(value.lot_id); setQualityKey((current) => current + 1); }} /><TracePanel expire={expireStable} lotId={traceLotId} refreshKey={qualityKey} onRefresh={() => setQualityKey((value) => value + 1)} /></div></div>;
}
