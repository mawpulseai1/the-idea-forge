# This file contains the fixed template for the view_session function

template = """
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
        .error-message {{
            color: #d32f2f;
            padding: 1em;
            background-color: #ffebee;
            border-radius: 4px;
            margin: 1em 0;
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
        <h2>Alchemical Agitations:</h2>
        {''.join([f'<div class="result-item"><p>{prompt}</p></div>' for prompt in prompts])}
    </div>

    <script type="text/javascript">
        document.addEventListener('DOMContentLoaded', function() {{
            try {{
                // Parse the JSON data first
                var nodesData = {json.dumps(graph_data['nodes'], ensure_ascii=False)};
                var edgesData = {json.dumps(graph_data['edges'], ensure_ascii=False)};
                
                var graphData = {{
                    nodes: new vis.DataSet(nodesData),
                    edges: new vis.DataSet(edgesData)
                }};

                var container = document.getElementById('conceptual-graph-detail');
                if (!container) {{
                    throw new Error('Graph container not found');
                }}

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
                network.fit();
                
                // Handle window resize
                var resizeTimer;
                window.addEventListener('resize', function() {{
                    clearTimeout(resizeTimer);
                    resizeTimer = setTimeout(function() {{
                        network.fit();
                    }}, 250);
                }});
                
            }} catch (error) {{
                console.error('Error initializing graph:', error);
                var container = document.getElementById('conceptual-graph-detail') || 
                               document.querySelector('.container');
                if (container) {{
                    var errorDiv = document.createElement('div');
                    errorDiv.className = 'error-message';
                    errorDiv.innerHTML = '<strong>Error loading graph visualization:</strong> ' + 
                                       'Please refresh the page to try again.';
                    container.appendChild(errorDiv);
                }}
            }}
        }});
    </script>
</body>
</html>
"""

# Usage in your view function:
# return render_template_string(template.format(
#     session_id=session_id,
#     input_text=input_text,
#     formatted_timestamp=formatted_timestamp,
#     key_terms=key_terms,
#     prompts=prompts,
#     graph_data=graph_data,
#     json=json
# ))

# Make sure to import json at the top of your file:
# import json
