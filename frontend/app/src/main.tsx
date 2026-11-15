import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';

import { Component, type ReactNode } from 'react';

class Boundary extends Component<{ children: ReactNode }, { err: boolean }> {
  state = { err: false };
  static getDerivedStateFromError() { return { err: true }; }
  render() {
    if (!this.state.err) return this.props.children;
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--app-bg)', padding: 16 }}>
        <div role="alert" data-testid="app-error" style={{ background: 'var(--panel)', border: '1px solid var(--line-soft)', borderRadius: 12, padding: 24, maxWidth: 380, boxShadow: 'var(--e2)' }}>
          <h1 style={{ fontFamily: 'var(--font-head)', fontSize: 22, margin: '0 0 8px' }}>Something went wrong</h1>
          <p style={{ margin: '0 0 16px' }}>This place could not be shown. Your fields are safe.</p>
          <button className="btn btn-primary" onClick={() => { history.replaceState(null, '', location.pathname); location.reload(); }}>Back to fields</button>
        </div>
      </div>
    );
  }
}

createRoot(document.getElementById('root')!).render(<Boundary><App /></Boundary>);
