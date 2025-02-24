import React from 'react';
import { AudioPlayer } from '@/components/audio-player';
import { Button } from '@/components/ui/button';
import { cn } from "@/lib/utils";
import { useState, useEffect } from 'react';

interface ImagePlayerProps {
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
  timestamp: string;
  description?: string;
  onUpdate?: (newData: any) => void;
  storyText?: string;
}

const ImagePlayer: React.FC<ImagePlayerProps> = ({ media, timestamp, description, onUpdate, storyText }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [audioErrors, setAudioErrors] = useState<{[key: string]: string}>({});

  // Function to format audio URL
  const formatAudioUrl = (url: string) => {
    // If URL is already absolute, return as is
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }
    
    // If URL is a relative path, prepend the API base URL
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    // Remove leading slash if present to avoid double slashes
    const cleanUrl = url.startsWith('/') ? url.slice(1) : url;
    
    // Handle different URL patterns
    if (cleanUrl.startsWith('audio/')) {
      // Direct audio endpoint
      return `${baseUrl}/${cleanUrl}`;
    } else if (cleanUrl.startsWith('output/')) {
      // Static file from output directory
      return `${baseUrl}/${cleanUrl}`;
    } else if (cleanUrl.startsWith('static/')) {
      // Static file from static directory
      return `${baseUrl}/${cleanUrl}`;
    } else {
      // Default to audio endpoint
      return `${baseUrl}/audio/${cleanUrl}`;
    }
  };

  // Debug function to check audio URL
  const debugAudioUrl = async (url: string) => {
    try {
      const formattedUrl = formatAudioUrl(url);
      console.log('Attempting to load audio from:', formattedUrl);
      
      // Try to fetch the headers to check content type
      const response = await fetch(formattedUrl, { method: 'HEAD' });
      const contentType = response.headers.get('content-type');
      console.log('Audio content type:', contentType);
      
      return formattedUrl;
    } catch (error) {
      console.error('Error checking audio URL:', error);
      return url;
    }
  };

  const handleAudioError = (index: number, error: string) => {
    const audioUrl = media.audio?.[index]?.url;
    console.log('Audio error for file:', audioUrl);
    console.log('Formatted URL:', formatAudioUrl(audioUrl || ''));
    console.log('Audio metadata:', media.audio?.[index]?.metadata);
    
    setAudioErrors(prev => ({
      ...prev,
      [index]: error
    }));
  };

  const handleRegenerate = async () => {
    if (!onUpdate) return;
    setIsLoading(true);
    setAudioErrors({});
    
    try {
      const response = await fetch('/api/regenerate-scene', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ timestamp })
      });
      const data = await response.json();
      onUpdate(data);
    } catch (error) {
      console.error('Error regenerating scene:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateVideo = async () => {
    if (!onUpdate) return;
    setIsLoading(true);
    
    try {
      const response = await fetch('/api/generate-video', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ timestamp })
      });
      const data = await response.json();
      onUpdate(data);
    } catch (error) {
      console.error('Error generating video:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Image display */}
      <div className="relative rounded-lg overflow-hidden bg-black/5">
        <div className="aspect-[16/9] max-h-[500px] relative">
          <img
            src={media.images?.[0]?.url || '/placeholder.png'}
            alt="Generated scene"
            className="absolute inset-0 w-full h-full object-contain"
          />
          <div className="absolute bottom-2 right-2 text-xs text-white bg-black/50 px-2 py-1 rounded">
            {timestamp}
          </div>
        </div>
      </div>
      
      {/* Story text and audio display */}
      {(storyText || (media.audio && media.audio.length > 0)) && (
        <div className="bg-card/50 backdrop-blur-sm p-6 rounded-lg space-y-4">
          {/* Story Text */}
          {storyText && (
            <p className="text-lg leading-relaxed whitespace-pre-wrap text-foreground/90 max-w-[900px] mx-auto">
              {storyText}
            </p>
          )}
          
          {/* Audio Players */}
          {media.audio && media.audio.length > 0 && (
            <div className="space-y-4 max-w-[900px] mx-auto">
              {media.audio.map((audio, index) => (
                <div key={index} className="bg-muted/50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-medium text-foreground/70">
                      {audio.speaker.emotion} • {audio.duration.toFixed(1)}s
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Format: {audio.metadata.format} • {audio.metadata.sample_rate}Hz
                    </span>
                  </div>
                  {audioErrors[index] ? (
                    <div className="text-sm text-destructive p-2 rounded bg-destructive/10">
                      Error: {audioErrors[index]}
                      <div className="text-xs mt-1 text-muted-foreground">
                        URL: {formatAudioUrl(audio.url)}
                      </div>
                    </div>
                  ) : (
                    <AudioPlayer
                      src={formatAudioUrl(audio.url)}
                      duration={audio.duration}
                      timestamp={timestamp}
                      className="w-full"
                      onError={(error) => handleAudioError(index, error)}
                    />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex w-full gap-2 max-w-[900px] mx-auto">
        <Button
          variant="ghost"
          className={cn(
            "flex-1 px-3 py-2 text-sm bg-muted-foreground/10 hover:bg-muted-foreground/20",
            isLoading && "opacity-50 cursor-not-allowed"
          )}
          onClick={handleRegenerate}
          disabled={isLoading}
        >
          {isLoading ? "Regenerating..." : "Regenerate Scene"}
        </Button>
        <Button
          variant="ghost"
          className={cn(
            "flex-1 px-3 py-2 text-sm bg-muted-foreground/10 hover:bg-muted-foreground/20",
            isLoading && "opacity-50 cursor-not-allowed"
          )}
          onClick={handleGenerateVideo}
          disabled={isLoading}
        >
          {isLoading ? "Generating..." : "Generate Video"}
        </Button>
      </div>
    </div>
  );
};

export default ImagePlayer; 