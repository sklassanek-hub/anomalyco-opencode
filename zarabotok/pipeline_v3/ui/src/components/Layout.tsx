import { useEffect, useMemo, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useHealth, useLogs, useMetrics } from '../hooks/queries';
import { ROLE_RU } from '../lib/status';

const NAV = [
  { to: '/overview', label: 'Обзор' },
  { to: '/pipeline', label: 'Пайплайн' },
  { to: '/orders', label: 'Заказы' },
  { to: '/llm-filter', label: 'LLM и фильтр' },
  { to: '/crm', label: 'CRM' },
  { to: '/agents', label: 'Агенты' },
  { to: '/billing', label: 'Оплата' },
  { to: '/monitoring', label: 'Мониторинг' },
];

const ROLES = ['operator', 'reviewer', 'admin'] as const;
const ROLE_KEY = 'zb_role';

function loadRole(): string {
  const r = localStorage.getItem(ROLE_KEY);
  return ROLES.includes(r as (typeof ROLES)[number]) ? (r as string) : 'operator';
}

function SystemStatusBar() {
  const navigate = useNavigate();
  const health = useHealth();
  const metrics = useMetrics();
  const alerts = useLogs({ level: 'error', limit: 5 });

  const { label, tone } = useMemo(() => {
    const h = health.data?.status;
    const hOk = health.data?.ok;
    if (health.isSuccess) {
      const s = String(h || '').toLowerCase();
      if (hOk === true || s === 'ok' || s === 'healthy') return { label: 'Healthy', tone: 'ok' as const };
      if (s === 'degraded' || s === 'warning' || s === 'degrading') return { label: 'Degraded', tone: 'warn' as const };
      if (hOk === false || s === 'error' || s === 'down' || s === 'offline') return { label: 'Error', tone: 'err' as const };
    }
    const workers = metrics.data?.workers;
    if (metrics.isSuccess && workers && workers.length > 0) {
      const online = workers.filter((w) => String(w.status || '').toLowerCase() !== 'offline');
      if (online.length === 0) return { label: 'Error', tone: 'err' as const };
      if (online.length < workers.length) return { label: 'Degraded', tone: 'warn' as const };
      return { label: 'Healthy', tone: 'ok' as const };
    }
    if (health.isError && metrics.isError) return { label: 'Недоступно', tone: 'gray' as const };
    return { label: 'Healthy', tone: 'ok' as const };
  }, [health, metrics]);

  const alertsList = (alerts.data?.logs || alerts.data?.items || []).filter((l) =>
    ['error', 'err', 'warning', 'warn'].includes(String(l.level || '').toLowerCase()),
  );

  return (
    <div className="sysbar" onClick={() => navigate('/monitoring')} role="button" tabIndex={0}>
      <span className={`sys-dot dot-${tone}`} />
      <span className="sys-label">Система: {label}</span>
      {alertsList.length > 0 && (
        <span className="sys-alerts">
          {alertsList.slice(0, 3).map((a, i) => (
            <span key={i} className="sys-alert">
              {a.text || a.msg}
            </span>
          ))}
        </span>
      )}
      <span className="sys-hint">→ Мониторинг</span>
    </div>
  );
}

function UserMenu() {
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState(loadRole);

  useEffect(() => {
    localStorage.setItem(ROLE_KEY, role);
  }, [role]);

  return (
    <div className="user-menu">
      <button className="user-btn" onClick={() => setOpen((o) => !o)}>
        <span className="user-avatar">{ROLE_RU[role]?.[0] || 'O'}</span>
        <span>{ROLE_RU[role] || role}</span>
        <span className="caret">▾</span>
      </button>
      {open && (
        <div className="user-dropdown" onClick={() => setOpen(false)}>
          {ROLES.map((r) => (
            <button
              key={r}
              className={`user-option${r === role ? ' user-option-active' : ''}`}
              onClick={() => setRole(r)}
            >
              {ROLE_RU[r]}
              {r === role && ' ✓'}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Layout() {
  const location = useLocation();
  const isActiveNav = (to: string) => location.pathname === to || (to !== '/' && location.pathname.startsWith(to + '/')) || location.pathname === to;
  return (
    <div className="app">
      <a href="#main" className="skip-link">Перейти к содержимому</a>
      <header className="header">
        <div className="header-top">
          <NavLink to="/overview" className="logo">
            <span className="logo-mark">z</span>
            <span className="logo-text">
              <strong>zarabotok</strong>
              <small>pipeline_v3</small>
            </span>
          </NavLink>
          <nav className="nav" aria-label="Основная навигация">
            {NAV.map((n) => {
              const active = isActiveNav(n.to);
              return (
                <Link
                  key={n.to}
                  to={n.to}
                  className={`nav-link${active ? ' nav-active' : ''}`}
                  aria-current={active ? 'page' : undefined}
                >
                  {n.label}
                </Link>
              );
            })}
          </nav>
          <UserMenu />
        </div>
        <SystemStatusBar />
      </header>
      <main id="main" className="content">
        <Outlet />
      </main>
    </div>
  );
}