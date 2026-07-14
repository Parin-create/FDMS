import type { FileListItem } from '@/features/files/api/filesApi';
import { FileRow } from '@/features/files/components/FileRow';

interface FileTableProps {
  items: FileListItem[];
}

/** Table of files. Horizontally scrollable on small screens. */
export function FileTable({ items }: FileTableProps): JSX.Element {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr className="text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Size</th>
              <th className="px-4 py-3">Uploaded</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.map((file) => (
              <FileRow key={file.id} file={file} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
