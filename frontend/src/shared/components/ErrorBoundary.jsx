import { Component } from 'react';

// In other words: if one page crashes, show a readable message instead of a blank screen.
export default class ErrorBoundary extends Component {
  state = { error: null };
  static getDerivedStateFromError(error) { return { error }; }
  componentDidUpdate(prev) { if (this.state.error && prev.resetKey !== this.props.resetKey) this.setState({ error: null }); }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div role="alert" className="card m-6 max-w-xl p-6">
        <h2 className="text-xl font-semibold text-white">Something went wrong on this screen</h2>
        <p className="mt-2 font-mono text-xs text-red-300">{String(this.state.error.message || this.state.error)}</p>
        <button className="btn-solid mt-4" onClick={() => this.setState({ error: null })}>Try again</button>
      </div>
    );
  }
}
