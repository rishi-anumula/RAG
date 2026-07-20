export interface User {
  id: string;
  email: string;
}

export interface Session {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  expires_at?: number;
}

export interface AuthResponse {
  message?: string;
  user: User;
  session: Session | null;
}

export interface BaseResponse {
  message: string;
  status?: string;
}

export interface LoginCredentials {
  email: string;
  password?: string;
}

export type SignupCredentials = LoginCredentials;

export interface Document {
  id: string;
  user_id: string;
  name: string;
  size: number;
  status: 'uploaded' | 'processing' | 'processed' | 'failed';
  storage_path: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  document_name: string;
  page_number: number;
  chunk: string;
  similarity: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  user_id: string;
  role: 'user' | 'assistant';
  content: string;
  sources: Citation[];
  feedback: 'liked' | 'disliked' | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatResponse {
  conversation_id: string;
  message: Message;
  metrics: {
    retrieval_time_seconds: number;
    gemini_time_seconds: number;
  };
}

export interface DashboardMetrics {
  total_pdfs: number;
  total_conversations: number;
  storage_usage_bytes: number;
  recent_uploads: Document[];
  recent_chats: Conversation[];
}
