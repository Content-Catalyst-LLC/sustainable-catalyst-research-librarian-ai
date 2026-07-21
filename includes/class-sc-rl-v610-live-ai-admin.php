<?php
/**
 * Research Librarian AI v7.0.3 — consolidated administration and Python intelligence operations.
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class SC_RL6_V610_Live_AI_Admin {
    const MENU_SLUG = 'sc-research-librarian-ai';

    public static function init() {
        add_action( 'admin_menu', array( __CLASS__, 'register_menu' ), 1000 );
        add_action( 'admin_enqueue_scripts', array( __CLASS__, 'enqueue_admin_assets' ) );
    }

    public static function register_menu() {
        foreach ( self::legacy_settings_slugs() as $slug ) {
            remove_submenu_page( 'options-general.php', $slug );
        }

        add_menu_page(
            __( 'Research Librarian AI', 'sustainable-catalyst-research-librarian-ai' ),
            __( 'Research Librarian AI', 'sustainable-catalyst-research-librarian-ai' ),
            'manage_options',
            self::MENU_SLUG,
            array( __CLASS__, 'render_dashboard' ),
            'dashicons-welcome-learn-more',
            58
        );

        add_submenu_page( self::MENU_SLUG, 'Research Librarian AI Dashboard', 'Dashboard', 'manage_options', self::MENU_SLUG, array( __CLASS__, 'render_dashboard' ) );
        add_submenu_page( self::MENU_SLUG, 'Knowledge Index and Settings', 'WordPress Index', 'manage_options', 'sc-rl-index-settings', array( SC_RL6_Core::instance(), 'render_admin_page' ) );
        add_submenu_page( self::MENU_SLUG, 'Routes and Sources', 'Routes & Sources', 'manage_options', 'sc-rl-routes-sources', array( 'SC_RL6_V440_Curation', 'render_admin_page' ) );
        add_submenu_page( self::MENU_SLUG, 'Guided Research Paths', 'Guided Paths', 'manage_options', 'sc-rl-guided-paths', array( 'SC_RL6_V470_Guided_Paths', 'render_admin_page' ) );
        add_submenu_page( self::MENU_SLUG, 'Feedback and Learning', 'Feedback & Learning', 'manage_options', 'sc-rl-feedback-learning', array( 'SC_RL6_V600_Integrated_Research_Guidance_Platform', 'render_admin_page' ) );
        add_submenu_page( self::MENU_SLUG, 'Operations', 'Operations', 'manage_options', 'sc-rl-operations', array( 'SC_RL6_V550_Stable_Operations', 'render_admin_page' ) );
        add_submenu_page( self::MENU_SLUG, 'Advanced Tools', 'Advanced', 'manage_options', 'sc-rl-advanced', array( __CLASS__, 'render_advanced' ) );
        // Hidden legacy provider screen retained only as a WordPress-side fallback.
        add_submenu_page( null, 'WordPress AI Provider Fallback', 'WordPress AI Provider Fallback', 'manage_options', 'sc-rl-ai-provider', array( __CLASS__, 'render_provider_page' ) );
    }

    private static function legacy_settings_slugs() {
        return array(
            'sc-research-librarian-ai',
            'sc-research-librarian-ai-recovery',
            'sc-research-librarian-ai-security',
            'sc-research-librarian-ai-observability',
            'sc-research-librarian-ai-curation',
            'sc-research-librarian-guided-paths',
            'sc-research-librarian-contracts',
            'sc-research-librarian-answer-ux',
            'sc-research-librarian-query-review',
            'sc-research-librarian-documentation',
            'sc-research-librarian-stable-release',
            'sc-research-librarian-live-ux',
            'sc-rl-ai-route-quality',
            'sc-rl-article-maps',
            'sc-rl-deep-links',
            'sc-rl-stable-operations',
            'sc-rl-feedback-bridge',
            'sc-rl-demand-intelligence',
            'sc-rl-adaptive-experiences',
            'sc-rl-route-improvement',
            'sc-rl-integrated-guidance',
        );
    }

    public static function enqueue_admin_assets( $hook ) {
        if ( false === strpos( (string) $hook, 'sc-rl' ) && false === strpos( (string) $hook, 'sc-research-librarian-ai' ) ) {
            return;
        }
        wp_register_style( 'sc-rl-v610-admin', false, array(), SC_RL6_Core::VERSION );
        wp_enqueue_style( 'sc-rl-v610-admin' );
        wp_add_inline_style( 'sc-rl-v610-admin', self::admin_css() );
    }

    private static function admin_css() {
        return '.sc-rl-admin-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;max-width:1200px;margin:18px 0}.sc-rl-admin-card{background:#fff;border:1px solid #c3c4c7;border-top:4px solid #111;padding:16px}.sc-rl-admin-card[data-state="online"]{border-top-color:#008a20}.sc-rl-admin-card[data-state="offline"]{border-top-color:#d63638}.sc-rl-admin-card[data-state="not-configured"],.sc-rl-admin-card[data-state="not-tested"]{border-top-color:#dba617}.sc-rl-admin-card h2,.sc-rl-admin-card h3{margin-top:0}.sc-rl-admin-metric{display:block;font-size:24px;font-weight:800;line-height:1.2}.sc-rl-admin-actions{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}.sc-rl-provider-table{max-width:1000px}.sc-rl-provider-table th{width:230px;text-align:left;vertical-align:top;padding:14px 12px 14px 0}.sc-rl-provider-table td{padding:10px 0}.sc-rl-provider-table input.regular-text,.sc-rl-provider-table select{width:min(520px,100%)}.sc-rl-admin-note{max-width:1000px;background:#fff;border-left:4px solid #b00000;padding:12px 16px}.sc-rl-model-results{max-height:320px;overflow:auto;background:#fff;border:1px solid #c3c4c7;padding:12px;max-width:1000px}.sc-rl-advanced-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;max-width:1200px}.sc-rl-advanced-grid a{display:block;background:#fff;border:1px solid #c3c4c7;padding:14px;text-decoration:none;font-weight:700}.sc-rl-advanced-grid a:hover{border-color:#b00000;color:#b00000}';
    }

    private static function require_admin() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( esc_html__( 'You do not have permission to manage Research Librarian AI.', 'sustainable-catalyst-research-librarian-ai' ) );
        }
    }

    public static function render_dashboard() {
        self::require_admin();
        $core = SC_RL6_Core::instance();
        $status = $core->ai_status_snapshot( false );
        $route = $core->resolve_route( 'What public evidence is available about Pakistan?' );
        ?>
        <div class="wrap">
            <h1><?php esc_html_e( 'Research Librarian AI', 'sustainable-catalyst-research-librarian-ai' ); ?></h1>
            <p><?php esc_html_e( 'Python knowledge intelligence, full-library title-aware retrieval, grounded AI guidance, Site Intelligence routing, and governed Sustainable Catalyst research workflows.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>

            <div class="sc-rl-admin-grid">
                <?php $python_status = class_exists( 'SC_RL6_V621_Endpoint_Reliability' ) ? SC_RL6_V621_Endpoint_Reliability::backend_status( false ) : new WP_Error( 'unavailable', 'Python module unavailable' ); ?>
                <article class="sc-rl-admin-card" data-state="<?php echo esc_attr( is_wp_error( $python_status ) ? 'offline' : ( isset( $python_status['state'] ) ? $python_status['state'] : 'unknown' ) ); ?>">
                    <h2><?php esc_html_e( 'Python Intelligence', 'sustainable-catalyst-research-librarian-ai' ); ?></h2>
                    <span class="sc-rl-admin-metric"><?php echo esc_html( is_wp_error( $python_status ) ? 'Not connected' : absint( isset( $python_status['indexed_titles'] ) ? $python_status['indexed_titles'] : 0 ) . ' titles' ); ?></span>
                    <p><?php echo esc_html( is_wp_error( $python_status ) ? 'Configure the Render backend.' : ( isset( $python_status['label'] ) ? $python_status['label'] : 'Backend online' ) ); ?></p>
                    <p><a class="button" href="<?php echo esc_url( admin_url( 'admin.php?page=sc-rl-python-intelligence' ) ); ?>">Open Python Intelligence</a></p>
                </article>
                <article class="sc-rl-admin-card" data-state="<?php echo esc_attr( $status['state'] ); ?>">
                    <h2><?php echo esc_html( $status['label'] ); ?></h2>
                    <span class="sc-rl-admin-metric"><?php echo esc_html( ucfirst( $status['provider'] ) ); ?></span>
                    <p><?php echo esc_html( $status['model'] ?: 'No provider model selected' ); ?></p>
                </article>
                <article class="sc-rl-admin-card">
                    <h2><?php esc_html_e( 'Knowledge index', 'sustainable-catalyst-research-librarian-ai' ); ?></h2>
                    <span class="sc-rl-admin-metric"><?php echo esc_html( absint( $status['indexed_records'] ) ); ?></span>
                    <p><?php echo esc_html( absint( $status['embedded_records'] ) . ' embedded · ' . $status['semantic_retrieval'] ); ?></p>
                </article>
                <article class="sc-rl-admin-card">
                    <h2><?php esc_html_e( 'Last provider result', 'sustainable-catalyst-research-librarian-ai' ); ?></h2>
                    <span class="sc-rl-admin-metric"><?php echo esc_html( $status['latency_ms'] ? $status['latency_ms'] . ' ms' : 'Not recorded' ); ?></span>
                    <p><?php echo esc_html( $status['last_success_utc'] ? 'Success: ' . $status['last_success_utc'] : ( $status['last_failure_utc'] ? 'Failure: ' . $status['last_failure_utc'] : 'Run a provider test.' ) ); ?></p>
                </article>
                <article class="sc-rl-admin-card">
                    <h2><?php esc_html_e( 'Country routing test', 'sustainable-catalyst-research-librarian-ai' ); ?></h2>
                    <span class="sc-rl-admin-metric"><?php echo esc_html( $route['matched_country']['alpha3'] ?? '—' ); ?></span>
                    <p><?php echo esc_html( ( $route['title'] ?? '' ) . ' · ' . ( $route['id'] ?? '' ) ); ?></p>
                </article>
            </div>

            <?php if ( 'standard' === $gemini_key_type ) : ?>
                <div class="notice notice-warning"><p><strong>Gemini key migration:</strong> This saved key uses the older standard-key format. Google rejects unrestricted standard keys after June 19, 2026 and plans to end standard-key support in September 2026. Restrict it to the Gemini API in Google AI Studio or replace it with a new authorization key.</p></div>
            <?php elseif ( 'authorization' === $gemini_key_type ) : ?>
                <div class="notice notice-info"><p><strong>Gemini authorization key detected.</strong> Research Librarian AI v7.0.3 retains support for modern Google AI Studio authorization keys, including keys that contain periods.</p></div>
            <?php endif; ?>

            <?php if ( ! empty( $status['last_error_message'] ) ) : ?>
                <div class="notice notice-error"><p><strong><?php esc_html_e( 'Latest AI provider error:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( $status['last_error_message'] ); ?><?php if ( $status['last_http_status'] ) : ?> <?php echo esc_html( '(HTTP ' . $status['last_http_status'] . ')' ); ?><?php endif; ?></p></div>
            <?php endif; ?>

            <div class="sc-rl-admin-actions">
                <a class="button button-primary" href="<?php echo esc_url( admin_url( 'admin.php?page=sc-rl-ai-provider' ) ); ?>">Configure and Test AI</a>
                <a class="button" href="<?php echo esc_url( admin_url( 'admin.php?page=sc-rl-index-settings' ) ); ?>">Knowledge Index</a>
                <a class="button" href="<?php echo esc_url( admin_url( 'admin.php?page=sc-rl-routes-sources' ) ); ?>">Routes & Sources</a>
                <a class="button" href="<?php echo esc_url( home_url( '/platform/research-librarian/' ) ); ?>" target="_blank" rel="noopener noreferrer">Open Public Research Librarian</a>
            </div>

            <div class="sc-rl-admin-note">
                <strong><?php esc_html_e( 'Operational boundary:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong>
                <?php esc_html_e( 'A configured provider is not considered online until a request succeeds. When AI fails, the public assistant identifies the outage and continues with country-aware, source-aware deterministic routing.', 'sustainable-catalyst-research-librarian-ai' ); ?>
            </div>
        </div>
        <?php
    }

    public static function render_provider_page() {
        self::require_admin();
        $core = SC_RL6_Core::instance();
        $notice = '';
        $notice_type = 'success';
        if ( 'POST' === strtoupper( $_SERVER['REQUEST_METHOD'] ?? '' ) ) {
            check_admin_referer( 'sc_rl_v610_provider_action' );
            if ( isset( $_POST['sc_rl_v610_save_provider'] ) ) {
                $payload = isset( $_POST['sc_rl_ai'] ) && is_array( $_POST['sc_rl_ai'] ) ? wp_unslash( $_POST['sc_rl_ai'] ) : array();
                $core->save_ai_provider_settings( $payload );
                $notice = 'AI provider settings saved.';
            } elseif ( isset( $_POST['sc_rl_v610_test_provider'] ) ) {
                $payload = isset( $_POST['sc_rl_ai'] ) && is_array( $_POST['sc_rl_ai'] ) ? wp_unslash( $_POST['sc_rl_ai'] ) : array();
                $core->save_ai_provider_settings( $payload );
                $result = $core->test_ai_provider_connection();
                if ( is_wp_error( $result ) ) {
                    $notice_type = 'error';
                    $data = $result->get_error_data();
                    $http = is_array( $data ) ? absint( $data['http_status'] ?? 0 ) : 0;
                    $notice = $result->get_error_message() . ( $http ? ' (HTTP ' . $http . ')' : '' );
                } else {
                    $notice = 'AI provider connection succeeded. ' . ( $result['response_excerpt'] ?? '' );
                }
            }
        }
        $options = $core->admin_options_snapshot();
        $status = $core->ai_status_snapshot( false );
        $full_options = wp_parse_args( get_option( SC_RL6_Core::OPTION_NAME, array() ), SC_RL6_Core::defaults() );
        $gemini_saved = ! empty( $full_options['gemini_api_key'] );
        $gemini_key_value = trim( (string) ( $full_options['gemini_api_key'] ?? '' ) );
        $gemini_key_type = $gemini_saved ? ( 0 === strpos( $gemini_key_value, 'AIza' ) ? 'standard' : 'authorization' ) : 'none';
        $openai_saved = ! empty( $full_options['openai_api_key'] );
        ?>
        <div class="wrap">
            <h1><?php esc_html_e( 'Optional WordPress Fallback Provider', 'sustainable-catalyst-research-librarian-ai' ); ?></h1>
            <p><?php esc_html_e( 'This page configures only the emergency WordPress-direct fallback. The production Research Librarian index and Gemini connection are managed under Python Intelligence and use Render SC_RL_GEMINI_API_KEY.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
            <div class="notice notice-info inline"><p><strong>Production path:</strong> Use <em>Research Librarian → Python Intelligence</em> to build the knowledge index. A successful fallback-provider test here does not build or verify the Python index.</p></div>

            <?php if ( $notice ) : ?><div class="notice notice-<?php echo esc_attr( $notice_type ); ?> is-dismissible"><p><?php echo esc_html( $notice ); ?></p></div><?php endif; ?>

            <div class="sc-rl-admin-grid">
                <article class="sc-rl-admin-card" data-state="<?php echo esc_attr( $status['state'] ); ?>"><h2>Fallback connection</h2><span class="sc-rl-admin-metric"><?php echo esc_html( 'online' === $status['state'] ? 'Connected' : ( 'disabled' === $status['provider'] ? 'Disabled' : 'Not verified' ) ); ?></span><p><?php echo esc_html( 'disabled' === $status['provider'] ? 'Verified deterministic fallback only' : ucfirst( $status['provider'] ) . ( $status['model'] ? ' · model configured' : '' ) ); ?></p></article>
                <article class="sc-rl-admin-card"><h2>Purpose</h2><span class="sc-rl-admin-metric">Fallback only</span><p>Does not control the Python durable index.</p></article>
                <article class="sc-rl-admin-card"><h2>Last successful test</h2><p><?php echo esc_html( $status['last_success_utc'] ?: 'No successful fallback test recorded.' ); ?></p></article>
                <article class="sc-rl-admin-card"><h2>Request latency</h2><p><?php echo esc_html( $status['latency_ms'] ? $status['latency_ms'] . ' ms' : 'Not recorded' ); ?></p></article>
            </div>

            <?php if ( ! empty( $status['last_error_message'] ) ) : ?>
                <div class="notice notice-error"><p><strong>Exact administrator diagnostic:</strong> <?php echo esc_html( $status['last_error_message'] ); ?><?php if ( $status['last_http_status'] ) : ?> <?php echo esc_html( '(HTTP ' . $status['last_http_status'] . ')' ); ?><?php endif; ?><?php if ( ! empty( $status['transport_error'] ) ) : ?> <?php echo esc_html( 'Transport: ' . $status['transport_error'] ); ?><?php endif; ?></p></div>
            <?php endif; ?>

            <details class="sc-rl-v702-settings" style="background:#fff;border:1px solid #dcdcde;border-radius:14px;padding:0 20px;margin:18px 0">
                <summary style="cursor:pointer;font-size:16px;font-weight:800;padding:18px 0">Configure optional fallback</summary>
            <form method="post">
                <?php wp_nonce_field( 'sc_rl_v610_provider_action' ); ?>
                <table class="form-table sc-rl-provider-table" role="presentation">
                    <tr><th><label for="sc-rl-provider">AI provider</label></th><td><select id="sc-rl-provider" name="sc_rl_ai[provider]"><?php foreach ( array( 'disabled' => 'Disabled / verified fallback only', 'gemini' => 'Gemini', 'openai' => 'OpenAI' ) as $value => $label ) : ?><option value="<?php echo esc_attr( $value ); ?>" <?php selected( $options['provider'], $value ); ?>><?php echo esc_html( $label ); ?></option><?php endforeach; ?></select></td></tr>
                    <tr><th><label for="sc-rl-gemini-model">Gemini model</label></th><td><input id="sc-rl-gemini-model" class="regular-text" name="sc_rl_ai[gemini_model]" value="<?php echo esc_attr( $options['gemini_model'] ); ?>"><p class="description">Use a model returned by the provider model list for this key.</p></td></tr>
                    <tr><th><label for="sc-rl-gemini-key">Gemini API key</label></th><td><input id="sc-rl-gemini-key" type="password" class="regular-text" name="sc_rl_ai[gemini_api_key_new]" value="" autocomplete="new-password" placeholder="<?php echo esc_attr( $gemini_saved ? 'Key saved. Paste only to replace.' : 'Paste Gemini API key' ); ?>"><p class="description">Fallback-only credential. Create it in Google AI Studio; leave blank to preserve it. The canonical Python backend uses Render SC_RL_GEMINI_API_KEY instead.</p><?php if ( $gemini_saved ) : ?><p><label><input type="checkbox" name="sc_rl_ai[gemini_api_key_clear]" value="1"> Clear saved Gemini key</label></p><?php endif; ?></td></tr>
                    <tr><th><label for="sc-rl-openai-model">OpenAI model</label></th><td><input id="sc-rl-openai-model" class="regular-text" name="sc_rl_ai[openai_model]" value="<?php echo esc_attr( $options['openai_model'] ); ?>"></td></tr>
                    <tr><th><label for="sc-rl-openai-key">OpenAI API key</label></th><td><input id="sc-rl-openai-key" type="password" class="regular-text" name="sc_rl_ai[openai_api_key_new]" value="" autocomplete="new-password" placeholder="<?php echo esc_attr( $openai_saved ? 'Key saved. Paste only to replace.' : 'Paste OpenAI API key' ); ?>"><?php if ( $openai_saved ) : ?><p><label><input type="checkbox" name="sc_rl_ai[openai_api_key_clear]" value="1"> Clear saved OpenAI key</label></p><?php endif; ?></td></tr>
                    <tr><th><label for="sc-rl-embedding-provider">Semantic retrieval</label></th><td><select id="sc-rl-embedding-provider" name="sc_rl_ai[embeddings_provider]"><option value="disabled" <?php selected( $options['embeddings_provider'], 'disabled' ); ?>>Keyword retrieval only</option><option value="gemini" <?php selected( $options['embeddings_provider'], 'gemini' ); ?>>Gemini embeddings</option></select></td></tr>
                    <tr><th><label for="sc-rl-embedding-model">Embedding model</label></th><td><input id="sc-rl-embedding-model" class="regular-text" name="sc_rl_ai[gemini_embedding_model]" value="<?php echo esc_attr( $options['gemini_embedding_model'] ); ?>"></td></tr>
                    <tr><th><label for="sc-rl-timeout">Request timeout</label></th><td><input id="sc-rl-timeout" type="number" min="10" max="60" name="sc_rl_ai[ai_request_timeout]" value="<?php echo esc_attr( $options['ai_request_timeout'] ); ?>"> seconds</td></tr>
                    <tr><th><label for="sc-rl-output">Maximum output tokens</label></th><td><input id="sc-rl-output" type="number" min="150" max="4000" name="sc_rl_ai[max_output_tokens]" value="<?php echo esc_attr( $options['max_output_tokens'] ); ?>"></td></tr>
                    <tr><th><label for="sc-rl-temperature">Temperature</label></th><td><input id="sc-rl-temperature" type="number" step="0.05" min="0" max="1" name="sc_rl_ai[temperature]" value="<?php echo esc_attr( $options['temperature'] ); ?>"></td></tr>
                    <tr><th><label for="sc-rl-rate">Public hourly rate limit</label></th><td><input id="sc-rl-rate" type="number" min="1" max="100" name="sc_rl_ai[rate_limit]" value="<?php echo esc_attr( $options['rate_limit'] ); ?>"></td></tr>
                    <tr><th>Public status</th><td><input type="hidden" name="sc_rl_ai[public_ai_status_enabled]" value="0"><label><input type="checkbox" name="sc_rl_ai[public_ai_status_enabled]" value="1" <?php checked( $options['public_ai_status_enabled'], '1' ); ?>> Show AI availability and fallback status on the public assistant</label></td></tr>
                </table>
                <p class="submit"><button class="button button-primary" type="submit" name="sc_rl_v610_save_provider" value="1">Save AI Provider Settings</button> <button class="button" type="submit" name="sc_rl_v610_test_provider" value="1">Test AI Connection</button> <button class="button" type="button" id="sc-rl-list-models">List Available Gemini Models</button></p>
            </form>
            </details>

            <div id="sc-rl-model-results" class="sc-rl-model-results" hidden aria-live="polite"></div>
            <p class="sc-rl-admin-note"><strong>Important:</strong> Saving a provider and key does not prove the route is online. Use <em>Test AI Connection</em>. The public interface reports AI Online only after a successful provider response; otherwise it states that verified fallback routing is active.</p>
        </div>
        <script>
        (function(){
          var button=document.getElementById('sc-rl-list-models');
          var output=document.getElementById('sc-rl-model-results');
          if(!button||!output)return;
          button.addEventListener('click',function(){
            button.disabled=true; output.hidden=false; output.textContent='Loading available Gemini models…';
            fetch(<?php echo wp_json_encode( rest_url( SC_RL6_Core::REST_NAMESPACE . '/ai/models' ) ); ?>,{credentials:'same-origin',headers:{'X-WP-Nonce':<?php echo wp_json_encode( wp_create_nonce( 'wp_rest' ) ); ?>}})
              .then(function(r){return r.json().then(function(d){if(!r.ok)throw new Error(d&&d.message?d.message:'Model listing failed.');return d;});})
              .then(function(data){var models=data.models||[];output.innerHTML=models.length?'<strong>'+models.length+' generateContent model(s)</strong><ul>'+models.map(function(m){return '<li><code>'+String(m.name||'').replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c];})+'</code> — '+String(m.display_name||'')+'</li>';}).join('')+'</ul>':'No generateContent models were returned for this key.';})
              .catch(function(e){output.textContent=e.message;})
              .finally(function(){button.disabled=false;});
          });
        }());
        </script>
        <?php
    }

    private static function advanced_tools() {
        return array(
            'recovery' => array( 'Recovery and Snapshots', 'SC_RL6_V410_Recovery' ),
            'security' => array( 'Security and Access Review', 'SC_RL6_V420_Security' ),
            'observability' => array( 'Observability', 'SC_RL6_V430_Observability' ),
            'contracts' => array( 'Integration Contracts', 'SC_RL6_V450_Contracts' ),
            'answer-ux' => array( 'Public Answer UX', 'SC_RL6_V460_Answer_UX' ),
            'query-review' => array( 'Query Review', 'SC_RL6_V480_Query_Review' ),
            'documentation' => array( 'Documentation Snapshot', 'SC_RL6_V490_Documentation' ),
            'stable-release' => array( 'Stable Release Audit', 'SC_RL6_V500_Stable_Release' ),
            'live-ux' => array( 'Live Public Experience QA', 'SC_RL6_V510_Live_UX' ),
            'route-quality' => array( 'Route Quality', 'SC_RL6_V520_Route_Quality' ),
            'article-maps' => array( 'Article Map Embeds', 'SC_RL6_V530_Article_Map_Embeds' ),
            'deep-links' => array( 'Deep-Link Actions', 'SC_RL6_V540_Deep_Links' ),
            'feedback-bridge' => array( 'Feature Suggestions Bridge', 'SC_RL6_V560_Feature_Suggestions_Bridge' ),
            'demand-intelligence' => array( 'Research Demand Intelligence', 'SC_RL6_V570_Research_Demand_Intelligence' ),
            'adaptive-experiences' => array( 'Adaptive Prompts and Surveys', 'SC_RL6_V580_Adaptive_Prompt_Surveys' ),
            'route-improvement' => array( 'Closed-Loop Route Improvement', 'SC_RL6_V590_Closed_Loop_Route_Improvement' ),
        );
    }

    public static function render_advanced() {
        self::require_admin();
        $tools = self::advanced_tools();
        $selected = isset( $_GET['tool'] ) ? sanitize_key( wp_unslash( $_GET['tool'] ) ) : '';
        if ( $selected && isset( $tools[ $selected ] ) ) {
            $class = $tools[ $selected ][1];
            echo '<div class="wrap"><p><a class="button" href="' . esc_url( admin_url( 'admin.php?page=sc-rl-advanced' ) ) . '">← Advanced tools</a></p></div>';
            if ( class_exists( $class ) && is_callable( array( $class, 'render_admin_page' ) ) ) {
                call_user_func( array( $class, 'render_admin_page' ) );
                return;
            }
            echo '<div class="wrap"><div class="notice notice-error"><p>That Research Librarian module is unavailable.</p></div></div>';
            return;
        }
        ?>
        <div class="wrap">
            <h1><?php esc_html_e( 'Advanced Research Librarian Tools', 'sustainable-catalyst-research-librarian-ai' ); ?></h1>
            <p><?php esc_html_e( 'Specialized diagnostics and governance tools are consolidated here instead of occupying the main WordPress Settings menu.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
            <div class="sc-rl-advanced-grid">
                <a href="<?php echo esc_url( admin_url( 'admin.php?page=sc-rl-ai-provider' ) ); ?>">WordPress AI Provider Fallback →</a>
                <?php foreach ( $tools as $key => $tool ) : ?>
                    <a href="<?php echo esc_url( add_query_arg( array( 'page' => 'sc-rl-advanced', 'tool' => $key ), admin_url( 'admin.php' ) ) ); ?>"><?php echo esc_html( $tool[0] ); ?> →</a>
                <?php endforeach; ?>
            </div>
        </div>
        <?php
    }
}
