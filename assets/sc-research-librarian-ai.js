(function () {
  'use strict';

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function renderMarkdownLite(markdown) {
    var safe = escapeHtml(markdown || '');

    safe = safe.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+|\/[^\s)]+)\)/g, function (_, text, url) {
      return '<a href="' + url + '" target="_blank" rel="noopener noreferrer">' + text + '</a>';
    });

    safe = safe.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    var lines = safe.split(/\n/);
    var html = [];
    var inList = false;

    lines.forEach(function (line) {
      var trimmed = line.trim();
      if (!trimmed) {
        if (inList) {
          html.push('</ul>');
          inList = false;
        }
        return;
      }

      if (/^-\s+/.test(trimmed)) {
        if (!inList) {
          html.push('<ul>');
          inList = true;
        }
        html.push('<li>' + trimmed.replace(/^-\s+/, '') + '</li>');
        return;
      }

      if (inList) {
        html.push('</ul>');
        inList = false;
      }

      if (/^#{2,4}\s+/.test(trimmed)) {
        html.push('<h3>' + trimmed.replace(/^#{2,4}\s+/, '') + '</h3>');
      } else {
        html.push('<p>' + trimmed + '</p>');
      }
    });

    if (inList) {
      html.push('</ul>');
    }

    return html.join('');
  }

  function init(root) {
    var endpoint = root.getAttribute('data-endpoint');
    var nonce = root.getAttribute('data-nonce');
    var textarea = root.querySelector('.sc-rl-ai__textarea');
    var submit = root.querySelector('[data-sc-rl-submit]');
    var clear = root.querySelector('[data-sc-rl-clear]');
    var answer = root.querySelector('[data-sc-rl-answer]');
    var status = root.querySelector('[data-sc-rl-status]');
    var honeypot = root.querySelector('.sc-rl-ai__hp');
    var examples = root.querySelectorAll('[data-sc-rl-example]');

    function setStatus(text, state) {
      status.textContent = text;
      root.setAttribute('data-state', state || 'ready');
    }

    function ask(question) {
      var clean = (question || textarea.value || '').trim();
      if (!clean) {
        setStatus('Add a question', 'error');
        answer.innerHTML = '<p>Please enter a question first.</p>';
        textarea.focus();
        return;
      }

      setStatus('Thinking…', 'loading');
      submit.disabled = true;
      answer.innerHTML = '<p class="sc-rl-ai__loading">Searching Sustainable Catalyst routes and knowledge-base context…</p>';

      fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-WP-Nonce': nonce
        },
        body: JSON.stringify({
          question: clean,
          hp: honeypot ? honeypot.value : ''
        })
      })
        .then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok) {
              var message = data && data.message ? data.message : 'The Research Librarian could not answer right now.';
              throw new Error(message);
            }
            return data;
          });
        })
        .then(function (data) {
          setStatus(data.source === 'ai_file_search' ? 'AI + knowledge base' : data.source || 'Ready', 'ready');
          answer.innerHTML = renderMarkdownLite(data.answer || 'No answer was returned. Try the Platform or Feature Suggestions route.');
        })
        .catch(function (error) {
          setStatus('Fallback', 'error');
          answer.innerHTML = renderMarkdownLite('The Research Librarian endpoint could not be reached.\n\n**Best starting points**\n- [Platform](/platform/)\n- [Platform Demos](/platform/demos/)\n- [Research Librarian](/platform/research-librarian/)\n- [Feature Suggestions](/platform/feature-suggestions/)\n\n' + error.message);
        })
        .finally(function () {
          submit.disabled = false;
        });
    }

    submit.addEventListener('click', function () {
      ask();
    });

    textarea.addEventListener('keydown', function (event) {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        ask();
      }
    });

    clear.addEventListener('click', function () {
      textarea.value = '';
      setStatus('Ready', 'ready');
      answer.innerHTML = '<p>Ask a question or choose an example. The librarian will recommend a route, explain why it fits, and suggest next steps.</p>';
      textarea.focus();
    });

    examples.forEach(function (button) {
      button.addEventListener('click', function () {
        textarea.value = button.getAttribute('data-sc-rl-example') || '';
        ask(textarea.value);
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.sc-rl-ai').forEach(init);
  });
}());
