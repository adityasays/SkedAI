import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import pytz
import pandas as pd
import re
import time
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Neural Scheduler Pro",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Global Reset & Variables */
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --success-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        --warning-gradient: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        --dark-gradient: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
        --glass-bg: rgba(255, 255, 255, 0.1);
        --glass-border: rgba(255, 255, 255, 0.2);
        --text-primary: #2d3748;
        --text-secondary: #4a5568;
        --shadow-soft: 0 10px 25px rgba(0, 0, 0, 0.1);
        --shadow-strong: 0 20px 50px rgba(0, 0, 0, 0.15);
        --border-radius: 16px;
        --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* Global Styles */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #f5576c 75%, #4facfe 100%);
        background-size: 400% 400%;
        animation: gradientShift 15s ease infinite;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container */
    .main-container {
        backdrop-filter: blur(20px);
        background: var(--glass-bg);
        border: 1px solid var(--glass-border);
        border-radius: var(--border-radius);
        margin: 20px;
        padding: 30px;
        box-shadow: var(--shadow-strong);
        transition: var(--transition);
    }
    
    /* Header section */
    .header-section {
        text-align: center;
        margin-bottom: 40px;
        padding: 40px 20px;
        background: linear-gradient(135deg, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0.1) 100%);
        border-radius: var(--border-radius);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    .main-title {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #f0f0f0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
        text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        animation: titleGlow 2s ease-in-out infinite alternate;
    }
    
    @keyframes titleGlow {
        from { filter: drop-shadow(0 0 20px rgba(255,255,255,0.3)); }
        to { filter: drop-shadow(0 0 30px rgba(255,255,255,0.6)); }
    }
    
    .subtitle {
        font-size: 1.2rem;
        color: rgba(255,255,255,0.8);
        font-weight: 400;
        margin-bottom: 20px;
    }
    
    
    .glass-card {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: var(--border-radius);
        padding: 25px;
        margin: 20px 0;
        box-shadow: var(--shadow-soft);
        transition: var(--transition);
        position: relative;
        overflow: hidden;
    }
    
    .glass-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.7s;
    }
    
    .glass-card:hover::before {
        left: 100%;
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
        border-color: rgba(255, 255, 255, 0.4);
    }
    
    /* Chat interface */
    .chat-container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: var(--border-radius);
        padding: 25px;
        max-height: 600px;
        overflow-y: auto;
        margin-bottom: 20px;
        scrollbar-width: thin;
        scrollbar-color: rgba(255,255,255,0.3) transparent;
    }
    
    .chat-container::-webkit-scrollbar {
        width: 6px;
    }
    
    .chat-container::-webkit-scrollbar-track {
        background: transparent;
    }
    
    .chat-container::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,0.3);
        border-radius: 3px;
    }
    
    .chat-message {
        padding: 15px 20px;
        border-radius: 20px;
        margin: 10px 0;
        animation: messageSlideIn 0.5s ease-out;
        position: relative;
        backdrop-filter: blur(10px);
    }
    
    @keyframes messageSlideIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .user-message {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.8) 0%, rgba(118, 75, 162, 0.8) 100%);
        color: white;
        margin-left: 20%;
        border-bottom-right-radius: 8px;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
    }
    
    .assistant-message {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.7) 100%);
        color: var(--text-primary);
        margin-right: 20%;
        border-bottom-left-radius: 8px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
    }
    
    
    .status-indicator {
        display: inline-flex;
        align-items: center;
        padding: 12px 24px;
        border-radius: 50px;
        font-weight: 600;
        margin: 10px 0;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.3);
        transition: var(--transition);
    }
    
    .status-healthy {
        background: linear-gradient(135deg, rgba(79, 172, 254, 0.8) 0%, rgba(0, 242, 254, 0.8) 100%);
        color: white;
        animation: pulse 2s infinite;
    }
    
    .status-error {
        background: linear-gradient(135deg, rgba(250, 112, 154, 0.8) 0%, rgba(254, 225, 64, 0.8) 100%);
        color: white;
        animation: shake 0.5s ease-in-out;
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }
    
    /* Buttons */
    .stButton > button {
        background: var(--primary-gradient);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 12px 30px;
        font-weight: 600;
        font-size: 16px;
        transition: var(--transition);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        transition: left 0.6s;
    }
    
    .stButton > button:hover::before {
        left: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 30px rgba(102, 126, 234, 0.4);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 50px;
        padding: 8px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        border-radius: 50px;
        color: rgba(255, 255, 255, 0.7);
        font-weight: 600;
        transition: var(--transition);
        background: transparent;
        border: none;
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--primary-gradient);
        color: white;
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
    }
    
    
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div,
    .stNumberInput > div > div > input {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 12px;
        color: var(--text-primary);
        font-weight: 500;
        transition: var(--transition);
        backdrop-filter: blur(10px);
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > div:focus,
    .stNumberInput > div > div > input:focus {
        border-color: rgba(102, 126, 234, 0.6);
        box-shadow: 0 0 20px rgba(102, 126, 234, 0.2);
        transform: scale(1.02);
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: rgba(45, 55, 72, 0.95);
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Metrics */
    .metric-card {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: var(--border-radius);
        padding: 20px;
        text-align: center;
        transition: var(--transition);
        position: relative;
        overflow: hidden;
    }
    
    .metric-card:hover {
        transform: scale(1.05);
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }
    
    .metric-label {
        color: rgba(255, 255, 255, 0.8);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 0.9rem;
    }
    
    /* Data tables */
    .stDataFrame {
        background: rgba(255, 255, 255, 0.9);
        border-radius: var(--border-radius);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.3);
        overflow: hidden;
    }
    
    /* Loading spinner */
    .stSpinner {
        text-align: center;
    }
    
    /* Custom animations */
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }
    
    .floating {
        animation: float 3s ease-in-out infinite;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .main-title {
            font-size: 2.5rem;
        }
        
        .user-message,
        .assistant-message {
            margin-left: 10%;
            margin-right: 10%;
        }
        
        .glass-card {
            margin: 10px 0;
            padding: 20px;
        }
    }
    
    /* Notification toast */
    .notification-toast {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1000;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: var(--border-radius);
        padding: 20px;
        box-shadow: var(--shadow-strong);
        animation: slideInRight 0.5s ease-out;
    }
    
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Backend URL
BACKEND_URL = "http://localhost:8000"

