import { type ReactNode } from 'react';

interface UploadButtonProps {
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
  children?: ReactNode;
}

/** Primary action button for triggering the upload, with a loading state. */
export function UploadButton({
  onClick,
  disabled = false,
  loading = false,
  children = 'Upload',
}: UploadButtonProps): JSX.Element {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || loading}
      className="inline-flex items-center justify-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {loading && (
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z" />
        </svg>
      )}
      {loading ? 'Uploading…' : children}
    </button>
  );
}
