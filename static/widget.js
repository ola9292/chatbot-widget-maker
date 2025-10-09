(function() {
  // Extract the business ID from the script tag’s data-id attribute
  const currentScript = document.currentScript;
  const businessId = currentScript.getAttribute('data-id');

  if (!businessId) {
    console.error("⚠️ No business ID found in widget script tag (data-id missing).");
    return;
  }

  // Create the chat button
  const chatButton = document.createElement('button');
  chatButton.innerText = '💬';
  Object.assign(chatButton.style, {
    position: 'fixed',
    bottom: '20px',
    right: '20px',
    borderRadius: '50%',
    width: '60px',
    height: '60px',
    border: 'none',
    backgroundColor: '#0078FF',
    color: '#fff',
    fontSize: '24px',
    cursor: 'pointer',
    zIndex: '9999'
  });
  document.body.appendChild(chatButton);

  // Create the chat window
  const chatBox = document.createElement('div');
  Object.assign(chatBox.style, {
    position: 'fixed',
    bottom: '100px',
    right: '20px',
    width: '320px',
    height: '400px',
    background: '#fff',
    border: '1px solid #ddd',
    borderRadius: '10px',
    boxShadow: '0 4px 10px rgba(0,0,0,0.1)',
    display: 'none',
    flexDirection: 'column',
    overflow: 'hidden',
    zIndex: '9999'
  });

  chatBox.innerHTML = `
    <div style="background:#0078FF;color:#fff;padding:10px;text-align:center;">Chat with Us</div>
    <div id="chat-content" style="flex:1;padding:10px;overflow-y:auto;font-family:sans-serif;font-size:14px;"></div>
    <div style="display:flex;border-top:1px solid #ddd;">
      <input id="chat-input" type="text" style="flex:1;border:none;padding:10px;" placeholder="Type a message..." />
      <button id="send-btn" style="background:#0078FF;color:#fff;border:none;padding:10px;">Send</button>
    </div>
  `;
  document.body.appendChild(chatBox);

  // Toggle chat window
  chatButton.addEventListener('click', () => {
    chatBox.style.display = chatBox.style.display === 'none' ? 'flex' : 'none';
  });

  // Handle message sending
  const sendMessage = async () => {
    const input = document.getElementById('chat-input');
    const content = document.getElementById('chat-content');
    const message = input.value.trim();
    if (!message) return;

    // Display user message
    const userMsg = document.createElement('div');
    userMsg.style.textAlign = 'right';
    userMsg.innerText = message;
    content.appendChild(userMsg);

    try {
      const response = await fetch(`http://127.0.0.1:5000/chat?id=${businessId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: message })
      });

      if (!response.ok) throw new Error('Network response was not ok.');

      const result = await response.json();

      // Display bot reply
      const botMsg = document.createElement('div');
      botMsg.style.textAlign = 'left';
      botMsg.style.color = '#0078FF';
      botMsg.innerText = result.answer;
      content.appendChild(botMsg);

    } catch (err) {
      const errMsg = document.createElement('div');
      errMsg.style.textAlign = 'left';
      errMsg.style.color = 'red';
      errMsg.innerText = 'Error connecting to chat.';
      content.appendChild(errMsg);
      console.error(err);
    }

    input.value = '';
    content.scrollTop = content.scrollHeight;
  };

  // Send on button click
  document.getElementById('send-btn').addEventListener('click', sendMessage);

  // Send on Enter key
  document.getElementById('chat-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
  });
})();
