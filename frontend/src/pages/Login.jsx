import React, { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { LockKeyhole, Mail, ShieldCheck } from 'lucide-react';
import { isReviewer, useAuth } from '../auth/AuthContext';

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to={isReviewer(user) ? '/' : '/claims'} replace />;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const signedInUser = await login(email, password);
      const requested = location.state?.from;
      navigate(requested || (isReviewer(signedInUser) ? '/' : '/claims'), { replace: true });
    } catch (failure) {
      setError(failure.response?.data?.detail || 'Sign-in failed. Check your company email and password.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-shell">
      <div className="login-card glass-card">
        <div className="login-mark"><ShieldCheck size={29} /></div>
        <p className="login-eyebrow">AUDITAI · SECURE WORKSPACE</p>
        <h1>Sign in to your audit workspace</h1>
        <p className="login-subtitle">Use your provisioned company account. Your access to claims and review actions follows your assigned roles.</p>
        <form onSubmit={handleSubmit} className="login-form">
          <label htmlFor="login-email">Company email</label>
          <div className="login-input-wrap"><Mail size={18} /><input id="login-email" className="input" type="email" autoComplete="username" value={email} onChange={event => setEmail(event.target.value)} required placeholder="name@company.com" /></div>
          <label htmlFor="login-password">Password</label>
          <div className="login-input-wrap"><LockKeyhole size={18} /><input id="login-password" className="input" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required placeholder="Enter your password" /></div>
          {error && <p className="login-error" role="alert">{error}</p>}
          <button className="btn btn-primary login-submit" type="submit" disabled={submitting}>{submitting ? 'Signing in…' : 'Sign in'}</button>
        </form>
        <p className="login-help">Need access? Ask your company administrator to provision your employee ID and role.</p>
      </div>
    </main>
  );
}
