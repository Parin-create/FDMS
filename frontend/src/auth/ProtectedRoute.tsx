import { InteractionStatus } from '@azure/msal-browser';
import { useIsAuthenticated, useMsal } from '@azure/msal-react';
import { Navigate, Outlet } from 'react-router-dom';

import { CurrentUserProvider } from '@/auth/CurrentUserContext';
import { RootLayout } from '@/layouts/RootLayout';

/**
 * Authentication guard for protected routes.
 *
 * - While MSAL is processing a redirect/interaction, shows a neutral loading state.
 * - If unauthenticated, redirects to the login page.
 * - If authenticated, loads the current user and renders the app shell + routes.
 */
export function ProtectedRoute(): JSX.Element {
  const isAuthenticated = useIsAuthenticated();
  const { inProgress } = useMsal();

  if (inProgress !== InteractionStatus.None) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <p className="text-sm text-gray-500">Signing you in…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <CurrentUserProvider>
      <RootLayout>
        <Outlet />
      </RootLayout>
    </CurrentUserProvider>
  );
}
