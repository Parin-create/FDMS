/**
 * Dedicated multipart upload client for POST /api/v1/files/upload.
 *
 * The shared `lib/api.ts` client sends JSON and cannot report upload progress, so
 * this feature uses XMLHttpRequest (which exposes `upload.onprogress`). It REUSES
 * the existing `acquireApiToken` for the bearer token — the shared API client and
 * auth layer are left untouched.
 */

import { z } from 'zod';

import { acquireApiToken } from '@/auth/tokens';
import { env } from '@/config/env';

/** Mirrors the backend `FileUploadResponse` schema (validated at runtime). */
export const fileUploadResponseSchema = z.object({
  container: z.string(),
  blob_name: z.string(),
  original_filename: z.string(),
  size: z.number(),
  content_type: z.string(),
  etag: z.string().nullable(),
});

export type FileUploadResponse = z.infer<typeof fileUploadResponseSchema>;

export interface UploadOptions {
  onProgress?: (percent: number) => void;
  signal?: AbortSignal;
}

/** Error carrying the HTTP status for friendly, status-aware UI messages. */
export class UploadError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'UploadError';
    this.status = status;
  }
}

function extractDetail(body: unknown): string | undefined {
  if (body && typeof body === 'object' && 'error' in body) {
    const error = (body as { error?: { message?: unknown } }).error;
    if (error && typeof error.message === 'string') {
      return error.message;
    }
  }
  return undefined;
}

function messageForStatus(status: number, body: unknown): string {
  const detail = extractDetail(body);
  switch (status) {
    case 401:
      return 'Your session has expired. Please sign in again.';
    case 403:
      return detail ?? 'You do not have permission to upload files.';
    case 413:
      return 'The file is too large.';
    case 415:
      return 'This file type is not supported.';
    case 503:
      return detail ?? 'The upload service is temporarily unavailable. Please try again.';
    default:
      return detail ?? `Upload failed (HTTP ${status}).`;
  }
}

/** Upload a single file as multipart/form-data, resolving the parsed response. */
export function uploadFileToApi(file: File, options: UploadOptions = {}): Promise<FileUploadResponse> {
  return acquireApiToken().then(
    (token) =>
      new Promise<FileUploadResponse>((resolve, reject) => {
        if (!token) {
          reject(new UploadError(401, 'Your session has expired. Please sign in again.'));
          return;
        }

        const form = new FormData();
        form.append('file', file);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${env.apiBaseUrl}/files/upload`);
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        xhr.responseType = 'json';

        if (options.onProgress) {
          xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
              options.onProgress?.(Math.round((event.loaded / event.total) * 100));
            }
          };
        }

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            const parsed = fileUploadResponseSchema.safeParse(xhr.response);
            if (parsed.success) {
              resolve(parsed.data);
            } else {
              reject(new UploadError(xhr.status, 'The server returned an unexpected response.'));
            }
          } else {
            reject(new UploadError(xhr.status, messageForStatus(xhr.status, xhr.response)));
          }
        };
        xhr.onerror = () => reject(new UploadError(0, 'Network error — could not reach the server.'));
        xhr.onabort = () => reject(new UploadError(0, 'Upload cancelled.'));

        if (options.signal) {
          options.signal.addEventListener('abort', () => xhr.abort(), { once: true });
        }

        xhr.send(form);
      }),
  );
}
