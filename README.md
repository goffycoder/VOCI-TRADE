# 🎤 Voice Trader (VociTrade)

> **Revolutionizing Stock Trading Through Voice-First Interaction Design**

<div align="center">

![Voice Trading](https://img.shields.io/badge/Modality-Voice%20First-blue?style=for-the-badge)
![HCI Project](https://img.shields.io/badge/HCI-Human%20Computer%20Interaction-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)

**A multimodal trading interface that brings the power of voice commands to the Indian stock market**

[🎯 Features](#-key-features) • [🏗️ Architecture](#️-system-architecture) • [📊 User Study](#-user-study-results) • [🚀 Quick Start](#-quick-start)

</div>

---

## 📖 Project Overview

**Voice Trader** introduces a paradigm shift in retail trading by eliminating the traditional point-and-click interface in favor of natural voice interaction. Built as an HCI exploration, this system demonstrates how voice modality can reduce cognitive load, increase trading speed, and make financial markets more accessible.

> **⚠️ REAL TRADING SYSTEM**: This is NOT a simulation. Voice Trader executes actual trades on a live brokerage account using real-time market data. Every order impacts real positions and capital.

### 🎯 The HCI Innovation

Traditional trading platforms require users to navigate complex multi-level menus, context-switch between information gathering and action execution, and perform repetitive manual tasks. **Voice Trader solves this by:**

- ✅ Enabling hands-free, eyes-free operation
- ✅ Supporting natural language with context awareness
- ✅ Providing real-time audio and visual feedback loops
- ✅ Handling complex multi-step workflows conversationally
- ✅ **Executing real trades** with live market data integration

**Validated Results**: Our user study with 15 participants demonstrated **60.8% average time reduction** and **80.4% fewer errors** compared to traditional GUI interfaces.

---

## ✨ Key Features

### 🗣️ Natural Language Understanding
```
User: "Buy max shares of Reliance with my available balance"
System: [Calculates funds → Fetches live price → Places order]
```

- **Intent Recognition**: 9 distinct trading intents (orders, news, portfolio, positions, etc.)
- **Slot Filling**: Multi-turn conversations to complete incomplete orders
- **Smart Disambiguation**: Fuzzy matching for company names with phonetic tolerance

### 🎯 Advanced Order Types

| Order Type | Description | Voice Example |
|------------|-------------|---------------|
| **Market** | Instant execution at current price | *"Buy 10 shares of TCS"* |
| **Limit** | Execute at specific price | *"Sell 50 Infosys at 1500 rupees"* |
| **Super Order** | Bracket order with target & stop-loss | *"Buy 100 HDFC at 1600 with target 1700 and stop loss 1550"* |
| **Bulk** | Multiple orders in one command | *"Buy 10 TCS and sell 5 Reliance"* |
| **Dynamic Quantity** | Percentage-based allocation | *"Buy 50% of Tata Motors with my funds"* |

### 🔔 Real-Time Notifications

- **WebSocket Integration**: Live order status updates from exchange
- **Contextual Audio Cues**: Different sounds for success/failure/info
- **Toast Notifications**: Non-intrusive visual confirmations
- **Live Trading Execution**: Real orders placed on actual NSE/BSE exchanges

### 🎨 Adaptive UI Components

The interface features three primary zones that work in harmony:

**History Feed** displays visual history of actions including price cards with trend indicators, news summaries with sentiment analysis, and holdings/positions displays.

**Interaction Island** shows current system state (IDLE, LISTENING, or PROCESSING) with intuitive visual feedback.

**Quick Actions** provides one-tap shortcuts for Portfolio, Funds, and Positions queries.

---

## 🏗️ System Architecture

### Technology Stack

**Frontend** (React + Vite): Speech Recognition (Web Speech API), Audio Playback (Web Audio API), Real-time Updates (WebSockets), and Reactive UI (React Hooks + Custom Controllers).

**Backend** (FastAPI + Python): NLU Engine (Google Gemini Flash), Speech Synthesis (ElevenLabs), Trading API (Dhan HQ - Live Account), Market Data (Real-time NSE/BSE + Google News), and WebSocket Server (Live Order Updates).

### Data Flow

The system follows a streamlined flow: User voice input is captured via Web Speech API and sent to the FastAPI server. The server uses Gemini for intent analysis, routes requests to appropriate handlers (Dhan API for orders, Google News for market intel, etc.), generates audio responses via ElevenLabs, and sends live order updates back through WebSocket connections.

### Key Modules

**nlu_service.py** handles intent classification and entity extraction using Gemini Flash. **dhan_handler.py** manages order execution and portfolio operations via the Dhan HQ SDK. **stock_finder.py** performs fuzzy symbol matching across 4000+ stocks using Pandas and SequenceMatcher. **speech_service.py** generates audio and transcribes speech using ElevenLabs and Google STT. **chat_service.py** provides conversational AI for general queries with context injection.

---

## 📊 User Study Results

To validate the efficacy of VociTrade, I conducted a comprehensive usability study employing a **Within-Subjects A/B Testing design**. The primary objective was to quantify the reduction in execution latency and cognitive friction when transitioning from traditional GUI to voice interface.

### Study Design

**Participants**: 15 users (N=15) ranging from novice investors to intermediate traders

**Methodology**: Counter-balanced protocol to mitigate learning effects
- Group A (8 users): Voice first, then GUI
- Group B (7 users): GUI first, then Voice

**Control Condition**: Standard Dhan Web Portal (desktop browser)

**Experimental Condition**: VociTrade prototype

### Task Scenarios

Four specific trading workflows were selected to represent varying levels of complexity:

**Task A - Super Order**: Placing a complex bracket order with four distinct variables (Quantity, Entry Price, Target Price, Stop Loss). This tests the system's ability to handle multi-parameter commands.

**Task B - Bulk Execution**: Buying two distinct stocks and selling two others in rapid succession. This concurrency test evaluates the interface's efficiency for multiple simultaneous operations.

**Task C - Panic Square Off**: Urgent instruction to close all open positions immediately. This simulates high-stress trading scenarios where speed is critical.

**Task D - After Market Order (AMO)**: Placing an order outside market hours, which typically requires locating a specific hidden toggle in traditional GUIs.

### Quantitative Results

The data reveals significant improvements across all metrics:

| Task Type | GUI Time (s) | Voice Time (s) | Time Improvement | GUI Errors | Voice Errors | Error Reduction |
|-----------|-------------|----------------|------------------|------------|--------------|-----------------|
| **Task A (Super Order)** | 45.39 | 17.58 | **61.2%** | 16 | 2 | 87.5% |
| **Task B (Bulk Order)** | 60.97 | 23.49 | **61.5%** | 14 | 4 | 71.4% |
| **Task C (Square Off)** | 14.98 | 10.79 | **27.9%** | 9 | 3 | 66.7% |
| **Task D (AMO)** | 41.54 | 11.99 | **71.1%** | 7 | 0 | 100% |
| **Average/Total** | 40.72 | 15.96 | **60.8%** | 46 | 9 | **80.4%** |

### Key Findings

**Execution Speed**: The voice interface outperformed GUI across all tasks, with improvement margins widening as task complexity increased. The most dramatic improvement (71.1%) was observed in Task D, where users struggled to locate the hidden AMO toggle in the GUI hierarchy.

**Error Reduction**: Participants committed 46 total errors using GUI compared to only 9 errors using Voice—an 80.4% reduction. Qualitative observation revealed GUI errors stemmed from "split attention" as users mistyped numbers while shifting gaze between keyboard and screen. Voice input maintained user focus, and the LLM's semantic correction handled phonetic slips.

**Consistency**: Voice interface demonstrated not only faster execution but significantly lower variance in completion times, indicating higher consistency across users and task repetitions.

**Complexity Decoupling**: For complex tasks (A & B), the GUI forced serial interactions through multiple fields, while VociTrade allowed users to express all variables in a single natural language utterance.

### Qualitative Insights

Post-study surveys (Likert Scale 1-7) indicated strong preference for voice modality:

- **Overall Rating**: 6.46/7 average across all participants
- **Task Complexity Preference**: Users rated voice interface at 6.2/7 for complex tasks
- **Stress Reduction**: For Task C (Square Off), participants noted that while the time difference was smaller (27.9%), the voice command felt "safer" and less stressful than searching for exit buttons during simulated panic scenarios

**User Testimonials**:
- *"The ability to say everything in one sentence for bracket orders was game-changing"*
- *"I didn't have to hunt through menus—just spoke what I wanted"*
- *"The voice interface felt more natural, like talking to a broker"*

### Statistical Significance

The counter-balanced design controlled for learning effects, and the consistent improvement across both user groups (A and B) demonstrates that the results are attributable to interface modality rather than task familiarity. The large effect sizes (60.8% time reduction, 80.4% error reduction) provide strong evidence for the efficacy of voice-first design in trading contexts.

---

## 🚀 Quick Start

### Prerequisites

```bash
# Required API Keys (add to .env)
GOOGLE_API_KEY=your_gemini_key
ELEVENLABS_API_KEY=your_elevenlabs_key
DHAN_CLIENT_ID=your_dhan_client_id
DHAN_ACCESS_TOKEN=your_dhan_access_token
```

### Installation

```bash
# Clone the repository
git clone https://github.com/goffycoder/VOCI-TRADE.git
cd voice-trader

# Backend setup
cd backend
pip install -r requirements.txt
python server.py

# Frontend setup (new terminal)
cd ../frontend
npm install
npm run dev
```

### Usage

1. **Grant microphone permissions** when prompted
2. **Press SPACEBAR** to start/stop listening
3. **Speak naturally**: *"What's the price of Reliance?"*
4. **Press ?** for command palette

---

## 🎨 Design Philosophy

### 1. Voice-First, Not Voice-Only
We complement voice with visual feedback because humans need confirmation for financial decisions, visual context aids memory and reduces errors, and multimodal redundancy improves accessibility.

### 2. Progressive Disclosure
Simple commands get instant results. Complex workflows (Super Orders) use guided slot-filling. The system asks clarifying questions only when necessary.

### 3. Forgiveness & Error Recovery
The system detects and corrects common speech-to-text errors. For example, "Cell 10 shares" is automatically corrected to "SELL" based on context.

### 4. Ambient Awareness
Background music changes based on context (news mode, trading mode). Audio ducking occurs during voice responses. Non-blocking notifications provide order updates without disrupting workflow.

---

## 🔬 HCI Research Contributions

### Evaluated Dimensions

| Dimension | Traditional GUI | Voice Trader | Improvement |
|-----------|-----------------|--------------|-------------|
| **Task Completion Time** | 40.72s average | 15.96s average | **60.8% faster** |
| **Error Rate** | 46 total errors | 9 total errors | **80.4% reduction** |
| **Cognitive Load** | High (visual scanning) | Low (natural speech) | Reduced friction |
| **Consistency** | High variance | Low variance | More predictable |
| **Accessibility** | Requires visual attention | Hands-free capable | Enables multitasking |

### Novel Interaction Patterns

**Contextual Slot Filling**: System remembers partial orders across conversational turns, allowing users to build complex commands incrementally.

**Dynamic Quantity Resolution**: "Max" and "50%" are computed server-side based on available funds and current market prices.

**Intent Fallback Chain**: Order → Chat → Conversational (the system never responds with "I don't understand").

**Complexity Flattening**: Multi-step GUI workflows collapsed into single-utterance commands.

---

## 📁 Project Structure

```
voice-trader/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── InteractionIsland.jsx    # Voice state indicator
│   │   │   ├── HistoryFeed.jsx          # Visual action log
│   │   │   ├── QuickActions.jsx         # Shortcut buttons
│   │   │   └── CommandPalette.jsx       # Help menu
│   │   ├── hooks/
│   │   │   ├── useAudioController.js    # Sound management
│   │   │   └── useToast.js              # Notification system
│   │   └── App.jsx                      # Main orchestrator
│   └── package.json
│
├── backend/
│   ├── server.py                         # FastAPI server
│   ├── nlu_service.py                    # Gemini intent engine
│   ├── dhan_handler.py                   # Trading API wrapper
│   ├── stock_finder.py                   # Symbol search engine
│   ├── speech_service.py                 # TTS/STT handlers
│   ├── chat_service.py                   # Conversational AI
│   ├── news_service.py                   # Market news fetcher
│   └── NSE_ONLY_STOCKS.csv              # 4000+ stock database
│
└── README.md
```

---

## 🛠️ Technical Challenges Solved

### 1. Ambiguous Entity Resolution
**Problem**: 4000+ stocks with similar names  
**Solution**: Multi-strategy matching (exact → abbreviated → fuzzy → partial)

### 2. Real-Time Order Updates
**Problem**: Orders placed via voice need instant status feedback  
**Solution**: Dual-channel updates (HTTP response + WebSocket broadcast)

### 3. Live Market Data Integration
**Problem**: Real trading requires accurate, up-to-the-second pricing  
**Solution**: Direct exchange connectivity via Dhan API with <100ms latency

### 4. Risk Management in Voice Interface
**Problem**: Voice commands are irreversible and high-stakes  
**Solution**: Multi-layer validation (funds check → price verification → confirmation flow)

### 5. TTS Markdown Cleanup
**Problem**: LLM responses contain formatting characters unsuitable for speech  
**Solution**: Regex preprocessing removes markdown syntax before audio generation

---

## 🔮 Future Enhancements

- [ ] **Multi-language Support**: Hindi, Tamil, Bengali voice commands
- [ ] **Wake Word Detection**: "Hey Trader, buy Reliance"
- [ ] **Voice Biometrics**: Speaker verification for enhanced security
- [ ] **Integrating Options & Futures **: Derivative contracts
- [ ] **Mobile App**: Native iOS/Android with offline STT
- [ ] **Portfolio Analytics**: Voice-activated performance insights
- [ ] **Smart Alerts**: Proactive notifications for price targets and stop losses

---

## ⚠️ Important Disclaimers

### Real Trading Environment
This system connects to **live brokerage accounts** and executes **real trades** with **real money**. 

- ✅ Orders are executed on actual NSE/BSE exchanges
- ✅ Market data is fetched in real-time from live feeds
- ✅ Portfolio, positions, and funds reflect actual account status
- ⚠️ All trades have financial consequences
- ⚠️ Use with caution and proper risk management

### Academic Use
This project was developed for **educational and research purposes** to explore voice-first interaction design in high-stakes domains. It is not financial advice.

---

## 🤝 Contributing

This is an academic HCI project. For inquiries:
- **Student**: Vraj Chetankumar Patel
- **Course**: Human-Computer Interaction (HCI)
- **Institution**: Stony Brook University
- **Contact**: vrajchetankuma.patel@stonybrook.edu

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 🙏 Acknowledgments

- **Google Gemini** for state-of-the-art NLU capabilities
- **ElevenLabs** for human-like voice synthesis
- **Dhan HQ** for comprehensive trading APIs and live market connectivity
- **NSE India** for market data standards
- **Study Participants** for valuable feedback and rigorous testing

---

## 📚 Citations

If you use this work in academic research, please cite:

```bibtex
@software{patel2024vocitrade,
  author = {Patel, Vraj Chetankumar},
  title = {VociTrade: Voice-First Trading Interface for Reduced Cognitive Load},
  year = {2024},
  institution = {Stony Brook University},
  howpublished = {\url{https://github.com/goffycoder/VOCI-TRADE}}
}
```

---

<div align="center">

**Built with 🎤 for the future of accessible trading**

⭐ Star this repo if you find it interesting | 🐛 Report issues | 💡 Suggest features

*Validated through rigorous HCI research: 60.8% faster, 80.4% fewer errors*

</div>
