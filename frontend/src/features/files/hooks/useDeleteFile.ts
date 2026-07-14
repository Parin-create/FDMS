/** Mutation that soft-deletes a file and refreshes the file list on success. */

import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';

import { deleteFile } from '@/features/files/api/filesApi';

export function useDeleteFile(): UseMutationResult<void, Error, string> {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (id) => deleteFile(id),
    onSuccess: () => {
      // Refresh every page of the tenant's file list (prefix match on the list key).
      void queryClient.invalidateQueries({ queryKey: ['files', 'list'] });
    },
  });
}
