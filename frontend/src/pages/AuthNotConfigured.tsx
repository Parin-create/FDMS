/** Shown when Entra ID env vars are missing, so the app can still start cleanly. */
export function AuthNotConfigured(): JSX.Element {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6">
      <div className="max-w-lg rounded-lg border border-amber-200 bg-amber-50 p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-amber-900">Authentication not configured</h1>
        <p className="mt-2 text-sm text-amber-800">
          Microsoft Entra ID environment variables are not set. Configure the following in
          <code className="mx-1 rounded bg-amber-100 px-1">frontend/.env</code> and restart:
        </p>
        <ul className="mt-4 space-y-1 text-sm text-amber-900">
          <li>
            <code>VITE_ENTRA_CLIENT_ID</code> — SPA app registration client id
          </li>
          <li>
            <code>VITE_ENTRA_TENANT_ID</code> — directory id (or <code>organizations</code>)
          </li>
          <li>
            <code>VITE_ENTRA_API_SCOPE</code> — e.g. <code>api://&lt;api-client-id&gt;/access_as_user</code>
          </li>
        </ul>
      </div>
    </div>
  );
}
