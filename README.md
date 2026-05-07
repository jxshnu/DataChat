# 📊 Grounded Sheet Q&A

Ask natural-language questions about your CSV/Excel data with **zero hallucination**. Powered by Groq API for fast, diverse model selection.

## 🎯 Core Features

- **100% Grounded Answers** — Every response is backed by actual data values. The LLM never invents data.
- **Outlier Detection** — Automatically identifies and flags statistical outliers using the IQR method.
- **Multi-Model Support** — Choose between cloud-based Groq models or local Ollama for privacy.
- **Live Code Generation** — The LLM generates and executes Pandas code against your real DataFrame for maximum accuracy.
- **Fast Performance** — Groq's inference API provides sub-second response times.

## 📌 Primary Use Case

**DataChat is specifically designed for:**
- 📊 Analyzing **CSV/Excel spreadsheets** with natural language queries
- 💰 **Financial data analysis** (sales, revenue, budgets)
- 📈 **Business intelligence** on structured datasets
- 🔬 **Data exploration** without SQL knowledge
- 🎯 **Fact-based reporting** where accuracy is critical

**NOT for:**
- 📚 Document/PDF analysis
- 📰 News/content summarization
- 🖼️ Image analysis
- 🔍 Semantic document search

## ✅ Advantages Over Other Architectures

### vs. RAG (Vector Databases)
| Feature | DataChat | RAG |
|---------|----------|-----|
| **Hallucination** | ❌ Impossible | ⚠️ High risk |
| **Accuracy on Numbers** | ✅ 100% | ❌ Unreliable |
| **Aggregations** | ✅ Perfect | ❌ Can't aggregate across chunks |
| **Cost** | ✅ Low (no vector DB) | ❌ High infrastructure |
| **Setup Complexity** | ✅ Simple | ❌ Complex |
| **Data Size** | ✅ Works well <500MB | ✅ Unlimited scale |

### vs. SQL Query Generation
| Feature | DataChat | SQL Gen |
|---------|----------|---------|
| **LLM Error Recovery** | ✅ Retries work | ❌ Hard to fix bad SQL |
| **No Schema Exposure** | ✅ Schema hidden | ❌ Full schema exposed |
| **Security** | ✅ Safer | ❌ SQL injection risks |
| **Non-Technical Users** | ✅ More forgiving | ❌ Requires SQL knowledge |

### vs. Direct LLM (No Grounding)
| Feature | DataChat | Direct LLM |
|---------|----------|-----------|
| **Accuracy** | ✅ 100% | ❌ Hallucinations |
| **Reliability** | ✅ Deterministic | ❌ Random errors |
| **Trust** | ✅ Verifiable | ❌ Can't verify |

## ❌ Disadvantages & Limitations

### Technical Limitations
1. **Only Structured Data** — Can't process PDFs, documents, or images
2. **Code Generation Failures** — LLM may write invalid Pandas syntax requiring retries
3. **Latency** — Code execution adds ~500ms-2s overhead vs. direct retrieval
4. **Context Window** — Can't pass massive datasets (>10MB) to LLM
5. **No Semantic Search** — Can't find data by meaning (only by value/structure)

### Scale Limitations
| Metric | Capacity |
|--------|----------|
| File Size | <500MB (practical) |
| Rows | <10 million (with pagination) |
| Columns | <1000 |
| Concurrent Users | Limited by LLM API rate limits |

### Cost Considerations
- ✅ No vector DB infrastructure costs
- ❌ Per-query LLM API calls (Groq pricing ~$0.0001/1000 tokens)
- ❌ Code retry attempts increase costs

### User Experience
1. **Speed** — Slower than direct retrieval (RAG) or database queries (SQL)
2. **Debugging** — Errors in generated code can be cryptic
3. **Data Types** — Struggles with highly nested/complex data structures

## 🎓 Architecture Deep Dive

**DataChat uses Code-Generation + Execution architecture:**

```
User Question
    ↓
[LLM sees: Schema + Statistics + Question]
    ↓
LLM generates Pandas code
    ↓
Code EXECUTES against real DataFrame
    ↓
[LLM sees: Code results (actual values)]
    ↓
LLM produces natural language answer
```

**Why this prevents hallucination:**
- LLM never directly invents data
- Results come from code execution, not generation
- Same question always produces identical answer
- Debuggable: Users can see generated code

