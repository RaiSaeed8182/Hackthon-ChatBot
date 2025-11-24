# 🚀 HOW TO RUN YOUR CHATBOTS

## Step 1: Open PowerShell
Press `Windows Key + R`, type `powershell`, and press Enter.

---

## Step 2: Navigate to Your Project
```powershell
cd "C:\Users\Prime Laptops\Desktop\Alzhemers"
```

---

## Step 3: Install Dependencies (First Time Only)
```powershell
pip install -r requirements.txt
```
⏱️ This may take 5-10 minutes as it installs all libraries.

---

## Step 4: Choose Which Chatbot to Run

### **Option A: Alzheimer's Support Chatbot** 🧠
```powershell
streamlit run Chatbot.py
```
**Features:**
- Chat with AI about Alzheimer's
- Chat history memory
- CSV-based knowledge base
- Uses Groq LLM

---

### **Option B: Hospital Management Chatbot** 🏥
```powershell
streamlit run chatbot_mysqlagent.py
```
**Features:**
- Query hospital database (MySQL)
- Voice input (Whisper STT)
- Voice output (Text-to-Speech)
- SQL Agent for complex queries
- 20+ database tables

---

## Step 5: Access Your Chatbot
After running either command, your browser will automatically open:
```
http://localhost:8501
```

If it doesn't, manually open this URL in your browser.

---

## 🎤 Using Voice Features (Hospital Bot)
1. Click **"🎙️ START RECORDING"**
2. Speak your question (e.g., "Show me all patients")
3. Click **"⏹️ STOP RECORDING"**
4. Your speech will be converted to text via Whisper AI
5. The bot will respond in text AND voice (TTS)

---

## ⚠️ Common Issues & Solutions

### Issue: `ModuleNotFoundError: No module named 'streamlit'`
**Solution:** Run step 3 again:
```powershell
pip install -r requirements.txt
```

### Issue: `GROQ_API_KEY not found in .env file`
**Solution:** 
1. Open `.env` file with Notepad
2. Make sure `GROQ_API_KEY` has your actual key
3. Save and restart

### Issue: `OPENAI_API_KEY not found` (Hospital Bot)
**Solution:**
1. Edit `.env` file
2. Add your OpenAI API key (get from https://platform.openai.com/api-keys)
3. Save and restart

### Issue: `MySQL Connection Error`
**Solution:**
1. Make sure MySQL is running on your machine
2. Verify credentials in `.env` file match your MySQL setup
3. Check if database `HospitalManagementSystem` exists

---

## 🛑 To Stop the Chatbot
Press `Ctrl + C` in PowerShell

---

## 📝 Quick Reference Commands

| Command | What It Does |
|---------|-------------|
| `streamlit run Chatbot.py` | Run Alzheimer's Bot |
| `streamlit run chatbot_mysqlagent.py` | Run Hospital Bot |
| `pip install -r requirements.txt` | Install all dependencies |
| `Ctrl + C` | Stop the bot |
| `pip list` | Check installed packages |

---

## 💡 Pro Tips

✅ **Keep PowerShell window open** while using the chatbot
✅ **Check `.env` file** if you get API key errors
✅ **Use `python -m streamlit run Chatbot.py`** if basic command doesn't work
✅ **Port 8501 must be free** (no other app using it)

---

## 🎯 First Time Setup Checklist

- [ ] 1. Installed Python (from python.org)
- [ ] 2. Navigated to project folder in PowerShell
- [ ] 3. Ran `pip install -r requirements.txt`
- [ ] 4. Updated `.env` with your API keys
- [ ] 5. Ran `streamlit run Chatbot.py` or `streamlit run chatbot_mysqlagent.py`
- [ ] 6. Browser opened to http://localhost:8501

**Ready to chat? Let's go!** 🚀
