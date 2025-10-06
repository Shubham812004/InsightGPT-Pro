# app/services/agent_service.py
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.agent_toolkits import create_sql_agent
from langchain.tools import Tool
from langchain_community.utilities.sql_database import SQLDatabase
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END

# --- ADD THESE MISSING IMPORTS ---
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
# --- END OF ADDITIONS ---

from app.services import rag_service
from app.core.database import DATABASE_URL

load_dotenv()

# --- 1. Define Tools (No change here) ---
llm = ChatGoogleGenerativeAI(model="gemini-pro-latest", temperature=0, convert_system_message_to_human=True)
db = SQLDatabase.from_uri(DATABASE_URL)
sql_agent_executor = create_sql_agent(llm=llm, db=db, agent_type="openai-tools", verbose=False)
sql_tool = Tool(name="SQLDatabase", func=sql_agent_executor.invoke, description="Use this tool to answer questions about structured sales data like sales, regions, products, revenue, etc.")
rag_tool = Tool(name="FinancialReportSearch", func=rag_service.query_rag, description="Use this tool to answer questions about the Q3 2025 financial report or any other uploaded document/summary.")

tools = [sql_tool, rag_tool]

# --- 2. Define the Agent State (No change here) ---
class AgentState(TypedDict):
    input: str
    context: str
    result: str

# --- 3. Define the Router (No change here) ---
def router(state: AgentState) -> Literal["sql_node", "rag_node"]:
    print("---ROUTER---")
    router_prompt = f"""Based on the user's question, decide which tool is the most appropriate to use.
    Your options are:
    - 'SQLDatabase': For questions about sales, revenue, products, and regions in the database.
    - 'FinancialReportSearch': For questions about financial reports, CEO statements, or uploaded summaries/documents.

    User Question: "{state['input']}"

    Respond with ONLY the name of the tool to use.
    """
    router_response = llm.invoke(router_prompt)

    if "sql" in router_response.content.lower():
        print("Routing to SQL node.")
        return "sql_node"
    else:
        print("Routing to RAG node.")
        return "rag_node"

# --- 4. Define Worker and Generation Nodes ---
prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are a helpful data analyst assistant. You have access to a SQL database and a document search tool.

    IMPORTANT: If the user asks for a visualization like a 'chart' or 'plot', first use the SQL tool to get the necessary data. Then, you MUST format your final response as a single JSON object.

    For a BAR CHART, the JSON should look like this:
    {{
      "comment": "Here is a bar chart showing the total revenue by region.",
      "chart_details": {{
        "type": "bar",
        "x_col": "region",
        "y_col": "total_revenue",
        "title": "Total Revenue by Region"
      }},
      "data": [ {{"region": "North", "total_revenue": 867.5}}, ... ]
    }}

    For a PIE CHART, the JSON should look like this:
    {{
      "comment": "Here is a pie chart showing the revenue distribution by product.",
      "chart_details": {{
        "type": "pie",
        "names_col": "product",
        "values_col": "total_revenue",
        "title": "Revenue Distribution by Product"
      }},
      "data": [ {{"product": "Widget A", "total_revenue": 1130.0}}, ... ]
    }}

    If the user asks a regular question, just answer in natural language.
    """),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

def sql_node(state: AgentState) -> dict:
    print("---SQL NODE---")
    agent = create_tool_calling_agent(llm, [sql_tool], prompt)
    agent_executor = AgentExecutor(agent=agent, tools=[sql_tool], verbose=True)
    response = agent_executor.invoke({"input": state["input"]})
    return {"context": response["output"]}

def rag_node(state: AgentState) -> dict:
    print("---RAG NODE---")
    response = rag_tool.invoke(state["input"])
    return {"context": response}

def generate_node(state: AgentState) -> dict:
    print("---GENERATE---")
    question = state["input"]
    context = state["context"]
    prompt_text = f"""You are a helpful assistant. Based on the following context that was retrieved,
    provide a concise, natural language answer to the user's question. If the context is a JSON object for a chart,
    simply return the JSON object as-is.

    Context:
    {context}

    User's Question:
    {question}
    """
    response = llm.invoke(prompt_text)
    return {"result": response.content}

# --- 5. Build the Graph (No change here) ---
workflow = StateGraph(AgentState)
workflow.add_node("sql_node", sql_node)
workflow.add_node("rag_node", rag_node)
workflow.add_node("generate_node", generate_node)
workflow.set_conditional_entry_point(router, {"sql_node": "sql_node", "rag_node": "rag_node"})
workflow.add_edge("sql_node", "generate_node")
workflow.add_edge("rag_node", "generate_node")
workflow.add_edge("generate_node", END)
agent_graph = workflow.compile()
print("Upgraded multi-agent graph compiled successfully.")

# --- 6. Main service functions (No change here) ---
def run_query(query: str):
    try:
        response = agent_graph.invoke({"input": query})
        return response.get('result', "No result found.")
    except Exception as e:
        return f"An error occurred in the agent graph: {e}"

def create_agent():
    return agent_graph