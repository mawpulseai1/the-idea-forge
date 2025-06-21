# alchemist_core.py

import torch
import networkx as nx
from sentence_transformers import SentenceTransformer, util
from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import spacy
import sqlite3
import json
from datetime import datetime
import requests # NEW IMPORT for making HTTP requests to Ollama

# --- Step 0: Load spaCy model ---
print("Loading spaCy model for advanced concept extraction...")
try:
    nlp_spacy = spacy.load("en_core_web_sm")
    print("spaCy model loaded successfully.")
except OSError:
    print("spaCy model 'en_core_web_sm' not found. Please run: python -m spacy download en_core_web_sm")
    print("Exiting for spaCy model download. Please restart after download.")
    exit()

# --- Step 1: Initialize the Conceptual Alchemist's core model ---
print("Initializing Conceptual Alchemist's core model...")
model_name = 'all-MiniLM-L6-v2'
device = "cuda" if torch.cuda.is_available() else "cpu"
if device == "cuda":
    print(f"CUDA GPU found: {torch.cuda.get_device_name(0)}. Setting model device to GPU.")
else:
    print("No CUDA GPU found or configured. Setting model device to CPU.")

alchemist_model = SentenceTransformer(model_name, device=device)
print("Conceptual Alchemist's core model ready.\n")

# --- Ollama Configuration (NEW) ---
OLLAMA_API_URL = "http://localhost:11434/api/generate" # Default Ollama API endpoint
OLLAMA_MODEL = "phi3:mini" # The model we pulled

def generate_llm_prompt(system_message, user_message, max_tokens=150, temperature=0.7):
    """
    Sends a request to the local Ollama API to generate a prompt.
    """
    headers = {'Content-Type': 'application/json'}
    data = {
        "model": OLLAMA_MODEL,
        "prompt": user_message, # Using 'prompt' field for direct text completion
        "system": system_message, # Ollama supports a 'system' message
        "stream": False, # We want the full response at once
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens # Max tokens for the response
        }
    }
    try:
        response = requests.post(OLLAMA_API_URL, headers=headers, json=data)
        response.raise_for_status() # Raise an exception for HTTP errors
        result = response.json()
        return result.get("response", "").strip()
    except requests.exceptions.ConnectionError:
        return "Error: Ollama server not running or unreachable. Please ensure Ollama is installed and running."
    except requests.exceptions.RequestException as e:
        return f"Error interacting with Ollama API: {e}"
    except json.JSONDecodeError:
        return "Error: Could not decode JSON response from Ollama."

# --- Step 1.5: Initialize SQLite Database ---
DATABASE = 'alchemist_sessions.db'

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_text TEXT NOT NULL,
                key_terms TEXT NOT NULL,
                prompts TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    print(f"SQLite database '{DATABASE}' initialized.")

# --- Step 2: Define the Conceptual Mapper Function (No change) ---
def map_concepts(text_input):
    doc = nlp_spacy(text_input)
    key_terms = [chunk.text.lower() for chunk in doc.noun_chunks]
    key_terms = [term for term in key_terms if len(term.split()) > 0 and len(term) > 2 and term not in ["i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them"]]
    key_terms = list(set(key_terms))
    if not key_terms:
        return nx.Graph(), []

    term_embeddings = alchemist_model.encode(key_terms, convert_to_tensor=True)
    concept_graph = nx.Graph()
    for term in key_terms:
        concept_graph.add_node(term)

    similarity_threshold = 0.4
    for i in range(len(key_terms)):
        for j in range(i + 1, len(key_terms)):
            term1 = key_terms[i]
            term2 = key_terms[j]
            similarity = util.cos_sim(term_embeddings[i], term_embeddings[j]).item()
            if similarity > similarity_threshold:
                concept_graph.add_edge(term1, term2, weight=similarity, relation="semantically similar")
    return concept_graph, key_terms

