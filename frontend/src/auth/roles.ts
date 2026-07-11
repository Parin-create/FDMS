/**
 * Frontend mirror of the RBAC role names and hierarchy.
 *
 * Used for UI gating and display only — the backend remains the source of truth
 * and the sole enforcement point. These constants avoid magic strings in the UI.
 */
export const RoleName = {
  TenantAdmin: 'TenantAdmin',
  Manager: 'Manager',
  Contributor: 'Contributor',
  Viewer: 'Viewer',
  Guest: 'Guest',
} as const;

export type RoleName = (typeof RoleName)[keyof typeof RoleName];

const ROLE_RANK: Record<RoleName, number> = {
  Guest: 0,
  Viewer: 1,
  Contributor: 2,
  Manager: 3,
  TenantAdmin: 4,
};

/** True when `role` meets or exceeds `minimum` in the hierarchy. */
export function roleAtLeast(role: string, minimum: RoleName): boolean {
  const current = ROLE_RANK[role as RoleName];
  if (current === undefined) {
    return false;
  }
  return current >= ROLE_RANK[minimum];
}
