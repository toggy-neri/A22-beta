import { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Video, VideoOff, MessageSquare, Send, Users, Loader2, Heart, Brain, Sparkles, ChevronRight } from 'lucide-react';

interface AvatarInfo {
  id: string;
  name: string;
  has_full_imgs: boolean;
  has_face_imgs: boolean;
  frame_count?: number;
}

function App() {
  const [showWelcome, setShowWelcome] = useState(true);
  const [isEntering, setIsEntering] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [videoEnabled, setVideoEnabled] = useState(true);
  const [messages, setMessages] = useState<{ role: string, text: string }[]>([
    { role: 'ai', text: '你好，我是你的AI心理健康伙伴。今天感觉怎么样？' }
  ]);
  const [isAITyping] = useState(false);
  const [inputText, setInputText] = useState('');
  const [aiTypingText] = useState("");
  
  const [avatars, setAvatars] = useState<AvatarInfo[]>([]);
  const [currentAvatar, setCurrentAvatar] = useState<string>('');
  const [showAvatarSelector, setShowAvatarSelector] = useState(false);
  const [isSwitchingAvatar, setIsSwitchingAvatar] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);

  const avatarVideoRef = useRef<HTMLVideoElement>(null);
  const avatarAudioRef = useRef<HTMLAudioElement>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const [sessionId, setSessionId] = useState<number>(0);
  const [connectionState, setConnectionState] = useState<string>('disconnected');

  const handleEnter = () => {
    setIsEntering(true);
    setTimeout(() => {
      setShowWelcome(false);
    }, 800);
  };

  useEffect(() => {
    fetch('http://localhost:12345/api/avatars')
      .then(res => res.json())
      .then(data => {
        if (data.code === 0 && data.avatars) {
          setAvatars(data.avatars);
          if (data.avatars.length > 0) {
            setCurrentAvatar(data.avatars[0].id);
          }
        }
      })
      .catch(err => console.error('Failed to fetch avatars:', err));
  }, []);

  const handleSwitchAvatar = async (avatarId: string) => {
    if (isSwitchingAvatar) return;
    
    console.log('[Avatar] Switching to:', avatarId, 'sessionId:', sessionId);
    setIsSwitchingAvatar(true);
    
    try {
      const response = await fetch('http://localhost:12345/api/switch_avatar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionid: sessionId, avatar_id: avatarId })
      });
      
      const data = await response.json();
      console.log('[Avatar] Switch response:', data);
      if (data.code === 0) {
        setCurrentAvatar(avatarId);
        console.log('Switched to avatar:', avatarId);
      } else {
        console.error('Failed to switch avatar:', data.msg);
        alert('切换数字人失败: ' + data.msg);
      }
    } catch (err) {
      console.error('Error switching avatar:', err);
      alert('切换数字人出错: ' + err);
    } finally {
      setIsSwitchingAvatar(false);
      setShowAvatarSelector(false);
    }
  };

  useEffect(() => {
    const pc = new RTCPeerConnection({
      sdpSemantics: 'unified-plan',
      iceServers: []
    } as RTCConfiguration);
    pcRef.current = pc;

    pc.addTransceiver('video', { direction: 'recvonly' });
    pc.addTransceiver('audio', { direction: 'recvonly' });

    pc.ontrack = (evt) => {
      console.log('[WebRTC] Received track:', evt.track.kind, evt.streams);
      if (evt.track.kind === 'video' && avatarVideoRef.current) {
        const video = avatarVideoRef.current;
        video.srcObject = evt.streams[0];
        
        video.onloadedmetadata = () => {
          console.log('[WebRTC] Video metadata loaded, videoWidth:', video.videoWidth, 'videoHeight:', video.videoHeight);
        };
        
        video.oncanplay = () => {
          console.log('[WebRTC] Video can play');
        };
        
        video.onplay = () => {
          console.log('[WebRTC] Video started playing');
        };
        
        video.onerror = (e) => {
          console.error('[WebRTC] Video error:', e);
        };
        
        const playPromise = video.play();
        if (playPromise !== undefined) {
          playPromise
            .then(() => console.log('[WebRTC] Video play() succeeded'))
            .catch(e => {
              console.log('[WebRTC] Video play() failed:', e.name, e.message);
              video.muted = true;
              video.play().catch(e2 => console.log('[WebRTC] Video play() retry failed:', e2));
            });
        }
      }
      if (evt.track.kind === 'audio' && avatarAudioRef.current) {
        const audio = avatarAudioRef.current;
        audio.srcObject = evt.streams[0];
        audio.play().catch(e => console.log('[WebRTC] Audio play error:', e));
      }
    };

    pc.onconnectionstatechange = () => {
      console.log('[WebRTC] Connection state:', pc.connectionState);
      setConnectionState(pc.connectionState);
    };

    pc.oniceconnectionstatechange = () => {
      console.log('[WebRTC] ICE state:', pc.iceConnectionState);
    };

    const negotiate = async () => {
      try {
        console.log('[WebRTC] Creating offer...');
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        console.log('[WebRTC] Local description set, ICE state:', pc.iceGatheringState);

        const iceGatheringPromise = new Promise<void>((resolve) => {
          if (pc.iceGatheringState === 'complete') {
            console.log('[WebRTC] ICE gathering already complete');
            resolve();
          } else {
            const checkState = () => {
              console.log('[WebRTC] ICE state changed:', pc.iceGatheringState);
              if (pc.iceGatheringState === 'complete') {
                console.log('[WebRTC] ICE gathering complete');
                pc.removeEventListener('icegatheringstatechange', checkState);
                resolve();
              }
            };
            pc.addEventListener('icegatheringstatechange', checkState);
            setTimeout(() => {
              console.log('[WebRTC] ICE gathering timeout, proceeding anyway');
              pc.removeEventListener('icegatheringstatechange', checkState);
              resolve();
            }, 3000);
          }
        });

        await iceGatheringPromise;

        console.log('[WebRTC] Sending offer to backend...');
        const response = await fetch('http://localhost:12345/offer', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sdp: pc.localDescription?.sdp,
            type: pc.localDescription?.type,
          })
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const answer = await response.json();
        console.log('[WebRTC] Received answer, sessionid:', answer.sessionid);
        setSessionId(answer.sessionid || 0);
        
        if (answer.sdp && answer.type) {
          await pc.setRemoteDescription(answer);
          console.log('[WebRTC] Remote description set successfully');
        } else {
          throw new Error('Invalid answer from server');
        }
      } catch (err) {
        console.error("[WebRTC] 连接失败:", err);
        setConnectionState('failed');
      }
    };

    negotiate();

    return () => {
      pc.close();
    };
  }, []);

  useEffect(() => {
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

    const newMessages = [...messages, { role: 'user', text: textToSend }];
    setMessages(newMessages);
    setInputText('');

    setMessages(prev => [...prev, { role: 'ai', text: '' }]);

    try {
      const response = await fetch('http://localhost:12345/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ messages: newMessages, sessionid: sessionId }),
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
                console.log("data:", data);
                if (data.error) {
                  aiResponseText += `\n[错误: ${data.error}]`;
                } else if (data.content) {
                  aiResponseText += data.content;
                } else if (data.audio_url) {
                  console.log("tts结果:", data.audio_url);
                  const audio = new Audio(data.audio_url);
                  audio.play();
                }

                setMessages(prev => {
                  const updated = [...prev];
                  updated[updated.length - 1].text = aiResponseText;
                  return updated;
                });
              } catch (e) {
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

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const handleToggleRecording = async () => {
    if (!isRecording) {
      setIsRecording(true);

      wsRef.current = new WebSocket("ws://localhost:12345/api/record");
      wsRef.current.onopen = () => {
        console.log("✅ WS connected for ASR streaming");
      };
      wsRef.current.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data);

          if (data.type === "conversation.item.input_audio_transcription.completed") {
            const text = data.transcript;

            console.log("🎤 ASR结果:", text);

            setInputText(text);

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

  if (showWelcome) {
    return (
      <div className={`w-full h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center overflow-hidden relative transition-all duration-700 ${isEntering ? 'opacity-0 scale-95' : 'opacity-100 scale-100'}`}>
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-200 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-200 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-2000"></div>
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-pink-200 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-4000"></div>
        </div>

        <div className="absolute top-10 left-10 opacity-20">
          <Heart className="w-16 h-16 text-pink-400 animate-pulse" />
        </div>
        <div className="absolute top-20 right-20 opacity-20">
          <Brain className="w-20 h-20 text-blue-400 animate-pulse animation-delay-1000" />
        </div>
        <div className="absolute bottom-20 left-20 opacity-20">
          <Sparkles className="w-14 h-14 text-purple-400 animate-pulse animation-delay-2000" />
        </div>
        <div className="absolute bottom-10 right-10 opacity-20">
          <Heart className="w-12 h-12 text-pink-400 animate-pulse animation-delay-3000" />
        </div>

        <div className="relative z-10 text-center px-8">
          <div className="mb-8 flex justify-center">
            <div className="relative">
              <div className="w-32 h-32 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center shadow-2xl transform hover:scale-105 transition-transform duration-300">
                <Brain className="w-16 h-16 text-white" />
              </div>
              <div className="absolute -top-2 -right-2 w-8 h-8 bg-pink-400 rounded-full flex items-center justify-center animate-bounce">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
            </div>
          </div>

          <h1 className="text-6xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-500 bg-clip-text text-transparent mb-6 tracking-wide">
            心理诊疗室
          </h1>
          
          <p className="text-xl text-gray-500 mb-4 font-light tracking-wider">
            Psychological Counseling Room
          </p>
          
          <p className="text-gray-400 mb-12 max-w-md mx-auto leading-relaxed">
            在这里，你将找到倾听与理解<br/>
            让我们一起探索内心的世界
          </p>

          <button
            onClick={handleEnter}
            className="group relative px-10 py-4 bg-gradient-to-r from-blue-500 to-purple-500 text-white text-lg font-medium rounded-full shadow-lg hover:shadow-xl transform hover:-translate-y-1 transition-all duration-300 overflow-hidden"
          >
            <span className="relative z-10 flex items-center gap-2">
              开始咨询
              <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </span>
            <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-pink-500 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          </button>

          <div className="mt-16 flex justify-center gap-8 text-gray-400 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span>AI智能对话</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
              <span>数字人交互</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></div>
              <span>隐私保护</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex w-full h-screen bg-gray-50 text-gray-800 font-sans animate-fadeIn">
      <div className="flex-1 flex flex-col p-4 bg-gray-100 relative">
        <div className="flex-1 rounded-xl bg-white flex items-center justify-center border border-gray-200 overflow-hidden relative shadow-lg">

          <video
            ref={avatarVideoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-contain"
            style={{ backgroundColor: 'white', minHeight: '200px' }}
          />
          <audio ref={avatarAudioRef} autoPlay />

          {connectionState !== 'connected' && (
            <div className="absolute text-gray-400 flex flex-col items-center gap-4 z-0 pointer-events-none">
              <div className="w-32 h-32 bg-gray-200 rounded-full flex items-center justify-center animate-pulse">
                <span className="text-sm">Avatar</span>
              </div>
              <p className="text-sm">2D/3D数字人渲染区域 (WebRTC/12345)</p>
              <p className="text-xs text-gray-400">连接状态: {connectionState}</p>
            </div>
          )}
        </div>

        <div className="h-20 mt-4 bg-white rounded-xl flex items-center justify-center gap-6 px-6 border border-gray-200 shadow">
          <button
            onClick={handleToggleRecording}
            className={`p-4 rounded-full transition-all duration-300 shadow ${isRecording ? 'bg-red-500 hover:bg-red-600' : 'bg-gray-200 hover:bg-gray-300'}`}
          >
            {isRecording ? <Mic className="w-6 h-6 text-white" /> : <MicOff className="w-6 h-6 text-gray-600" />}
          </button>

          <button
            onClick={() => setVideoEnabled(!videoEnabled)}
            className={`p-4 rounded-full transition-all duration-300 shadow ${videoEnabled ? 'bg-blue-500 hover:bg-blue-600' : 'bg-gray-200 hover:bg-gray-300'}`}
          >
            {videoEnabled ? <Video className="w-6 h-6 text-white" /> : <VideoOff className="w-6 h-6 text-gray-600" />}
          </button>

          <div className="relative">
            <button
              onClick={() => !isSwitchingAvatar && setShowAvatarSelector(!showAvatarSelector)}
              className={`p-4 rounded-full transition-all duration-300 shadow ${
                isSwitchingAvatar 
                  ? 'bg-orange-500 cursor-wait' 
                  : showAvatarSelector 
                    ? 'bg-purple-500 hover:bg-purple-600' 
                    : 'bg-gray-200 hover:bg-gray-300'
              }`}
              title="切换数字人"
              disabled={isSwitchingAvatar}
            >
              {isSwitchingAvatar ? (
                <Loader2 className="w-6 h-6 text-white animate-spin" />
              ) : (
                <Users className={`w-6 h-6 ${showAvatarSelector ? 'text-white' : 'text-gray-600'}`} />
              )}
            </button>
            
            {showAvatarSelector && !isSwitchingAvatar && (
              <div className="absolute bottom-16 left-1/2 transform -translate-x-1/2 bg-white border border-gray-200 rounded-lg shadow-xl p-2 min-w-[200px] z-50">
                <div className="text-xs text-gray-500 px-2 py-1 border-b border-gray-100 mb-1">选择数字人</div>
                {avatars.map((avatar) => (
                  <button
                    key={avatar.id}
                    onClick={() => handleSwitchAvatar(avatar.id)}
                    className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                      currentAvatar === avatar.id 
                        ? 'bg-purple-500 text-white' 
                        : 'hover:bg-gray-100 text-gray-700'
                    }`}
                  >
                    <div className="font-medium flex items-center justify-between">
                      <span>{avatar.name}</span>
                      {currentAvatar === avatar.id && (
                        <span className="text-xs bg-purple-300 px-1.5 py-0.5 rounded text-purple-800">当前</span>
                      )}
                    </div>
                    {avatar.frame_count && (
                      <div className="text-xs text-gray-400">{avatar.frame_count} 帧</div>
                    )}
                  </button>
                ))}
                {avatars.length === 0 && (
                  <div className="px-3 py-2 text-sm text-gray-400">暂无可用数字人</div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="absolute bottom-28 right-8 w-48 h-36 bg-white rounded-lg overflow-hidden border-2 border-gray-200 shadow-xl">
          <video
            ref={videoRef}
            autoPlay
            muted
            className="w-full h-full object-cover transform scale-x-[-1]"
          />
          {!videoEnabled && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-200">
              <VideoOff className="w-6 h-6 text-gray-400" />
            </div>
          )}
        </div>
      </div>

      <div className="w-96 bg-white border-l border-gray-200 flex flex-col shadow-lg">
        <div className="h-16 border-b border-gray-200 flex items-center px-6 bg-gray-50">
          <MessageSquare className="w-5 h-5 mr-3 text-blue-500" />
          <h2 className="font-semibold text-lg text-gray-800">心理引导对话</h2>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${msg.role === 'user'
                  ? 'bg-blue-500 text-white rounded-br-none'
                  : 'bg-white text-gray-800 rounded-bl-none border border-gray-200'
                }`}>
                {msg.text}
              </div>
            </div>
          ))}
        </div>

        <div className="p-4 border-t border-gray-200 bg-white">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={isAITyping ? aiTypingText : inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendText()}
              placeholder={isAITyping ? 'AI正在输入...' : '输入消息...'}
              disabled={isAITyping}
              className="flex-1 bg-gray-100 border border-gray-200 rounded-full px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent disabled:bg-gray-100 disabled:text-gray-400"
            />
            <button
              onClick={() => handleSendText()}
              disabled={isAITyping || !inputText.trim()}
              className="p-2 bg-blue-500 hover:bg-blue-600 rounded-full transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed shadow"
            >
              <Send className="w-5 h-5 text-white" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