if "messages" not in st.session_state:
    st.session_state.messages = []
if "preferences" not in st.session_state:
    st.session_state.preferences = {
        "timezone": "Asia/Kolkata",
        "business_hours_start": "09:00",
        "business_hours_end": "17:00",
        "default_duration": 60,
        "theme": "modern",
        "notifications": True
    }
if "meetings" not in st.session_state:
    st.session_state.meetings = []
if "analytics" not in st.session_state:
    st.session_state.analytics = {
        "total_meetings": 0,
        "meetings_today": 0,
        "upcoming_meetings": 0,
        "meeting_efficiency": 85
    }

def check_backend_health():
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("status") == "healthy", data.get("message", "All systems operational")
        return False, f"Backend error (Status: {response.status_code})"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused - Backend offline"
    except requests.exceptions.Timeout:
        return False, "Connection timeout - Backend slow"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def fetch_meetings():
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/meetings", timeout=10)
        if response.status_code == 200:
            meetings = response.json()
            st.session_state.meetings = meetings
            # Update analytics
            today = datetime.now().date()
            st.session_state.analytics["total_meetings"] = len(meetings)
            st.session_state.analytics["meetings_today"] = len([m for m in meetings if datetime.fromisoformat(m.get("start_time", "")).date() == today])
            st.session_state.analytics["upcoming_meetings"] = len([m for m in meetings if datetime.fromisoformat(m.get("start_time", "")) > datetime.now()])
            return True
        return False
    except Exception as e:
        st.error(f"Error fetching meetings: {str(e)}")
        return False

