import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Clock, Globe, Radio, RefreshCw } from "lucide-react";
import { api } from "../lib/api";
import {
  AppleGlassStat,
  DisclosurePill,
  SegmentedControl,
  ShimmerButton,
  SpotlightCard,
} from "../components/aceternity";
import { Badge } from "../components/shadcn";

interface NotificationLog {
  id: number;
  alert_id: number;
  channel: string;
  recipient_target: string;
  language: string;
  status: "PENDING" | "PROCESSING" | "DELIVERED" | "FAILED";
  subject: string;
  message_preview: string;
  attempt_count: number;
  provider_ref: string | null;
  provider_confirmed_at: string | null;
  failure_reason?: string;
  escalation_level: number;
}

interface NotificationLogsResponse {
  count: number;
  logs: NotificationLog[];
  multilingual_support: Record<string, { language_name: string; headline: string; instructions: string }>;
  rule?: string;
}

export default function NotificationMonitor() {
  const [selectedLanguage, setSelectedLanguage] = useState<string>("as");

  const { data, isLoading, refetch } = useQuery<NotificationLogsResponse>({
    queryKey: ["notification-logs"],
    queryFn: () => api("/api/v1/notifications/logs"),
    refetchInterval: 15_000,
  });

  const logs = data?.logs ?? [];
  const delivered = logs.filter((l) => l.status === "DELIVERED").length;

  return (
    <div className="space-y-6">
      {/* Header and Disclosures */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-2 border-b border-line">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="flex items-center gap-1.5 text-[11px] font-semibold text-forest bg-forest-soft border border-forest/25 px-2.5 py-0.5 rounded-full">
              <Radio size={12} className="animate-pulse" />
              Cell-Broadcast & Push Pipeline
            </span>
            <DisclosurePill
              text="Tamper-Evident Carrier Delivery Receipts"
              tooltip="A notification is never recorded as DELIVERED based solely on API submission. Real carrier SMPP / FCM delivery receipts are required to confirm delivery."
            />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            Notification Delivery Monitor
          </h1>
          <p className="text-xs text-muted mt-0.5">
            Emergency broadcast distribution pipeline: multi-carrier SMS, mobile push, and local language localization with tamper-evident carrier delivery confirmations.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <ShimmerButton
            variant="secondary"
            onClick={() => refetch()}
            className="text-xs"
          >
            <RefreshCw size={13} className={isLoading ? "animate-spin" : ""} />
            Poll Gateway
          </ShimmerButton>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <AppleGlassStat
          label="Total Broadcasts"
          value={isLoading ? "—" : logs.length}
          delta="Queued & dispatched"
          deltaType="positive"
        />
        <AppleGlassStat
          label="Verified Delivered"
          value={isLoading ? "—" : delivered}
          delta="Carrier receipt verified"
          deltaType="positive"
        />
        <AppleGlassStat
          label="Multi-Lingual Coverage"
          value="4 Languages"
          delta="Assamese, Khasi, Mizo, EN"
          deltaType="positive"
        />
        <AppleGlassStat
          label="Offline Fallback"
          value="Cached"
          delta="Service worker ready"
          deltaType="positive"
        />
      </div>

      {/* Multilingual Template Previewer */}
      <SpotlightCard>
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-forest-soft text-forest">
              <Globe size={16} />
            </div>
            <div>
              <h3 className="font-bold text-xs uppercase tracking-wider text-ink">
                Localized Regional Emergency Language Templates
              </h3>
              <p className="text-[11px] text-muted">
                Pre-authorized public early warning broadcasts in native vernacular scripts
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <SegmentedControl
            options={[
              { value: "as", label: "Assamese (অসমীয়া)" },
              { value: "kha", label: "Khasi (Ka Ktien Khasi)" },
              { value: "miz", label: "Mizo (Mizo ṭawng)" },
              { value: "en", label: "English" },
            ]}
            value={selectedLanguage}
            onChange={setSelectedLanguage}
          />

          {data?.multilingual_support[selectedLanguage] ? (
            <div className="p-4 bg-surface-2/70 dark:bg-surface-2/40 border border-line rounded-2xl space-y-2 text-xs">
              <div className="text-[10px] font-bold text-forest uppercase tracking-wider">
                {data.multilingual_support[selectedLanguage].language_name} Emergency Payload
              </div>
              <h3 className="text-sm font-bold text-ink">
                {data.multilingual_support[selectedLanguage].headline}
              </h3>
              <p className="text-muted leading-relaxed font-medium">
                {data.multilingual_support[selectedLanguage].instructions}
              </p>
            </div>
          ) : null}
        </div>
      </SpotlightCard>

      {/* Active Gateway Transmissions Table */}
      <SpotlightCard>
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-forest-soft text-forest">
              <Radio size={16} />
            </div>
            <div>
              <h3 className="font-bold text-xs uppercase tracking-wider text-ink">
                Emergency Broadcast Gateway Transmissions
              </h3>
              <p className="text-[11px] text-muted">
                Live delivery receipts from telecom providers (Airtel, BSNL, Jio, FCM)
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          {logs.length === 0 ? (
            <div className="text-center py-8 text-xs text-muted">
              No transmission logs recorded in this session.
            </div>
          ) : (
            logs.map((log) => (
              <div
                key={log.id}
                className="p-4 bg-surface-2/70 dark:bg-surface-2/40 border border-line rounded-2xl flex flex-wrap items-center justify-between gap-4 text-xs hover:border-forest/40 transition duration-200"
              >
                <div className="min-w-0 max-w-lg space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-ink">
                      #{log.id} • {log.channel}
                    </span>
                    <Badge
                      variant={
                        log.status === "DELIVERED"
                          ? "success"
                          : log.status === "PROCESSING"
                          ? "default"
                          : log.status === "PENDING"
                          ? "warning"
                          : "destructive"
                      }
                    >
                      {log.status}
                    </Badge>
                    <span className="text-[10px] text-muted uppercase font-mono">
                      Lang: {log.language}
                    </span>
                  </div>
                  <div className="font-semibold text-ink">{log.subject}</div>
                  <p className="text-muted text-[11px] truncate">{log.message_preview}</p>
                  <div className="text-[10px] text-muted font-mono">
                    Target: <span className="text-ink font-semibold">{log.recipient_target}</span>
                  </div>
                </div>

                <div className="text-right shrink-0 space-y-1">
                  <div className="text-[10px] text-muted font-mono">Provider Ref:</div>
                  <div className="font-mono text-[11px] text-ink font-semibold">
                    {log.provider_ref ?? "Awaiting Gateway Confirmation"}
                  </div>
                  {log.provider_confirmed_at ? (
                    <div className="text-[10px] text-safe flex items-center justify-end gap-1 font-semibold">
                      <CheckCircle2 size={12} /> Confirmed Delivered
                    </div>
                  ) : log.status === "FAILED" ? (
                    <div className="text-[10px] text-critical flex items-center justify-end gap-1 font-semibold">
                      <AlertCircle size={12} /> {log.failure_reason ?? "Transmission Failed"}
                    </div>
                  ) : (
                    <div className="text-[10px] text-warning flex items-center justify-end gap-1 font-semibold">
                      <Clock size={12} /> Carrier In-Flight
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </SpotlightCard>
    </div>
  );
}
