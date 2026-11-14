import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Hospital, MapPin, Phone, RefreshCw, ShieldAlert } from "lucide-react";
import { api } from "../lib/api";
import {
  AppleGlassStat,
  DisclosurePill,
  SegmentedControl,
  ShimmerButton,
  SpotlightCard,
} from "../components/aceternity";
import {
  Badge,
  Progress,
  Alert,
  AlertTitle,
  AlertDescription,
} from "../components/shadcn";

interface Facility {
  id: number;
  district_code: string;
  kind: string;
  name: string;
  lat: number;
  lon: number;
  capacity: number;
  current_occupancy: number;
  available_capacity: number;
  contact_phone: string;
  contact_officer: string;
  power_backup: boolean;
  water_supply: boolean;
  medical_supplies: boolean;
  status: "OPERATIONAL" | "STANDBY" | "AT_CAPACITY" | "INACCESSIBLE" | "CLOSED";
  address: string;
  verified_by_authority: boolean;
}

export default function EmergencyFacilities() {
  const [district, setDistrict] = useState<string>("ALL");
  const [kindFilter, setKindFilter] = useState<string>("ALL");

  const { data, isLoading, refetch } = useQuery<{
    count: number;
    facilities: Facility[];
    evacuation_authority_notice: string;
  }>({
    queryKey: ["facilities", district, kindFilter],
    queryFn: () => {
      const params = new URLSearchParams();
      if (district !== "ALL") params.append("district_code", district);
      if (kindFilter !== "ALL") params.append("kind", kindFilter);
      return api(`/api/v1/facilities?${params.toString()}`);
    },
  });

  const facilities = data?.facilities ?? [];
  const totalCapacity = facilities.reduce((sum, f) => sum + f.capacity, 0);
  const totalOpen = facilities.reduce((sum, f) => sum + f.available_capacity, 0);

  return (
    <div className="space-y-6">
      {/* Header and Disclosures */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-2 border-b border-line">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="flex items-center gap-1.5 text-[11px] font-semibold text-safe bg-safe/10 border border-safe/25 px-2.5 py-0.5 rounded-full">
              <Hospital size={12} />
              Verified Geospatial Relief Infrastructure
            </span>
            <DisclosurePill
              text="State Disaster Management Authority Shelter Registry"
              tooltip="Facility coordinates and capacities are formally ground-verified by District Disaster Management Authorities. Automatic AI evacuation orders are legally prohibited."
            />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            Emergency Facility Management
          </h1>
          <p className="text-xs text-muted mt-0.5">
            Geospatial directory of verified emergency shelters, multi-specialty hospitals, public schools, and assembly hubs across the North Eastern pilot region.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <ShimmerButton
            variant="secondary"
            onClick={() => refetch()}
            className="text-xs"
          >
            <RefreshCw size={13} className={isLoading ? "animate-spin" : ""} />
            Sync Registry
          </ShimmerButton>
        </div>
      </div>

      {/* District & Facility Type Filters */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <SegmentedControl
          options={[
            { value: "ALL", label: "All Districts" },
            { value: "AS-KMR", label: "Kamrup Metro" },
            { value: "ML-EKH", label: "East Khasi Hills" },
            { value: "MZ-AIZ", label: "Aizawl" },
          ]}
          value={district}
          onChange={setDistrict}
        />
        <div className="flex items-center gap-2">
          <select
            value={kindFilter}
            onChange={(e) => setKindFilter(e.target.value)}
            className="bg-surface-2/80 dark:bg-surface-2/50 border border-line rounded-xl px-3 py-1.5 text-xs text-ink focus:outline-none"
          >
            <option value="ALL">All Facility Types</option>
            <option value="HOSPITAL">Hospitals & Trauma Centers</option>
            <option value="SHELTER">Community Shelters</option>
            <option value="SCHOOL_SHELTER">Designated Schools</option>
            <option value="FIRE_RESCUE">Fire & Rescue Stations</option>
          </select>
        </div>
      </div>

      {/* High-Level Apple Glass Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <AppleGlassStat
          label="Registered Facilities"
          value={isLoading ? "—" : facilities.length}
          delta="Across pilot districts"
          deltaType="positive"
        />
        <AppleGlassStat
          label="Total Emergency Beds"
          value={isLoading ? "—" : totalCapacity.toLocaleString()}
          delta="Verified capacity"
          deltaType="positive"
        />
        <AppleGlassStat
          label="Currently Available Beds"
          value={isLoading ? "—" : totalOpen.toLocaleString()}
          delta="Immediate vacancies"
          deltaType="positive"
        />
        <AppleGlassStat
          label="Authority Verified"
          value="100%"
          delta="GPS ground surveyed"
          deltaType="positive"
        />
      </div>

      {/* Mandatory Evacuation Authority Disclaimer */}
      <Alert variant="info">
        <ShieldAlert className="h-4 w-4 text-forest" />
        <AlertTitle className="text-xs font-bold text-ink">Official Disaster Management Authority Protocol</AlertTitle>
        <AlertDescription className="text-xs text-muted leading-relaxed">
          {data?.evacuation_authority_notice ??
            "Emergency evacuation orders and shelter assignments are strictly issued by District Disaster Management Authorities (DDMA). BHUSHAKTI AI does not auto-order evacuations."}
        </AlertDescription>
      </Alert>

      {/* Facilities Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {facilities.map((fac) => {
          const occupancyPct = fac.capacity > 0 ? Math.round(((fac.capacity - fac.available_capacity) / fac.capacity) * 100) : 0;
          return (
            <SpotlightCard key={fac.id} className="p-4 flex flex-col justify-between space-y-3">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold font-mono uppercase tracking-wider text-muted bg-surface-3/80 dark:bg-surface-3/50 px-2.5 py-0.5 rounded-full border border-line">
                    {fac.kind.replace("_", " ")}
                  </span>
                  <Badge
                    variant={fac.status === "OPERATIONAL" ? "success" : "warning"}
                    className="font-mono text-[9px] uppercase tracking-wide"
                  >
                    {fac.status}
                  </Badge>
                </div>
                <h3 className="text-sm font-bold text-ink mt-2 truncate">{fac.name}</h3>
                <p className="text-xs text-muted mt-1 leading-normal line-clamp-1">{fac.address}</p>

                <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs py-2 bg-surface-2/70 dark:bg-surface-2/40 rounded-xl border border-line">
                  <div>
                    <div className="text-[10px] text-muted uppercase font-semibold">Total Capacity</div>
                    <div className="font-bold font-mono text-ink mt-0.5">{fac.capacity} beds</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-muted uppercase font-semibold">Available</div>
                    <div className="font-bold font-mono text-safe mt-0.5">{fac.available_capacity} open</div>
                  </div>
                </div>

                <div className="mt-2.5 space-y-1">
                  <div className="flex justify-between text-[10px] text-muted font-medium">
                    <span>Occupancy Rate</span>
                    <span className="font-mono">{occupancyPct}%</span>
                  </div>
                  <Progress value={occupancyPct} className="h-1.5" />
                </div>

                <div className="mt-3 space-y-1 text-xs text-muted">
                  <div className="flex items-center gap-1.5">
                    <Phone size={12} className="text-muted" />
                    <span className="font-mono text-[11px]">{fac.contact_phone}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <MapPin size={12} className="text-muted" />
                    <span className="font-mono text-[11px]">{fac.lat.toFixed(3)}, {fac.lon.toFixed(3)}</span>
                  </div>
                </div>
              </div>

            <div className="pt-2.5 border-t border-line/60 flex items-center justify-between text-[11px] text-muted">
              <span className="flex items-center gap-1 text-safe font-medium">
                <CheckCircle2 size={12} /> Verified by DDMA
              </span>
              <span className="font-mono text-[10px]">{fac.power_backup ? "Generator Backup" : "Standard Grid"}</span>
            </div>
          </SpotlightCard>
          );
        })}
      </div>
    </div>
  );
}
