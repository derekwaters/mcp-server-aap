from llama_stack_client import Agent, AgentEventLogger, RAGDocument, LlamaStackClient

vector_db_id = "my_demo_vector_db"
client = LlamaStackClient(base_url="http://0.0.0.0:8321")

models = client.models.list()

# Select the first ollama and first ollama's embedding model
model_id = next(m for m in models if m.model_type == "llm" and m.provider_id == "ollama").identifier
embedding_model = next(m for m in models if m.model_type == "embedding" and m.provider_id == "ollama")
embedding_model_id = embedding_model.identifier
embedding_dimension = embedding_model.metadata["embedding_dimension"]

vector_db = client.vector_dbs.register(
    vector_db_id = vector_db_id,
    embedding_model = embedding_model_id,
    embedding_dimension = embedding_dimension,
    provider_id = "faiss",
)
vector_db_id = vector_db.identifier

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
    chunk_size_in_tokens = 100,
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
