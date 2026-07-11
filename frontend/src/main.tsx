import { StrictMode } from 'react';
import { createRoot, type Root } from 'react-dom/client';

import { authConfigured } from '@/auth/authConfig';
import { AuthNotConfigured } from '@/pages/AuthNotConfigured';

import '@/index.css';

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Root element "#root" not found in document.');
}

const root = createRoot(rootElement);

if (!authConfigured) {
  // App can still start; show clear guidance instead of crashing on MSAL init.
  root.render(
    <StrictMode>
      <AuthNotConfigured />
    </StrictMode>,
  );
} else {
  void bootstrap(root);
}

/**
 * Initialize MSAL, wire up token-aware API calls, and render the app.
 * MSAL v3 requires `initialize()` to be awaited before the instance is used.
 */
async function bootstrap(root: Root): Promise<void> {
  const [{ msalInstance }, { acquireApiToken }, { registerTokenProvider }, { App }, msalBrowser] =
    await Promise.all([
      import('@/auth/msal'),
      import('@/auth/tokens'),
      import('@/lib/api'),
      import('@/App'),
      import('@azure/msal-browser'),
    ]);

  await msalInstance.initialize();

  // Maintain an active account so silent token acquisition works across reloads.
  const accounts = msalInstance.getAllAccounts();
  if (accounts.length > 0 && !msalInstance.getActiveAccount()) {
    msalInstance.setActiveAccount(accounts[0] ?? null);
  }

  msalInstance.addEventCallback((event) => {
    if (
      event.eventType === msalBrowser.EventType.LOGIN_SUCCESS &&
      event.payload &&
      'account' in event.payload &&
      event.payload.account
    ) {
      msalInstance.setActiveAccount(event.payload.account);
    }
  });

  registerTokenProvider(acquireApiToken);

  root.render(
    <StrictMode>
      <App msalInstance={msalInstance} />
    </StrictMode>,
  );
}
