<?php
/**
 * Research Librarian AI v7.1.2 — Cross-Product Reliability Patch.
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class SC_RL6_V660_Platform_Handoffs {
    const VERSION = '7.1.2';
    const OPTION_NAME = 'sc_rl_v660_platform_options';
    const STATUS_OPTION = 'sc_rl_v660_platform_status';
    const LOG_OPTION = 'sc_rl_v660_handoff_log';
    const ARTIFACT_OPTION = 'sc_rl_v660_artifact_returns';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';
    const HANDOFF_SCHEMA = 'sc-research-handoff/2.0';
    const ROUTE_SCHEMA = 'sc-research-route/2.0';
    const ARTIFACT_SCHEMA = 'sc-research-artifact-return/1.0';
    const CAPABILITIES_SCHEMA = 'sc-platform-capabilities/1.1';
    const COMPATIBILITY_SCHEMA = 'sc-platform-compatibility/1.0';
    const DELIVERY_SCHEMA = 'sc-research-handoff-delivery/1.0';
    const RECEIPT_SCHEMA = 'sc-research-handoff-receipt/1.0';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_rest_routes' ), 125 );
        add_action( 'admin_menu', array( __CLASS__, 'register_admin_menu' ), 1030 );
        add_shortcode( 'sc_research_librarian_platform_handoffs', array( __CLASS__, 'render_summary' ) );
    }

    public static function activate() {
        $existing = get_option( self::OPTION_NAME, array() );
        update_option( self::OPTION_NAME, wp_parse_args( is_array( $existing ) ? $existing : array(), self::defaults() ), false );
    }

    public static function defaults() {
        return array(
            'workbench_enabled' => '1',
            'workbench_url' => 'https://sustainablecatalyst.com/modeling-analytics/workbench/',
            'workbench_version' => 'unknown',
            'decision_studio_enabled' => '1',
            'decision_studio_url' => 'https://sustainablecatalyst.com/platform/decision-studio/',
            'decision_studio_version' => 'unknown',
            'site_intelligence_enabled' => '1',
            'site_intelligence_url' => 'https://sustainablecatalyst.com/platform/site-intelligence/',
            'site_intelligence_version' => 'unknown',
            'lab_enabled' => '1',
            'lab_url' => 'https://sustainablecatalyst.com/lab/',
            'lab_version' => 'unknown',
            'feature_suggestions_enabled' => '1',
            'feature_suggestions_url' => 'https://sustainablecatalyst.com/platform/feature-suggestions/',
            'feature_suggestions_version' => 'unknown',
            'log_limit' => 100,
            'retry_limit' => 3,
            'retry_base_seconds' => 30,
            'delivery_ttl_seconds' => 1800,
            'event_ttl_seconds' => 86400,
            'max_artifact_bytes' => 1048576,
        );
    }

    public static function options() {
        return wp_parse_args( get_option( self::OPTION_NAME, array() ), self::defaults() );
    }

    public static function register_rest_routes() {
        register_rest_route( self::REST_NAMESPACE, '/platform/capabilities', array(
            'methods' => WP_REST_Server::READABLE,
            'callback' => array( __CLASS__, 'rest_capabilities' ),
            'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/compatibility', array(
            'methods' => WP_REST_Server::READABLE,
            'callback' => array( __CLASS__, 'rest_compatibility' ),
            'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/handoff/prepare', array(
            'methods' => WP_REST_Server::CREATABLE,
            'callback' => array( __CLASS__, 'rest_prepare' ),
            'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/handoff/validate', array(
            'methods' => WP_REST_Server::CREATABLE,
            'callback' => array( __CLASS__, 'rest_validate' ),
            'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/handoff/retry', array(
            'methods' => WP_REST_Server::CREATABLE,
            'callback' => array( __CLASS__, 'rest_retry' ),
            'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/handoff/token/refresh', array(
            'methods' => WP_REST_Server::CREATABLE,
            'callback' => array( __CLASS__, 'rest_token_refresh' ),
            'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/handoff/receipt', array(
            'methods' => WP_REST_Server::CREATABLE,
            'callback' => array( __CLASS__, 'rest_receipt' ),
            'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/artifact/return', array(
            'methods' => WP_REST_Server::CREATABLE,
            'callback' => array( __CLASS__, 'rest_artifact_return' ),
            'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/handoffs/export', array(
            'methods' => WP_REST_Server::READABLE,
            'callback' => array( __CLASS__, 'rest_export' ),
            'permission_callback' => array( __CLASS__, 'can_manage' ),
        ) );
    }

    public static function can_manage() {
        return current_user_can( 'manage_options' );
    }

    private static function require_nonce( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_v660_bad_nonce', __( 'Security check failed. Refresh the page and try again.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 403 ) );
        }
        return true;
    }

    private static function minimum_version( $id ) {
        $versions = array(
            'workbench' => '4.0.0',
            'decision_studio' => '1.0.0',
            'site_intelligence' => '2.0.0',
            'lab' => '0.6.0',
            'feature_suggestions' => '3.0.0',
        );
        return isset( $versions[ $id ] ) ? $versions[ $id ] : '0.0.0';
    }

    public static function version_compatibility( $version, $minimum, $enabled = true, $url = '' ) {
        if ( ! $enabled || '' === trim( (string) $url ) ) {
            return array( 'state' => 'disabled', 'compatible' => false, 'verified' => true, 'reason' => 'Destination is disabled or has no URL.' );
        }
        if ( ! preg_match( '/\d+\.\d+(?:\.\d+)?/', (string) $version, $match ) ) {
            return array( 'state' => 'unverified', 'compatible' => true, 'verified' => false, 'reason' => 'Destination version is unknown; intake must validate the contract.' );
        }
        $compatible = version_compare( $match[0], $minimum, '>=' );
        return array(
            'state' => $compatible ? 'compatible' : 'incompatible',
            'compatible' => $compatible,
            'verified' => true,
            'reason' => $compatible ? 'Destination meets the minimum supported version.' : sprintf( 'Destination requires version %s or newer.', $minimum ),
        );
    }

    private static function capability( $id, $label, $url, $enabled, $version, $accepts, $returns ) {
        $configured = '1' === (string) $enabled && '' !== trim( (string) $url );
        $minimum = self::minimum_version( $id );
        $compatibility = self::version_compatibility( $version, $minimum, $configured, $url );
        return array(
            'id' => sanitize_key( $id ),
            'label' => sanitize_text_field( $label ),
            'available' => $configured && ! empty( $compatibility['compatible'] ),
            'state' => sanitize_key( $compatibility['state'] ),
            'url' => esc_url_raw( $url ),
            'version' => sanitize_text_field( $version ? $version : 'unknown' ),
            'minimum_version' => $minimum,
            'contract' => self::HANDOFF_SCHEMA,
            'compatibility' => $compatibility,
            'accepts' => array_values( array_map( 'sanitize_key', $accepts ) ),
            'returns' => array_values( array_map( 'sanitize_key', $returns ) ),
        );
    }

    public static function local_capabilities() {
        $o = self::options();
        $capabilities = array(
            'workbench' => self::capability( 'workbench', 'Sustainable Catalyst Workbench', $o['workbench_url'], $o['workbench_enabled'], $o['workbench_version'], array( 'question', 'equations', 'variables', 'units', 'assumptions', 'datasets', 'evidence' ), array( 'calculation_report', 'graph', 'validation_record', 'reproducible_code' ) ),
            'decision_studio' => self::capability( 'decision_studio', 'Sustainable Catalyst Decision Studio', $o['decision_studio_url'], $o['decision_studio_enabled'], $o['decision_studio_version'], array( 'decision_question', 'evidence', 'alternatives', 'criteria', 'assumptions', 'uncertainties' ), array( 'decision_packet', 'scenario_comparison', 'audit_appendix', 'brief' ) ),
            'site_intelligence' => self::capability( 'site_intelligence', 'Sustainable Catalyst Site Intelligence', $o['site_intelligence_url'], $o['site_intelligence_enabled'], $o['site_intelligence_version'], array( 'places', 'countries', 'indicators', 'time_range', 'source_requirements', 'evidence' ), array( 'country_brief', 'indicator_dashboard', 'map_view', 'source_ledger' ) ),
            'lab' => self::capability( 'lab', 'Sustainable Catalyst Lab', $o['lab_url'], $o['lab_enabled'], $o['lab_version'], array( 'research_question', 'hypotheses', 'datasets', 'instrumentation', 'calculations', 'evidence' ), array( 'experiment_record', 'calculation_notebook', 'validation_report', 'reproducibility_bundle' ) ),
            'feature_suggestions' => self::capability( 'feature_suggestions', 'Feature Suggestions', $o['feature_suggestions_url'], $o['feature_suggestions_enabled'], $o['feature_suggestions_version'], array( 'requested_capability', 'workflow_context', 'evidence' ), array( 'suggestion_record' ) ),
        );
        return apply_filters( 'sc_rl_v660_platform_capabilities', $capabilities );
    }

    private static function backend_options() {
        $defaults = array( 'enabled' => '0', 'backend_url' => '', 'backend_api_key' => '', 'request_timeout' => 45 );
        return wp_parse_args( get_option( 'sc_rl_v620_python_options', array() ), $defaults );
    }

    private static function backend_request( $path, $method = 'GET', $payload = null ) {
        $options = self::backend_options();
        if ( '1' !== (string) $options['enabled'] || empty( $options['backend_url'] ) || empty( $options['backend_api_key'] ) ) {
            return new WP_Error( 'sc_rl_v661_backend_disabled', 'The Python backend is not configured.', array( 'status' => 503 ) );
        }
        $platform = self::options();
        $limit = max( 1, min( 5, absint( $platform['retry_limit'] ) ) );
        $args = array(
            'method' => strtoupper( $method ),
            'timeout' => max( 10, min( 120, absint( $options['request_timeout'] ) ) ),
            'redirection' => 3,
            'headers' => array(
                'Accept' => 'application/json',
                'Content-Type' => 'application/json',
                'X-SC-RL-Key' => (string) $options['backend_api_key'],
                'User-Agent' => 'Sustainable-Catalyst-Research-Librarian/' . self::VERSION . '; ' . home_url( '/' ),
            ),
        );
        if ( null !== $payload ) {
            $args['body'] = wp_json_encode( $payload );
        }
        $last_error = null;
        for ( $attempt = 1; $attempt <= $limit; $attempt++ ) {
            $response = wp_remote_request( untrailingslashit( $options['backend_url'] ) . '/' . ltrim( $path, '/' ), $args );
            if ( is_wp_error( $response ) ) {
                $last_error = $response;
                continue;
            }
            $code = wp_remote_retrieve_response_code( $response );
            $body = json_decode( wp_remote_retrieve_body( $response ), true );
            if ( $code >= 200 && $code < 300 && is_array( $body ) ) {
                $body['wordpress_delivery_attempts'] = $attempt;
                return $body;
            }
            $detail = is_array( $body ) && isset( $body['detail'] ) ? $body['detail'] : wp_remote_retrieve_body( $response );
            $message = is_string( $detail ) ? sanitize_text_field( $detail ) : 'The typed-handoff backend request failed.';
            $last_error = new WP_Error( 'sc_rl_v661_backend_failed', $message, array( 'status' => $code ? $code : 502, 'attempt' => $attempt ) );
            if ( ! in_array( (int) $code, array( 408, 425, 429, 500, 502, 503, 504 ), true ) ) {
                break;
            }
        }
        return $last_error instanceof WP_Error ? $last_error : new WP_Error( 'sc_rl_v661_backend_failed', 'The typed-handoff backend request failed.', array( 'status' => 502 ) );
    }

    private static function sanitize_deep( $value, $depth = 0 ) {
        if ( $depth > 8 ) {
            return '[depth-limited]';
        }
        if ( is_bool( $value ) || is_numeric( $value ) || null === $value ) {
            return $value;
        }
        if ( is_array( $value ) ) {
            $clean = array();
            foreach ( $value as $key => $child ) {
                $clean_key = is_int( $key ) ? $key : sanitize_key( $key );
                $clean[ $clean_key ] = self::sanitize_deep( $child, $depth + 1 );
            }
            return $clean;
        }
        return sanitize_textarea_field( (string) $value );
    }

    public static function capabilities() {
        $local = self::local_capabilities();
        $backend = self::backend_request( '/v1/platform/capabilities', 'GET' );
        if ( ! is_wp_error( $backend ) && ! empty( $backend['capabilities'] ) && is_array( $backend['capabilities'] ) ) {
            foreach ( $backend['capabilities'] as $item ) {
                $id = sanitize_key( isset( $item['id'] ) ? $item['id'] : '' );
                if ( $id && isset( $local[ $id ] ) ) {
                    $local[ $id ]['backend_available'] = ! empty( $item['available'] );
                    $local[ $id ]['backend_state'] = sanitize_key( isset( $item['state'] ) ? $item['state'] : '' );
                    $local[ $id ]['backend_version'] = sanitize_text_field( isset( $item['version'] ) ? $item['version'] : '' );
                    $local[ $id ]['backend_compatibility'] = isset( $item['compatibility'] ) && is_array( $item['compatibility'] ) ? self::sanitize_deep( $item['compatibility'] ) : array();
                    $local[ $id ]['available'] = ! empty( $local[ $id ]['available'] ) && ! empty( $item['available'] );
                    if ( ! empty( $item['state'] ) ) {
                        $local[ $id ]['state'] = sanitize_key( $item['state'] );
                    }
                }
            }
        }
        return array_values( $local );
    }

    public static function rest_capabilities() {
        $capabilities = self::capabilities();
        $available = array_values( array_filter( $capabilities, function( $item ) { return ! empty( $item['available'] ); } ) );
        return new WP_REST_Response( array(
            'ok' => true,
            'version' => self::VERSION,
            'schema' => self::CAPABILITIES_SCHEMA,
            'capabilities' => $capabilities,
            'available' => array_values( array_map( function( $item ) { return $item['id']; }, $available ) ),
        ), 200 );
    }

    public static function compatibility_report() {
        $capabilities = self::capabilities();
        $counts = array( 'compatible' => 0, 'unverified' => 0, 'incompatible' => 0, 'disabled' => 0 );
        foreach ( $capabilities as $capability ) {
            $state = isset( $capability['state'] ) ? sanitize_key( $capability['state'] ) : 'unverified';
            if ( isset( $counts[ $state ] ) ) {
                $counts[ $state ]++;
            }
        }
        return array(
            'schema' => self::COMPATIBILITY_SCHEMA,
            'version' => self::VERSION,
            'generated_utc' => gmdate( 'c' ),
            'counts' => $counts,
            'destinations' => $capabilities,
        );
    }

    public static function rest_compatibility() {
        return new WP_REST_Response( array_merge( array( 'ok' => true ), self::compatibility_report() ), 200 );
    }

    private static function token_secret() {
        return defined( 'AUTH_SALT' ) && AUTH_SALT ? AUTH_SALT : 'sc-rl-v661-' . self::VERSION;
    }

    private static function issue_delivery_token( $handoff_id, $destination, $expires_utc ) {
        return hash_hmac( 'sha256', $handoff_id . '|' . $destination . '|' . $expires_utc, self::token_secret() );
    }

    private static function validate_delivery_token( $payload ) {
        $delivery = isset( $payload['delivery'] ) && is_array( $payload['delivery'] ) ? $payload['delivery'] : array();
        $expires = isset( $delivery['token_expires_utc'] ) ? sanitize_text_field( $delivery['token_expires_utc'] ) : '';
        $token = isset( $delivery['token'] ) ? sanitize_text_field( $delivery['token'] ) : '';
        $expected = $expires ? self::issue_delivery_token( isset( $payload['handoff_id'] ) ? $payload['handoff_id'] : '', isset( $payload['destination'] ) ? $payload['destination'] : '', $expires ) : '';
        $expired = ! $expires || strtotime( $expires ) <= time();
        $ok = ! $expired && $token && $expected && hash_equals( $expected, $token );
        return array( 'ok' => $ok, 'expired' => $expired, 'expires_utc' => $expires, 'error' => $ok ? '' : ( $expired ? 'Delivery token expired.' : 'Delivery token is invalid.' ) );
    }

    private static function local_handoff( $params ) {
        $destination = sanitize_key( isset( $params['destination'] ) ? str_replace( '-', '_', $params['destination'] ) : '' );
        $question = sanitize_textarea_field( isset( $params['question'] ) ? $params['question'] : '' );
        $capabilities = self::local_capabilities();
        if ( ! $destination || empty( $capabilities[ $destination ]['available'] ) ) {
            return new WP_Error( 'sc_rl_v660_destination_unavailable', 'The requested destination is not currently available.', array( 'status' => 409 ) );
        }
        $evidence = isset( $params['evidence'] ) && is_array( $params['evidence'] ) ? self::sanitize_deep( array_slice( $params['evidence'], 0, 8 ) ) : array();
        $route = array(
            'schema' => self::ROUTE_SCHEMA,
            'research_mode' => sanitize_key( isset( $params['research_mode'] ) ? $params['research_mode'] : 'auto' ),
            'destination' => $destination,
            'destination_label' => $capabilities[ $destination ]['label'],
            'destination_url' => $capabilities[ $destination ]['url'],
            'destination_version' => $capabilities[ $destination ]['version'],
            'minimum_destination_version' => $capabilities[ $destination ]['minimum_version'],
            'compatibility' => $capabilities[ $destination ]['compatibility'],
            'reason' => 'WordPress prepared a typed handoff while the Python handoff endpoint was unavailable.',
        );
        $handoff_id = 'handoff-wp-' . wp_generate_uuid4();
        $created_utc = gmdate( 'c' );
        $expires_utc = gmdate( 'c', time() + max( 300, absint( self::options()['delivery_ttl_seconds'] ) ) );
        $payload = array(
            'schema' => self::HANDOFF_SCHEMA,
            'handoff_id' => $handoff_id,
            'created_utc' => $created_utc,
            'expires_utc' => $expires_utc,
            'source_system' => 'research_librarian_wordpress',
            'source_version' => self::VERSION,
            'session_id' => sanitize_key( isset( $params['session_id'] ) ? $params['session_id'] : '' ),
            'question' => $question,
            'route' => $route,
            'destination' => $destination,
            'destination_contract' => self::HANDOFF_SCHEMA,
            'status' => 'prepared-local-fallback',
            'evidence' => $evidence,
            'assumptions' => isset( $params['assumptions'] ) && is_array( $params['assumptions'] ) ? self::sanitize_deep( $params['assumptions'] ) : array(),
            'uncertainties' => isset( $params['uncertainties'] ) && is_array( $params['uncertainties'] ) ? self::sanitize_deep( $params['uncertainties'] ) : array(),
            'human_confirmation_required' => true,
            'boundaries' => array( 'This handoff is a reviewable draft.', 'The destination must validate its contract, token, and version before accepting the payload.' ),
            'delivery' => array(
                'schema' => self::DELIVERY_SCHEMA,
                'attempt' => 0,
                'max_attempts' => max( 1, absint( self::options()['retry_limit'] ) ),
                'token_expires_utc' => $expires_utc,
                'token' => self::issue_delivery_token( $handoff_id, $destination, $expires_utc ),
                'last_refresh_utc' => $created_utc,
                'last_refresh_reason' => 'wordpress-local-fallback',
                'next_retry_utc' => '',
            ),
            'idempotency_key' => sanitize_text_field( isset( $params['idempotency_key'] ) ? $params['idempotency_key'] : '' ),
            'payload' => self::destination_body( $destination, $question, $evidence, isset( $params['route_hint'] ) && is_array( $params['route_hint'] ) ? $params['route_hint'] : array() ),
            'provenance' => array(
                'source_record_ids' => array_values( array_filter( array_map( function( $item ) { return isset( $item['record_id'] ) ? sanitize_text_field( $item['record_id'] ) : ''; }, $evidence ) ) ),
                'chain' => array( 'research_question', 'verified_retrieval', 'typed_handoff' ),
                'parent_handoff_id' => '',
            ),
        );
        $fingerprint_payload = $payload;
        $payload['provenance']['payload_fingerprint'] = hash( 'sha256', wp_json_encode( $fingerprint_payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) );
        $payload['validation'] = self::validate_payload( $payload );
        return $payload;
    }

    private static function destination_body( $destination, $question, $evidence, $hint ) {
        if ( 'workbench' === $destination ) {
            return array( 'contract' => 'sc-workbench-task/1.0', 'task_type' => 'analysis', 'equations' => array(), 'variables' => array(), 'units' => array(), 'datasets' => array(), 'requested_outputs' => array( 'calculation_report', 'validation_warnings', 'reproducible_method' ), 'validation_requirements' => array( 'show_inputs', 'show_units', 'show_assumptions', 'show_method' ), 'evidence_context' => $evidence );
        }
        if ( 'decision_studio' === $destination ) {
            return array( 'contract' => 'sc-decision-packet-seed/1.0', 'decision_question' => $question, 'alternatives' => array(), 'criteria' => array(), 'scenarios' => array(), 'evidence_ledger' => $evidence, 'requested_outputs' => array( 'decision_packet', 'assumption_register', 'uncertainty_register', 'audit_appendix' ) );
        }
        if ( 'site_intelligence' === $destination ) {
            return array( 'contract' => 'sc-site-intelligence-query/1.0', 'places' => array(), 'countries' => array(), 'indicators' => array(), 'time_range' => array(), 'source_requirements' => array( 'public', 'attributable', 'freshness_visible', 'methodology_visible' ), 'requested_outputs' => array( 'source_aware_brief', 'indicator_view', 'map_view' ), 'evidence_context' => $evidence );
        }
        if ( 'lab' === $destination ) {
            return array( 'contract' => 'sc-lab-workflow/1.0', 'research_question' => $question, 'domain' => 'auto-detect', 'hypotheses' => array(), 'experiment_type' => 'analysis-or-simulation', 'datasets' => array(), 'instrumentation' => array(), 'calculations' => array(), 'requested_outputs' => array( 'experiment_record', 'validation_report', 'reproducibility_bundle' ), 'evidence_context' => $evidence );
        }
        return array( 'contract' => 'sc-feature-suggestion/1.0', 'requested_capability' => $question, 'workflow_context' => self::sanitize_deep( $hint ), 'evidence_context' => $evidence, 'requested_outputs' => array( 'suggestion_record' ) );
    }

    public static function validate_payload( $payload ) {
        $errors = array();
        foreach ( array( 'schema', 'handoff_id', 'created_utc', 'source_system', 'source_version', 'question', 'route', 'destination', 'payload', 'provenance', 'delivery' ) as $field ) {
            if ( ! isset( $payload[ $field ] ) || '' === $payload[ $field ] || array() === $payload[ $field ] ) {
                $errors[] = 'Missing required field: ' . $field;
            }
        }
        if ( isset( $payload['schema'] ) && self::HANDOFF_SCHEMA !== $payload['schema'] ) {
            $errors[] = 'Unsupported handoff schema.';
        }
        if ( empty( $payload['route']['schema'] ) || self::ROUTE_SCHEMA !== $payload['route']['schema'] ) {
            $errors[] = 'Route schema is missing or unsupported.';
        }
        if ( empty( $payload['payload']['contract'] ) ) {
            $errors[] = 'Destination payload contract is missing.';
        }
        $expected_fingerprint = isset( $payload['provenance']['payload_fingerprint'] ) ? sanitize_text_field( $payload['provenance']['payload_fingerprint'] ) : '';
        if ( $expected_fingerprint ) {
            $fingerprint_payload = $payload;
            unset( $fingerprint_payload['validation'] );
            unset( $fingerprint_payload['provenance']['payload_fingerprint'] );
            $actual_fingerprint = hash( 'sha256', wp_json_encode( $fingerprint_payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) );
            if ( ! hash_equals( $expected_fingerprint, $actual_fingerprint ) ) {
                $errors[] = 'Payload fingerprint does not match the handoff contents.';
            }
        }
        $token_validation = self::validate_delivery_token( $payload );
        if ( empty( $token_validation['ok'] ) ) {
            $errors[] = $token_validation['error'];
        }
        return array( 'ok' => empty( $errors ), 'schema' => self::HANDOFF_SCHEMA, 'destination' => sanitize_key( isset( $payload['destination'] ) ? $payload['destination'] : '' ), 'compatibility' => isset( $payload['route']['compatibility'] ) ? $payload['route']['compatibility'] : array(), 'token' => $token_validation, 'errors' => $errors, 'warnings' => empty( $payload['evidence'] ) ? array( 'No verified source records are attached to this handoff.' ) : array() );
    }

    private static function event_key( $type, $key ) {
        return $key ? 'sc_rl_v661_event_' . md5( sanitize_key( $type ) . ':' . sanitize_text_field( $key ) ) : '';
    }

    private static function event_hash( $payload ) {
        if ( is_array( $payload ) ) {
            unset( $payload['idempotency_key'], $payload['created_utc'] );
        }
        return hash( 'sha256', wp_json_encode( $payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) );
    }

    private static function event_get( $type, $key, $payload ) {
        $transient_key = self::event_key( $type, $key );
        if ( ! $transient_key || ! function_exists( 'get_transient' ) ) {
            return false;
        }
        $event = get_transient( $transient_key );
        if ( ! is_array( $event ) ) {
            return false;
        }
        if ( ! hash_equals( isset( $event['payload_hash'] ) ? $event['payload_hash'] : '', self::event_hash( $payload ) ) ) {
            return new WP_Error( 'sc_rl_v661_idempotency_conflict', 'The idempotency key was already used with a different payload.', array( 'status' => 409 ) );
        }
        return isset( $event['response'] ) ? $event['response'] : false;
    }

    private static function event_set( $type, $key, $payload, $response ) {
        $transient_key = self::event_key( $type, $key );
        if ( ! $transient_key || ! function_exists( 'set_transient' ) ) {
            return;
        }
        $ttl = max( 300, min( 604800, absint( self::options()['event_ttl_seconds'] ) ) );
        set_transient( $transient_key, array( 'payload_hash' => self::event_hash( $payload ), 'response' => $response ), $ttl );
    }

    public static function rest_prepare( WP_REST_Request $request ) {
        $verified = self::require_nonce( $request );
        if ( is_wp_error( $verified ) ) {
            return $verified;
        }
        $params = $request->get_json_params();
        $question = sanitize_textarea_field( isset( $params['question'] ) ? $params['question'] : '' );
        if ( strlen( trim( $question ) ) < 3 ) {
            return new WP_Error( 'sc_rl_v661_empty_question', 'Enter a research question before preparing a handoff.', array( 'status' => 400 ) );
        }
        $idempotency_key = sanitize_text_field( isset( $params['idempotency_key'] ) ? $params['idempotency_key'] : '' );
        $event = self::event_get( 'handoff-prepare', $idempotency_key, $params );
        if ( is_wp_error( $event ) ) {
            return $event;
        }
        if ( is_array( $event ) ) {
            $event['duplicate_event'] = true;
            return new WP_REST_Response( self::sanitize_deep( $event ), 200 );
        }
        $backend_payload = array(
            'destination' => sanitize_key( isset( $params['destination'] ) ? str_replace( '-', '_', $params['destination'] ) : '' ),
            'question' => $question,
            'research_mode' => sanitize_key( isset( $params['research_mode'] ) ? $params['research_mode'] : 'auto' ),
            'session_id' => sanitize_key( isset( $params['session_id'] ) ? $params['session_id'] : '' ),
            'route_hint' => isset( $params['route_hint'] ) && is_array( $params['route_hint'] ) ? self::sanitize_deep( $params['route_hint'] ) : array(),
            'assumptions' => isset( $params['assumptions'] ) && is_array( $params['assumptions'] ) ? array_values( array_map( 'sanitize_textarea_field', $params['assumptions'] ) ) : array(),
            'uncertainties' => isset( $params['uncertainties'] ) && is_array( $params['uncertainties'] ) ? array_values( array_map( 'sanitize_textarea_field', $params['uncertainties'] ) ) : array(),
            'source_ids' => isset( $params['source_ids'] ) && is_array( $params['source_ids'] ) ? array_values( array_map( 'sanitize_text_field', $params['source_ids'] ) ) : array(),
            'persist' => true,
            'idempotency_key' => $idempotency_key,
        );
        $result = self::backend_request( '/v1/handoffs/prepare', 'POST', $backend_payload );
        if ( is_wp_error( $result ) ) {
            $params['question'] = $question;
            $params['idempotency_key'] = $idempotency_key;
            $handoff = self::local_handoff( $params );
            if ( is_wp_error( $handoff ) ) {
                return $handoff;
            }
            $result = array( 'ok' => true, 'version' => self::VERSION, 'handoff' => $handoff, 'fallback' => true, 'backend_error' => $result->get_error_message(), 'duplicate_event' => false );
        }
        self::append_log( isset( $result['handoff'] ) && is_array( $result['handoff'] ) ? $result['handoff'] : array() );
        self::event_set( 'handoff-prepare', $idempotency_key, $params, $result );
        return new WP_REST_Response( self::sanitize_deep( $result ), 200 );
    }

    public static function rest_validate( WP_REST_Request $request ) {
        $verified = self::require_nonce( $request );
        if ( is_wp_error( $verified ) ) {
            return $verified;
        }
        $params = $request->get_json_params();
        $payload = isset( $params['payload'] ) && is_array( $params['payload'] ) ? $params['payload'] : array();
        $backend = self::backend_request( '/v1/handoffs/validate', 'POST', array( 'payload' => $payload ) );
        $validation = is_wp_error( $backend ) ? self::validate_payload( $payload ) : $backend;
        return new WP_REST_Response( self::sanitize_deep( $validation ), ! empty( $validation['ok'] ) ? 200 : 409 );
    }

    public static function rest_retry( WP_REST_Request $request ) {
        $verified = self::require_nonce( $request );
        if ( is_wp_error( $verified ) ) {
            return $verified;
        }
        $params = self::sanitize_deep( $request->get_json_params() );
        if ( empty( $params['handoff_id'] ) ) {
            return new WP_Error( 'sc_rl_v661_missing_handoff', 'A handoff ID is required.', array( 'status' => 400 ) );
        }
        $payload = array(
            'handoff_id' => sanitize_text_field( $params['handoff_id'] ),
            'reason' => sanitize_text_field( isset( $params['reason'] ) ? $params['reason'] : 'wordpress-delivery-retry' ),
            'idempotency_key' => sanitize_text_field( isset( $params['idempotency_key'] ) ? $params['idempotency_key'] : '' ),
        );
        $result = self::backend_request( '/v1/handoffs/retry', 'POST', $payload );
        return is_wp_error( $result ) ? $result : new WP_REST_Response( self::sanitize_deep( $result ), 200 );
    }

    public static function rest_token_refresh( WP_REST_Request $request ) {
        $verified = self::require_nonce( $request );
        if ( is_wp_error( $verified ) ) {
            return $verified;
        }
        $params = self::sanitize_deep( $request->get_json_params() );
        if ( empty( $params['handoff_id'] ) ) {
            return new WP_Error( 'sc_rl_v661_missing_handoff', 'A handoff ID is required.', array( 'status' => 400 ) );
        }
        $result = self::backend_request( '/v1/handoffs/token/refresh', 'POST', array(
            'handoff_id' => sanitize_text_field( $params['handoff_id'] ),
            'reason' => sanitize_text_field( isset( $params['reason'] ) ? $params['reason'] : 'wordpress-token-refresh' ),
        ) );
        return is_wp_error( $result ) ? $result : new WP_REST_Response( self::sanitize_deep( $result ), 200 );
    }

    public static function rest_receipt( WP_REST_Request $request ) {
        $verified = self::require_nonce( $request );
        if ( is_wp_error( $verified ) ) {
            return $verified;
        }
        $params = self::sanitize_deep( $request->get_json_params() );
        foreach ( array( 'receipt_id', 'handoff_id', 'destination', 'status' ) as $field ) {
            if ( empty( $params[ $field ] ) ) {
                return new WP_Error( 'sc_rl_v661_invalid_receipt', 'Receipt ID, handoff ID, destination, and status are required.', array( 'status' => 400 ) );
            }
        }
        $params['schema'] = self::RECEIPT_SCHEMA;
        $params['created_utc'] = isset( $params['created_utc'] ) ? $params['created_utc'] : gmdate( 'c' );
        $params['idempotency_key'] = isset( $params['idempotency_key'] ) ? $params['idempotency_key'] : $params['receipt_id'];
        $result = self::backend_request( '/v1/handoffs/receipts', 'POST', $params );
        return is_wp_error( $result ) ? $result : new WP_REST_Response( self::sanitize_deep( $result ), 200 );
    }

    public static function rest_artifact_return( WP_REST_Request $request ) {
        $verified = self::require_nonce( $request );
        if ( is_wp_error( $verified ) ) {
            return $verified;
        }
        $params = self::sanitize_deep( $request->get_json_params() );
        if ( empty( $params['artifact_id'] ) || empty( $params['handoff_id'] ) || empty( $params['destination'] ) || empty( $params['artifact_type'] ) ) {
            return new WP_Error( 'sc_rl_v661_invalid_artifact', 'Artifact ID, handoff ID, destination, and artifact type are required.', array( 'status' => 400 ) );
        }
        $params['schema'] = self::ARTIFACT_SCHEMA;
        $params['created_utc'] = isset( $params['created_utc'] ) ? $params['created_utc'] : gmdate( 'c' );
        $params['idempotency_key'] = isset( $params['idempotency_key'] ) ? $params['idempotency_key'] : $params['artifact_id'];
        $artifact_json = wp_json_encode( isset( $params['artifact'] ) ? $params['artifact'] : array(), JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
        if ( strlen( $artifact_json ) > max( 1024, absint( self::options()['max_artifact_bytes'] ) ) ) {
            return new WP_Error( 'sc_rl_v661_artifact_too_large', 'The returned artifact exceeds the configured size limit.', array( 'status' => 413 ) );
        }
        $artifact_fingerprint = hash( 'sha256', wp_json_encode( array(
            'handoff_id' => $params['handoff_id'],
            'destination' => $params['destination'],
            'artifact_type' => $params['artifact_type'],
            'artifact' => isset( $params['artifact'] ) ? $params['artifact'] : array(),
        ), JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) );
        if ( ! isset( $params['provenance'] ) || ! is_array( $params['provenance'] ) ) {
            $params['provenance'] = array();
        }
        $params['provenance']['artifact_fingerprint'] = $artifact_fingerprint;
        $returns = get_option( self::ARTIFACT_OPTION, array() );
        $returns = is_array( $returns ) ? $returns : array();
        foreach ( $returns as $existing ) {
            if ( isset( $existing['artifact_id'] ) && $existing['artifact_id'] === $params['artifact_id'] ) {
                if ( isset( $existing['artifact_fingerprint'] ) && hash_equals( $existing['artifact_fingerprint'], $artifact_fingerprint ) ) {
                    return new WP_REST_Response( array( 'ok' => true, 'version' => self::VERSION, 'duplicate_event' => true, 'artifact' => $existing ), 200 );
                }
                return new WP_Error( 'sc_rl_v661_artifact_conflict', 'Artifact ID is immutable and already exists with different contents.', array( 'status' => 409 ) );
            }
        }
        $result = self::backend_request( '/v1/handoffs/artifacts/return', 'POST', $params );
        if ( is_wp_error( $result ) ) {
            return $result;
        }
        array_unshift( $returns, array(
            'artifact_id' => $params['artifact_id'],
            'handoff_id' => $params['handoff_id'],
            'destination' => $params['destination'],
            'artifact_type' => $params['artifact_type'],
            'artifact_fingerprint' => $artifact_fingerprint,
            'created_utc' => $params['created_utc'],
        ) );
        update_option( self::ARTIFACT_OPTION, array_slice( $returns, 0, 100 ), false );
        return new WP_REST_Response( self::sanitize_deep( $result ), 200 );
    }

    private static function append_log( $handoff ) {
        if ( empty( $handoff['handoff_id'] ) ) {
            return;
        }
        $logs = get_option( self::LOG_OPTION, array() );
        $logs = is_array( $logs ) ? $logs : array();
        array_unshift( $logs, array(
            'handoff_id' => sanitize_text_field( $handoff['handoff_id'] ),
            'created_utc' => sanitize_text_field( isset( $handoff['created_utc'] ) ? $handoff['created_utc'] : gmdate( 'c' ) ),
            'destination' => sanitize_key( isset( $handoff['destination'] ) ? $handoff['destination'] : '' ),
            'status' => sanitize_key( isset( $handoff['status'] ) ? $handoff['status'] : 'prepared' ),
            'source_count' => isset( $handoff['evidence'] ) && is_array( $handoff['evidence'] ) ? count( $handoff['evidence'] ) : 0,
            'fingerprint' => sanitize_text_field( isset( $handoff['provenance']['payload_fingerprint'] ) ? $handoff['provenance']['payload_fingerprint'] : '' ),
        ) );
        $limit = max( 10, min( 500, absint( self::options()['log_limit'] ) ) );
        update_option( self::LOG_OPTION, array_slice( $logs, 0, $limit ), false );
        update_option( self::STATUS_OPTION, array( 'last_handoff_id' => $handoff['handoff_id'], 'last_destination' => $handoff['destination'], 'last_handoff_utc' => $handoff['created_utc'] ), false );
    }

    public static function rest_export() {
        return new WP_REST_Response( array(
            'version' => self::VERSION,
            'generated_utc' => gmdate( 'c' ),
            'schemas' => array( 'handoff' => self::HANDOFF_SCHEMA, 'route' => self::ROUTE_SCHEMA, 'artifact_return' => self::ARTIFACT_SCHEMA, 'delivery' => self::DELIVERY_SCHEMA, 'receipt' => self::RECEIPT_SCHEMA, 'compatibility' => self::COMPATIBILITY_SCHEMA ),
            'capabilities' => self::capabilities(),
            'compatibility' => self::compatibility_report(),
            'status' => get_option( self::STATUS_OPTION, array() ),
            'handoffs' => get_option( self::LOG_OPTION, array() ),
            'artifact_returns' => get_option( self::ARTIFACT_OPTION, array() ),
            'boundary' => 'Admin export excludes backend keys and full artifact contents.',
        ), 200 );
    }

    public static function register_admin_menu() {
        add_options_page( 'Research Librarian Platform Handoffs', 'Research Librarian Handoffs', 'manage_options', 'sc-rl-platform-handoffs', array( __CLASS__, 'render_admin_page' ) );
    }

    public static function render_admin_page() {
        if ( ! current_user_can( 'manage_options' ) ) {
            return;
        }
        if ( isset( $_POST['sc_rl_v660_save'] ) && check_admin_referer( 'sc_rl_v660_save_action' ) ) {
            $old = self::options();
            $new = $old;
            foreach ( array( 'workbench', 'decision_studio', 'site_intelligence', 'lab', 'feature_suggestions' ) as $id ) {
                $new[ $id . '_enabled' ] = isset( $_POST[ $id . '_enabled' ] ) ? '1' : '0';
                $new[ $id . '_url' ] = isset( $_POST[ $id . '_url' ] ) ? esc_url_raw( wp_unslash( $_POST[ $id . '_url' ] ) ) : $old[ $id . '_url' ];
                $new[ $id . '_version' ] = isset( $_POST[ $id . '_version' ] ) ? sanitize_text_field( wp_unslash( $_POST[ $id . '_version' ] ) ) : $old[ $id . '_version' ];
            }
            update_option( self::OPTION_NAME, $new, false );
            echo '<div class="notice notice-success"><p>Platform capability settings saved.</p></div>';
        }
        $options = self::options();
        $capabilities = self::capabilities();
        $logs = get_option( self::LOG_OPTION, array() );
        ?>
        <div class="wrap">
            <h1>Research Librarian Platform Intelligence</h1>
            <p>v7.1.2 preserves versioned research handoffs with compatibility checks, bounded retries, token recovery, idempotency, receipts, and immutable artifact returns for Workbench, Decision Studio, Site Intelligence, Lab, and Feature Suggestions. Disabling a destination removes it from public actions and handoff preparation.</p>
            <form method="post">
                <?php wp_nonce_field( 'sc_rl_v660_save_action' ); ?>
                <table class="widefat striped"><thead><tr><th>Destination</th><th>Available</th><th>URL</th><th>Version</th><th>Minimum</th><th>Compatibility</th><th>Contract</th></tr></thead><tbody>
                <?php foreach ( $capabilities as $capability ) : $id = $capability['id']; ?>
                    <tr>
                        <td><strong><?php echo esc_html( $capability['label'] ); ?></strong></td>
                        <td><label><input type="checkbox" name="<?php echo esc_attr( $id . '_enabled' ); ?>" value="1" <?php checked( '1', $options[ $id . '_enabled' ] ); ?>> Enabled</label><br><small><?php echo esc_html( $capability['state'] ); ?></small></td>
                        <td><input class="large-text" type="url" name="<?php echo esc_attr( $id . '_url' ); ?>" value="<?php echo esc_attr( $options[ $id . '_url' ] ); ?>"></td>
                        <td><input type="text" name="<?php echo esc_attr( $id . '_version' ); ?>" value="<?php echo esc_attr( $options[ $id . '_version' ] ); ?>"></td>
                        <td><code><?php echo esc_html( $capability['minimum_version'] ); ?></code></td>
                        <td><?php echo esc_html( $capability['state'] ); ?><br><small><?php echo esc_html( isset( $capability['compatibility']['reason'] ) ? $capability['compatibility']['reason'] : '' ); ?></small></td>
                        <td><code><?php echo esc_html( self::HANDOFF_SCHEMA ); ?></code></td>
                    </tr>
                <?php endforeach; ?>
                </tbody></table>
                <p><button class="button button-primary" type="submit" name="sc_rl_v660_save" value="1">Save capabilities</button> <a class="button" href="<?php echo esc_url( rest_url( self::REST_NAMESPACE . '/platform/handoffs/export' ) ); ?>">Export handoff audit</a></p>
            </form>
            <h2>Recent handoffs</h2>
            <table class="widefat striped"><thead><tr><th>Created</th><th>Destination</th><th>Status</th><th>Sources</th><th>Handoff ID</th></tr></thead><tbody>
            <?php foreach ( array_slice( is_array( $logs ) ? $logs : array(), 0, 20 ) as $row ) : ?>
                <tr><td><?php echo esc_html( isset( $row['created_utc'] ) ? $row['created_utc'] : '' ); ?></td><td><?php echo esc_html( isset( $row['destination'] ) ? $row['destination'] : '' ); ?></td><td><?php echo esc_html( isset( $row['status'] ) ? $row['status'] : '' ); ?></td><td><?php echo esc_html( absint( isset( $row['source_count'] ) ? $row['source_count'] : 0 ) ); ?></td><td><code><?php echo esc_html( isset( $row['handoff_id'] ) ? $row['handoff_id'] : '' ); ?></code></td></tr>
            <?php endforeach; ?>
            </tbody></table>
        </div>
        <?php
    }

    public static function render_summary( $atts = array() ) {
        $atts = shortcode_atts( array( 'title' => 'Connected Research Handoffs' ), $atts, 'sc_research_librarian_platform_handoffs' );
        $capabilities = self::capabilities();
        ob_start();
        ?>
        <section class="sc-rl-product sc-rl-platform-handoff-summary" data-sc-rl-product="platform-handoffs">
            <p class="sc-rl-product__eyebrow">Connected Platform</p>
            <h2><?php echo esc_html( $atts['title'] ); ?></h2>
            <p class="sc-rl-product__lede">Research Librarian can prepare reviewable, versioned payloads for connected Sustainable Catalyst tools while preserving verified sources, assumptions, uncertainty, and provenance.</p>
            <div class="sc-rl-product__grid">
                <?php foreach ( $capabilities as $capability ) : if ( empty( $capability['available'] ) ) { continue; } ?>
                    <article><span><?php echo esc_html( $capability['version'] ); ?></span><strong><?php echo esc_html( $capability['label'] ); ?></strong><p>Accepts <?php echo esc_html( implode( ', ', array_slice( $capability['accepts'], 0, 4 ) ) ); ?> and returns traceable research artifacts.</p><a href="<?php echo esc_url( $capability['url'] ); ?>">Open destination →</a></article>
                <?php endforeach; ?>
            </div>
        </section>
        <?php
        return ob_get_clean();
    }
}
