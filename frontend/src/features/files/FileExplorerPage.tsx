import { useState } from 'react';

import { useCurrentUser } from '@/auth/CurrentUserContext';
import { EmptyState } from '@/features/files/components/EmptyState';
import { FileTable } from '@/features/files/components/FileTable';
import { LoadingState } from '@/features/files/components/LoadingState';
import { Pagination } from '@/features/files/components/Pagination';
import { useFilesQuery } from '@/features/files/hooks/useFilesQuery';
import { ApiError } from '@/lib/api';

const PAGE_SIZE = 20;

function errorMessage(error: Error | null): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return 'Your session has expired. Please sign in again.';
    }
    if (error.status === 403) {
      return 'You do not have permission to view files.';
    }
  }
  return 'Could not load files. Please try again.';
}

/** Files > browse. Lists the tenant's uploaded documents with pagination. */
export function FileExplorerPage(): JSX.Element {
  const user = useCurrentUser();
  const [page, setPage] = useState(0);

  const { data, isLoading, isError, error, isFetching } = useFilesQuery({
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    sort: 'desc',
  });

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Files</h1>
        <p className="mt-1 text-sm text-gray-600">
          Documents in <span className="font-medium">{user.tenant_name}</span>.
        </p>
      </header>

      {isLoading ? (
        <LoadingState />
      ) : isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">
          {errorMessage(error)}
        </div>
      ) : data && data.items.length === 0 ? (
        <EmptyState />
      ) : data ? (
        <div className="space-y-4">
          <FileTable items={data.items} />
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={data.total}
            onPageChange={setPage}
            isFetching={isFetching}
          />
        </div>
      ) : null}
    </div>
  );
}
