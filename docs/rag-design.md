# AegisMesh AI — RAG Knowledge Layer Design

## RAG Architecture Overview
The Retrieval-Augmented Generation (RAG) layer is responsible for injecting relevant corporate policies, legal regulations, and data governance rules into the LLM context. This ensures that agent reasoning is grounded in factual, organization-specific guidelines.

## Policy Document Corpus
The system maintains a corpus of policy documents, including:
- Data Privacy Policies (e.g., GDPR, CCPA handling rules)
- Security Standards (e.g., encryption requirements)
- Acceptable Use Policies

## Retrieval Interface
```python
def retrieve_policy_context(action: str, context: dict) -> list[Document]:
    pass
```

## Response Schema
```json
{
  "documents": [
    {
      "policy_id": "POL-SEC-042",
      "policy_text": "All PII data exported to external vendors must be encrypted and anonymized.",
      "metadata": {
        "version": "1.2",
        "category": "Data Handling"
      },
      "source": "Corporate_Security_Guidelines_v1.pdf",
      "citation": "Section 4.1.2",
      "relevance_score": 0.92
    }
  ]
}
```

## Provider Abstraction
The system utilizes a `RAGProvider` interface to allow seamless switching between implementations.
- `LocalProvider`: A simplified, lightweight provider used for development and local testing.
- `VectorStoreProvider`: The production implementation backing into a vector database.

## Embedding Strategy
- **MVP**: Keyword and semantic matching using lightweight local models or regex-based heuristic filtering for demo purposes.
- **Future State**: Full vector embeddings using models like `ibm/slate-125m-english-rtrvr` stored in a vector database.

## Policy Document Format
Documents are ingested in markdown or plain text, chunked by semantic sections (e.g., paragraphs or specific rule clauses), and tagged with metadata (domain, strictness, target roles).

## How Agents Consume Evidence
The Compliance Agent receives the retrieved policy texts as direct context in its system prompt:
*"Evaluate the user's request against the following company policies: [Retrieved Policy Text]. Determine if the request violates any of these rules."*

## Extensibility for Vector Databases
The `RAGProvider` interface is designed to support drop-in replacements for robust vector stores like ChromaDB, Pinecone, or Milvus as the policy corpus scales.
