import { useState } from 'react';

import { DropZone } from '@/features/files/components/DropZone';
import { SelectedFileCard } from '@/features/files/components/SelectedFileCard';
import { UploadButton } from '@/features/files/components/UploadButton';
import { UploadProgress } from '@/features/files/components/UploadProgress';
import { useUploadFile } from '@/features/files/hooks/useUploadFile';
import { validateFile } from '@/features/files/validation';

/** Self-contained upload workflow: select → validate → upload → result. */
export function UploadCard(): JSX.Element {
  const [file, setFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const { upload, reset, progress, isPending, isSuccess, isError, error, data } = useUploadFile();

  const selectFile = (candidate: File): void => {
    const result = validateFile(candidate);
    reset();
    if (!result.ok) {
      setFile(null);
      setValidationError(result.error ?? 'Invalid file.');
      return;
    }
    setValidationError(null);
    setFile(candidate);
  };

  const clear = (): void => {
    setFile(null);
    setValidationError(null);
    reset();
  };

  const startUpload = (): void => {
    if (file) {
      upload(file);
    }
  };

  const showProgress = isPending || isSuccess || isError;
  const progressStatus = isSuccess ? 'success' : isError ? 'error' : 'uploading';

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Upload a document</h2>

      <div className="mt-4 space-y-4">
        {!file && !isSuccess && <DropZone onFileSelected={selectFile} disabled={isPending} />}

        {validationError && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{validationError}</p>
        )}

        {file && !isSuccess && (
          <SelectedFileCard file={file} onRemove={clear} disabled={isPending} />
        )}

        {showProgress && <UploadProgress progress={progress} status={progressStatus} />}

        {isSuccess && data && (
          <p className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
            <span className="font-medium">{data.original_filename}</span> uploaded successfully.
          </p>
        )}

        {isError && error && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error.message}</p>
        )}

        <div className="flex flex-wrap items-center gap-3 pt-1">
          {!isSuccess ? (
            <UploadButton onClick={startUpload} disabled={!file || isPending} loading={isPending} />
          ) : (
            <UploadButton onClick={clear}>Upload another</UploadButton>
          )}
          {isError && file && (
            <button
              type="button"
              onClick={startUpload}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
