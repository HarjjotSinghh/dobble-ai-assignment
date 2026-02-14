/**
 * Chat Interface Component - Refined Minimalist Design
 */

import { useState, useRef, useEffect } from 'react';
import { chatAPI } from '../services/api';
import {
  Send,
  PlusCircle,
  Sparkles,
  Terminal,
  Info,
  ChevronDown,
  RefreshCcw,
  Bot,
  User
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export default function ChatInterface({ role }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: role === 'doctor'
        ? "Hello! I'm your CareBridge Intelligence. I've analyzed your current practice data. How can I assist you today?\n\n- **Practice Analytics**: \"Yesterday's patient summary\"\n- **Schedule Insights**: \"List my afternoon appointments\"\n- **Condition Trends**: \"Patients with respiratory issues this week\"\n- **Smart Reports**: \"Generate weekly efficiency report\""
        : "Welcome to CareBridge. I'm here to streamline your healthcare journey. What can I do for you?\n\n- **Smart Booking**: \"Schedule a consultation with Dr. Ahuja for Friday morning\"\n- **Availability**: \"When is Dr. Sharma free next?\"\n- **My Care**: \"Review my upcoming visits\"\n- **Management**: \"Reschedule my existing appointment\"",
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const res = await chatAPI.sendMessage(userMessage, sessionId);
      const { reply, session_id, actions_taken } = res.data;

      setSessionId(session_id);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: reply,
          actions: actions_taken,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'I encountered an unexpected interruption in our connection. Please try resending your request.',
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const startNewSession = () => {
    setSessionId(null);
    setMessages([messages[0]]);
  };

  const samplePrompts = role === 'doctor'
    ? ['Yesterday\'s summary', 'Today\'s load', 'Weekly trends', 'Fever patients']
    : ['Book Dr. Ahuja tomorrow', 'Check Dr. Sharma', 'My appointments', 'Who is available?'];

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto bg-white rounded-[2.5rem] border border-slate-300 overflow-hidden">
      {/* Header */}
      <div className="px-8 py-5 border-b border-slate-200 flex items-center justify-between bg-slate-50 sticky top-0 z-10">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 bg-slate-900 rounded-2xl flex items-center justify-center text-white border border-slate-950">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-display font-bold text-slate-950">CareBridge Intelligence</h3>
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-emerald-600 rounded-full animate-pulse" />
              <p className="text-xs uppercase tracking-widest text-slate-700 font-black">Active Engine</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={startNewSession}
            className="p-2 text-slate-700 hover:text-slate-950 hover:bg-slate-100 rounded-xl transition-all border border-slate-200"
            title="Reset Conversation"
          >
            <RefreshCcw className="w-5 h-5" />
          </button>
          <div className="h-6 w-px bg-slate-200 mx-2" />
          <button className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg text-sm font-black text-slate-900 hover:bg-slate-50 transition-all border border-slate-300 uppercase tracking-widest">
            Settings <ChevronDown className="w-3 h-3 text-slate-500" />
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-8 py-10 space-y-10 custom-scrollbar bg-white">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex items-start gap-5 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} animate-slide-up`}
          >
            <div className={`w-10 h-10 rounded-2xl flex-shrink-0 flex items-center justify-center border ${msg.role === 'user'
              ? 'bg-slate-100 border-slate-300 text-slate-900'
              : 'bg-slate-900 border-slate-950 text-white'
              }`}>
              {msg.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
            </div>

            <div className={`flex flex-col max-w-[75%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div
                className={`rounded-[1.5rem] px-6 py-4 border ${msg.role === 'user'
                  ? 'bg-slate-50 text-slate-950 border-slate-300 rounded-tr-none'
                  : msg.error
                    ? 'bg-red-50 text-red-900 border-red-200 rounded-tl-none font-medium'
                    : 'bg-white text-slate-950 border-slate-200 rounded-tl-none'
                  }`}
              >
                <div className="text-sm prose prose-sm max-w-none leading-relaxed font-medium">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>

                {/* MCP Actions Visualization */}
                {msg.actions && msg.actions.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-slate-200">
                    <div className="flex items-center gap-2 mb-2">
                      <Terminal className="w-3 h-3 text-slate-700" />
                      <span className="text-xs uppercase tracking-widest text-slate-700 font-black">System Execution</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {msg.actions.map((action, k) => (
                        <div
                          key={k}
                          className="flex items-center gap-1.5 bg-slate-100 border border-slate-300 px-2.5 py-1 rounded-md"
                        >
                          <div className="w-1.5 h-1.5 bg-slate-900 rounded-full opacity-70" />
                          <span className="text-xs font-mono text-slate-900 font-bold">{action}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <span className="mt-2 text-xs text-slate-500 font-black uppercase tracking-widest">
                {msg.role === 'user' ? 'Patient Transmission' : 'Intelligence Response'}
              </span>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-start gap-5 animate-fade-in">
            <div className="w-10 h-10 rounded-2xl bg-slate-900 border border-slate-950 text-white flex items-center justify-center flex-shrink-0">
              <Bot className="w-5 h-5" />
            </div>
            <div className="bg-slate-50 rounded-[1.5rem] rounded-tl-none px-6 py-4 flex items-center gap-1.5 border border-slate-300">
              <div className="w-1.5 h-1.5 bg-slate-900 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <div className="w-1.5 h-1.5 bg-slate-900 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <div className="w-1.5 h-1.5 bg-slate-900 rounded-full animate-bounce" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Section */}
      <div className="p-8 border-t border-slate-200 bg-slate-50">
        {/* Sample Prompts */}
        {messages.length <= 1 && (
          <div className="flex flex-wrap gap-2 mb-6 justify-center">
            {samplePrompts.map((prompt, i) => (
              <button
                key={i}
                onClick={() => { setInput(prompt); inputRef.current?.focus(); }}
                className="text-xs font-bold uppercase tracking-wider bg-white text-slate-700 border border-slate-300 px-4 py-2 rounded-xl hover:border-slate-900 hover:text-slate-950 transition-all hover:bg-slate-100"
              >
                {prompt}
              </button>
            ))}
          </div>
        )}

        <div className="relative group">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 flex items-center gap-2">
            <button className="p-1.5 text-slate-600 hover:text-slate-950 hover:bg-white border border-transparent hover:border-slate-300 rounded-lg transition-all">
              <PlusCircle className="w-5 h-5" />
            </button>
          </div>

          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Describe what you need..."
            className="w-full bg-white border border-slate-300 rounded-2xl pl-16 pr-16 py-5 focus:outline-none focus:ring-4 focus:ring-slate-900/10 focus:border-slate-900 transition-all text-sm placeholder:text-slate-500 font-bold text-slate-950 shadow-inner"
            disabled={loading}
          />

          <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-3">
            <div className="hidden md:flex items-center gap-1.5 px-2 py-1 bg-slate-100 border border-slate-300 rounded text-xs font-black text-slate-700 uppercase tracking-tighter">
              <span className="border border-slate-400 px-1 rounded bg-white">Enter</span>
              <span>to send</span>
            </div>
            <button
              onClick={sendMessage}
              disabled={!input.trim() || loading}
              className="w-10 h-10 bg-slate-900 text-white rounded-xl flex items-center justify-center border border-slate-950 hover:bg-slate-950 disabled:opacity-30 disabled:grayscale transition-all"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="mt-4 flex items-center justify-center gap-4">
          <p className="text-xs text-slate-600 font-black uppercase tracking-[0.1em] flex items-center gap-1">
            <Info className="w-3 h-3 text-slate-500" />
            AI Disclaimer: Medical accuracy not guaranteed.
          </p>
          {sessionId && (
            <>
              <div className="w-1 h-1 bg-slate-400 rounded-full" />
              <p className="text-xs text-slate-700 font-mono font-black tracking-widest">ID: {sessionId}</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}