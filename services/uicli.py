import time
from langchain.messages import AIMessageChunk, ToolMessage


def print_ai_response(result):
    final = result["messages"][-1]

    print("=" * 80)
    print("AI Response")
    print("=" * 80)

    if isinstance(final.content, list):
        for part in final.content:
            if part.get("type") == "text":
                print(part["text"])
    else:
        print(final.content)

    usage = getattr(final, "usage_metadata", None)
    if usage:
        print("\n" + "-" * 80)
        print(
            f"INPUT: {usage.get('input_tokens', 0)}   "
            f"OUTPUT: {usage.get('output_tokens', 0)}   "
            f"TOTAL: {usage.get('total_tokens', 0)}"
        )

        print(f"MODEL: {final.response_metadata.get('model_name', 'Unknown')}")


def print_documents(vector_store, query: str, k: int = 5):
    print(f"\n🔍 Query: {query}")

    results = vector_store.similarity_search(query, k=k)

    for index, doc in enumerate(results, 1):
        print("\n" + "=" * 100)
        print(f"Result #{index}")
        print(f"Title    : {doc.metadata.get('title', 'N/A')}")
        print(f"Category : {doc.metadata.get('category', 'N/A')}")
        print(f"Source   : {doc.metadata.get('source', 'N/A')}")
        print("-" * 100)
        print(doc.page_content.strip())
        print(doc.metadata)



def stream_response(agent, inputs, **kwargs):
    print("=" * 100)
    print("🤖 AI Response")
    print("=" * 100)

    start = time.perf_counter()

    complete_message = None
    usage = None
    response_metadata = None

    for chunk, metadata in agent.stream(
        inputs,
        stream_mode="messages",
        **kwargs,
    ):

        # -------------------------
        # AI Response
        # -------------------------
        if isinstance(chunk, AIMessageChunk):

            # Stream text
            if chunk.text:
                print(chunk.text, end="", flush=True)

            # Merge chunks
            if complete_message is None:
                complete_message = chunk
            else:
                complete_message += chunk

            # Save latest metadata if present
            if getattr(chunk, "usage_metadata", None):
                usage = chunk.usage_metadata

            if getattr(chunk, "response_metadata", None):
                response_metadata = chunk.response_metadata

            # Tool calls
            if chunk.tool_calls:
                print("\n\n🔧 Tool Call(s):")
                for tool in chunk.tool_calls:
                    print(f"   • {tool['name']}")
                    print(f"     Args: {tool['args']}")

        # -------------------------
        # Tool Response
        # -------------------------
        elif isinstance(chunk, ToolMessage):
            print("\n")
            print("-" * 100)
            print("📄 Tool Response")
            print("-" * 100)
            print(chunk.content)
            print("-" * 100)

    elapsed = time.perf_counter() - start

    print("\n")

    # If metadata wasn't found in an individual chunk, check the merged message
    if complete_message:
        usage = usage or getattr(complete_message, "usage_metadata", None)
        response_metadata = response_metadata or getattr(
            complete_message,
            "response_metadata",
            {},
        )

    # -------------------------
    # Usage
    # -------------------------
    if usage:
        print("=" * 100)
        print("📊 Usage")
        print("=" * 100)
        print(
            f"INPUT : {usage.get('input_tokens', 0):<8}"
            f"OUTPUT : {usage.get('output_tokens', 0):<8}"
            f"TOTAL : {usage.get('total_tokens', 0):<8}"
        )

    if response_metadata:
        print(f"MODEL : {response_metadata.get('model_name', 'Unknown')}")

    print(f"TIME  : {elapsed:.2f}s")
    print("=" * 100)