/**
 * File listing API — GET /api/v1/files.
 *
 * A plain JSON GET, so it reuses the existing shared `apiClient` (which attaches
 * the bearer token). The API client and auth layer are left untouched.
 */

import { z } from 'zod';

import { apiClient } from '@/lib/api';

/** Mirrors the backend `FileListItem` schema. */
export const fileListItemSchema = z.object({
  id: z.string().uuid(),
  original_filename: z.string(),
  content_type: z.string(),
  size_bytes: z.number(),
  blob_name: z.string(),
  etag: z.string().nullable().optional(),
  uploaded_by_id: z.string().uuid().nullable().optional(),
  created_at: z.string(),
});

export type FileListItem = z.infer<typeof fileListItemSchema>;

/** Mirrors the backend `FileListResponse` schema. */
export const fileListResponseSchema = z.object({
  items: z.array(fileListItemSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export type FileListResponse = z.infer<typeof fileListResponseSchema>;

/** Mirrors the backend `FileDetailResponse` schema. */
export const fileDetailSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  original_filename: z.string(),
  content_type: z.string(),
  size_bytes: z.number(),
  blob_container: z.string(),
  blob_name: z.string(),
  etag: z.string().nullable().optional(),
  uploaded_by_id: z.string().uuid().nullable().optional(),
  uploaded_by: z.string().nullable().optional(),
  status: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type FileDetail = z.infer<typeof fileDetailSchema>;

export interface FileListParams {
  limit: number;
  offset: number;
  sort: 'asc' | 'desc';
  /** Case-insensitive filename substring filter. */
  search?: string;
  /** Case-insensitive MIME-type prefix filter (e.g. "image/", "application/pdf"). */
  contentType?: string;
}

/** Fetch a page of the tenant's files. */
export async function fetchFiles(params: FileListParams): Promise<FileListResponse> {
  const query = new URLSearchParams({
    limit: String(params.limit),
    offset: String(params.offset),
    sort: params.sort,
  });
  if (params.search) {
    query.set('search', params.search);
  }
  if (params.contentType) {
    query.set('content_type', params.contentType);
  }
  const data = await apiClient.get<unknown>(`/files?${query.toString()}`);
  return fileListResponseSchema.parse(data);
}

/** Fetch a single file's metadata. */
export async function fetchFileDetail(id: string): Promise<FileDetail> {
  const data = await apiClient.get<unknown>(`/files/${id}`);
  return fileDetailSchema.parse(data);
}

/** Mirrors the backend `FileDownloadResponse` schema (short-lived SAS URL). */
export const fileDownloadSchema = z.object({
  download_url: z.string().url(),
  expires_at: z.string(),
  filename: z.string(),
});

export type FileDownload = z.infer<typeof fileDownloadSchema>;

/** Request a short-lived download URL for a file. */
export async function fetchDownloadUrl(id: string): Promise<FileDownload> {
  const data = await apiClient.get<unknown>(`/files/${id}/download`);
  return fileDownloadSchema.parse(data);
}

/** Soft-delete a file. Resolves on success (backend returns 204 No Content). */
export async function deleteFile(id: string): Promise<void> {
  await apiClient.delete<void>(`/files/${id}`);
}

export const fileQueryKeys = {
  list: (params: FileListParams) => ['files', 'list', params] as const,
  detail: (id: string) => ['files', 'detail', id] as const,
};
