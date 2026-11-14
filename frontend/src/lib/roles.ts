export interface RoleHomeConfig {
  route: string;
  label: string;
  badge: string;
  description: string;
}

export const ROLE_HOMES: Record<string, RoleHomeConfig> = {
  citizen: {
    route: "/citizen",
    label: "Citizen Safety Portal",
    badge: "Public Safety",
    description: "Live local hazard check, community hazard reporting, and emergency storm shelters.",
  },
  field_officer: {
    route: "/field",
    label: "Field Operations Workspace",
    badge: "Field Ops",
    description: "Inspection task queue, offline ground truth reporting, and road blockage updates.",
  },
  district_admin: {
    route: "/situation-room",
    label: "District Situation Room",
    badge: "DDMA Authority",
    description: "District hazard heatmap, candidate alert sign-off, and rapid team tasking.",
  },
  analyst: {
    route: "/scenarios",
    label: "Scenario Lab & Simulation Engine",
    badge: "Duty Analyst",
    description: "What-if rainfall simulations, deterministic model recalculations, and risk trajectories.",
  },
  researcher: {
    route: "/historical-replay",
    label: "Historical Replay & Geotechnical Science",
    badge: "Science & Research",
    description: "Disaster reconstruction benchmark, runout envelopes, and spatial validation metrics.",
  },
  platform_admin: {
    route: "/admin",
    label: "System Administration & Governance",
    badge: "Platform Admin",
    description: "User management, feature flags, audit trail, and ML model checkpoint lifecycle.",
  },
  state_admin: {
    route: "/situation-room",
    label: "State Emergency Situation Room",
    badge: "SDMA Command",
    description: "Statewide multi-district hazard matrix, alert approval queue, and evacuation directives.",
  },
};

export function getRoleHomeRoute(role?: string): string {
  if (!role) return "/";
  return ROLE_HOMES[role]?.route ?? "/";
}
