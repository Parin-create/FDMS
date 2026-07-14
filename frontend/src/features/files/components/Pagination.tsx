interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  isFetching?: boolean;
}

/** Backend-offset pagination controls with a range summary. */
export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  isFetching = false,
}: PaginationProps): JSX.Element {
  const start = total === 0 ? 0 : page * pageSize + 1;
  const end = Math.min(total, (page + 1) * pageSize);
  const canPrev = page > 0;
  const canNext = end < total;

  const buttonClass =
    'rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50';

  return (
    <div className="flex items-center justify-between gap-3">
      <p className="text-sm text-gray-500">
        {start}–{end} of {total}
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          className={buttonClass}
          disabled={!canPrev || isFetching}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </button>
        <button
          type="button"
          className={buttonClass}
          disabled={!canNext || isFetching}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
