import api from './api';
import type { Conversation, Message, ChatResponse, BaseResponse } from '../types';

export const chatService = {
  async listConversations(): Promise<Conversation[]> {
    const response = await api.get<Conversation[]>('/chat/conversations');
    return response.data;
  },

  async getHistory(conversationId: string): Promise<Message[]> {
    const response = await api.get<Message[]>(`/chat/history/${conversationId}`);
    return response.data;
  },

  async sendMessage(
    message: string,
    conversationId?: string,
    documentIds?: string[]
  ): Promise<ChatResponse> {
    const response = await api.post<ChatResponse>('/chat', {
      message,
      conversation_id: conversationId,
      document_ids: documentIds && documentIds.length > 0 ? documentIds : null,
    }, {
      timeout: 60000
    });
    return response.data;
  },

  async delete(conversationId: string): Promise<BaseResponse> {
    const response = await api.delete<BaseResponse>(`/chat/${conversationId}`);
    return response.data;
  },

  async rename(conversationId: string, title: string): Promise<BaseResponse & { title: string }> {
    const response = await api.put<BaseResponse & { title: string }>(`/chat/${conversationId}/rename`, {
      title,
    });
    return response.data;
  },

  async submitFeedback(messageId: string, feedback: 'liked' | 'disliked' | null): Promise<BaseResponse & { feedback: string }> {
    const response = await api.post<BaseResponse & { feedback: string }>('/chat/message/feedback', {
      message_id: messageId,
      feedback,
    });
    return response.data;
  },

  exportToMarkdown(title: string, messages: Message[]): void {
    let mdContent = `# Chat Session: ${title}\n\n`;
    
    messages.forEach((msg) => {
      const roleName = msg.role === 'user' ? 'User' : 'Assistant';
      const timeStr = new Date(msg.created_at).toLocaleString();
      
      mdContent += `### **${roleName}** _(${timeStr})_\n\n${msg.content}\n\n`;
      
      if (msg.sources && msg.sources.length > 0) {
        mdContent += `*Citations & Sources:*\n`;
        msg.sources.forEach((src) => {
          mdContent += `- **${src.document_name}** (Page ${src.page_number}) - Match: ${(src.similarity * 100).toFixed(1)}%\n`;
        });
        mdContent += `\n`;
      }
      
      mdContent += `---\n\n`;
    });

    const blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${title.toLowerCase().replace(/[^a-z0-9]+/g, '_')}_history.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
};
export default chatService;