# --- Step 3: Define the Alchemical Agitation Function (UPDATED to use LLM) ---
def generate_agitation_prompts(concept_graph, key_terms_list, original_input_text):
    agitation_prompts = []
    if not key_terms_list:
        agitation_prompts.append("Please provide more descriptive text to extract concepts for agitation.")
        return agitation_prompts

    main_term = key_terms_list[0] if key_terms_list else "your core idea"

    # Determine a secondary term for 'Explore a new link' if available
    secondary_term = key_terms_list[1] if len(key_terms_list) > 1 else None

    # Agitation 1: Explore / Challenge Link (Generated by LLM)
    if secondary_term:
        system_msg = f"You are a conceptual alchemist. Your task is to challenge conventional thinking about two given concepts. Provide a single, thought-provoking question that makes the user reconsider the connection or explore an unexpected link."
        user_msg = f"Concepts: '{main_term}' and '{secondary_term}'. Question their relationship."
        llm_prompt = generate_llm_prompt(system_msg, user_msg)
        if "Error" not in llm_prompt:
            agitation_prompts.append(f"**Explore/Challenge Link (AI):** {llm_prompt}")
        else: # Fallback to template if LLM fails
             agitation_prompts.append(
                f"**Explore a new link (Template):** Consider an unexpected connection between '{main_term}' and '{secondary_term}'. How might '{main_term}' lead to '{secondary_term}' if conventional logic was suspended?"
            )
    else:
        agitation_prompts.append(f"**Explore New Link:** Not enough distinct concepts to explore new links. Consider adding more detail.")


    # Agitation 2: Deconstruct (Generated by LLM)
    system_msg = f"You are a conceptual alchemist. Your task is to help the user deconstruct a core concept. Provide a single, concise, and thought-provoking question that probes the fundamental components of '{main_term}'."
    user_msg = f"Deconstruct the concept: '{main_term}'. What are its essential parts? What if one part was removed?"
    llm_prompt = generate_llm_prompt(system_msg, user_msg)
    if "Error" not in llm_prompt:
        agitation_prompts.append(f"**Deconstruct (AI):** {llm_prompt}")
    else: # Fallback to template if LLM fails
        agitation_prompts.append(
            f"**Deconstruct (Template):** Let's deconstruct '{main_term}'. What are its absolute core components? If you removed one essential part, would it still be '{main_term}'? What would it become?"
        )

    # Agitation 3: Cross-pollinate (Generated by LLM)
    unrelated_domains = ["nature", "music", "ancient philosophy", "outer space", "childhood games", "culinary arts", "architecture", "military strategy", "biological systems", "quantum physics", "poetry", "mythology", "cybernetics", "impressionist painting"]
    import random
    random_domain = random.choice(unrelated_domains)
    system_msg = f"You are a conceptual alchemist. Your task is to inspire cross-pollination of ideas. Provide a single, creative question that helps the user connect '{main_term}' with '{random_domain}'."
    user_msg = f"How would a key concept from '{random_domain}' help you see '{main_term}' differently?"
    llm_prompt = generate_llm_prompt(system_msg, user_msg)
    if "Error" not in llm_prompt:
        agitation_prompts.append(f"**Cross-pollinate (AI):** {llm_prompt}")
    else: # Fallback to template if LLM fails
        agitation_prompts.append(
            f"**Cross-pollinate (Template):** Imagine '{main_term}' in the context of '{random_domain}'. How would a key concept from '{random_domain}' help you see '{main_term}' differently?"
        )

    # Agitation 4: Challenge Assumptions (Generated by LLM)
    system_msg = f"You are a conceptual alchemist. Your task is to challenge the user's hidden assumptions about their core idea. Provide a single, direct question about assumptions related to '{main_term}' or the problem '{original_input_text}'."
    user_msg = f"What are the implicit assumptions about '{main_term}' or '{original_input_text}'? What if the opposite were true?"
    llm_prompt = generate_llm_prompt(system_msg, user_msg)
    if "Error" not in llm_prompt:
        agitation_prompts.append(f"**Challenge Assumptions (AI):** {llm_prompt}")
    else: # Fallback to template if LLM fails
        agitation_prompts.append(
            f"**Challenge Assumptions (Template):** What core assumptions are you making about '{main_term}' or the overall problem? Try to list them out and then consider what would happen if the opposite of one of those assumptions were true."
        )

    # Agitation 5: Perspective Shifting (Generated by LLM)
    perspectives = [
        "a child seeing it for the first time",
        "an ancient philosopher",
        "a highly advanced alien civilization",
        "a minimalist designer",
        "a comedian",
        "a historian looking back from 1000 years in the future",
        "a cybersecurity expert",
        "a spiritual guru"
    ]
    random_perspective = random.choice(perspectives)
    system_msg = f"You are a conceptual alchemist. Your task is to help the user gain a new perspective. Provide a single, creative question that makes the user consider '{original_input_text}' from the viewpoint of {random_perspective}."
    user_msg = f"How would '{original_input_text}' be perceived or solved by {random_perspective}?"
    llm_prompt = generate_llm_prompt(system_msg, user_msg)
    if "Error" not in llm_prompt:
        agitation_prompts.append(f"**Shift Perspective (AI):** {llm_prompt}")
    else: # Fallback to template if LLM fails
        agitation_prompts.append(
            f"**Shift Perspective (Template):** How would '{original_input_text}' (your input) be perceived, approached, or solved by {random_perspective}?"
        )

    return agitation_prompts

