# alchemist_core.py

import torch
import networkx as nx
from sentence_transformers import SentenceTransformer, util
from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import spacy
import sqlite3
import json
from datetime import datetime

# [Previous code remains the same until line 286...]

                    // Update session history sidebar dynamically
                    const newSessionHtml = `
                        <div class="session-item">
                            <a href="/session/${data.new_session_id}">${data.input_text.substring(0, 50)}${data.input_text.length > 50 ? '...' : ''}</a>
                            <small>${data.timestamp}</small>
                        </div>`;
// [Rest of the code remains the same...]
