'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Play, Pause, Volume2, VolumeX, AlertCircle } from 'lucide-react';
import { cn } from "@/lib/utils";

export interface AudioPlayerProps {
  src: string;
  duration: number;
  timestamp: string;
  className?: string;
  onError?: (error: string) => void;
}

export function AudioPlayer({ src, duration, timestamp, className, onError }: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  useEffect(() => {
    // Reset state when src changes
    setIsPlaying(false);
    setCurrentTime(0);
    setError(null);
    setIsLoading(true);
  }, [src]);

  const handlePlayPause = () => {
    if (!audioRef.current || error) return;
    
    try {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play().catch((err) => {
          const errorMessage = 'Failed to play audio: ' + (err.message || 'Unknown error');
          console.error(errorMessage, err);
          setError(errorMessage);
          onError?.(errorMessage);
        });
      }
      setIsPlaying(!isPlaying);
    } catch (err) {
      const errorMessage = 'Error handling play/pause: ' + (err instanceof Error ? err.message : 'Unknown error');
      console.error(errorMessage);
      setError(errorMessage);
      onError?.(errorMessage);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleSeek = (value: number[]) => {
    if (audioRef.current && !error) {
      audioRef.current.currentTime = value[0];
      setCurrentTime(value[0]);
    }
  };

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const handleAudioError = (e: React.SyntheticEvent<HTMLAudioElement, Event>) => {
    const audioElement = e.currentTarget;
    let errorMessage = 'Failed to load audio';
    
    if (audioElement.error) {
      switch (audioElement.error.code) {
        case MediaError.MEDIA_ERR_ABORTED:
          errorMessage = 'Audio playback was aborted';
          break;
        case MediaError.MEDIA_ERR_NETWORK:
          errorMessage = 'Network error while loading audio';
          break;
        case MediaError.MEDIA_ERR_DECODE:
          errorMessage = 'Audio decoding failed';
          break;
        case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
          errorMessage = 'Audio format not supported';
          break;
        default:
          errorMessage = `Audio error: ${audioElement.error.message}`;
      }
    }
    
    console.error(errorMessage);
    setError(errorMessage);
    onError?.(errorMessage);
    setIsLoading(false);
  };

  return (
    <div className={cn(
      "flex items-center space-x-2 p-2 rounded-lg bg-muted",
      error && "opacity-70",
      className
    )}>
      <Button
        variant="ghost"
        size="icon"
        onClick={handlePlayPause}
        disabled={isLoading || !!error}
        className="text-foreground/70 hover:text-foreground"
      >
        {isPlaying ? <Pause size={20} /> : <Play size={20} />}
      </Button>
      
      <div className="flex-1 space-y-1">
        <Slider
          value={[currentTime]}
          max={duration}
          step={0.1}
          onValueChange={handleSeek}
          disabled={isLoading || !!error}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-foreground/70">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <Slider
          value={[volume]}
          max={1}
          step={0.1}
          onValueChange={(value) => setVolume(value[0])}
          disabled={isLoading || !!error}
          className="w-20"
        />
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setIsMuted(!isMuted)}
          disabled={isLoading || !!error}
          className="text-foreground/70 hover:text-foreground"
        >
          {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
        </Button>
      </div>

      {error && (
        <div className="flex items-center text-destructive">
          <AlertCircle size={16} className="mr-1" />
          <span className="text-xs">{error}</span>
        </div>
      )}

      <audio
        ref={audioRef}
        src={src}
        onTimeUpdate={handleTimeUpdate}
        onEnded={() => setIsPlaying(false)}
        onLoadStart={() => setIsLoading(true)}
        onLoadedData={() => setIsLoading(false)}
        onError={handleAudioError}
      />

      <span className="text-xs text-foreground/70">{timestamp}</span>
    </div>
  );
}
