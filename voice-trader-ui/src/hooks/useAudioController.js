import { useRef, useEffect, useCallback } from 'react';

export const useAudioController = () => {
  const voiceRef = useRef(new Audio());
  const bgmRef = useRef(new Audio());
  const sfxRef = useRef(new Audio());

  // Initialize Audio Listeners (for BGM loop)
  useEffect(() => {
    bgmRef.current.loop = true;
    bgmRef.current.volume = 0.2;
  }, []);

  const playSfx = useCallback((filename) => {
    sfxRef.current.src = `/sounds/${filename}`;
    sfxRef.current.volume = 0.4;
    sfxRef.current.play().catch(e => console.log("SFX Blocked", e));
  }, []);

  const playBgm = useCallback((type) => {
    const track = type === 'NEWS' ? '/sounds/news_bed.mp3' : '/sounds/ambient_loop.mp3';
    
    // Only change if track is different
    if (!bgmRef.current.src.includes(track)) {
        bgmRef.current.pause();
        bgmRef.current.src = track;
        bgmRef.current.play().catch(e => console.log("Autoplay blocked", e));
    }
  }, []);

  const playVoice = useCallback((audioBase64, onEnded) => {
    voiceRef.current.src = `data:audio/mp3;base64,${audioBase64}`;
    
    // Duck BGM
    bgmRef.current.volume = 0.1; 
    
    voiceRef.current.play();
    
    voiceRef.current.onended = () => {
      // Restore BGM
      bgmRef.current.volume = 0.3; 
      if (onEnded) onEnded();
    };
  }, []);

  const stopVoice = useCallback(() => {
    voiceRef.current.pause();
    voiceRef.current.currentTime = 0;
    bgmRef.current.volume = 0.2; 
  }, []);

  const setBgmVolume = useCallback((vol) => {
    bgmRef.current.volume = vol;
  }, []);

  return {
    playSfx,
    playBgm,
    playVoice,
    stopVoice,
    setBgmVolume
  };
};
