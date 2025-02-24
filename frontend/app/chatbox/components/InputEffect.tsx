'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Loader2, Send } from 'lucide-react';
import { cn } from '@/lib/utils';

interface InputSoundEffectProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
}

export function InputSoundEffect({ onSend, isLoading }: InputSoundEffectProps) {
  const [message, setMessage] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Focus input on mount
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSend(message.trim());
      setMessage('');
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="relative w-full"
    >
      <div className="relative">
        <Input
          ref={inputRef}
          type="text"
          placeholder={isLoading ? "Processing..." : "Type your message..."}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          disabled={isLoading}
          className={cn(
            "w-full pr-12 py-6 text-base rounded-xl",
            "bg-background/50 backdrop-blur border-2",
            "focus:ring-2 focus:ring-primary/50 focus:border-primary",
            "transition-all duration-200",
            "placeholder:text-muted-foreground/70",
            isLoading && "opacity-50"
          )}
        />
        <Button
          type="submit"
          size="icon"
          disabled={!message.trim() || isLoading}
          className={cn(
            "absolute right-2 top-1/2 -translate-y-1/2",
            "w-10 h-10 rounded-xl",
            "bg-primary hover:bg-primary/90",
            "text-primary-foreground",
            "transition-all duration-200",
            "disabled:opacity-50"
          )}
        >
          {isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Send className="h-5 w-5" />
          )}
        </Button>
      </div>
    </form>
  );
}
