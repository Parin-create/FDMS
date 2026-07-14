import { useCurrentUser } from '@/auth/CurrentUserContext';
import { RoleName, roleAtLeast } from '@/auth/roles';
import { UploadCard } from '@/features/files/components/UploadCard';

/** Files > Upload page. Contributor/Admin can upload; others see a notice. */
export function UploadPage(): JSX.Element {
  const user = useCurrentUser();
  const canUpload = roleAtLeast(user.role, RoleName.Contributor);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Upload documents</h1>
        <p className="mt-1 text-sm text-gray-600">
          Add a document to <span className="font-medium">{user.tenant_name}</span>.
        </p>
      </header>

      {canUpload ? (
        <UploadCard />
      ) : (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-5">
          <h2 className="text-sm font-semibold text-amber-900">Upload not available</h2>
          <p className="mt-1 text-sm text-amber-800">
            Your role (<span className="font-medium">{user.role}</span>) does not permit uploading
            documents. Contact a tenant administrator to request the Contributor role.
          </p>
        </div>
      )}
    </div>
  );
}
