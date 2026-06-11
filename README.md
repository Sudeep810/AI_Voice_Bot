# 🤖 AI Voice Bot

An AI-powered Voice Bot that converts speech to text, understands user queries, retrieves the most relevant answers from an FAQ knowledge base using semantic search, and responds in both text and voice.

---

## 📌 Overview

AI Voice Bot is a  application that enables users to interact with an FAQ knowledge base using either voice or text. The system uses Sentence Transformers for semantic search, allowing it to understand the meaning of questions rather than relying on exact keyword matches.

The bot can answer employee, customer support, or knowledge-base related queries and provide spoken responses using Text-to-Speech (gTTS).

---

## ✨ Features

* 🎤 Voice Input using browser speech recognition
* 💬 Text-based query interface
* 🔊 Text-to-Speech responses using gTTS
* 🧠 Semantic search with Sentence Transformers
* 📋 FAQ management interface
* 🔐 Admin login system
* 📊 Query logging and analytics
* ⚡ Fast response retrieval from knowledge base

---

## 🏗️ Architecture

User (Voice/Text)
↓
Flask Backend
↓
Sentence Transformer Embeddings
↓
FAQ Knowledge Base
↓
Best Match Retrieval
↓
Text + Voice Response

---

## 📁 Project Structure

```text
AI_Voice_Bot/
│
├── app.py
├── faq.txt
├── requirements.txt
├── README.md
│
├── templates/
│   ├── index.html
│   ├── admin.html
│   └── manage_faq.html
│
├── static/
│   ├── style.css
│   └── audio/
│
└── .gitignore
```

## 🔧 Tech Stack

### Backend

* Python
* Flask

### AI / NLP

* Sentence Transformers
* all-MiniLM-L6-v2

### Voice Processing

* gTTS
* Browser Speech Recognition API

### Frontend

* HTML
* CSS
* JavaScript

---

## 🚀 Installation

### Clone Repository

```bash
git clone https://github.com/Sudeep810/AI_Voice_Bot.git
cd AI_Voice_Bot
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
python app.py
```

### Open Browser

```text
http://127.0.0.1:5000
```

---

## 📊 Key Functionalities

### User Features

* Ask questions using voice or text
* Receive text responses
* Receive audio responses
* Fast semantic search-based retrieval

### Admin Features

* View analytics dashboard
* Manage FAQs
* Monitor user queries
* Update knowledge base

---

## 👨‍💻 Author

Sudeep

GitHub: https://github.com/Sudeep810

---

## ⭐ Project Highlights

* Semantic FAQ Retrieval
* Voice-Based Interaction
* Flask Web Application
* Admin Dashboard
* Real-Time Speech Processing

---

## 📄 License

This project is intended for educational and learning purposes.
