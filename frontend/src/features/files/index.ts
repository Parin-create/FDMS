/**
 * Files feature module — clinical document upload and browsing.
 *
 * Implemented: Upload (4.3.1), File Explorer / list (4.3.3), File details (4.4.1),
 * secure Download (4.4.2), and soft Delete (4.4.3). Restore, recycle bin, bulk
 * delete, search, versioning, and sharing are intentionally not implemented yet.
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
