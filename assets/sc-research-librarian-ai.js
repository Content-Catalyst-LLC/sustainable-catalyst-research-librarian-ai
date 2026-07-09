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
        if (inList) { html.push('</ul>'); inList = false; }
        return;
      }
      if (/^-\s+/.test(trimmed)) {
        if (!inList) { html.push('<ul>'); inList = true; }
        html.push('<li>' + trimmed.replace(/^-\s+/, '') + '</li>');
        return;
      }
      if (inList) { html.push('</ul>'); inList = false; }
      if (/^#{2,4}\s+/.test(trimmed)) {
        html.push('<h3>' + trimmed.replace(/^#{2,4}\s+/, '') + '</h3>');
      } else {
        html.push('<p>' + trimmed + '</p>');
      }
    });
    if (inList) { html.push('</ul>'); }
    return html.join('');
  }

  function routeNoteMarkdown(note) {
    if (!note) return '';
    var lines = [];
    lines.push('# Sustainable Catalyst Research Librarian Route Note');
    lines.push('');
    lines.push('Created: ' + (note.created_at_utc || ''));
    lines.push('Source: ' + (note.source || ''));
    lines.push('');
    lines.push('## Question');
    lines.push(note.question || '');
    lines.push('');
    lines.push('## Recommended Route');
    if (note.recommended_route) {
      lines.push('[' + note.recommended_route.title + '](' + note.recommended_route.url + ')');
      lines.push('Category: ' + note.recommended_route.category);
      lines.push(note.recommended_route.description || '');
    }
    lines.push('');
    lines.push('## Intent');
    lines.push(note.intent || '');
    lines.push('');
    lines.push('## Why');
    lines.push(note.why || '');
    lines.push('');
    lines.push('## Platform Fit');
    lines.push(note.platform_fit || '');
    lines.push('');
    lines.push('## Related Links');
    Object.keys(note.related || {}).forEach(function (label) {
      lines.push('- [' + label + '](' + note.related[label] + ')');
    });
    if (note.confidence) {
      lines.push('');
      lines.push('## Confidence');
      lines.push((note.confidence.level || '') + ' — ' + (note.confidence.explanation || ''));
    }
    if ((note.sources || []).length) {
      lines.push('');
      lines.push('## Grounding Sources');
      (note.sources || []).forEach(function (source) {
        lines.push('- [' + source.title + '](' + source.url + ') — ' + source.summary + (source.retrieval_mode ? ' [' + source.retrieval_mode + ', score ' + source.score + ']' : ''));
      });
    }
    if ((note.handoffs || []).length) {
      lines.push('');
      lines.push('## Handoffs');
      (note.handoffs || []).forEach(function (handoff) {
        lines.push('- ' + handoff.label + ': ' + handoff.reason + ' (' + handoff.url + ')');
      });
    }
    if (note.handoff_payload) {
      lines.push('');
      lines.push('## Structured Handoff Payload');
      lines.push('Target: ' + (note.handoff_payload.target || ''));
      lines.push('Payload ID: ' + (note.handoff_payload.payload_id || ''));
    }
    lines.push('');
    lines.push('## Next Step');
    lines.push(note.next_step || '');
    lines.push('');
    lines.push('## Boundaries');
    (note.boundaries || []).forEach(function (item) { lines.push('- ' + item); });
    return lines.join('\n');
  }

  function downloadJson(filename, data) {
    var blob = new Blob([JSON.stringify(data || {}, null, 2)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function renderRouteSummary(container, route, grounding) {
    if (!container || !route) return;
    container.hidden = false;
    var confidence = grounding && grounding.confidence ? grounding.confidence : null;
    var sources = grounding && grounding.sources ? grounding.sources.slice(0, 3) : [];
    var handoffs = grounding && grounding.handoffs ? grounding.handoffs.slice(0, 2) : [];
    var html = '<span>' + escapeHtml(route.category || 'Route') + '</span>' +
      '<strong>' + escapeHtml(route.title || '') + '</strong>' +
      '<p>' + escapeHtml(route.description || '') + '</p>';
    if (confidence) {
      html += '<div class="sc-rl-ai__confidence"><b>' + escapeHtml((confidence.level || 'unknown').toUpperCase()) + '</b><small>' + escapeHtml(confidence.explanation || '') + '</small></div>';
    }
    if (sources.length) {
      html += '<div class="sc-rl-ai__source-list"><b>Grounding sources</b>' + sources.map(function (source) {
        return '<a href="' + escapeHtml(source.url || '#') + '">' + escapeHtml(source.title || '') + (source.semantic_score ? ' · sem ' + escapeHtml(source.semantic_score) : '') + '</a>';
      }).join('') + '</div>';
    }
    if (handoffs.length) {
      html += '<div class="sc-rl-ai__source-list"><b>Suggested handoffs</b>' + handoffs.map(function (handoff) {
        return '<a href="' + escapeHtml(handoff.url || '#') + '">' + escapeHtml(handoff.label || '') + '</a>';
      }).join('') + '</div>';
    }
    html += '<a href="' + escapeHtml(route.url || '#') + '">Open route →</a>';
    container.innerHTML = html;
  }

  function init(root) {
    var endpoint = root.getAttribute('data-endpoint');
    var routesEndpoint = root.getAttribute('data-routes-endpoint');
    var sessionEndpoint = root.getAttribute('data-session-endpoint');
    var nonce = root.getAttribute('data-nonce');
    var textarea = root.querySelector('.sc-rl-ai__textarea');
    var submit = root.querySelector('[data-sc-rl-submit]');
    var clear = root.querySelector('[data-sc-rl-clear]');
    var copy = root.querySelector('[data-sc-rl-copy]');
    var download = root.querySelector('[data-sc-rl-download]');
    var handoffDownload = root.querySelector('[data-sc-rl-handoff-download]');
    var saveSession = root.querySelector('[data-sc-rl-save-session]');
    var answer = root.querySelector('[data-sc-rl-answer]');
    var status = root.querySelector('[data-sc-rl-status]');
    var honeypot = root.querySelector('.sc-rl-ai__hp');
    var examples = root.querySelectorAll('[data-sc-rl-example]');
    var routeSummary = root.querySelector('[data-sc-rl-route-summary]');
    var routeStrip = root.querySelector('[data-sc-rl-route-strip]');
    var latest = null;

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
      setStatus('Routing…', 'loading');
      submit.disabled = true;
      answer.innerHTML = '<p class="sc-rl-ai__loading">Checking Sustainable Catalyst routes, source records, semantic matches, Workbench handoffs, and Decision Studio workflows</p>';

      fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
        body: JSON.stringify({ question: clean, hp: honeypot ? honeypot.value : '' })
      })
        .then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok) {
              throw new Error(data && data.message ? data.message : 'The Research Librarian could not answer right now.');
            }
            return data;
          });
        })
        .then(function (data) {
          latest = data;
          setStatus(data.source || 'Ready', 'ready');
          answer.innerHTML = renderMarkdownLite(data.answer || 'No answer was returned. Try the Platform or Feature Suggestions route.');
          renderRouteSummary(routeSummary, data.route, data.grounding);
        })
        .catch(function (error) {
          latest = null;
          setStatus('Fallback', 'error');
          answer.innerHTML = renderMarkdownLite('The Research Librarian endpoint could not be reached.\n\n**Best starting points**\n- [Platform](/platform/)\n- [Platform Demos](/platform/demos/)\n- [Workbench](https://sustainablecatalyst.com/modeling-analytics/workbench/)\n- [Decision Studio](/platform/#decision-studio)\n- [Feature Suggestions](/platform/feature-suggestions/)\n\n' + error.message);
        })
        .finally(function () { submit.disabled = false; });
    }

    submit.addEventListener('click', function () { ask(); });
    textarea.addEventListener('keydown', function (event) {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') ask();
    });
    clear.addEventListener('click', function () {
      textarea.value = '';
      latest = null;
      setStatus('Ready', 'ready');
      answer.innerHTML = '<p>Ask a question or choose an example. The librarian will recommend a route, explain why it fits, show related links, and produce an exportable route note and structured handoff payload.</p>';
      if (routeSummary) { routeSummary.hidden = true; routeSummary.innerHTML = ''; }
      textarea.focus();
    });
    copy.addEventListener('click', function () {
      if (!latest || !latest.route_note) {
        setStatus('Ask first', 'error');
        return;
      }
      var text = routeNoteMarkdown(latest.route_note);
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () { setStatus('Copied', 'ready'); });
      } else {
        setStatus('Copy unavailable', 'error');
      }
    });
    download.addEventListener('click', function () {
      if (!latest || !latest.route_note) {
        setStatus('Ask first', 'error');
        return;
      }
      downloadJson('sustainable-catalyst-route-note.json', latest.route_note);
      setStatus('Downloaded', 'ready');
    });

    if (handoffDownload) {
      handoffDownload.addEventListener('click', function () {
        if (!latest || !latest.route_note || !latest.route_note.handoff_payload) {
          setStatus('Ask first', 'error');
          return;
        }
        var target = latest.route_note.handoff_payload.target || 'handoff';
        downloadJson('sustainable-catalyst-' + target.replace(/_/g, '-') + '-handoff.json', latest.route_note.handoff_payload);
        setStatus('Handoff downloaded', 'ready');
      });
    }

    if (saveSession) {
      saveSession.addEventListener('click', function () {
        if (!latest || !latest.route_note) {
          setStatus('Ask first', 'error');
          return;
        }
        if (!sessionEndpoint) {
          setStatus('Session endpoint unavailable', 'error');
          return;
        }
        saveSession.disabled = true;
        setStatus('Saving session…', 'loading');
        fetch(sessionEndpoint, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
          body: JSON.stringify({ route_note: latest.route_note })
        })
          .then(function (response) {
            return response.json().then(function (data) {
              if (!response.ok) {
                throw new Error(data && data.message ? data.message : 'The session could not be saved.');
              }
              return data;
            });
          })
          .then(function () { setStatus('Session saved', 'ready'); })
          .catch(function (error) { setStatus(error.message || 'Save failed', 'error'); })
          .finally(function () { saveSession.disabled = false; });
      });
    }

    examples.forEach(function (button) {
      button.addEventListener('click', function () {
        textarea.value = button.getAttribute('data-sc-rl-example') || '';
        ask(textarea.value);
      });
    });

    if (routeStrip && routesEndpoint) {
      fetch(routesEndpoint, { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var routes = (data && data.routes ? data.routes : []).slice(0, 8);
          routeStrip.innerHTML = routes.map(function (route) {
            return '<a href="' + escapeHtml(route.url) + '"><span>' + escapeHtml(route.category) + '</span><strong>' + escapeHtml(route.title) + '</strong></a>';
          }).join('');
        })
        .catch(function () { routeStrip.hidden = true; });
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.sc-rl-ai').forEach(init);
  });
}());
