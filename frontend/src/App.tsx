import { type IPublicClientApplication } from '@azure/msal-browser';
import { MsalProvider } from '@azure/msal-react';
import { QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';

import { ErrorBoundary } from '@/components/ErrorBoundary';
import { queryClient } from '@/lib/queryClient';
import { router } from '@/routes/router';

interface AppProps {
  msalInstance: IPublicClientApplication;
}

/** Root application component: MSAL -> data layer -> error boundary -> router. */
export function App({ msalInstance }: AppProps): JSX.Element {
  return (
    <MsalProvider instance={msalInstance}>
      <QueryClientProvider client={queryClient}>
        <ErrorBoundary>
          <RouterProvider router={router} />
        </ErrorBoundary>
      </QueryClientProvider>
    </MsalProvider>
  );
}
