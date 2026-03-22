import { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Video, VideoOff, MessageSquare, Send } from 'lucide-react';

function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [videoEnabled, setVideoEnabled] = useState(true);
  const [messages, setMessages] = useState<{role: string, text: string}[]>([
    { role: 'ai', text: '你好，我是你的AI心理健康伙伴。今天感觉怎么样？' }
  ]);
  //输入框互斥
  const [isAITyping, setIsAITyping] = useState(false);
  const [inputText, setInputText] = useState('');
  const [aiTypingText, setAiTypingText] = useState("");   

  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    // 获取用户摄像头
    if (videoEnabled) {
      navigator.mediaDevices.getUserMedia({ video: true, audio: true })
        .then(stream => {
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
          }
        })
        .catch(err => console.error("摄像头获取失败:", err));
    } else {
      if (videoRef.current && videoRef.current.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach(track => {
          if (track.kind === 'video') track.stop();
        });
        videoRef.current.srcObject = null;
      }
    }
  }, [videoEnabled]);

const handleSendText = async (overrideText?: string) => {
    const textToSend = overrideText ?? inputText;

    if (!textToSend.trim()) return;

    // User message
    const newMessages = [...messages, { role: 'user', text: textToSend }];
    setMessages(newMessages);
    setInputText('');

    // 添加一个空的AI回复用于流式写入
    setMessages(prev => [...prev, { role: 'ai', text: '' }]);

    try {
      const response = await fetch('http://localhost:12345/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ messages: newMessages }),
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;
      let aiResponseText = '';

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.replace('data: ', '');
              if (dataStr === '[DONE]') break;
              try {
                const data = JSON.parse(dataStr);
                console.log("data:",data);
                if (data.error) {
                  aiResponseText += `\n[错误: ${data.error}]`;
                } else if (data.content) {
                  aiResponseText += data.content;
                } else if (data.audio_url) {
              console.log("tts结果:", data.audio_url);
              const audio = new Audio(data.audio_url);
              audio.play();
              }
                
                // 更新界面的最后一条AI回复
                setMessages(prev => {
                  const updated = [...prev];
                  updated[updated.length - 1].text = aiResponseText;
                  return updated;
                });
              } catch (e) {
                // Ignore incomplete JSON chunks from SSE splitting
              }
            }
          }
        }
      }
    } catch (error) {
      console.error("生成回复失败:", error);
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1].text = "网络连接错误或后端未启动，请检查你的服务。";
        return updated;
      });
    }
  };
// asr部分
const wsRef = useRef<WebSocket | null>(null);
const audioContextRef = useRef<AudioContext | null>(null);
const processorRef = useRef<ScriptProcessorNode | null>(null);
const handleToggleRecording = async () => {
  if (!isRecording) {
    setIsRecording(true);

    wsRef.current = new WebSocket("ws://localhost:12345/api/record"); // 替换为你的后端地址
    wsRef.current.onopen = () => {
    console.log("✅ WS connected for ASR streaming");
  };
    wsRef.current.onmessage = (msg) => {
        try {
        const data = JSON.parse(msg.data);

        if (data.type === "conversation.item.input_audio_transcription.completed") {
          const text = data.transcript;

          console.log("🎤 ASR结果:", text);

          // 1️⃣ 写入输入框（模拟用户输入）
          setInputText(text);

          // 2️⃣ 直接调用发送逻辑（模拟按下回车）
          setTimeout(() => {
            handleSendText(text);
          }, 0);
        }
      } catch (e) {
        console.error("WS message parse error:", e);
      }
    };

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioContextRef.current = new AudioContext({ sampleRate: 16000 });
    const source = audioContextRef.current.createMediaStreamSource(stream);
    processorRef.current = audioContextRef.current.createScriptProcessor(4096, 1, 1);

    processorRef.current.onaudioprocess = (event) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

      const inputBuffer = event.inputBuffer.getChannelData(0);
      const pcm16 = floatTo16BitPCM(inputBuffer);
      const base64Chunk = btoa(pcm16);
      wsRef.current.send(JSON.stringify({
        event_id: `event_${Date.now()}`,
        type: "input_audio_buffer.append",
        audio: base64Chunk
      }));
    };

    source.connect(processorRef.current);
    processorRef.current.connect(audioContextRef.current.destination);

  } else {
    setIsRecording(false);

    if (processorRef.current) processorRef.current.disconnect();
    if (audioContextRef.current) audioContextRef.current.close();

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ event_id: `event_${Date.now()}`, type: "input_audio_buffer.commit" }));
      wsRef.current.send(JSON.stringify({ event_id: `event_${Date.now()}`, type: "session.finish" }));
    }
  }
};


