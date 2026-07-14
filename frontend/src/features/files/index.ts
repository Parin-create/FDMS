/**
 * Files feature module — clinical document upload and browsing.
 *
 * Implemented: Upload (Sprint 4.3.1) and File Explorer / list (Sprint 4.3.3).
 * Download, delete, search, versioning, and sharing are intentionally not
 * implemented yet.
 *
 * Public surface:
 *   UploadPage        - Files > Upload
 *   FileExplorerPage  - Files > browse (list, paginated)
 *   UploadCard        - reusable upload workflow
 */
export { UploadPage } from '@/features/files/UploadPage';
export { FileExplorerPage } from '@/features/files/FileExplorerPage';
export { UploadCard } from '@/features/files/components/UploadCard';
export { FileDetailsDrawer } from '@/features/files/components/FileDetailsDrawer';
