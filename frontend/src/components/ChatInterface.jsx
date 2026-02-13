/**
 * Chat Interface Component - The main AI assistant interaction.
 *
 * Features:
 * - Natural language prompt input
 * - Multi-turn conversation with context retention
 * - Displays AI actions taken (MCP tool calls)
 * - Typing indicator while agent processes
 * - Session management for conversation history
 */

import { useState, useRef, useEffect } from 'react';
import { chatAPI } from '../services/api';

export default function ChatInterface({ role }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: role === 'doctor'
        ? "Hello! I'm your AI assistant. I can help you with:\n\n- **View appointment stats**: \"How many patients visited yesterday?\"\n- **Today's schedule**: \"How many appointments do I have today?\"\n- **Patient analytics**: \"How many patients with fever?\"\n- **Generate reports**: \"Send me a summary of this week\"\n\nWhat would you like to know?"
        : "Hello! I'm your AI appointment assistant. I can help you with:\n\n- **Book appointments**: \"I want to book an appointment with Dr. Ahuja tomorrow morning\"\n- **Check availability**: \"Is Dr. Sharma available on Friday?\"\n- **View appointments**: \"Show my upcoming appointments\"\n- **Cancel appointments**: \"Cancel my appointment #5\"\n\nHow can I help you today?",
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    chatAPI.getSessions().then((res) => setSessions(res.data)).catch(() => {});
  }, []);

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
          content: 'Sorry, I encountered an error processing your request. Please try again.',
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
    setMessages([messages[0]]); // Keep welcome message
  };

  const samplePrompts = role === 'doctor'
    ? [
        'How many patients visited yesterday?',
        'How many appointments do I have today?',
        'Show me appointments for this week',
        'How many patients with fever?',
      ]
    : [
        'I want to book with Dr. Ahuja tomorrow morning',
        "Check Dr. Sharma's availability for Friday",
        'Show my upcoming appointments',
        'Which doctors are available?',
      ];

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center">
            <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">AI Assistant</h3>
            <p className="text-xs text-slate-500">Powered by MCP + LLM</p>
          </div>
        </div>
        <button
          onClick={startNewSession}
          className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
        >
          New Chat
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`animate-fade-in flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white'
                  : msg.error
                  ? 'bg-red-50 text-red-700 border border-red-200'
                  : 'bg-slate-100 text-slate-800'
              }`}
            >
              {/* Message content with basic markdown rendering */}
              <div className="text-sm whitespace-pre-wrap leading-relaxed">
                {msg.content.split('\n').map((line, j) => (
                  <span key={j}>
                    {line.replace(/\*\*(.*?)\*\*/g, (_, text) => text)}
                    {j < msg.content.split('\n').length - 1 && <br />}
                  </span>
                ))}
              </div>

              {/* Show MCP actions taken */}
              {msg.actions && msg.actions.length > 0 && (
                <div className="mt-2 pt-2 border-t border-slate-200">
                  <p className="text-xs text-slate-500 mb-1">MCP Tools Used:</p>
                  <div className="flex flex-wrap gap-1">
                    {msg.actions.map((action, k) => (
                      <span
                        key={k}
                        className="inline-block text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full"
                      >
                        {action}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex justify-start animate-fade-in">
            <div className="bg-slate-100 rounded-2xl px-4 py-3 flex items-center gap-1.5">
              <div className="w-2 h-2 bg-slate-400 rounded-full typing-dot"></div>
              <div className="w-2 h-2 bg-slate-400 rounded-full typing-dot"></div>
              <div className="w-2 h-2 bg-slate-400 rounded-full typing-dot"></div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Sample prompts */}
      {messages.length <= 1 && (
        <div className="px-4 pb-2">
          <div className="flex flex-wrap gap-2">
            {samplePrompts.map((prompt, i) => (
              <button
                key={i}
                onClick={() => { setInput(prompt); inputRef.current?.focus(); }}
                className="text-xs bg-slate-100 text-slate-600 px-3 py-1.5 rounded-full hover:bg-slate-200 transition-colors"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-slate-100">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Type your message..."
            className="flex-1 px-4 py-2.5 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="px-4 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        {sessionId && (
          <p className="text-xs text-slate-400 mt-1 text-center">
            Session #{sessionId} - Multi-turn conversation active
          </p>
        )}
      </div>
    </div>
  );
}
