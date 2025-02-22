'use client';

import {useState, useEffect} from 'react';

import {InputSoundEffect} from '@/components/input-sound-effect';
import {ScrollArea} from '@/components/ui/scroll-area';
import {cn} from '@/lib/utils';

export default function Page() {
  const [firstIn, setFirstIn] = useState(true);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(1);

  useEffect(() => {
    const videoElement = document.querySelector('video');
    if (videoElement) {
      videoElement.volume = volume;
    }
  }, [volume]);

  return (
    <div>
      {firstIn ? (
        <div className="container mx-auto">
          <div className="bg-card flex flex-col rounded-lg p-6 h-[calc(100vh-320px)]">
            <div className="flex flex-1 flex-col justify-center">
              <div className="space-y-4 h-full">
                <ScrollArea className="h-full w-full rounded-md border p-4">
                  <div className="space-y-4">
                    {/* 發送者的消息 */}
                    <div className="flex justify-end">
                      <div className="max-w-[70%] rounded-lg bg-primary px-4 py-2 text-primary-foreground">
                        <p>嗨！這是一條測試消息</p>
                        <div className="mt-1 text-right text-xs opacity-70">
                          02:30
                        </div>
                      </div>
                    </div>

                    {/* 接收者的消息 */}
                    <div className="flex justify-start">
                      <div className="max-w-[70%] rounded-lg bg-muted px-4 py-2">
                        <p>你好！這是回覆消息！你好！這是回覆消息！你好！這是回覆消息！你好！這是回覆消息！</p>
                        <div className="mt-1 text-left text-xs opacity-70">
                          02:31
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex justify-start">
                        <div className="w-[45%] rounded-lg bg-muted p-2">
                          <div className="relative aspect-[9/16] overflow-hidden rounded-lg">
                            <video
                              className="absolute inset-0 w-full h-full object-cover"
                              controls={false}
                              src="/sample-video.mp4"
                              muted={isMuted}
                            />
                            <div
                              className="absolute top-2 right-1 flex items-center gap-2 bg-black/60 backdrop-blur-sm p-2 rounded-lg">
                              <input
                                type="range"
                                min="0"
                                max="1"
                                step="0.1"
                                value={volume}
                                onChange={(e) => setVolume(Number(e.target.value))}
                                className="w-20 h-1 bg-white rounded-md appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white"
                              />
                              <button
                                onClick={() => setIsMuted(!isMuted)}
                                className="text-white/70 hover:text-white"
                              >
                                {isMuted ? (
                                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
                                       fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                                       strokeLinejoin="round">
                                    <path d="M11 5 6 9H2v6h4l5 4V5Z"/>
                                    <line x1="23" y1="9" x2="17" y2="15"/>
                                    <line x1="17" y1="9" x2="23" y2="15"/>
                                  </svg>
                                ) : (
                                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
                                       fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                                       strokeLinejoin="round">
                                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                                    <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
                                    <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
                                  </svg>
                                )}
                              </button>
                            </div>
                            <div className={cn(
                              "absolute bottom-0 left-0 right-0 bg-black/60 backdrop-blur-sm p-3 transition-all duration-300",
                              isExpanded ? "h-[50%]" : "h-[25%]"
                            )}>
                              <div className="h-full">
                                <div className={cn(
                                  "text-white h-[calc(100%-20px)] overflow-y-auto"
                                )}>
                                  <p className={cn(
                                    "text-xs text-white/70",
                                    !isExpanded ? "line-clamp-5" : ""
                                  )}>
                                    這是一段視頻描述文本，可以展示視頻的相關信息和簡介。如果文本過長會自動截斷。這是一段視頻描述文本，可以展示視頻的相關信息和簡介。如果文本過長會自動截斷。
                                    這是一段視頻描述文本，可以展示視頻的相關信息和簡介。如果文本過長會自動截斷。這是一段視頻描述文本，可以展示視頻的相關信息和簡介。如果文本過長會自動截斷。
                                    這是一段視頻描述文本，可以展示視頻的相關信息和簡介。如果文本過長會自動截斷。這是一段視頻描述文本，可以展示視頻的相關信息和簡介。如果文本過長會自動截斷。
                                    這是一段視頻描述文本，可以展示視頻的相關信息和簡介。如果文本過長會自動截斷。這是一段視頻描述文本，可以展示視頻的相關信息和簡介。如果文本過長會自動截斷。
                                    這是一段視頻描述文本，可以展示視頻的相關信息和簡介。如果文本過長會自動截斷。這是一段視頻描述文本，可以展示視頻的相關信息和簡介。如果文本過長會自動截斷。
                                  </p>
                                </div>
                                <button
                                  onClick={() => setIsExpanded(!isExpanded)}
                                  className="text-xs text-white/50 hover:text-white/80 absolute bottom-3 left-3"
                                >
                                  {isExpanded ? 'Show less' : 'Show more'}
                                </button>
                              </div>
                            </div>
                          </div>
                          <div className="mt-1 text-left text-xs opacity-70">
                            02:32
                          </div>
                        </div>
                      </div>

                      <div className="w-[45%] space-y-1">
                        <div className="flex w-full gap-1">
                          <button
                            className="flex-1 px-3 py-2 text-xs rounded-md bg-muted-foreground/10 hover:bg-muted-foreground/20">
                            U1
                          </button>
                          <button
                            className="flex-1 px-3 py-2 text-xs rounded-md bg-muted-foreground/10 hover:bg-muted-foreground/20">
                            U2
                          </button>
                          <button
                            className="flex-1 px-3 py-2 text-xs rounded-md bg-muted-foreground/10 hover:bg-muted-foreground/20">
                            U3
                          </button>
                          <button
                            className="flex-1 px-3 py-2 text-xs rounded-md bg-muted-foreground/10 hover:bg-muted-foreground/20">
                            U4
                          </button>
                        </div>
                      </div>
                    </div>
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
          <InputSoundEffect/>
        </div>
      </div>
    </div>
  );
}
