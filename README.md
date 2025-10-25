# Orchestrated Generative AI Support Agent
> A portfolio project demonstrating an advanced, secure, and multi-turn conversational AI. This agent leverages a Generative AI reasoning engine to transcend the limitations of traditional deterministic chatbots.

**Author:** [Mnatra Raval]
**LinkedIn:** [Your LinkedIn URL]

---

## 1. The Core Problem
The current landscape of customer support automation is saturated with deterministic chatbots, which function as rigid **Finite-State Machines (FSMs)**. These systems are fundamentally brittle: they fail at query ambiguity and cannot maintain conversational context.

More critically, they are incapable of **“slot-filling”**—the process of identifying and acquiring missing pieces of information. A user asking “What is my order status?” is often met with failure because the bot cannot dynamically ask the crucial follow-up: “What is your order ID?” This rigid interaction is the primary source of user friction and inefficiency.

## 2. The Architectural Solution
This project presents a paradigm shift from a simple "chatbot" to an **intelligent, context-aware agent**.

It operates on a sophisticated **orchestrated reasoning model**. The Anthropic (Claude AI) LLM acts as the central **reasoning engine**, while a secure Python backend acts as the **executor and data provider**. This decoupled architecture allows the agent to:
1.  Understand complex, multi-step user intent.
2.  Dynamically identify missing information ("slots").
3.  Query the user to fill those slots.
4.  Maintain conversational context for follow-up interactions.

This architecture is powered by a dual-database model to provide comprehensive, accurate responses:

* **The Live Transactional Layer (Relational Database):** A secure database (e.g., PostgreSQL) containing customer-specific, real-time data (order status, delivery info).
* **The Curated Knowledge Layer (MongoDB):** A NoSQL database containing the bot’s predefined knowledge base (company policies, shipping times, product FAQs).

## 3. Key Features
* 🧠 **Multi-Turn Conversational Reasoning:** Uses Anthropic Claude AI to understand multi-step dialogues, maintain conversational context, and generate coherent responses.
* 🎯 **Intelligent Slot-Filling:** Dynamically identifies missing information (e.g., `order_id`) and generates natural language prompts to acquire it.
* 🔐 **Secure, Orchestrated Data Retrieval:** The LLM **never** accesses databases directly. The Python service retrieves the necessary data, and the LLM frames the final answer—ensuring full data security and preventing data leakage.
* ⚙️ **Dual-Source Data Synthesis:** Seamlessly handles queries like “What is my order status?” (from the Relational DB) and “How long does shipping take?” (from MongoDB) within the same conversation.
* 🎨 **Modern, Responsive UI:** A sleek React.js interface built for a fluid user experience.

## 4. Technology & Architecture Justification
The stack was architected for a decoupled, microservice-oriented deployment, ensuring scalability, maintainability, and a clean separation of concerns.

#### 4.1 Programming & Scripting
* **Python:** Powers the AI microservice, orchestrating multi-step LLM conversations, executing database queries, and managing conversational states.
* **JavaScript (ES6+) / Node.js:** The Node.js runtime offers asynchronous, non-blocking I/O, ideal for handling concurrent chat requests in the API gateway.

#### 4.2 Application Layer
* **React.js:** Component-based library used to build a fast, stateful, and dynamic Single-Page Application (SPA).
* **Express.js:** Lightweight Node.js framework that manages routing, session handling, and API endpoints.
* **Node–Python Communication:** The Node.js API gateway communicates with the Python AI microservice via **REST APIs**, forwarding user messages and receiving structured responses. This design ensures modularity and decoupling.

#### 4.3 AI & Machine Learning
* **LLM APIs (Anthropic Claude AI):** Acts as the core reasoning engine. It *only* receives text and data snippets and *returns* text, ensuring complete separation of reasoning and data retrieval.
* **Conversational AI Design:** Demonstrates stateful, multi-turn reasoning with contextual slot-filling.

#### 4.4 Databases
* **Relational Database :** The system of record for all structured company data (customer profiles, order histories). Its ACID-compliant nature is essential for transactional integrity.
* **MongoDB:** High-throughput NoSQL database for unstructured and semi-structured knowledge (FAQs, policies, conversation logs).

## 5. Request Lifecycle: A User Scenario
This workflow demonstrates the agent's full capability, from ambiguity to resolution.

1.  **Initial Query**
    * **User:** “What is my order status?”
    * **System:** React.js client sends this to the Node.js API gateway.

2.  **Intent & Slot Analysis (LLM Pass 1)**
    * **System:** Node.js forwards the query to the Python AI service.
    * **Python Service:** Invokes Anthropic LLM to analyze intent.
    * **LLM Output:** `Intent = get_order_status`, `Missing Slot = order_id`

3.  **Dynamic Slot-Filling**
    * **Python → LLM:** “Generate a prompt to ask the user for order ID.”
    * **LLM → User:** “I can help with that. Could you please share your order ID?”

4.  **Data Retrieval (Live Transactional DB)**
    * **User:** “id-857591726814891”
    * **Python Service (Orchestrator):** Queries PostgreSQL:
        ```sql
        SELECT status FROM orders WHERE order_id = 'id-857591726814891';
        ```
    * **DB Response:** `{ "status": "Packed" }`

5.  **Generative Framing (LLM Pass 2)**
    * **Python → LLM:** “Context: User asked for order status. Data: Order status is ‘Packed’. Frame a response.”
    * **LLM → User:** “Thank you. Your order (id-857591726814891) is packed and ready to be dispatched.”

6.  **Contextual Follow-Up (Knowledge DB)**
    * **User:** “How much time will it take?”
    * **Python Service:** LLM interprets context (knows "it" means the "Packed" order), then queries MongoDB:
        ```json
        db.policies.find({ "status": "Packed" });
        ```
    * **DB Response:** `{ "delivery_estimate": "3 working days" }`

7.  **Final Answer (LLM Pass 3)**
    * **Python → LLM:** “Context: User asked for delivery time for their 'Packed' order. Data: Delivery estimate is '3 working days'. Frame a response.”
    * **LLM → User:** “It usually takes about 3 working days to be delivered from this stage.”

## 6. Future Enhancements
This project provides a robust foundation for several advanced features:
* **Long-Term Conversational Memory:** Implementing a vector database (e.g., Pinecone, ChromaDB) to store conversation embeddings, allowing the agent to recall context from past interactions.
* **Proactive Agentic Behavior:** Granting the agent the ability to *initiate* actions, such as automatically flagging a late order for human review or offering a discount after a negative sentiment is detected.
* **Multi-Modal Input:** Expanding the interface to accept image uploads (e.g., a photo of a damaged product) for analysis.

## 7. Project Demo
![Light Mode](./LightMode.png)
![Dark Mode](./DarkMode.png)
![Conversation Demo 1](./Conversation1.png)
![Conversation Demo 2](./Conversation2.png)
![Light Mode](./LightMode.png)


## 8. License
This project is distributed under the MIT License.
