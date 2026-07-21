<?php
/**
 * Research Librarian AI v7.0.5 — Research Quality and Governance Center.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class SC_RL6_V670_Governance_Center {
    const VERSION = '7.0.5';
    const OPTION_NAME = 'sc_rl_v670_governance_options';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';
    const POLICY_SCHEMA = 'sc-research-governance-policy/1.0';
    const METHODOLOGY_SCHEMA = 'sc-research-methodology/1.0';
    const EXPORT_SCHEMA = 'sc-research-governance-export/1.0';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_rest_routes' ), 130 );
        add_action( 'admin_menu', array( __CLASS__, 'register_admin_menu' ), 1040 );
        add_shortcode( 'sc_research_librarian_methodology', array( __CLASS__, 'render_methodology' ) );
        add_shortcode( 'sc_research_librarian_governance_status', array( __CLASS__, 'render_status' ) );
    }

    public static function activate() {
        update_option( self::OPTION_NAME, wp_parse_args( get_option( self::OPTION_NAME, array() ), self::defaults() ), false );
    }

    public static function defaults() {
        return array(
            'profile' => 'public-trust-v7.0.5',
            'require_approved_sources' => '0',
            'exclude_rejected_sources' => '1',
            'stale_after_days' => 730,
            'warn_on_stale_sources' => '1',
            'answer_trace_days' => 30,
            'quality_evaluation_days' => 365,
            'governance_event_days' => 365,
            'store_query_text' => '0',
            'store_answer_text' => '0',
            'methodology_public' => '1',
            'exact_title_accuracy' => 0.90,
            'hit_at_3' => 0.85,
            'citation_precision' => 0.95,
            'citation_completeness' => 0.90,
            'unsupported_claim_rate_max' => 0.05,
            'route_accuracy' => 0.80,
            'pdf_page_accuracy' => 0.80,
            'fallback_success' => 0.95,
            'minimum_answer_quality' => 0.80,
        );
    }

    public static function options() { return wp_parse_args( get_option( self::OPTION_NAME, array() ), self::defaults() ); }
    public static function can_manage() { return current_user_can( 'manage_options' ); }

    private static function backend_options() {
        return wp_parse_args( get_option( 'sc_rl_v620_python_options', array() ), array( 'enabled' => '0', 'backend_url' => '', 'backend_api_key' => '', 'request_timeout' => 45 ) );
    }

    private static function backend_request( $path, $method = 'GET', $payload = null ) {
        $o = self::backend_options();
        if ( '1' !== (string) $o['enabled'] || empty( $o['backend_url'] ) || empty( $o['backend_api_key'] ) ) {
            return new WP_Error( 'sc_rl_v670_backend_disabled', 'The Python governance backend is not configured.', array( 'status' => 503 ) );
        }
        $args = array(
            'method' => strtoupper( $method ),
            'timeout' => max( 10, min( 120, absint( $o['request_timeout'] ) ) ),
            'headers' => array( 'Accept' => 'application/json', 'Content-Type' => 'application/json', 'X-SC-RL-Key' => (string) $o['backend_api_key'], 'User-Agent' => 'Sustainable-Catalyst-Research-Librarian/' . self::VERSION ),
        );
        if ( null !== $payload ) { $args['body'] = wp_json_encode( $payload ); }
        $response = wp_remote_request( untrailingslashit( $o['backend_url'] ) . '/' . ltrim( $path, '/' ), $args );
        if ( is_wp_error( $response ) ) { return $response; }
        $code = wp_remote_retrieve_response_code( $response );
        $body = json_decode( wp_remote_retrieve_body( $response ), true );
        if ( $code < 200 || $code >= 300 || ! is_array( $body ) ) {
            return new WP_Error( 'sc_rl_v670_backend_failed', 'The governance backend request failed.', array( 'status' => $code ? $code : 502, 'response' => $body ) );
        }
        return $body;
    }

    public static function local_policy() {
        $o = self::options();
        return array(
            'schema' => self::POLICY_SCHEMA,
            'profile' => sanitize_text_field( $o['profile'] ),
            'source_controls' => array(
                'require_approved_sources' => '1' === (string) $o['require_approved_sources'],
                'exclude_rejected_sources' => '1' === (string) $o['exclude_rejected_sources'],
                'stale_after_days' => max( 1, min( 3650, absint( $o['stale_after_days'] ) ) ),
                'warn_on_stale_sources' => '1' === (string) $o['warn_on_stale_sources'],
                'block_expired_reviews' => false,
            ),
            'quality_thresholds' => array(
                'exact_title_accuracy' => (float) $o['exact_title_accuracy'],
                'hit_at_3' => (float) $o['hit_at_3'],
                'citation_precision' => (float) $o['citation_precision'],
                'citation_completeness' => (float) $o['citation_completeness'],
                'unsupported_claim_rate_max' => (float) $o['unsupported_claim_rate_max'],
                'route_accuracy' => (float) $o['route_accuracy'],
                'pdf_page_accuracy' => (float) $o['pdf_page_accuracy'],
                'fallback_success' => (float) $o['fallback_success'],
                'minimum_answer_quality' => (float) $o['minimum_answer_quality'],
            ),
            'retention' => array(
                'answer_trace_days' => max( 1, min( 3650, absint( $o['answer_trace_days'] ) ) ),
                'quality_evaluation_days' => max( 30, min( 3650, absint( $o['quality_evaluation_days'] ) ) ),
                'governance_event_days' => max( 30, min( 3650, absint( $o['governance_event_days'] ) ) ),
                'store_query_text' => '1' === (string) $o['store_query_text'],
                'store_answer_text' => '1' === (string) $o['store_answer_text'],
                'hash_session_ids' => true,
            ),
            'human_review' => array(
                'required_for_policy_changes' => true,
                'required_for_release_override' => true,
                'required_for_source_exclusion' => true,
                'allow_automatic_publication' => false,
            ),
            'boundaries' => array(
                'professional_advice' => array( 'medical', 'legal', 'financial', 'clinical' ),
                'diagnosis_or_certification' => false,
                'autonomous_publishing' => false,
                'unreviewed_ranking_changes' => false,
            ),
        );
    }

    public static function register_rest_routes() {
        register_rest_route( self::REST_NAMESPACE, '/governance/methodology', array( 'methods' => WP_REST_Server::READABLE, 'callback' => array( __CLASS__, 'rest_methodology' ), 'permission_callback' => '__return_true' ) );
        register_rest_route( self::REST_NAMESPACE, '/governance/status', array( 'methods' => WP_REST_Server::READABLE, 'callback' => array( __CLASS__, 'rest_status' ), 'permission_callback' => array( __CLASS__, 'can_manage' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/governance/policy', array( 'methods' => WP_REST_Server::CREATABLE, 'callback' => array( __CLASS__, 'rest_policy' ), 'permission_callback' => array( __CLASS__, 'can_manage' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/governance/source-review', array( 'methods' => WP_REST_Server::CREATABLE, 'callback' => array( __CLASS__, 'rest_source_review' ), 'permission_callback' => array( __CLASS__, 'can_manage' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/governance/release-gate', array( 'methods' => WP_REST_Server::CREATABLE, 'callback' => array( __CLASS__, 'rest_release_gate' ), 'permission_callback' => array( __CLASS__, 'can_manage' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/governance/retention', array( 'methods' => WP_REST_Server::CREATABLE, 'callback' => array( __CLASS__, 'rest_retention' ), 'permission_callback' => array( __CLASS__, 'can_manage' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/governance/export', array( 'methods' => WP_REST_Server::READABLE, 'callback' => array( __CLASS__, 'rest_export' ), 'permission_callback' => array( __CLASS__, 'can_manage' ) ) );
    }

    public static function rest_methodology() {
        $remote = self::backend_request( '/v1/governance/methodology', 'GET' );
        if ( ! is_wp_error( $remote ) ) { return new WP_REST_Response( $remote, 200 ); }
        return new WP_REST_Response( array( 'ok' => true, 'version' => self::VERSION, 'methodology' => self::methodology() ), 200 );
    }

    public static function rest_status() {
        $policy = self::backend_request( '/v1/governance/policy', 'GET' );
        $history = self::backend_request( '/v1/governance/release-gate/history?limit=10', 'GET' );
        return new WP_REST_Response( array(
            'ok' => ! is_wp_error( $policy ),
            'version' => self::VERSION,
            'policy' => is_wp_error( $policy ) ? self::local_policy() : $policy['policy'],
            'release_gates' => is_wp_error( $history ) ? array() : $history['runs'],
            'backend_error' => is_wp_error( $policy ) ? $policy->get_error_message() : '',
        ), 200 );
    }

    public static function rest_policy( WP_REST_Request $request ) {
        $params = $request->get_json_params();
        $reviewer = sanitize_text_field( isset( $params['reviewer'] ) ? $params['reviewer'] : wp_get_current_user()->display_name );
        $policy = isset( $params['policy'] ) && is_array( $params['policy'] ) ? $params['policy'] : self::local_policy();
        $response = self::backend_request( '/v1/governance/policy', 'POST', array( 'policy' => $policy, 'reviewer' => $reviewer, 'reason' => sanitize_text_field( $params['reason'] ?? 'wordpress-admin-update' ) ) );
        if ( is_wp_error( $response ) ) { return $response; }
        return new WP_REST_Response( $response, 200 );
    }

    public static function rest_source_review( WP_REST_Request $request ) {
        $p = $request->get_json_params();
        $payload = array( 'record_id' => sanitize_text_field( $p['record_id'] ?? '' ), 'state' => sanitize_key( $p['state'] ?? 'review' ), 'reviewer' => sanitize_text_field( $p['reviewer'] ?? wp_get_current_user()->display_name ), 'note' => sanitize_textarea_field( $p['note'] ?? '' ), 'expires_utc' => sanitize_text_field( $p['expires_utc'] ?? '' ) );
        $response = self::backend_request( '/v1/governance/sources', 'POST', $payload );
        return is_wp_error( $response ) ? $response : new WP_REST_Response( $response, 200 );
    }

    public static function rest_release_gate( WP_REST_Request $request ) {
        $p = $request->get_json_params();
        $response = self::backend_request( '/v1/governance/release-gate', 'POST', array( 'release_version' => sanitize_text_field( $p['release_version'] ?? self::VERSION ), 'metrics' => is_array( $p['metrics'] ?? null ) ? $p['metrics'] : array(), 'persist' => true, 'override' => ! empty( $p['override'] ), 'reviewer' => sanitize_text_field( $p['reviewer'] ?? '' ) ) );
        return is_wp_error( $response ) ? $response : new WP_REST_Response( $response, 200 );
    }

    public static function rest_retention( WP_REST_Request $request ) {
        $p = $request->get_json_params();
        $response = self::backend_request( '/v1/governance/retention/run', 'POST', array( 'dry_run' => ! isset( $p['dry_run'] ) || ! empty( $p['dry_run'] ) ) );
        return is_wp_error( $response ) ? $response : new WP_REST_Response( $response, 200 );
    }

    public static function rest_export() {
        $response = self::backend_request( '/v1/governance/export', 'GET' );
        if ( is_wp_error( $response ) ) { return $response; }
        $response['wordpress'] = array( 'version' => self::VERSION, 'site_url' => home_url( '/' ), 'local_policy' => self::local_policy() );
        return new WP_REST_Response( $response, 200 );
    }

    public static function methodology() {
        $o = self::options();
        return array(
            'schema' => self::METHODOLOGY_SCHEMA,
            'title' => 'Research Librarian Methodology and Limitations',
            'version' => self::VERSION,
            'principles' => array( 'Retrieval occurs before generation.', 'Only synchronized Sustainable Catalyst records may be cited.', 'Citation verification and deterministic fallback protect the public response.', 'Ranking, exclusions, release overrides, and publication remain human-controlled.' ),
            'evaluation' => array( 'Exact-title and top-three retrieval accuracy', 'Citation precision and completeness', 'Unsupported-claim detection', 'Route and PDF page-reference accuracy', 'Fallback continuity and answer quality' ),
            'limitations' => array( 'The system is site-scoped and cannot answer beyond synchronized records.', 'Older sources may require freshness review.', 'It does not diagnose, certify, or replace professional judgment.', 'AI synthesis remains reviewable and reversible.' ),
            'retention_summary' => array( 'answer_trace_days' => absint( $o['answer_trace_days'] ), 'query_text_stored' => '1' === (string) $o['store_query_text'], 'answer_text_stored' => '1' === (string) $o['store_answer_text'] ),
        );
    }

    public static function register_admin_menu() {
        add_submenu_page( 'options-general.php', 'Research Quality and Governance', 'Research Quality & Governance', 'manage_options', 'sc-research-librarian-governance', array( __CLASS__, 'render_admin' ) );
    }

    public static function render_admin() {
        if ( ! current_user_can( 'manage_options' ) ) { return; }
        if ( isset( $_POST['sc_rl_v670_save'] ) && check_admin_referer( 'sc_rl_v670_save' ) ) {
            $d = self::defaults(); $clean = array();
            foreach ( $d as $key => $value ) {
                if ( in_array( $key, array( 'require_approved_sources','exclude_rejected_sources','warn_on_stale_sources','store_query_text','store_answer_text','methodology_public' ), true ) ) { $clean[$key] = isset($_POST[$key]) ? '1' : '0'; }
                elseif ( is_float( $value ) ) { $clean[$key] = max(0,min(1,(float)($_POST[$key] ?? $value))); }
                elseif ( is_int( $value ) ) { $clean[$key] = absint($_POST[$key] ?? $value); }
                else { $clean[$key] = sanitize_text_field($_POST[$key] ?? $value); }
            }
            update_option( self::OPTION_NAME, $clean, false );
            self::backend_request( '/v1/governance/policy', 'POST', array( 'policy' => self::local_policy(), 'reviewer' => wp_get_current_user()->display_name, 'reason' => 'wordpress-admin-save' ) );
            echo '<div class="notice notice-success"><p>Governance policy saved and submitted to the backend.</p></div>';
        }
        $o = self::options(); $status = self::backend_request('/v1/governance/policy','GET'); $history = self::backend_request('/v1/governance/release-gate/history?limit=5','GET');
        ?>
        <div class="wrap"><h1>Research Quality and Governance Center</h1><p>Control source approval, freshness, quality thresholds, retention, answer traceability, and release gates. Automated signals can recommend action, but they cannot publish, exclude sources, or override a failed gate without human review.</p>
        <div class="card"><h2>Current state</h2><p><strong>Backend:</strong> <?php echo is_wp_error($status)?esc_html($status->get_error_message()):'Connected'; ?></p><p><strong>Policy profile:</strong> <?php echo esc_html($o['profile']); ?></p><p><strong>Recent release gates:</strong> <?php echo esc_html(is_wp_error($history)?0:count($history['runs']??array())); ?></p></div>
        <form method="post"><?php wp_nonce_field('sc_rl_v670_save'); ?><table class="form-table"><tbody>
        <tr><th><label for="profile">Policy profile</label></th><td><input class="regular-text" id="profile" name="profile" value="<?php echo esc_attr($o['profile']); ?>"></td></tr>
        <tr><th>Source governance</th><td><label><input type="checkbox" name="require_approved_sources" <?php checked($o['require_approved_sources'],'1'); ?>> Require explicit approval</label><br><label><input type="checkbox" name="exclude_rejected_sources" <?php checked($o['exclude_rejected_sources'],'1'); ?>> Exclude rejected records</label><br><label><input type="checkbox" name="warn_on_stale_sources" <?php checked($o['warn_on_stale_sources'],'1'); ?>> Warn on stale records</label><br><label>Stale after <input type="number" name="stale_after_days" min="1" max="3650" value="<?php echo esc_attr($o['stale_after_days']); ?>"> days</label></td></tr>
        <tr><th>Privacy and retention</th><td><label>Answer traces <input type="number" name="answer_trace_days" min="1" max="3650" value="<?php echo esc_attr($o['answer_trace_days']); ?>"> days</label><br><label>Evaluations <input type="number" name="quality_evaluation_days" min="30" max="3650" value="<?php echo esc_attr($o['quality_evaluation_days']); ?>"> days</label><br><label>Events <input type="number" name="governance_event_days" min="30" max="3650" value="<?php echo esc_attr($o['governance_event_days']); ?>"> days</label><br><label><input type="checkbox" name="store_query_text" <?php checked($o['store_query_text'],'1'); ?>> Store query text in traces</label><br><label><input type="checkbox" name="store_answer_text" <?php checked($o['store_answer_text'],'1'); ?>> Store answer text in traces</label></td></tr>
        <tr><th>Quality thresholds</th><td><?php foreach(array('exact_title_accuracy','hit_at_3','citation_precision','citation_completeness','unsupported_claim_rate_max','route_accuracy','pdf_page_accuracy','fallback_success','minimum_answer_quality') as $key): ?><label style="display:inline-block;min-width:280px;margin:0 12px 8px 0;"><?php echo esc_html(str_replace('_',' ',ucwords($key,'_'))); ?> <input type="number" step="0.01" min="0" max="1" name="<?php echo esc_attr($key); ?>" value="<?php echo esc_attr($o[$key]); ?>"></label><?php endforeach; ?></td></tr>
        </tbody></table><?php submit_button('Save Governance Policy','primary','sc_rl_v670_save'); ?></form>
        <p><code>[sc_research_librarian_methodology]</code> publishes the methodology and limitations section. <code>[sc_research_librarian_governance_status]</code> publishes a compact public governance status.</p></div><?php
    }

    public static function render_methodology() {
        if ( '1' !== (string) self::options()['methodology_public'] ) { return ''; }
        $m = self::methodology(); ob_start(); ?>
        <section class="sc-rl-governance sc-rl-governance--methodology"><p class="sc-rl-product__eyebrow">Research Quality and Governance</p><h2><?php echo esc_html($m['title']); ?></h2><p>Research Librarian retrieves verified Sustainable Catalyst records before generation and preserves answer, model, prompt, index, policy, and citation provenance.</p>
        <div class="sc-rl-product__grid"><article><strong>Method</strong><ul><?php foreach($m['principles'] as $item): ?><li><?php echo esc_html($item); ?></li><?php endforeach; ?></ul></article><article><strong>Evaluation</strong><ul><?php foreach($m['evaluation'] as $item): ?><li><?php echo esc_html($item); ?></li><?php endforeach; ?></ul></article><article><strong>Limitations</strong><ul><?php foreach($m['limitations'] as $item): ?><li><?php echo esc_html($item); ?></li><?php endforeach; ?></ul></article></div><p class="sc-rl-boundary-note">AI can assist with retrieval and synthesis. Source approval, ranking changes, release overrides, interpretation, and publication remain human decisions.</p></section><?php return ob_get_clean();
    }

    public static function render_status() {
        $o=self::options(); ob_start(); ?><section class="sc-rl-governance sc-rl-governance--status"><p class="sc-rl-product__eyebrow">Public Trust Status</p><h2>Research Librarian Governance</h2><div class="sc-rl-product__grid"><article><span><?php echo esc_html($o['profile']); ?></span><strong>Active policy</strong><p>Versioned quality, source, retention, and human-review controls.</p></article><article><span><?php echo esc_html(absint($o['answer_trace_days'])); ?> days</span><strong>Trace retention</strong><p>Queries and answers are not stored by default; hashes preserve audit linkage.</p></article><article><span>Human</span><strong>Final control</strong><p>No autonomous publication, source exclusion, or release-gate override.</p></article></div></section><?php return ob_get_clean();
    }
}
