import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import chatService from '../services/chatService';
import { documentService } from '../services/documentService';
import type { Conversation, Message, Document, Citation } from '../types';
import { 
  Send, 
  Plus, 
  Trash2, 
  Edit3, 
  Download, 
  Copy, 
  ThumbsUp, 
  ThumbsDown, 
  BookOpen, 
  ChevronRight,
  ChevronDown,
  MessageSquare,
  Sparkles,
  Info,
  Check,
  X
} from 'lucide-react';

export const Chat: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Conversations list & status
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  
  // Mobile drawer state for threads list
  const [mobileThreadsOpen, setMobileThreadsOpen] = useState(false);
  
  // Active messages list & state
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);

  // Suggested Questions
  const suggestions = [
    "What is the main summary of this document?",
    "List the key findings page-by-page.",
    "Are there any statistical tables or charts mentioned?",
    "Explain the methodology described in the document."
  ];

  // Document filters (RAG bounds)
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  // Active Citation inspection sidebar/drawer
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  
  // Clipboard states
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Rename states
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editingConvValue, setEditingConvValue] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom helper
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, chatLoading, loading]);

  // Load conversations & documents list
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      try {
        const [convList, docList] = await Promise.all([
          chatService.listConversations(),
          documentService.list()
        ]);
        setConversations(convList);
        // Only show processed docs as filters
        setDocuments(docList.filter(d => d.status === 'processed'));

        // Load conversation from URL param if available
        const urlConvId = searchParams.get('conv_id');
        if (urlConvId && convList.some(c => c.id === urlConvId)) {
          handleSelectConversation(urlConvId);
        } else if (convList.length > 0) {
          handleSelectConversation(convList[0].id);
        }
      } catch (err) {
        console.error('Failed to load initial chat configurations:', err);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const handleSelectConversation = async (convId: string) => {
    setActiveConvId(convId);
    setSearchParams({ conv_id: convId });
    setMobileThreadsOpen(false);
    setChatLoading(true);
    try {
      const history = await chatService.getHistory(convId);
      setMessages(history);
    } catch (err) {
      console.error('Failed to load conversation history:', err);
    } finally {
      setChatLoading(false);
    }
  };

  const handleNewChat = () => {
    setActiveConvId(null);
    setMessages([]);
    searchParams.delete('conv_id');
    setSearchParams(searchParams);
    setMobileThreadsOpen(false);
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim() || loading) return;
    
    // Add user message optimistically
    const userMsgText = text.trim();
    setInputMessage('');
    
    // Mock user message record to display in list immediately
    const tempUserMsg: Message = {
      id: `temp_${Date.now()}`,
      conversation_id: activeConvId || '',
      user_id: '',
      role: 'user',
      content: userMsgText,
      sources: [],
      feedback: null,
      created_at: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, tempUserMsg]);
    setLoading(true);

    try {
      const res = await chatService.sendMessage(
        userMsgText,
        activeConvId || undefined,
        selectedDocIds
      );

      // If new conversation was created on the backend
      if (!activeConvId) {
        setActiveConvId(res.conversation_id);
        setSearchParams({ conv_id: res.conversation_id });
        // Refresh conversations sidebar list
        const updatedConvs = await chatService.listConversations();
        setConversations(updatedConvs);
      }

      setMessages(prev => {
        // Remove temporary message and append verified list
        const filtered = prev.filter(m => !m.id.startsWith('temp_'));
        // Include user query and assistant response
        return [
          ...filtered,
          { ...tempUserMsg, conversation_id: res.conversation_id },
          res.message
        ];
      });
    } catch (err: any) {
      console.error('Error sending message:', err);
      const detailMsg = err?.response?.data?.detail || err?.message || 'Could not generate chat answer. Please check your network or backend configuration.';
      alert(`Chat Error: ${detailMsg}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this chat thread?')) return;
    
    try {
      await chatService.delete(convId);
      setConversations(prev => prev.filter(c => c.id !== convId));
      if (activeConvId === convId) {
        handleNewChat();
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  const startRenameConversation = (conv: Conversation, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingConvId(conv.id);
    setEditingConvValue(conv.title);
  };

  const handleRenameSubmit = async () => {
    if (!editingConvId || !editingConvValue.trim()) return;
    try {
      await chatService.rename(editingConvId, editingConvValue.trim());
      setConversations(prev => 
        prev.map(c => c.id === editingConvId ? { ...c, title: editingConvValue.trim() } : c)
      );
      setEditingConvId(null);
    } catch (err) {
      console.error('Failed to rename conversation:', err);
    }
  };

  const handleFeedback = async (msgId: string, feedback: 'liked' | 'disliked') => {
    const targetMsg = messages.find(m => m.id === msgId);
    const newFeedback = targetMsg?.feedback === feedback ? null : feedback;
    
    try {
      await chatService.submitFeedback(msgId, newFeedback);
      setMessages(prev => 
        prev.map(m => m.id === msgId ? { ...m, feedback: newFeedback } : m)
      );
    } catch (err) {
      console.error('Failed to save message feedback:', err);
    }
  };

  const copyToClipboard = (text: string, msgId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(msgId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleDownloadChat = () => {
    if (messages.length === 0) return;
    const activeConv = conversations.find(c => c.id === activeConvId);
    const title = activeConv ? activeConv.title : 'New Chat Session';
    chatService.exportToMarkdown(title, messages);
  };

  const handleDocFilterToggle = (docId: string) => {
    setSelectedDocIds(prev => 
      prev.includes(docId) ? prev.filter(id => id !== docId) : [...prev, docId]
    );
  };

  // Simple Markdown parser implementation for code block / bullets / bold
  const renderMessageContent = (content: string) => {
    const parts = content.split(/(```[\s\S]*?```)/g);
    return parts.map((part, idx) => {
      if (part.startsWith('```')) {
        const lines = part.split('\n');
        const code = lines.slice(1, lines.length - 1).join('\n');
        return (
          <pre key={idx} className="bg-dark-900 border border-dark-800 rounded-xl p-3 sm:p-4 my-2.5 overflow-x-auto text-xs font-mono text-brand-300 max-w-full">
            <code>{code}</code>
          </pre>
        );
      }
      
      const formattedLines = part.split('\n').map((line, lIdx) => {
        if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
          return (
            <ul key={lIdx} className="list-disc pl-5 sm:pl-6 my-1">
              <li>{line.trim().substring(2)}</li>
            </ul>
          );
        }
        return <p key={lIdx} className="mb-2 leading-relaxed break-words">{line}</p>;
      });
      return <div key={idx}>{formattedLines}</div>;
    });
  };

  // Content helper for threads list items
  const renderThreadsList = () => (
    <div className="flex-1 overflow-y-auto p-3 space-y-1.5 min-h-0">
      {loading ? (
        <div className="text-center py-6 text-xs text-dark-500">Loading threads...</div>
      ) : conversations.length === 0 ? (
        <div className="text-center py-6 text-xs text-dark-500">No conversations.</div>
      ) : (
        conversations.map((conv) => {
          const isActive = activeConvId === conv.id;
          const isEditing = editingConvId === conv.id;
          return (
            <div
              key={conv.id}
              onClick={() => !isEditing && handleSelectConversation(conv.id)}
              className={`
                w-full flex items-center justify-between px-3.5 py-3 rounded-xl cursor-pointer text-xs font-medium transition-all group border
                ${isActive 
                  ? 'bg-brand-600/10 border-brand-500/20 text-brand-400 font-semibold' 
                  : 'border-transparent text-dark-400 hover:bg-dark-800/40 hover:text-dark-200'
                }
              `}
            >
              <div className="flex items-center space-x-2.5 min-w-0 flex-1 pr-2">
                <BookOpen className="h-4 w-4 shrink-0" />
                
                {isEditing ? (
                  <input
                    type="text"
                    value={editingConvValue}
                    onChange={(e) => setEditingConvValue(e.target.value)}
                    onBlur={handleRenameSubmit}
                    onKeyDown={(e) => e.key === 'Enter' && handleRenameSubmit()}
                    className="w-full bg-dark-900 border border-brand-500/50 rounded px-1.5 py-0.5 text-white text-[11px] focus:outline-none"
                    onClick={(e) => e.stopPropagation()}
                    autoFocus
                  />
                ) : (
                  <span className="truncate">{conv.title}</span>
                )}
              </div>
              
              {!isEditing && (
                <div className="flex items-center space-x-1 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                  <button 
                    onClick={(e) => startRenameConversation(conv, e)}
                    className="p-1 hover:bg-dark-800 text-dark-500 hover:text-brand-400 rounded transition-colors"
                  >
                    <Edit3 className="h-3.5 w-3.5" />
                  </button>
                  <button 
                    onClick={(e) => handleDeleteConversation(conv.id, e)}
                    className="p-1 hover:bg-red-500/10 text-dark-500 hover:text-red-400 rounded transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );

  return (
    <div className="h-full flex-1 flex flex-col lg:flex-row relative glass rounded-xl sm:rounded-2xl overflow-hidden shadow-2xl border border-dark-800/80 min-h-0">
      
      {/* 1. Left Desktop Sidebar: Chat list threads */}
      <aside className="hidden lg:flex w-64 border-r border-dark-800 flex-col justify-between shrink-0 bg-dark-900/40 min-h-0">
        <div className="p-4 border-b border-dark-800 flex items-center justify-between">
          <h3 className="text-sm font-bold text-white tracking-wide">Conversations</h3>
          <button 
            onClick={handleNewChat}
            className="p-1.5 bg-brand-600/10 hover:bg-brand-600/20 text-brand-400 rounded-lg border border-brand-500/15 transition-all text-xs font-semibold flex items-center space-x-1"
          >
            <Plus className="h-4 w-4" />
            <span>New Chat</span>
          </button>
        </div>

        {renderThreadsList()}

        {documents.length > 0 && (
          <div className="p-3 border-t border-dark-800">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`
                w-full flex items-center justify-between p-2.5 rounded-xl border text-xs font-semibold transition-all
                ${showFilters 
                  ? 'border-brand-500/30 bg-brand-500/5 text-brand-400' 
                  : 'border-dark-800 text-dark-400 hover:border-dark-700 hover:bg-dark-900/40'
                }
              `}
            >
              <span className="flex items-center space-x-2">
                <Sparkles className="h-4 w-4" />
                <span>Source Filtering</span>
              </span>
              {selectedDocIds.length > 0 && (
                <span className="h-5 w-5 bg-brand-600 text-white rounded-full flex items-center justify-center text-[10px]">
                  {selectedDocIds.length}
                </span>
              )}
            </button>
          </div>
        )}
      </aside>

      {/* Mobile Threads Modal Drawer (Slide-over overlay on mobile screens) */}
      {mobileThreadsOpen && (
        <div className="lg:hidden fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex flex-col justify-end sm:justify-center p-0 sm:p-4">
          <div className="w-full max-w-md bg-dark-900 border-t sm:border border-dark-800 rounded-t-2xl sm:rounded-2xl max-h-[80vh] flex flex-col overflow-hidden shadow-2xl">
            <div className="p-4 border-b border-dark-800 flex items-center justify-between bg-dark-950/50">
              <div className="flex items-center space-x-2">
                <MessageSquare className="h-5 w-5 text-brand-400" />
                <h3 className="text-sm font-bold text-white">Chat Threads</h3>
              </div>
              <div className="flex items-center space-x-2">
                <button 
                  onClick={handleNewChat}
                  className="px-3 py-1.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-semibold flex items-center space-x-1"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>New Chat</span>
                </button>
                <button 
                  onClick={() => setMobileThreadsOpen(false)}
                  className="p-1 text-dark-400 hover:text-white"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {renderThreadsList()}

            {documents.length > 0 && (
              <div className="p-3 border-t border-dark-800 bg-dark-950/30">
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className={`
                    w-full flex items-center justify-between p-2.5 rounded-xl border text-xs font-semibold transition-all
                    ${showFilters 
                      ? 'border-brand-500/30 bg-brand-500/5 text-brand-400' 
                      : 'border-dark-800 text-dark-400 hover:border-dark-700 hover:bg-dark-900/40'
                    }
                  `}
                >
                  <span className="flex items-center space-x-2">
                    <Sparkles className="h-4 w-4" />
                    <span>Source Filtering ({selectedDocIds.length > 0 ? `${selectedDocIds.length} active` : 'All docs'})</span>
                  </span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 2. Middle Content Area: Chat Viewport */}
      <section className="flex-1 flex flex-col justify-between min-w-0 bg-dark-950/20 min-h-0">
        
        {/* Chat Header */}
        <header className="p-3.5 sm:p-4 border-b border-dark-800 flex items-center justify-between bg-dark-900/40 backdrop-blur-md shrink-0">
          <div className="flex items-center space-x-2 min-w-0 flex-1 pr-2">
            {/* Mobile thread menu toggle button */}
            <button
              onClick={() => setMobileThreadsOpen(true)}
              className="lg:hidden flex items-center space-x-1.5 px-2.5 py-1.5 bg-dark-850 hover:bg-dark-800 border border-dark-700 rounded-xl text-xs font-semibold text-white transition-all shrink-0"
              title="Switch Chat Thread"
            >
              <MessageSquare className="h-4 w-4 text-brand-400" />
              <ChevronDown className="h-3.5 w-3.5 text-dark-400" />
            </button>

            <div className="min-w-0 flex-1">
              <h2 className="text-xs sm:text-sm font-bold text-white truncate">
                {activeConvId 
                  ? conversations.find(c => c.id === activeConvId)?.title || 'Active Conversation'
                  : 'New Chat Session'
                }
              </h2>
              {selectedDocIds.length > 0 && (
                <p className="text-[10px] text-brand-400 font-medium truncate">
                  Filtered to {selectedDocIds.length} document(s)
                </p>
              )}
            </div>
          </div>
          
          <div className="flex items-center space-x-2 shrink-0">
            {documents.length > 0 && (
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`lg:hidden p-2 rounded-xl border text-xs font-semibold transition-all ${
                  showFilters 
                    ? 'border-brand-500/30 bg-brand-500/10 text-brand-400' 
                    : 'border-dark-800 text-dark-400 hover:text-white'
                }`}
                title="Filter Sources"
              >
                <Sparkles className="h-4 w-4" />
              </button>
            )}

            {messages.length > 0 && (
              <button
                onClick={handleDownloadChat}
                className="p-2 hover:bg-dark-800 text-dark-400 hover:text-dark-100 border border-dark-800 rounded-xl transition-colors font-semibold text-xs flex items-center space-x-1.5"
                title="Download Conversation"
              >
                <Download className="h-4 w-4" />
                <span className="hidden sm:inline">Export</span>
              </button>
            )}
          </div>
        </header>

        {/* Source Filter checklist drawer (if active) */}
        {showFilters && documents.length > 0 && (
          <div className="p-3 border-b border-dark-800 bg-dark-900/70 backdrop-blur-md flex flex-col space-y-2 shrink-0">
            <p className="text-[10px] uppercase font-bold tracking-wider text-dark-500">Filter Search Context</p>
            <div className="flex flex-wrap gap-1.5 max-h-[90px] overflow-y-auto py-1">
              {documents.map((doc) => {
                const checked = selectedDocIds.includes(doc.id);
                return (
                  <button
                    key={doc.id}
                    onClick={() => handleDocFilterToggle(doc.id)}
                    className={`
                      px-2.5 py-1 rounded-full text-xs font-semibold transition-all border inline-flex items-center space-x-1.5
                      ${checked 
                        ? 'bg-brand-600/10 border-brand-500/30 text-brand-400' 
                        : 'bg-dark-900 border-dark-800 text-dark-400 hover:border-dark-700'
                      }
                    `}
                  >
                    {checked && <Check className="h-3 w-3" />}
                    <span className="truncate max-w-[130px]">{doc.name}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Message Log Viewport (Smooth Touch Scrolling) */}
        <div 
          className="flex-1 overflow-y-auto p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6 min-h-0 overscroll-contain"
          style={{ WebkitOverflowScrolling: 'touch' }}
        >
          {chatLoading ? (
            <div className="flex flex-col items-center justify-center h-full py-12 space-y-3">
              <svg className="animate-spin h-8 w-8 text-brand-500" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="text-dark-500 text-xs">Loading history logs...</span>
            </div>
          ) : messages.length === 0 ? (
            /* Prompt screen */
            <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto py-8 sm:py-12 px-2">
              <Sparkles className="h-8 sm:h-10 w-8 sm:w-10 text-brand-400 mb-3 animate-bounce" />
              <h3 className="text-lg sm:text-xl font-bold text-white">Ask your knowledge base</h3>
              <p className="text-xs text-dark-400 mt-2 leading-relaxed">
                Submit queries about your uploaded papers. Gemini will digest vectorized context segments and compile a concise response.
              </p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full mt-6">
                {suggestions.map((sug, sIdx) => (
                  <button
                    key={sIdx}
                    onClick={() => handleSendMessage(sug)}
                    className="p-3 bg-dark-900/80 border border-dark-800 hover:border-brand-500/30 rounded-xl hover:bg-dark-800/50 text-left text-xs font-medium text-dark-300 transition-all leading-normal active:scale-[0.98]"
                  >
                    {sug}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Message list */
            <div className="space-y-4 sm:space-y-6">
              {messages.map((msg) => {
                const isUser = msg.role === 'user';
                return (
                  <div 
                    key={msg.id} 
                    className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`
                      max-w-[92%] sm:max-w-[85%] rounded-2xl p-3.5 sm:p-4 border text-xs sm:text-sm
                      ${isUser 
                        ? 'bg-brand-600/15 border-brand-500/25 text-brand-100 rounded-tr-none' 
                        : 'glass border-dark-800 text-dark-100 rounded-tl-none'
                      }
                    `}>
                      {/* Message Content */}
                      <div className="space-y-2">
                        {renderMessageContent(msg.content)}
                      </div>

                      {/* Message Meta / Sources (only for Assistant) */}
                      {!isUser && (
                        <div className="mt-3.5 pt-3 border-t border-dark-800/80 flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2.5 sm:space-y-0 text-xs">
                          {/* Sources list */}
                          <div className="flex flex-wrap gap-1.5">
                            {msg.sources && msg.sources.length > 0 ? (
                              msg.sources.map((src, srcIdx) => (
                                <button
                                  key={srcIdx}
                                  onClick={() => setSelectedCitation(src)}
                                  className="px-2 py-0.5 bg-dark-900/90 border border-dark-800 hover:border-brand-500/30 rounded text-[10px] text-dark-300 hover:text-brand-400 font-semibold transition-all inline-flex items-center space-x-1"
                                >
                                  <BookOpen className="h-3 w-3 shrink-0 text-brand-400" />
                                  <span className="truncate max-w-[110px] sm:max-w-[140px]">{src.document_name}</span>
                                  <span>p.{src.page_number}</span>
                                </button>
                              ))
                            ) : (
                              <span className="text-[10px] text-dark-500 inline-flex items-center space-x-1">
                                <Info className="h-3.5 w-3.5" />
                                <span>No local document cited.</span>
                              </span>
                            )}
                          </div>

                          {/* Quick buttons (Feedback & Copy) */}
                          <div className="flex items-center space-x-2 shrink-0 self-end sm:self-auto">
                            <button
                              onClick={() => copyToClipboard(msg.content, msg.id)}
                              className="p-1 hover:bg-dark-800 rounded text-dark-500 hover:text-dark-300 transition-colors"
                              title="Copy Answer"
                            >
                              {copiedId === msg.id ? <Check className="h-3.5 w-3.5 text-green-400" /> : <Copy className="h-3.5 w-3.5" />}
                            </button>
                            <button
                              onClick={() => handleFeedback(msg.id, 'liked')}
                              className={`p-1 rounded transition-colors ${msg.feedback === 'liked' ? 'text-green-400 bg-green-500/10' : 'text-dark-500 hover:text-green-400'}`}
                            >
                              <ThumbsUp className="h-3.5 w-3.5" />
                            </button>
                            <button
                              onClick={() => handleFeedback(msg.id, 'disliked')}
                              className={`p-1 rounded transition-colors ${msg.feedback === 'disliked' ? 'text-red-400 bg-red-500/10' : 'text-dark-500 hover:text-red-400'}`}
                            >
                              <ThumbsDown className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
              
              {/* Spinner for indexing / typing */}
              {loading && (
                <div className="flex justify-start">
                  <div className="glass border-dark-800 rounded-2xl rounded-tl-none p-3.5 sm:p-4 flex items-center space-x-2">
                    <div className="typing-dots flex space-x-1 text-brand-400">
                      <span>•</span>
                      <span>•</span>
                      <span>•</span>
                    </div>
                    <span className="text-xs text-dark-400 font-medium select-none">Gemini is searching docs...</span>
                  </div>
                </div>
              )}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input box */}
        <div className="p-3 sm:p-4 border-t border-dark-800 bg-dark-900/60 backdrop-blur-md shrink-0">
          <form 
            onSubmit={(e) => { e.preventDefault(); handleSendMessage(inputMessage); }}
            className="flex items-center space-x-2 sm:space-x-3 bg-dark-900 border border-dark-800 focus-within:border-brand-500/50 focus-within:ring-1 focus-within:ring-brand-500/50 rounded-2xl px-3 sm:px-4 py-1.5 sm:py-2"
          >
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask a question about your documents..."
              disabled={loading}
              className="w-full bg-transparent border-none py-1 focus:outline-none text-white placeholder-dark-500 text-xs sm:text-sm disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!inputMessage.trim() || loading}
              className="p-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white rounded-xl transition-all shadow-md shadow-brand-600/15 shrink-0"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      </section>

      {/* 3. Desktop Citation Details Drawer Sidebar */}
      {selectedCitation && (
        <aside className="hidden lg:flex w-80 border-l border-dark-800 flex-col justify-between bg-dark-900/50 shrink-0 z-10 min-h-0">
          <div className="p-4 border-b border-dark-800 flex items-center justify-between bg-dark-900/20">
            <span className="text-xs font-bold text-white tracking-wider uppercase">Source Citations</span>
            <button 
              onClick={() => setSelectedCitation(null)}
              className="p-1 hover:bg-dark-800 text-dark-500 hover:text-dark-200 rounded-lg transition-colors"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
            <div>
              <p className="text-[10px] font-semibold text-dark-500 uppercase tracking-wider">Document Name</p>
              <p className="text-sm font-bold text-brand-400 mt-1 truncate">{selectedCitation.document_name}</p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-[10px] font-semibold text-dark-500 uppercase tracking-wider">Page Number</p>
                <p className="text-sm font-bold text-white mt-1">Page {selectedCitation.page_number}</p>
              </div>
              <div>
                <p className="text-[10px] font-semibold text-dark-500 uppercase tracking-wider">Match Accuracy</p>
                <p className="text-sm font-bold text-emerald-400 mt-1">{(selectedCitation.similarity * 100).toFixed(1)}%</p>
              </div>
            </div>

            <div className="border-t border-dark-800 pt-4">
              <p className="text-[10px] font-semibold text-dark-500 uppercase tracking-wider mb-2">Retrieved Segment Chunk</p>
              <div className="bg-dark-900/60 border border-dark-800 rounded-xl p-3.5 text-xs text-dark-300 leading-relaxed font-mono overflow-y-auto max-h-[300px]">
                {selectedCitation.chunk}
              </div>
            </div>
          </div>
        </aside>
      )}

      {/* Mobile Citation Sheet Overlay (Bottom sheet modal on mobile screens) */}
      {selectedCitation && (
        <div className="lg:hidden fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-end justify-center p-0 sm:p-4">
          <div className="w-full max-w-lg bg-dark-900 border-t sm:border border-dark-800 rounded-t-2xl sm:rounded-2xl max-h-[85vh] flex flex-col overflow-hidden shadow-2xl">
            <div className="p-4 border-b border-dark-800 flex items-center justify-between bg-dark-950/60">
              <span className="text-xs font-bold text-white tracking-wider uppercase flex items-center space-x-2">
                <BookOpen className="h-4 w-4 text-brand-400" />
                <span>Source Citation Details</span>
              </span>
              <button 
                onClick={() => setSelectedCitation(null)}
                className="p-1 hover:bg-dark-800 text-dark-400 hover:text-white rounded-lg transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
              <div>
                <p className="text-[10px] font-semibold text-dark-500 uppercase tracking-wider">Document Name</p>
                <p className="text-sm font-bold text-brand-400 mt-1 truncate">{selectedCitation.document_name}</p>
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-dark-950/50 p-2.5 rounded-xl border border-dark-800">
                  <p className="text-[10px] font-semibold text-dark-500 uppercase tracking-wider">Page Number</p>
                  <p className="text-sm font-bold text-white mt-0.5">Page {selectedCitation.page_number}</p>
                </div>
                <div className="bg-dark-950/50 p-2.5 rounded-xl border border-dark-800">
                  <p className="text-[10px] font-semibold text-dark-500 uppercase tracking-wider">Match Accuracy</p>
                  <p className="text-sm font-bold text-emerald-400 mt-0.5">{(selectedCitation.similarity * 100).toFixed(1)}%</p>
                </div>
              </div>

              <div className="border-t border-dark-800 pt-3">
                <p className="text-[10px] font-semibold text-dark-500 uppercase tracking-wider mb-2">Retrieved Segment Chunk</p>
                <div className="bg-dark-950/80 border border-dark-800 rounded-xl p-3.5 text-xs text-dark-200 leading-relaxed font-mono overflow-y-auto max-h-[250px]">
                  {selectedCitation.chunk}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
export default Chat;
