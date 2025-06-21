// Replace the JavaScript code in alchemist_core.py around line 720 with this code
const newSessionHtml = `
    <div class="session-item" id="session-${data.new_session_id}">
        <div>
            <a href="/session/${data.new_session_id}">
                ${data.input_text.substring(0, 50)}${data.input_text.length > 50 ? '...' : ''}
            </a>
            <small>${data.timestamp}</small>
        </div>
        <button class="delete-btn" data-session-id="${data.new_session_id}">Delete</button>
    </div>`;

const currentProjectIdOnPage = document.getElementById('project_id').value;
if (!currentProjectIdOnPage || currentProjectIdOnPage == data.project_id) {
    sessionHistoryList.insertAdjacentHTML('afterbegin', newSessionHtml);
    document.querySelector(`#session-${data.new_session_id} .delete-btn`).addEventListener('click', handleDeleteClick);
}
