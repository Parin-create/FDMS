/**
 * Files feature module — clinical document upload, listing, download, and management.
 *
 * Sprint 4.3.1 implements the **Upload** feature only. Listing, download, delete,
 * search, metadata editing, and versioning are intentionally not implemented yet
 * (they depend on backend endpoints that do not exist).
 *
 * Public surface:
 *   UploadPage    - the route target (Files > Upload)
 *   UploadCard    - self-contained upload workflow (reusable)
 */
export { UploadPage } from '@/features/files/UploadPage';
export { UploadCard } from '@/features/files/components/UploadCard';
