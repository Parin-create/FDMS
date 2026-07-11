import { useCurrentUser } from '@/auth/CurrentUserContext';

/** Authenticated landing page showing the signed-in user and tenant context. */
export function HomePage(): JSX.Element {
  const user = useCurrentUser();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Welcome, {user.display_name}</h1>
        <p className="mt-1 text-gray-600">
          You are signed in to <span className="font-medium">{user.tenant_name}</span> as{' '}
          <span className="font-medium">{user.role}</span>.
        </p>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
          Your account
        </h2>
        <dl className="mt-4 grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-gray-500">Email</dt>
            <dd className="font-medium text-gray-900">{user.email}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Role</dt>
            <dd className="font-medium text-gray-900">{user.role}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Tenant</dt>
            <dd className="font-medium text-gray-900">{user.tenant_name}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Status</dt>
            <dd className="font-medium text-gray-900">{user.is_active ? 'Active' : 'Disabled'}</dd>
          </div>
        </dl>
      </div>

      <p className="max-w-2xl text-sm text-gray-500">
        Authentication &amp; identity foundation (Sprint 1) is in place. Tenant management, folders,
        documents, and document-level permissions are delivered in subsequent sprints.
      </p>
    </div>
  );
}
