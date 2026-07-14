/** TanStack Query hook for the paginated file list. */

import { keepPreviousData, useQuery, type UseQueryResult } from '@tanstack/react-query';

import {
  fetchFiles,
  fileQueryKeys,
  type FileListParams,
  type FileListResponse,
} from '@/features/files/api/filesApi';

export function useFilesQuery(params: FileListParams): UseQueryResult<FileListResponse, Error> {
  return useQuery<FileListResponse, Error>({
    queryKey: fileQueryKeys.list(params),
    queryFn: () => fetchFiles(params),
    // Keep the current page visible while the next page loads (smooth pagination).
    placeholderData: keepPreviousData,
  });
}
