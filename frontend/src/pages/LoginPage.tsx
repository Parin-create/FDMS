import { InteractionStatus } from '@azure/msal-browser';
import { useIsAuthenticated, useMsal } from '@azure/msal-react';
import { Navigate } from 'react-router-dom';

import { loginRequest } from '@/auth/authConfig';
import { env } from '@/config/env';

/** Public login page. Redirects to home once authenticated. */
export function LoginPage(): JSX.Element {
  const isAuthenticated = useIsAuthenticated();
  const { instance, inProgress } = useMsal();

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const handleLogin = (): void => {
    void instance.loginRedirect(loginRequest);
  };

  const busy = inProgress !== InteractionStatus.None;

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6">
      <div className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-brand-600 text-lg font-bold text-white">
          F
        </span>
        <h1 className="mt-4 text-xl font-semibold text-gray-900">{env.appName}</h1>
        <p className="mt-1 text-sm text-gray-500">
          Sign in with your organization account to continue.
        </p>

        <button
          type="button"
          onClick={handleLogin}
          disabled={busy}
          className="mt-6 w-full rounded-md bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy ? 'Signing in…' : 'Sign in with Microsoft'}
        </button>
      </div>
    </div>
  );
}
