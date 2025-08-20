from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from fastapi.responses import StreamingResponse
import json
import asyncio
from contextlib import asynccontextmanager
import uvicorn

from .agent.graph import agent

# Pydantic models for request/response
class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = "default"
    stream: Optional[bool] = False

class ChatResponse(BaseModel):
    response: str
    thread_id: str

class StreamChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = "default"

class GraphVisualizationResponse(BaseModel):
    mermaid_code: str
    message: str

# Global variable to store agent
app_agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global app_agent
    app_agent = agent
    print("✅ Agent loaded successfully")
    yield
    # Shutdown
    print("🔄 Shutting down...")

app = FastAPI(
    title="Memento Agent API",
    description="FastAPI deployment for the Memento Agent with table search and SQL generation capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Memento Agent API is running!",
        "endpoints": {
            "chat": "/chat - POST request to chat with the agent",
            "stream": "/stream - POST request for streaming chat",
            "graph": "/graph - GET request to view graph structure",
            "health": "/health - GET request for health check"
        },
        "agent_info": {
            "name": app_agent.name if app_agent else "Not loaded",
            "model": app_agent.model if app_agent else "Not loaded",
            "tools": [tool.name for tool in app_agent.tools] if app_agent else []
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent_loaded": app_agent is not None,
        "timestamp": "2025-01-01T00:00:00Z"  # You can use datetime.now() if needed
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the Memento agent
    
    - **message**: The user's message
    - **thread_id**: Optional thread ID for conversation continuity (default: "default")
    - **stream**: Whether to stream response (for this endpoint, always False)
    """
    if not app_agent:
        raise HTTPException(status_code=500, detail="Agent not loaded")
    
    try:
        # Configure the agent with thread_id
        config = {"configurable": {"thread_id": request.thread_id}}
        
        # Get response from agent
        response = app_agent.invoke(request.message, config=config)
        
        return ChatResponse(
            response=response,
            thread_id=request.thread_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.post("/stream")
async def stream_chat(request: StreamChatRequest):
    """
    Stream chat with the Memento agent

    - **message**: The user's message
    - **thread_id**: Optional thread ID for conversation continuity (default: "default")
    """
    if not app_agent:
        raise HTTPException(status_code=500, detail="Agent not loaded")

    async def generate_stream():
        try:
            config = {"configurable": {"thread_id": request.thread_id}}
            
            for chunk in app_agent.stream(request.message, config=config):
                # Format each chunk as SSE (Server-Sent Events)
                data = {
                    "content": chunk,
                    "thread_id": request.thread_id,
                    "type": "chunk"
                }
                yield f"data: {json.dumps(data)}\n\n"
            
            # Send final message
            final_data = {
                "content": "",
                "thread_id": request.thread_id,
                "type": "end"
            }
            yield f"data: {json.dumps(final_data)}\n\n"
            
        except Exception as e:
            error_data = {
                "content": f"Error: {str(e)}",
                "thread_id": request.thread_id,
                "type": "error"
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_stream(), 
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@app.get("/graph", response_model=GraphVisualizationResponse)
async def get_graph():
    """
    Get the agent's graph structure as mermaid code
    """
    if not app_agent:
        raise HTTPException(status_code=500, detail="Agent not loaded")
    
    try:
        graph = app_agent.build_graph()
        mermaid_code = graph.get_graph().draw_mermaid()
        
        return GraphVisualizationResponse(
            mermaid_code=mermaid_code,
            message="Copy the mermaid_code to https://mermaid.live to visualize"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating graph: {str(e)}")

@app.get("/tools")
async def get_tools():
    """Get information about available tools"""
    if not app_agent:
        raise HTTPException(status_code=500, detail="Agent not loaded")
    
    tools_info = []
    for tool in app_agent.tools:
        tool_info = {
            "name": tool.name,
            "description": tool.description,
            "args_schema": tool.args if hasattr(tool, 'args') else None
        }
        tools_info.append(tool_info)
    
    return {
        "tools": tools_info,
        "count": len(tools_info)
    }

@app.post("/reset")
async def reset_conversation(thread_id: str = "default"):
    """Reset a conversation thread"""
    # Note: With MemorySaver, you might need to implement thread cleanup
    # For now, we'll just return a success message
    return {
        "message": f"Conversation thread '{thread_id}' reset",
        "thread_id": thread_id
    }

if __name__ == "__main__":
    print("🚀 Starting Memento Agent API...")
    print("📊 Graph visualization available at: http://localhost:8000/graph")
    print("💬 Chat endpoint available at: http://localhost:8000/chat")
    print("🌊 Streaming chat available at: http://localhost:8000/stream")
    print("📚 API docs available at: http://localhost:8000/docs")
    
    uvicorn.run(
        "memento.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )