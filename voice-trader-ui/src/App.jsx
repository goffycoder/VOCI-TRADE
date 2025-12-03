import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';
import { useAudioController } from './hooks/useAudioController';
import HistoryFeed from './components/HistoryFeed';
import InteractionIsland from './components/InteractionIsland';
import Header from './components/Header';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastProvider, useToast } from './hooks/useToast';
import CommandPalette from './components/CommandPalette';
import QuickActions from './components/QuickActions';

function VoiceTraderApp() {
  const [mode, setMode] = useState("IDLE");
  const [transcript, setTranscript] = useState("");
  const [history, setHistory] = useState([]);
  const [serverContext, setServerContext] = useState({});
  const [isConnected, setIsConnected] = useState(true);
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  const { playSfx, playBgm, playVoice, stopVoice, setBgmVolume } = useAudioController();
  const toast = useToast();
  const recognitionRef = useRef(null);


  // Initialize Audio
  useEffect(() => {
    // Start Ambient Music on first interaction
    const initAudio = () => {
      playBgm('AMBIENT');
      window.removeEventListener('click', initAudio);
      window.removeEventListener('keydown', initAudio);
    };
    window.addEventListener('click', initAudio);
    window.addEventListener('keydown', initAudio);

    // STT Setup
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.lang = 'en-IN';
      recognition.onstart = () => {
        setMode("LISTENING");
        setBgmVolume(0.1); // Duck volume
      };
      recognition.onresult = async (event) => {
        const text = event.results[0][0].transcript;
        setMode("PROCESSING");
        setTranscript(text);
        recognition.stop();
        await handleCommand(text);
      };
      recognitionRef.current = recognition;
    }

    // Spacebar to toggle listening on/off
    const handleKeyDown = (e) => {
      if (e.code === 'Space' && !isHelpOpen) {
        e.preventDefault();

        // If already listening, stop
        if (mode === 'LISTENING') {
          if (recognitionRef.current) {
            try {
              recognitionRef.current.stop();
              setMode('IDLE');
              setBgmVolume(0.3); // Reset BGM volume
            } catch (err) {
              console.error('Error stopping recognition:', err);
            }
          }
        } else {
          // Otherwise, start listening
          interruptAndListen();
        }
      }

      if (e.key === '?' && !isHelpOpen) {
        e.preventDefault();
        setIsHelpOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [playBgm, setBgmVolume, isHelpOpen, mode]);

  const interruptAndListen = () => {
    stopVoice();

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
        setTimeout(() => recognitionRef.current.start(), 100);
      } catch (e) { console.error(e); }
    }
  };

  const handleQuickAction = async (action) => {
    const commandMap = {
      'portfolio': 'Show my holdings',
      'funds': 'Show my funds',
      'positions': 'Show my positions'
    };

    const command = commandMap[action];
    if (command) {
      setMode('PROCESSING');
      await handleCommand(command);
    }
  };

  const handleCommand = async (text) => {
    try {
      setIsConnected(true); // Connection successful
      const payload = { message: text, context: serverContext };
      const response = await axios.post('http://localhost:8000/chat', payload);
      const data = response.data;
      const intent = data.data?.intent;

      // Update Context
      if (data.data && (data.data.status === "WAITING_FOR_SLOT" || data.data.pending_order)) {
        setServerContext(data.data);
      } else {
        setServerContext({});
      }

      setMode("SPEAKING");

      // --- AUDIO & UI LOGIC ---
      let newItem = { id: Date.now(), type: 'TEXT', content: data.text };

      // 1. NEWS LOGIC
      if (intent === 'MARKET_NEWS') {
        playBgm('NEWS');
        newItem = {
          type: 'NEWS',
          content: data.text.replace("Here is the latest news for", "")
        };
      }

      // 2. PRICE LOGIC
      else if (intent === 'CHECK_PRICE' && data.data?.price) {
        const isPositive = Math.random() > 0.5;
        playSfx(isPositive ? 'success2.mp3' : 'failure.mp3');

        newItem = {
          type: 'PRICE',
          data: {
            symbol: data.data.symbol,
            price: data.data.price,
            change: isPositive ? 'up' : 'down'
          }
        };
      }

      // 3. ORDER LOGIC
      else if (intent === 'ORDER_RESULT') {
        playSfx('confirm.mp3');
        // Show toast notification
        if (data.text.toLowerCase().includes('successfully') || data.text.toLowerCase().includes('placed')) {
          toast.success(data.text);
        } else if (data.text.toLowerCase().includes('rejected') || data.text.toLowerCase().includes('failed')) {
          toast.error(data.text);
        } else if (data.text.toLowerCase().includes('insufficient')) {
          toast.warning(data.text);
        }
      }

      // 4. FUNDS LOGIC
      else if (intent === 'GET_FUNDS') {
        playSfx('success.mp3');
        newItem = {
          type: 'FUNDS',
          content: data.text.match(/[\d,]+\.\d{2}/)?.[0] || "---"
        };
      }

      // 5. HOLDINGS LOGIC
      else if (intent === 'GET_HOLDINGS' || data.data?.type === 'HOLDINGS') {
        playSfx('success.mp3');
        newItem = {
          type: 'HOLDINGS',
          content: data.text
        };
      }

      // 6. POSITIONS LOGIC
      else if (intent === 'GET_POSITIONS' || data.data?.type === 'POSITIONS') {
        playSfx('success.mp3');
        newItem = {
          type: 'POSITIONS',
          content: data.text
        };
      }

      // Add to History
      const isSystemMessage = data.text.toLowerCase().includes("system error") ||
        (data.data?.status === "WAITING_FOR_SLOT");

      if (!isSystemMessage) addToHistory(newItem);

      // Play Voice
      if (data.audio_base64) {
        playVoice(data.audio_base64, () => {
          setMode("IDLE");
          // If news, revert to ambient
          if (intent === 'MARKET_NEWS') playBgm('AMBIENT');
        });
      } else {
        setMode("IDLE");
        setBgmVolume(0.3);
      }

    } catch (error) {
      setMode("IDLE");
      setIsConnected(false); // Connection failed
      console.error(error);
    }
  };

  const addToHistory = (newItem) => {
    setHistory(prev => {
      const lastItem = prev[prev.length - 1];
      if (newItem.type === 'PRICE' && lastItem && lastItem.type === 'PRICE_CLUSTER') {
        const updatedCluster = { ...lastItem, data: [...lastItem.data, newItem.data] };
        return [...prev.slice(0, -1), updatedCluster];
      }
      if (newItem.type === 'PRICE') {
        return [...prev, { id: Date.now(), type: 'PRICE_CLUSTER', title: 'Market Watch', data: [newItem.data] }];
      }
      return [...prev, newItem];
    });
  };

  return (
    <ErrorBoundary>
      <Header isConnected={isConnected} />
      <HistoryFeed history={history} />
      <InteractionIsland
        mode={mode}
        transcript={transcript}
        onInterrupt={interruptAndListen}
      />
      <QuickActions
        onOpenHelp={() => setIsHelpOpen(true)}
        onTriggerAction={handleQuickAction}
      />
      <CommandPalette isOpen={isHelpOpen} onClose={() => setIsHelpOpen(false)} />
    </ErrorBoundary>
  );
}

// Wrap with ToastProvider for global toast access
function App() {
  return (
    <ToastProvider>
      <VoiceTraderApp />
    </ToastProvider>
  );
}

export default App;