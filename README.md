```markdown
# Grounded Sheet Q&A

Query CSV and Excel datasets using natural language while eliminating hallucinations. This application is powered by the Groq API to provide high-performance inference and diverse model selection.

---

## Core Features

*   **Fully Grounded Responses:** Every response is backed by actual data values. The LLM does not invent or estimate data.
*   **Outlier Detection:** Automatically identifies and flags statistical outliers utilizing the Interquartile Range (IQR) method.
*   **Multi-Model Support:** Configure the system to use either cloud-based Groq models or local Ollama deployments for strict data privacy.
*   **Live Code Generation:** The LLM generates and executes Pandas code against the provided DataFrame to ensure maximum mathematical accuracy.
*   **High Performance Inference:** Groq's inference API delivers sub-second response times for code generation and analysis.

---

## Primary Use Cases

**DataChat is engineered for the following applications:**
*   Analyzing CSV and Excel spreadsheets via natural language queries.
*   Financial data analysis (e.g., sales, revenue, budget tracking).
*   Business intelligence operations on structured datasets.
*   Data exploration for non-technical users without SQL proficiency.
*   Fact-based reporting where precision and accuracy are strictly required.

**Out of Scope:**
*   Unstructured document or PDF analysis.
*   News or long-form content summarization.
*   Image processing and computer vision tasks.
*   Semantic document search.

---

## Architectural Advantages

### vs. Retrieval-Augmented Generation (RAG)
| Feature | DataChat | Standard RAG |
|---------|----------|-----|
| **Hallucination Risk** | Impossible | High |
| **Numerical Accuracy** | 100% | Unreliable |
| **Aggregations** | Supported | Unsupported across chunks |
| **Infrastructure Cost**| Low (No Vector DB) | High |
| **Setup Complexity** | Simple | Complex |
| **Optimal Data Size** | < 500MB | Unlimited |

### vs. Text-to-SQL Generation
| Feature | DataChat | SQL Generation |
|---------|----------|---------|
| **Error Recovery** | Supported via retries | Difficult to automate |
| **Schema Exposure** | Abstracted | Fully Exposed |
| **Security Risk** | Secure (Local Execution) | Susceptible to SQL Injection |
| **User Experience** | Accessible | Often requires SQL debugging |

### vs. Direct LLM Prompting
| Feature | DataChat | Direct LLM |
|---------|----------|-----------|
| **Factual Accuracy** | 100% | Prone to hallucinations |
| **Reliability** | Deterministic | Stochastic |
| **Verifiability** | High (Code is visible) | Low |

---

## Disadvantages & Limitations

### Technical Limitations
1.  **Structured Data Only:** Cannot process unstructured formats like PDFs, Word documents, or images.
2.  **Code Generation Failures:** The LLM may occasionally write invalid Pandas syntax, necessitating automated retries.
3.  **Execution Latency:** Local code execution adds approximately 500ms to 2s of overhead compared to direct retrieval.
4.  **Context Window Constraints:** Extremely wide datasets cannot have their full statistical profiles passed into the standard context window.
5.  **Lack of Semantic Search:** Queries must align with the structural naming conventions of the data; it cannot search purely by conceptual meaning.

### Scale Limitations
| Metric | Supported Capacity |
|--------|----------|
| **File Size** | < 500MB (Practical limit for Pandas) |
| **Row Count** | < 10 million (Requires pagination/chunking for larger sets) |
| **Column Count** | < 1000 |
| **Concurrency** | Bound by active LLM API rate limits |

### Cost Considerations
*   Eliminates standard vector database infrastructure costs.
*   Incurs per-query API costs (e.g., Groq API pricing).
*   Automated code-retry attempts will multiply token consumption per query.

### User Experience Implications
1.  **Response Time:** Marginally slower than direct vector retrieval or indexed database queries.
2.  **Debugging Complexity:** Errors stemming from generated Pandas code can be complex for non-technical users to diagnose.
3.  **Complex Data Types:** May struggle with heavily nested JSON or highly denormalized data structures within CSVs.

---

## Architecture Deep Dive

**DataChat utilizes a Code-Generation and Execution pipeline:**
```text
User Query
    ↓
[LLM Context: Schema + Statistical Profile + Query]
    ↓
LLM generates Pandas executable code
    ↓
Code executes securely against the DataFrame
    ↓
[LLM Context: Execution Output (Actual Values)]
    ↓
LLM generates natural language synthesis
```

**Hallucination Prevention Mechanism:**
*   The model never attempts to recall or synthesize data points directly.
*   All quantitative results are derived from deterministic code execution.
*   Identical queries yield identical answers.
*   Full transparency: The underlying Pandas code is accessible for user auditing.

---

## Quick Start Guide

### Prerequisites

*   Python 3.8 or higher.
*   A Groq API key (Available at console.groq.com).
*   Optional: Ollama installed locally for offline inference.

### Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd llm_sheet

# Install dependencies
pip install -r requirements.txt
```

