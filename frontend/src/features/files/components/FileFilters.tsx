/** Search bar + type filter + sort selector for the File Explorer. */

export interface FileFiltersProps {
  search: string;
  onSearchChange: (value: string) => void;
  contentType: string;
  onContentTypeChange: (value: string) => void;
  sort: 'asc' | 'desc';
  onSortChange: (value: 'asc' | 'desc') => void;
}

/** Type filter options mapped to backend MIME-type prefixes ('' = all). */
const TYPE_OPTIONS: ReadonlyArray<{ label: string; value: string }> = [
  { label: 'All types', value: '' },
  { label: 'PDF', value: 'application/pdf' },
  { label: 'Images', value: 'image/' },
  { label: 'Text & CSV', value: 'text/' },
  { label: 'Office documents', value: 'application/vnd' },
];

const selectClass =
  'rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 ' +
  'focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500';

export function FileFilters({
  search,
  onSearchChange,
  contentType,
  onContentTypeChange,
  sort,
  onSortChange,
}: FileFiltersProps): JSX.Element {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <div className="relative flex-1">
        <svg
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M9 3.5a5.5 5.5 0 1 0 3.4 9.82l3.14 3.14a.75.75 0 1 0 1.06-1.06l-3.14-3.14A5.5 5.5 0 0 0 9 3.5ZM5 9a4 4 0 1 1 8 0 4 4 0 0 1-8 0Z"
            clipRule="evenodd"
          />
        </svg>
        <input
          type="search"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search by filename…"
          aria-label="Search files by filename"
          className="w-full rounded-md border border-gray-300 bg-white py-2 pl-9 pr-3 text-sm text-gray-900 placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      <label className="flex items-center gap-2 text-sm text-gray-600">
        <span className="sr-only sm:not-sr-only">Type</span>
        <select
          value={contentType}
          onChange={(event) => onContentTypeChange(event.target.value)}
          aria-label="Filter by file type"
          className={selectClass}
        >
          {TYPE_OPTIONS.map((option) => (
            <option key={option.label} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-2 text-sm text-gray-600">
        <span className="sr-only sm:not-sr-only">Sort</span>
        <select
          value={sort}
          onChange={(event) => onSortChange(event.target.value === 'asc' ? 'asc' : 'desc')}
          aria-label="Sort files by date"
          className={selectClass}
        >
          <option value="desc">Newest first</option>
          <option value="asc">Oldest first</option>
        </select>
      </label>
    </div>
  );
}
