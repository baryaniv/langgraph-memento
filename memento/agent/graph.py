from pydantic import BaseModel
from typing import Annotated, List, Generator
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessageChunk
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from .tools import table_searcher, sql_checker, sql_runner
from ..prompts import prompts
from .. import env


class  MementoState(BaseModel):
    messages: Annotated[List[BaseMessage], add_messages] = []
    chart_json: str = ""


class Agent:
    """
    Agent class for implementing Langgraph agents.

    Attributes:
        name: The name of the agent.
        tools: The tools available to the agent.
        model: The model to use for the agent.
        system_prompt: The system prompt for the agent.
        temperature: The temperature for the agent.
    """
    def __init__(
            self, 
            name: str, 
            tools: List = [],
            model: str = None, 
            system_prompt: str = "You are a helpful assistant.",
            temperature: float = 0.1
            ):
        self.name = name
        self.tools = tools
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        
        self.llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=env.OPENAI_API_KEY,
            base_url=env.OPENAI_API_BASE_URL
            ).bind_tools(self.tools)
        
        self.runnable = self.build_graph()


    def build_graph(self):
        """
        Build the LangGraph application.
        """
        def memento_node(state: MementoState) -> MementoState:
            response = self.llm.invoke(
                [SystemMessage(content=self.system_prompt)] +
                state.messages
                )
            state.messages = state.messages + [response]
            print(f"Memento node response: {response}")
            return state
        
        def chatbot_router(state: MementoState) -> str:
            """Route from chatbot to specific tools"""
            last_message = state.messages[-1]

            if not last_message.tool_calls:
                return END

            tool_call = last_message.tool_calls[0]
            tool_name = tool_call["name"]

            if tool_name == "table_searcher":
                return "table_search_node"
            elif tool_name == "sql_checker":
                return "sql_check_node"
            elif tool_name == "sql_runner":
                return "sql_runner_node"
            else:
                return END


        table_searcher_tool = [tool for tool in self.tools if tool.name == 'table_searcher'][0]
        sql_checker_tool = [tool for tool in self.tools if tool.name == 'sql_checker'][0]
        sql_runner_tool = [tool for tool in self.tools if tool.name == 'sql_runner'][0]

        builder = StateGraph(MementoState)

        # Add nodes
        builder.add_node("chatbot", memento_node)
        builder.add_node("table_search_node", ToolNode([table_searcher_tool]))
        builder.add_node("sql_check_node", ToolNode([sql_checker_tool]))
        builder.add_node("sql_runner_node", ToolNode([sql_runner_tool]))

        builder.add_edge(START, "chatbot")
        builder.add_conditional_edges("chatbot",chatbot_router,["table_search_node","sql_check_node","sql_runner_node",END])
        builder.add_edge("table_search_node", "chatbot")
        builder.add_edge("sql_check_node", "chatbot")
        builder.add_edge("sql_runner_node", "chatbot")

        return builder.compile(checkpointer=MemorySaver())

    def inspect_graph(self):
        """
        Visualize the graph using the mermaid.ink API.
        """
        from IPython.display import display, Image

        graph = self.build_graph()
        display(Image(graph.get_graph(xray=True).draw_mermaid_png()))


    def invoke(self, message: str, **kwargs) -> str:
        """Synchronously invoke the graph.

        Args:
            message: The user message.

        Returns:
            str: The LLM response.
        """
        result = self.runnable.invoke(
            input = {
                "messages": [HumanMessage(content=message)]
            },
            **kwargs
        )

        return result["messages"][-1].content
    

    def stream(self, message: str, **kwargs) -> Generator[str, None, None]:
        """Synchronously stream the results of the graph run.

        Args:
            message: The user message.

        Returns:
            str: The final LLM response or tool call response
        """
        for message_chunk, metadata in self.runnable.stream(
            input = {
                "messages": [HumanMessage(content=message)]
            },
            stream_mode="messages",
            **kwargs
        ):
            if isinstance(message_chunk, AIMessageChunk):
                if message_chunk.response_metadata:
                    finish_reason = message_chunk.response_metadata.get("finish_reason", "")
                    if finish_reason == "tool_calls":
                        yield "\n\n"

                if message_chunk.tool_call_chunks:
                    tool_chunk = message_chunk.tool_call_chunks[0]

                    tool_name = tool_chunk.get("name", "")
                    args = tool_chunk.get("args", "")

                    
                    if tool_name:
                        tool_call_str = f"\n\n< TOOL CALL: {tool_name} >\nArgs: {args}\n\n"
                    yield tool_call_str

                    if args:
                        tool_call_str = args
                    yield tool_call_str
                else:
                    yield message_chunk.content
                continue


# Define and instantiate the agent 
agent = Agent(
        name="Memento",
        system_prompt=prompts.memento_system_prompt,
        tools=[table_searcher, sql_checker, sql_runner],
        model=env.OPENAI_MODEL
        )
graph = agent.build_graph()

try:
    # Get mermaid diagram as text
    mermaid_code = graph.get_graph().draw_mermaid()
    print("=== Graph Mermaid Diagram ===")
    print(mermaid_code)
    print("\n" + "="*50)
    print("Copy the above code to https://mermaid.live to visualize")
except Exception as e:
    print(f"Could not generate mermaid diagram: {e}")


print(f'graph', graph)
