# AegisMesh AI — IBM Services Integration

## IBM Granite Integration
AegisMesh AI utilizes IBM Granite models via watsonx.ai as the core reasoning engine for complex agentic tasks.

### Provider Abstraction
The system uses an `LLMProvider` interface to decouple business logic from the specific LLM API.
- **GraniteProvider**: Implements `LLMProvider` using the IBM watsonx.ai SDK.
- **MockProvider**: Returns hardcoded, deterministic responses for testing and demos.

### Auto-Selection
The system selects the provider based on environment variables:
```bash
# Use IBM Granite
USE_MOCK_LLM=false
WATSONX_API_KEY=your_key
WATSONX_PROJECT_ID=your_project

# Use Mock Provider
USE_MOCK_LLM=true
```

### Agent Usage of Granite
Granite models excel at structured tasks and compliance reasoning. They are utilized by:
- **Intent Classification**: Determining the real goal behind a request.
- **Compliance Assessment**: Complex logical reasoning comparing request parameters against retrieved RAG policies.
- **Risk Reasoning**: Evaluating multi-factor risk contexts.
- **Explainability**: Generating clear, auditor-friendly text explaining the decision.

### Structured Output Format
Agents instruct Granite to return responses in strict JSON formats (enforced via prompt engineering and schema validation) to ensure reliable parsing by the orchestration layer.

## IBM BOB (Builder for watsonx)
IBM BOB was utilized as a powerful development accelerator during the creation of AegisMesh AI. **Note: BOB is not a runtime dependency.**

### Use Cases During Development
- **Boilerplate Generation**: Rapidly scaffolding FastAPI routes and React components.
- **Code Navigation**: Understanding complex relationships in the initial multi-agent framework.
- **Debugging**: Identifying state-leakage issues across asynchronous agent calls.
- **Test Generation**: Automating the creation of unit tests for the `DecisionRouter`.
- **Documentation**: Assisting in the generation of structured markdown files (like this one).

### Team Workflow with BOB
The engineering team integrated BOB into their IDEs to maintain high velocity, particularly when writing the prompt templates and validation logic for the Granite integration.

## Demo Mode Behavior
When demo mode is activated, mock providers are engaged which simulate the behavior of Granite models to ensure seamless, repeatable demos.

## UI Provider Indicator
The Frontend UI features a small status indicator in the footer that displays the active LLM provider (e.g., "Powered by IBM Granite" or "Demo Mode (Mock LLM)"), giving users immediate visibility into the system's operational mode.
