import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ChatMessage {
  content: string;
  timestamp: string;
  isSender: boolean;
  type: 'message';
  storyId?: string;
  sceneNumber?: number;
  text?: string;
  metadata?: {
    word_count: number;
    tone: string;
    emotional_context: string;
    setting_description: string;
  };
}

export interface MediaMessage {
  status: string;
  story_id: string;
  scene_id: string;
  isSender: boolean;
  timestamp: string;
  type: 'media';
  media: {
    images?: Array<{
      url: string;
      thumbnail_url: string;
      prompt_used: string;
      style: string;
      metadata: {
        width: number;
        height: number;
        model: string;
        seed: number;
      };
    }>;
    audio?: Array<{
      url: string;
      duration: number;
      speaker: {
        character_id: string;
        voice_id: string;
        emotion: string;
      };
      metadata: {
        format: string;
        sample_rate: number;
      };
    }>;
  };
}

export interface VideoMessage {
  status: string;
  story_id: string;
  scene_id: string;
  isSender: boolean;
  timestamp: string;
  type: 'video';
  text: string;
  media: {
    video: {
      url: string;
      thumbnail_url: string;
      duration: number;
      metadata: {
        resolution: string;
        fps: number;
        format: string;
      };
    };
  };
}

export type Message = ChatMessage | MediaMessage | VideoMessage;

export interface ChatResponse {
  status: string;
  messages: Message[];
}

export const sendMessage = async (message: ChatMessage): Promise<ChatResponse> => {
  try {
    const response = await axios.post<ChatResponse>(`${API_BASE_URL}/api/chat`, message);
    return response.data;
  } catch (error) {
    console.error('Error sending message:', error);
    throw error;
  }
}; 