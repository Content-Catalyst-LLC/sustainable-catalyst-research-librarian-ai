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

  function confidenceClass(level) {
    var clean = String(level || 'unknown').toLowerCase();
    if (clean.indexOf('high') !== -1) return 'sc-rl-answer-ux__badge--high';
    if (clean.indexOf('medium') !== -1) return 'sc-rl-answer-ux__badge--medium';
    if (clean.indexOf('low') !== -1) return 'sc-rl-answer-ux__badge--low';
    return 'sc-rl-answer-ux__badge--unknown';
  }

  function sourceScore(source) {
    var score = source.final_score || source.score || source.semantic_score || source.keyword_score || '';
    if (score === '') return '';
    return String(score);
  }

  function routeNoteHandoffTarget(note) {
    if (!note || !note.handoff_payload) return '';
    return String(note.handoff_payload.target || '').replace(/_/g, ' ');
  }

  function renderAnswerUx(container, data, fallbackHtml) {
    if (!container) return;
    var route = data.route || (data.route_note && data.route_note.recommended_route) || {};
    var grounding = data.grounding || {};
    var note = data.route_note || {};
    var confidence = grounding.confidence || note.confidence || {};
    var sources = (grounding.sources || note.sources || []).slice(0, 5);
    var handoffs = (grounding.handoffs || note.handoffs || []).slice(0, 4);
    var reasonCodes = grounding.reason_codes || note.reason_codes || [];
    var ambiguity = grounding.ambiguity || note.ambiguity || [];
    var confidenceLevel = confidence.level || 'unknown';
    var routeUrl = route.url || (note.recommended_route && note.recommended_route.url) || '#';
    var routeTitle = route.title || (note.recommended_route && note.recommended_route.title) || 'Recommended route';
    var routeCategory = route.category || (note.recommended_route && note.recommended_route.category) || 'Route';
    var routeDescription = route.description || (note.recommended_route && note.recommended_route.description) || note.intent || '';
    var why = note.why || route.why || '';
    var platformFit = note.platform_fit || route.platform_fit || '';
    var nextStep = note.next_step || route.next_step || '';

    var html = '<div class="sc-rl-answer-ux__grid">';
    html += '<article class="sc-rl-answer-ux__route-card">';
    html += '<div class="sc-rl-answer-ux__card-head"><span>' + escapeHtml(routeCategory) + '</span><b class="sc-rl-answer-ux__badge ' + confidenceClass(confidenceLevel) + '">' + escapeHtml(String(confidenceLevel).toUpperCase()) + '</b></div>';
    html += '<h3>' + escapeHtml(routeTitle) + '</h3>';
    html += '<p>' + escapeHtml(routeDescription) + '</p>';
    if (why) html += '<div class="sc-rl-answer-ux__why"><strong>Why this fits</strong><p>' + escapeHtml(why) + '</p></div>';
    if (platformFit) html += '<div class="sc-rl-answer-ux__why"><strong>Platform fit</strong><p>' + escapeHtml(platformFit) + '</p></div>';
    html += '<a class="sc-rl-answer-ux__primary-link" href="' + escapeHtml(routeUrl) + '">Open recommended route →</a>';
    html += '</article>';

    html += '<article class="sc-rl-answer-ux__answer-body"><div class="sc-rl-answer-ux__card-head"><span>Route explanation</span></div>' + (fallbackHtml || '') + '</article>';
    html += '</div>';

    html += '<div class="sc-rl-answer-ux__meta-row">';
    html += '<div class="sc-rl-answer-ux__confidence"><strong>Confidence</strong><p>' + escapeHtml(confidence.explanation || 'Confidence is based on route match quality, matched sources, and ambiguity.') + '</p></div>';
    if (reasonCodes.length) {
      html += '<div class="sc-rl-answer-ux__chips"><strong>Reason codes</strong><div>' + reasonCodes.map(function (code) { return '<span>' + escapeHtml(code) + '</span>'; }).join('') + '</div></div>';
    }
    if (ambiguity.length) {
      html += '<div class="sc-rl-answer-ux__chips sc-rl-answer-ux__chips--warning"><strong>Ambiguity</strong><div>' + ambiguity.map(function (item) { return '<span>' + escapeHtml(item) + '</span>'; }).join('') + '</div></div>';
    }
    html += '</div>';

    html += '<section class="sc-rl-answer-ux__source-section"><div class="sc-rl-answer-ux__section-head"><span>Matched sources</span><strong>' + sources.length + ' source' + (sources.length === 1 ? '' : 's') + '</strong></div>';
    if (sources.length) {
      html += '<div class="sc-rl-answer-ux__source-grid">' + sources.map(function (source) {
        return '<article class="sc-rl-answer-ux__source-card"><span>' + escapeHtml(source.type || source.route_id || 'Source') + '</span><h4><a href="' + escapeHtml(source.url || '#') + '">' + escapeHtml(source.title || 'Untitled source') + '</a></h4><p>' + escapeHtml(source.summary || '') + '</p><small>' + escapeHtml(source.retrieval_mode || 'match') + (sourceScore(source) ? ' · score ' + escapeHtml(sourceScore(source)) : '') + '</small></article>';
      }).join('') + '</div>';
    } else {
      html += '<div class="sc-rl-answer-ux__empty-state"><strong>No strong source match yet.</strong><p>Use the route as a starting point, ask a narrower follow-up, or send the gap to Feature Suggestions.</p></div>';
    }
    html += '</section>';

    html += '<section class="sc-rl-answer-ux__action-center"><div class="sc-rl-answer-ux__section-head"><span>Route Action Center</span><strong>Next actions</strong></div><div class="sc-rl-answer-ux__actions-row">';
    html += '<a href="' + escapeHtml(routeUrl) + '">Open route</a>';
    handoffs.forEach(function (handoff) { html += '<a href="' + escapeHtml(handoff.url || '#') + '">' + escapeHtml(handoff.label || 'Open handoff') + '</a>'; });
    if (note.handoff_payload) html += '<button type="button" data-sc-rl-handoff-download-inline>Download ' + escapeHtml(routeNoteHandoffTarget(note) || 'handoff') + ' JSON</button>';
    html += '<button type="button" data-sc-rl-copy-inline>Copy route note</button><button type="button" data-sc-rl-download-inline>Download route note</button>';
    html += '<a href="/platform/feature-suggestions/">Suggest missing feature</a>';
    html += '</div>';
    if (nextStep) html += '<p class="sc-rl-answer-ux__next-step"><strong>Suggested next step:</strong> ' + escapeHtml(nextStep) + '</p>';
    html += '</section>';

    container.hidden = false;
    container.innerHTML = html;
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
    var feedbackEndpoint = root.getAttribute('data-feedback-endpoint');
    var nonce = root.getAttribute('data-nonce');
    var textarea = root.querySelector('.sc-rl-ai__textarea');
    var submit = root.querySelector('[data-sc-rl-submit]');
    var clear = root.querySelector('[data-sc-rl-clear]');
    var copy = root.querySelector('[data-sc-rl-copy]');
    var download = root.querySelector('[data-sc-rl-download]');
    var handoffDownload = root.querySelector('[data-sc-rl-handoff-download]');
    var saveSession = root.querySelector('[data-sc-rl-save-session]');
    var feedbackHelpful = root.querySelector('[data-sc-rl-feedback-helpful]');
    var feedbackIssue = root.querySelector('[data-sc-rl-feedback-issue]');
    var answer = root.querySelector('[data-sc-rl-answer]');
    var status = root.querySelector('[data-sc-rl-status]');
    var honeypot = root.querySelector('.sc-rl-ai__hp');
    var examples = root.querySelectorAll('[data-sc-rl-example]');
    var routeSummary = root.querySelector('[data-sc-rl-route-summary]');
    var answerUx = root.querySelector('[data-sc-rl-answer-ux]');
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
          var renderedAnswer = renderMarkdownLite(data.answer || 'No answer was returned. Try the Platform or Feature Suggestions route.');
          answer.innerHTML = renderedAnswer;
          renderAnswerUx(answerUx, data, renderedAnswer);
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
      if (answerUx) { answerUx.hidden = true; answerUx.innerHTML = ''; }
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

    root.addEventListener('click', function (event) {
      var target = event.target;
      if (!target || !target.matches) return;
      if (target.matches('[data-sc-rl-copy-inline]')) {
        if (copy) copy.click();
      }
      if (target.matches('[data-sc-rl-download-inline]')) {
        if (download) download.click();
      }
      if (target.matches('[data-sc-rl-handoff-download-inline]')) {
        if (handoffDownload) handoffDownload.click();
      }
    });




    function submitFeedback(type, note) {
      if (!latest || !latest.route_note) {
        setStatus('Ask first', 'error');
        return;
      }
      if (!feedbackEndpoint) {
        setStatus('Feedback endpoint unavailable', 'error');
        return;
      }
      setStatus('Saving feedback…', 'loading');
      fetch(feedbackEndpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
        body: JSON.stringify({ type: type, note: note || '', route_note: latest.route_note })
      })
        .then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok) {
              throw new Error(data && data.message ? data.message : 'Feedback could not be saved.');
            }
            return data;
          });
        })
        .then(function () { setStatus(type === 'helpful' ? 'Feedback saved' : 'Issue recorded', 'ready'); })
        .catch(function (error) { setStatus(error.message || 'Feedback failed', 'error'); });
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


    if (feedbackHelpful) {
      feedbackHelpful.addEventListener('click', function () {
        submitFeedback('helpful', 'Visitor marked this route as helpful.');
      });
    }

    if (feedbackIssue) {
      feedbackIssue.addEventListener('click', function () {
        var note = window.prompt('What should be reviewed? Examples: wrong route, missing source, unclear answer, feature gap, knowledge gap.');
        if (note === null) return;
        var lowered = (note || '').toLowerCase();
        var type = 'issue';
        if (lowered.indexOf('wrong route') !== -1) type = 'wrong_route';
        else if (lowered.indexOf('missing source') !== -1 || lowered.indexOf('source') !== -1) type = 'missing_source';
        else if (lowered.indexOf('knowledge gap') !== -1 || lowered.indexOf('gap') !== -1) type = 'knowledge_gap';
        else if (lowered.indexOf('feature') !== -1) type = 'feature_gap';
        else if (lowered.indexOf('unclear') !== -1) type = 'unclear';
        submitFeedback(type, note || 'Visitor reported a route issue.');
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

  function renderPathMarkdown(path) {
    if (!path) return '';
    var lines = [];
    lines.push('# Sustainable Catalyst Guided Research Path');
    lines.push('');
    lines.push('Question: ' + (path.question || ''));
    lines.push('Path: ' + (path.title || ''));
    lines.push('Depth: ' + (path.depth || ''));
    lines.push('Confidence: ' + ((path.confidence && path.confidence.level) || 'unknown') + ' (' + ((path.confidence && path.confidence.score) || 0) + ')');
    lines.push('');
    (path.steps || []).forEach(function(step, index) {
      lines.push((index + 1) + '. ' + (step.label || '') + ' — ' + (step.route_target || ''));
      lines.push('   Task: ' + (step.task || ''));
      lines.push('   Output: ' + (step.output || ''));
      if (step.route_url) lines.push('   Route: ' + step.route_url);
      if (step.handoff_target) lines.push('   Handoff: ' + step.handoff_target);
      lines.push('');
    });
    if ((path.checkpoints || []).length) {
      lines.push('Checkpoints:');
      (path.checkpoints || []).forEach(function(item) { lines.push('- ' + item); });
    }
    lines.push('');
    lines.push('Boundary: ' + (path.boundary_note || ''));
    return lines.join('\n');
  }

  function renderPathResult(path) {
    if (!path) return '<p>No path was returned.</p>';
    var confidence = path.confidence || {};
    var html = '<div class="sc-rl-path-result">' +
      '<div class="sc-rl-path-result__summary"><h3>' + escapeHtml(path.title || '') + '</h3>' +
      '<p>' + escapeHtml(path.summary || '') + '</p></div>' +
      '<div class="sc-rl-path-result__meta">' +
      '<span>Depth: ' + escapeHtml(path.depth || 'standard') + '</span>' +
      '<span>Confidence: ' + escapeHtml((confidence.level || 'unknown').toUpperCase()) + ' · ' + escapeHtml(confidence.score || 0) + '</span>' +
      '<span>Steps: ' + escapeHtml((path.steps || []).length) + '</span>' +
      '</div>' +
      '<div class="sc-rl-path-steps">';
    (path.steps || []).forEach(function(step) {
      html += '<article class="sc-rl-path-step"><h3>' + escapeHtml(step.label || '') + '</h3>' +
        '<p><strong>Route:</strong> ' + escapeHtml(step.route_target || '') + '</p>' +
        '<p>' + escapeHtml(step.task || '') + '</p>' +
        '<p><strong>Output:</strong> ' + escapeHtml(step.output || '') + '</p>';
      if (step.handoff_target) html += '<p><strong>Handoff:</strong> ' + escapeHtml(step.handoff_target) + '</p>';
      if (step.route_url) html += '<p><a href="' + escapeHtml(step.route_url) + '">Open route →</a></p>';
      html += '</article>';
    });
    html += '</div>';
    if ((path.checkpoints || []).length) {
      html += '<div class="sc-rl-path-checkpoints"><h3>Checkpoints</h3><ul>' + path.checkpoints.map(function(item) { return '<li>' + escapeHtml(item) + '</li>'; }).join('') + '</ul></div>';
    }
    if (path.next_action && path.next_action.url) {
      html += '<p><a class="sc-rl-ai__button sc-rl-ai__button--primary" href="' + escapeHtml(path.next_action.url) + '">' + escapeHtml(path.next_action.label || 'Open next route') + '</a></p>';
    }
    html += '<p class="sc-rl-ai__fineprint">' + escapeHtml(path.boundary_note || '') + '</p></div>';
    return html;
  }

  function initPathBuilder(root) {
    var endpoint = root.getAttribute('data-path-endpoint');
    var saveEndpoint = root.getAttribute('data-path-save-endpoint');
    var nonce = root.getAttribute('data-nonce');
    var textarea = root.querySelector('.sc-rl-path-builder__textarea');
    var preferred = root.querySelector('[data-sc-rl-path-preferred]');
    var depth = root.querySelector('[data-sc-rl-path-depth]');
    var build = root.querySelector('[data-sc-rl-path-build]');
    var copy = root.querySelector('[data-sc-rl-path-copy]');
    var download = root.querySelector('[data-sc-rl-path-download]');
    var save = root.querySelector('[data-sc-rl-path-save]');
    var output = root.querySelector('[data-sc-rl-path-output]');
    var status = root.querySelector('[data-sc-rl-path-status]');
    var examples = root.querySelectorAll('[data-sc-rl-path-example]');
    var latest = null;

    function setStatus(text, state) {
      if (status) status.textContent = text;
      root.setAttribute('data-state', state || 'ready');
    }

    function runBuild(question) {
      var clean = (question || textarea.value || '').trim();
      if (!clean) {
        setStatus('Add a question', 'error');
        output.innerHTML = '<p>Please enter a question or workflow goal first.</p>';
        return;
      }
      setStatus('Building path…', 'loading');
      build.disabled = true;
      output.innerHTML = '<p class="sc-rl-ai__loading">Building an ordered Sustainable Catalyst route path</p>';
      fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
        body: JSON.stringify({ question: clean, preferred_path: preferred ? preferred.value : '', depth: depth ? depth.value : 'standard' })
      })
        .then(function(response) { return response.json().then(function(data) { if (!response.ok) throw new Error(data && data.message ? data.message : 'Path could not be built.'); return data; }); })
        .then(function(data) { latest = data; output.innerHTML = renderPathResult(data); setStatus('Path ready', 'ready'); })
        .catch(function(error) { latest = null; output.innerHTML = '<p>' + escapeHtml(error.message || 'The path builder could not run.') + '</p>'; setStatus('Error', 'error'); })
        .finally(function() { build.disabled = false; });
    }

    build.addEventListener('click', function() { runBuild(); });
    textarea.addEventListener('keydown', function(event) { if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') runBuild(); });
    examples.forEach(function(button) { button.addEventListener('click', function() { textarea.value = button.getAttribute('data-sc-rl-path-example') || ''; runBuild(textarea.value); }); });
    copy.addEventListener('click', function() { if (!latest) { setStatus('Build first', 'error'); return; } if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(renderPathMarkdown(latest)).then(function(){ setStatus('Copied', 'ready'); }); });
    download.addEventListener('click', function() { if (!latest) { setStatus('Build first', 'error'); return; } downloadJson('sustainable-catalyst-guided-path.json', latest); setStatus('Downloaded', 'ready'); });
    save.addEventListener('click', function() {
      if (!latest) { setStatus('Build first', 'error'); return; }
      if (!saveEndpoint) { setStatus('Save unavailable', 'error'); return; }
      setStatus('Saving path…', 'loading');
      fetch(saveEndpoint, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce }, body: JSON.stringify({ path: latest }) })
        .then(function(response) { return response.json().then(function(data) { if (!response.ok) throw new Error(data && data.message ? data.message : 'Path could not be saved.'); return data; }); })
        .then(function(){ setStatus('Path saved', 'ready'); })
        .catch(function(error){ setStatus(error.message || 'Save failed', 'error'); });
    });
  }


  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.sc-rl-ai').forEach(init);
    document.querySelectorAll('.sc-rl-path-builder').forEach(initPathBuilder);
  });
}());
