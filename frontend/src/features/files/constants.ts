/** Upload feature constants (frontend-only validation limits). */

/** Maximum file size accepted by the UI (backend does not enforce a limit yet). */
export const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024; // 50 MB

/** Human-readable form of {@link MAX_FILE_SIZE_BYTES} for messages. */
export const MAX_FILE_SIZE_LABEL = '50 MB';

/** Allowed file extensions (lowercase, with leading dot). UI-only allowlist. */
export const ALLOWED_EXTENSIONS = [
  '.pdf',
  '.doc',
  '.docx',
  '.xls',
  '.xlsx',
  '.ppt',
  '.pptx',
  '.txt',
  '.csv',
  '.png',
  '.jpg',
  '.jpeg',
  '.gif',
  '.zip',
] as const;
