import { LogLevel, type Configuration, type RedirectRequest } from '@azure/msal-browser';

import { env } from '@/config/env';

/** True when the Entra client id is present (auth can be initialized). */
export const authConfigured = env.entraClientId.length > 0;

/** API scope(s) requested to obtain an access token for the FDMS backend. */
export const apiScopes = env.entraApiScope.length > 0 ? [env.entraApiScope] : [];

const redirectUri =
  env.entraRedirectUri.length > 0 ? env.entraRedirectUri : window.location.origin;

/** MSAL browser configuration (Authorization Code + PKCE, per ADR-005). */
export const msalConfig: Configuration = {
  auth: {
    clientId: env.entraClientId,
    authority: `https://login.microsoftonline.com/${env.entraTenantId || 'organizations'}`,
    redirectUri,
    postLogoutRedirectUri: redirectUri,
    navigateToLoginRequestUrl: true,
  },
  cache: {
    cacheLocation: 'localStorage',
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      logLevel: LogLevel.Warning,
      piiLoggingEnabled: false,
      loggerCallback: (level, message) => {
        if (level === LogLevel.Error) {
          console.error(message);
        }
      },
    },
  },
};

/** Scopes requested at login / token acquisition. */
export const loginRequest: RedirectRequest = {
  scopes: apiScopes.length > 0 ? apiScopes : ['openid', 'profile', 'email'],
};
