'use client';

import {useState, useEffect} from 'react';

import {InputSoundEffect} from '@/app/chatbox/components/InputEffect';
import {ScrollArea} from '@/components/ui/scroll-area';
import {cn} from '@/lib/utils';
import Message from './components/Message';
import VideoPlayer from './components/VideoPlayer';
import ImagePlayer from './components/ImagePlayer';

export default function Page() {
  const [firstIn, setFirstIn] = useState(true);

  const [messages, setMessages] = useState([
    {
      content: '這是一個故事消息！',
      timestamp: '02:33',
      isSender: true,
      type: 'message'
    },
    {
      content: '這是一個故事消息！',
      timestamp: '02:33',
      isSender: false,
      type: 'message',
      storyId: 'story_1',
      sceneNumber: 1,
      text: '這是故事的內容。',
      metadata: {word_count: 10, tone: 'neutral', emotional_context: 'calm', setting_description: '一個寧靜的公園'},
    },
    {
      status: 'success',
      story_id: 'story_1',
      scene_id: 'scene_1',
      isSender: false,
      timestamp: '02:33',
      type: 'media',
      media: {
        images: [{
          url: '/resource/sample-img.png',
          thumbnail_url: '/resource/story-image-thumbnail.png',
          prompt_used: '故事場景',
          style: '插畫',
          metadata: {width: 800, height: 600, model: 'model_v1', seed: 12345}
        }],
        audio: [{
          url: '/resource/audioplayback.m4a',
          duration: 120,
          speaker: {character_id: 'char_1', voice_id: 'voice_1', emotion: 'happy'},
          metadata: {format: 'mp3', sample_rate: 44100}
        }],
      },
    },
    {
      status: 'success',
      story_id: 'story_1',
      scene_id: 'scene_1',
      isSender: false,
      timestamp: '02:33',
      type: 'video',
      text: '這是故事的內容。',
      media: {
        video: {
          url: '/resource/videoplayback.mp4',
          thumbnail_url: '/resource/story-video-thumbnail.png',
          duration: 180,
          metadata: {resolution: '1080p', fps: 30, format: 'mp4'}
        }
      },
    },
  ]);

  const [buttonConfigs, setButtonConfigs] = useState([
    {id: '1', label: 'Step 1', value: 'Step 1'},
    {id: '2', label: 'Step 2', value: 'Step 2'},
    {id: '3', label: 'Step 3', value: 'Step 3'},
  ]);

  // 添加更新消息的方法
  const handleMessageUpdate = (index: number, newData: any) => {
    setMessages(prevMessages => {
      const updatedMessages = [...prevMessages];
      updatedMessages[index] = {
        ...updatedMessages[index],
        ...newData
      };
      return updatedMessages;
    });
  };

  return (
    <div>
      {firstIn ? (
        <div className="container mx-auto">
          <div className="bg-card flex flex-col rounded-lg p-6 h-[calc(100vh-320px)]">
            <div className="flex flex-1 flex-col justify-center  overflow-y-auto">
              <div className="space-y-4 h-full">
                <ScrollArea className="h-full w-full rounded-md border p-4 ">
                  <div className="space-y-4">
                    {messages.map((msg, index) => (
                      <div key={index} className="space-y-2">
                        {msg.type === 'message' ? (
                          <Message
                            content={msg.content || ''}
                            timestamp={msg.timestamp || ''}
                            isSender={msg.isSender}
                          />
                        ) : (
                          <div className="flex justify-start">
                            <div className="w-[45%] rounded-lg p-2">
                              {msg.type === 'video' ? (
                                <VideoPlayer
                                  media={msg.media as {
                                    video: {
                                      url: string;
                                      thumbnail_url: string;
                                      duration: number;
                                      metadata: { resolution: string; fps: number; format: string; };
                                    };
                                  }}
                                  timestamp={msg.timestamp}
                                  description={msg.text || ''}
                                  onUpdate={(newData) => handleMessageUpdate(index, newData)}
                                />
                              ) : (
                                <ImagePlayer
                                  media={msg.media as {
                                    images: {
                                      url: string;
                                      thumbnail_url: string;
                                      prompt_used: string;
                                      style: string;
                                      metadata: { width: number; height: number; model: string; seed: number; };
                                    }[];
                                    audio?: {
                                      url: string;
                                      duration: number;
                                      speaker: { character_id: string; voice_id: string; emotion: string; };
                                      metadata: { format: string; sample_rate: number; };
                                    }[];
                                  }}
                                  timestamp={msg.timestamp}
                                  description={msg.text || ''}
                                  onUpdate={(newData) => handleMessageUpdate(index, newData)}
                                />
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            </div>
          </div>
        </div>
      ) : null}
      <div
        className={cn(
          "absolute bottom-0 left-0 right-0 p-4",
          !firstIn && "h-[calc(100%-200px)]"
        )}
      >
        <div className="mx-auto max-w-4xl h-full flex flex-col justify-center">
          <InputSoundEffect buttons={buttonConfigs}/>
        </div>
      </div>
    </div>
  );
}
