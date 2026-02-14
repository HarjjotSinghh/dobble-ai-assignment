/**
 * Login / Register Page - Refined Minimalist Design
 */

import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Stethoscope, ArrowRight, User, Mail, Lock, Briefcase } from 'lucide-react';

export default function Login() {
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const [form, setForm] = useState({
    email: '',
    password: '',
    name: '',
    role: 'patient',
    specialization: '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isRegister) {
        await register(form);
      } else {
        await login(form.email, form.password);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const quickLogin = async (email) => {
    setLoading(true);
    setError('');
    try {
      await login(email, 'password123');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 font-sans">
      <div className="w-full max-w-lg flex flex-col gap-8 animate-slide-up">
        {/* Header Section */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-white border border-slate-200 rounded-2xl mb-4">
            <Stethoscope className="w-7 h-7 text-slate-900" />
          </div>
          <h1 className="text-4xl font-display font-semibold tracking-tight text-slate-950">
            CareBridge
          </h1>
          <p className="text-slate-500 font-medium tracking-wide text-sm uppercase">
            Intelligence in Healthcare
          </p>
        </div>

        {/* Main Content Card */}
        <div className="bg-white rounded-[2rem] border border-slate-200 p-10">
          <div className="mb-8">
            <h2 className="text-2xl font-display font-semibold text-slate-900">
              {isRegister ? 'Create your account' : 'Welcome back'}
            </h2>
            <p className="text-slate-500 mt-2 font-medium">
              {isRegister
                ? 'Join our network of healthcare professionals and patients.'
                : 'Sign in to access your appointments and health records.'}
            </p>
          </div>

          {error && (
            <div className="bg-red-50 text-red-700 text-sm px-4 py-3 rounded-xl mb-6 border border-red-200 flex items-center gap-2 font-medium">
              <span className="w-1.5 h-1.5 bg-red-600 rounded-full animate-pulse" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {isRegister && (
              <div className="grid grid-cols-1 gap-5">
                <div className="relative group">
                  <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 transition-colors group-focus-within:text-slate-900" />
                  <input
                    type="text"
                    placeholder="Full Name"
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-slate-900 focus:ring-4 focus:ring-slate-900/5 transition-all duration-300 outline-none pl-12 text-slate-900 placeholder:text-slate-500 font-medium"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    required
                  />
                </div>
                <div className="flex p-1 bg-slate-100 rounded-xl border border-slate-200">
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, role: 'patient' })}
                    className={`flex-1 py-2 text-sm font-bold rounded-lg transition-all border ${form.role === 'patient' ? 'bg-white border-slate-300 text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900 border-transparent hover:bg-slate-200/50'}`}
                  >
                    Patient
                  </button>
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, role: 'doctor' })}
                    className={`flex-1 py-2 text-sm font-bold rounded-lg transition-all border ${form.role === 'doctor' ? 'bg-white border-slate-300 text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900 border-transparent hover:bg-slate-200/50'}`}
                  >
                    Doctor
                  </button>
                </div>
                {form.role === 'doctor' && (
                  <div className="relative group animate-fade-in">
                    <Briefcase className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 transition-colors group-focus-within:text-slate-900" />
                    <input
                      type="text"
                      placeholder="Specialization (e.g. Cardiologist)"
                      className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-slate-900 focus:ring-4 focus:ring-slate-900/5 transition-all duration-300 outline-none pl-12 text-slate-900 placeholder:text-slate-500 font-medium"
                      value={form.specialization}
                      onChange={(e) => setForm({ ...form, specialization: e.target.value })}
                      required
                    />
                  </div>
                )}
              </div>
            )}

            <div className="relative group">
              <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 transition-colors group-focus-within:text-slate-900" />
              <input
                type="email"
                placeholder="Email Address"
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-slate-900 focus:ring-4 focus:ring-slate-900/5 transition-all duration-300 outline-none pl-12 text-slate-900 placeholder:text-slate-500 font-medium"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
              />
            </div>

            <div className="relative group">
              <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 transition-colors group-focus-within:text-slate-900" />
              <input
                type="password"
                placeholder="Password"
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-slate-900 focus:ring-4 focus:ring-slate-900/5 transition-all duration-300 outline-none pl-12 text-slate-900 placeholder:text-slate-500 font-medium"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full px-6 py-3 bg-slate-900 text-white border border-slate-950 rounded-xl font-bold hover:bg-slate-800 transition-all duration-300 active:scale-[0.98] flex items-center justify-center gap-2 group uppercase tracking-widest text-sm shadow-lg shadow-slate-900/20"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  {isRegister ? 'Create Account' : 'Sign In'}
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>

          <div className="mt-8 text-center">
            <button
              onClick={() => { setIsRegister(!isRegister); setError(''); }}
              className="text-slate-600 text-sm font-bold hover:text-slate-900 transition-colors uppercase tracking-widest hover:underline decoration-2 underline-offset-4"
            >
              {isRegister ? 'Already have an account? Sign In' : "Don't have an account? Create one"}
            </button>
          </div>
        </div>

        {/* Quick Demo Login - Discrete Design */}
        <div className="bg-slate-100 rounded-2xl p-6 border border-slate-200">
          <p className="text-xs font-black text-slate-500 uppercase tracking-[0.2em] mb-4 text-center">Quick Access Demo</p>
          <div className="grid grid-cols-2 gap-3">
            {[
              { name: 'John (Patient)', email: 'john@email.com', color: 'bg-white text-slate-900 border-slate-200 hover:border-slate-400' },
              { name: 'Jane (Patient)', email: 'jane@email.com', color: 'bg-white text-slate-900 border-slate-200 hover:border-slate-400' },
              { name: 'Dr. Ahuja', email: 'dr.ahuja@hospital.com', color: 'bg-slate-900 text-white border-slate-900 hover:bg-slate-800' },
              { name: 'Dr. Sharma', email: 'dr.sharma@hospital.com', color: 'bg-slate-900 text-white border-slate-900 hover:bg-slate-800' },
            ].map((user) => (
              <button
                key={user.email}
                onClick={() => quickLogin(user.email)}
                className={`px-4 py-2 ${user.color} border rounded-xl text-xs font-bold transition-all uppercase tracking-tighter shadow-sm`}
              >
                {user.name}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
