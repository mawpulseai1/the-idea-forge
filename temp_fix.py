import json
import sqlite3
from datetime import datetime
from flask import render_template_string, url_for

# This is the fixed version of the view_session function
def view_session(session_id):
    DATABASE = 'alchemist_sessions.db'  # Make sure this matches your database path
    
    def get_project_name(project_id):
        if not project_id:
            return None
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM projects WHERE id = ?', (project_id,))
        name = cursor.fetchone()
        conn.close()
        return name[0] if name else None
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT input_text, key_terms, prompts, timestamp, graph_data, project_id FROM sessions WHERE id = ?',
        (session_id,))
    session_data = cursor.fetchone()
    conn.close()
    
    if session_data:
        input_text, key_terms_json, prompts_json, timestamp_str, graph_data_json, project_id = session_data
        key_terms = json.loads(key_terms_json)
        prompts = json.loads(prompts_json)
        graph_data = json.loads(graph_data_json) if graph_data_json else {'nodes': [], 'edges': []}

        project_name_display = ""
        if project_id:
            project_name = get_project_name(project_id)
            if project_name:
                project_name_display = f" (Project: {project_name})"

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
        <a href="{url_for('index')}" class="back-link">&larr; Back to Alchemist Main</a>
        <h1>Session Details (ID: {session_id}){project_name_display}</h1>
        <p><strong>Input:</strong> {input_text}</p>
        <p><strong>Date:</strong> {formatted_timestamp}</p>
        <h2>Conceptual Map:</h2>
        <div id="conceptual-graph-detail"></div>
        <h2>Key Terms:</h2>
        <p>{', '.join(key_terms) if key_terms else 'No key terms'}</p>
        <h2>Alchemical Agitations:</h2>
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
        }});
    </script>
</body>
</html>
"""
        return render_template_string(detail_html)
    return "Session not found or you don't have permission to view it.", 403
