import streamlit as st
import requests
import json
from typing import Dict, List
import time
from datetime import datetime

# Configure the page
st.set_page_config(
    page_title="Memento Agent Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
API_BASE_URL = "http://localhost:8000"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "default"
if "agent_info" not in st.session_state:
    st.session_state.agent_info = None

def get_agent_info():
    """Fetch agent information from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to connect to API: {e}")
    return None

def get_health_status():
    """Check API health status"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException:
        return {"status": "unhealthy", "agent_loaded": False}

def send_message(message: str, thread_id: str, use_streaming: bool = False):
    """Send message to the agent"""
    if use_streaming:
        return send_streaming_message(message, thread_id)
    else:
        try:
            payload = {
                "message": message,
                "thread_id": thread_id,
                "stream": False
            }
            response = requests.post(f"{API_BASE_URL}/chat", json=payload)
            if response.status_code == 200:
                return response.json()["response"]
            else:
                return f"Error: {response.status_code} - {response.text}"
        except requests.exceptions.RequestException as e:
            return f"Connection error: {e}"

def send_streaming_message(message: str, thread_id: str):
    """Send message with streaming response"""
    try:
        payload = {
            "message": message,
            "thread_id": thread_id
        }
        
        response = requests.post(
            f"{API_BASE_URL}/stream",
            json=payload,
            stream=True,
            headers={"Accept": "text/event-stream"}
        )
        
        if response.status_code == 200:
            full_response = ""
            placeholder = st.empty()
            
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])  # Remove "data: " prefix
                        if data["type"] == "chunk":
                            full_response += data["content"]
                            placeholder.markdown(full_response)
                        elif data["type"] == "end":
                            break
                        elif data["type"] == "error":
                            return f"Streaming error: {data['content']}"
                    except json.JSONDecodeError:
                        continue
            
            return full_response
        else:
            return f"Streaming error: {response.status_code} - {response.text}"
    
    except requests.exceptions.RequestException as e:
        return f"Streaming connection error: {e}"

def reset_conversation(thread_id: str):
    """Reset the conversation thread"""
    try:
        response = requests.post(f"{API_BASE_URL}/reset", params={"thread_id": thread_id})
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def get_tools_info():
    """Get available tools information"""
    try:
        response = requests.get(f"{API_BASE_URL}/tools")
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException:
        return None

# Sidebar
with st.sidebar:
    st.title("🤖 Memento Agent")
    
    # Health status
    health = get_health_status()
    if health["status"] == "healthy" and health["agent_loaded"]:
        st.success("✅ Agent Online")
    else:
        st.error("❌ Agent Offline")
    
    # Thread ID input
    new_thread_id = st.text_input(
        "Thread ID", 
        value=st.session_state.thread_id,
        help="Unique identifier for conversation continuity"
    )
    if new_thread_id != st.session_state.thread_id:
        st.session_state.thread_id = new_thread_id
        st.rerun()
    
    # Streaming option
    use_streaming = st.checkbox("Enable Streaming", value=False)
    
    # Reset conversation
    if st.button("🔄 Reset Conversation"):
        if reset_conversation(st.session_state.thread_id):
            st.session_state.messages = []
            st.success("Conversation reset!")
            st.rerun()
        else:
            st.error("Failed to reset conversation")
    
    # Agent info
    if st.button("🔄 Refresh Agent Info"):
        st.session_state.agent_info = get_agent_info()
    
    if st.session_state.agent_info is None:
        st.session_state.agent_info = get_agent_info()
    
    if st.session_state.agent_info:
        st.subheader("Agent Information")
        agent_info = st.session_state.agent_info.get("agent_info", {})
        st.write(f"**Name:** {agent_info.get('name', 'N/A')}")
        st.write(f"**Model:** {agent_info.get('model', 'N/A')}")
        
        tools = agent_info.get('tools', [])
        if tools:
            st.write(f"**Tools ({len(tools)}):**")
            for tool in tools:
                st.write(f"• {tool}")
    
    # Tools information
    with st.expander("🛠️ Available Tools"):
        tools_info = get_tools_info()
        if tools_info:
            st.write(f"**Total Tools:** {tools_info['count']}")
            for tool in tools_info['tools']:
                st.write(f"**{tool['name']}**")
                st.write(tool['description'])
                st.write("---")
        else:
            st.write("No tools information available")

# Main chat interface
st.title("💬 Chat with Memento Agent")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "timestamp" in message:
            st.caption(f"*{message['timestamp']}*")

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat history
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.messages.append({
        "role": "user", 
        "content": prompt, 
        "timestamp": timestamp
    })
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
        st.caption(f"*{timestamp}*")
    
    # Get bot response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = send_message(prompt, st.session_state.thread_id, use_streaming)
        
        if not use_streaming:
            st.markdown(response)
        
        # Add assistant response to chat history
        response_timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response, 
            "timestamp": response_timestamp
        })
        
        if not use_streaming:
            st.caption(f"*{response_timestamp}*")

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("📊 View Graph Structure"):
        try:
            response = requests.get(f"{API_BASE_URL}/graph")
            if response.status_code == 200:
                graph_data = response.json()
                st.code(graph_data["mermaid_code"], language="text")
                st.info(graph_data["message"])
            else:
                st.error("Failed to fetch graph structure")
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching graph: {e}")

with col2:
    if st.button("📋 Export Chat"):
        chat_export = {
            "thread_id": st.session_state.thread_id,
            "messages": st.session_state.messages,
            "exported_at": datetime.now().isoformat()
        }
        st.download_button(
            label="Download Chat JSON",
            data=json.dumps(chat_export, indent=2),
            file_name=f"memento_chat_{st.session_state.thread_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

with col3:
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Display connection info
st.sidebar.markdown("---")
st.sidebar.markdown(f"**API Endpoint:** {API_BASE_URL}")
st.sidebar.markdown(f"**Current Thread:** {st.session_state.thread_id}")
st.sidebar.markdown(f"**Messages:** {len(st.session_state.messages)}")