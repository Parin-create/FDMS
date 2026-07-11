import { z } from 'zod';

import { apiClient } from '@/lib/api';

/** Schema mirroring the backend `ReadinessResponse` (validated at runtime). */
const readinessSchema = z.object({
  status: z.enum(['ready', 'degraded']),
  database: z.enum(['ok', 'error']),
});

export type Readiness = z.infer<typeof readinessSchema>;

/** Query the backend readiness endpoint and validate the response shape. */
export async function fetchReadiness(): Promise<Readiness> {
  const data = await apiClient.get<unknown>('/health/ready');
  return readinessSchema.parse(data);
}

export const healthQueryKeys = {
  readiness: ['health', 'readiness'] as const,
};
