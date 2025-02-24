'use client';

import {useState, useEffect, useRef} from 'react';
import {InputSoundEffect} from '@/app/chatbox/components/InputEffect';
import {ScrollArea} from '@/components/ui/scroll-area';
import {cn} from '@/lib/utils';
import Message from './components/Message';
import VideoPlayer from './components/VideoPlayer';
import ImagePlayer from './components/ImagePlayer';
import {sendMessage, type Message as APIMessage} from '@/app/actions/api';
import { Button } from '@/components/ui/button';
import { Progress } from "@/components/ui/progress";

interface ExtendedMetadata {
  word_count: number;
  tone: string;
  emotional_context: string;
  setting_description: string;
  options?: string[];
}

export default function Page() {
  const [messages, setMessages] = useState<APIMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentOptions, setCurrentOptions] = useState<string[]>([]);
  const [currentStep, setCurrentStep] = useState(1);
  const [showOptions, setShowOptions] = useState(false);
  const [storyText, setStoryText] = useState<string>('');
  const [progress, setProgress] = useState(0);
  const [loadingStage, setLoadingStage] = useState('');

  // Add a ref for scrolling
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Progress bar animation
  useEffect(() => {
    if (isLoading) {
      const stages = [
        'Analyzing your input...',
        'Generating story...',
        'Creating visuals...',
        'Preparing response...'
      ];
      let currentStage = 0;

      const progressTimer = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            return 90;
          }
          return prev + 2;
        });
      }, 200);

      const stageTimer = setInterval(() => {
        setLoadingStage(stages[currentStage]);
        currentStage = (currentStage + 1) % stages.length;
      }, 2000);

      return () => {
        clearInterval(progressTimer);
        clearInterval(stageTimer);
        setProgress(0);
        setLoadingStage('');
      };
    }
  }, [isLoading]);

  // Scroll to bottom when messages change
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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

  const handleSendMessage = async (content: string) => {
    try {
      setIsLoading(true);
      
      // Add user message to the chat
      const userMessage = {
        content,
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' }),
        isSender: true,
        type: 'message' as const
      };
      
      setMessages(prev => [...prev, userMessage]);

      // Send message to API
      const response = await sendMessage(userMessage);
      
      if (response.status === 'success' && response.messages) {
        // Process each message in the response
        const newMessages = response.messages.map(msg => {
          if (msg.type === 'message' && msg.metadata) {
            // Extract options and story text from message metadata
            const metadata = msg.metadata as ExtendedMetadata;
            if (metadata.options && metadata.options.length > 0) {
              setCurrentOptions(metadata.options);
              setCurrentStep(prev => Math.min(prev + 1, 3));
            }
            // Set story text only for non-user messages
            if (!msg.isSender) {
              setStoryText(msg.content);
            }
          }
          return msg;
        });

        setMessages(prev => [...prev, ...newMessages]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        content: 'Sorry, there was an error processing your message. Please try again.',
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' }),
        isSender: false,
        type: 'message' as const
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStepClick = (step: number) => {
    if (step === currentStep && currentOptions.length > 0) {
      const optionIndex = step - 1;
      if (currentOptions[optionIndex]) {
        handleOptionSelect(currentOptions[optionIndex]);
      }
    }
  };

  const handleOptionSelect = async (option: string) => {
    setShowOptions(false);
    await handleSendMessage(option);
  };

  return (
    <div className="fixed inset-0 flex flex-col ml-[300px]">
      <div className="absolute inset-0 bg-gradient-to-b from-background/90 to-background" />
      <div className="absolute inset-0 bg-grid-white/[0.02] bg-[size:50px_50px]" />
      
      {/* Game Title */}
      <div className="relative z-10 py-6 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b">
        <div className="max-w-[1000px] mx-auto px-6">
          <div className="text-center space-y-2">
            <h1 className="text-6xl font-bold tracking-tight">
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-violet-500 via-primary to-indigo-500 animate-gradient">
                PlayPlot
              </span>
            </h1>
            <p className="text-lg font-medium bg-clip-text text-transparent bg-gradient-to-r from-muted-foreground/80 to-muted-foreground">
              Interactive Entertainment Next Gen
            </p>
          </div>
        </div>
      </div>

      {/* Add animation keyframes at the top of your CSS */}
      <style jsx>{`
        @keyframes gradient {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        .animate-gradient {
          background-size: 200% auto;
          animation: gradient 8s linear infinite;
        }
      `}</style>

      {/* Main Content Area - Fixed Height */}
      <div className="relative flex-1 overflow-hidden">
        {/* Messages Area with ScrollArea */}
        <ScrollArea className="h-[calc(100vh-200px)] w-full">
          <div className="max-w-[1000px] mx-auto px-6 py-4">
            <div className="space-y-6">
              {messages.map((msg, index) => (
                <div key={index} className={cn(
                  "max-w-[85%] transition-all duration-200",
                  msg.isSender ? "ml-auto" : "mr-auto"
                )}>
                  {msg.type === 'message' && msg.isSender ? (
                    <Message
                      content={msg.content}
                      timestamp={msg.timestamp}
                      isSender={msg.isSender}
                      metadata={msg.metadata as ExtendedMetadata}
                    />
                  ) : msg.type === 'message' && !msg.isSender ? null : (
                    <div className="rounded-lg overflow-hidden shadow-lg">
                      {msg.type === 'video' ? (
                        <VideoPlayer
                          media={msg.media}
                          timestamp={msg.timestamp}
                          description={msg.text}
                          onUpdate={(newData) => handleMessageUpdate(index, newData)}
                        />
                      ) : msg.type === 'media' && (
                        <ImagePlayer
                          media={msg.media}
                          timestamp={msg.timestamp}
                          storyText={storyText}
                          onUpdate={(newData) => handleMessageUpdate(index, newData)}
                        />
                      )}
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>
        </ScrollArea>
      </div>

      {/* Fixed Bottom Input Area */}
      <div className="relative z-20 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-t">
        <div className="max-w-[1000px] mx-auto p-6">
          {/* Processing Indicator */}
          {isLoading && (
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <div className="space-y-1">
                  <span className="text-sm font-medium text-primary">Processing your request...</span>
                  <p className="text-xs text-primary/80">{loadingStage}</p>
                </div>
                <span className="text-sm font-medium text-primary">{progress}%</span>
              </div>
              <Progress value={progress} className="h-2" />
            </div>
          )}

          {/* Options Buttons */}
          <div className="flex flex-wrap justify-center gap-4 mb-4">
            {currentOptions.map((option, index) => (
              <Button
                key={index}
                variant="outline"
                onClick={() => handleOptionSelect(option)}
                disabled={isLoading}
                className="flex-1 min-w-[250px] max-w-[350px] h-[80px] text-sm text-left p-4 whitespace-normal hover:bg-primary hover:text-primary-foreground transition-colors"
              >
                {option}
              </Button>
            ))}
          </div>

          {/* Input Field */}
          <InputSoundEffect 
            onSend={handleSendMessage}
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  );
}
