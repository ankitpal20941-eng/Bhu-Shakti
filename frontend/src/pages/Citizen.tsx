import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle, ArrowLeft, CheckCircle2, ClipboardCheck, Crosshair, Languages, MapPin, Phone, Send, LogOut,
} from "lucide-react";
import clsx from "clsx";
import { api } from "../lib/api";
import { fmtDateTime } from "../lib/format";
import { LANGUAGES, t, type Lang } from "../lib/i18n";
import { RiskBadge, StateBadge, toast } from "../components/ui";
import { useSession } from "../store/session";
import { BhuShaktiLogoMark } from "../components/BhuShaktiLogo";

interface PublicConfig {
  app_name: string;
  mode: string;
  disclaimer: string;
  languages: string[];
  reviewed_languages: string[];
  districts: Array<{ code: string; name: string; state: string; lat: number; lon: number; boundary_note: string }>;
  data_attribution: Array<{ source: string; provider: string; attribution: string; state: string }>;
  features: { public_alerts: boolean };
}

interface PublicRisk {
  location: { lat: number; lon: number; nearest_unit: string; distance_km: number; district: string | null; state: string | null };
  risk_level: "SAFE" | "WATCH" | "WARNING" | "CRITICAL";
  risk_label: string;
  plain_reason: string;
  updated_at: string;
  observation_time: string | null;
  data_state: "LIVE" | "CACHED" | "STALE" | "DEGRADED" | "UNAVAILABLE" | "SIMULATED";
  official_advisory: {
    active: boolean;
    count: number;
    latest: { reference: string; headline: string; approved_at: string | null; expires: string; instructions: string } | null;
    note: string;
  };
  safety_instructions: string;
  language: string;
  language_reviewed: boolean;
  nearest_hospital: { name: string; distance_km: number; note: string } | null;
  disclaimer: string;
  can_report: boolean;
}

const HAZARDS = [
  ["GROUND_CRACK", "Cracks in the ground"],
  ["SLOPE_MOVEMENT", "Slope moving"],
  ["ROCKFALL", "Falling rocks"],
  ["ROAD_BLOCKAGE", "Road blocked"],
  ["DEBRIS_FLOW", "Mud / debris flow"],
  ["SUBSIDENCE", "Ground sinking"],
  ["OTHER", "Something else"],
];

const levelTone: Record<PublicRisk["risk_level"], string> = {
  SAFE: "border-safe/40 bg-safe/5",
  WATCH: "border-watch/40 bg-watch/5",
  WARNING: "border-warning/40 bg-warning/5",
  CRITICAL: "border-critical/40 bg-critical/5",
};

