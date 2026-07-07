import { Component, type ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';
import styles from './ErrorBoundary.module.css';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

/**
 * Guards the dashboard subtree. A bad API response or render-time crash shows a
 * themed fallback with a reload action instead of blanking the screen.
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: '' };

  static getDerivedStateFromError(error: unknown): State {
    return {
      hasError: true,
      message: error instanceof Error ? error.message : 'Unexpected error',
    };
  }

  componentDidCatch(error: unknown) {
    console.error('Dashboard error boundary caught:', error);
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className={styles.root}>
        <div className={styles.panel}>
          <div className={styles.iconWrap}>
            <AlertTriangle size={22} />
          </div>
          <h1 className={styles.title}>Something went wrong</h1>
          <p className={styles.message}>{this.state.message}</p>
          <button type="button" className={styles.reload} onClick={this.handleReload}>
            <RotateCcw size={14} />
            Reload
          </button>
        </div>
      </div>
    );
  }
}
