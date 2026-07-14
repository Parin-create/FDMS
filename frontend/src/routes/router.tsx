import { createBrowserRouter } from 'react-router-dom';

import { ProtectedRoute } from '@/auth/ProtectedRoute';
import { RouteError } from '@/components/RouteError';
import { FileExplorerPage, UploadPage } from '@/features/files';
import { HomePage } from '@/pages/HomePage';
import { LoginPage } from '@/pages/LoginPage';
import { NotFoundPage } from '@/pages/NotFoundPage';

/**
 * Application route tree.
 *
 * `/login` is public; everything under `/` is gated by `ProtectedRoute`, which
 * enforces authentication and renders the app shell + current-user context.
 */
export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
    errorElement: <RouteError />,
  },
  {
    path: '/',
    element: <ProtectedRoute />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'files', element: <FileExplorerPage /> },
      { path: 'files/upload', element: <UploadPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