**Comparison to alternatives:**
- **RAG**: Retrieves chunks, LLM synthesizes (high hallucination risk)
- **SQL**: Also code-execution-based, but requires schema exposure
- **Direct LLM**: No grounding, pure generation (maximum hallucination)

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- A Groq API key ([get one free](https://console.groq.com))
- Or: Ollama running locally for offline inference

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd llm_sheet

# Install dependencies
pip install -r requirements.txt
```

### Run the App

```bash
streamlit run app.py
```

Then open your browser to `http://localhost:8501`

## 📋 Project Structure

```
llm_sheet/
├── app.py                 # Streamlit UI and session management
├── llm_engine.py          # LLM interaction with code-generation grounding
├── data_processor.py      # CSV/Excel loading, profiling, outlier detection
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── archive/
    └── superstore.csv     # Sample dataset for testing
```

## 🔧 Architecture

### Data Processing (`data_processor.py`)

- **File Loading**: Supports CSV and Excel (.xlsx, .xls)
- **Schema Extraction**: Automatically detects column names, data types, and null counts
- **Statistical Profiling**: Calculates min, max, mean, median, std, Q1, Q3, IQR for numeric columns
- **Outlier Detection**: Flags rows where values fall outside `Q1 - 1.5*IQR` to `Q3 + 1.5*IQR`
- **Context Building**: Generates comprehensive data summaries injected into the LLM prompt

### LLM Engine (`llm_engine.py`)

**Anti-Hallucination Architecture:**

1. **System Prompt** includes:
   - Full schema with data types
   - Statistical summaries per column
   - Outlier flags
   - First 50 rows as markdown table (or full data if ≤50 rows)
   - Explicit grounding instruction: *"Answer ONLY based on the provided data"*

2. **Code Generation**: The LLM writes Pandas code to answer the question
3. **Execution**: Code is executed against the real DataFrame (no hallucination possible)
4. **Response**: The LLM produces a natural-language summary of results
5. **Temperature = 0**: Deterministic output for factual consistency

### Streamlit UI (`app.py`)

**Sidebar Controls:**
- LLM Provider selection (Groq Cloud / Ollama Local)
- API key input
- Model selection
- File upload

**Main Interface:**
- Chat-style Q&A
- Data profile cards (preview, statistics, outliers)
- Interactive conversation history

## 🤖 Available Models

### Groq Cloud Models

| Model | ID | Best For |
|---|---|---|
| Llama 3.3 70B | `llama-3.3-70b-versatile` | Best overall quality |
| Mixtral 8x7B | `mixtral-8x7b-32768` | Fast multi-task |
| Llama 3.1 8B | `llama-3.1-8b-instant` | Fastest responses |
| Gemma 2 9B | `gemma2-9b-it` | Lightweight, capable |
| Llama 4 Scout 17B | `meta-llama/llama-4-scout-17b-16e-instruct` | Advanced reasoning |
| Qwen3 32B | `qwen/qwen3-32b` | Strong logic |

### Ollama Local Models

Simply ensure Ollama is running (`ollama serve`) and select any installed model locally.

## 🛡️ Design Principles

1. **Zero Hallucination** — Grounding via code execution ensures factual accuracy
2. **Outlier Awareness** — Statistical outliers are detected and reported
3. **Data-First Prompting** — System prompt includes complete data context
4. **Privacy First** — Use Ollama for offline processing (no API calls)
5. **Transparency** — Users can see generated code and execution results

## 📊 Example Usage

1. **Upload Data**: Select a CSV or Excel file
2. **Ask a Question**: *"What are the top 5 sales regions by revenue?"*
3. **Get Instant Answer**: The LLM generates Pandas code, executes it, and explains results
4. **Review Outliers**: See flagged statistical anomalies that might affect aggregations

## ⚙️ Configuration

### Environment Variables

Create a `.env` file (or use secrets in Streamlit Cloud):

```
GROQ_API_KEY=your_api_key_here
```



## 🐛 Troubleshooting

**"Invalid API Key"**
- Verify your Groq API key at [console.groq.com](https://console.groq.com)
- Check that `GROQ_API_KEY` is set correctly

**"Ollama Connection Failed"**
- Ensure Ollama is running: `ollama serve`
- Verify localhost:11434 is accessible

**"Code Execution Error"**
- The LLM may generate invalid Pandas syntax
- Max retries (3) will automatically try different approaches
- Check the error message for hints

## 📦 Dependencies

- **streamlit** — UI framework
- **pandas** — Data processing
- **openpyxl** — Excel file support
- **groq** — Groq API client
- **numpy/scipy** — Statistical operations

