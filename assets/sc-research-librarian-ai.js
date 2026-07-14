(function () {
  'use strict';

  var runtime = window.SCResearchLibrarianRuntime = window.SCResearchLibrarianRuntime || {
    health: {},
    routes: {},
    suggestions: {},
    suggestionOrder: []
  };

  function nowMs() { return Date.now ? Date.now() : new Date().getTime(); }

  function prefersReducedMotion() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  function nextFrame(callback) {
    if (prefersReducedMotion() || !window.requestAnimationFrame) { callback(); return; }
    window.requestAnimationFrame(callback);
  }

  function safeFocus(element) {
    if (!element || !element.focus) return;
    try { element.focus({ preventScroll: true }); } catch (e) { element.focus(); }
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(String(text || ''));
    return new Promise(function (resolve, reject) {
      var field = document.createElement('textarea');
      field.value = String(text || '');
      field.setAttribute('readonly', 'readonly');
      field.style.position = 'fixed';
      field.style.left = '-9999px';
      document.body.appendChild(field);
      field.select();
      try {
        if (!document.execCommand('copy')) throw new Error('Copy command unavailable.');
        resolve();
      } catch (error) { reject(error); }
      document.body.removeChild(field);
    });
  }

  function sharedJson(endpoint, bucketName, ttl, fetcher) {
    var bucket = runtime[bucketName] = runtime[bucketName] || {};
    var entry = bucket[endpoint];
    var current = nowMs();
    if (entry && entry.data && current - entry.time < ttl) return Promise.resolve(entry.data);
    if (entry && entry.promise) return entry.promise;
    var promise = fetcher().then(function (data) {
      bucket[endpoint] = { data: data, time: nowMs(), promise: null };
      return data;
    }).catch(function (error) {
      if (bucket[endpoint]) bucket[endpoint].promise = null;
      throw error;
    });
    bucket[endpoint] = { data: entry && entry.data, time: entry && entry.time || 0, promise: promise };
    return promise;
  }

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
    window.setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function downloadText(filename, text, mime) {
    var blob = new Blob([String(text || '')], { type: mime || 'text/plain;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function workspaceMarkdown(data, question) {
    data = data || {};
    var grounding = data.grounding || {};
    var workspace = data.workspace || grounding.workspace || {};
    var sources = data.matches || grounding.sources || [];
    var path = data.research_path || grounding.research_path || [];
    var lines = ['# Sustainable Catalyst Research Workspace', '', 'Question: ' + (question || ''), 'Mode: ' + (workspace.mode_label || data.research_mode || grounding.research_mode || 'Auto-detect'), 'Generated: ' + (data.generated_utc || new Date().toISOString()), '', '## Answer', '', data.answer || ''];
    if (sources.length) {
      lines.push('', '## Verified Sources');
      sources.forEach(function (source) {
        var location = source.section || '';
        if (source.page) location += (location ? ', ' : '') + 'page ' + source.page;
        lines.push('- [' + (source.title || 'Untitled source') + '](' + (source.url || '#') + ')' + (location ? ' — ' + location : '') + (source.passage ? ' — ' + source.passage : ''));
      });
    }
    if (path.length) {
      lines.push('', '## Suggested Research Path');
      path.forEach(function (step, index) { lines.push((index + 1) + '. [' + (step.title || 'Open step') + '](' + (step.url || '#') + ') — ' + (step.reason || '')); });
    }
    lines.push('', '## Boundaries', '', 'This workspace is site-scoped to verified Sustainable Catalyst records. Generated synthesis remains reviewable and does not replace authoritative sources or professional judgment.');
    return lines.join('\n');
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
    var confidence = grounding.confidence || note.confidence || data.confidence || {};
    var sources = (data.matches || grounding.sources || note.sources || []).slice(0, 8);
    var related = (data.related_titles || grounding.related_titles || []).slice(0, 8);
    var researchPath = (data.research_path || grounding.research_path || []).slice(0, 6);
    var actions = (data.actions || grounding.actions || []).slice(0, 6);
    var typedHandoffs = (data.typed_handoffs || grounding.typed_handoffs || note.typed_handoffs || []).slice(0, 4);
    var capabilities = (data.capabilities || grounding.capabilities || note.capabilities || []).filter(function (item) { return item && item.available; });
    var reasonCodes = grounding.reason_codes || note.reason_codes || [];
    var citationVerification = data.citation_verification || grounding.citation_verification || note.citation_verification || {};
    var retrievalDiagnostics = data.retrieval_diagnostics || grounding.retrieval_diagnostics || note.retrieval_diagnostics || {};
    var ambiguity = grounding.ambiguity || note.ambiguity || [];
    var confidenceLevel = confidence.level || 'unknown';
    var routeUrl = route.url || (note.recommended_route && note.recommended_route.url) || '#';
    var routeTitle = route.title || (note.recommended_route && note.recommended_route.title) || 'Recommended route';
    var routeCategory = route.category || (note.recommended_route && note.recommended_route.category) || 'Knowledge Library';
    var routeDescription = route.description || (note.recommended_route && note.recommended_route.description) || note.intent || '';
    var clarification = data.clarification || '';

    var workspace = data.workspace || grounding.workspace || {};
    var researchMode = data.research_mode || grounding.research_mode || workspace.mode || 'auto';
    var modeLabel = workspace.mode_label || String(researchMode).replace(/-/g, ' ');
    var answerKind = workspace.answer_kind || (data.ai_used ? 'citation-verified-ai' : 'deterministic-evidence');
    var html = '<div class="sc-rl-production-answer">';
    html += '<header class="sc-rl-production-answer__workspace-head"><div><span>Production research workspace</span><h3 tabindex="-1" data-sc-rl-result-heading>' + escapeHtml(modeLabel) + '</h3></div><div><b>' + escapeHtml(data.ai_used ? 'Verified AI synthesis' : 'Verified evidence fallback') + '</b><small>' + escapeHtml(sources.length + ' source' + (sources.length === 1 ? '' : 's')) + '</small></div></header>';
    html += '<section class="sc-rl-production-answer__response">';
    html += '<div class="sc-rl-production-answer__label">Direct response · ' + escapeHtml(answerKind.replace(/-/g, ' ')) + '</div>';
    html += (fallbackHtml || '');
    if (clarification) html += '<div class="sc-rl-production-answer__clarification"><strong>One useful clarification</strong><p>' + escapeHtml(clarification) + '</p></div>';
    html += '</section>';

    html += '<section class="sc-rl-production-answer__best">';
    html += '<div class="sc-rl-production-answer__head"><div><span>' + escapeHtml(routeCategory) + '</span><h3>' + escapeHtml(routeTitle) + '</h3></div><b class="sc-rl-answer-ux__badge ' + confidenceClass(confidenceLevel) + '">' + escapeHtml(String(confidenceLevel).toUpperCase()) + '</b></div>';
    if (routeDescription) html += '<p>' + escapeHtml(routeDescription) + '</p>';
    html += '<a class="sc-rl-production-answer__primary" href="' + escapeHtml(routeUrl) + '">Open best match →</a>';
    html += '</section>';

    if (sources.length) {
      html += '<section class="sc-rl-production-answer__section"><div class="sc-rl-production-answer__section-head"><div><span>Knowledge Library intelligence</span><h3>Best matches</h3></div><strong>' + sources.length + ' verified title' + (sources.length === 1 ? '' : 's') + '</strong></div>';
      html += '<div class="sc-rl-production-answer__source-grid">' + sources.map(function (source, index) {
        var exact = source.exact_title_match ? '<em>Exact title</em>' : '';
        var relationship = source.series || source.article_map || source.parent_title || '';
        var evidenceLabel = source.citation_label || (source.evidence_id ? '[' + source.evidence_id + ']' : '');
        var location = source.section || '';
        if (source.page) location += (location ? ' · ' : '') + 'Page ' + source.page;
        var excerpt = source.passage || source.summary || '';
        return '<article class="sc-rl-production-answer__source-card' + (index === 0 ? ' is-best' : '') + '"><div><span>' + escapeHtml(source.type || source.post_type || source.route_id || 'Public source') + '</span>' + exact + '</div><h4><a href="' + escapeHtml(source.url || '#') + '">' + escapeHtml(source.title || 'Untitled source') + '</a></h4>' + ((evidenceLabel || location) ? '<small class="sc-rl-production-answer__evidence-location">' + escapeHtml([evidenceLabel, location].filter(Boolean).join(' · ')) + '</small>' : '') + '<p>' + escapeHtml(excerpt) + '</p>' + (relationship ? '<small>' + escapeHtml(relationship) + '</small>' : '') + '</article>';
      }).join('') + '</div></section>';
    } else {
      html += '<section class="sc-rl-production-answer__empty"><strong>No verified title match yet.</strong><p>Try the exact title, series name, country, subject, calculation, or intended output.</p></section>';
    }

    if (researchPath.length) {
      html += '<section class="sc-rl-production-answer__section"><div class="sc-rl-production-answer__section-head"><div><span>Guided continuation</span><h3>Suggested research path</h3></div></div><ol class="sc-rl-production-answer__path">';
      researchPath.forEach(function (step) {
        html += '<li><a href="' + escapeHtml(step.url || '#') + '">' + escapeHtml(step.title || 'Open step') + '</a><span>' + escapeHtml(step.reason || '') + '</span></li>';
      });
      html += '</ol></section>';
    }

    if (related.length) {
      html += '<section class="sc-rl-production-answer__section"><div class="sc-rl-production-answer__section-head"><div><span>Connected knowledge</span><h3>Related titles</h3></div></div><div class="sc-rl-production-answer__related">';
      related.forEach(function (item) {
        html += '<a href="' + escapeHtml(item.url || '#') + '"><strong>' + escapeHtml(item.title || 'Related title') + '</strong><span>' + escapeHtml(item.series || item.article_map || item.summary || '') + '</span></a>';
      });
      html += '</div></section>';
    }

    html += '<section class="sc-rl-production-answer__actions"><div class="sc-rl-production-answer__section-head"><div><span>Continue</span><h3>Next actions</h3></div></div><div>';
    if (actions.length) {
      actions.forEach(function (action) {
        if (action.handoff) {
          html += '<button type="button" data-sc-rl-prepare-typed-handoff="' + escapeHtml(action.handoff) + '" data-destination-url="' + escapeHtml(action.url || '#') + '">' + escapeHtml(action.label || 'Prepare handoff') + '</button>';
        } else {
          html += '<a href="' + escapeHtml(action.url || '#') + '">' + escapeHtml(action.label || 'Open action') + '</a>';
        }
      });
    } else {
      html += '<a href="' + escapeHtml(routeUrl) + '">Open best match</a><a href="/platform/feature-suggestions/">Report a missing route</a>';
    }
    html += '</div></section>';

    if (typedHandoffs.length || capabilities.length) {
      html += '<section class="sc-rl-production-answer__section sc-rl-production-answer__handoffs"><div class="sc-rl-production-answer__section-head"><div><span>Connected platform</span><h3>Typed research handoffs</h3></div><strong>' + escapeHtml(typedHandoffs.length + ' prepared') + '</strong></div>';
      html += '<div class="sc-rl-production-answer__handoff-grid">';
      typedHandoffs.forEach(function (handoff) {
        var routeInfo = handoff.route || {};
        var validation = handoff.validation || {};
        var destination = handoff.destination || routeInfo.destination || 'platform';
        html += '<article><div><span>' + escapeHtml((routeInfo.destination_version || 'version unknown')) + '</span><b>' + escapeHtml(validation.ok === false ? 'Needs review' : 'Validated') + '</b></div><h4>' + escapeHtml(routeInfo.destination_label || destination.replace(/_/g, ' ')) + '</h4><p>' + escapeHtml(routeInfo.reason || 'Prepared from verified Sustainable Catalyst evidence.') + '</p><small>' + escapeHtml((handoff.evidence || []).length + ' verified source' + ((handoff.evidence || []).length === 1 ? '' : 's') + ' · ' + (handoff.payload && handoff.payload.contract ? handoff.payload.contract : handoff.schema || 'typed contract')) + '</small><div><button type="button" data-sc-rl-download-typed-handoff="' + escapeHtml(handoff.handoff_id || destination) + '">Download payload</button><a href="' + escapeHtml(routeInfo.destination_url || '#') + '">Open destination →</a></div></article>';
      });
      if (!typedHandoffs.length) {
        capabilities.slice(0, 4).forEach(function (capability) {
          html += '<article><div><span>' + escapeHtml(capability.version || 'version unknown') + '</span><b>Available</b></div><h4>' + escapeHtml(capability.label || capability.id) + '</h4><p>Prepare a versioned handoff with verified evidence and provenance.</p><div><button type="button" data-sc-rl-prepare-typed-handoff="' + escapeHtml(capability.id || '') + '" data-destination-url="' + escapeHtml(capability.url || '#') + '">Prepare payload</button><a href="' + escapeHtml(capability.url || '#') + '">Open destination →</a></div></article>';
        });
      }
      html += '</div></section>';
    }

    html += '<details class="sc-rl-production-answer__details"><summary>Why these results?</summary>';
    html += '<p><strong>Confidence:</strong> ' + escapeHtml(confidence.explanation || 'Based on title, slug, heading, series, article-map, taxonomy, and content matches.') + '</p>';
    if (reasonCodes.length) html += '<p><strong>Retrieval signals:</strong> ' + reasonCodes.map(escapeHtml).join(', ') + '</p>';
    if (ambiguity.length) html += '<p><strong>Ambiguity:</strong> ' + ambiguity.map(escapeHtml).join(', ') + '</p>';
    if (citationVerification && Object.keys(citationVerification).length) html += '<p><strong>Citation verification:</strong> ' + (citationVerification.ok ? 'Passed' : 'Fallback used') + ' · ' + escapeHtml(String(citationVerification.citation_count || 0)) + ' citation token(s).</p>';
    if (retrievalDiagnostics && retrievalDiagnostics.retrieval_mode) html += '<p><strong>Retrieval mode:</strong> ' + escapeHtml(retrievalDiagnostics.retrieval_mode) + (retrievalDiagnostics.semantic_coverage !== undefined ? ' · semantic coverage ' + escapeHtml(String(retrievalDiagnostics.semantic_coverage)) + '%' : '') + '</p>';
    html += '<p>Internal scores are available in the downloadable route record but are intentionally hidden from the primary public answer.</p>';
    html += '</details>';
    html += '</div>';

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
    var aiStatusEndpoint = root.getAttribute('data-ai-status-endpoint');
    var suggestEndpoint = root.getAttribute('data-suggest-endpoint');
    var nonceEndpoint = root.getAttribute('data-nonce-endpoint');
    var routesEndpoint = root.getAttribute('data-routes-endpoint');
    var sessionEndpoint = root.getAttribute('data-session-endpoint');
    var feedbackEndpoint = root.getAttribute('data-feedback-endpoint');
    var feedbackBridgeEndpoint = root.getAttribute('data-feedback-bridge-endpoint');
    var deepLinkEndpoint = root.getAttribute('data-deep-link-endpoint');
    var platformCapabilitiesEndpoint = root.getAttribute('data-platform-capabilities-endpoint');
    var platformHandoffEndpoint = root.getAttribute('data-platform-handoff-endpoint');
    var platformHandoffValidateEndpoint = root.getAttribute('data-platform-handoff-validate-endpoint');
    var artifactReturnEndpoint = root.getAttribute('data-artifact-return-endpoint');
    var nonce = root.getAttribute('data-nonce');
    var textarea = root.querySelector('.sc-rl-ai__textarea');
    var submit = root.querySelector('[data-sc-rl-submit]');
    var clear = root.querySelector('[data-sc-rl-clear]');
    var copy = root.querySelector('[data-sc-rl-copy]');
    var copyAnswer = root.querySelector('[data-sc-rl-copy-answer]');
    var download = root.querySelector('[data-sc-rl-download]');
    var downloadMarkdown = root.querySelector('[data-sc-rl-download-markdown]');
    var researchNote = root.querySelector('[data-sc-rl-research-note]');
    var printButton = root.querySelector('[data-sc-rl-print]');
    var handoffDownload = root.querySelector('[data-sc-rl-handoff-download]');
    var saveSession = root.querySelector('[data-sc-rl-save-session]');
    var feedbackHelpful = root.querySelector('[data-sc-rl-feedback-helpful]');
    var feedbackIssue = root.querySelector('[data-sc-rl-feedback-issue]');
    var answer = root.querySelector('[data-sc-rl-answer]');
    var status = root.querySelector('[data-sc-rl-status]');
    var answerCard = root.querySelector('.sc-rl-ai__answer-card');
    var health = root.querySelector('[data-sc-rl-ai-health]');
    var healthLabel = root.querySelector('[data-sc-rl-ai-health-label]');
    var healthDetail = root.querySelector('[data-sc-rl-ai-health-detail]');
    var honeypot = root.querySelector('.sc-rl-ai__hp');
    var examples = root.querySelectorAll('[data-sc-rl-example]');
    var routeSummary = root.querySelector('[data-sc-rl-route-summary]');
    var answerUx = root.querySelector('[data-sc-rl-answer-ux]');
    var routeStrip = root.querySelector('[data-sc-rl-route-strip]');
    var suggestionsBox = root.querySelector('[data-sc-rl-title-suggestions]');
    var modeButtons = root.querySelectorAll('[data-sc-rl-mode]');
    var modeLabel = root.querySelector('[data-sc-rl-mode-label]');
    var progress = root.querySelector('[data-sc-rl-progress]');
    var progressBar = root.querySelector('[data-sc-rl-progress-bar]');
    var progressLabel = root.querySelector('[data-sc-rl-progress-label]');
    var sessionBar = root.querySelector('[data-sc-rl-session-bar]');
    var sessionMode = root.querySelector('[data-sc-rl-session-mode]');
    var sessionTurns = root.querySelector('[data-sc-rl-session-turns]');
    var resetSession = root.querySelector('[data-sc-rl-reset-session]');
    var followUps = root.querySelector('[data-sc-rl-follow-ups]');
    var followUpList = root.querySelector('[data-sc-rl-follow-up-list]');
    var announcer = root.querySelector('[data-sc-rl-announcer]');
    var feedbackDialog = root.querySelector('[data-sc-rl-feedback-dialog]');
    var feedbackSubmit = root.querySelector('[data-sc-rl-feedback-submit]');
    var feedbackCancelButtons = root.querySelectorAll('[data-sc-rl-feedback-cancel]');
    var feedbackType = root.querySelector('[data-sc-rl-feedback-type]');
    var feedbackRating = root.querySelector('[data-sc-rl-feedback-rating]');
    var feedbackNote = root.querySelector('[data-sc-rl-feedback-note]');
    var feedbackExpected = root.querySelector('[data-sc-rl-feedback-expected]');
    var feedbackTypeRow = root.querySelector('[data-sc-rl-feedback-type-row]');
    var feedbackRatingRow = root.querySelector('[data-sc-rl-feedback-rating-row]');
    var feedbackExpectedRow = root.querySelector('[data-sc-rl-feedback-expected-row]');
    var latest = null;
    var currentAskController = null;
    var currentAskKey = '';
    var currentAskSequence = 0;
    var suggestionController = null;
    var suggestionSequence = 0;
    var activeSuggestionIndex = -1;
    var feedbackMode = 'issue';
    var sessionId = '';
    try { sessionId = window.localStorage.getItem('sc_rl_ai_session_id') || ''; } catch (e) { sessionId = ''; }
    var suggestionTimer = null;
    var currentMode = 'auto';
    try { currentMode = window.localStorage.getItem('sc_rl_ai_research_mode') || 'auto'; } catch (e) { currentMode = 'auto'; }
    var modeCopy = {
      auto: ['Auto-detect', 'What are you trying to understand, find, compare, analyze, or prepare?'],
      title: ['Find a title', 'Enter an exact or partial Sustainable Catalyst title.'],
      subject: ['Explore a subject', 'What subject or concept should the Library explain and connect?'],
      path: ['Build a research path', 'What do you want to learn, and what should the ordered path lead toward?'],
      evidence: ['Find evidence', 'What claim, question, passage, or document needs supporting evidence?'],
      analyze: ['Analyze a question', 'What assumptions, variables, formula, data, or method should be analyzed?'],
      compare: ['Compare records', 'Which titles, concepts, places, or approaches should be compared?'],
      decision: ['Prepare a decision', 'What decision, alternatives, evidence, and uncertainty should be organized?']
    };

    function announce(text, assertive) {
      if (!announcer || !text) return;
      announcer.setAttribute('aria-live', assertive ? 'assertive' : 'polite');
      announcer.textContent = '';
      window.setTimeout(function () { announcer.textContent = String(text); }, 20);
    }

    function setStatus(text, state) {
      if (status) {
        status.textContent = text;
        status.setAttribute('data-status-state', state || 'ready');
      }
      root.setAttribute('data-state', state || 'ready');
      if (answerCard) answerCard.setAttribute('aria-busy', state === 'loading' ? 'true' : 'false');
    }

    function setMode(mode, preserveQuestion) {
      currentMode = modeCopy[mode] ? mode : 'auto';
      modeButtons.forEach(function (button) {
        var active = button.getAttribute('data-sc-rl-mode') === currentMode;
        button.classList.toggle('is-active', active);
        button.setAttribute('aria-checked', active ? 'true' : 'false');
        button.setAttribute('tabindex', active ? '0' : '-1');
      });
      if (modeLabel) modeLabel.textContent = modeCopy[currentMode][0];
      if (textarea && (!preserveQuestion || !textarea.value.trim())) textarea.setAttribute('placeholder', modeCopy[currentMode][1]);
      try { window.localStorage.setItem('sc_rl_ai_research_mode', currentMode); } catch (e) {}
    }

    function setProgress(visible, percent, label) {
      if (!progress) return;
      var value = Math.max(0, Math.min(100, Number(percent) || 0));
      progress.hidden = !visible;
      progress.setAttribute('aria-hidden', visible ? 'false' : 'true');
      progress.setAttribute('aria-valuenow', String(value));
      progress.setAttribute('aria-valuetext', label || (visible ? 'Working' : 'Workspace ready'));
      if (progressBar) progressBar.style.width = value + '%';
      if (progressLabel && label) progressLabel.textContent = label;
    }

    function updateSession(data) {
      if (!sessionBar) return;
      var workspace = (data && data.workspace) || (data && data.grounding && data.grounding.workspace) || {};
      var mode = (data && data.research_mode) || (data && data.grounding && data.grounding.research_mode) || currentMode;
      var turns = Number((data && data.session_turns) || (data && data.grounding && data.grounding.session_turns) || 0);
      sessionBar.hidden = false;
      if (sessionMode) sessionMode.textContent = workspace.mode_label || (modeCopy[mode] ? modeCopy[mode][0] : mode);
      if (sessionTurns) sessionTurns.textContent = turns ? turns + ' research turn' + (turns === 1 ? '' : 's') + ' in this session' : 'New research session';
    }

    function renderFollowUps(data) {
      if (!followUps || !followUpList) return;
      var prompts = (data && data.follow_up_prompts) || (data && data.grounding && data.grounding.follow_up_prompts) || [];
      if (!prompts.length) { followUps.hidden = true; followUpList.innerHTML = ''; return; }
      followUpList.innerHTML = prompts.slice(0, 3).map(function (prompt) { return '<button type="button" data-sc-rl-follow-up="' + escapeHtml(prompt) + '">' + escapeHtml(prompt) + '</button>'; }).join('');
      followUps.hidden = false;
    }

    function formatHealthTime(value) {
      if (!value) return '';
      var parsed = new Date(value);
      return isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString();
    }

    function renderHealth(payload) {
      if (!health || !healthLabel || !healthDetail || !payload) return;
      var state = String(payload.state || 'not-tested');
      var provider = String(payload.provider || 'disabled');
      var model = String(payload.model || '');
      var detail = '';
      root.setAttribute('data-ai-health', state);
      health.setAttribute('data-ai-health-state', state);
      healthLabel.textContent = payload.label || 'AI status unavailable';
      if (state === 'online') {
        detail = (provider !== 'disabled' ? provider.charAt(0).toUpperCase() + provider.slice(1) : 'AI') + (model ? ' · ' + model : '');
        if (payload.semantic_retrieval) detail += ' · ' + payload.semantic_retrieval;
        if (payload.indexed_titles !== undefined) detail += ' · ' + payload.indexed_titles + ' indexed titles';
        else if (payload.indexed_records !== undefined) detail += ' · ' + payload.indexed_records + ' indexed records';
        if (payload.last_sync_utc) detail += ' · library synced ' + formatHealthTime(payload.last_sync_utc);
        else if (payload.last_success_utc) detail += ' · last success ' + formatHealthTime(payload.last_success_utc);
      } else if (state === 'retrieval-only') {
        detail = 'Python title-aware retrieval is online';
        if (payload.indexed_titles !== undefined) detail += ' · ' + payload.indexed_titles + ' indexed titles';
        detail += ' · AI generation is unavailable';
      } else if (state === 'ready') {
        detail = 'Python knowledge index is ready';
        if (payload.indexed_titles !== undefined) detail += ' · ' + payload.indexed_titles + ' indexed titles';
        detail += ' · awaiting first successful AI answer';
      } else if (state === 'offline') {
        detail = 'AI or Python backend request failed · verified title-aware fallback remains active when available';
        if (payload.last_failure_utc) detail += ' · checked ' + formatHealthTime(payload.last_failure_utc);
      } else if (state === 'not-configured' || state === 'backend-not-configured') {
        detail = 'No live provider or authenticated Python connection is configured · verified local routing remains active';
      } else if (state === 'needs-sync' || state === 'index-empty') {
        detail = 'The Python service is reachable, but the Knowledge Library index is empty · run Repair Endpoint and Resynchronize';
      } else if (state === 'backend-warming') {
        detail = 'The free Render service is starting';
        if (payload.startup_phase) detail += ' · ' + String(payload.startup_phase).replace(/-/g, ' ');
        if (payload.startup_progress !== undefined) detail += ' · ' + Math.max(0, Math.min(100, Number(payload.startup_progress) || 0)) + '%';
        if (payload.recovery_progress && payload.recovery_progress.phase) {
          detail += ' · recovery ' + String(payload.recovery_progress.phase).replace(/-/g, ' ');
          if (payload.recovery_progress.progress !== undefined) detail += ' ' + Math.max(0, Math.min(100, Number(payload.recovery_progress.progress) || 0)) + '%';
        }
        detail += ' · verified WordPress fallback remains available';
      } else if (state === 'integration-key-mismatch') {
        detail = 'WordPress reached Python, but the shared integration key was rejected';
      } else if (state === 'backend-rate-limited') {
        detail = 'The Python service temporarily rejected requests because of a rate limit';
      } else if (state === 'backend-unreachable' || state === 'backend-unavailable' || state === 'backend-invalid-response') {
        detail = 'The Python endpoint is temporarily unavailable · verified WordPress fallback remains active';
      } else if (state === 'hidden') {
        detail = 'Verified fallback routing remains available.';
      } else {
        detail = (provider !== 'disabled' ? provider.charAt(0).toUpperCase() + provider.slice(1) : 'AI') + (model ? ' · ' + model : '') + ' · knowledge service status is being verified';
      }
      healthDetail.textContent = detail;
      if (state === 'backend-warming') setProgress(true, payload.startup_progress || 20, 'Starting knowledge service · verified fallback remains available');
      else if (root.getAttribute('data-state') !== 'loading') setProgress(false, 100, 'Workspace ready');
    }

    function responseError(response, data) {
      var error = new Error((data && data.message) || 'The Research Librarian request failed.');
      error.status = response.status || 0;
      error.code = data && data.code ? String(data.code) : '';
      error.data = data && data.data ? data.data : {};
      error.retryAfter = Number(response.headers.get('Retry-After') || (error.data && error.data.retry_after) || 0);
      return error;
    }

    function parseJsonResponse(response) {
      return response.text().then(function (text) {
        var data = {};
        if (text) {
          try { data = JSON.parse(text); }
          catch (e) {
            var invalid = new Error('The WordPress endpoint returned an invalid response.');
            invalid.status = response.status || 0;
            invalid.code = 'invalid_json';
            throw invalid;
          }
        }
        if (!response.ok) throw responseError(response, data);
        return data;
      });
    }

    function refreshNonce() {
      if (!nonceEndpoint) return Promise.reject(new Error('Nonce refresh endpoint is unavailable.'));
      return fetch(nonceEndpoint, { credentials: 'same-origin', cache: 'no-store' })
        .then(parseJsonResponse)
        .then(function (data) {
          if (!data || !data.nonce) throw new Error('WordPress did not return a refreshed security token.');
          nonce = String(data.nonce);
          root.setAttribute('data-nonce', nonce);
          return nonce;
        });
    }

    function fetchWithNonce(url, options, allowRetry) {
      options = options || {};
      options.credentials = 'same-origin';
      options.headers = options.headers || {};
      options.headers['X-WP-Nonce'] = nonce;
      return fetch(url, options).then(parseJsonResponse).catch(function (error) {
        var nonceFailure = error && (error.code === 'sc_rl_ai_bad_nonce' || error.code === 'sc_rl_v621_bad_nonce' || error.status === 403);
        if (allowRetry !== false && nonceFailure && nonceEndpoint) {
          return refreshNonce().then(function () { return fetchWithNonce(url, options, false); });
        }
        throw error;
      });
    }

    function endpointFailureCopy(error) {
      var code = error && error.code ? error.code : '';
      var statusCode = error && error.status ? Number(error.status) : 0;
      if (code === 'sc_rl_ai_rate_limit' || statusCode === 429) {
        var minutes = error.retryAfter ? Math.max(1, Math.ceil(error.retryAfter / 60)) : 0;
        return {
          label: 'Question limit reached',
          intro: minutes ? 'The public question limit has been reached. Try again in about ' + minutes + ' minute(s).' : (error.message || 'The public question limit has been reached.'),
          detail: 'This limit applies to successful public questions. Empty prompts, health checks, and expired security tokens do not consume the allowance.'
        };
      }
      if (code === 'sc_rl_ai_bad_nonce' || code === 'sc_rl_v621_bad_nonce' || statusCode === 403) {
        return { label: 'Security session expired', intro: 'The WordPress security token could not be refreshed.', detail: 'Reload this page and submit the question again.' };
      }
      if (code === 'invalid_json') {
        return { label: 'Invalid endpoint response', intro: 'WordPress returned a response that the Research Librarian could not read.', detail: 'Check caching, security, or REST-response modification plugins.' };
      }
      if (statusCode === 404) {
        return { label: 'WordPress route unavailable', intro: 'The Research Librarian REST route was not found.', detail: 'Resave WordPress permalinks and confirm that the active v6.6.0 plugin registered its routes.' };
      }
      if (statusCode >= 500) {
        return { label: 'WordPress endpoint error', intro: 'WordPress reached the Research Librarian route but returned a server error.', detail: 'The Python provider status is separate from this WordPress failure.' };
      }
      if (!statusCode) {
        return { label: 'WordPress endpoint unreachable', intro: 'The browser could not reach the Research Librarian WordPress endpoint.', detail: 'Check the site connection, Cloudflare, REST restrictions, or browser network controls.' };
      }
      return { label: 'Request unavailable', intro: error && error.message ? error.message : 'The Research Librarian request could not be completed.', detail: 'The Python and AI status indicators may still be online because they are separate from this browser-to-WordPress request.' };
    }

    function endpointNoticeHtml(endpointStatus) {
      if (!endpointStatus || !endpointStatus.label || endpointStatus.state === 'online' || endpointStatus.suppress_notice) return '';
      return '<aside class="sc-rl-ai__endpoint-notice" role="status"><strong>' + escapeHtml(endpointStatus.label) + '</strong><span>' + escapeHtml(endpointStatus.message || '') + '</span></aside>';
    }

    function loadHealth() {
      if (!aiStatusEndpoint) return;
      sharedJson(aiStatusEndpoint, 'health', 45000, function () {
        return fetch(aiStatusEndpoint, { credentials: 'same-origin', cache: 'no-store' })
          .then(function (response) {
            return response.json().then(function (data) {
              if (!response.ok) throw new Error('AI status unavailable');
              return data;
            });
          });
      }).then(renderHealth).catch(function () {
        renderHealth({ state: 'offline', label: 'AI Status Unavailable', provider: 'disabled', fallback_active: true });
        if (healthDetail) healthDetail.textContent = 'The status endpoint could not be reached · verified fallback routing may still be available.';
      });
    }

    function ask(question) {
      var clean = (question || textarea.value || '').trim();
      if (!clean) {
        setStatus('Add a question', 'error');
        answer.innerHTML = '<p>Please enter a question first.</p>';
        safeFocus(textarea);
        return;
      }

      var askKey = currentMode + '|' + clean.toLowerCase();
      if (currentAskController && currentAskKey === askKey) {
        setStatus('Already researching this question…', 'loading');
        return;
      }
      if (currentAskController && currentAskController.abort) currentAskController.abort();
      currentAskController = window.AbortController ? new AbortController() : null;
      currentAskKey = askKey;
      currentAskSequence += 1;
      var sequence = currentAskSequence;

      setStatus('Researching…', 'loading');
      setProgress(true, 18, 'Interpreting the research task');
      submit.disabled = true;
      submit.setAttribute('aria-disabled', 'true');
      answer.hidden = false;
      answer.innerHTML = '<p class="sc-rl-ai__loading">Searching indexed Sustainable Catalyst titles, series, article maps, headings, sources, and platform actions</p>';
      if (answerUx) { answerUx.hidden = true; answerUx.innerHTML = ''; }

      var requestOptions = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: clean, research_mode: currentMode, hp: honeypot ? honeypot.value : '', session_id: sessionId })
      };
      if (currentAskController) requestOptions.signal = currentAskController.signal;

      fetchWithNonce(endpoint, requestOptions, true)
        .then(function (data) {
          if (sequence !== currentAskSequence) return;
          latest = data;
          setProgress(true, 72, 'Preparing the direct response');
          if (data.session_id) { sessionId = String(data.session_id); try { window.localStorage.setItem('sc_rl_ai_session_id', sessionId); } catch (e) {} }
          if (data.ai_status) renderHealth(data.ai_status);
          if (data.ai_used) {
            setStatus('Grounded AI answer', 'ready');
          } else if (data.source === 'boundary') {
            setStatus('Boundary guidance', 'ready');
          } else {
            setStatus(data.source && String(data.source).indexOf('python') !== -1 ? 'Title-aware answer' : 'Verified fallback', data.ai_status && data.ai_status.state === 'offline' ? 'error' : 'ready');
          }
          if (data.endpoint_status && data.endpoint_status.label && data.endpoint_status.state !== 'online') {
            setStatus(data.endpoint_status.label, data.endpoint_status.state === 'retrieval-only' || data.endpoint_status.state === 'wordpress-fallback' ? 'ready' : 'error');
          }
          var renderedAnswer = renderMarkdownLite(data.answer || 'No answer was returned. Try the Platform or Feature Suggestions route.');
          var endpointNotice = endpointNoticeHtml(data.endpoint_status);
          answer.innerHTML = endpointNotice + renderedAnswer;
          renderRouteSummary(routeSummary, data.route, data.grounding);
          setMode(data.research_mode || (data.grounding && data.grounding.research_mode) || currentMode, true);
          updateSession(data);
          renderFollowUps(data);
          setProgress(true, 88, 'Rendering verified evidence and research actions');

          nextFrame(function () {
            if (sequence !== currentAskSequence) return;
            renderAnswerUx(answerUx, data, endpointNotice + renderedAnswer);
            if (answerUx) {
              answer.hidden = true;
              var heading = answerUx.querySelector('[data-sc-rl-result-heading]');
              safeFocus(heading);
            }
            setProgress(false, 100, 'Workspace ready');
            announce('Research workspace ready with ' + String((data.matches || (data.grounding && data.grounding.sources) || []).length) + ' verified sources.', false);
          });
        })
        .catch(function (error) {
          if (error && error.name === 'AbortError') return;
          if (sequence !== currentAskSequence) return;
          latest = null;
          setProgress(false, 100, 'Request unavailable');
          var failure = endpointFailureCopy(error);
          setStatus(failure.label, 'error');
          answer.hidden = false;
          answer.innerHTML = '<aside class="sc-rl-ai__endpoint-notice sc-rl-ai__endpoint-notice--error" role="alert" tabindex="-1"><strong>' + escapeHtml(failure.label) + '</strong><span>' + escapeHtml(failure.intro) + '</span><small>' + escapeHtml(failure.detail) + '</small></aside>' + renderMarkdownLite('**Verified starting points remain available**\n- [Site Intelligence](/platform/site-intelligence/)\n- [Platform](/platform/)\n- [Platform Demos](/platform/demos/)\n- [Workbench](https://sustainablecatalyst.com/modeling-analytics/workbench/)\n- [Decision Studio](/platform/decision-studio/)\n- [Feature Suggestions](/platform/feature-suggestions/)');
          safeFocus(answer.querySelector('[role="alert"]'));
        })
        .finally(function () {
          if (sequence !== currentAskSequence) return;
          submit.disabled = false;
          submit.removeAttribute('aria-disabled');
          currentAskController = null;
          currentAskKey = '';
        });
    }

    function hideSuggestions() {
      if (!suggestionsBox) return;
      suggestionsBox.hidden = true;
      suggestionsBox.innerHTML = '';
      activeSuggestionIndex = -1;
      textarea.setAttribute('aria-expanded', 'false');
      textarea.removeAttribute('aria-activedescendant');
    }

    function suggestionCacheKey(query) {
      return String(suggestEndpoint || '') + '|' + String(query || '').trim().toLowerCase();
    }

    function cacheSuggestions(key, suggestions) {
      runtime.suggestions[key] = { data: suggestions, time: nowMs() };
      runtime.suggestionOrder.push(key);
      while (runtime.suggestionOrder.length > 40) {
        var oldest = runtime.suggestionOrder.shift();
        if (oldest !== key) delete runtime.suggestions[oldest];
      }
    }

    function renderSuggestions(suggestions, query, cached) {
      if (!suggestionsBox) return;
      if (!suggestions.length) { hideSuggestions(); return; }
      activeSuggestionIndex = -1;
      suggestionsBox.innerHTML = '<div class="sc-rl-ai__title-suggestions-label" aria-hidden="true">Indexed Sustainable Catalyst titles' + (cached ? ' · cached' : '') + '</div>' + suggestions.map(function (item, index) {
        var optionId = root.id + '-suggestion-' + index;
        return '<button id="' + escapeHtml(optionId) + '" type="button" role="option" aria-selected="false" tabindex="-1" data-sc-rl-title-suggestion="' + escapeHtml(item.title || '') + '" data-sc-rl-suggestion-index="' + index + '"><strong>' + escapeHtml(item.title || '') + '</strong><span>' + escapeHtml(item.summary || item.match_type || '') + '</span></button>';
      }).join('');
      suggestionsBox.hidden = false;
      textarea.setAttribute('aria-expanded', 'true');
      announce(suggestions.length + ' title suggestion' + (suggestions.length === 1 ? '' : 's') + ' available for ' + query + '.', false);
    }

    function setActiveSuggestion(index) {
      if (!suggestionsBox || suggestionsBox.hidden) return;
      var buttons = Array.prototype.slice.call(suggestionsBox.querySelectorAll('[role="option"]'));
      if (!buttons.length) return;
      activeSuggestionIndex = (index + buttons.length) % buttons.length;
      buttons.forEach(function (button, buttonIndex) {
        var selected = buttonIndex === activeSuggestionIndex;
        button.setAttribute('aria-selected', selected ? 'true' : 'false');
        button.classList.toggle('is-active', selected);
      });
      textarea.setAttribute('aria-activedescendant', buttons[activeSuggestionIndex].id);
      try {
        buttons[activeSuggestionIndex].scrollIntoView({ block: 'nearest' });
      } catch (error) {
        buttons[activeSuggestionIndex].scrollIntoView(false);
      }
      announce(buttons[activeSuggestionIndex].textContent, false);
    }

    function chooseSuggestion(button) {
      if (!button) return;
      textarea.value = button.getAttribute('data-sc-rl-title-suggestion') || '';
      setMode('title', true);
      hideSuggestions();
      ask(textarea.value);
    }

    function loadSuggestions() {
      if (!suggestEndpoint || !suggestionsBox) return;
      var query = (textarea.value || '').trim();
      if (query.length < 2) { hideSuggestions(); return; }
      var key = suggestionCacheKey(query);
      var cached = runtime.suggestions[key];
      if (cached && nowMs() - cached.time < 300000) {
        renderSuggestions(cached.data || [], query, true);
        return;
      }
      if (suggestionController && suggestionController.abort) suggestionController.abort();
      suggestionController = window.AbortController ? new AbortController() : null;
      suggestionSequence += 1;
      var sequence = suggestionSequence;
      var options = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query })
      };
      if (suggestionController) options.signal = suggestionController.signal;
      fetchWithNonce(suggestEndpoint, options, true)
        .then(function (data) {
          if (sequence !== suggestionSequence || query !== (textarea.value || '').trim()) return;
          var suggestions = data && data.suggestions ? data.suggestions : [];
          cacheSuggestions(key, suggestions);
          renderSuggestions(suggestions, query, !!(data && data.cached));
        }).catch(function (error) {
          if (error && error.name === 'AbortError') return;
          if (sequence === suggestionSequence) hideSuggestions();
        });
    }

    textarea.addEventListener('input', function () {
      window.clearTimeout(suggestionTimer);
      activeSuggestionIndex = -1;
      textarea.removeAttribute('aria-activedescendant');
      suggestionTimer = window.setTimeout(loadSuggestions, 220);
    });
    if (suggestionsBox) {
      suggestionsBox.addEventListener('click', function (event) {
        var button = event.target.closest ? event.target.closest('[data-sc-rl-title-suggestion]') : null;
        chooseSuggestion(button);
      });
    }
    document.addEventListener('click', function (event) {
      if (!root.contains(event.target)) hideSuggestions();
    });

    submit.addEventListener('click', function () { hideSuggestions(); ask(); });
    textarea.addEventListener('keydown', function (event) {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        event.preventDefault();
        hideSuggestions();
        ask();
        return;
      }
      if (suggestionsBox && !suggestionsBox.hidden && event.key === 'ArrowDown') {
        event.preventDefault();
        setActiveSuggestion(activeSuggestionIndex + 1);
        return;
      }
      if (suggestionsBox && !suggestionsBox.hidden && event.key === 'ArrowUp') {
        event.preventDefault();
        setActiveSuggestion(activeSuggestionIndex < 0 ? -1 : activeSuggestionIndex - 1);
        return;
      }
      if (suggestionsBox && !suggestionsBox.hidden && event.key === 'Enter' && activeSuggestionIndex >= 0) {
        event.preventDefault();
        chooseSuggestion(suggestionsBox.querySelectorAll('[role="option"]')[activeSuggestionIndex]);
        return;
      }
      if (event.key === 'Escape') hideSuggestions();
    });

    clear.addEventListener('click', function () {
      if (currentAskController && currentAskController.abort) currentAskController.abort();
      currentAskSequence += 1;
      currentAskController = null;
      currentAskKey = '';
      hideSuggestions();
      textarea.value = '';
      latest = null;
      setStatus('Ready for a question', 'ready');
      answer.hidden = false;
      answer.innerHTML = '<p>Ask about an exact title, subject, country, source, calculation, dashboard, or decision workflow. Research Librarian AI will search the indexed library and show the strongest verified matches.</p>';
      if (routeSummary) { routeSummary.hidden = true; routeSummary.innerHTML = ''; }
      if (answerUx) { answerUx.hidden = true; answerUx.innerHTML = ''; }
      if (followUps) { followUps.hidden = true; followUpList.innerHTML = ''; }
      setProgress(false, 100, 'Workspace ready');
      safeFocus(textarea);
    });
    if (copyAnswer) {
      copyAnswer.addEventListener('click', function () {
        if (!latest) { setStatus('Ask first', 'error'); return; }
        var text = workspaceMarkdown(latest, textarea ? textarea.value : '');
        copyText(text).then(function () { setStatus('Answer copied', 'ready'); }).catch(function () { setStatus('Copy unavailable', 'error'); });
      });
    }
    if (downloadMarkdown) {
      downloadMarkdown.addEventListener('click', function () {
        if (!latest) { setStatus('Ask first', 'error'); return; }
        downloadText('sustainable-catalyst-research-workspace.md', workspaceMarkdown(latest, textarea ? textarea.value : ''), 'text/markdown;charset=utf-8');
        setStatus('Markdown downloaded', 'ready');
      });
    }
    if (researchNote) {
      researchNote.addEventListener('click', function () {
        if (!latest) { setStatus('Ask first', 'error'); return; }
        var note = workspaceMarkdown(latest, textarea ? textarea.value : '') + '\n\n## Research Notes\n\n- Observation:\n- Question:\n- Assumption:\n- Next action:\n';
        downloadText('sustainable-catalyst-research-note.md', note, 'text/markdown;charset=utf-8');
        setStatus('Research note downloaded', 'ready');
      });
    }
    if (printButton) {
      printButton.addEventListener('click', function () {
        if (!latest) { setStatus('Ask first', 'error'); return; }
        root.classList.add('is-printing');
        window.print();
        window.setTimeout(function () { root.classList.remove('is-printing'); }, 300);
      });
    }

    copy.addEventListener('click', function () {
      if (!latest || !latest.route_note) {
        setStatus('Ask first', 'error');
        return;
      }
      var text = routeNoteMarkdown(latest.route_note);
      copyText(text).then(function () { setStatus('Copied', 'ready'); }).catch(function () { setStatus('Copy unavailable', 'error'); });
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
        var target = latest.route_note.handoff_payload.destination || latest.route_note.handoff_payload.target || 'handoff';
        downloadJson('sustainable-catalyst-' + target.replace(/_/g, '-') + '-handoff.json', latest.route_note.handoff_payload);
        setStatus('Handoff downloaded', 'ready');
      });
    }

    function typedHandoffById(handoffId) {
      var list = (latest && (latest.typed_handoffs || (latest.grounding && latest.grounding.typed_handoffs))) || [];
      for (var i = 0; i < list.length; i += 1) {
        if (String(list[i].handoff_id || '') === String(handoffId || '')) return list[i];
      }
      return null;
    }

    function prepareTypedHandoff(destination, button) {
      if (!latest || !platformHandoffEndpoint) { setStatus('Ask a question first', 'error'); return; }
      var sources = latest.matches || (latest.grounding && latest.grounding.sources) || [];
      var originalText = button ? button.textContent : '';
      if (button) { button.disabled = true; button.textContent = 'Preparing…'; }
      setStatus('Preparing typed handoff…', 'loading');
      fetchWithNonce(platformHandoffEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destination: destination,
          question: textarea ? textarea.value : '',
          research_mode: currentMode,
          session_id: sessionId,
          source_ids: sources.map(function (source) { return source.id || source.record_id || ''; }).filter(Boolean),
          evidence: latest.evidence || (latest.grounding && latest.grounding.evidence) || [],
          route_hint: {
            destination: destination,
            reason: 'Prepared from the public Research Librarian workspace after explicit user confirmation.',
            parent_handoff_id: latest.provenance && latest.provenance.handoff_ids ? latest.provenance.handoff_ids[0] || '' : ''
          }
        })
      }, true).then(function (result) {
        var handoff = result.handoff || (result.data && result.data.handoff);
        if (!handoff) throw new Error('The platform handoff endpoint returned no payload.');
        latest.typed_handoffs = latest.typed_handoffs || [];
        latest.typed_handoffs = latest.typed_handoffs.filter(function (item) { return item.destination !== handoff.destination; });
        latest.typed_handoffs.unshift(handoff);
        if (latest.route_note) latest.route_note.handoff_payload = handoff;
        downloadJson('sustainable-catalyst-' + String(handoff.destination || destination || 'platform').replace(/_/g, '-') + '-handoff.json', handoff);
        setStatus('Typed handoff prepared', 'ready');
        announce('Typed handoff prepared and downloaded for ' + String((handoff.route && handoff.route.destination_label) || handoff.destination || destination) + '.', false);
      }).catch(function (error) {
        setStatus('Handoff unavailable', 'error');
        announce(error.message || 'Unable to prepare the typed handoff.', true);
      }).finally(function () {
        if (button) { button.disabled = false; button.textContent = originalText; }
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
      if (target.matches('[data-sc-rl-download-typed-handoff]')) {
        var handoff = typedHandoffById(target.getAttribute('data-sc-rl-download-typed-handoff'));
        if (!handoff) { setStatus('Handoff preview unavailable', 'error'); return; }
        downloadJson('sustainable-catalyst-' + String(handoff.destination || 'platform').replace(/_/g, '-') + '-handoff.json', handoff);
        setStatus('Typed handoff downloaded', 'ready');
      }
      if (target.matches('[data-sc-rl-prepare-typed-handoff]')) {
        prepareTypedHandoff(target.getAttribute('data-sc-rl-prepare-typed-handoff') || '', target);
      }
      if (target.matches('[data-sc-rl-deep-link]')) {
        if (!latest || !deepLinkEndpoint) {
          setStatus('Deep-link action unavailable', 'error');
          return;
        }
        var destination = target.getAttribute('data-sc-rl-deep-link') || '';
        var requestedAction = target.getAttribute('data-sc-rl-action') || '';
        var route = latest.route || (latest.route_note && latest.route_note.recommended_route) || {};
        var grounding = latest.grounding || {};
        var confidence = grounding.confidence || (latest.route_note && latest.route_note.confidence) || {};
        var sources = (grounding.sources || (latest.route_note && latest.route_note.sources) || []).slice(0, 8);
        var originalText = target.textContent;
        target.disabled = true;
        target.textContent = 'Preparing…';
        setStatus('Preparing handoff…', 'loading');
        fetch(deepLinkEndpoint, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
          body: JSON.stringify({
            destination: destination,
            requested_action: requestedAction,
            question: textarea ? textarea.value : '',
            route_id: route.id || route.route_id || '',
            route_label: route.title || route.label || '',
            query_topic: (latest.route_note && latest.route_note.intent) || route.category || '',
            confidence: confidence.level || '',
            page_url: window.location.href,
            sources: sources
          })
        }).then(function (response) {
          return response.json().then(function (data) { return { ok: response.ok, data: data }; });
        }).then(function (result) {
          if (!result.ok || !result.data || !result.data.deep_link) {
            throw new Error((result.data && result.data.message) || 'Unable to prepare the destination handoff.');
          }
          setStatus('Opening ' + (destination === 'workbench' ? 'Workbench' : 'Decision Studio') + '…', 'ready');
          window.location.assign(result.data.deep_link);
        }).catch(function (error) {
          setStatus('Handoff unavailable', 'error');
          var fallback = destination === 'workbench' ? '/modeling-analytics/workbench/' : '/platform/decision-studio/';
          if (window.confirm(error.message + '\n\nOpen the destination without the prepared context?')) window.location.assign(fallback);
        }).finally(function () {
          target.disabled = false;
          target.textContent = originalText;
        });
      }
    });




    function feedbackContext(type, note, extra) {
      var route = (latest && latest.route) || (latest && latest.route_note && latest.route_note.recommended_route) || {};
      var grounding = (latest && latest.grounding) || {};
      var confidence = grounding.confidence || (latest && latest.route_note && latest.route_note.confidence) || {};
      var data = {
        type: type,
        note: note || '',
        rating: extra && extra.rating ? extra.rating : 0,
        expected_result: extra && extra.expectedResult ? extra.expectedResult : '',
        question: textarea ? textarea.value : '',
        route_id: route.id || route.route_id || '',
        route_label: route.title || route.label || '',
        route_url: route.url || '',
        query_topic: (latest && latest.route_note && latest.route_note.intent) || route.category || '',
        confidence: confidence.level || '',
        page_url: window.location.href,
        sources: (grounding.sources || (latest && latest.route_note && latest.route_note.sources) || []).slice(0, 8),
        route_note: latest ? latest.route_note : {},
        consent: true
      };
      if (extra && extra.source) data.source = extra.source;
      return data;
    }

    function submitFeedback(type, note, extra) {
      if (!latest || !latest.route_note) {
        setStatus('Ask first', 'error');
        return;
      }
      if (!feedbackEndpoint) {
        setStatus('Feedback endpoint unavailable', 'error');
        return;
      }
      var payload = feedbackContext(type, note, extra || {});
      setStatus('Saving feedback…', 'loading');
      fetch(feedbackEndpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
        body: JSON.stringify({ type: type, note: note || '', route_note: latest.route_note, question: payload.question, route_id: payload.route_id })
      })
        .then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok) throw new Error(data && data.message ? data.message : 'Feedback could not be saved.');
            return data;
          });
        })
        .then(function () {
          if (!feedbackBridgeEndpoint) return null;
          return fetch(feedbackBridgeEndpoint, {
            method: 'POST', credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
            body: JSON.stringify(payload)
          }).then(function (response) {
            return response.json().then(function (data) {
              if (!response.ok) throw new Error(data && data.message ? data.message : 'Contextual feedback bridge failed.');
              return data;
            });
          });
        })
        .then(function (bridge) {
          var suffix = bridge && bridge.receipt ? ' · receipt ' + bridge.receipt : '';
          setStatus((type === 'helpful' ? 'Feedback saved' : 'Issue recorded') + suffix, 'ready');
          closeFeedbackDialog();
        })
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


    function closeFeedbackDialog() {
      if (!feedbackDialog) return;
      if (feedbackDialog.close && feedbackDialog.open) feedbackDialog.close();
      else feedbackDialog.removeAttribute('open');
      feedbackDialog.classList.remove('is-open');
      if (feedbackMode === 'helpful') safeFocus(feedbackHelpful);
      else safeFocus(feedbackIssue);
    }

    function openFeedbackDialog(mode) {
      if (!latest || !latest.route_note) {
        setStatus('Ask first', 'error');
        return;
      }
      if (!feedbackDialog) {
        setStatus('Feedback form unavailable', 'error');
        return;
      }
      feedbackMode = mode === 'helpful' ? 'helpful' : 'issue';
      if (feedbackTypeRow) feedbackTypeRow.hidden = feedbackMode === 'helpful';
      if (feedbackRatingRow) feedbackRatingRow.hidden = feedbackMode !== 'helpful';
      if (feedbackExpectedRow) feedbackExpectedRow.hidden = feedbackMode === 'helpful';
      if (feedbackNote) feedbackNote.value = feedbackMode === 'helpful' ? 'Visitor marked this research workspace as helpful.' : '';
      if (feedbackExpected) feedbackExpected.value = '';
      if (feedbackRating) feedbackRating.value = '5';
      feedbackDialog.classList.add('is-open');
      if (feedbackDialog.showModal) feedbackDialog.showModal();
      else feedbackDialog.setAttribute('open', 'open');
      window.setTimeout(function () {
        safeFocus(feedbackMode === 'helpful' ? feedbackRating : feedbackType);
      }, 20);
    }

    if (feedbackHelpful) feedbackHelpful.addEventListener('click', function () { openFeedbackDialog('helpful'); });
    if (feedbackIssue) feedbackIssue.addEventListener('click', function () { openFeedbackDialog('issue'); });
    feedbackCancelButtons.forEach(function (button) { button.addEventListener('click', closeFeedbackDialog); });
    if (feedbackDialog) {
      feedbackDialog.addEventListener('cancel', function (event) { event.preventDefault(); closeFeedbackDialog(); });
      feedbackDialog.addEventListener('click', function (event) {
        if (event.target === feedbackDialog) closeFeedbackDialog();
      });
    }
    if (feedbackSubmit) {
      feedbackSubmit.addEventListener('click', function () {
        var type = feedbackMode === 'helpful' ? 'helpful' : ((feedbackType && feedbackType.value) || 'issue');
        var note = (feedbackNote && feedbackNote.value.trim()) || (feedbackMode === 'helpful' ? 'Visitor marked this route as helpful.' : 'Visitor reported a route issue.');
        var extra = {
          rating: feedbackMode === 'helpful' ? parseInt((feedbackRating && feedbackRating.value) || '5', 10) || 5 : 0,
          expectedResult: feedbackMode === 'issue' && feedbackExpected ? feedbackExpected.value.trim() : ''
        };
        submitFeedback(type, note, extra);
      });
    }

    modeButtons.forEach(function (button, buttonIndex) {
      button.addEventListener('click', function () { setMode(button.getAttribute('data-sc-rl-mode') || 'auto', true); safeFocus(textarea); });
      button.addEventListener('keydown', function (event) {
        var keys = ['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp', 'Home', 'End'];
        if (keys.indexOf(event.key) === -1) return;
        event.preventDefault();
        var nextIndex = buttonIndex;
        if (event.key === 'ArrowRight' || event.key === 'ArrowDown') nextIndex = (buttonIndex + 1) % modeButtons.length;
        else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') nextIndex = (buttonIndex - 1 + modeButtons.length) % modeButtons.length;
        else if (event.key === 'Home') nextIndex = 0;
        else if (event.key === 'End') nextIndex = modeButtons.length - 1;
        var nextButton = modeButtons[nextIndex];
        setMode(nextButton.getAttribute('data-sc-rl-mode') || 'auto', true);
        safeFocus(nextButton);
      });
    });
    setMode(currentMode, true);

    if (resetSession) {
      resetSession.addEventListener('click', function () {
        sessionId = '';
        latest = null;
        try { window.localStorage.removeItem('sc_rl_ai_session_id'); } catch (e) {}
        if (sessionBar) sessionBar.hidden = true;
        if (followUps) { followUps.hidden = true; followUpList.innerHTML = ''; }
        setStatus('New session ready', 'ready');
        answer.hidden = false;
        answer.innerHTML = '<p>The prior conversational context has been cleared. Start a new site-scoped research question.</p>';
        if (answerUx) { answerUx.hidden = true; answerUx.innerHTML = ''; }
        safeFocus(textarea);
      });
    }

    if (followUpList) {
      followUpList.addEventListener('click', function (event) {
        var button = event.target.closest ? event.target.closest('[data-sc-rl-follow-up]') : null;
        if (!button) return;
        textarea.value = button.getAttribute('data-sc-rl-follow-up') || '';
        ask(textarea.value);
      });
    }

    examples.forEach(function (button) {
      button.addEventListener('click', function () {
        var exampleMode = button.getAttribute('data-sc-rl-example-mode') || 'auto';
        setMode(exampleMode, true);
        textarea.value = button.getAttribute('data-sc-rl-example') || '';
        hideSuggestions();
        ask(textarea.value);
      });
    });

    loadHealth();

    if (routeStrip && routesEndpoint) {
      sharedJson(routesEndpoint, 'routes', 300000, function () {
        return fetch(routesEndpoint, { credentials: 'same-origin', cache: 'no-store' })
          .then(function (response) {
            return response.json().then(function (data) {
              if (!response.ok) throw new Error('Routes unavailable');
              return data;
            });
          });
      }).then(function (data) {
        var routes = (data && data.routes ? data.routes : []).slice(0, 8);
        routeStrip.innerHTML = routes.map(function (route) {
          return '<a href="' + escapeHtml(route.url) + '"><span>' + escapeHtml(route.category) + '</span><strong>' + escapeHtml(route.title) + '</strong></a>';
        }).join('');
      }).catch(function () { routeStrip.hidden = true; });
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
    var buildController = null;
    var buildKey = '';

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
      var requestedKey = clean + '|' + (preferred ? preferred.value : '') + '|' + (depth ? depth.value : 'standard');
      if (buildController && buildKey === requestedKey) { setStatus('Already building this path…', 'loading'); return; }
      if (buildController && buildController.abort) buildController.abort();
      buildController = window.AbortController ? new AbortController() : null;
      buildKey = requestedKey;
      setStatus('Building path…', 'loading');
      build.disabled = true;
      build.setAttribute('aria-disabled', 'true');
      output.setAttribute('aria-busy', 'true');
      output.innerHTML = '<p class="sc-rl-ai__loading">Building an ordered Sustainable Catalyst route path</p>';
      var options = {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
        body: JSON.stringify({ question: clean, preferred_path: preferred ? preferred.value : '', depth: depth ? depth.value : 'standard' })
      };
      if (buildController) options.signal = buildController.signal;
      fetch(endpoint, options)
        .then(function(response) { return response.json().then(function(data) { if (!response.ok) throw new Error(data && data.message ? data.message : 'Path could not be built.'); return data; }); })
        .then(function(data) { latest = data; output.innerHTML = renderPathResult(data); setStatus('Path ready', 'ready'); })
        .catch(function(error) { if (error && error.name === 'AbortError') return; latest = null; output.innerHTML = '<p>' + escapeHtml(error.message || 'The path builder could not run.') + '</p>'; setStatus('Error', 'error'); })
        .finally(function() { build.disabled = false; build.removeAttribute('aria-disabled'); output.setAttribute('aria-busy', 'false'); buildController = null; buildKey = ''; });
    }

    build.addEventListener('click', function() { runBuild(); });
    textarea.addEventListener('keydown', function(event) { if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') runBuild(); });
    examples.forEach(function(button) { button.addEventListener('click', function() { textarea.value = button.getAttribute('data-sc-rl-path-example') || ''; runBuild(textarea.value); }); });
    copy.addEventListener('click', function() { if (!latest) { setStatus('Build first', 'error'); return; } copyText(renderPathMarkdown(latest)).then(function(){ setStatus('Copied', 'ready'); }).catch(function(){ setStatus('Copy unavailable', 'error'); }); });
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
