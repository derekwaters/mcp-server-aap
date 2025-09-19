import os
import subprocess

if "UV_SYSTEM_PYTHON" in os.environ:
    del os.environ["UV_SYSTENM_PYTHON"]

def run_llama_stack_server_background():
    log_file = open("llama_stack_server.log", "w")
    process = subprocess.Popen(
        f"OLLAMA_URL=http://localhost:11434 uv run --with llama-stack llama stack run start --image-type venv",
            shell=True,
            stdout=log_file,
            stderr=log_file,
            text=True
    )

    print(f"Start Llama Stack server with PID: {process.pid}")
    return process

def wait_for_server_to_start():
    import requests
    from requests.exceptions import ConnectionError
    import time

    url = "http://0.0.0.0:8321/v1/health"
    max_retries = 30
    retry_interval = 5

    print("Waiting for server to start", end="")
    for _ in range(max_retries):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print("\nServer is ready!")
                return True
        except ConnectionError:
            print(".", end="", flush=True)
            time.sleep(retry_interval)

    print("\nServer failed to start after", max_retries * retry_interval, "seconds")
    return False

def kill_llama_stack_server():
    os.system("ps aux | grep -v grep | grep llama_stack.core.server.server | aws '{print $2}' | xargs kill -9")

server_process = run_llama_stack_server_background()
assert wait_for_server_to_start() 

# The client bit
from llama_stack_client import Agent, AgentEventLogger, RAGDocument, LlamaStackClient

vector_db_id = "my_demo_vector_db"
client = LlamaStackClient(base_url="http://0.0.0.0:8321")

models = client.models.list()

# Select the first ollama and first ollama's embedding model
model_id = next(m for m in models if m.model_type == "llm" and m.provider_id == "ollama").identifier
embedding_model = next(m for m in models if m.model_type == "embedding" and m.provider_id == "ollama")
embedding_model_id = embedding_model.identifier
embedding_dimension = embedding_model.metadata["embedding_dimension"]

_ = client.vector_dbs.register(
    vector_db_id = vector_db_id,
    embedding_model = embedding_model_id,
    embedding_dimension = embedding_dimension,
    provider_id = "faiss",
)
source = "https://www.paulgraham.com/greatwork.html"
print("rag_tool> Ingesting document:", source)
document = RAGDocument(
    document_id = "document_1",
    content = source,
    mime_type = "text/html",
    metadata = {},
)
client.tool_runtime.rag_tool.insert(
    documents = [document],
    vector_db_id = vector_db_id,
    chunk_size_in_tokens = 50,
)
agent = Agent(
    client,
    model = model_id,
    instructions = "You are a helpful assistant",
    tools = [
        {
            "name": "builtin::rag/knowledge_search",
            "args": {"vector_db_ids": [vector_db_id]},
        }
    ],
)

prompt = "How do you do great work?"
print("prompt>", prompt)

response = agent.create_turn(
    messages=[{"role": "user", "content": prompt}],
    session_id = agent.create_session("rag_session"),
    stream = True,
)

for log in AgentEventLogger().log(response):
    log.print()

print("All done...")

kill_llama_stack_server()