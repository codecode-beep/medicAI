import { useEffect, useRef, useState } from 'react';
import { Send, Bot, User, Paperclip, Loader2 } from 'lucide-react';
import { chatApi, uploadApi } from '../lib/api';
import { useAppStore, useAuthStore } from '../store';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState('');
  const { chatSessionId, setChatSessionId, saveToHistory } = useAppStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const { user } = useAuthStore();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streaming]);

  const sendMessage = async (message: string) => {
    const sessionId = chatSessionId || crypto.randomUUID().replace(/-/g, '');
    if (!chatSessionId) setChatSessionId(sessionId);

    setMessages((prev) => [...prev, { role: 'user', content: message }]);
    setStreaming(true);
    setError('');

    try {
      const { data } = await chatApi.send(message, sessionId);
      setChatSessionId(data.session_id);
      setMessages((prev) => [...prev, { role: 'assistant', content: data.message }]);
    } catch {
      setError('Could not reach the AI assistant. Ensure the backend is running on port 8000.');
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            'Sorry, I could not process your message. Please check that the backend is running and your Gemini API key is configured.',
        },
      ]);
    } finally {
      setStreaming(false);
    }
  };

  const handleSend = () => {
    if (!input.trim() || streaming) return;
    const text = input.trim();
    setInput('');
    sendMessage(text);
  };

  const handleFileAttach = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const question = input.trim() || 'Analyze this medical file and explain the findings.';
    setInput('');
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: `[Uploaded: ${file.name}] ${question}` },
    ]);
    setStreaming(true);
    setError('');
    try {
      await uploadApi.analyze(file, saveToHistory, question);
      const sessionId = chatSessionId || crypto.randomUUID().replace(/-/g, '');
      if (!chatSessionId) setChatSessionId(sessionId);
      const { data } = await chatApi.send(question, sessionId);
      setChatSessionId(data.session_id);
      setMessages((prev) => [...prev, { role: 'assistant', content: data.message }]);
    } catch {
      setError('File upload or analysis failed.');
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I could not analyze that file. Please try again.' },
      ]);
    } finally {
      setStreaming(false);
    }
    if (fileRef.current) fileRef.current.value = '';
  };

  return (
    <div className="flex flex-col h-full min-h-[calc(100vh-0px)]">
      <div className="p-6 border-b bg-white shrink-0">
        <h1 className="text-xl font-bold">AI Medical Assistant</h1>
        <p className="text-sm text-slate-500">
          Ask questions about your reports, scans, and medical history
          {user ? ` · ${user.full_name}` : ''}
        </p>
        {error && <p className="text-sm text-red-500 mt-2">{error}</p>}
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-16 text-slate-400">
            <Bot className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>Start a conversation with MedIntel AI</p>
            <p className="text-sm mt-1">Try: &quot;What medicines am I taking?&quot; or upload a scan</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-primary-600" />
              </div>
            )}
            <div
              className={`max-w-[70%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-primary-600 text-white rounded-br-md'
                  : 'bg-white border shadow-sm rounded-bl-md'
              }`}
            >
              {msg.content}
            </div>
            {msg.role === 'user' && (
              <div className="w-8 h-8 bg-slate-200 rounded-full flex items-center justify-center shrink-0">
                <User className="w-4 h-4 text-slate-600" />
              </div>
            )}
          </div>
        ))}
        {streaming && (
          <div className="flex gap-3 items-center text-slate-500 text-sm">
            <Loader2 className="w-5 h-5 animate-spin text-primary-600" />
            <span>MedIntel AI is thinking…</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-4 border-t bg-white shrink-0">
        <div className="flex gap-2 max-w-4xl mx-auto">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="p-3 text-slate-400 hover:text-primary-600 hover:bg-slate-50 rounded-lg"
            disabled={streaming}
          >
            <Paperclip className="w-5 h-5" />
          </button>
          <input ref={fileRef} type="file" className="hidden" accept=".pdf,image/*" onChange={handleFileAttach} />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Ask about your medical reports..."
            className="flex-1 px-4 py-3 border rounded-xl focus:ring-2 focus:ring-primary-500 outline-none"
            disabled={streaming}
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={!input.trim() || streaming}
            className="px-5 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
