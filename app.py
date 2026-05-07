import streamlit as st
import pandas as pd
from data_processor import load_file, build_full_context, get_profile_cards, detect_outliers
from llm_engine import query_dataframe, AVAILABLE_MODELS

# ---------------------------------------------------------------------------
# Page Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Grounded Sheet Q&A",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Session State
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "df" not in st.session_state:
    st.session_state.df = None
if "data_context" not in st.session_state:
    st.session_state.data_context = ""
if "profile_cards" not in st.session_state:
    st.session_state.profile_cards = {}
if "outlier_report" not in st.session_state:
    st.session_state.outlier_report = ""

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("📊 Sheet Q&A Config")
    
    provider_choice = st.radio("LLM Provider", ["Groq (Cloud)", "Ollama (Local)"])
    
    if provider_choice == "Groq (Cloud)":
        provider_val = "groq"
        api_key = st.text_input("Groq API Key", type="password", help="Get this from console.groq.com")
        selected_model_name = st.selectbox(
            "Select Model",
            options=list(AVAILABLE_MODELS.keys()),
            index=0
        )
        selected_model_id = AVAILABLE_MODELS[selected_model_name]
    else:
        provider_val = "local"
        api_key = "local_dummy"
        st.info("Make sure Ollama is running locally (e.g. `ollama serve`).")
        selected_model_id = st.text_input("Ollama Model Name", value="llama3", help="e.g. llama3, qwen2.5-coder:7b")
    
    st.divider()
    
    st.subheader("📁 Upload Data")
    uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
    
    if uploaded_file is not None:
        try:
            with st.spinner("Loading and profiling data..."):
                # Only process if it's a new file
                if st.session_state.df is None or getattr(st.session_state, 'last_uploaded', '') != uploaded_file.name:
                    df = load_file(uploaded_file)
                    st.session_state.df = df
                    st.session_state.data_context = build_full_context(df)
                    st.session_state.profile_cards = get_profile_cards(df)
                    st.session_state.outlier_report, _ = detect_outliers(df)
                    st.session_state.messages = []  # Reset chat for new file
                    st.session_state.last_uploaded = uploaded_file.name
            st.success("Data loaded successfully!")
        except Exception as e:
            st.error(f"Error loading file: {e}")

    # Display stats if data is loaded
    if st.session_state.df is not None:
        st.divider()
        st.subheader("📈 Dataset Stats")
        cards = st.session_state.profile_cards
        
        col1, col2 = st.columns(2)
        col1.metric("Rows", f"{cards['rows']:,}")
        col2.metric("Columns", f"{cards['columns']:,}")
        
        col3, col4 = st.columns(2)
        col3.metric("Numeric Cols", cards['numeric_cols'])
        col4.metric("Text Cols", cards['text_cols'])
        
        col5, col6 = st.columns(2)
        col5.metric("Outlier Cells", f"{cards['total_outliers']:,}")
        col6.metric("Memory", f"{cards['memory_mb']} MB")
        
        if st.button("Clear Data & Chat"):
            st.session_state.df = None
            st.session_state.messages = []
            st.rerun()

# ---------------------------------------------------------------------------
# Main Layout
# ---------------------------------------------------------------------------
st.title("Grounded Sheet Q&A")
st.markdown("Ask natural language questions about your CSV/Excel data. The LLM generates Python code to find the exact answer, ensuring zero hallucination.")

if st.session_state.df is None:
    st.info("👈 Please upload a dataset in the sidebar to get started.")
    st.stop()

# ---------------------------------------------------------------------------
# Data Preview Expander
# ---------------------------------------------------------------------------
with st.expander("🔍 View Data Preview & Schema", expanded=False):
    st.dataframe(st.session_state.df.head(100), use_container_width=True)
    st.markdown("### Schema & Context sent to LLM:")
    st.text(st.session_state.data_context)

with st.expander("⚠️ Outlier Report", expanded=False):
    st.text(st.session_state.outlier_report)

st.divider()

# ---------------------------------------------------------------------------
# Chat Interface
# ---------------------------------------------------------------------------
st.subheader("💬 Ask Questions")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display the code and result if available (for assistant messages)
        if message["role"] == "assistant" and "code" in message:
            with st.expander("🛠️ View execution details"):
                st.markdown("**Generated Code:**")
                st.code(message["code"], language="python")
                st.markdown("**Raw Result:**")
                st.text(message["raw_result"])

# Chat Input
if prompt := st.chat_input("Ask a question about the dataset..."):
    if provider_val == "groq" and not api_key:
        st.error("Please enter your Groq API key in the sidebar.")
        st.stop()
        
    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner("Generating code & analyzing data..."):
            
            # Format chat history for the API
            api_history = [
                {"role": m["role"], "content": m["content"]} 
                for m in st.session_state.messages[:-1]
            ]
            
            response = query_dataframe(
                question=prompt,
                df=st.session_state.df,
                data_context=st.session_state.data_context,
                api_key=api_key,
                model_id=selected_model_id,
                chat_history=api_history,
                provider=provider_val
            )
            
            if response["success"]:
                st.markdown(response["answer"])
                st.caption("✅ Grounded via code execution")
                
                with st.expander("🛠️ View execution details"):
                    st.markdown("**Generated Code:**")
                    st.code(response["generated_code"], language="python")
                    st.markdown("**Raw Result:**")
                    st.text(response["raw_result"])
                    
                # Save to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response["answer"],
                    "code": response["generated_code"],
                    "raw_result": response["raw_result"]
                })
            else:
                st.error("Failed to answer the question.")
                st.markdown(response["error"])
                if response["generated_code"]:
                    with st.expander("Failed Code"):
                        st.code(response["generated_code"], language="python")
