type UploadStatus = 'uploading' | 'success' | 'error';

interface UploadProgressProps {
  progress: number;
  status: UploadStatus;
}

const BAR_COLOR: Record<UploadStatus, string> = {
  uploading: 'bg-brand-600',
  success: 'bg-green-600',
  error: 'bg-red-500',
};

const LABEL: Record<UploadStatus, string> = {
  uploading: 'Uploading…',
  success: 'Upload complete',
  error: 'Upload failed',
};

/** Determinate progress bar with a status label. */
export function UploadProgress({ progress, status }: UploadProgressProps): JSX.Element {
  const clamped = Math.min(100, Math.max(0, progress));
  const width = status === 'success' ? 100 : clamped;

  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="font-medium text-gray-700">{LABEL[status]}</span>
        <span className="text-gray-500">{width}%</span>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-gray-200"
        role="progressbar"
        aria-valuenow={width}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={`h-full rounded-full transition-all duration-200 ${BAR_COLOR[status]}`}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}
