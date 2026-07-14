import { Link } from 'react-router-dom';

/** Zero-state shown when the tenant has no files yet. */
export function EmptyState(): JSX.Element {
  return (
    <div className="rounded-lg border border-dashed border-gray-300 bg-white p-10 text-center shadow-sm">
      <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 text-gray-400">
        <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M14 3v4a1 1 0 0 0 1 1h4" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2Z" />
        </svg>
      </span>
      <h2 className="mt-4 text-sm font-semibold text-gray-900">No files yet</h2>
      <p className="mt-1 text-sm text-gray-500">Uploaded documents will appear here.</p>
      <Link
        to="/files/upload"
        className="mt-4 inline-block rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
      >
        Upload a document
      </Link>
    </div>
  );
}