function floatTo16BitPCM(float32Array: Float32Array) {
  const buffer = new ArrayBuffer(float32Array.length * 2);
  const view = new DataView(buffer);
  let offset = 0;
  for (let i = 0; i < float32Array.length; i++, offset += 2) {
    let s = Math.max(-1, Math.min(1, float32Array[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  let binary = '';
  const bytes = new Uint8Array(buffer);
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    const sub = bytes.subarray(i, i + chunk);
    binary += String.fromCharCode.apply(null, sub as any);
  }
  return binary;
}
  return (
    <div className="flex w-full h-screen bg-neutral-900 text-neutral-100 font-sans">
      {/* 左侧：3D/2D数字人渲染与摄像头画面 */}
      <div className="flex-1 flex flex-col p-4 bg-black relative">
        {/* 数字人显示区域 */}
        <div className="flex-1 rounded-xl bg-neutral-800 flex items-center justify-center border border-neutral-700 overflow-hidden relative shadow-inner">
          <div className="text-neutral-500 flex flex-col items-center gap-4">
            <div className="w-32 h-32 bg-neutral-700/50 rounded-full flex items-center justify-center animate-pulse">
              <span className="text-sm">Avatar</span>
            </div>
            <p className="text-sm">2D/3D数字人渲染区域 (WebGL/Canvas)</p>
            <p className="text-xs text-neutral-600">等待驱动数据...</p>
          </div>
        </div>

        {/* 底部控制栏 */}
        <div className="h-20 mt-4 bg-neutral-800 rounded-xl flex items-center justify-center gap-6 px-6 border border-neutral-700">
           <button 
            onClick={handleToggleRecording}
            className={`p-4 rounded-full transition-all duration-300 ${isRecording ? 'bg-red-500 hover:bg-red-600' : 'bg-neutral-600 hover:bg-neutral-500'}`}
          >
            {isRecording ? <Mic className="w-6 h-6 text-white" /> : <MicOff className="w-6 h-6 text-white" />}
          </button>
          
          <button 
             onClick={() => setVideoEnabled(!videoEnabled)}
             className={`p-4 rounded-full transition-all duration-300 ${videoEnabled ? 'bg-blue-500 hover:bg-blue-600' : 'bg-neutral-600 hover:bg-neutral-500'}`}
          >
            {videoEnabled ? <Video className="w-6 h-6 text-white" /> : <VideoOff className="w-6 h-6 text-white" />}
          </button>
        </div>

        {/* 右下角：本地摄像头画面 */}
        <div className="absolute bottom-28 right-8 w-48 h-36 bg-neutral-800 rounded-lg overflow-hidden border-2 border-neutral-600 shadow-xl">
          <video 
            ref={videoRef} 
            autoPlay 
            muted 
            className="w-full h-full object-cover transform scale-x-[-1]"
          />
          {!videoEnabled && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/80">
              <VideoOff className="w-6 h-6 text-neutral-400" />
            </div>
          )}
        </div>
      </div>

      {/* 右侧：聊天面板 */}
      <div className="w-96 bg-neutral-800 border-l border-neutral-700 flex flex-col">
        <div className="h-16 border-b border-neutral-700 flex items-center px-6">
          <MessageSquare className="w-5 h-5 mr-3 text-blue-400" />
          <h2 className="font-semibold text-lg">心理引导对话</h2>
        </div>
        
        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                msg.role === 'user' 
                  ? 'bg-blue-600 text-white rounded-br-none' 
                  : 'bg-neutral-700 text-neutral-100 rounded-bl-none'
              }`}>
                {msg.text}
              </div>
            </div>
          ))}
        </div>

        {/* 文本输入 */}
        <div className="p-4 border-t border-neutral-700 bg-neutral-800/50">
          <div className="flex items-center gap-2">
            <input 
              type="text" 
              value={isAITyping ? aiTypingText : inputText} 
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendText()}
              placeholder="输入你想说的话..." 
              className="flex-1 bg-neutral-900 border border-neutral-700 rounded-full px-4 py-2 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
            />
            <button onClick={() => handleSendText()}  
                    className="p-2 bg-blue-600 hover:bg-blue-500 rounded-full text-white transition-colors">
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;