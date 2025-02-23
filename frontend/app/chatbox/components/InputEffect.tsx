'use client';

import {zodResolver} from '@hookform/resolvers/zod';
import {ArrowUpIcon, Loader2Icon, StepForward} from 'lucide-react';
import {useState} from 'react';
import {useForm} from 'react-hook-form';
import {toast} from 'sonner';

import {Button} from '@/components/ui/button';
import {Textarea} from '@/components/ui/textarea';
import {Tooltip, TooltipContent, TooltipProvider, TooltipTrigger} from '@/components/ui/tooltip';
import {SoundEffectInput, soundEffectSchema} from '@/lib/schemas';

type ButtonConfig = {
  id: string;
  label: string;
  value: string;
};

type InputSoundEffectProps = {
  buttons?: ButtonConfig[];
};

export function InputSoundEffect({buttons = []}: InputSoundEffectProps) {
  const form = useForm<SoundEffectInput>({
    resolver: zodResolver(soundEffectSchema),
    defaultValues: {
      text: ''
    },
  });

  const [isGenerating, setIsGenerating] = useState(false);

  const generate = async (data: SoundEffectInput) => {
    try {
      setIsGenerating(true);
      console.log(data);
    } catch (err) {
      toast.error(`An unexpected error occurred: ${err}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleButtonClick = (button: ButtonConfig) => {
    console.log(`Button clicked: ${button.label}, Value: ${button.value}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const formData = form.getValues();
      if (formData.text.trim() && !isGenerating) {
        form.handleSubmit(generate)();
      }
    }
  };

  return (
    <div>
      <form onSubmit={form.handleSubmit(generate)}>
        <div className="relative rounded-[24px] border border-white/10 bg-[#2B2B2B]/70 p-2 backdrop-blur-xl">
          <div className="flex items-center justify-between w-full">
            <div className="flex gap-5 w-full justify-center">
              {buttons.map((button) => (
                <div key={button.id} className="flex flex-wrap gap-5">
                  <Button
                    size="icon"
                    variant="ghost"
                    className="flex h-9 w-9 min-w-[80px] items-center gap-1.5 rounded-md bg-white/10 p-0 hover:bg-white/20"
                    onClick={() => handleButtonClick(button)}
                  >
                    <StepForward className="h-[18px] w-[18px]"/>
                    <span className="mr-2">
                      {button.label}
                    </span>
                  </Button>
                </div>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-between flex-grow">

            <Textarea
              {...form.register('text', {
                onChange: (e) => {
                  e.target.style.height = 'auto';
                  e.target.style.height = `${e.target.scrollHeight}px`;
                },
              })}
              disabled={isGenerating}
              className="placeholder:text-token-text-secondary scrollbar-hide flex-grow rounded-md border-0 bg-transparent px-3 pb-4 pt-3 text-sm focus-visible:outline-none focus-visible:ring-0 disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="Describe your story..."
              rows={1}
              style={{
                overflowY: 'auto',
                overflowX: 'hidden',
                overflowWrap: 'break-word',
                resize: 'none',
                minHeight: '48px',
                scrollbarWidth: 'none',
                msOverflowStyle: 'none',
                scrollbarColor: 'transparent transparent',
              }}
              onKeyDown={handleKeyDown}
            />
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="icon"
                    disabled={!form.watch('text').trim() || isGenerating}
                    className="h-[36px] w-[36px] rounded-full bg-white p-1.5 text-zinc-900 hover:bg-white/80"
                    type="submit"
                  >
                    {isGenerating ? (
                      <Loader2Icon className="h-6 w-6 animate-spin"/>
                    ) : (
                      <ArrowUpIcon className="h-6 w-6"/>
                    )}
                    <span className="sr-only">Create sound effect</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Generate sound (Enter)</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>

      </form>
    </div>
  );
}
