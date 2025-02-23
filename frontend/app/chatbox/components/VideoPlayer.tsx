import {Slider} from '@/components/ui/slider';
import {Button} from '@/components/ui/button';
import {Volume2, VolumeX, Pause, Play} from 'lucide-react';
import {cn} from '@/lib/utils';
import {useState, useRef, useEffect} from 'react';

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
  onUpdate: (newData: {
    media?: {
      video?: {
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
  }) => void;
}

const MAX_LENGTH = 75;

const VideoPlayer: React.FC<VideoPlayerProps> = ({ media, timestamp, description, onUpdate }) => {
  const { video } = media;
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [isPlaying, setIsPlaying] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);

  const handleVolumeChange = (value: number[]) => {
    const newVolume = value[0];
    setVolume(newVolume);
    if (videoRef.current) {
      videoRef.current.volume = newVolume;
    }
  };

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleRegenerate = async () => {
    try {
      const params = {};
      const response = await fetch('YOUR_API_ENDPOINT', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(params)
      });
      const data = await response.json();
      onUpdate(data);
    } catch (error) {
      console.error('Error calling API:', error);
    }
  };

  useEffect(() => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.play();
      } else {
        videoRef.current.pause();
      }
    }
  }, [isPlaying]);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  return (
    <div className="w-full space-y-2">
      <div className="bg-muted relative aspect-[9/16] overflow-hidden rounded-lg">
        <video
          ref={videoRef}
          className="absolute inset-0 w-full h-full object-cover rounded-lg"
          controls={false}
          src={video.url}
          muted={isMuted}
        />
        <div className="absolute top-2 right-1 flex items-center gap-2 bg-black/60 backdrop-blur-sm p-2 rounded-lg">
          <Slider
            value={[volume]}
            onValueChange={handleVolumeChange}
            min={0}
            max={1}
            step={0.1}
            className="w-20"
          />
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsMuted(!isMuted)}
            className="text-white/70 hover:text-white p-0"
          >
            {isMuted ? <VolumeX size={20}/> : <Volume2 size={20}/>}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={handlePlayPause}
            className="text-white/70 hover:text-white p-0"
          >
            {isPlaying ? <Pause size={24} className="text-white"/> : <Play size={24} className="text-white"/>}
          </Button>
        </div>
        {
          description && description.length > 0 ? (
            <div className={cn(
              "absolute bottom-0 left-0 right-0 bg-black/50 backdrop-blur-sm p-3 transition-all duration-300 rounded-lg",
              isExpanded ? "h-[50%]" : "h-[18%]"
            )}>
              <div className="h-full">
                <div className={cn(
                  "text-white h-[calc(100%-20px)] overflow-y-auto no-scrollbar"
                )}>
                  <p className={cn(
                    "text-xs text-white/70",
                    !isExpanded ? "line-clamp-3" : ""
                  )}>
                    {description}
                  </p>
                </div>
                {description.length >= MAX_LENGTH ? <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-xs text-white/50 hover:text-white/80 absolute bottom-3 left-3"
                >
                  {isExpanded ? 'Show less' : 'Show more'}
                </button> : null}
              </div>
            </div>
          ) : null
        }
      </div>
      <div className="flex w-full gap-1">
        <Button
          variant="ghost"
          className="flex-1 px-3 py-2 text-xs bg-muted-foreground/10 hover:bg-muted-foreground/20"
          onClick={handleRegenerate}
        >
          Regenerate
        </Button>
      </div>
      <div className="text-left text-xs opacity-70">
        {timestamp}
      </div>
    </div>
  );
};

export default VideoPlayer; 