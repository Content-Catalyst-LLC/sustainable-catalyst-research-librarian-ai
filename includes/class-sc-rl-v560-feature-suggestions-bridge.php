<?php
/**
 * Research Librarian v5.6.0 Feature Suggestions feedback bridge.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class SC_RL_V560_Feature_Suggestions_Bridge {
    const VERSION = '5.6.0';
    const REST_NAMESPACE = 'sc-research-librarian/v1';
    const EVENT_SCHEMA = 'sc-platform-event/1.0';
    const BRIDGE_SCHEMA = 'sc-librarian-feedback/1.0';
    const LOG_OPTION = 'sc_rl_v560_feedback_bridge_log';
    const STATUS_OPTION = 'sc_rl_v560_feedback_bridge_status';
    const RECEIPT_PREFIX = 'rlfb_';
    const RECEIPT_TTL = 15552000; // 180 days.

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ) );
        add_action( 'admin_menu', array( __CLASS__, 'register_admin_page' ), 85 );
        add_filter( 'sc_rl_integration_capabilities', array( __CLASS__, 'capabilities' ) );
        add_shortcode( 'sc_research_librarian_feedback_status', array( __CLASS__, 'render_status_shortcode' ) );
    }

    public static function register_routes() {
        register_rest_route( self::REST_NAMESPACE, '/feedback/bridge', array(
            'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_submit' ), 'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/feedback/bridge/status', array(
            'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_status' ),
            'permission_callback' => function() { return current_user_can( 'manage_options' ); },
        ) );
        register_rest_route( self::REST_NAMESPACE, '/feedback/bridge/(?P<receipt>[A-Za-z0-9_-]{20,96})', array(
            'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_receipt' ), 'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/feedback/bridge/export', array(
            'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_export' ),
            'permission_callback' => function() { return current_user_can( 'manage_options' ); },
        ) );
    }

    public static function capabilities( $caps = array() ) {
        return array_merge( is_array( $caps ) ? $caps : array(), array(
            'research_librarian_version' => self::VERSION,
            'feature_suggestions_feedback_bridge' => true,
            'feedback_bridge_schema' => self::BRIDGE_SCHEMA,
            'contextual_ratings' => true,
            'route_correction_reports' => true,
            'source_card_feedback' => true,
            'knowledge_gap_reports' => true,
            'missing_tool_reports' => true,
            'receipt_status' => true,
            'duplicate_protection' => true,
            'feature_suggestions_available' => self::feature_suggestions_available(),
        ) );
    }

    private static function feature_suggestions_available() {
        return (bool) ( has_action( 'scfs_research_librarian_feedback' ) || class_exists( 'Sustainable_Catalyst_Feature_Suggestions' ) || post_type_exists( 'sc_feature_suggestion' ) );
    }

    private static function allowed_types() {
        return array(
            'helpful', 'not_helpful', 'wrong_route', 'missing_source', 'irrelevant_source',
            'answer_grounding', 'knowledge_gap', 'missing_topic', 'feature_gap', 'missing_tool', 'unclear', 'issue',
        );
    }

    private static function sanitize_sources( $sources ) {
        $out = array();
        foreach ( is_array( $sources ) ? array_slice( $sources, 0, 8 ) : array() as $source ) {
            if ( ! is_array( $source ) ) { continue; }
            $out[] = array_filter( array(
                'id' => sanitize_text_field( $source['id'] ?? $source['source_id'] ?? '' ),
                'title' => sanitize_text_field( $source['title'] ?? '' ),
                'url' => esc_url_raw( $source['url'] ?? '' ),
                'type' => sanitize_text_field( $source['type'] ?? '' ),
            ) );
        }
        return $out;
    }

    private static function normalize( $input ) {
        $route_note = isset( $input['route_note'] ) && is_array( $input['route_note'] ) ? $input['route_note'] : array();
        $route = isset( $route_note['recommended_route'] ) && is_array( $route_note['recommended_route'] ) ? $route_note['recommended_route'] : array();
        $confidence = isset( $route_note['confidence'] ) && is_array( $route_note['confidence'] ) ? $route_note['confidence'] : array();
        $type = sanitize_key( $input['type'] ?? 'issue' );
        if ( ! in_array( $type, self::allowed_types(), true ) ) { $type = 'issue'; }
        $rating = isset( $input['rating'] ) ? max( 0, min( 5, absint( $input['rating'] ) ) ) : 0;
        $question = sanitize_textarea_field( mb_substr( (string) ( $input['question'] ?? $route_note['question'] ?? '' ), 0, 1200 ) );
        $note = sanitize_textarea_field( mb_substr( (string) ( $input['note'] ?? '' ), 0, 1600 ) );
        $expected = sanitize_textarea_field( mb_substr( (string) ( $input['expected_result'] ?? '' ), 0, 1000 ) );
        $route_id = sanitize_key( $input['route_id'] ?? $route['id'] ?? 'unknown' );
        $sources = self::sanitize_sources( $input['sources'] ?? $route_note['sources'] ?? array() );
        $source = isset( $input['source'] ) && is_array( $input['source'] ) ? self::sanitize_sources( array( $input['source'] ) ) : array();
        $context = array(
            'schema' => self::BRIDGE_SCHEMA,
            'source' => 'research_librarian',
            'source_version' => self::VERSION,
            'feedback_type' => $type,
            'rating' => $rating,
            'question' => $question,
            'note' => $note,
            'expected_result' => $expected,
            'route_id' => $route_id,
            'route_label' => sanitize_text_field( $input['route_label'] ?? $route['title'] ?? '' ),
            'route_url' => esc_url_raw( $input['route_url'] ?? $route['url'] ?? '' ),
            'query_topic' => sanitize_text_field( $input['query_topic'] ?? $route_note['intent'] ?? '' ),
            'article_map' => sanitize_text_field( $input['article_map'] ?? '' ),
            'page_id' => absint( $input['page_id'] ?? 0 ),
            'page_url' => esc_url_raw( $input['page_url'] ?? '' ),
            'session_reference' => sanitize_text_field( $input['session_reference'] ?? '' ),
            'answer_reference' => sanitize_text_field( $input['answer_reference'] ?? $route_note['note_id'] ?? '' ),
            'prompt_reference' => sanitize_text_field( $input['prompt_reference'] ?? '' ),
            'confidence' => sanitize_text_field( $input['confidence'] ?? $confidence['level'] ?? '' ),
            'sources' => $sources,
            'source_card' => ! empty( $source ) ? $source[0] : array(),
            'consent' => ! empty( $input['consent'] ),
        );
        $context['fingerprint'] = hash( 'sha256', wp_json_encode( array( $type, $route_id, $question, $note, $context['source_card'] ) ) );
        return $context;
    }

    private static function duplicate( $fingerprint ) {
        foreach ( self::logs() as $row ) {
            if ( ! empty( $row['fingerprint'] ) && hash_equals( (string) $row['fingerprint'], (string) $fingerprint ) && ! empty( $row['created_ts'] ) && ( time() - absint( $row['created_ts'] ) ) < DAY_IN_SECONDS ) {
                return $row;
            }
        }
        return false;
    }

    private static function receipt() {
        return self::RECEIPT_PREFIX . wp_generate_password( 32, false, false );
    }

    private static function logs() {
        $rows = get_option( self::LOG_OPTION, array() );
        return is_array( $rows ) ? $rows : array();
    }

    private static function save( $row ) {
        $rows = self::logs();
        array_unshift( $rows, $row );
        update_option( self::LOG_OPTION, array_slice( $rows, 0, 500 ), false );
        update_option( self::STATUS_OPTION, array(
            'last_submission_utc' => $row['created_at'],
            'last_status' => $row['status'],
            'last_type' => $row['feedback_type'],
            'feature_suggestions_available' => self::feature_suggestions_available(),
        ), false );
    }

    private static function publish_event( $type, $payload, $extra = array() ) {
        $event = array_merge( array(
            'schema' => self::EVENT_SCHEMA,
            'event_type' => sanitize_key( $type ),
            'source' => 'research_librarian',
            'source_version' => self::VERSION,
            'occurred_at' => gmdate( 'c' ),
            'correlation_id' => $payload['receipt'] ?? '',
            'context' => array_filter( array(
                'feedback_type' => $payload['feedback_type'] ?? '',
                'rating' => $payload['rating'] ?? 0,
                'route_id' => $payload['route_id'] ?? '',
                'query_topic' => $payload['query_topic'] ?? '',
                'page_id' => $payload['page_id'] ?? 0,
                'status' => $payload['status'] ?? '',
            ) ),
            'privacy' => array( 'contains_raw_conversation'=>false, 'contains_api_key'=>false, 'contains_email'=>false, 'contains_ip'=>false ),
        ), $extra );
        do_action( 'sc_rl_event', $event );
        do_action( 'sc_platform_event', $event );
        return $event;
    }

    public static function rest_submit( WP_REST_Request $request ) {
        $params = $request->get_json_params();
        $params = is_array( $params ) ? $params : $request->get_params();
        if ( empty( $params['consent'] ) ) {
            return new WP_Error( 'consent_required', 'Consent is required to submit contextual feedback.', array( 'status' => 400 ) );
        }
        $payload = self::normalize( $params );
        $existing = self::duplicate( $payload['fingerprint'] );
        if ( $existing ) {
            return new WP_REST_Response( array( 'ok'=>true, 'duplicate'=>true, 'receipt'=>$existing['receipt'], 'status'=>$existing['status'], 'status_url'=>rest_url( self::REST_NAMESPACE . '/feedback/bridge/' . $existing['receipt'] ) ), 200 );
        }
        $receipt = self::receipt();
        $payload['receipt'] = $receipt;
        $payload['created_at'] = gmdate( 'c' );
        $payload['created_ts'] = time();
        $payload['expires_at'] = gmdate( 'c', time() + self::RECEIPT_TTL );
        $payload['status'] = 'received';
        $payload['feature_suggestions_available'] = self::feature_suggestions_available();

        $handoff = array(
            'feedback_type' => $payload['feedback_type'], 'rating' => $payload['rating'], 'question' => $payload['question'],
            'note' => $payload['note'], 'expected_result' => $payload['expected_result'], 'route_id' => $payload['route_id'],
            'route_label' => $payload['route_label'], 'query_topic' => $payload['query_topic'], 'article_map' => $payload['article_map'],
            'page_id' => $payload['page_id'], 'page_url' => $payload['page_url'], 'session_reference' => $payload['session_reference'],
            'answer_reference' => $payload['answer_reference'], 'prompt_reference' => $payload['prompt_reference'],
            'confidence' => $payload['confidence'], 'sources' => $payload['sources'], 'source_card' => $payload['source_card'],
            'consent' => true, 'external_receipt' => $receipt, 'source_product' => 'research_librarian',
        );
        $result = apply_filters( 'scfs_research_librarian_feedback_response', null, $handoff );
        do_action( 'scfs_research_librarian_feedback', $handoff );
        if ( is_array( $result ) ) {
            $payload['feature_suggestions_reference'] = sanitize_text_field( $result['uuid'] ?? $result['submission_uuid'] ?? '' );
            $payload['status'] = sanitize_key( $result['status'] ?? 'forwarded' );
        } elseif ( $payload['feature_suggestions_available'] ) {
            $payload['status'] = 'forwarded';
        } else {
            $payload['status'] = 'queued_locally';
        }
        self::save( $payload );
        self::publish_event( 'librarian.feedback_submitted', $payload );
        if ( 'helpful' !== $payload['feedback_type'] ) { self::publish_event( 'librarian.feedback_bridge_created', $payload ); }
        return new WP_REST_Response( array(
            'ok'=>true, 'duplicate'=>false, 'receipt'=>$receipt, 'status'=>$payload['status'],
            'feature_suggestions_available'=>$payload['feature_suggestions_available'],
            'status_url'=>rest_url( self::REST_NAMESPACE . '/feedback/bridge/' . $receipt ),
            'message'=>'Feedback received. It will remain subject to human review.',
        ), 201 );
    }

    public static function rest_receipt( WP_REST_Request $request ) {
        $receipt = sanitize_text_field( $request['receipt'] );
        foreach ( self::logs() as $row ) {
            if ( ! empty( $row['receipt'] ) && hash_equals( (string) $row['receipt'], $receipt ) ) {
                if ( ! empty( $row['created_ts'] ) && ( time() - absint( $row['created_ts'] ) ) > self::RECEIPT_TTL ) {
                    return new WP_Error( 'receipt_expired', 'This feedback receipt has expired.', array( 'status'=>410 ) );
                }
                return new WP_REST_Response( array(
                    'receipt'=>$receipt, 'status'=>$row['status'], 'feedback_type'=>$row['feedback_type'],
                    'created_at'=>$row['created_at'], 'expires_at'=>$row['expires_at'],
                    'feature_suggestions_reference'=>$row['feature_suggestions_reference'] ?? '',
                ), 200 );
            }
        }
        return new WP_Error( 'receipt_not_found', 'Feedback receipt not found.', array( 'status'=>404 ) );
    }

    private static function summary() {
        $rows = self::logs(); $types = array(); $statuses = array();
        foreach ( $rows as $row ) { $types[$row['feedback_type']] = ($types[$row['feedback_type']] ?? 0) + 1; $statuses[$row['status']] = ($statuses[$row['status']] ?? 0) + 1; }
        return array(
            'version'=>self::VERSION, 'total'=>count($rows), 'types'=>$types, 'statuses'=>$statuses,
            'feature_suggestions_available'=>self::feature_suggestions_available(),
            'last'=>get_option(self::STATUS_OPTION,array()), 'receipt_ttl_days'=>180,
        );
    }

    public static function rest_status() { return new WP_REST_Response( self::summary(), 200 ); }
    public static function rest_export() { return new WP_REST_Response( array( 'generated_at'=>gmdate('c'), 'summary'=>self::summary(), 'records'=>self::logs() ), 200 ); }

    public static function register_admin_page() {
        add_submenu_page( 'options-general.php', 'Research Librarian Feedback Bridge', 'Research Librarian Feedback Bridge', 'manage_options', 'sc-rl-feedback-bridge', array( __CLASS__, 'render_admin_page' ) );
    }

    public static function render_admin_page() {
        if ( ! current_user_can( 'manage_options' ) ) { wp_die( 'You do not have permission to access this page.' ); }
        $summary = self::summary(); $rows = array_slice( self::logs(), 0, 50 );
        ?>
        <div class="wrap"><h1>Research Librarian Feedback Bridge</h1>
        <p>Contextual Research Librarian feedback is retained locally, normalized for Feature Suggestions, and published as privacy-minimized Site Intelligence events.</p>
        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;max-width:1100px;margin:16px 0;">
        <div class="postbox" style="padding:14px"><strong style="font-size:22px;display:block"><?php echo esc_html($summary['total']); ?></strong><span>Total bridge records</span></div>
        <div class="postbox" style="padding:14px"><strong style="font-size:22px;display:block"><?php echo $summary['feature_suggestions_available'] ? 'Connected' : 'Local queue'; ?></strong><span>Feature Suggestions</span></div>
        <div class="postbox" style="padding:14px"><strong style="font-size:22px;display:block"><?php echo esc_html(count($summary['types'])); ?></strong><span>Feedback types</span></div>
        <div class="postbox" style="padding:14px"><strong style="font-size:22px;display:block">180 days</strong><span>Receipt lifetime</span></div></div>
        <p><a class="button" href="<?php echo esc_url(rest_url(self::REST_NAMESPACE.'/feedback/bridge/export')); ?>">Export Bridge JSON</a></p>
        <table class="widefat striped"><thead><tr><th>Created</th><th>Type</th><th>Route</th><th>Rating</th><th>Status</th><th>Receipt</th></tr></thead><tbody>
        <?php if(!$rows): ?><tr><td colspan="6">No contextual feedback has been received yet.</td></tr><?php endif; ?>
        <?php foreach($rows as $row): ?><tr><td><?php echo esc_html($row['created_at']); ?></td><td><?php echo esc_html($row['feedback_type']); ?></td><td><?php echo esc_html($row['route_id']); ?></td><td><?php echo esc_html($row['rating'] ?: '—'); ?></td><td><?php echo esc_html($row['status']); ?></td><td><code><?php echo esc_html($row['receipt']); ?></code></td></tr><?php endforeach; ?>
        </tbody></table><p><em>Raw conversations, email addresses, IP addresses, and API keys are not included in bridge records or shared events.</em></p></div><?php
    }

    public static function render_status_shortcode() {
        $summary = self::summary();
        return '<section class="sc-rl-product sc-rl-feedback-bridge-status"><p class="sc-rl-product__eyebrow">Feedback Bridge</p><h2>Research feedback connection</h2><p>' . esc_html( $summary['feature_suggestions_available'] ? 'Feature Suggestions is available for contextual handoffs.' : 'Contextual feedback is being retained in the Research Librarian local queue.' ) . '</p><p class="sc-rl-boundary-note">All submissions remain subject to human review. Public support signals and AI classifications do not make roadmap decisions.</p></section>';
    }
}
