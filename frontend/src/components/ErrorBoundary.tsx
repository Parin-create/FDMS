import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

/**
 * Top-level error boundary that catches render-time exceptions anywhere in the
 * tree and shows a safe fallback instead of a blank screen. Route-level errors
 * are handled separately by the router's `errorElement`.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // In production this would forward to the observability pipeline.
    console.error('Unhandled UI error:', error, info.componentStack);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6">
            <div className="max-w-md rounded-lg border border-gray-200 bg-white p-8 text-center shadow-sm">
              <h1 className="text-xl font-semibold text-gray-900">Something went wrong</h1>
              <p className="mt-2 text-sm text-gray-600">
                An unexpected error occurred. Please reload the page.
              </p>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="mt-6 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
              >
                Reload
              </button>
            </div>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
