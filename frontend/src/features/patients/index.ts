/**
 * Patients feature module — patient records and demographics.
 *
 * Healthcare platform module. No business logic yet (Sprint 4.1 scaffolding).
 * Handles Protected Health Information (PHI): PHI must never be logged and must
 * follow the platform's least-privilege and audit conventions.
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
