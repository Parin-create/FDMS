/** Client-side file validation and formatting helpers for the Upload feature. */

import { ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_LABEL } from '@/features/files/constants';

export interface ValidationResult {
  ok: boolean;
  error?: string;
}

/** Lowercased extension including the leading dot, or '' when none. */
export function getExtension(filename: string): string {
  const dot = filename.lastIndexOf('.');
  return dot >= 0 ? filename.slice(dot).toLowerCase() : '';
}

/** Human-readable byte size (e.g. "3.4 MB"). */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

/** Format an ISO datetime string for display (locale-aware). */
export function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Validate a file against the UI allowlist and size limit. */
export function validateFile(file: File): ValidationResult {
  const extension = getExtension(file.name);

  if (!extension || !ALLOWED_EXTENSIONS.includes(extension as (typeof ALLOWED_EXTENSIONS)[number])) {
    return {
      ok: false,
      error: `Unsupported file type. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}.`,
    };
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      ok: false,
      error: `File is too large (${formatBytes(file.size)}). Maximum is ${MAX_FILE_SIZE_LABEL}.`,
    };
  }

  if (file.size === 0) {
    return { ok: false, error: 'File is empty.' };
  }

  return { ok: true };
}
