import type { KeyboardEvent } from 'react';

import type { FileListItem } from '@/features/files/api/filesApi';
import { formatBytes, formatDate } from '@/features/files/validation';

interface FileRowProps {
  file: FileListItem;
  onSelect: (file: FileListItem) => void;
}

/** A single file row: name, type, size, upload date. Clicking opens details. */
export function FileRow({ file, onSelect }: FileRowProps): JSX.Element {
  const onKeyDown = (event: KeyboardEvent<HTMLTableRowElement>): void => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onSelect(file);
    }
  };

  return (
    <tr
      className="cursor-pointer hover:bg-gray-50"
      tabIndex={0}
      onClick={() => onSelect(file)}
      onKeyDown={onKeyDown}
    >
      <td className="max-w-xs px-4 py-3">
        <div className="flex items-center gap-2">
          <svg
            className="h-4 w-4 flex-shrink-0 text-gray-400"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M14 3v4a1 1 0 0 0 1 1h4" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2Z" />
          </svg>
          <span className="truncate font-medium text-gray-900" title={file.original_filename}>
            {file.original_filename}
          </span>
        </div>
      </td>
      <td className="px-4 py-3 text-gray-500">{file.content_type}</td>
      <td className="whitespace-nowrap px-4 py-3 text-gray-500">{formatBytes(file.size_bytes)}</td>
      <td className="whitespace-nowrap px-4 py-3 text-gray-500">{formatDate(file.created_at)}</td>
    </tr>
  );
}
