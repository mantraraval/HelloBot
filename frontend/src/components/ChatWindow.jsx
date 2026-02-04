import React, { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";

const ChatWindow = ({ messages, onSend, isTyping }) => {
  const [draft, setDraft] = useState("");
  const scrollRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text) return;
    onSend(text);
    setDraft("");
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  return (
    <section className="chat-window">
      <div className="chat-messages" ref={scrollRef}>
        {messages.map((msg, idx) => (
          <MessageBubble key={idx} role={msg.role} content={msg.content} />
        ))}
        {isTyping && <TypingIndicator />}
      </div>
      <form className="chat-input-row" onSubmit={handleSubmit}>
        <input
          className="chat-input"
          type="text"
          placeholder="Ask HelloBot about your order, delivery time, or refunds..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button className="chat-send-btn" type="submit">
          Send
        </button>
      </form>
    </section>
  );
};

export default ChatWindow;

