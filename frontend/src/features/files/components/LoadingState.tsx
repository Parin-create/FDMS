/** Loading placeholder for the file list. */
export function LoadingState(): JSX.Element {
  return (
    <div className="flex items-center justify-center gap-3 rounded-lg border border-gray-200 bg-white p-10 text-sm text-gray-500 shadow-sm">
      <svg className="h-5 w-5 animate-spin text-brand-600" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z" />
      </svg>
      Loading files…
    </div>
  );
}