# NEW Functions for SQLite interactions (no change here)
def save_session(input_text, key_terms, prompts):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    key_terms_json = json.dumps(key_terms)
    prompts_json = json.dumps(prompts)
    cursor.execute(
        'INSERT INTO sessions (input_text, key_terms, prompts) VALUES (?, ?, ?)',
        (input_text, key_terms_json, prompts_json)
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id

def get_all_sessions():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT id, input_text, timestamp FROM sessions ORDER BY timestamp DESC')
    sessions = cursor.fetchall()
    conn.close()
    return [
        {'id': s['id'], 'input_text': s['input_text'], 'timestamp': datetime.strptime(s['timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')}
        for s in sessions
    ]

# --- Step 4: Setup Flask Web Application (No significant changes here, JS handles dynamic update) ---
app = Flask(__name__)

# HTML template (no changes needed in this section as it's handled by JS)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Conceptual Alchemist</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 2em; background-color: #f0f4f8; color: #333; display: flex; min-height: 95vh; }
        .main-content { flex: 3; padding-right: 2em; display: flex; flex-direction: column; }
        .history-sidebar { flex: 1; background-color: #e0e6f6; padding: 1em; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); overflow-y: auto; max-height: 90vh; }
        .container { max-width: 800px; margin: 0 auto 2em; background-color: #fff; padding: 2em; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h1 { color: #5c678a; text-align: center; margin-bottom: 1.5em; }
        h2 { color: #5c678a; margin-top: 1.5em; border-bottom: 2px solid #dcdfe6; padding-bottom: 0.5em; }
        h3 { color: #5c678a; margin-top: 1.5em; }
        textarea { width: 100%; padding: 1em; margin-bottom: 1em; border: 1px solid #cdd4df; border-radius: 6px; box-sizing: border-box; font-size: 1.1em; resize: vertical; min-height: 100px; transition: border-color 0.3s ease; }
        textarea:focus { border-color: #7a82ab; outline: none; box-shadow: 0 0 0 2px rgba(122, 130, 171, 0.2); }
        button { display: block; width: 100%; padding: 1em; background-color: #7a82ab; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 1.1em; transition: background-color 0.3s ease; }
        button:hover { background-color: #5c678a; }
        .results { margin-top: 2em; padding: 1.5em; background-color: #e9eef6; border-left: 5px solid #5c678a; border-radius: 8px; }
        .result-item { margin-bottom: 1em; }
        .results ul { list-style: none; padding: 0; }
        .results li { background-color: #f0f4fb; margin-bottom: 0.8em; padding: 1em; border-radius: 6px; border: 1px solid #dcdfe6; }
        strong { color: #333; }
        .footer { text-align: center; margin-top: auto; padding-top: 2em; font-size: 0.8em; color: #777; }
        .session-item { background-color: #f9f9f9; border: 1px solid #eee; padding: 0.8em; margin-bottom: 0.5em; border-radius: 4px; }
        .session-item a { text-decoration: none; color: #5c678a; font-weight: bold; }
        .session-item a:hover { text-decoration: underline; }
        .session-item small { display: block; color: #777; margin-top: 0.3em; }
        #loading-spinner {
            display: none; /* Hidden by default */
            text-align: center;
            margin-top: 1em;
            font-size: 1.2em;
            color: #7a82ab;
        }
    </style>
</head>
<body>
    <div class="main-content">
        <div class="container">
            <h1>The Conceptual Alchemist</h1>
            <p>Enter your idea, problem, or concept below, and let the Alchemist help you discover new perspectives and unlock breakthrough insights.</p>
            <form id="alchemist-form">
                <textarea name="user_input" id="user_input" rows="6" placeholder="E.g., 'How to foster sustainable energy solutions in urban environments?' or 'The challenge of balancing privacy and security in digital communication.'">{{ user_input }}</textarea>
                <button type="submit">Alchemize My Concept!</button>
            </form>

            <div id="loading-spinner">Alchemizing... Please wait.</div>

            <div id="results-area" class="results" style="display: none;">
                <h2>Alchemical Agitations:</h2>
                <ul id="prompts-list"></ul>
                <h3>Extracted Key Terms:</h3>
                <p id="key-terms-display"></p>
            </div>
        </div>
        <div class="footer">
            <p>Powered by Your Conceptual Alchemist AI</p>
        </div>
    </div>

    <div class="history-sidebar">
        <h2>Session History</h2>
        <div id="session-history-list">
        {% if sessions %}
            {% for session in sessions %}
                <div class="session-item">
                    <a href="{{ url_for('view_session', session_id=session.id) }}">{{ session.input_text[:50] }}{% if session.input_text|length > 50 %}...{% endif %}</a>
                    <small>{{ session.timestamp }}</small>
                </div>
            {% endfor %}
        {% else %}
            <p>No past sessions yet. Start Alchemizing!</p>
        {% endif %}
        </div>
    </div>

    <script>
        document.getElementById('alchemist-form').addEventListener('submit', async function(event) {
            event.preventDefault();

            const userInput = document.getElementById('user_input').value;
            const resultsArea = document.getElementById('results-area');
            const promptsList = document.getElementById('prompts-list');
            const keyTermsDisplay = document.getElementById('key-terms-display');
            const loadingSpinner = document.getElementById('loading-spinner');
            const sessionHistoryList = document.getElementById('session-history-list');

            promptsList.innerHTML = '';
            keyTermsDisplay.innerHTML = '';
            resultsArea.style.display = 'none';
            loadingSpinner.style.display = 'block';

            try {
                const response = await fetch('/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ user_input: userInput })
                });

                const data = await response.json();

                loadingSpinner.style.display = 'none';

                if (data.prompts && data.key_terms) {
                    data.prompts.forEach(prompt => {
                        const li = document.createElement('li');
                        li.innerHTML = prompt;
                        promptsList.appendChild(li);
                    });
                    keyTermsDisplay.textContent = data.key_terms.join(', ');
                    resultsArea.style.display = 'block';

                    const newSessionHtml = `
    <div class="session-item">
        <a href="/session/${data.new_session_id}">${data.input_text.substring(0, 50)}${data.input_text.length > 50 ? '...' : ''}</a>
        <small>${data.timestamp}</small>
    </div>`;
sessionHistoryList.insertAdjacentHTML('afterbegin', newSessionHtml);
resultsArea.scrollIntoView({ behavior: 'smooth' });
                } else {
                    promptsList.innerHTML = `<li><p>${data.message || 'No concepts extracted or error occurred.'}</p></li>`;
                    resultsArea.style.display = 'block';
                }

            } catch (error) {
                console.error('Error:', error);
                loadingSpinner.style.display = 'none';
                resultsArea.style.display = 'block';
                promptsList.innerHTML = `<li><p style="color: red;">An error occurred while processing your request. Please ensure Ollama is running and the 'phi3:mini' model is pulled. Error details: ${error.message}</p></li>`;
            }
        });
    </script>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = request.get_json()
        user_input = data.get("user_input", "")

        if not user_input:
            return jsonify({"message": "Please provide input text."}), 400

        concept_graph, extracted_terms = map_concepts(user_input)

        # --- CRITICAL CHANGE: Call the LLM-powered prompt generation ---
        prompts = generate_agitation_prompts(concept_graph, extracted_terms, user_input)

        new_session_id = save_session(user_input, extracted_terms, prompts)

        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        return jsonify({
            "prompts": prompts,
            "key_terms": extracted_terms,
            "new_session_id": new_session_id,
            "input_text": user_input,
            "timestamp": current_timestamp
        })

    user_input = ""
    prompts = []
    key_terms = []
    sessions = get_all_sessions()

    return render_template_string(HTML_TEMPLATE, user_input=user_input, prompts=prompts, key_terms=key_terms,
                                  sessions=sessions)


@app.route("/session/<int:session_id>")
def view_session(session_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT input_text, key_terms, prompts, timestamp FROM sessions WHERE id = ?', (session_id,))
    session = cursor.fetchone()
    conn.close()

    if session:
        input_text, key_terms_json, prompts_json, timestamp_str = session
        key_terms = json.loads(key_terms_json)
        prompts = json.loads(prompts_json)

        timestamp_obj = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        formatted_timestamp = timestamp_obj.strftime('%Y-%m-%d %H:%M')

        detail_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Session {session_id}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 2em; background-color: #f0f4f8; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; background-color: #fff; padding: 2em; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
                h1, h2 {{ color: #5c678a; margin-bottom: 0.8em; border-bottom: 2px solid #dcdfe6; padding-bottom: 0.5em; }}
                .result-item {{ margin-bottom: 1em; padding: 1em; border-left: 5px solid #7a82ab; background-color: #e9eef6; border-radius: 6px;}}
                strong {{ color: #333; }}
                .back-link {{ display: inline-block; margin-bottom: 1.5em; color: #7a82ab; text-decoration: none; font-weight: bold; }}
                .back-link:hover {{ text-decoration: underline; }}
                p {{ margin-bottom: 0.5em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <a href="{url_for('index')}" class="back-link">&larr; Back to Alchemist Main</a>
                <h1>Session Details (ID: {session_id})</h1>
                <p><strong>Input:</strong> {input_text}</p>
                <p><strong>Date:</strong> {formatted_timestamp}</p>
                <h2>Key Terms:</h2>
                <p>{', '.join(key_terms)}</p>
                <h2>Alchemical Agitations:</h2>
                {''.join([f'<div class="result-item"><p>{prompt}</p></div>' for prompt in prompts])}
            </div>
        </body>
        </html>
        """
        return render_template_string(detail_html)
    return "Session not found.", 404


# --- Step 5: Run the Flask App ---
if __name__ == "__main__":
    init_db()
    print("\nStarting Flask web server...")
    print("Open your web browser and go to: http://127.0.0.1:5000/")
    app.run(debug=True, use_reloader=False)