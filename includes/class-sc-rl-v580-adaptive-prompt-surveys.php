<?php
/**
 * Research Librarian v5.8.0 Adaptive Prompt and Survey Experiences.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class SC_RL_V580_Adaptive_Prompt_Surveys {
    const VERSION = '5.8.0';
    const REST_NAMESPACE = 'sc-research-librarian/v1';
    const RULE_SCHEMA = 'sc-adaptive-experience-rule/1.0';
    const EVENT_SCHEMA = 'sc-platform-event/1.0';
    const RULES_OPTION = 'sc_rl_v580_adaptive_rules';
    const SETTINGS_OPTION = 'sc_rl_v580_adaptive_settings';
    const LOG_OPTION = 'sc_rl_v580_adaptive_log';
    const AUDIT_OPTION = 'sc_rl_v580_adaptive_audit';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ) );
        add_action( 'admin_menu', array( __CLASS__, 'register_admin_page' ), 87 );
        add_action( 'wp_enqueue_scripts', array( __CLASS__, 'enqueue_assets' ) );
        add_filter( 'sc_rl_integration_capabilities', array( __CLASS__, 'capabilities' ) );
        add_shortcode( 'sc_research_librarian_adaptive_experience', array( __CLASS__, 'shortcode' ) );
    }

    public static function capabilities( $caps = array() ) {
        return array_merge( is_array( $caps ) ? $caps : array(), array(
            'research_librarian_version' => self::VERSION,
            'adaptive_prompt_experiences' => true,
            'contextual_survey_triggers' => true,
            'feature_suggestions_survey_handoff' => true,
            'frequency_caps' => true,
            'consent_aware_targeting' => true,
            'adaptive_rule_schema' => self::RULE_SCHEMA,
        ) );
    }

    private static function defaults() {
        return array(
            array(
                'id' => 'low-confidence-goal', 'enabled' => true, 'name' => 'Low-confidence research goal',
                'trigger' => 'low_confidence', 'threshold' => 50, 'route' => '', 'minimum_sources' => 0,
                'title' => 'Help us improve this research path',
                'message' => 'What were you hoping to find, and what would make this route more useful?',
                'experience_type' => 'inline_feedback', 'survey_id' => '', 'destination_url' => '',
                'button_label' => 'Share research goal', 'priority' => 80,
            ),
            array(
                'id' => 'missing-tool-demand', 'enabled' => true, 'name' => 'Repeated tool demand',
                'trigger' => 'tool_demand', 'threshold' => 1, 'route' => '', 'minimum_sources' => 0,
                'title' => 'Would a calculator or analysis tool help?',
                'message' => 'Tell us what you would need the tool to calculate, compare, or explain.',
                'experience_type' => 'feature_suggestion', 'survey_id' => '', 'destination_url' => '',
                'button_label' => 'Describe the tool', 'priority' => 70,
            ),
            array(
                'id' => 'completed-path-survey', 'enabled' => false, 'name' => 'Completed path survey',
                'trigger' => 'path_completed', 'threshold' => 1, 'route' => '', 'minimum_sources' => 0,
                'title' => 'How useful was this research path?',
                'message' => 'A short survey can help improve routes, sources, and follow-up prompts.',
                'experience_type' => 'survey', 'survey_id' => '', 'destination_url' => '',
                'button_label' => 'Take the short survey', 'priority' => 50,
            ),
        );
    }

    private static function settings() {
        return wp_parse_args( get_option( self::SETTINGS_OPTION, array() ), array(
            'enabled' => true,
            'require_consent' => true,
            'daily_cap' => 2,
            'cooldown_hours' => 24,
            'dismiss_days' => 14,
            'minimum_seconds_on_page' => 8,
            'log_limit' => 500,
        ) );
    }

    private static function rules() {
        $rules = get_option( self::RULES_OPTION, array() );
        if ( ! is_array( $rules ) || empty( $rules ) ) { $rules = self::defaults(); }
        return array_values( array_filter( array_map( array( __CLASS__, 'sanitize_rule' ), $rules ) ) );
    }

    private static function sanitize_rule( $rule ) {
        if ( ! is_array( $rule ) ) { return array(); }
        $types = array( 'inline_feedback', 'survey', 'feature_suggestion', 'prompt_library' );
        $triggers = array( 'low_confidence', 'zero_sources', 'source_opened', 'route_abandoned', 'path_completed', 'tool_demand', 'decision_handoff', 'workbench_handoff', 'always' );
        return array(
            'schema' => self::RULE_SCHEMA,
            'id' => sanitize_key( $rule['id'] ?? wp_generate_uuid4() ),
            'enabled' => ! empty( $rule['enabled'] ),
            'name' => sanitize_text_field( $rule['name'] ?? 'Adaptive experience' ),
            'trigger' => in_array( $rule['trigger'] ?? '', $triggers, true ) ? $rule['trigger'] : 'always',
            'threshold' => max( 0, min( 100, absint( $rule['threshold'] ?? 0 ) ) ),
            'route' => sanitize_key( $rule['route'] ?? '' ),
            'minimum_sources' => max( 0, absint( $rule['minimum_sources'] ?? 0 ) ),
            'title' => sanitize_text_field( $rule['title'] ?? '' ),
            'message' => sanitize_textarea_field( $rule['message'] ?? '' ),
            'experience_type' => in_array( $rule['experience_type'] ?? '', $types, true ) ? $rule['experience_type'] : 'inline_feedback',
            'survey_id' => sanitize_text_field( $rule['survey_id'] ?? '' ),
            'destination_url' => esc_url_raw( $rule['destination_url'] ?? '' ),
            'button_label' => sanitize_text_field( $rule['button_label'] ?? 'Continue' ),
            'priority' => max( 0, min( 100, absint( $rule['priority'] ?? 50 ) ) ),
        );
    }

    public static function enqueue_assets() {
        if ( is_admin() || ! self::settings()['enabled'] ) { return; }
        wp_enqueue_style( 'sc-rl-v580-adaptive', plugins_url( '../assets/sc-rl-adaptive-experiences.css', __FILE__ ), array(), self::VERSION );
        wp_enqueue_script( 'sc-rl-v580-adaptive', plugins_url( '../assets/sc-rl-adaptive-experiences.js', __FILE__ ), array(), self::VERSION, true );
        wp_localize_script( 'sc-rl-v580-adaptive', 'SCRLAdaptive', array(
            'evaluateUrl' => rest_url( self::REST_NAMESPACE . '/adaptive/evaluate' ),
            'respondUrl' => rest_url( self::REST_NAMESPACE . '/adaptive/respond' ),
            'nonce' => wp_create_nonce( 'wp_rest' ),
            'settings' => array(
                'dailyCap' => absint( self::settings()['daily_cap'] ),
                'cooldownHours' => absint( self::settings()['cooldown_hours'] ),
                'dismissDays' => absint( self::settings()['dismiss_days'] ),
                'minimumSeconds' => absint( self::settings()['minimum_seconds_on_page'] ),
                'requireConsent' => ! empty( self::settings()['require_consent'] ),
            ),
        ) );
    }

    public static function register_routes() {
        register_rest_route( self::REST_NAMESPACE, '/adaptive/evaluate', array(
            'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_evaluate' ), 'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/adaptive/respond', array(
            'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_respond' ), 'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/adaptive/rules', array(
            'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_rules' ), 'permission_callback' => function(){ return current_user_can( 'manage_options' ); },
        ) );
        register_rest_route( self::REST_NAMESPACE, '/adaptive/analytics', array(
            'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_analytics' ), 'permission_callback' => function(){ return current_user_can( 'manage_options' ); },
        ) );
    }

    private static function context( WP_REST_Request $request ) {
        $p = (array) $request->get_json_params();
        return array(
            'trigger' => sanitize_key( $p['trigger'] ?? 'always' ),
            'route_id' => sanitize_key( $p['route_id'] ?? '' ),
            'confidence' => max( 0, min( 100, (float) ( $p['confidence'] ?? 0 ) ) ),
            'source_count' => max( 0, absint( $p['source_count'] ?? 0 ) ),
            'query_topic' => sanitize_text_field( $p['query_topic'] ?? '' ),
            'article_map' => sanitize_key( $p['article_map'] ?? '' ),
            'session_ref' => sanitize_text_field( $p['session_ref'] ?? '' ),
            'answer_ref' => sanitize_text_field( $p['answer_ref'] ?? '' ),
            'consent' => ! empty( $p['consent'] ),
            'page_url' => esc_url_raw( $p['page_url'] ?? '' ),
        );
    }

    private static function matches( $rule, $ctx ) {
        if ( empty( $rule['enabled'] ) ) { return false; }
        if ( $rule['route'] && $rule['route'] !== $ctx['route_id'] ) { return false; }
        if ( $rule['minimum_sources'] && $ctx['source_count'] < $rule['minimum_sources'] ) { return false; }
        switch ( $rule['trigger'] ) {
            case 'low_confidence': return $ctx['confidence'] > 0 && $ctx['confidence'] <= $rule['threshold'];
            case 'zero_sources': return 0 === $ctx['source_count'];
            case 'tool_demand': return in_array( $ctx['trigger'], array( 'tool_demand', 'workbench_handoff' ), true );
            case 'decision_handoff': return 'decision_handoff' === $ctx['trigger'];
            case 'workbench_handoff': return 'workbench_handoff' === $ctx['trigger'];
            case 'always': return true;
            default: return $rule['trigger'] === $ctx['trigger'];
        }
    }

    public static function rest_evaluate( WP_REST_Request $request ) {
        if ( ! self::settings()['enabled'] ) { return new WP_REST_Response( array( 'eligible' => false, 'reason' => 'disabled' ), 200 ); }
        $ctx = self::context( $request );
        if ( self::settings()['require_consent'] && empty( $ctx['consent'] ) ) { return new WP_REST_Response( array( 'eligible' => false, 'reason' => 'consent_required' ), 200 ); }
        $eligible = array_values( array_filter( self::rules(), function( $rule ) use ( $ctx ) { return self::matches( $rule, $ctx ); } ) );
        usort( $eligible, function( $a, $b ){ return (int) $b['priority'] <=> (int) $a['priority']; } );
        if ( empty( $eligible ) ) { return new WP_REST_Response( array( 'eligible' => false, 'reason' => 'no_matching_rule' ), 200 ); }
        $rule = $eligible[0];
        $receipt = wp_generate_uuid4();
        self::log( 'experience_offered', $rule, $ctx, $receipt );
        self::publish_event( 'librarian.adaptive_experience_offered', array( 'rule_id' => $rule['id'], 'trigger' => $ctx['trigger'], 'route_id' => $ctx['route_id'], 'experience_type' => $rule['experience_type'] ) );
        return new WP_REST_Response( array(
            'eligible' => true, 'receipt' => $receipt,
            'experience' => array_intersect_key( $rule, array_flip( array( 'id','title','message','experience_type','survey_id','destination_url','button_label' ) ) ),
        ), 200 );
    }

    public static function rest_respond( WP_REST_Request $request ) {
        $p = (array) $request->get_json_params();
        $rule_id = sanitize_key( $p['rule_id'] ?? '' );
        $receipt = sanitize_text_field( $p['receipt'] ?? '' );
        $action = sanitize_key( $p['action'] ?? 'dismissed' );
        $allowed = array( 'opened','submitted','dismissed','later','handoff' );
        if ( ! in_array( $action, $allowed, true ) ) { $action = 'dismissed'; }
        $rule = null; foreach ( self::rules() as $candidate ) { if ( $candidate['id'] === $rule_id ) { $rule = $candidate; break; } }
        if ( ! $rule ) { return new WP_Error( 'rule_not_found', 'Adaptive experience rule was not found.', array( 'status' => 404 ) ); }
        $ctx = array(
            'route_id' => sanitize_key( $p['route_id'] ?? '' ), 'query_topic' => sanitize_text_field( $p['query_topic'] ?? '' ),
            'session_ref' => sanitize_text_field( $p['session_ref'] ?? '' ), 'answer_ref' => sanitize_text_field( $p['answer_ref'] ?? '' ),
            'response' => sanitize_textarea_field( $p['response'] ?? '' ), 'rating' => max( 0, min( 5, absint( $p['rating'] ?? 0 ) ) ),
        );
        self::log( 'experience_' . $action, $rule, $ctx, $receipt );
        $handoff = array();
        if ( in_array( $action, array( 'submitted','handoff' ), true ) ) {
            $handoff = self::handoff( $rule, $ctx, $receipt );
        }
        self::publish_event( 'librarian.adaptive_experience_' . $action, array( 'rule_id' => $rule_id, 'experience_type' => $rule['experience_type'], 'route_id' => $ctx['route_id'], 'has_response' => '' !== $ctx['response'], 'rating' => $ctx['rating'] ) );
        return new WP_REST_Response( array( 'ok' => true, 'receipt' => $receipt, 'handoff' => $handoff ), 200 );
    }

    private static function handoff( $rule, $ctx, $receipt ) {
        $payload = array(
            'schema' => 'sc-librarian-adaptive-handoff/1.0', 'source' => 'research_librarian', 'source_version' => self::VERSION,
            'rule_id' => $rule['id'], 'experience_type' => $rule['experience_type'], 'survey_id' => $rule['survey_id'],
            'route_id' => $ctx['route_id'], 'query_topic' => $ctx['query_topic'], 'session_ref' => $ctx['session_ref'],
            'answer_ref' => $ctx['answer_ref'], 'response' => $ctx['response'], 'rating' => $ctx['rating'], 'receipt' => $receipt,
        );
        $result = apply_filters( 'sc_rl_adaptive_survey_handoff', array(), $payload );
        do_action( 'scfs_research_librarian_survey_handoff', $payload );
        if ( 'inline_feedback' === $rule['experience_type'] && class_exists( 'SC_RL_V560_Feature_Suggestions_Bridge' ) ) {
            do_action( 'sc_rl_v580_inline_feedback', $payload );
        }
        return is_array( $result ) ? $result : array();
    }

    private static function log( $event, $rule, $ctx, $receipt ) {
        $rows = get_option( self::LOG_OPTION, array() ); if ( ! is_array( $rows ) ) { $rows = array(); }
        array_unshift( $rows, array(
            'event' => sanitize_key( $event ), 'rule_id' => $rule['id'], 'experience_type' => $rule['experience_type'],
            'route_id' => sanitize_key( $ctx['route_id'] ?? '' ), 'query_topic' => sanitize_text_field( $ctx['query_topic'] ?? '' ),
            'rating' => absint( $ctx['rating'] ?? 0 ), 'has_response' => ! empty( $ctx['response'] ),
            'receipt' => sanitize_text_field( $receipt ), 'occurred_at' => gmdate( 'c' ),
        ) );
        update_option( self::LOG_OPTION, array_slice( $rows, 0, max( 50, absint( self::settings()['log_limit'] ) ) ), false );
    }

    private static function publish_event( $type, $context ) {
        $event = array(
            'schema' => self::EVENT_SCHEMA, 'event_type' => sanitize_key( $type ), 'source' => 'research_librarian',
            'source_version' => self::VERSION, 'occurred_at' => gmdate( 'c' ), 'context' => $context,
            'privacy' => array( 'contains_raw_conversation' => false, 'contains_email' => false, 'contains_ip' => false, 'contains_api_key' => false ),
        );
        do_action( 'sc_rl_event', $event ); do_action( 'sc_platform_event', $event );
    }

    public static function analytics() {
        $rows = get_option( self::LOG_OPTION, array() ); if ( ! is_array( $rows ) ) { $rows = array(); }
        $out = array( 'total' => count( $rows ), 'events' => array(), 'rules' => array(), 'types' => array(), 'ratings' => array(), 'generated_at' => gmdate( 'c' ) );
        foreach ( $rows as $row ) {
            foreach ( array( 'events' => $row['event'] ?? 'unknown', 'rules' => $row['rule_id'] ?? 'unknown', 'types' => $row['experience_type'] ?? 'unknown' ) as $bucket => $key ) {
                $out[ $bucket ][ $key ] = ( $out[ $bucket ][ $key ] ?? 0 ) + 1;
            }
            if ( ! empty( $row['rating'] ) ) { $out['ratings'][ (string) $row['rating'] ] = ( $out['ratings'][ (string) $row['rating'] ] ?? 0 ) + 1; }
        }
        return $out;
    }

    public static function rest_rules() { return new WP_REST_Response( array( 'schema' => self::RULE_SCHEMA, 'rules' => self::rules(), 'settings' => self::settings() ), 200 ); }
    public static function rest_analytics() { return new WP_REST_Response( self::analytics(), 200 ); }

    public static function shortcode( $atts ) {
        $atts = shortcode_atts( array( 'trigger' => 'always', 'route' => '', 'topic' => '', 'consent' => 'true' ), $atts );
        return '<div class="sc-rl-adaptive-host" data-sc-rl-adaptive-host data-trigger="' . esc_attr( $atts['trigger'] ) . '" data-route="' . esc_attr( $atts['route'] ) . '" data-topic="' . esc_attr( $atts['topic'] ) . '" data-consent="' . esc_attr( $atts['consent'] ) . '"></div>';
    }

    public static function register_admin_page() {
        add_submenu_page( 'options-general.php', 'Adaptive Prompts and Surveys', 'Adaptive Prompts and Surveys', 'manage_options', 'sc-rl-adaptive-experiences', array( __CLASS__, 'render_admin_page' ) );
    }

    public static function render_admin_page() {
        if ( ! current_user_can( 'manage_options' ) ) { wp_die( 'You do not have permission to access this page.' ); }
        if ( isset( $_POST['sc_rl_v580_save'] ) && check_admin_referer( 'sc_rl_v580_save' ) ) {
            $settings = array(
                'enabled' => ! empty( $_POST['enabled'] ), 'require_consent' => ! empty( $_POST['require_consent'] ),
                'daily_cap' => max( 1, min( 10, absint( $_POST['daily_cap'] ?? 2 ) ) ),
                'cooldown_hours' => max( 1, min( 168, absint( $_POST['cooldown_hours'] ?? 24 ) ) ),
                'dismiss_days' => max( 1, min( 365, absint( $_POST['dismiss_days'] ?? 14 ) ) ),
                'minimum_seconds_on_page' => max( 0, min( 120, absint( $_POST['minimum_seconds_on_page'] ?? 8 ) ) ),
                'log_limit' => max( 50, min( 5000, absint( $_POST['log_limit'] ?? 500 ) ) ),
            );
            update_option( self::SETTINGS_OPTION, $settings, false );
            if ( isset( $_POST['rules_json'] ) ) {
                $decoded = json_decode( wp_unslash( $_POST['rules_json'] ), true );
                if ( is_array( $decoded ) ) { update_option( self::RULES_OPTION, array_values( array_filter( array_map( array( __CLASS__, 'sanitize_rule' ), $decoded ) ) ), false ); }
            }
            self::audit( 'settings_saved' );
            echo '<div class="notice notice-success"><p>Adaptive experience settings saved.</p></div>';
        }
        $settings = self::settings(); $rules = self::rules(); $analytics = self::analytics();
        echo '<div class="wrap"><h1>Adaptive Prompt and Survey Experiences</h1><p>Configure contextual, consent-aware prompts without turning the Research Librarian into an intrusive survey layer. All targeting is rule-based and all resulting insights remain advisory.</p>';
        echo '<form method="post">'; wp_nonce_field( 'sc_rl_v580_save' );
        echo '<table class="form-table"><tr><th>Enable adaptive experiences</th><td><label><input type="checkbox" name="enabled" value="1" ' . checked( $settings['enabled'], true, false ) . '> Enabled</label></td></tr>';
        echo '<tr><th>Require consent signal</th><td><label><input type="checkbox" name="require_consent" value="1" ' . checked( $settings['require_consent'], true, false ) . '> Do not evaluate a visitor without a consent signal</label></td></tr>';
        foreach ( array( 'daily_cap' => 'Daily experience cap', 'cooldown_hours' => 'Cooldown hours', 'dismiss_days' => 'Dismissal suppression days', 'minimum_seconds_on_page' => 'Minimum seconds on page', 'log_limit' => 'Bounded analytics log size' ) as $key => $label ) {
            echo '<tr><th>' . esc_html( $label ) . '</th><td><input type="number" name="' . esc_attr( $key ) . '" value="' . esc_attr( $settings[ $key ] ) . '"></td></tr>';
        }
        echo '</table><h2>Rules JSON</h2><p>Edit or export the versioned rule set. Invalid entries are ignored and sanitized on save.</p><textarea name="rules_json" rows="28" class="large-text code">' . esc_textarea( wp_json_encode( $rules, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) ) . '</textarea>';
        submit_button( 'Save adaptive experience settings', 'primary', 'sc_rl_v580_save' ); echo '</form>';
        echo '<h2>Aggregate analytics</h2><pre style="max-height:420px;overflow:auto;background:#fff;padding:16px;border:1px solid #ccd0d4">' . esc_html( wp_json_encode( $analytics, JSON_PRETTY_PRINT ) ) . '</pre>';
        echo '<h2>Integration notes</h2><ul><li>Feature Suggestions survey handoffs use <code>scfs_research_librarian_survey_handoff</code>.</li><li>Custom consumers may use <code>sc_rl_adaptive_survey_handoff</code>.</li><li>Site Intelligence receives privacy-minimized aggregate interaction events.</li></ul></div>';
    }

    private static function audit( $action ) {
        $rows = get_option( self::AUDIT_OPTION, array() ); if ( ! is_array( $rows ) ) { $rows = array(); }
        array_unshift( $rows, array( 'action' => sanitize_key( $action ), 'user_id' => get_current_user_id(), 'occurred_at' => gmdate( 'c' ) ) );
        update_option( self::AUDIT_OPTION, array_slice( $rows, 0, 200 ), false );
    }
}
