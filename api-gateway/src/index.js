const express = require("express");
const cors = require("cors");
const morgan = require("morgan");
const axios = require("axios");
require("dotenv").config();

const app = express();
const PORT = process.env.PORT || 4000;
const PYTHON_SERVICE_URL =
  process.env.PYTHON_SERVICE_URL || "http://python-service:8000";

// Basic JSON parsing and CORS
app.use(cors());
app.use(express.json());

// Structured logging via morgan
app.use(
  morgan(':date[iso] | :method :url :status :res[content-length] - :response-time ms')
);

// Mock authentication middleware
app.use((req, res, next) => {
  // In a real system this would validate JWTs or session cookies.
  // Here we just attach a mock user identity for downstream logging.
  req.user = {
    id: "user-123",
    role: "test-user"
  };
  next();
});

// Simple logging middleware with user context
app.use((req, res, next) => {
  const userId = req.user?.id || "anonymous";
  console.log(
    JSON.stringify({
      level: "info",
      msg: "Incoming API request",
      path: req.path,
      method: req.method,
      userId
    })
  );
  next();
});

// Health check
app.get("/healthz", (req, res) => {
  res.json({ status: "ok", service: "api-gateway" });
});

// Proxy chat requests to Python orchestration service
app.post("/api/chat", async (req, res, next) => {
  try {
    const { conversation_id, user_message } = req.body || {};

    if (!conversation_id || !user_message) {
      return res.status(400).json({
        error: "conversation_id and user_message are required"
      });
    }

    const response = await axios.post(`${PYTHON_SERVICE_URL}/chat`, {
      conversation_id,
      user_message
    });

    res.json(response.data);
  } catch (err) {
    next(err);
  }
});

// Proxy conversation state inspection
app.get("/api/conversations/:id", async (req, res, next) => {
  try {
    const conversationId = req.params.id;
    const response = await axios.get(
      `${PYTHON_SERVICE_URL}/conversations/${conversationId}`
    );
    res.json(response.data);
  } catch (err) {
    next(err);
  }
});

// Centralized error handler
app.use((err, req, res, next) => {
  console.error(
    JSON.stringify({
      level: "error",
      msg: "Unhandled error in API gateway",
      error: err.message,
      stack: err.stack
    })
  );

  if (err.response) {
    // Error came from downstream Python service
    return res
      .status(err.response.status || 500)
      .json(err.response.data || { error: "Upstream service error" });
  }

  res.status(500).json({ error: "Internal server error" });
});

app.listen(PORT, () => {
  console.log(`HelloBot API gateway listening on port ${PORT}`);
});