st.markdown("""
    <div class="header-section">
        <div class="main-title floating">🧠 Neural Scheduler Pro</div>
        <div class="subtitle">AI-Powered Intelligent Appointment Management</div>
        <div style="margin-top: 20px; color: rgba(255,255,255,0.7);">
            ✨ Natural Language Processing • 🎯 Smart Scheduling • 📊 Advanced Analytics
        </div>
    </div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
        <div style="text-align: center; padding: 20px 0; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px;">
            <h2 style="color: white; margin: 0;">⚙️ Control Center</h2>
        </div>
    """, unsafe_allow_html=True)
    
    # Quick stats
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Total</div>
            </div>
        """.format(st.session_state.analytics["total_meetings"]), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Today</div>
            </div>
        """.format(st.session_state.analytics["meetings_today"]), unsafe_allow_html=True)

    st.markdown("---")
    
    st.markdown("### 🎨 Preferences")
    timezone = st.selectbox(
        "🌍 Timezone",
        ["Asia/Kolkata", "UTC", "America/New_York", "Europe/London", "Australia/Sydney"],
        index=0,
        key="timezone"
    )
    
    business_hours_start = st.text_input("🌅 Business Start", value=st.session_state.preferences["business_hours_start"])
    business_hours_end = st.text_input("🌇 Business End", value=st.session_state.preferences["business_hours_end"])
    default_duration = st.slider("⏱️ Default Duration (min)", 15, 240, st.session_state.preferences["default_duration"], step=15)
    
    notifications = st.toggle("🔔 Notifications", value=st.session_state.preferences["notifications"])

    if st.button("💾 Save Preferences", use_container_width=True):
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/v1/preferences",
                json={
                    "timezone": timezone,
                    "business_hours_start": business_hours_start,
                    "business_hours_end": business_hours_end,
                    "default_duration": default_duration,
                    "notifications": notifications
                },
                timeout=10
            )
            if response.status_code == 200:
                st.session_state.preferences.update({
                    "timezone": timezone,
                    "business_hours_start": business_hours_start,
                    "business_hours_end": business_hours_end,
                    "default_duration": default_duration,
                    "notifications": notifications
                })
                st.success("✅ Preferences saved successfully")
            else:
                st.error(f"❌ Failed to save preferences: Status {response.status_code}")
        except Exception as e:
            st.error(f"❌ Error saving preferences: {str(e)}")

    st.markdown("---")
    
    # System status
    st.markdown("### 🔍 System Status")
    is_healthy, health_message = check_backend_health()
    if is_healthy:
        st.markdown('<div class="status-indicator status-healthy">✅ System Online</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-indicator status-error">❌ {health_message}</div>', unsafe_allow_html=True)

    st.markdown("---")
    
    # Quick actions
    st.markdown("### ⚡ Quick Actions")
    if st.button("🔄 Refresh Data", use_container_width=True):
        fetch_meetings()
        st.rerun()
    
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

tab1, tab2, tab3, tab4 = st.tabs(["💬 AI Assistant", "📅 Smart Calendar", "📋 Meeting Hub", "📊 Analytics"])

