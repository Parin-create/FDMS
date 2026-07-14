import { useEffect, useState } from 'react';

import { useCurrentUser } from '@/auth/CurrentUserContext';
import { type FileListParams } from '@/features/files/api/filesApi';
import { EmptyState } from '@/features/files/components/EmptyState';
import { FileDetailsDrawer } from '@/features/files/components/FileDetailsDrawer';
import { FileFilters } from '@/features/files/components/FileFilters';
import { FileTable } from '@/features/files/components/FileTable';
import { LoadingState } from '@/features/files/components/LoadingState';
import { Pagination } from '@/features/files/components/Pagination';
import { useDebouncedValue } from '@/features/files/hooks/useDebouncedValue';
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
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [deletedName, setDeletedName] = useState<string | null>(null);

  const [searchInput, setSearchInput] = useState('');
  const [contentType, setContentType] = useState('');
  const [sort, setSort] = useState<'asc' | 'desc'>('desc');
  const debouncedSearch = useDebouncedValue(searchInput.trim(), 300);
  const hasFilters = debouncedSearch !== '' || contentType !== '';

  // Any filter/sort change resets to the first page so results start from the top.
  useEffect(() => {
    setPage(0);
  }, [debouncedSearch, contentType, sort]);

  const queryParams: FileListParams = {
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    sort,
    // exactOptionalPropertyTypes: only include filters when set (never `undefined`).
    ...(debouncedSearch ? { search: debouncedSearch } : {}),
    ...(contentType ? { contentType } : {}),
  };

  const { data, isLoading, isError, error, isFetching } = useFilesQuery(queryParams);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Files</h1>
        <p className="mt-1 text-sm text-gray-600">
          Documents in <span className="font-medium">{user.tenant_name}</span>.
        </p>
      </header>

      {deletedName && (
        <div
          role="status"
          className="flex items-center justify-between rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800"
        >
          <span>
            “<span className="font-medium">{deletedName}</span>” was deleted.
          </span>
          <button
            type="button"
            onClick={() => setDeletedName(null)}
            aria-label="Dismiss notification"
            className="rounded p-1 text-green-700 hover:bg-green-100 hover:text-green-900"
          >
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
            </svg>
          </button>
        </div>
      )}

      <FileFilters
        search={searchInput}
        onSearchChange={setSearchInput}
        contentType={contentType}
        onContentTypeChange={setContentType}
        sort={sort}
        onSortChange={setSort}
      />

      {isLoading ? (
        <LoadingState />
      ) : isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">
          {errorMessage(error)}
        </div>
      ) : data && data.items.length === 0 ? (
        hasFilters ? (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-6 text-center text-sm text-gray-600">
            <p>No files match your search or filters.</p>
            <button
              type="button"
              onClick={() => {
                setSearchInput('');
                setContentType('');
              }}
              className="mt-2 font-medium text-brand-600 hover:text-brand-700"
            >
              Clear filters
            </button>
          </div>
        ) : (
          <EmptyState />
        )
      ) : data ? (
        <div className="space-y-4">
          <FileTable items={data.items} onSelect={(file) => setSelectedId(file.id)} />
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={data.total}
            onPageChange={setPage}
            isFetching={isFetching}
          />
        </div>
      ) : null}

      <FileDetailsDrawer
        fileId={selectedId}
        onClose={() => setSelectedId(null)}
        onDeleted={(name) => setDeletedName(name)}
      />
    </div>
  );
}
