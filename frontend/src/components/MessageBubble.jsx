import React from "react";

const MessageBubble = ({ role, content }) => {
  const isUser = role === "user";
  return (
    <div className={`message-row ${isUser ? "from-user" : "from-bot"}`}>
      <div className="message-avatar">
        {isUser ? "You" : "HB"}
      </div>
      <div className="message-bubble">
        <div className="message-content">{content}</div>
      </div>
    </div>
  );
};

export default MessageBubble;

