import { formatBytes } from '@/features/files/validation';

interface SelectedFileCardProps {
  file: File;
  onRemove: () => void;
  disabled?: boolean;
}

/** Shows the currently selected file with a remove action. */
export function SelectedFileCard({ file, onRemove, disabled = false }: SelectedFileCardProps): JSX.Element {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white p-3">
      <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-md bg-brand-50 text-brand-600">
        <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M14 3v4a1 1 0 0 0 1 1h4" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2Z" />
        </svg>
      </span>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-gray-900" title={file.name}>
          {file.name}
        </p>
        <p className="text-xs text-gray-500">
          {formatBytes(file.size)}
          {file.type ? ` · ${file.type}` : ''}
        </p>
      </div>

      <button
        type="button"
        onClick={onRemove}
        disabled={disabled}
        aria-label="Remove selected file"
        className="flex-shrink-0 rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
        </svg>
      </button>
    </div>
  );
}
