import type { Message } from '../components/chat/ChatInterface';
import type { ChatResponse } from '../types';

interface SessionContext {
  messages: Message[];
  keyContext: {
    locations: string[];
    timeRanges: string[];
    dataTypes: string[];
    recentQueries: string[];
  };
  summary: string;
}

interface APIContext {
  recent_exchanges: Array<{
    user_query: string;
    ai_response_summary: string;
    timestamp: string;
  }>;
  key_context: {
    locations: string[];
    time_ranges: string[];
    data_types: string[];
    recent_focus: string[];
  };
  conversation_summary: string;
}

export class SessionContextManager {
  private readonly STORAGE_KEY = 'floatchat_session_context';

  constructor() {
    this.initializeSession();
  }

  private initializeSession(): void {
    if (!this.getStoredContext()) {
      this.saveContext({
        messages: [],
        keyContext: {
          locations: [],
          timeRanges: [],
          dataTypes: [],
          recentQueries: []
        },
        summary: ''
      });
    }
  }

  private getStoredContext(): SessionContext | null {
    try {
      const stored = sessionStorage.getItem(this.STORAGE_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch (error) {
      console.warn('Failed to parse session context:', error);
      return null;
    }
  }

  private saveContext(context: SessionContext): void {
    try {
      // Convert dates to strings before serialization
      const serializedContext = {
        ...context,
        messages: context.messages.map(msg => ({
          ...msg,
          timestamp: typeof msg.timestamp === 'string' ? msg.timestamp : msg.timestamp.toISOString()
        }))
      };
      sessionStorage.setItem(this.STORAGE_KEY, JSON.stringify(serializedContext));
    } catch (error) {
      console.warn('Failed to save session context:', error);
    }
  }

  addMessage(message: Message): void {
    const context = this.getStoredContext() || {
      messages: [],
      keyContext: { locations: [], timeRanges: [], dataTypes: [], recentQueries: [] },
      summary: ''
    };

    // Add new message
    context.messages.push(message);

    // Keep only last 10 messages (5 exchanges)
    if (context.messages.length > 10) {
      context.messages = context.messages.slice(-10);
    }

    // Extract key context from user messages
    if (message.isUser) {
      this.extractKeyContext(message.content, context.keyContext);
    }

    // Update summary
    context.summary = this.generateSummary(context.messages);

    this.saveContext(context);
  }

  private extractKeyContext(userMessage: string, keyContext: SessionContext['keyContext']): void {
    const message = userMessage.toLowerCase();

    // Extract locations with better patterns and context inference
    const locationPatterns = [
      /mumbai/gi,
      /bombay/gi,
      /indian\s+coast/gi,
      /arabian\s+sea/gi,
      /bay\s+of\s+bengal/gi,
      /indian\s+ocean/gi,
      /pacific/gi,
      /atlantic/gi,
      /mediterranean/gi,
      /near\s+(\w+)/gi,
      /(\w+)\s+sea/gi,
      /(\w+)\s+ocean/gi,
      /(\w+)\s+coast/gi
    ];

    locationPatterns.forEach(pattern => {
      const matches = message.match(pattern);
      if (matches) {
        matches.forEach(match => {
          const location = match.trim();
          if (!keyContext.locations.includes(location)) {
            keyContext.locations.push(location);
          }
        });
      }
    });

    // Infer context from relative references like "what about below 1000m"
    if (message.includes('below') || message.includes('above') || message.includes('deeper') || 
        message.includes('shallower') || message.includes('there') || message.includes('that area')) {
      // Preserve recent location context more aggressively
      const recentLocation = keyContext.locations[keyContext.locations.length - 1];
      if (recentLocation && !keyContext.locations.slice(-3).includes(recentLocation)) {
        keyContext.locations.push(recentLocation);
      }
    }

    // Extract time ranges
    const timePatterns = [
      /\b20\d{2}\b/g, // Years like 2024
      /recent/gi,
      /latest/gi,
      /last\s+\w+/gi,
      /past\s+\w+/gi,
      /current/gi,
      /(january|february|march|april|may|june|july|august|september|october|november|december)/gi
    ];

    timePatterns.forEach(pattern => {
      const matches = message.match(pattern);
      if (matches) {
        matches.forEach(match => {
          const timeRange = match.trim();
          if (!keyContext.timeRanges.includes(timeRange)) {
            keyContext.timeRanges.push(timeRange);
          }
        });
      }
    });

    // Extract data types and depth context
    const dataTypePatterns = [
      /temperature/gi,
      /salinity/gi,
      /pressure/gi,
      /depth/gi,
      /profile/gi,
      /measurement/gi,
      /argo/gi,
      /float/gi,
      /data/gi,
      /below.*\d+m/gi,
      /above.*\d+m/gi,
      /\d+m.*deep/gi,
      /surface/gi,
      /deep.*water/gi
    ];

    dataTypePatterns.forEach(pattern => {
      const matches = message.match(pattern);
      if (matches) {
        matches.forEach(match => {
          const dataType = match.toLowerCase().trim();
          if (!keyContext.dataTypes.includes(dataType)) {
            keyContext.dataTypes.push(dataType);
          }
        });
      }
    });

    // Extract specific depth references for better context continuity
    const depthMatches = message.match(/(?:below|above|at|around)\s*(\d+)\s*m/gi);
    if (depthMatches) {
      depthMatches.forEach(match => {
        if (!keyContext.dataTypes.includes(match)) {
          keyContext.dataTypes.push(match);
        }
      });
    }

    // Keep only recent items (max 10 each)
    keyContext.locations = keyContext.locations.slice(-10);
    keyContext.timeRanges = keyContext.timeRanges.slice(-10);
    keyContext.dataTypes = keyContext.dataTypes.slice(-10);

    // Store recent queries
    keyContext.recentQueries.push(userMessage.slice(0, 100)); // Truncate long queries
    keyContext.recentQueries = keyContext.recentQueries.slice(-5); // Keep last 5
  }

  private generateSummary(messages: Message[]): string {
    if (messages.length === 0) return '';

    // Get last few exchanges
    const recentMessages = messages.slice(-6); // Last 3 exchanges (user + AI)
    
    const summaryParts: string[] = [];
    
    for (let i = 0; i < recentMessages.length; i += 2) {
      const userMsg = recentMessages[i];
      const aiMsg = recentMessages[i + 1];
      
      if (userMsg && aiMsg && userMsg.isUser && !aiMsg.isUser) {
        const userQuery = userMsg.content.slice(0, 50) + (userMsg.content.length > 50 ? '...' : '');
        const aiSummary = this.summarizeAIResponse(aiMsg.content, aiMsg.chatResponse);
        summaryParts.push(`Q: ${userQuery} -> A: ${aiSummary}`);
      }
    }

    return summaryParts.join(' | ');
  }

  private summarizeAIResponse(response: string, chatResponse?: ChatResponse): string {
    // Use API-generated summary if available
    if (chatResponse?.response_summary) {
      return chatResponse.response_summary;
    }
    
    // Fallback to client-side summary generation
    const cleanResponse = response.replace(/<[^>]*>/g, ''); // Remove HTML tags
    
    // Look for key phrases that indicate what was found/discussed
    const keyPhrases: string[] = [];
    
    if (cleanResponse.match(/found|data|measurements?|records?/i)) {
      keyPhrases.push('data found');
    }
    if (cleanResponse.match(/temperature/i)) {
      keyPhrases.push('temperature');
    }
    if (cleanResponse.match(/salinity/i)) {
      keyPhrases.push('salinity');
    }
    if (cleanResponse.match(/location|latitude|longitude|coast|sea|ocean/i)) {
      keyPhrases.push('location data');
    }
    if (cleanResponse.match(/\d+.*floats?/i)) {
      keyPhrases.push('float data');
    }

    const summary = keyPhrases.length > 0 
      ? keyPhrases.join(', ')
      : cleanResponse.slice(0, 40) + '...';

    return summary;
  }

  getMessages(): Message[] {
    const context = this.getStoredContext();
    if (!context?.messages) return [];
    
    // Convert string timestamps back to Date objects
    return context.messages.map(msg => ({
      ...msg,
      timestamp: typeof msg.timestamp === 'string' ? new Date(msg.timestamp) : msg.timestamp
    }));
  }

  getContextForAPI(): APIContext {
    const context = this.getStoredContext();
    if (!context) {
      return {
        recent_exchanges: [],
        key_context: {
          locations: [],
          time_ranges: [],
          data_types: [],
          recent_focus: []
        },
        conversation_summary: ''
      };
    }

    // Build recent exchanges for API
    const recentExchanges: APIContext['recent_exchanges'] = [];
    const messages = context.messages.slice(-10); // Last 5 exchanges
    
    for (let i = 0; i < messages.length; i += 2) {
      const userMsg = messages[i];
      const aiMsg = messages[i + 1];
      
      if (userMsg && aiMsg && userMsg.isUser && !aiMsg.isUser) {
        const timestamp = typeof userMsg.timestamp === 'string' ? userMsg.timestamp : userMsg.timestamp.toISOString();
        recentExchanges.push({
          user_query: userMsg.content,
          ai_response_summary: this.summarizeAIResponse(aiMsg.content, aiMsg.chatResponse),
          timestamp: timestamp
        });
      }
    }

    return {
      recent_exchanges: recentExchanges,
      key_context: {
        locations: context.keyContext.locations,
        time_ranges: context.keyContext.timeRanges,
        data_types: context.keyContext.dataTypes,
        recent_focus: context.keyContext.recentQueries.slice(-3) // Last 3 query focuses
      },
      conversation_summary: context.summary
    };
  }

  clearSession(): void {
    sessionStorage.removeItem(this.STORAGE_KEY);
    this.initializeSession();
  }

  getSessionStats(): { messageCount: number; contextItems: number } {
    const context = this.getStoredContext();
    if (!context) return { messageCount: 0, contextItems: 0 };

    const contextItems = context.keyContext.locations.length + 
                        context.keyContext.timeRanges.length + 
                        context.keyContext.dataTypes.length;

    return {
      messageCount: context.messages.length,
      contextItems
    };
  }
}