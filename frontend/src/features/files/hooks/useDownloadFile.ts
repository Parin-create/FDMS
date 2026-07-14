/** Mutation that fetches a short-lived download URL and initiates the download. */

import { useMutation } from '@tanstack/react-query';

import { fetchDownloadUrl } from '@/features/files/api/filesApi';

function triggerBrowserDownload(url: string): void {
  // The SAS URL responds with Content-Disposition: attachment, so a plain anchor
  // click downloads the file (with its original name) without navigating away.
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.rel = 'noopener';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

export interface UseDownloadFileResult {
  download: (id: string) => void;
  isPending: boolean;
  isError: boolean;
  error: Error | null;
}

export function useDownloadFile(): UseDownloadFileResult {
  const mutation = useMutation<void, Error, string>({
    mutationFn: async (id) => {
      const info = await fetchDownloadUrl(id);
      triggerBrowserDownload(info.download_url);
    },
  });

  return {
    download: mutation.mutate,
    isPending: mutation.isPending,
    isError: mutation.isError,
    error: mutation.error,
  };
}
