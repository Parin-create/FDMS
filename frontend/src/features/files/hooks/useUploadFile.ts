/** TanStack Query mutation for uploading a single file, exposing progress. */

import { useMutation } from '@tanstack/react-query';
import { useCallback, useState } from 'react';

import { uploadFileToApi, type FileUploadResponse } from '@/features/files/api/uploadClient';

export interface UseUploadFileResult {
  upload: (file: File) => void;
  reset: () => void;
  progress: number;
  isPending: boolean;
  isSuccess: boolean;
  isError: boolean;
  error: Error | null;
  data: FileUploadResponse | undefined;
}

export function useUploadFile(): UseUploadFileResult {
  const [progress, setProgress] = useState(0);

  const mutation = useMutation<FileUploadResponse, Error, File>({
    mutationFn: (file) => uploadFileToApi(file, { onProgress: setProgress }),
  });

  const upload = useCallback(
    (file: File) => {
      setProgress(0);
      mutation.mutate(file);
    },
    [mutation],
  );

  const reset = useCallback(() => {
    setProgress(0);
    mutation.reset();
  }, [mutation]);

  return {
    upload,
    reset,
    progress,
    isPending: mutation.isPending,
    isSuccess: mutation.isSuccess,
    isError: mutation.isError,
    error: mutation.error,
    data: mutation.data,
  };
}
