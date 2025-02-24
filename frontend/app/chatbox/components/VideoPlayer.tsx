import React from 'react';

interface VideoPlayerProps {
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
  timestamp: string;
  description?: string;
  onUpdate?: (newData: any) => void;
}

export default function VideoPlayer({ media, timestamp, description }: VideoPlayerProps) {
  return (
    <div className="space-y-2">
      <div className="relative aspect-video overflow-hidden rounded-lg">
        <video
          src={media.video.url}
          poster={media.video.thumbnail_url}
          controls
          className="w-full h-full object-cover"
        />
      </div>
      {description && (
        <p className="text-sm text-gray-500">{description}</p>
      )}
      <div className="text-xs text-gray-400">
        {timestamp}
      </div>
    </div>
  );
} 