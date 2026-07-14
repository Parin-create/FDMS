import { NavLink } from 'react-router-dom';

import { useCurrentUser } from '@/auth/CurrentUserContext';
import { RoleName, roleAtLeast } from '@/auth/roles';
import { env } from '@/config/env';

interface NavItem {
  to: string;
  label: string;
  end?: boolean;
  /** Active route now, or a future capability shown disabled. */
  enabled: boolean;
  /** Minimum role required to see the item (UI gating only). */
  minimumRole?: RoleName;
}

// Home is live in Sprint 1. Remaining items preview the roadmap and are rendered
// disabled until their sprints land — no fake routes are wired up.
const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Home', end: true, enabled: true },
  { to: '/files', label: 'Files', end: true, enabled: true },
  { to: '/files/upload', label: 'Upload', enabled: true },
  { to: '/folders', label: 'Folders', enabled: false },
  { to: '/documents', label: 'Documents', enabled: false },
  { to: '/shared', label: 'Shared with me', enabled: false },
  { to: '/admin', label: 'Administration', enabled: false, minimumRole: RoleName.TenantAdmin },
];

interface SidebarProps {
  /** Mobile drawer open state. */
  open: boolean;
  onClose: () => void;
}

/** Primary navigation. Static on desktop; a slide-over drawer on mobile. */
export function Sidebar({ open, onClose }: SidebarProps): JSX.Element {
  const user = useCurrentUser();

  const visibleItems = NAV_ITEMS.filter(
    (item) => item.minimumRole === undefined || roleAtLeast(user.role, item.minimumRole),
  );

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-gray-200 bg-white transition-transform duration-200 md:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-16 items-center gap-2 border-b border-gray-200 px-5">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-brand-600 text-sm font-bold text-white">
            F
          </span>
          <span className="text-lg font-semibold">{env.appName}</span>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {visibleItems.map((item) =>
            item.enabled ? (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end ?? false}
                onClick={onClose}
                className={({ isActive }) =>
                  `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-brand-50 text-brand-700'
                      : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ) : (
              <div
                key={item.to}
                aria-disabled="true"
                title="Available in a later release"
                className="flex cursor-not-allowed items-center justify-between rounded-md px-3 py-2 text-sm font-medium text-gray-400"
              >
                {item.label}
                <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                  Soon
                </span>
              </div>
            ),
          )}
        </nav>

        <div className="border-t border-gray-200 px-5 py-3 text-xs text-gray-400">
          Signed in to {user.tenant_name}
        </div>
      </aside>
    </>
  );
}
