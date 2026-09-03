import React, { ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          aria-live="assertive"
          className="error-boundary"
          style={{ padding: '2rem', textAlign: 'center', color: 'var(--text)' }}
        >
          <h2 style={{ fontSize: '1.2rem', marginBottom: '0.5rem', color: 'var(--text)' }}>
            Ошибка загрузки раздела
          </h2>
          <p style={{ color: 'var(--text-dim)' }}>
            {this.state.error?.message || 'Неизвестная ошибка'}
          </p>
          <button
            className="btn"
            onClick={() => this.setState({ hasError: false, error: undefined })}
            style={{ marginTop: '1rem', padding: '0.5rem 1rem', cursor: 'pointer' }}
          >
            Попробовать снова
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
