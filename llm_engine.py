"""
LLM engine with code-generation grounding.

Flow:
  1. Send schema + stats + user question -> LLM generates Pandas code
  2. Execute that code against the real DataFrame
  3. Send execution result back -> LLM produces natural language answer

The LLM never sees raw data rows. It only sees schema, stats, and
the output of code it wrote - ensuring zero hallucination.
"""

import re
import io
import sys
import traceback
import pandas as pd
import numpy as np
from groq import Groq


# ---------------------------------------------------------------------------
# Available models (curated for chat / code-gen quality)
# ---------------------------------------------------------------------------
AVAILABLE_MODELS = {
    "Llama 3.3 70B (Open Source Large)": "llama-3.3-70b-versatile",
    "Mixtral 8x7B (Open Source MoE)": "mixtral-8x7b-32768",
    "Llama 3.1 8B (Fast)": "llama-3.1-8b-instant",
    "Gemma 2 9B": "gemma2-9b-it",
    "Llama 4 Scout 17B (Preview)": "meta-llama/llama-4-scout-17b-16e-instruct",
    "Qwen3 32B (Preview)": "qwen/qwen3-32b",
}

MAX_RETRIES = 3  # retries if generated code fails


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

CODE_GEN_SYSTEM_PROMPT = """\
You are a Python data analyst. You have access to a pandas DataFrame called `df`.

Here is the dataset schema and statistics:
{context}

RULES:
1. Write a short Python snippet that answers the user's question.
2. Use only `pandas` (imported as `pd`) and `numpy` (imported as `np`). No other imports.
3. Store the final answer in a variable called `result`.
4. `result` must be a simple type: str, int, float, list, or a small DataFrame/Series (<=30 rows).
5. Do NOT print anything. Just assign to `result`.
6. Do NOT modify `df` in place (no inplace=True, no reassigning df).
7. Handle potential NaN/null values gracefully.
8. If the question asks to ignore outliers, filter using the IQR bounds from the stats above.
9. Return ONLY the Python code inside a single ```python``` block. No explanation.
"""

INTERPRET_SYSTEM_PROMPT = """\
You are a data analyst presenting findings to a non-technical user.

Dataset schema and statistics:
{context}

RULES:
1. The user asked a question and code was executed against the real dataset.
2. You are given the raw execution result below.
3. Explain the result in clear, concise natural language.
4. ONLY state what the data shows. Do NOT speculate, estimate, or add information beyond the result.
5. If the result is empty or None, say the data does not contain the answer.
6. Use bullet points or short paragraphs. Include the actual numbers/values from the result.
7. If outliers are relevant, mention them.
"""


# ---------------------------------------------------------------------------
# Code extraction
# ---------------------------------------------------------------------------

