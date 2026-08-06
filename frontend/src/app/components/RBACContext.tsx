"use client";

/**
 * RBACContext — Role-Based Access Control (FR-7.1)
 *
 * Roles (aligned to PRD FR-7.1):
 *  - associate          : intake, generate, view results
 *  - reviewer           : + approve/flag/reject, correction form
 *  - compliance_officer : + full audit log read, all review actions
 *  - admin              : all of the above + admin dashboard, user management
 *
 * Role source (in priority order):
 *  1. AuthContext.profile.role — real Supabase-sourced role (when logged in)
 *  2. localStorage "sententia_role" — dev/demo mode switcher fallback
 *
 * The role-switcher in NavigationBar is shown ONLY when Supabase is not
 * configured (i.e., profile is null). Once a user is authenticated, their
 * role is immutable from the nav — only a Supabase admin can change it.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

export type Role = "associate" | "reviewer" | "compliance_officer" | "admin";

interface RBACContextValue {
  role: Role;
  setRole: (role: Role) => void;  // only available in dev/demo mode
  can: (permission: Permission) => boolean;
  isDevMode: boolean;             // true when using localStorage stub
}

type Permission =
  | "intake:submit"
  | "structures:generate"
  | "compliance:evaluate"
  | "review:read"
  | "review:write"
  | "audit:read"
  | "admin:read";

const PERMISSIONS: Record<Role, Permission[]> = {
  associate: [
    "intake:submit", "structures:generate", "compliance:evaluate",
  ],
  reviewer: [
    "intake:submit", "structures:generate", "compliance:evaluate",
    "review:read", "review:write",
  ],
  compliance_officer: [
    "intake:submit", "structures:generate", "compliance:evaluate",
    "review:read", "review:write", "audit:read",
  ],
  admin: [
    "intake:submit", "structures:generate", "compliance:evaluate",
    "review:read", "review:write", "audit:read", "admin:read",
  ],
};

const RBACContext = createContext<RBACContextValue>({
  role: "associate",
  setRole: () => {},
  can: () => false,
  isDevMode: true,
});

const STORAGE_KEY = "sententia_role";

export function RBACProvider({ children }: { children: React.ReactNode }) {
  const [devRole, setDevRoleState] = useState<Role>("associate");
  const [profileRole, setProfileRole] = useState<Role | null>(null);

  // Hydrate dev role from localStorage
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as Role | null;
    if (stored && stored in PERMISSIONS) setDevRoleState(stored);
  }, []);

  // Sync profile role from AuthContext if available
  useEffect(() => {
    // Dynamically import to avoid circular dep — AuthContext is a sibling
    let unsub: (() => void) | null = null;
    try {
      // We read from a window event dispatched by AuthContext on profile load
      const handler = (e: Event) => {
        const role = (e as CustomEvent<{ role: Role }>).detail?.role;
        if (role && role in PERMISSIONS) setProfileRole(role);
      };
      window.addEventListener("sententia:profile", handler);
      unsub = () => window.removeEventListener("sententia:profile", handler);
    } catch {
      // SSR — no window
    }
    return () => unsub?.();
  }, []);

  const role: Role = profileRole ?? devRole;
  const isDevMode = profileRole === null;

  const setRole = useCallback((r: Role) => {
    if (!isDevMode) return; // Can't override a real profile role
    setDevRoleState(r);
    localStorage.setItem(STORAGE_KEY, r);
  }, [isDevMode]);

  const can = useCallback(
    (permission: Permission) => PERMISSIONS[role].includes(permission),
    [role]
  );

  return (
    <RBACContext.Provider value={{ role, setRole, can, isDevMode }}>
      {children}
    </RBACContext.Provider>
  );
}

export function useRole(): RBACContextValue {
  return useContext(RBACContext);
}

/** Compact role badge */
export function RoleBadge({ role }: { role: Role }) {
  const cfg: Record<Role, { label: string; color: string; bg: string }> = {
    associate:           { label: "Associate",           color: "#94a3b8", bg: "rgba(148,163,184,0.1)" },
    reviewer:            { label: "Reviewer",            color: "#818cf8", bg: "rgba(129,140,248,0.12)" },
    compliance_officer:  { label: "Compliance Officer",  color: "#34d399", bg: "rgba(52,211,153,0.1)"  },
    admin:               { label: "Admin",               color: "#f59e0b", bg: "rgba(245,158,11,0.12)" },
  };
  const { label, color, bg } = cfg[role] ?? cfg.associate;
  return (
    <span
      className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold"
      style={{ background: bg, color }}
    >
      {label}
    </span>
  );
}
