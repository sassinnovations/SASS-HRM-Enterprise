import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './style.css';

/** Show an actionable error screen instead of an empty viewport if React crashes. */
class AppErrorBoundary extends React.Component<
  {children: React.ReactNode},
  {failed: boolean; message: string}
> {
  state = {failed: false, message: ''};
  static getDerivedStateFromError(error: Error) {
    return {failed: true, message: error?.message || 'Unknown rendering error'};
  }
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[SASS HRM] React rendering failure:', error, info.componentStack);
  }
  render() {
    if (this.state.failed) {
      return (
        <main className="sass-boot-failure" role="alert">
          <section>
            <h1>SASS HRM could not display this screen</h1>
            <p>The frontend hit a JavaScript rendering error. The error message is shown below, so the page will no longer fail silently.</p>
            <pre>{this.state.message}</pre>
            <p>Open developer tools with <strong>F12</strong>, select <strong>Console</strong>, and check the first red error for details.</p>
            <button type="button" onClick={() => window.location.reload()}>Reload app</button>
          </section>
        </main>
      );
    }
    return this.props.children;
  }
}

const mount = document.getElementById('root');
if (!mount) {
  throw new Error('Missing #root element in index.html');
}
ReactDOM.createRoot(mount).render(
  <React.StrictMode>
    <AppErrorBoundary><App /></AppErrorBoundary>
  </React.StrictMode>
);
