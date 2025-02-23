import {Button} from '@/components/ui/button';
import {Slider} from '@/components/ui/slider';
import {Volume2, VolumeX, Play, Pause} from 'lucide-react';
import {useState, useEffect, useRef} from 'react';
import {cn} from "@/lib/utils";

interface ImagePlayerProps {
  media: {
    images: {
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
    }[];
    audio?: {
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
    }[];
  };
  timestamp: string;
  description?: string;
}

const MAX_LENGTH = 75;

const ImagePlayer: React.FC<ImagePlayerProps> = ({ media, timestamp, description }) => {
  const { images, audio } = media;
  const [isExpanded, setIsExpanded] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
      audioRef.current.muted = isMuted;
    }
  }, [volume, isMuted]);

  const handlePlayPause = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleMuteToggle = () => {
    setIsMuted(!isMuted);
  };

  return (
    <div className="w-full space-y-2">
      <div className="bg-muted relative min-h-[200px] max-h-[calc(100vh-400px)] overflow-hidden rounded-lg">
        <img
          className="w-full h-full object-contain rounded-lg"
          src={images[0].url}
          alt="Image content"
        />
        <div className="absolute top-2 right-1 flex items-center gap-2 bg-black/60 backdrop-blur-sm p-2 rounded-lg">
          <Slider
            value={[volume]}
            onValueChange={(value) => setVolume(value[0])}
            min={0}
            max={1}
            step={0.1}
            className="w-20"
          />
          <Button
            variant="ghost"
            size="icon"
            onClick={handleMuteToggle}
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
            {isPlaying ? <Pause size={24} className="text-white" /> : <Play size={24} className="text-white" />}
          </Button>
        </div>
        {description && description.length > 0 ? (
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
        ) : null}
        <audio
          ref={audioRef}
          src={audio ? audio[0].url : ''}
          controls={false}
        />
      </div>
      <div className="flex w-full gap-1">
        <Button
          variant="ghost"
          className="flex-1 px-3 py-2 text-xs bg-muted-foreground/10 hover:bg-muted-foreground/20"
        >
          Regenerate
        </Button>
        <Button
          variant="ghost"
          className="flex-1 px-3 py-2 text-xs bg-muted-foreground/10 hover:bg-muted-foreground/20"
        >
          Generate Video
        </Button>
      </div>
      <div className="text-left text-xs opacity-70">
        {timestamp}
      </div>
    </div>
  );
};

export default ImagePlayer; 