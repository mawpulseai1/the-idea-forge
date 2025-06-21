fixed_js = """
const newSessionHtml = `
    <div class="session-item" id="session-${data.new_session_id}">
        <div>
            <a href="/session/${data.new_session_id}">${data.input_text.substring(0, 50)}${data.input_text.length > 50 ? '...' : ''}</a>
            <small>${data.timestamp}</small>
        </div>
        <button class="delete-btn" data-session-id="${data.new_session_id}">Delete</button>
    </div>`;
"""

print("Replace the malformed template literal in your code with this:")
print(fixed_js)
