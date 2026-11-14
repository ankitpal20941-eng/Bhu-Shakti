import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "../lib/types";

interface SessionState {
  token: string | null;
  user: User | null;
  permissions: string[];
  setSession: (token: string, user: User, permissions: string[]) => void;
  clear: () => void;
  has: (permission: string) => boolean;
  canAccessDistrict: (districtCode: string | null | undefined) => boolean;
}

export const useSession = create<SessionState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      permissions: [],
      setSession: (token, user, permissions) => set({ token, user, permissions }),
      clear: () => set({ token: null, user: null, permissions: [] }),
      has: (permission) => get().permissions.includes(permission),
      canAccessDistrict: (districtCode) => {
        const { user } = get();
        if (!user) return false;
        if (user.statewide || user.role === "citizen") return true;
        if (!districtCode) return true;
        return user.districts.includes(districtCode);
      },
    }),
    { name: "bhushakti-session", partialize: (state) => ({ token: state.token, user: state.user, permissions: state.permissions }) },
  ),
);
