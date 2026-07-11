import { z } from 'zod';

/**
 * Runtime environment configuration, validated at startup.
 *
 * Vite exposes only variables prefixed with `VITE_`. Validating with Zod gives us
 * a single, type-safe source of truth and fails fast on misconfiguration.
 */
const envSchema = z.object({
  VITE_API_BASE_URL: z.string().min(1).default('/api/v1'),
  VITE_APP_NAME: z.string().min(1).default('FDMS'),
  // Microsoft Entra ID (MSAL). Empty client id => auth not configured.
  VITE_ENTRA_CLIENT_ID: z.string().default(''),
  VITE_ENTRA_TENANT_ID: z.string().default('organizations'),
  VITE_ENTRA_REDIRECT_URI: z.string().default(''),
  VITE_ENTRA_API_SCOPE: z.string().default(''),
});

const parsed = envSchema.safeParse(import.meta.env);

if (!parsed.success) {
  // Surface a clear message rather than failing deep inside the app.
  console.error('Invalid environment configuration:', parsed.error.flatten().fieldErrors);
  throw new Error('Invalid environment configuration. See console for details.');
}

export const env = {
  apiBaseUrl: parsed.data.VITE_API_BASE_URL,
  appName: parsed.data.VITE_APP_NAME,
  entraClientId: parsed.data.VITE_ENTRA_CLIENT_ID,
  entraTenantId: parsed.data.VITE_ENTRA_TENANT_ID,
  entraRedirectUri: parsed.data.VITE_ENTRA_REDIRECT_URI,
  entraApiScope: parsed.data.VITE_ENTRA_API_SCOPE,
} as const;
