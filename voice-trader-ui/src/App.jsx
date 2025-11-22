import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Activity, DollarSign, TrendingUp, FileText, X } from 'lucide-react';
import './App.css';

function App() {
  // UI States
  const [mode, setMode] = useState("IDLE"); // IDLE, LISTENING, PROCESSING, SPEAKING
  const [transcript, setTranscript] = useState("");
  
  // The "Canvas" - A history of interactions
  const [history, setHistory] = useState([]); 
  
  // Audio Ref for Interrupt handling
  const audioRef = useRef(new Audio());
  const recognitionRef = useRef(null);
  const canvasRef = useRef(null);

  // --- 1. INITIALIZATION ---
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.lang = 'en-IN';
      recognition.interimResults = false;

      recognition.onstart = () => setMode("LISTENING");
      
      recognition.onresult = async (event) => {
        const text = event.results[0][0].transcript;
        setMode("PROCESSING");
        setTranscript(text);
        recognition.stop();
        await handleCommand(text);
      };

      recognitionRef.current = recognition;
    }

    // Spacebar Global Interrupt
    const handleKeyDown = (e) => {
      if (e.code === 'Space') {
        e.preventDefault(); // Prevent scrolling
        interruptAndListen();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Scroll to bottom when history changes
  useEffect(() => {
    if (canvasRef.current) {
      canvasRef.current.scrollTop = canvasRef.current.scrollHeight;
    }
  }, [history]);

  // --- 2. INTERRUPT & LISTEN LOGIC ---
  const interruptAndListen = () => {
    // 1. Kill Audio Immediately
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }

    // 2. Start Listening
    if (recognitionRef.current) {
      try {
        // If already listening, restart. If idle, start.
        recognitionRef.current.stop(); 
        setTimeout(() => recognitionRef.current.start(), 100); 
      } catch (e) { 
        console.error(e); 
      }
    }
  };

  // --- 3. BACKEND COMMUNICATION ---
  const handleCommand = async (text) => {
    try {
      // Optimistic Update: Add user query to history immediately (optional)
      // For now, we wait for server to decide what card to show

      const response = await axios.post('http://localhost:8000/chat', { message: text });
      const data = response.data;
      
      setMode("SPEAKING");

      // --- CARD CREATION LOGIC ---
      let newCard = {
        id: Date.now(),
        type: 'TEXT', // Default
        title: 'Assistant',
        content: data.text,
        sub: ''
      };

      const intent = data.data?.intent;
      
      if (intent === 'CHECK_PRICE' && data.data?.price) {
        newCard = {
          ...newCard,
          type: 'PRICE',
          title: data.data.symbol || 'Stock Price',
          content: `₹${data.data.price}`,
          sub: 'Live Market Data'
        };
      } 
      else if (intent === 'GET_FUNDS') {
        const amount = data.text.match(/[\d,]+\.\d{2}/)?.[0] || "---";
        newCard = {
          ...newCard,
          type: 'FUNDS',
          title: 'Wallet Balance',
          content: `₹${amount}`,
          sub: 'Available Margin'
        };
      }
      else if (intent === 'MARKET_NEWS') {
        newCard = {
          ...newCard,
          type: 'NEWS',
          title: 'Market Intelligence',
          content: 'News Summary',
          sub: data.text.replace("Here is the latest news for", "Analysis:")
        };
      }

      // Add to Canvas History
      setHistory(prev => [...prev, newCard]);

      // Play Audio
      if (data.audio_base64) {
        audioRef.current.src = `data:audio/mp3;base64,${data.audio_base64}`;
        audioRef.current.play()
          .then(() => console.log("Playing"))
          .catch(e => console.error("Playback failed", e));
        
        audioRef.current.onended = () => setMode("IDLE");
      } else {
        setTimeout(() => setMode("IDLE"), 2000);
      }

    } catch (error) {
      setMode("IDLE");
      console.error(error);
    }
  };

  return (
    <>
      {/* --- 1. THE CANVAS (Persistent History) --- */}
      <div className="canvas-container" ref={canvasRef}>
        <div className="card-grid">
          <AnimatePresence>
            {history.map((card) => (
              <motion.div
                key={card.id}
                className="notion-card"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
              >
                <div className="card-header">
                  {card.type === 'PRICE' ? <TrendingUp size={16}/> : 
                   card.type === 'FUNDS' ? <DollarSign size={16}/> :
                   card.type === 'NEWS' ? <FileText size={16}/> : <Activity size={16}/>}
                  <span>{card.title}</span>
                </div>
                
                {/* Content rendering based on type */}
                <div className="card-content">
                  {card.type === 'NEWS' ? 
                    <div style={{fontSize: '1rem', lineHeight: '1.5'}}>{card.sub}</div> 
                    : card.content
                  }
                </div>
                
                {card.type !== 'NEWS' && <div className="card-sub">{card.sub}</div>}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* --- 2. THE TRANSCRIPT PILL --- */}
      <AnimatePresence>
        {(mode !== 'IDLE') && (
          <motion.div 
            className="transcript-overlay"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
          >
            {mode === 'LISTENING' ? "Listening..." : 
             mode === 'PROCESSING' ? "Thinking..." : transcript}
          </motion.div>
        )}
      </AnimatePresence>

      {/* --- 3. FLOATING DRAGGABLE BLOB --- */}
      <motion.div 
        className="blob-wrapper"
        drag
        dragMomentum={false} // Stops sliding after release
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={interruptAndListen} // Click = Interrupt & Listen
      >
        <motion.div 
          className="obsidian-orb"
          animate={{
            boxShadow: mode === 'LISTENING' 
              ? "0px 0px 40px rgba(0,0,0,0.4)" 
              : "0px 10px 30px rgba(0,0,0,0.3)"
          }}
        >
          {/* Inner Pulse */}
          {mode === 'LISTENING' && (
            <motion.div 
              className="ripple"
              style={{ width: '100%', height: '100%' }}
              animate={{ scale: [1, 2], opacity: [0.5, 0] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            />
          )}
          
          <Mic color="white" size={32} opacity={mode === 'LISTENING' ? 1 : 0.5} />
        </motion.div>
      </motion.div>
    </>
  );
}

export default App;