import { InteractionRequiredAuthError } from '@azure/msal-browser';

import { loginRequest } from '@/auth/authConfig';
import { msalInstance } from '@/auth/msal';

/**
 * Acquire an access token for the FDMS API.
 *
 * Attempts silent acquisition first; if interaction is required, falls back to a
 * redirect and returns null for the current call (the page will reload post-auth).
 */
export async function acquireApiToken(): Promise<string | null> {
  const account = msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0];
  if (!account) {
    return null;
  }

  try {
    const result = await msalInstance.acquireTokenSilent({ ...loginRequest, account });
    return result.accessToken;
  } catch (error) {
    if (error instanceof InteractionRequiredAuthError) {
      await msalInstance.acquireTokenRedirect({ ...loginRequest, account });
      return null;
    }
    throw error;
  }
}
