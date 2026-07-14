/** TanStack Query hook for a single file's metadata (enabled when an id is set). */

import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { fetchFileDetail, fileQueryKeys, type FileDetail } from '@/features/files/api/filesApi';

export function useFileDetailQuery(id: string | null): UseQueryResult<FileDetail, Error> {
  return useQuery<FileDetail, Error>({
    queryKey: fileQueryKeys.detail(id ?? ''),
    queryFn: () => fetchFileDetail(id as string),
    enabled: id !== null,
  });
}
