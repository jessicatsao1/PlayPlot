import React from 'react';
import { cn } from '@/lib/utils';

interface MessageProps {
  content: string;
  timestamp: string;
  isSender: boolean;
  metadata?: {
    word_count?: number;
    tone?: string;
    emotional_context?: string;
    setting_description?: string;
    options?: string[];
  };
}

export default function Message({ content, timestamp, isSender, metadata }: MessageProps) {
  return (
    <div className={cn("flex flex-col gap-2", isSender ? "items-end" : "items-start")}>
      <div
        className={cn(
          "rounded-lg p-4 shadow-sm",
          isSender
            ? "bg-primary text-primary-foreground"
            : "bg-muted"
        )}
      >
        <p className="text-base leading-relaxed whitespace-pre-wrap">{content}</p>
        
        {metadata && !isSender && (
          <div className="mt-2 pt-2 border-t border-primary/10 space-y-1">
            {metadata.tone && (
              <p className="text-xs opacity-70">
                Tone: <span className="font-medium">{metadata.tone}</span>
              </p>
            )}
            {metadata.emotional_context && (
              <p className="text-xs opacity-70">
                Context: <span className="font-medium">{metadata.emotional_context}</span>
              </p>
            )}
            {metadata.setting_description && (
              <p className="text-xs opacity-70">
                Setting: <span className="font-medium">{metadata.setting_description}</span>
              </p>
            )}
            {metadata.options && metadata.options.length > 0 && (
              <div className="mt-3 pt-2 border-t border-primary/10">
                <p className="text-xs font-medium mb-2">Available Options:</p>
                <div className="space-y-1">
                  {metadata.options.map((option, index) => (
                    <p key={index} className="text-xs opacity-90">
                      • {option}
                    </p>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        <div className="mt-2 flex items-center justify-between text-xs opacity-70">
          <span>{timestamp}</span>
          {metadata?.word_count && !isSender && (
            <span>{metadata.word_count} words</span>
          )}
        </div>
      </div>
    </div>
  );
}