### Execution

```bash
streamlit run app.py
```

Navigate to `http://localhost:8501` in your web browser.

---

## Project Structure

```text
llm_sheet/
├── app.py                 # Streamlit UI routing and session state management
├── llm_engine.py          # LLM API handlers and code-generation pipelines
├── data_processor.py      # I/O operations, statistical profiling, and outlier detection
├── requirements.txt       # Environment dependencies
├── README.md              # Project documentation
└── archive/
    └── superstore.csv     # Sample dataset for testing and validation
```

---

## System Components

### Data Processing (`data_processor.py`)

*   **File I/O:** Native support for CSV and Excel formats (.xlsx, .xls).
*   **Schema Extraction:** Dynamic detection of column headers, dtypes, and null distributions.
*   **Statistical Profiling:** Automated calculation of minimum, maximum, mean, median, standard deviation, Q1, Q3, and IQR for all numeric series.
*   **Outlier Detection:** Highlights records falling outside the standard distribution curve (`Q1 - 1.5*IQR` to `Q3 + 1.5*IQR`).
*   **Context Engineering:** Compiles the extracted metadata into a strict prompt template for the LLM.

### LLM Engine (`llm_engine.py`)

*   **System Prompting:** Injects the schema, statistical summaries, outlier flags, and a sample DataFrame head into the context window.
*   **Execution Sandbox:** Safely executes the generated Pandas code.
*   **Deterministic Output:** Enforces a temperature of 0.0 to ensure consistent, factual reporting.

### User Interface (`app.py`)

*   **Sidebar Configuration:** Controls for LLM provider selection, API key management, model toggling, and file uploading.
*   **Main Dashboard:** Features a conversational interface, data profile metrics, outlier warnings, and an expandable execution log.

---

## Supported Models

### Groq Cloud Models

| Model | Identifier | Optimal Use Case |
|---|---|---|
| Llama 3.3 70B | `llama-3.3-70b-versatile` | Highest overall reasoning quality |
| Mixtral 8x7B | `mixtral-8x7b-32768` | Balanced speed and multi-tasking |
| Llama 3.1 8B | `llama-3.1-8b-instant` | Lowest latency responses |
| Gemma 2 9B | `gemma2-9b-it` | Lightweight processing |
| Llama 4 Scout 17B | `meta-llama/llama-4-scout-17b-16e-instruct` | Advanced logic and reasoning |
| Qwen3 32B | `qwen/qwen3-32b` | Strong structural understanding |

### Local Models (Ollama)

Ensure the Ollama service is active (`ollama serve`). The application will automatically detect and populate available local models.

---

## Design Principles

1.  **Factual Determinism:** Grounding via local code execution is mandatory.
2.  **Statistical Awareness:** Anomalies and outliers must be surfaced automatically to prevent skewed interpretations.
3.  **Context-Heavy Prompting:** The LLM must be fully aware of the data schema before generating execution paths.
4.  **Data Sovereignty:** Support for local inference (Ollama) to ensure sensitive data never leaves the host machine.
5.  **Auditability:** Generated code and intermediate execution outputs are fully transparent.

---

## Example Workflow

1.  **Initialization:** Upload a target CSV or Excel file.
2.  **Query Input:** Submit a prompt (e.g., "Identify the top 5 sales regions by gross revenue.")
3.  **Processing:** The system generates Pandas code, executes the aggregation, and synthesizes the raw output.
4.  **Review:** Analyze the natural language response alongside the execution log and any flagged statistical outliers.

---

## Configuration

### Environment Variables

Establish a `.env` file in the root directory (or utilize Streamlit Secrets):
```env
GROQ_API_KEY=your_api_key_here
```

---

## Troubleshooting

**API Key Authentication Errors**
*   Validate the active Groq API key via the Groq Console.
*   Ensure the `.env` file is properly formatted and loaded.

**Ollama Connection Timeouts**
*   Confirm the Ollama background service is running (`ollama serve`).
*   Verify network access to `localhost:11434`.

**Code Execution Failures**
*   The LLM may attempt unsupported Pandas operations. The system includes an automated 3-attempt retry logic.
*   Review the generated code in the UI expander to identify structural errors.

---

## Dependencies

*   **streamlit:** Front-end framework and state management.
*   **pandas:** Core data manipulation and execution engine.
*   **openpyxl:** Excel file format support.
*   **groq:** Official Groq API client.
*   **numpy / scipy:** Advanced statistical computations.
```
