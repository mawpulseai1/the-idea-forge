# alchemist_core.py

import torch
import networkx as nx
from sentence_transformers import SentenceTransformer, util
from flask import Flask, render_template_string, request, redirect, url_for, jsonify, session as flask_session
import spacy
import sqlite3
import json
from datetime import datetime
import requests
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template_string, render_template, request, redirect, url_for, jsonify, \
    session as flask_session

# --- Step 0: Load spaCy model ---
print("Loading spaCy model for advanced concept extraction...")
try:
    nlp_spacy = spacy.load("en_core_web_sm")
    print("spaCy model loaded successfully.")
except OSError:
    print("spaCy model 'en_core_web_sm' not found. Please run: python -m spacy download en_core_web_sm")
    print("Exiting for spaCy model download. Please restart after download.")
    exit()

# --- Step 1: Initialize The Idea Forge's core model ---
print("Initializing The Idea Forge's core model...")
model_name = 'all-MiniLM-L6-v2'
device = "cuda" if torch.cuda.is_available() else "cpu"
if device == "cuda":
    print(f"CUDA GPU found: {torch.cuda.get_device_name(0)}. Setting model device to GPU.")
else:
    print("No CUDA GPU found or configured. Setting model device to CPU.")

alchemist_model = SentenceTransformer(model_name, device=device)
print("The Idea Forge's core model ready.\n")

# --- Ollama Configuration ---
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi3:mini"


def generate_llm_prompt(system_message, user_message, max_tokens=150, temperature=0.7):
    """
    Sends a request to the local Ollama API to generate a prompt.
    """
    headers = {'Content-Type': 'application/json'}
    data = {
        "model": OLLAMA_MODEL,
        "prompt": user_message,
        "system": system_message,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens
        }
    }
    try:
        response = requests.post(OLLAMA_API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result.get("response", "").strip()
    except requests.exceptions.ConnectionError:
        return "Error: Ollama server not running or unreachable. Please ensure Ollama is installed and running."
    except requests.exceptions.RequestException as e:
        return f"Error interacting with Ollama API: {e}"
    except json.JSONDecodeError:
        return "Error: Could not decode JSON response from Ollama."


# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.login_view = 'login'


# User Model
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        if user_data:
            return User(user_data[0], user_data[1], user_data[2])
        return None

    @staticmethod
    def find_by_username(username):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        conn.close()
        if user_data:
            return User(user_data[0], user_data[1], user_data[2])
        return None


@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))


# --- Step 1.5: Initialize SQLite Database (Simplified) ---
DATABASE = 'alchemist_sessions.db'


