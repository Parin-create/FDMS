/**
 * Admin feature module — tenant administration: users, roles, and policies.
 *
 * Healthcare platform module. No business logic yet (Sprint 4.1 scaffolding).
 * Access is restricted to the TenantAdmin role (UI gating only; the backend is
 * the enforcement point).
 * Intended internal structure as this module grows:
 *   api/          typed service functions + zod response schemas
 *   hooks/        TanStack Query hooks (queries/mutations)
 *   components/   module-specific UI
 *   types/        module types (prefer z.infer from schemas)
 *   queryKeys.ts  query-key factory for cache invalidation
 *
 * Re-export this module's public surface from here as it is built.
 */
export {};
