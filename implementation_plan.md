# Grounded LLM Sheet Q&A Application

A Streamlit app that lets users upload CSV/Excel files and ask natural-language questions grounded strictly in the data — using Groq API for fast, diverse model selection.

## Core Design Principles

1. **Zero hallucination** — The LLM never invents data. Every answer is backed by actual values from the sheet.
2. **Outlier awareness** — Statistical outliers are detected and flagged so the LLM can reason about them without being misled.
3. **Data-first prompting** — The system prompt includes the full data context (schema, stats, sample rows) so the LLM is grounded.

---

## Proposed Changes

### 1. Project Setup & Dependencies

#### [NEW] requirements.txt
```
streamlit
pandas
openpyxl
groq
numpy
scipy
```

#### [NEW] .env.example
```
GROQ_API_KEY=your_groq_api_key_here
```

---

### 2. Data Processing Engine

#### [NEW] data_processor.py

Handles all CSV/Excel ingestion, profiling, and outlier detection.

**Key responsibilities:**
- **File loading**: `pd.read_csv()` / `pd.read_excel()` with encoding detection
- **Schema extraction**: Column names, dtypes, nullable counts
- **Statistical profiling** (numeric columns): min, max, mean, median, std, Q1, Q3, IQR
- **Outlier detection** (IQR method): Flag rows where numeric values fall outside `Q1 - 1.5*IQR` to `Q3 + 1.5*IQR`
- **Text profiling** (text columns): unique count, most frequent values, avg length
- **Context builder**: Generates a structured text summary of the entire dataset that gets injected into the LLM prompt

**Outlier handling strategy:**
- Outliers are **not removed** from the data
- They are **tagged** in a separate summary section
- The system prompt instructs the LLM: *"The following rows contain statistical outliers. When answering aggregate questions, note these outliers but still include them unless the user asks to exclude them."*

---

### 3. LLM Grounding Engine

#### [NEW] llm_engine.py

Manages Groq API interaction with strict grounding.

**Anti-hallucination architecture:**

1. **System prompt** contains:
   - Full schema with dtypes
   - Statistical summary per column
   - Outlier flags
   - First 50 rows of data (or full data if ≤ 50 rows) serialized as markdown table
   - For larger datasets: full data as CSV text (up to context window limit)
   - Explicit instruction: *"You are a data analyst. Answer ONLY based on the provided data. If the data does not contain information to answer a question, say 'This information is not available in the dataset.' Never invent, estimate, or extrapolate beyond what the data shows."*

2. **User prompt** is the raw question, wrapped with:
   - *"Based strictly on the data provided above, answer the following question:"*

3. **Temperature = 0** — Deterministic output for factual grounding

4. **Response validation** — Post-process to check if the LLM mentions values not present in the dataset (basic sanity check)

**Available Groq models for selection:**

| Model | ID | Best For |
|---|---|---|
| Llama 3.3 70B | `llama-3.3-70b-versatile` | Best overall quality |
| Llama 3.1 8B | `llama-3.1-8b-instant` | Fast, lightweight queries |
| Llama 4 Scout | `meta-llama/llama-4-scout-17b-16e-instruct` | Good mid-tier option |
| Qwen3 32B | `qwen/qwen3-32b` | Strong reasoning |
| GPT-OSS 120B | `openai/gpt-oss-120b` | Highest capability |
| GPT-OSS 20B | `openai/gpt-oss-20b` | Balanced performance |

---

### 4. Streamlit UI

#### [NEW] app.py

**Layout:**

```
┌─────────────────────────────────────────────┐
│  📊 Sheet Q&A — Ask Your Data Anything      │
├──────────────┬──────────────────────────────┤
│  SIDEBAR     │  MAIN AREA                   │
│              │                              │
│  🔑 API Key  │  📁 Upload CSV/Excel         │
│  🤖 Model    │  📋 Data Preview (table)     │
│  📊 Stats    │  📈 Data Profile Summary     │
│              │  ⚠️ Outlier Report            │
│              │                              │
│              │  💬 Ask a Question            │
│              │  ┌──────────────────────┐    │
│              │  │ Chat input box       │    │
│              │  └──────────────────────┘    │
│              │                              │
│              │  🤖 Answer                    │
│              │  (with grounding indicator)  │
│              │                              │
│              │  📜 Chat History              │
└──────────────┴──────────────────────────────┘
```

**Features:**
- **Sidebar**: API key input (password field), model selector dropdown, data stats summary
- **File upload**: Supports `.csv`, `.xlsx`, `.xls`
- **Data preview**: Interactive `st.dataframe` with first 100 rows
- **Data profile**: Auto-generated stats cards (row count, column count, numeric/text split, memory usage)
- **Outlier report**: Expandable section showing detected outliers per column
- **Chat interface**: `st.chat_input` + `st.chat_message` for conversational Q&A
- **Chat history**: Maintained in `st.session_state` across questions
- **Grounding indicator**: Shows "✅ Grounded" or "⚠️ Could not verify" badge on each answer

---

## Open Questions

> [!IMPORTANT]
> **Large file handling**: For very large CSVs (100k+ rows), the full data won't fit in the LLM context window. The current plan sends the first 50 rows as a sample + full statistical summary. Should I also implement a chunked search where the system scans the full dataset for relevant rows before sending to the LLM?

> [!NOTE]
> **API key storage**: The current plan uses sidebar input for the API key (session-only, never persisted). Alternatively, I can read from a `.env` file. The sidebar approach is simpler and more portable. Let me know your preference.

---

## Verification Plan

### Automated Tests
- Upload a sample CSV with known outliers and verify outlier detection
- Ask factual questions and verify answers match the data
- Ask a question that cannot be answered from the data and verify the LLM says so
- Test with both numeric-heavy and text-heavy CSVs

### Manual Verification
- Run `streamlit run app.py` and test the full flow interactively
- Verify model switching works across all Groq models
- Test edge cases: empty files, single-column files, files with all-null columns
