import { useEffect, type ReactNode } from 'react';

import { useFileDetailQuery } from '@/features/files/hooks/useFileDetailQuery';
import { formatBytes, formatDate } from '@/features/files/validation';
import { ApiError } from '@/lib/api';

interface FileDetailsDrawerProps {
  fileId: string | null;
  onClose: () => void;
}

function errorMessage(error: Error | null): string {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return 'This file no longer exists.';
    }
    if (error.status === 403) {
      return 'You do not have access to this file.';
    }
  }
  return 'Could not load file details.';
}

function DetailRow({ label, children }: { label: string; children: ReactNode }): JSX.Element {
  return (
    <div className="grid grid-cols-3 gap-3 py-2">
      <dt className="text-sm text-gray-500">{label}</dt>
      <dd className="col-span-2 break-words text-sm font-medium text-gray-900">{children}</dd>
    </div>
  );
}

/** Slide-over drawer showing a single file's metadata. Read-only. */
export function FileDetailsDrawer({ fileId, onClose }: FileDetailsDrawerProps): JSX.Element {
  const open = fileId !== null;
  const { data, isLoading, isError, error } = useFileDetailQuery(fileId);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-40 bg-black/40" onClick={onClose} aria-hidden="true" />
      )}
      <aside
        role="dialog"
        aria-label="File details"
        aria-hidden={!open}
        className={`fixed inset-y-0 right-0 z-50 flex w-full max-w-md transform flex-col border-l border-gray-200 bg-white shadow-xl transition-transform duration-200 ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex h-16 items-center justify-between border-b border-gray-200 px-5">
          <h2 className="text-base font-semibold">File details</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
          >
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {isLoading && <p className="text-sm text-gray-500">Loading…</p>}

          {isError && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
              {errorMessage(error)}
            </p>
          )}

          {data && (
            <dl className="divide-y divide-gray-100">
              <DetailRow label="Name">{data.original_filename}</DetailRow>
              <DetailRow label="Type">{data.content_type}</DetailRow>
              <DetailRow label="Size">{formatBytes(data.size_bytes)}</DetailRow>
              <DetailRow label="Uploaded">{formatDate(data.created_at)}</DetailRow>
              <DetailRow label="Uploaded by">
                {data.uploaded_by ?? data.uploaded_by_id ?? '—'}
              </DetailRow>
              <DetailRow label="Container">{data.blob_container}</DetailRow>
              <DetailRow label="Status">
                <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium capitalize text-green-700">
                  {data.status}
                </span>
              </DetailRow>
            </dl>
          )}
        </div>
      </aside>
    </>
  );
}