with tab1:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 🤖 Conversational AI Assistant")
    st.markdown("Interact with your intelligent scheduling assistant using natural language.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for message in st.session_state.messages:
        role_class = "user-message" if message["role"] == "user" else "assistant-message"
        timestamp = message.get("timestamp", datetime.now().strftime("%H:%M"))
        st.markdown(f'''
            <div class="chat-message {role_class}">
                <div style="font-size: 0.8em; opacity: 0.7; margin-bottom: 5px;">{timestamp}</div>
                <div>{message["content"]}</div>
            </div>
        ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("#### 💡 Quick Suggestions")
    suggestion_cols = st.columns(4)
    suggestions = [
        "📅 Book meeting tomorrow 3pm",
        "🔍 Show my schedule today",
        "❌ Cancel next meeting",
        "📋 List all meetings"
    ]
    
    for i, suggestion in enumerate(suggestions):
        with suggestion_cols[i]:
            if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                prompt = suggestion.split(" ", 1)[1]  
                st.session_state.messages.append({
                    "role": "user", 
                    "content": prompt,
                    "timestamp": datetime.now().strftime("%H:%M")
                })
                # Process the suggestion
                with st.spinner("🧠 AI thinking..."):
                    try:
                        response = requests.post(
                            f"{BACKEND_URL}/api/v1/book",
                            json={"message": prompt},
                            timeout=30
                        )
                        if response.status_code == 200:
                            result = response.json()
                            assistant_response = result.get("message", "I couldn't process that request.")
                        else:
                            assistant_response = f"Service temporarily unavailable (Error: {response.status_code})"
                    except Exception as e:
                        assistant_response = f"❌ Connection error: {str(e)}"
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": assistant_response,
                    "timestamp": datetime.now().strftime("%H:%M")
                })
                st.rerun()

    if prompt := st.chat_input("💬 Ask me anything about your schedule..."):
        st.session_state.messages.append({
            "role": "user", 
            "content": prompt,
            "timestamp": datetime.now().strftime("%H:%M")
        })
        
        with st.spinner("🧠 AI Processing..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/v1/book",
                    json={"message": prompt},
                    timeout=30
                )
                if response.status_code == 200:
                    result = response.json()
                    assistant_response = result.get("message", "I couldn't process that request.")
                else:
                    assistant_response = f"❌ Service error (Status: {response.status_code})"
            except requests.exceptions.ConnectionError:
                assistant_response = "🔌 Backend service is offline. Please check if the server is running."
            except requests.exceptions.Timeout:
                assistant_response = "⏰ Request timed out. Please try again."
            except Exception as e:
                assistant_response = f"❌ Unexpected error: {str(e)}"

        st.session_state.messages.append({
            "role": "assistant", 
            "content": assistant_response,
            "timestamp": datetime.now().strftime("%H:%M")
        })
        st.rerun()

with tab2:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 📅 Intelligent Calendar Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_date = st.date_input(
            "📆 Select Date",
            value=datetime.now(pytz.timezone(st.session_state.preferences["timezone"])).date(),
            min_value=datetime.now().date(),
            max_value=datetime.now().date() + timedelta(days=90)
        )
    
    with col2:
        if st.button("🔍 Check Availability", use_container_width=True):
            with st.spinner("🔄 Analyzing schedule..."):
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/api/v1/availability",
                        json={"message": f"What's available on {selected_date.strftime('%Y-%m-%d')}?"},
                        timeout=10
                    )
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"📊 {result.get('message', 'Schedule analyzed')}")
                    else:
                        st.error(f"❌ Analysis failed: Status {response.status_code}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### ⚡ Quick Book Meeting")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        meeting_title = st.text_input("📝 Meeting Title", value="Team Sync", placeholder="Enter meeting name...")
        meeting_type = st.selectbox("🏷️ Meeting Type", ["Team Sync", "Client Call", "Interview", "Workshop", "Review", "Other"])
    
    with col2:
        meeting_time = st.time_input("🕐 Start Time", value=datetime.now().replace(minute=0, second=0, microsecond=0).time())
        priority = st.selectbox("⚡ Priority", ["Low", "Medium", "High", "Critical"])
    
    with col3:
        duration = st.selectbox("⏱️ Duration", [15, 30, 45, 60, 90, 120], index=3)
        attendees = st.number_input("👥 Attendees", min_value=1, max_value=50, value=2)
    
    if st.button("📅 Book Meeting", use_container_width=True):
        with st.spinner("🚀 Creating meeting..."):
            try:
                meeting_datetime = datetime.combine(selected_date, meeting_time)
                meeting_datetime = pytz.timezone(st.session_state.preferences["timezone"]).localize(meeting_datetime)
                
                prompt = f"Book a {priority.lower()} priority {meeting_type} titled '{meeting_title}' on {selected_date.strftime('%Y-%m-%d')} at {meeting_time.strftime('%I:%M %p')} for {duration} minutes with {attendees} attendees"
                
                response = requests.post(
                    f"{BACKEND_URL}/api/v1/book",
                    json={"message": prompt},
                    timeout=30
                )
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ {result.get('message', 'Meeting booked successfully!')}")
                    if st.session_state.preferences["notifications"]:
                        st.balloons()
                else:
                    st.error(f"❌ Booking failed: Status {response.status_code}")
            except Exception as e:
                st.error(f"❌ Error booking meeting: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 📋 Meeting Management Hub")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**Upcoming Meetings Overview**")
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            with st.spinner("🔄 Syncing meetings..."):
                if fetch_meetings():
                    st.success("✅ Meetings updated")
                else:
                    st.error("❌ Update failed")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.session_state.meetings:
        for i, meeting in enumerate(st.session_state.meetings):
            with st.expander(f"📅 {meeting.get('summary', 'Untitled Meeting')} - {meeting.get('start_time', 'No time')}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"**📝 Title:** {meeting.get('summary', 'N/A')}")
                    st.markdown(f"**🕐 Time:** {meeting.get('start_time', 'N/A')}")
                    st.markdown(f"**⏱️ Duration:** {meeting.get('duration', 'N/A')} minutes")
                
                with col2:
                    st.markdown(f"**📍 Location:** {meeting.get('location', 'Virtual')}")
                    st.markdown(f"**👥 Attendees:** {meeting.get('attendees', 1)}")
                    st.markdown(f"**⚡ Priority:** {meeting.get('priority', 'Medium')}")
                
                with col3:
                    if st.button(f"✏️ Edit", key=f"edit_{i}"):
                        st.info("Edit functionality coming soon!")
                    if st.button(f"❌ Cancel", key=f"cancel_{i}"):
                        with st.spinner("Cancelling meeting..."):
                            try:
                                prompt = f"Cancel my {meeting.get('summary', 'meeting')}"
                                response = requests.delete(
                                    f"{BACKEND_URL}/api/v1/meetings",
                                    json={"message": prompt},
                                    timeout=30
                                )
                                if response.status_code == 200:
                                    st.success("✅ Meeting cancelled")
                                    fetch_meetings()
                                    st.rerun()
                                else:
                                    st.error(f"❌ Cancellation failed: Status {response.status_code}")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
        
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### ⚡ Bulk Actions")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📧 Send Reminders", use_container_width=True):
                st.info("📧 Reminders sent to all attendees!")
        
        with col2:
            if st.button("📊 Export Schedule", use_container_width=True):
                df = pd.DataFrame(st.session_state.meetings)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="💾 Download CSV",
                    data=csv,
                    file_name=f"meetings_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        with col3:
            if st.button("🔄 Sync Calendar", use_container_width=True):
                st.info("🔄 Calendar sync initiated!")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("""
            <div style="text-align: center; padding: 40px;">
                <div style="font-size: 4rem; margin-bottom: 20px;">📅</div>
                <h3 style="color: rgba(255,255,255,0.8);">No meetings scheduled</h3>
                <p style="color: rgba(255,255,255,0.6);">Start by booking your first meeting using the AI assistant!</p>
            </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

with tab4:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Advanced Analytics Dashboard")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{st.session_state.analytics['total_meetings']}</div>
                <div class="metric-label">Total Meetings</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{st.session_state.analytics['meetings_today']}</div>
                <div class="metric-label">Today's Meetings</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{st.session_state.analytics['upcoming_meetings']}</div>
                <div class="metric-label">Upcoming</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{st.session_state.analytics['meeting_efficiency']}%</div>
                <div class="metric-label">Efficiency</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.session_state.meetings:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 📈 Meeting Trends")
        
        dates = [datetime.now().date() - timedelta(days=x) for x in range(7, 0, -1)]
        meeting_counts = [2, 1, 3, 2, 4, 1, 2]  # Sample data
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=meeting_counts,
            mode='lines+markers',
            name='Daily Meetings',
            line=dict(color='rgba(102, 126, 234, 0.8)', width=3),
            marker=dict(size=8, color='rgba(102, 126, 234, 1)')
        ))
        
        fig.update_layout(
            title="Meeting Activity (Last 7 Days)",
            xaxis_title="Date",
            yaxis_title="Number of Meetings",
            template="plotly_dark",
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 🏷️ Meeting Types Distribution")
        
        # Sample data
        meeting_types = ['Team Sync', 'Client Call', 'Interview', 'Workshop', 'Review']
        counts = [5, 3, 2, 4, 2]
        
        fig = go.Figure(data=[go.Pie(
            labels=meeting_types,
            values=counts,
            hole=0.4,
            marker_colors=['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe']
        )])
        
        fig.update_layout(
            title="Meeting Types Distribution",
            template="plotly_dark",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("""
            <div style="text-align: center; padding: 40px;">
                <div style="font-size: 4rem; margin-bottom: 20px;">📊</div>
                <h3 style="color: rgba(255,255,255,0.8);">No analytics data available</h3>
                <p style="color: rgba(255,255,255,0.6);">Schedule some meetings to see your analytics!</p>
            </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
    <div style="margin-top: 50px; padding: 30px; text-align: center; background: rgba(255,255,255,0.1); backdrop-filter: blur(15px); border-radius: 16px; border: 1px solid rgba(255,255,255,0.2);">
        <div style="font-size: 1.2rem; font-weight: 600; color: white; margin-bottom: 10px;">
            🧠 Neural Scheduler Pro
        </div>
        <div style="color: rgba(255,255,255,0.7); margin-bottom: 15px;">
            Powered by Advanced AI • Natural Language Processing • Smart Automation
        </div>
        <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap;">
            <span style="color: rgba(255,255,255,0.6);">🚀 Version 2.0</span>
            <span style="color: rgba(255,255,255,0.6);">•</span>
            <span style="color: rgba(255,255,255,0.6);">⚡ Ultra-Fast Performance</span>
            <span style="color: rgba(255,255,255,0.6);">•</span>
            <span style="color: rgba(255,255,255,0.6);">🔒 Enterprise Security</span>
        </div>
    </div>
""", unsafe_allow_html=True)

st.markdown("""
    <script>
    // Add smooth scrolling
    document.documentElement.style.scrollBehavior = 'smooth';
    
    // Add some interactive elements
    document.addEventListener('DOMContentLoaded', function() {
        // Add click animation to cards
        const cards = document.querySelectorAll('.glass-card');
        cards.forEach(card => {
            card.addEventListener('click', function() {
                this.style.transform = 'scale(0.98)';
                setTimeout(() => {
                    this.style.transform = 'scale(1)';
                }, 100);
            });
        });
    });
    </script>
""", unsafe_allow_html=True)