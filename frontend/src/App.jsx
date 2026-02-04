import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import ChatWindow from "./components/ChatWindow";
import ContextPanel from "./components/ContextPanel";

const randomConversationId = () =>
  "conv-" + Math.random().toString(36).substring(2, 10);

const App = () => {
  const [conversationId] = useState(randomConversationId);
  const [messages, setMessages] = useState([]);
  const [contextState, setContextState] = useState(null);
  const [isTyping, setIsTyping] = useState(false);

  const latestController = useRef(null);

  const sendMessage = async (text) => {
    if (!text.trim()) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setIsTyping(true);

    if (latestController.current) {
      latestController.current.abort();
    }
    latestController.current = new AbortController();

    try {
      const res = await axios.post(
        "/api/chat",
        {
          conversation_id: conversationId,
          user_message: text
        },
        { signal: latestController.current.signal }
      );

      const { response_text } = res.data;

      // Simulate streaming by gradually revealing the response
      await simulateStreaming(response_text, (partial) => {
        setMessages((prev) => {
          const withoutTempAssistant = prev.filter(
            (m) => m._tempStream !== true
          );
          return [
            ...withoutTempAssistant,
            { role: "assistant", content: partial, _tempStream: true }
          ];
        });
      });

      // Finalize assistant message
      setMessages((prev) => {
        const withoutTempAssistant = prev.filter((m) => m._tempStream !== true);
        return [...withoutTempAssistant, { role: "assistant", content: response_text }];
      });

      await refreshContext();
    } catch (err) {
      console.error("Error sending message", err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, something went wrong while talking to the server."
        }
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const simulateStreaming = async (fullText, onChunk) => {
    const tokens = fullText.split(" ");
    let partial = "";
    for (const token of tokens) {
      partial = partial ? `${partial} ${token}` : token;
      onChunk(partial);
      // Small delay to give a realistic typing effect
      // eslint-disable-next-line no-await-in-loop
      await new Promise((resolve) => setTimeout(resolve, 40));
    }
  };

  const refreshContext = async () => {
    try {
      const res = await axios.get(`/api/conversations/${conversationId}`);
      setContextState(res.data);
    } catch (err) {
      console.error("Error fetching context", err);
    }
  };

  useEffect(() => {
    refreshContext();
  }, []);

  return (
    <div className="app-root">
      <header className="app-header">
        <h1>HelloBot</h1>
        <span className="subtitle">LLM-Orchestrated Conversational AI</span>
      </header>
      <main className="app-main">
        <ChatWindow
          messages={messages}
          onSend={sendMessage}
          isTyping={isTyping}
        />
        <ContextPanel conversationId={conversationId} context={contextState} />
      </main>
    </div>
  );
};

export default App;