def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
             CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE NOT NULL,
                 password TEXT NOT NULL
             )
         ''')
        cursor.execute('''
             CREATE TABLE IF NOT EXISTS sessions (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 input_text TEXT NOT NULL,
                 key_terms TEXT,
                 prompts TEXT,
                 graph_data TEXT,
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY (user_id) REFERENCES users (id)
             )
         ''')
        cursor.execute('''
             CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id);
         ''')
        conn.commit()
    print(f"SQLite database '{DATABASE}' initialized/updated with user and sessions tables.")


# --- Step 2: Define the Conceptual Mapper Function ---
def map_concepts(text_input):
    doc = nlp_spacy(text_input)
    key_terms = [chunk.text.lower() for chunk in doc.noun_chunks]
    key_terms = [term for term in key_terms if
                 len(term.split()) > 0 and len(term) > 2 and term not in ["i", "you", "he", "she", "it", "we", "they",
                                                                          "me", "him", "her", "us", "them"]]
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


# --- Convert networkx graph to vis.js format ---
def convert_graph_to_vis_data(concept_graph):
    nodes = []
    edges = []
    node_id_map = {node: i for i, node in enumerate(concept_graph.nodes())}

    for node, data in concept_graph.nodes(data=True):
        nodes.append({
            'id': node_id_map[node],
            'label': node,
            'title': node,
            'font': {'size': 16},
            'shape': 'dot',
            'color': {
                'background': '#8d99ae',
                'border': '#2b2d42',
                'highlight': {'background': '#edf2f4', 'border': '#ef233c'},
                'hover': {'background': '#edf2f4', 'border': '#ef233c'}
            }
        })

    for u, v, data in concept_graph.edges(data=True):
        edge_width = max(1, int(data.get('weight', 0) * 4) + 1)
        edges.append({
            'from': node_id_map[u],
            'to': node_id_map[v],
            'title': f"Similarity: {data.get('weight', 0):.2f}",
            'width': edge_width,
            'color': {
                'color': '#8d99ae',
                'highlight': '#ef233c',
                'hover': '#ef233c'
            }
        })
    return {'nodes': nodes, 'edges': edges}


# --- Step 3: Define the Provocative Prompt Generation Function ---
def generate_agitation_prompts(concept_graph, key_terms_list, original_input_text):
    agitation_prompts = []
    if not key_terms_list:
        agitation_prompts.append("Please provide more descriptive text to extract concepts for prompt generation.")
        return agitation_prompts

    main_term = key_terms_list[0] if key_terms_list else "your core idea"

    secondary_term = key_terms_list[1] if len(key_terms_list) > 1 else None

    # Agitation 1: Explore / Challenge Link
    if secondary_term:
        system_msg_link = (
            f"You are a conceptual alchemist and an expert in lateral thinking. "
            f"Your task is to forge a single, profound, and counter-intuitive question "
            f"that either reveals an unexpected connection between two concepts or "
            f"challenges a seemingly obvious link. The question should provoke deep, non-linear thought."
        )
        user_msg_link = (
            f"Given concepts: '{main_term}' and '{secondary_term}'. "
            f"Formulate a question exploring a hidden or paradoxical link between them.\n\n"
            f"Example 1: Concepts 'Internet' and 'Privacy'. "
            f"Question: 'How does the relentless pursuit of digital privacy inadvertently lead to its erosion, creating a surveillance paradox?'\n"
            f"Example 2: Concepts 'Growth' and 'Stagnation'. "
            f"Question: 'In what ways is apparent stagnation a necessary precursor to true, sustainable growth, rather than its antithesis?'"
        )
        llm_prompt_link = generate_llm_prompt(system_msg_link, user_msg_link)
        if "Error" not in llm_prompt_link:
            agitation_prompts.append(f"<b>Explore a New Link:</b> {llm_prompt_link}")
        else:
            agitation_prompts.append(
                f"<b>Explore a New Link (Template):</b> Consider an unexpected connection between '{main_term}' and '{secondary_term}'. How might '{main_term}' lead to '{secondary_term}' if conventional logic was suspended?"
            )
    else:
        agitation_prompts.append(
            f"<b>Explore a New Link:</b> Not enough distinct concepts to explore new links. Consider adding more detail.")

    # Agitation 2: Deconstruct
    system_msg_deconstruct = (
        f"You are a conceptual alchemist specializing in radical deconstruction. "
        f"Your task is to formulate a single, incisive question that forces the user to dissect "
        f"the fundamental components, assumptions, or boundaries of a given concept. "
        f"The question should challenge the very definition or existence of the concept itself."
    )
    user_msg_deconstruct = (
        f"Deconstruct the concept: '{main_term}'. What are its essential, indivisible parts? "
        f"What happens if a core component is removed or fundamentally altered?\n\n"
        f"Example 1: Concept 'Justice'. "
        f"Question: 'If the outcome of a just system is always subjective, is justice a fixed principle or merely a continuous, unattainable pursuit?'\n"
        f"Example 2: Concept 'Decision'. "
        f"Question: 'If every decision is ultimately influenced by a cascade of prior unconscious biases, can true free will in decision-making ever truly exist?'"
    )
    llm_prompt_deconstruct = generate_llm_prompt(system_msg_deconstruct, user_msg_deconstruct)
    if "Error" not in llm_prompt_deconstruct:
        agitation_prompts.append(f"<b>Deconstruct This:</b> {llm_prompt_deconstruct}")
    else:
        agitation_prompts.append(
            f"<b>Deconstruct This (Template):</b> Let's deconstruct '{main_term}'. What are its absolute core components? If you removed one essential part, would it still be '{main_term}'? What would it become?"
        )

    # Agitation 3: Cross-pollinate
    unrelated_domains = [
        "the intricate dance of subatomic particles",
        "the evolutionary strategies of deep-sea organisms",
        "the composition of classical symphonies",
        "the logic gates within a quantum computer",
        "ancient martial arts philosophy",
        "the principles of surrealist art",
        "the complex rules of a board game",
        "the formation of celestial bodies",
        "the internal mechanisms of a clock",
        "the growth patterns of fungi"
    ]
    import random
    random_domain = random.choice(unrelated_domains)
    system_msg_crosspollinate = (
        f"You are a conceptual alchemist specializing in radical ideation through cross-domain pollination. "
        f"Your task is to generate a single, highly creative and thought-provoking question that "
        f"bridges the concept '{main_term}' with a seemingly unrelated domain: '{random_domain}'. "
        f"The question should reveal unexpected insights or solutions."
    )
    user_msg_crosspollinate = (
        f"Connect '{main_term}' with '{random_domain}'. What new perspective emerges when applying principles from '{random_domain}' to '{main_term}'?\n\n"
        f"Example 1: Concept 'Innovation', Domain 'Fungal Networks'. "
        f"Question: 'If innovation were to mimic the distributed, resilient, and adaptive growth of a fungal network, how would organizations restructure to optimize for pervasive knowledge sharing and emergent solutions?'\n"
        f"Example 2: Concept 'Decision-making', Domain 'Classical Music Composition'. "
        f"Question: 'How might the principles of counterpoint and harmony in classical music composition offer a framework for balancing conflicting priorities in complex decision-making processes?'"
    )
    llm_prompt_crosspollinate = generate_llm_prompt(system_msg_crosspollinate, user_msg_crosspollinate)
    if "Error" not in llm_prompt_crosspollinate:
        agitation_prompts.append(f"<b>Cross-Pollinate Ideas:</b> {llm_prompt_crosspollinate}")
    else:
        agitation_prompts.append(
            f"<b>Cross-Pollinate Ideas (Template):</b> Imagine '{main_term}' in the context of '{random_domain}'. How would a key concept from '{random_domain}' help you see '{main_term}' differently?"
        )

    # Agitation 4: Challenge Assumptions
    system_msg_assumptions = (
        f"You are a conceptual alchemist dedicated to uncovering hidden biases and unquestioned truths. "
        f"Your task is to formulate a single, direct, and unsettling question that forces the user to "
        f"identify and confront the fundamental, often implicit, assumptions underlying their input "
        f"or the core concept. The question should propose a radical counter-factual or alternative reality."
    )
    user_msg_assumptions = (
        f"What are the unstated assumptions behind '{main_term}' or the problem '{original_input_text}'? "
        f"What if the most foundational assumption were completely false?\n\n"
        f"Example 1: Concept 'Education'. "
        f"Question: 'If the primary purpose of education was not knowledge transfer but the cultivation of radical uncertainty, how would learning environments transform?'\n"
        f"Example 2: Concept 'Success'. "
        f"Question: 'What if the very metric by which we define 'success' was inherently designed to perpetuate systemic inequities, making true universal success impossible?'"
    )
    llm_prompt_assumptions = generate_llm_prompt(system_msg_assumptions, user_msg_assumptions)
    if "Error" not in llm_prompt_assumptions:
        agitation_prompts.append(f"<b>Challenge Assumptions:</b> {llm_prompt_assumptions}")
    else:
        agitation_prompts.append(
            f"<b>Challenge Assumptions (Template):</b> What core assumptions are you making about '{main_term}' or the overall problem? Try to list them out and then consider what would happen if the opposite of one of those assumptions were true."
        )

    # Agitation 5: Perspective Shifting
    perspectives = [
        "a time-traveling anthropologist from 3077",
        "a sentient quantum AI managing a planetary ecosystem",
        "a deep-sea vent microbiologist observing a new life form",
        "a minimalist architect designing a space colony",
        "a performance artist interpreting the concept through dance",
        "a disillusioned philosopher from the digital dark ages",
        "a wise elder from a pre-industrial indigenous tribe",
        "a rogue neuroscientist experimenting with dream states"
    ]
    random_perspective = random.choice(perspectives)
    system_msg_perspective = (
        f"You are a conceptual alchemist facilitating radical empathy and reframing. "
        f"Your task is to generate a single, imaginative question that forces the user to "
        f"view their concept or problem '{original_input_text}' through the highly unique "
        f"lens of a specific, unconventional perspective: '{random_perspective}'. "
        f"The question should reveal unexpected values, priorities, or solutions."
    )
    user_msg_perspective = (
        f"How would '{original_input_text}' be understood, solved, or transformed by {random_perspective}?\n\n"
        f"Example 1: Problem 'Urban Traffic Congestion', Perspective 'a migratory bird observing from above'. "
        f"Question: 'If urban traffic congestion was viewed through the eyes of a migratory bird, what fundamental, unseen patterns of flow and bottleneck would become apparent, suggesting solutions entirely external to human infrastructure?'\n"
        f"Example 2: Concept 'Data Security', Perspective 'a medieval cryptographer protecting ancient scrolls'. "
        f"Question: 'How might the principles of counterpoint and harmony in classical music composition offer a framework for balancing conflicting priorities in complex decision-making processes?'"
    )
    llm_prompt_perspective = generate_llm_prompt(system_msg_perspective, user_msg_perspective)
    if "Error" not in llm_prompt_perspective:
        agitation_prompts.append(f"<b>Shift Your Perspective:</b> {llm_prompt_perspective}")
    else:
        agitation_prompts.append(
            f"<b>Shift Your Perspective (Template):</b> How would '{original_input_text}' (your input) be perceived, approached, or solved by {random_perspective}?"
        )

    return agitation_prompts


# --- SQLite Interactions ---
def save_session(user_id, input_text, key_terms, prompts, graph_data_json):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    key_terms_json = json.dumps(key_terms)
    prompts_json = json.dumps(prompts)

    cursor.execute(
        'INSERT INTO sessions (user_id, input_text, key_terms, prompts, graph_data) VALUES (?, ?, ?, ?, ?)',
        (user_id, input_text, key_terms_json, prompts_json, graph_data_json)
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def delete_session_from_db(session_id, user_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sessions WHERE id = ? AND user_id = ?', (session_id, user_id))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0


def get_all_sessions(user_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT id, input_text, timestamp FROM sessions WHERE user_id = ? ORDER BY timestamp DESC',
                   (user_id,))
    sessions = cursor.fetchall()
    conn.close()
    return [
        {'id': s['id'], 'input_text': s['input_text'],
         'timestamp': datetime.strptime(s['timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')}
        for s in sessions
    ]


def get_last_session_data(user_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        'SELECT input_text, key_terms, prompts, graph_data FROM sessions WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1',
        (user_id,))
    last_session = cursor.fetchone()
    conn.close()

    if last_session:
        return {
            'input_text': last_session['input_text'],
            'key_terms': json.loads(last_session['key_terms']),
            'prompts': json.loads(last_session['prompts']),
            'graph_data': json.loads(last_session['graph_data']) if last_session['graph_data'] else {'nodes': [],
                                                                                                     'edges': []}
        }
    return None


# --- Step 4: Setup Flask Web Application ---
app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here'
login_manager.init_app(app)

# HTML template
LOGIN_REGISTER_HTML = """
 <!DOCTYPE html>
 <html lang="en">
 <head>
     <meta charset="UTF-8">
     <meta name="viewport" content="width=device-width, initial-scale=1.0">
     <title>The Idea Forge</title>
     <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
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
         .session-item { background-color: #f9f9f9; border: 1px solid #eee; padding: 0.8em; margin-bottom: 0.5em; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
         .session-item a { text-decoration: none; color: #5c678a; font-weight: bold; flex-grow: 1; }
         .session-item a:hover { text-decoration: underline; }
         .delete-btn { background-color: #dc3545; color: white; border: none; border-radius: 4px; padding: 0.4em 0.7em; cursor: pointer; font-size: 0.8em; transition: background-color 0.3s ease; margin-left: 10px; }
         .delete-btn:hover { background-color: #c82333; }
         #loading-spinner {
             display: none;
             text-align: center;
             margin-top: 1em;
             font-size: 1.2em;
             color: #7a82ab;
         }
         .user-info { display: flex; justify-content: space-between; align-items: center; padding: 0.5em 0; border-bottom: 1px solid #dcdfe6; margin-bottom: 1em; }
         .user-info p { margin: 0; font-weight: bold; color: #5c678a; }
         .user-info a { color: #7a82ab; text-decoration: none; font-weight: normal; margin-left: 1em; }
         .user-info a:hover { text-decoration: underline; }
         #conceptual-graph {
             width: 100%;
             height: 400px;
             border: 1px solid #cdd4df;
             margin-top: 2em;
             background-color: #fdfefe;
             border-radius: 8px;
         }
     </style>
 </head>
 <body>
     <div class="main-content">
         <div class="container">
             <div class="user-info">
                 <p>Welcome, {{ current_user.username }}!</p>
                 <a href="{{ url_for('logout') }}">Logout</a>
             </div>
             <h1>The Idea Forge</h1>
             <p>Enter your idea, problem, or concept below, and let The Idea Forge help you discover new perspectives and unlock breakthrough insights.</p>
             <form id="alchemist-form">
                 <textarea name="user_input" id="user_input" rows="6" placeholder="E.g., 'How to foster sustainable energy solutions in urban environments?' or 'The challenge of balancing privacy and security in digital communication.'">{{ user_input }}</textarea>
                 <button type="submit">Forge My Ideas!</button>
             </form>

             <div id="loading-spinner">Forging Ideas... Please wait.</div>

             <div id="results-area" class="results" style="{% if not show_results %}display: none;{% endif %}">
                 <h2>Your Thought Network:</h2>
                 <div id="conceptual-graph"></div>
                 <h3>Core Concepts:</h3>
                 <p id="key-terms-display">{{ key_terms|join(', ') }}</p>
                 <h2>Provocative Prompts:</h2>
                 <ul id="prompts-list">
                     {% for prompt in prompts %}
                         <li>{{ prompt|safe }}</li>
                     {% endfor %}
                 </ul>
             </div>
         </div>
         <div class="footer">
             <p>Powered by The Idea Forge AI</p>
         </div>
     </div>

     <div class="history-sidebar">
         <h2>Session History</h2>
         <div id="session-history-list">
         {% if sessions %}
             {% for session in sessions %}
                 <div class="session-item" id="session-{{ session.id }}">
                     <div>
                         <a href="{{ url_for('view_session', session_id=session.id) }}">{{ session.input_text[:50] }}{% if session.input_text|length > 50 %}...{% endif %}</a>
                         <small>{{ session.timestamp }}</small>
                     </div>
                     <button class="delete-btn" data-session-id="{{ session.id }}">Delete</button>
                 </div>
             {% endfor %}
         {% else %}
             <p>No past sessions yet. Start Forging!</p>
         {% endif %}
         </div>
     </div>

     <script>
         // Data passed from Flask for initial load
         const INITIAL_GRAPH_DATA = {{ graph_data|tojson|safe }};

         // Function to render the graph
         function renderGraph(graphData) {
             var nodes = new vis.DataSet(graphData.nodes);
             var edges = new vis.DataSet(graphData.edges);
             var data = { nodes: nodes, edges: edges };
             var options = {
                 nodes: { borderWidth: 2, size: 20, font: { face: 'Segoe UI' } },
                 edges: { smooth: { type: 'continuous' } },
                 physics: { stabilization: false, barnesHut: { gravitationalConstant: -2000, centralGravity: 0.3, springLength: 95, springConstant: 0.04, damping: 0.09, avoidOverlap: 0 } },
                 interaction: { hover: true, navigationButtons: true, zoomView: true },
                 manipulation: { enabled: false }
             };
             var container = document.getElementById('conceptual-graph');
             if (container) {
                 // Clear any existing graph instance to prevent memory leaks/conflicts
                 if (window.currentNetwork) {
                     window.currentNetwork.destroy();
                 }
                 var network = new vis.Network(container, data, options);
                 network.fit(); // This makes the graph fit the view and center
                 window.currentNetwork = network; // Store for potential destruction
             }
         }

         // --- Main page load graph initialization ---
         document.addEventListener('DOMContentLoaded', function() {
             // Check if INITIAL_GRAPH_DATA has nodes (meaning data exists)
             if (INITIAL_GRAPH_DATA && INITIAL_GRAPH_DATA.nodes && INITIAL_GRAPH_DATA.nodes.length > 0) {
                 renderGraph(INITIAL_GRAPH_DATA);
                 document.getElementById('results-area').style.display = 'block';
             }
         });

         document.getElementById('alchemist-form').addEventListener('submit', async function(event) {
             event.preventDefault();

             const userInput = document.getElementById('user_input').value;
             const resultsArea = document.getElementById('results-area');
             const promptsList = document.getElementById('prompts-list');
             const keyTermsDisplay = document.getElementById('key-terms-display');
             const loadingSpinner = document.getElementById('loading-spinner');
             const sessionHistoryList = document.getElementById('session-history-list');
             const conceptualGraphDiv = document.getElementById('conceptual-graph');

             promptsList.innerHTML = '';
             keyTermsDisplay.innerHTML = '';
             conceptualGraphDiv.innerHTML = ''; // Clear graph container before new rendering
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

                 if (data.prompts && data.key_terms && data.graph_data) {
                     data.prompts.forEach(prompt => {
                         const li = document.createElement('li');
                         li.innerHTML = prompt;
                         promptsList.appendChild(li);
                     });
                     keyTermsDisplay.textContent = data.key_terms.join(', ');

                     renderGraph(data.graph_data); // Use the new function

                     resultsArea.style.display = 'block';

                     const newSessionHtml = `
                         <div class="session-item" id="session-${data.new_session_id}">
                             <div>
                                 <a href="/session/${data.new_session_id}">${data.input_text.substring(0, 50)}${data.input_text.length > 50 ? '...' : ''}</a>
                                 <small>${data.timestamp}</small>
                             </div>
                             <button class="delete-btn" data-session-id="${data.new_session_id}">Delete</button>
                         </div>
                     `;
                     sessionHistoryList.insertAdjacentHTML('afterbegin', newSessionHtml);
                     document.querySelector(`#session-${data.new_session_id} .delete-btn`).addEventListener('click', handleDeleteClick);

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

         async function handleDeleteClick(event) {
             const sessionId = event.target.dataset.sessionId;
             if (confirm(`Are you sure you want to delete session ID ${sessionId}?`)) {
                 try {
                     const response = await fetch(`/delete_session/${sessionId}`, {
                         method: 'DELETE',
                         headers: {
                             'Content-Type': 'application/json'
                         }
                     });

                     if (response.ok) {
                         document.getElementById(`session-${sessionId}`).remove();
                         // Reload the page to refresh the last displayed session if the deleted one was it
                         // This reload will trigger the DOMContentLoaded block to re-render the graph
                         window.location.reload();
                     } else {
                         const errorData = await response.json();
                         alert(`Error deleting session: ${errorData.message || response.statusText}`);
                     }
                 } catch (error) {
                     console.error('Error deleting session:', error);
                     alert('An error occurred while trying to delete the session.');
                 }
             }
         }

         document.querySelectorAll('.delete-btn').forEach(button => {
             button.addEventListener('click', handleDeleteClick);
         });

         // Function to render graph for session detail page
         function renderGraphDetail(graphData, containerId) {
             var nodes = new vis.DataSet(graphData.nodes);
             var edges = new vis.DataSet(graphData.edges);
             var data = { nodes: nodes, edges: edges };
             var options = {
                 nodes: { borderWidth: 2, size: 20, font: { face: 'Segoe UI' } },
                 edges: { smooth: { type: 'continuous' } },
                 physics: { stabilization: false, barnesHut: { gravitationalConstant: -2000, centralGravity: 0.3, springLength: 95, springConstant: 0.04, damping: 0.09, avoidOverlap: 0 } },
                 interaction: { hover: true, navigationButtons: true, zoomView: true },
                 manipulation: { enabled: false }
             };
             var container = document.getElementById(containerId);
             if (container) {
                 // Clear any existing graph instance for detail page
                 if (window.currentNetworkDetail) {
                     window.currentNetworkDetail.destroy();
                 }
                 var network = new vis.Network(container, data, options);
                 network.fit(); // Fit graph to screen on detail page too
                 window.currentNetworkDetail = network; // Store for destruction
             }
         }
     </script>
 </body>
 </html>
 """

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        data = request.get_json()
        user_input = data.get("user_input", "")

        if not user_input:
            return jsonify({"message": "Please provide input text."}), 400

        concept_graph, extracted_terms = map_concepts(user_input)
        graph_data = convert_graph_to_vis_data(concept_graph)
        prompts = generate_agitation_prompts(concept_graph, extracted_terms, user_input)

        new_session_id = save_session(current_user.id, user_input, extracted_terms, prompts, json.dumps(graph_data))

        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        # When we return JSON, the frontend script handles rendering
        return jsonify({
            "prompts": prompts,
            "key_terms": extracted_terms,
            "new_session_id": new_session_id,
            "input_text": user_input,
            "timestamp": current_timestamp,
            "graph_data": graph_data,
        })

    # This is the GET request handling - always fetches the latest session data
    user_input = ""
    prompts = []
    key_terms = []
    graph_data = {'nodes': [], 'edges': []} # Default empty
    show_results = False # Default to false, only show if data is loaded

    sessions = get_all_sessions(current_user.id)
    last_session_data = get_last_session_data(current_user.id)

    if last_session_data:
        user_input = last_session_data['input_text']
        prompts = last_session_data['prompts']
        key_terms = last_session_data['key_terms']
        graph_data = last_session_data['graph_data']
        show_results = True # Set to true if there's data to display

    # CORRECTED LINE: Pass the graph_data dictionary directly to the template.
    # The `|tojson` filter in the template will handle serializing it for JavaScript.
    return render_template_string(LOGIN_REGISTER_HTML, user_input=user_input, prompts=prompts, key_terms=key_terms,
                                  sessions=sessions, current_user=current_user,
                                  graph_data=graph_data, # FIX: Was json.dumps(graph_data)
                                  show_results=show_results)

@app.route("/register", methods=["GET", "POST"])
def register():
    message = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        existing_user = cursor.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()

        if existing_user:
            message = "Username already exists. Please choose a different one."
        else:
            hashed_password = generate_password_hash(password)
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            conn.close()
            return redirect(url_for('login', message="Registration successful! Please log in."))
        conn.close()
    return render_template('login_register.html', page_title="Register", button_text="Register", message=message)


@app.route("/login", methods=["GET", "POST"])
def login():
    message = request.args.get('message')
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.find_by_username(username)
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            message = "Invalid username or password."
    return render_template('login_register.html', page_title="Login", button_text="Login", message=message)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login', message="You have been logged out."))


@app.route("/delete_session/<int:session_id>", methods=["DELETE"])
@login_required
def delete_session(session_id):
    if delete_session_from_db(session_id, current_user.id):
        return jsonify({"message": "Session deleted successfully."}), 200
    else:
        return jsonify({"message": "Session not found or you don't have permission to delete it."}), 404


@app.route("/session/<int:session_id>")
@login_required
def view_session(session_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT input_text, key_terms, prompts, timestamp, graph_data FROM sessions WHERE id = ? AND user_id = ?',
        (session_id, current_user.id))
    session_data = cursor.fetchone()
    conn.close()

    if session_data:
        input_text, key_terms_json, prompts_json, timestamp_str, graph_data_json = session_data
        key_terms = json.loads(key_terms_json)
        prompts = json.loads(prompts_json)
        graph_data = json.loads(graph_data_json) if graph_data_json else {'nodes': [], 'edges': []}

        timestamp_obj = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        formatted_timestamp = timestamp_obj.strftime('%Y-%m-%d %H:%M')

        detail_html = f"""
 <!DOCTYPE html>
 <html lang="en">
 <head>
     <meta charset="UTF-8">
     <meta name="viewport" content="width=device-width, initial-scale=1.0">
     <title>Session {session_id}</title>
     <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
     <style>
         body {{
             font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
             margin: 2em;
             background-color: #f0f4f8;
             color: #333;
         }}
         .container {{
             max-width: 800px;
             margin: 0 auto;
             background-color: #fff;
             padding: 2em;
             border-radius: 8px;
             box-shadow: 0 4px 8px rgba(0,0,0,0.1);
         }}
         h1, h2 {{
             color: #5c678a;
             margin-bottom: 0.8em;
             border-bottom: 2px solid #dcdfe6;
             padding-bottom: 0.5em;
         }}
         .result-item {{
             margin-bottom: 1em;
             padding: 1em;
             border-left: 5px solid #7a82ab;
             background-color: #e9eef6;
             border-radius: 6px;
         }}
         strong {{
             color: #333;
         }}
         .back-link {{
             display: inline-block;
             margin-bottom: 1.5em;
             color: #7a82ab;
             text-decoration: none;
             font-weight: bold;
         }}
         .back-link:hover {{
             text-decoration: underline;
         }}
         p {{
             margin-bottom: 0.5em;
         }}
         #conceptual-graph-detail {{
             width: 100%;
             height: 400px;
             border: 1px solid #cdd4df;
             margin-top: 2em;
             background-color: #fdfefe;
             border-radius: 8px;
         }}
     </style>
 </head>
 <body>
     <div class="container">
         <a href="{url_for('index')}" class="back-link">&larr; Back to The Idea Forge Main</a>
         <h1>Session Details (ID: {session_id})</h1>
         <p><strong>Input:</strong> {input_text}</p>
         <p><strong>Date:</strong> {formatted_timestamp}</p>
         <h2>Your Thought Network:</h2>
         <div id="conceptual-graph-detail"></div>
         <h2>Core Concepts:</h2>
         <p>{', '.join(key_terms) if key_terms else 'No core concepts'}</p>
         <h2>Provocative Prompts:</h2>
         {''.join([f'<div class="result-item"><p>{prompt}</p></div>' for prompt in prompts])}
     </div>

     <script type="text/javascript">
         document.addEventListener('DOMContentLoaded', function() {{
             var graphData = {{
                 nodes: new vis.DataSet({json.dumps(graph_data['nodes'])}),
                 edges: new vis.DataSet({json.dumps(graph_data['edges'])})
             }};

             var container = document.getElementById('conceptual-graph-detail');

             var options = {{
                 nodes: {{
                     borderWidth: 2,
                     size: 20,
                     font: {{face: 'Segoe UI'}}
                 }},
                 edges: {{
                     smooth: {{type: 'continuous'}}
                 }},
                 physics: {{
                     stabilization: false,
                     barnesHut: {{
                         gravitationalConstant: -2000,
                         centralGravity: 0.3,
                         springLength: 95,
                         springConstant: 0.04,
                         damping: 0.09,
                         avoidOverlap: 0
                     }}
                 }},
                 interaction: {{
                     hover: true,
                     navigationButtons: true,
                     zoomView: true
                 }},
                 manipulation: {{
                     enabled: false
                 }}
             }};

             var network = new vis.Network(container, graphData, options);
             network.fit(); // Fit graph to screen on detail page too
         }});
     </script>
 </body>
 </html>
 """
        return render_template_string(detail_html)
    return "Session not found or you don't have permission to view it.", 403


# --- Step 5: Run the Flask App ---
if __name__ == "__main__":
    init_db()
    print("\nStarting Flask web server...")
    print("Open your web browser and go to: http://127.0.0.1:5000/")
    app.run(debug=True, use_reloader=False)