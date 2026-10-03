import { NavLink, Outlet } from 'react-router-dom'
import { API_BASE } from '../api'
import { useHealth } from '../hooks'

export default function Layout() {
  const health = useHealth()
  const offline = health.isError
  return (
    <div className="shell">
      <header className="top">
        <div>
          <h1>Retrieval bench</h1>
          <nav className="nav" aria-label="Pages">
            <NavLink to="/" end className="nav__link">Ask</NavLink>
            <NavLink to="/config" className="nav__link">Settings</NavLink>
          </nav>
        </div>
        <p className={`conn conn--${offline ? 'off' : health.isSuccess ? 'on' : 'wait'}`} role="status">
          <span className="conn__dot" aria-hidden="true" />
          {offline ? 'API not reachable' : health.isSuccess ? 'API connected' : 'Connecting…'}
        </p>
      </header>

      {offline ? (
        <div className="panel offline" role="alert">
          <h2>The API is not running</h2>
          <p>
            This page could not reach <code>{API_BASE}</code>. Start the backend from the project folder, and this page reconnects
            by itself:
          </p>
          <pre>uv run uvicorn backend.app.main:create_app --factory --reload</pre>
        </div>
      ) : (
        <Outlet />
      )}
    </div>
  )
}
