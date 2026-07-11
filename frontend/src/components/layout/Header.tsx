import { UserMenu } from '@/components/layout/UserMenu';
import { env } from '@/config/env';

interface HeaderProps {
  /** Opens the mobile navigation drawer. */
  onMenuClick: () => void;
}

/** Top application bar: mobile menu toggle, title (mobile), and user menu. */
export function Header({ onMenuClick }: HeaderProps): JSX.Element {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4 md:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          aria-label="Open navigation menu"
          className="rounded-md p-2 text-gray-500 hover:bg-gray-100 md:hidden"
        >
          <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path
              fillRule="evenodd"
              d="M2.75 5.75A.75.75 0 013.5 5h13a.75.75 0 010 1.5h-13a.75.75 0 01-.75-.75zm0 4.25a.75.75 0 01.75-.75h13a.75.75 0 010 1.5h-13a.75.75 0 01-.75-.75zm.75 3.5a.75.75 0 000 1.5h13a.75.75 0 000-1.5h-13z"
              clipRule="evenodd"
            />
          </svg>
        </button>
        <span className="text-base font-semibold md:hidden">{env.appName}</span>
      </div>

      <UserMenu />
    </header>
  );
}
