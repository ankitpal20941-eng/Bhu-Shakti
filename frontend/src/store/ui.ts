import { create } from "zustand";
import { persist } from "zustand/middleware";

export type LayerKey = "risk" | "susceptibility" | "roads" | "assets" | "incidents" | "reports";

interface UiState {
  theme: "light" | "dark";
  lowBandwidth: boolean;
  sidebarOpen: boolean;
  liveStatus: "connecting" | "live" | "paused";
  selectedZoneId: number | null;
  layers: Record<LayerKey, boolean>;
  districtFilter: string;
  riskFilter: string;
  priorityFilter: string;
  search: string;
  setTheme: (theme: "light" | "dark") => void;
  toggleTheme: () => void;
  setLowBandwidth: (value: boolean) => void;
  setSidebarOpen: (value: boolean) => void;
  setLiveStatus: (status: UiState["liveStatus"]) => void;
  selectZone: (id: number | null) => void;
  toggleLayer: (layer: LayerKey) => void;
  setDistrictFilter: (value: string) => void;
  setRiskFilter: (value: string) => void;
  setPriorityFilter: (value: string) => void;
  setSearch: (value: string) => void;
}

export const useUi = create<UiState>()(
  persist(
    (set, get) => ({
      theme: "light",
      lowBandwidth: false,
      sidebarOpen: false,
      liveStatus: "connecting",
      selectedZoneId: null,
      layers: { risk: true, susceptibility: false, roads: true, assets: true, incidents: false, reports: true },
      districtFilter: "",
      riskFilter: "",
      priorityFilter: "",
      search: "",
      setTheme: (theme) => set({ theme }),
      toggleTheme: () => set({ theme: get().theme === "light" ? "dark" : "light" }),
      setLowBandwidth: (lowBandwidth) => set({ lowBandwidth }),
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      setLiveStatus: (liveStatus) => set({ liveStatus }),
      selectZone: (selectedZoneId) => set({ selectedZoneId }),
      toggleLayer: (layer) => set({ layers: { ...get().layers, [layer]: !get().layers[layer] } }),
      setDistrictFilter: (districtFilter) => set({ districtFilter }),
      setRiskFilter: (riskFilter) => set({ riskFilter }),
      setPriorityFilter: (priorityFilter) => set({ priorityFilter }),
      setSearch: (search) => set({ search }),
    }),
    {
      name: "bhushakti-ui",
      partialize: (state) => ({ theme: state.theme, lowBandwidth: state.lowBandwidth, layers: state.layers }),
    },
  ),
);

export function applyTheme(theme: "light" | "dark") {
  document.documentElement.dataset.theme = theme;
}
