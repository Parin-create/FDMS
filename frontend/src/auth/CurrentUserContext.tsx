import { useMsal } from '@azure/msal-react';
import { useQuery } from '@tanstack/react-query';
import { createContext, useContext, type ReactNode } from 'react';

import { authQueryKeys, fetchCurrentUser, type CurrentUser } from '@/lib/currentUser';

const CurrentUserContext = createContext<CurrentUser | null>(null);

/** Access the authenticated FDMS user. Must be used within `CurrentUserProvider`. */
export function useCurrentUser(): CurrentUser {
  const user = useContext(CurrentUserContext);
  if (!user) {
    throw new Error('useCurrentUser must be used within a CurrentUserProvider.');
  }
  return user;
}

interface CurrentUserProviderProps {
  children: ReactNode;
}

/**
 * Loads the current FDMS user (`/auth/me`) after authentication and exposes it via
 * context. Handles the loading and error states (e.g. tenant not provisioned).
 */
export function CurrentUserProvider({ children }: CurrentUserProviderProps): JSX.Element {
  const { instance } = useMsal();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: authQueryKeys.me,
    queryFn: fetchCurrentUser,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <p className="text-sm text-gray-500">Loading your account…</p>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6">
        <div className="max-w-md rounded-lg border border-gray-200 bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-semibold text-gray-900">Account unavailable</h1>
          <p className="mt-2 text-sm text-gray-600">
            {error instanceof Error ? error.message : 'Unable to load your account.'}
          </p>
          <button
            type="button"
            onClick={() => void instance.logoutRedirect()}
            className="mt-6 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Sign out
          </button>
        </div>
      </div>
    );
  }

  return <CurrentUserContext.Provider value={data}>{children}</CurrentUserContext.Provider>;
}