export default function Citizen() {
  const { user, clear } = useSession();
  const [lang, setLang] = useState<Lang>("en");
  const [lat, setLat] = useState<number | null>(null);
  const [lon, setLon] = useState<number | null>(null);
  const [districtCode, setDistrictCode] = useState("");
  const [result, setResult] = useState<PublicRisk | null>(null);
  const [checking, setChecking] = useState(false);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showReport, setShowReport] = useState(false);
  const [hazard, setHazard] = useState("GROUND_CRACK");
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [reportState, setReportState] = useState<{ id: number; status: string; duplicate: boolean } | null>(null);

  const strings = t(lang);
  const config = useQuery({ queryKey: ["public-config"], queryFn: () => api<PublicConfig>("/api/v1/public/config"), staleTime: 600_000 });

  const check = async (queryLat: number, queryLon: number) => {
    setChecking(true);
    setError(null);
    try {
      const data = await api<PublicRisk>(`/api/v1/public/risk?lat=${queryLat}&lon=${queryLon}&lang=${lang}`);
      setResult(data);
    } catch (caught) {
      setResult(null);
      setError(caught instanceof Error ? caught.message : "Could not check this location");
    } finally {
      setChecking(false);
    }
  };

  const locate = () => {
    setError(null);
    if (!navigator.geolocation) { setError("This browser cannot access your location. Choose a district instead."); return; }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLat(position.coords.latitude);
        setLon(position.coords.longitude);
        setLocating(false);
        check(position.coords.latitude, position.coords.longitude);
      },
      (geoError) => { setLocating(false); setError(`${geoError.message} You can choose a district centre instead.`); },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 },
    );
  };

  const chooseDistrict = async (code: string) => {
    setDistrictCode(code);
    const district = config.data?.districts.find((item) => item.code === code);
    if (district) {
      setLat(district.lat);
      setLon(district.lon);
      await check(district.lat, district.lon);
    }
  };

  const submitReport = async () => {
    if (!consent) { toast(strings.consent, "error"); return; }
    setReporting(true);
    try {
      const form = new FormData();
      form.append("hazard_type", hazard);
      form.append("description", description);
      if (lat !== null && lon !== null) { form.append("lat", String(lat)); form.append("lon", String(lon)); }
      form.append("consent", "true");
      form.append("client_uuid", crypto.randomUUID());
      if (photo) form.append("files", photo);
      const data = await api<{ report: { id: number; status: string }; duplicate: boolean }>("/api/v1/public/reports", { method: "POST", body: form });
      setReportState({ id: data.report.id, status: data.report.status, duplicate: data.duplicate });
      setDescription("");
      setPhoto(null);
      setConsent(false);
    } catch (caught) {
      toast(caught instanceof Error ? caught.message : "Could not send the report", "error");
    } finally {
      setReporting(false);
    }
  };

  const reviewed = lang === "en";

  return (
    <div className="min-h-screen bg-canvas">
      <header className="bg-gradient-to-br from-forest to-forest-deep px-4 py-10 text-white">
        <div className="mx-auto flex max-w-3xl flex-col gap-4">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <BhuShaktiLogoMark size={32} className="shadow-md shadow-black/20" />
              <div className="flex items-center gap-1.5 leading-none">
                <span className="text-sm font-bold tracking-tight text-white font-heading">BHUSHAKTI</span>
                <span className="bg-white/20 border border-white/30 text-white text-[9px] font-black px-1.5 py-0.5 rounded-md tracking-wider">AI</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <label htmlFor="lang" className="sr-only">Language</label>
              <select id="lang" className="rounded-md border border-white/25 bg-white/10 px-2 py-1 text-xs text-white" value={lang} onChange={(event) => setLang(event.target.value as Lang)}>
                {LANGUAGES.map((item) => <option key={item.code} value={item.code} className="text-ink">{item.label}</option>)}
              </select>
            </div>
          </div>
          {user ? (
            <div className="flex items-center justify-between gap-3 p-2.5 rounded-xl bg-white/10 border border-white/20 text-xs">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>Signed in as <strong>{user.email}</strong> ({user.role})</span>
              </div>
              <button
                onClick={() => {
                  clear();
                  window.location.href = "/login";
                }}
                className="px-2.5 py-1 rounded-lg bg-white/15 hover:bg-white/25 text-white transition flex items-center gap-1.5 text-xs font-medium"
              >
                <LogOut size={12} /> Switch to Authority Account
              </button>
            </div>
          ) : null}
          <div>
            <h1 className="text-2xl font-semibold sm:text-3xl">{strings.title}</h1>
            <p className="mt-1 max-w-xl text-sm text-white/80">{strings.subtitle}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button className="btn bg-white text-forest hover:bg-white/90" onClick={locate} disabled={locating || checking}>
              <Crosshair size={16} /> {locating ? "Locating…" : strings.useLocation}
            </button>
            <span className="text-2xs text-white/70">or</span>
            <select
              className="rounded-md border border-white/25 bg-white/10 px-2 py-2 text-sm text-white"
              value={districtCode}
              onChange={(event) => chooseDistrict(event.target.value)}
              aria-label={strings.chooseDistrict}
            >
              <option value="" className="text-ink">{strings.chooseDistrict}</option>
              {(config.data?.districts ?? []).map((district) => (
                <option key={district.code} value={district.code} className="text-ink">{district.name}, {district.state}</option>
              ))}
            </select>
          </div>
          <p className="rounded-md border border-white/20 bg-white/5 px-2.5 py-1.5 text-2xs text-white/75">
            This pilot covers three districts only. Results are for a ~2 km planning unit, not a house-level prediction.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-3 px-4 py-5">
        {!reviewed ? (
          <div className="rounded-lg border border-watch/40 bg-watch/5 px-3 py-2 text-xs text-watch">
            <Languages size={13} className="mr-1 inline" /> This translation has not been reviewed by a native speaker yet. The English advisory is authoritative.
          </div>
        ) : null}

        {checking ? <div className="card px-4 py-6 text-sm text-muted">{strings.checking}</div> : null}
        {error ? (
          <div className="rounded-lg border border-critical/40 bg-critical/5 px-3 py-2 text-sm" role="alert">
            <AlertTriangle size={14} className="mr-1 inline text-critical" /> {error}
          </div>
        ) : null}

        {result ? (
          <>
            <section className={clsx("card overflow-hidden border-2", levelTone[result.risk_level])}>
              <div className="px-4 py-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="text-2xs uppercase tracking-wide text-muted">{strings.riskHere}</div>
                    <h2 className="mt-1 text-xl font-semibold">{result.risk_label}</h2>
                  </div>
                  <RiskBadge level={result.risk_level} size="lg" />
                </div>
                <p className="mt-2 text-sm leading-relaxed">{result.plain_reason}</p>
                <div className="mt-3 flex flex-wrap items-center gap-1.5 text-2xs text-muted">
                  <span className="chip"><MapPin size={11} /> {result.location.nearest_unit}</span>
                  <span className="chip">{result.location.district}</span>
                  <StateBadge state={result.data_state} />
                  <span className="chip">{strings.updated} {fmtDateTime(result.updated_at)}</span>
                </div>
              </div>
            </section>

            <section className="card px-4 py-3">
              <div className="flex items-center gap-1.5 text-sm font-semibold"><ClipboardCheck size={15} /> {strings.officialAdvisory}</div>
              {result.official_advisory.active && result.official_advisory.latest ? (
                <div className="mt-2 rounded-lg border border-critical/30 bg-critical/5 p-3">
                  <div className="text-sm font-semibold">{result.official_advisory.latest.headline}</div>
                  <p className="mt-1 whitespace-pre-line text-xs leading-relaxed">{result.official_advisory.latest.instructions}</p>
                  <div className="mt-1 text-2xs text-muted">
                    {result.official_advisory.latest.reference} · approved {fmtDateTime(result.official_advisory.latest.approved_at)} · valid until {fmtDateTime(result.official_advisory.latest.expires)}
                  </div>
                </div>
              ) : (
                <p className="mt-1 text-xs text-muted">{strings.noAdvisory} {result.official_advisory.note}</p>
              )}
            </section>

            <section className="card px-4 py-3">
              <div className="flex items-center gap-1.5 text-sm font-semibold"><AlertTriangle size={15} /> {strings.safety}</div>
              <p className="mt-1 text-sm leading-relaxed">{result.safety_instructions}</p>
              {result.nearest_hospital ? (
                <p className="mt-2 text-xs text-muted">
                  Nearest hospital in the reference dataset: <b>{result.nearest_hospital.name}</b> ({result.nearest_hospital.distance_km} km straight line). {result.nearest_hospital.note}
                </p>
              ) : null}
              <a className="btn btn-danger mt-2" href="tel:112"><Phone size={14} /> {strings.emergency}</a>
            </section>

            {config.data?.features.public_alerts ? (
              <div className="card px-4 py-3 text-xs text-muted">
                Public advisory feed is enabled for approved advisories only. Pending candidates are never published.
              </div>
            ) : null}

            <button className="btn w-full" onClick={() => setShowReport((value) => !value)}>
              <Send size={14} /> {strings.reportHazard}
            </button>
          </>
        ) : null}

        {showReport ? (
          <section className="card px-4 py-3">
            <h2 className="text-sm font-semibold">{strings.reportHazard}</h2>
            {reportState ? (
              <div className="mt-2 rounded-lg border border-safe/40 bg-safe/5 p-3 text-sm">
                <div className="flex items-center gap-1.5 font-semibold text-safe"><CheckCircle2 size={15} /> {strings.submitted}</div>
                <p className="mt-1 text-xs text-muted">
                  Reference #{reportState.id} · <b>{reportState.status.replaceAll("_", " ")}</b>
                  {reportState.duplicate ? " · this report was already received (duplicate)" : ""}
                </p>
                <p className="mt-1 text-2xs text-muted">
                  An officer must verify it before it can influence any warning. You will not receive a personal reply.
                </p>
                <button className="btn btn-sm mt-2" onClick={() => { setReportState(null); setShowReport(false); }}>Close</button>
              </div>
            ) : (
              <div className="mt-2 space-y-2">
                <div>
                  <label className="label" htmlFor="cit-hazard">{strings.hazardType}</label>
                  <select id="cit-hazard" className="select" value={hazard} onChange={(event) => setHazard(event.target.value)}>
                    {HAZARDS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label" htmlFor="cit-desc">{strings.describe}</label>
                  <textarea id="cit-desc" className="textarea" rows={3} value={description} onChange={(event) => setDescription(event.target.value)} maxLength={1000} />
                </div>
                <label className="btn btn-sm cursor-pointer">
                  {photo ? photo.name.slice(0, 28) : strings.addPhoto}
                  <input type="file" accept="image/*" capture="environment" className="hidden" onChange={(event) => setPhoto(event.target.files?.[0] ?? null)} />
                </label>
                <label className="flex items-start gap-2 text-xs">
                  <input type="checkbox" className="mt-0.5" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
                  {strings.consent}
                </label>
                <button className="btn btn-primary w-full" onClick={submitReport} disabled={reporting || !consent}>
                  <Send size={14} /> {reporting ? strings.submitting : strings.submit}
                </button>
                <p className="hint">Rate limited to 5 reports per minute per network. No account needed.</p>
              </div>
            )}
          </section>
        ) : null}

        <footer className="space-y-2 border-t border-line pt-3 text-2xs text-muted">
          <p>{result?.disclaimer ?? config.data?.disclaimer ?? strings.disclaimer}</p>
          <p>
            Data: {(config.data?.data_attribution ?? []).map((item) => `${item.source} (${item.state})`).join(" · ")}.
            Basemap © OpenStreetMap contributors. This page is decision support, not an official warning.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <a className="underline" href="/login"><ArrowLeft size={11} className="inline" /> Authority sign-in</a>
            <span>·</span>
            <span>Platform: Operational</span>
          </div>
        </footer>
      </main>
    </div>
  );
}
