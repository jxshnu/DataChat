# DataChat: Grounded Sheet Q&A

DataChat provides an interface to query CSV and Excel data using natural language while ensuring factual, reproducible answers through code generation and execution.

## Core Features

- 100% grounded answers: Every response is derived from executed code against the source dataset.
- Outlier detection: Identifies and annotates statistical outliers using the interquartile range (IQR) method.
- Multi-model support: Select cloud-based Groq models or a locally hosted Ollama instance for private inference.
- Code generation and execution: The system generates Pandas code to answer queries and executes it against the DataFrame to produce results.
- Deterministic output: Model temperature is configured for deterministic responses where possible.

## Primary Use Cases

DataChat is intended for scenarios that require precise, auditable answers from structured tabular data, including:

- Analysis of CSV or Excel spreadsheets using natural language queries.
- Financial and operational reporting (sales, revenue, budgets, forecasting validation).
- Business intelligence and exploratory data analysis for structured datasets.
- Enabling non-technical users to perform data analysis without SQL knowledge.

The system is not designed for unstructured document analysis, image processing, or multimedia retrieval.

## Advantages Compared to Retrieval-Based Architectures

### Versus retrieval-augmented generation (RAG) / vector databases

| Feature | DataChat | RAG / Vector DB |
|---|---:|:---|
| Hallucination risk | None (answers are executed) | High (synthesis from retrieved context) |
| Numerical accuracy and aggregations | High (native computation) | Low (retrieved snippets may not aggregate correctly) |
| Infrastructure complexity | Low (no vector DB required) | High (embeddings and index management) |
| Suitable data types | Structured tabular data | Unstructured text, documents, multimedia |

### Versus SQL generation against a database

| Feature | DataChat | SQL generation |
|---|---:|:---|
| Exposure of schema | Controlled (schema summarized for prompt) | Exposes full schema to generator |
| Error recovery | Retries and result validation built-in | Can be brittle; SQL errors may require manual fixes |
| User accessibility | High for non-technical users | Lower without SQL knowledge |

### Versus direct LLM answers without grounding

Direct LLM responses can be fluent but are prone to errors and fabrications when precise, factual answers are required. DataChat reduces that risk by executing code that produces the underlying results.

## Limitations and Trade-offs

### Technical constraints

1. The architecture is optimized for structured, tabular data; it does not perform semantic search or deep language understanding for unstructured documents.
2. The LLM must generate syntactically correct Pandas code; generation failures or invalid code may require retries.
3. Code execution adds latency relative to pure retrieval approaches.
4. Large datasets that exceed prompt or memory limits require sampling, pagination, or pre-aggregation strategies.

### Scale and performance

| Metric | Practical guideline |
|---|---:|
| File size | Recommended under ~500 MB for direct in-memory processing |
| Rows | Practical with tens of millions if processing is batched, otherwise consider a database backend |
| Columns | Works well with up to several hundred columns; extremely wide tables may require preprocessing |

### Cost considerations

- Eliminates vector DB costs but incurs per-query LLM API costs. Invalid code retries increase the number of model calls.

## Architecture Overview

DataChat uses a code-generation and execution approach:

1. The system summarizes schema and statistics for the dataset and constructs a constrained system prompt.
2. The LLM generates a short Pandas snippet intended to compute the requested result and assigns the output to a variable (for example, `result`).
3. The application executes the generated code against the DataFrame in a controlled environment and captures the output.
4. The output is returned to the LLM for formatting into a human-readable response, and the executed code may be presented to the user for audit.

This approach enforces that numeric and tabular answers are derived directly from computation rather than free-form generation.

## Getting Started

### Prerequisites

- Python 3.8 or newer
- A Groq API key (if using the Groq cloud models) or a local Ollama instance for private inference

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd DataChat

# Install dependencies
pip install -r requirements.txt
```

### Run the application

```bash
streamlit run app.py
```

Then open your browser to `http://localhost:8501`.

## Project Layout

```
DataChat/
├── app.py                 # Streamlit UI and session management
├── llm_engine.py          # LLM interaction with code-generation grounding
├── data_processor.py      # CSV/Excel loading, profiling, outlier detection
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── archive/
    └── superstore.csv     # Sample dataset for testing
```

## Implementation Details

### Data processing (`data_processor.py`)

- File loading: CSV and Excel (.xlsx/.xls) support
- Schema extraction: column names, inferred data types, null counts
- Statistical profiling: min, max, mean, median, std, Q1, Q3, IQR for numeric columns
- Outlier detection: IQR-based flagging
- Context builder: summary used to constrain the model prompt

### LLM engine (`llm_engine.py`)

- The system prompt contains schema, column statistics, and a clear instruction to reason only from provided data.
- The LLM generates Pandas code constrained to `pandas` and `numpy` operations.
- Generated code is executed in process; results are validated and returned as the authoritative answer.

### Streamlit UI (`app.py`)

- Controls for model/provider selection, API key input, and file upload
- Conversation-style interface for issuing queries and reviewing generated code

## Available Models

Supported model identifiers for Groq and local Ollama instances are provided in `llm_engine.py`. Ensure your selected model is available and compatible with the provider you choose.

## Design Principles

1. Grounded computation: answers are derived by executing code against the dataset.
2. Outlier awareness: statistical anomalies are surfaced to the user.
3. Privacy-first options: local inference via Ollama is supported.
4. Transparency: users can review generated code and execution results.

## Example Workflow

1. Upload a CSV or Excel file.
2. Ask a question in natural language, for example: "What are the top five regions by revenue?"
3. The LLM generates Pandas code that computes the result; the application executes it and returns the answer with supporting code and context.

## Configuration and Troubleshooting

### Environment variables

Create a `.env` file or configure secrets for deployment:

```
GROQ_API_KEY=your_api_key_here
```

### Common issues

- Invalid API key: confirm the key at https://console.groq.com and verify environment configuration.
- Ollama connection: ensure `ollama serve` is running and accessible when using a local provider.
- Code execution errors: inspect the generated code and the execution trace; the system will attempt retries for common failure modes.

## Dependencies

- streamlit
- pandas
- openpyxl
- groq (Groq client library)
- numpy, scipy

## Contributing and Support

For issues or feature requests, please open an issue on GitHub with a clear description and sample data if applicable.

---

Built with Streamlit, Groq, and Pandas.
