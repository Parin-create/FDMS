import { PublicClientApplication } from '@azure/msal-browser';

import { msalConfig } from '@/auth/authConfig';

/**
 * Singleton MSAL application instance.
 *
 * IMPORTANT: this module constructs `PublicClientApplication` on import, which
 * requires a non-empty client id. It must therefore only be imported once auth is
 * known to be configured (see `main.tsx`, which guards and dynamically imports it).
 */
export const msalInstance = new PublicClientApplication(msalConfig);
