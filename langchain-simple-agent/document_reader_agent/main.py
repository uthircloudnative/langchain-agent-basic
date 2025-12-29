import os
from langchain.agents import create_agent
from langchain.tools import tool
from langchain.chat_models import init_chat_model
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 1. Initialize OpenAI Embeddings
embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        chunk_size=1000
    )

# 2. Initialize Chroma
vector_store = Chroma(
        collection_name = "spring_boot_4_document_collection",
        embedding_function = embeddings,
        persist_directory = "../data/vector_store"
    )

@tool(response_format="content_and_artifact")
def retrive_context(query: str):
    """
    Retrieve information from Spring Boot 4 docs.
    Returns text and the specific source URL for each chunk.
    """
    # 1. Get raw results from your database
    


    retrieved_docs = vector_store.similarity_search(query, k=3)

    formatted_context = []
    for doc in retrieved_docs:
        source_url = doc.metadata.get('source', 'No URL available')
        snippet = f"SOURCE: {source_url}\nCONTENT: {doc.page_content}"
        formatted_context.append(snippet)

    content = "\n\n---\n\n".join(formatted_context)

    # 3. Return content for LLM and full docs as artifact
    return content, retrieved_docs


def run_agent_query(query: str, agent):
    """
    Standardized function to handle agent execution.
    Easy to call from a CLI, a Web API, or a Colab loop.
    """
    responses = []
    for event in agent.stream(
        {"messages": [{"role": "user", "content": query}]},
        stream_mode="values"
    ):
        # In production, you might return the response rather than just printing
        responses.append(event["messages"][-1])

    return responses

def init_agent(tools):
    system_prompt=(
        """
        You are an expert on Spring Boot 4.0.1.
        Use the provided tool to find context for the user's query.

        CRITICAL INSTRUCTION: For every fact or code snippet you provide,
        you MUST cite the specific SOURCE URL provided in the context.

        Format your response like this:
        - Answer text...
        - Source: [URL here]

        If the query is not related to Spring Boot, say you don't understand.
        """
    )

    model = init_chat_model("gpt-4.1")
    agent = create_agent(model, tools, system_prompt=system_prompt)
    return agent

# Main function to run the agent
if __name__ == "__main__":
    print("Document reader agent is running...")
    tools = [retrive_context]

    agent = init_agent(tools)

    print("Ask me anything about Spring Boot 4.0.1!")
    print("Type 'exit', 'quit', or 'q' to stop.\n")
    while True:
        # Get user input
        user_query = input("You: ").strip()
        
        if not user_query:
            print("⚠️  Please enter a question.\n")
            continue

        # Exit conditions
        if user_query.lower() in ['exit', 'quit', 'q']:
            print("\n👋 Goodbye! Agent shutting down...")
            break
        
        # Process query
        print("\n🔍 Searching documentation...\n")
        result = run_agent_query(user_query, agent)
        
        # Display response
        for message in result:
            message.pretty_print()
        
        print("\n" + "-" * 50 + "\n")
    print("Document reader agent is executed successfully...")
