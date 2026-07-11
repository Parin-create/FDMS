import { isRouteErrorResponse, useRouteError, Link } from 'react-router-dom';

/** Router `errorElement`: renders thrown route/loader errors safely. */
export function RouteError(): JSX.Element {
  const error = useRouteError();

  let title = 'Unexpected error';
  let message = 'Something went wrong while loading this page.';

  if (isRouteErrorResponse(error)) {
    title = `${error.status} ${error.statusText}`;
    message = typeof error.data === 'string' ? error.data : message;
  } else if (error instanceof Error) {
    message = error.message;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6">
      <div className="max-w-md rounded-lg border border-gray-200 bg-white p-8 text-center shadow-sm">
        <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
        <p className="mt-2 text-sm text-gray-600">{message}</p>
        <Link
          to="/"
          className="mt-6 inline-block rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          Back to home
        </Link>
      </div>
    </div>
  );
}