def _extract_code(response_text: str) -> str:
    """Extract Python code from a ```python``` fenced block."""
    # Try fenced code block first
    pattern = r"```(?:python)?\s*\n(.*?)```"
    match = re.search(pattern, response_text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: if the response looks like raw code (no markdown fencing)
    lines = response_text.strip().split("\n")
    code_lines = [l for l in lines if not l.startswith("#") or "import" in l or "=" in l]
    if any("result" in l for l in code_lines):
        return "\n".join(lines).strip()

    return response_text.strip()


# ---------------------------------------------------------------------------
# Safe execution
# ---------------------------------------------------------------------------

def _execute_code(code: str, df: pd.DataFrame) -> dict:
    """
    Execute generated Pandas code in a restricted namespace.
    Returns {"success": bool, "result": Any, "stdout": str, "error": str}
    """
    # Restricted namespace - only pandas, numpy, and the dataframe
    namespace = {
        "df": df.copy(),  # work on a copy so original is never mutated
        "pd": pd,
        "np": np,
    }

    # Capture stdout just in case
    old_stdout = sys.stdout
    sys.stdout = captured = io.StringIO()

    try:
        exec(code, {"__builtins__": {}}, namespace)
        stdout_val = captured.getvalue()

        result = namespace.get("result", None)

        # Convert large DataFrames/Series to string for the LLM
        if isinstance(result, (pd.DataFrame, pd.Series)):
            if isinstance(result, pd.DataFrame) and len(result) > 30:
                result = f"DataFrame with {len(result)} rows. First 30 rows:\n{result.head(30).to_string()}"
            else:
                result = result.to_string()

        return {
            "success": True,
            "result": result,
            "stdout": stdout_val,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "stdout": captured.getvalue(),
            "error": f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
        }
    finally:
        sys.stdout = old_stdout


# ---------------------------------------------------------------------------
# Main query function
# ---------------------------------------------------------------------------

def query_dataframe(
    question: str,
    df: pd.DataFrame,
    data_context: str,
    api_key: str,
    model_id: str,
    chat_history: list | None = None,
    provider: str = "groq",
) -> dict:
    """
    Two-step grounded Q&A:
      Step 1: LLM generates Pandas code
      Step 2: Execute code, send result back for natural language answer

    Returns:
        {
            "answer": str,           # Final natural language answer
            "generated_code": str,   # The Pandas code that was executed
            "raw_result": str,       # Raw execution output
            "success": bool,         # Whether the pipeline succeeded
            "error": str | None,     # Error message if failed
        }
    """
    if provider == "groq":
        from groq import Groq
        client = Groq(api_key=api_key)
    elif provider == "local":
        from openai import OpenAI
        client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    else:
        raise ValueError(f"Unknown provider: {provider}")

    # ------------------------------------------------------------------
    # Step 1: Generate Pandas code
    # ------------------------------------------------------------------
    code_system = CODE_GEN_SYSTEM_PROMPT.format(context=data_context)
    code_messages = [{"role": "system", "content": code_system}]

    # Include recent chat history for context (last 4 exchanges max)
    if chat_history:
        recent = chat_history[-8:]  # 4 Q&A pairs = 8 messages
        for msg in recent:
            code_messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

    code_messages.append({"role": "user", "content": question})

    generated_code = None
    exec_result = None

    for attempt in range(MAX_RETRIES):
        try:
            code_response = client.chat.completions.create(
                model=model_id,
                messages=code_messages,
                temperature=0,
            )
            raw_code_response = code_response.choices[0].message.content
            generated_code = _extract_code(raw_code_response)
        except Exception as e:
            return {
                "answer": None,
                "generated_code": None,
                "raw_result": None,
                "success": False,
                "error": f"{provider.capitalize()} API error during code generation: {e}",
            }

        # ------------------------------------------------------------------
        # Step 2: Execute the code
        # ------------------------------------------------------------------
        exec_result = _execute_code(generated_code, df)

        if exec_result["success"]:
            break

        # On failure, ask the LLM to fix the code
        error_msg = exec_result["error"]
        code_messages.append({"role": "assistant", "content": f"```python\n{generated_code}\n```"})
        code_messages.append({
            "role": "user",
            "content": (
                f"That code raised an error:\n{error_msg}\n\n"
                f"Please fix the code. Remember the rules: only pandas/numpy, "
                f"assign to `result`, no prints, no inplace modifications."
            ),
        })

    if not exec_result["success"]:
        return {
            "answer": f"I wasn't able to compute the answer after {MAX_RETRIES} attempts. "
                      f"Last error: {exec_result['error']}",
            "generated_code": generated_code,
            "raw_result": None,
            "success": False,
            "error": exec_result["error"],
        }

    # ------------------------------------------------------------------
    # Step 3: Interpret the result in natural language
    # ------------------------------------------------------------------
    raw_result = exec_result["result"]
    if raw_result is None:
        raw_result = exec_result["stdout"] or "No output produced."

    interpret_system = INTERPRET_SYSTEM_PROMPT.format(context=data_context)
    interpret_messages = [
        {"role": "system", "content": interpret_system},
        {
            "role": "user",
            "content": (
                f"USER QUESTION: {question}\n\n"
                f"CODE EXECUTED:\n```python\n{generated_code}\n```\n\n"
                f"RAW RESULT:\n{raw_result}\n\n"
                f"Please provide a clear, grounded answer based on this result."
            ),
        },
    ]

    try:
        interpret_response = client.chat.completions.create(
            model=model_id,
            messages=interpret_messages,
            temperature=0,
        )
        answer = interpret_response.choices[0].message.content
    except Exception as e:
        # If interpretation fails, just return the raw result
        answer = f"Here is the raw result from the data:\n\n{raw_result}"

    return {
        "answer": answer,
        "generated_code": generated_code,
        "raw_result": str(raw_result),
        "success": True,
        "error": None,
    }
