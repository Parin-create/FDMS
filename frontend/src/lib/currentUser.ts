import { z } from 'zod';

import { apiClient } from '@/lib/api';

/** Schema mirroring the backend `CurrentUserResponse` (validated at runtime). */
const currentUserSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  tenant_name: z.string(),
  email: z.string(),
  display_name: z.string(),
  role: z.string(),
  is_active: z.boolean(),
});

export type CurrentUser = z.infer<typeof currentUserSchema>;

/** Fetch the authenticated, provisioned FDMS user from the backend. */
export async function fetchCurrentUser(): Promise<CurrentUser> {
  const data = await apiClient.get<unknown>('/auth/me');
  return currentUserSchema.parse(data);
}

export const authQueryKeys = {
  me: ['auth', 'me'] as const,
};
