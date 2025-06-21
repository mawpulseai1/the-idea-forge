from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import sqlite3
import json
from datetime import datetime
from flask_login import login_required, current_user

app = Flask(__name__)

@app.route("/session/<int:session_id>")
@login_required
def view_session(session_id):
    conn = sqlite3.connect('alchemist_sessions.db')
    cursor = conn.cursor()
    
    # Retrieve session data including graph_data
    cursor.execute('''
        SELECT id, user_id, input_text, key_terms, prompts, graph_data,
               strftime('%Y-%m-%d %H:%M', timestamp) as formatted_time
        FROM sessions 
        WHERE id = ? AND user_id = ?
    ''', (session_id, current_user.id))
    
    session_data = cursor.fetchone()
    conn.close()

    if not session_data:
        return "Session not found or access denied", 404
    
    # Parse the session data
    session_id = session_data[0]
    user_id = session_data[1]
    input_text = session_data[2]
    key_terms = json.loads(session_data[3])
    prompts = json.loads(session_data[4])
    graph_data = json.loads(session_data[5]) if session_data[5] else {'nodes': [], 'edges': []}
    formatted_timestamp = session_data[6]

    # Create the HTML response
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Session {session_id}</title>
        <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 2em;
                background-color: #f0f4f8;
                color: #333;
                line-height: 1.6;
            }}
            .container {{
                max-width: 1000px;
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
            strong {{ color: #333; }}
            .back-link {{
                display: inline-block;
                margin-bottom: 1.5em;
                color: #7a82ab;
                text-decoration: none;
                font-weight: bold;
            }}
            .back-link:hover {{ text-decoration: underline; }}
            p {{ margin-bottom: 0.5em; }}
            #conceptual-graph-detail {{
                width: 100%;
                height: 500px;
                border: 1px solid #cdd4df;
                margin: 1em 0 2em;
                background-color: #fdfefe;
                border-radius: 8px;
            }}
            .key-terms {{
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin: 1em 0;
            }}
            .term-tag {{
                background-color: #e0f7fa;
                border: 1px solid #80deea;
                border-radius: 12px;
                padding: 3px 10px;
                font-size: 0.9em;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <a href="{url_for('index')}" class="back-link">&larr; Back to Alchemist Main</a>
            <h1>Session Details (ID: {session_id})</h1>
            
            <div class="section">
                <h2>Original Input</h2>
                <p>{input_text}</p>
            </div>
            
            <div class="section">
                <h2>Concept Map</h2>
                <div id="conceptual-graph-detail"></div>
            </div>
            
            <div class="section">
                <h2>Key Terms</h2>
                <div class="key-terms">
                    {key_terms_html}
                </div>
            </div>
            
            <div class="section">
                <h2>Alchemical Agitations</h2>
                {prompts_html}
            </div>
        </div>

        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const graphData = {graph_data_json};
                const container = document.getElementById('conceptual-graph-detail');
                
                if (graphData && graphData.nodes && graphData.nodes.length > 0) {{
                    const data = {{
                        nodes: new vis.DataSet(graphData.nodes),
                        edges: new vis.DataSet(graphData.edges)
                    }};
                    
                    const options = {{
                        nodes: {{
                            shape: 'box',
                            margin: 10,
                            font: {{
                                size: 12,
                                face: 'Arial'
                            }},
                            borderWidth: 1,
                            shadow: true
                        }},
                        edges: {{
                            width: 2,
                            smooth: true,
                            arrows: {{
                                to: {{enabled: true, scaleFactor: 0.5}}
                            }},
                            font: {{size: 10, align: 'middle'}}
                        }},
                        physics: {{
                            barnesHut: {{
                                gravitationalConstant: -2000,
                                centralGravity: 0.3,
                                springLength: 200
                            }},
                            minVelocity: 0.4,
                            solver: 'barnesHut'
                        }},
                        layout: {{
                            improvedLayout: true
                        }},
                        interaction: {{
                            dragNodes: true,
                            dragView: true,
                            zoomView: true
                        }}
                    }};
                    
                    new vis.Network(container, data, options);
                }} else {{
                    container.innerHTML = '<p style="text-align: center; margin-top: 50px; color: #666;">No graph data available for this session.</p>';
                }}
            }});
        </script>
    </body>
    </html>
    """.format(
        session_id=session_id,
        input_text=input_text,
        formatted_timestamp=formatted_timestamp,
        key_terms_html='\n'.join(f'<span class="term-tag">{term}</span>' for term in key_terms),
        prompts_html='\n'.join(f'<div class="result-item"><p>{prompt}</p></div>' for prompt in prompts),
        graph_data_json=json.dumps(graph_data),
        url_for=url_for
    )
    
    return html

if __name__ == "__main__":
    app.run(debug=True)
