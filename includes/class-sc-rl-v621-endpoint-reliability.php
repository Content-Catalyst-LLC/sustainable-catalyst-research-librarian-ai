<?php
/**
 * Research Librarian AI v6.2.1 — WordPress indexing and endpoint reliability patch.
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class SC_RL6_V621_Endpoint_Reliability {
    const VERSION = '6.2.1';
    const OPTION_NAME = 'sc_rl_v620_python_options';
    const STATUS_OPTION = 'sc_rl_v620_python_status';
    const SYNC_HOOK = 'sc_rl_v620_python_sync_event';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';
    const SYNC_REPORT_OPTION = 'sc_rl_v621_sync_report';
    const SYNC_HISTORY_OPTION = 'sc_rl_v621_sync_history';

    public static function init() {
        add_action( 'admin_menu', array( __CLASS__, 'register_admin_menu' ), 1010 );
        add_action( 'rest_api_init', array( __CLASS__, 'register_rest_routes' ), 110 );
        add_action( self::SYNC_HOOK, array( __CLASS__, 'run_scheduled_sync' ) );
        add_action( 'save_post', array( __CLASS__, 'schedule_incremental_sync' ), 30, 3 );
        add_action( 'deleted_post', array( __CLASS__, 'schedule_sync_after_delete' ), 30, 1 );
        add_action( 'transition_post_status', array( __CLASS__, 'schedule_transition_sync' ), 30, 3 );
        add_filter( 'cron_schedules', array( __CLASS__, 'cron_schedules' ) );
    }

    public static function activate() {
        $existing = get_option( self::OPTION_NAME, array() );
        update_option( self::OPTION_NAME, wp_parse_args( $existing, self::defaults() ), false );
        self::sync_cron();
    }

    public static function deactivate() {
        wp_clear_scheduled_hook( self::SYNC_HOOK );
    }

    public static function defaults() {
        return array(
            'enabled' => '0',
            'backend_url' => '',
            'backend_api_key' => '',
            'request_timeout' => 45,
            'sync_batch_size' => 100,
            'max_records' => 5000,
            'auto_sync' => '1',
            'sync_frequency' => 'twicedaily',
            'include_content' => '1',
            'content_character_limit' => 30000,
            'public_title_suggestions' => '1',
        );
    }

    public static function options() {
        return wp_parse_args( get_option( self::OPTION_NAME, array() ), self::defaults() );
    }

    public static function enabled() {
        $options = self::options();
        return '1' === (string) $options['enabled'] && ! empty( $options['backend_url'] ) && ! empty( $options['backend_api_key'] );
    }

    public static function cron_schedules( $schedules ) {
        if ( ! isset( $schedules['sc_rl_six_hourly'] ) ) {
            $schedules['sc_rl_six_hourly'] = array(
                'interval' => 6 * HOUR_IN_SECONDS,
                'display' => 'Every six hours',
            );
        }
        return $schedules;
    }

    private static function sync_cron() {
        $options = self::options();
        wp_clear_scheduled_hook( self::SYNC_HOOK );
        if ( '1' !== (string) $options['auto_sync'] ) {
            return;
        }
        $frequency = in_array( $options['sync_frequency'], array( 'hourly', 'sc_rl_six_hourly', 'twicedaily', 'daily' ), true ) ? $options['sync_frequency'] : 'twicedaily';
        if ( ! wp_next_scheduled( self::SYNC_HOOK ) ) {
            wp_schedule_event( time() + 15 * MINUTE_IN_SECONDS, $frequency, self::SYNC_HOOK );
        }
    }

    public static function schedule_incremental_sync( $post_id, $post, $update ) {
        if ( wp_is_post_revision( $post_id ) || wp_is_post_autosave( $post_id ) || ! self::enabled() ) {
            return;
        }
        if ( ! is_object( $post ) || 'publish' !== $post->post_status ) {
            return;
        }
        if ( ! self::is_public_post_type( $post->post_type ) ) {
            return;
        }
        self::schedule_single_sync();
    }

    public static function schedule_transition_sync( $new_status, $old_status, $post ) {
        if ( $new_status === $old_status || ! self::enabled() || ! is_object( $post ) || ! self::is_public_post_type( $post->post_type ) ) {
            return;
        }
        if ( 'publish' === $new_status || 'publish' === $old_status ) {
            self::schedule_single_sync();
        }
    }

    public static function schedule_sync_after_delete( $post_id ) {
        if ( self::enabled() ) {
            self::schedule_single_sync();
        }
    }

    private static function schedule_single_sync() {
        if ( ! wp_next_scheduled( self::SYNC_HOOK ) ) {
            wp_schedule_single_event( time() + 5 * MINUTE_IN_SECONDS, self::SYNC_HOOK );
        }
    }

    public static function run_scheduled_sync() {
        if ( self::enabled() ) {
            self::sync_all_records();
        }
        self::sync_cron();
    }

    public static function register_admin_menu() {
        add_submenu_page(
            'sc-research-librarian-ai',
            'Python Intelligence',
            'Python Intelligence',
            'manage_options',
            'sc-rl-python-intelligence',
            array( __CLASS__, 'render_admin_page' )
        );
    }

    public static function register_rest_routes() {
        register_rest_route( self::REST_NAMESPACE, '/python/status', array(
            'methods' => WP_REST_Server::READABLE,
            'callback' => array( __CLASS__, 'handle_public_status' ),
            'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/python/suggest', array(
            'methods' => WP_REST_Server::CREATABLE,
            'callback' => array( __CLASS__, 'handle_suggestions' ),
            'permission_callback' => '__return_true',
            'args' => array( 'query' => array( 'required' => true, 'type' => 'string', 'sanitize_callback' => 'sanitize_text_field' ) ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/python/diagnostics', array(
            'methods' => WP_REST_Server::READABLE,
            'callback' => array( __CLASS__, 'handle_diagnostics' ),
            'permission_callback' => array( __CLASS__, 'can_manage' ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/python/sync-report', array(
            'methods' => WP_REST_Server::READABLE,
            'callback' => array( __CLASS__, 'handle_sync_report' ),
            'permission_callback' => array( __CLASS__, 'can_manage' ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/python/sync', array(
            'methods' => WP_REST_Server::CREATABLE,
            'callback' => array( __CLASS__, 'handle_admin_sync' ),
            'permission_callback' => array( __CLASS__, 'can_manage' ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/python/repair', array(
            'methods' => WP_REST_Server::CREATABLE,
            'callback' => array( __CLASS__, 'handle_admin_repair' ),
            'permission_callback' => array( __CLASS__, 'can_manage' ),
        ) );
    }

    public static function can_manage() {
        return current_user_can( 'manage_options' );
    }

    public static function handle_public_status() {
        $status = self::backend_status( false );
        if ( is_wp_error( $status ) ) {
            $error = self::public_error_snapshot( $status );
            return new WP_REST_Response( array(
                'version' => self::VERSION,
                'enabled' => self::enabled(),
                'state' => $error['state'],
                'label' => $error['label'],
                'detail' => $error['message'],
                'error_type' => $error['error_type'],
                'indexed_records' => 0,
                'indexed_titles' => 0,
                'fallback_active' => true,
            ), 200 );
        }
        unset( $status['last_ai_error'] );
        $status['enabled'] = self::enabled();
        $status['fallback_active'] = true;
        return new WP_REST_Response( $status, 200 );
    }

    public static function handle_diagnostics() {
        return new WP_REST_Response( self::diagnostics_snapshot(), 200 );
    }

    public static function handle_sync_report() {
        return new WP_REST_Response( array(
            'version' => self::VERSION,
            'report' => self::latest_sync_report(),
            'history' => self::sync_history(),
        ), 200 );
    }

    public static function handle_suggestions( WP_REST_Request $request ) {
        if ( ! self::enabled() ) {
            return new WP_REST_Response( array( 'suggestions' => array() ), 200 );
        }
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_v621_bad_nonce', 'Security check failed.', array( 'status' => 403 ) );
        }
        $query = sanitize_text_field( $request->get_param( 'query' ) );
        if ( strlen( $query ) < 2 ) {
            return new WP_REST_Response( array( 'suggestions' => array() ), 200 );
        }
        $response = self::request( '/v1/retrieve', 'POST', array( 'query' => $query, 'limit' => 8 ) );
        if ( is_wp_error( $response ) ) {
            return new WP_REST_Response( array( 'suggestions' => array() ), 200 );
        }
        $suggestions = array();
        foreach ( is_array( $response ) ? $response : array() as $item ) {
            if ( empty( $item['title'] ) || empty( $item['url'] ) ) {
                continue;
            }
            $suggestions[] = array(
                'title' => sanitize_text_field( $item['title'] ),
                'url' => esc_url_raw( $item['url'] ),
                'summary' => sanitize_textarea_field( isset( $item['summary'] ) ? $item['summary'] : '' ),
                'match_type' => sanitize_key( isset( $item['match_type'] ) ? $item['match_type'] : '' ),
            );
        }
        return new WP_REST_Response( array( 'suggestions' => $suggestions ), 200 );
    }

    public static function handle_admin_sync() {
        $result = self::sync_all_records();
        if ( is_wp_error( $result ) ) {
            return $result;
        }
        return new WP_REST_Response( $result, 200 );
    }


    public static function handle_admin_repair() {
        $result = self::repair_and_resync();
        if ( is_wp_error( $result ) ) {
            return $result;
        }
        return new WP_REST_Response( $result, 200 );
    }

    public static function repair_and_resync() {
        self::sync_cron();
        $health = self::test_backend();
        if ( is_wp_error( $health ) ) {
            return new WP_Error(
                $health->get_error_code(),
                $health->get_error_message(),
                array_merge( (array) $health->get_error_data(), array( 'repair_stage' => 'backend-test' ) )
            );
        }
        $sync = self::sync_all_records();
        if ( is_wp_error( $sync ) ) {
            return new WP_Error(
                $sync->get_error_code(),
                $sync->get_error_message(),
                array_merge( (array) $sync->get_error_data(), array( 'repair_stage' => 'knowledge-sync' ) )
            );
        }
        return array(
            'version' => self::VERSION,
            'ok' => true,
            'message' => 'Endpoint verification, WP-Cron scheduling, and full knowledge synchronization completed.',
            'health' => $health,
            'sync' => $sync,
            'diagnostics' => self::diagnostics_snapshot(),
            'repaired_utc' => gmdate( 'c' ),
        );
    }

    public static function ask( $question, $route_hint = array(), $wordpress_status = array(), $session_id = '' ) {
        if ( ! self::enabled() ) {
            return new WP_Error( 'sc_rl_v621_disabled', 'The Python intelligence backend is not enabled.' );
        }
        $payload = array(
            'question' => sanitize_textarea_field( $question ),
            'session_id' => sanitize_key( $session_id ),
            'page_url' => isset( $_SERVER['HTTP_REFERER'] ) ? esc_url_raw( wp_unslash( $_SERVER['HTTP_REFERER'] ) ) : '',
            'route_hint' => is_array( $route_hint ) ? $route_hint : array(),
            'wordpress_status' => is_array( $wordpress_status ) ? $wordpress_status : array(),
        );
        return self::request( '/v1/ask', 'POST', $payload );
    }

    public static function normalize_ask_response( $backend, $question, $fallback_route, $fallback_grounding ) {
        if ( ! is_array( $backend ) || empty( $backend['answer'] ) ) {
            return new WP_Error( 'sc_rl_v621_invalid_response', 'The Python backend returned an invalid answer.' );
        }
        $matches = isset( $backend['matches'] ) && is_array( $backend['matches'] ) ? $backend['matches'] : array();
        $best = isset( $backend['best_match'] ) && is_array( $backend['best_match'] ) ? $backend['best_match'] : ( $matches ? $matches[0] : array() );
        $route = $fallback_route;
        if ( ! empty( $best['title'] ) && ! empty( $best['url'] ) ) {
            $route = array(
                'id' => ! empty( $best['route_id'] ) ? sanitize_key( $best['route_id'] ) : 'knowledge-title',
                'route_id' => ! empty( $best['route_id'] ) ? sanitize_key( $best['route_id'] ) : 'knowledge-title',
                'title' => sanitize_text_field( $best['title'] ),
                'url' => esc_url_raw( $best['url'] ),
                'category' => ! empty( $best['series'] ) ? sanitize_text_field( $best['series'] ) : 'Knowledge Library',
                'description' => sanitize_textarea_field( isset( $best['summary'] ) ? $best['summary'] : 'Strongest title-aware match in the Sustainable Catalyst knowledge index.' ),
                'why' => 'The Python knowledge service ranked this as the strongest title-aware Sustainable Catalyst match.',
                'platform_fit' => ! empty( $best['article_map'] ) ? 'This title is connected to the article map: ' . sanitize_text_field( $best['article_map'] ) . '.' : 'This title is indexed as a public Sustainable Catalyst knowledge record.',
                'next_step' => 'Open the best match, review the related titles, and ask a follow-up question when needed.',
            );
        }
        $sources = array();
        foreach ( array_slice( $matches, 0, 10 ) as $item ) {
            if ( empty( $item['title'] ) || empty( $item['url'] ) ) {
                continue;
            }
            $sources[] = array(
                'id' => sanitize_text_field( isset( $item['id'] ) ? $item['id'] : '' ),
                'title' => sanitize_text_field( $item['title'] ),
                'url' => esc_url_raw( $item['url'] ),
                'summary' => sanitize_textarea_field( isset( $item['summary'] ) ? $item['summary'] : '' ),
                'type' => sanitize_key( isset( $item['post_type'] ) ? $item['post_type'] : 'source' ),
                'route_id' => sanitize_key( isset( $item['route_id'] ) ? $item['route_id'] : '' ),
                'score' => isset( $item['score'] ) ? round( (float) $item['score'], 2 ) : 0,
                'final_score' => isset( $item['score'] ) ? round( (float) $item['score'], 2 ) : 0,
                'retrieval_mode' => sanitize_key( isset( $item['match_type'] ) ? $item['match_type'] : 'python-hybrid' ),
                'series' => sanitize_text_field( isset( $item['series'] ) ? $item['series'] : '' ),
                'article_map' => sanitize_text_field( isset( $item['article_map'] ) ? $item['article_map'] : '' ),
                'exact_title_match' => ! empty( $item['exact_title_match'] ),
            );
        }
        $confidence = isset( $backend['confidence'] ) && is_array( $backend['confidence'] ) ? $backend['confidence'] : array( 'level' => 'medium', 'score' => 60, 'explanation' => 'Python title-aware retrieval returned grounded Sustainable Catalyst records.' );
        $grounding = is_array( $fallback_grounding ) ? $fallback_grounding : array();
        $grounding['sources'] = $sources;
        $grounding['confidence'] = $confidence;
        $grounding['reason_codes'] = array( 'python-backend', 'title-aware-retrieval', ! empty( $backend['ai_used'] ) ? 'grounded-ai' : 'retrieval-only' );
        $grounding['related_titles'] = isset( $backend['related_titles'] ) && is_array( $backend['related_titles'] ) ? $backend['related_titles'] : array();
        $grounding['research_path'] = isset( $backend['research_path'] ) && is_array( $backend['research_path'] ) ? $backend['research_path'] : array();
        $grounding['actions'] = isset( $backend['actions'] ) && is_array( $backend['actions'] ) ? $backend['actions'] : array();

        $note = array(
            'schema' => 'sc-research-librarian-route-note/6.2.1',
            'created_at_utc' => gmdate( 'c' ),
            'question' => sanitize_textarea_field( $question ),
            'source' => sanitize_key( isset( $backend['source'] ) ? $backend['source'] : 'python-backend' ),
            'intent' => sanitize_textarea_field( isset( $backend['interpretation'] ) ? $backend['interpretation'] : 'Knowledge Library research guidance' ),
            'recommended_route' => $route,
            'why' => isset( $route['why'] ) ? $route['why'] : '',
            'platform_fit' => isset( $route['platform_fit'] ) ? $route['platform_fit'] : '',
            'related' => array(),
            'confidence' => $confidence,
            'sources' => $sources,
            'handoffs' => array(),
            'next_step' => isset( $route['next_step'] ) ? $route['next_step'] : 'Open the best match and continue through the related titles.',
            'boundaries' => array(
                'Use only verified Sustainable Catalyst links and records shown in the response.',
                'AI synthesis is advisory and does not replace authoritative sources or professional judgment.',
            ),
            'python_backend' => array(
                'version' => self::VERSION,
                'session_id' => sanitize_key( isset( $backend['session_id'] ) ? $backend['session_id'] : '' ),
                'provider' => sanitize_key( isset( $backend['provider'] ) ? $backend['provider'] : '' ),
                'model' => sanitize_text_field( isset( $backend['model'] ) ? $backend['model'] : '' ),
                'research_path' => $grounding['research_path'],
                'actions' => $grounding['actions'],
            ),
        );
        return array(
            'answer' => wp_kses_post( $backend['answer'] ),
            'source' => sanitize_key( isset( $backend['source'] ) ? $backend['source'] : 'python-backend' ),
            'provider' => sanitize_key( isset( $backend['provider'] ) ? $backend['provider'] : '' ),
            'model' => sanitize_text_field( isset( $backend['model'] ) ? $backend['model'] : '' ),
            'ai_used' => ! empty( $backend['ai_used'] ),
            'session_id' => sanitize_key( isset( $backend['session_id'] ) ? $backend['session_id'] : '' ),
            'ai_status' => self::public_ai_status_from_backend( isset( $backend['status'] ) && is_array( $backend['status'] ) ? $backend['status'] : array() ),
            'route' => $route,
            'grounding' => $grounding,
            'route_note' => $note,
            'matches' => $sources,
            'related_titles' => $grounding['related_titles'],
            'research_path' => $grounding['research_path'],
            'actions' => $grounding['actions'],
            'clarification' => sanitize_textarea_field( isset( $backend['clarification'] ) ? $backend['clarification'] : '' ),
            'endpoint_status' => self::endpoint_status_from_backend( isset( $backend['status'] ) && is_array( $backend['status'] ) ? $backend['status'] : array(), ! empty( $backend['ai_used'] ) ),
        );
    }

    private static function endpoint_status_from_backend( $status, $ai_used = false ) {
        $indexed = absint( isset( $status['indexed_records'] ) ? $status['indexed_records'] : 0 );
        $last_error = sanitize_text_field( isset( $status['last_ai_error'] ) ? $status['last_ai_error'] : '' );
        if ( 0 === $indexed ) {
            return array(
                'state' => 'index-empty',
                'label' => 'Knowledge index needs synchronization',
                'message' => 'The Python service is reachable, but no synchronized Sustainable Catalyst records are available.',
                'error_type' => 'index-empty',
            );
        }
        if ( ! $ai_used && $last_error ) {
            $lower = strtolower( $last_error );
            $quota = false !== strpos( $lower, '429' ) || false !== strpos( $lower, 'quota' ) || false !== strpos( $lower, 'resource_exhausted' );
            return array(
                'state' => $quota ? 'provider-rate-limited' : 'retrieval-only',
                'label' => $quota ? 'Gemini quota unavailable' : 'AI synthesis unavailable',
                'message' => $quota ? 'Title-aware retrieval remains active while the Gemini quota recovers.' : 'Title-aware retrieval remains active without AI synthesis.',
                'error_type' => $quota ? 'provider-rate-limit' : 'provider-unavailable',
            );
        }
        return array(
            'state' => $ai_used ? 'online' : 'retrieval-only',
            'label' => $ai_used ? 'WordPress, Python, and grounded AI online' : 'Python retrieval online',
            'message' => $ai_used ? 'The complete Research Librarian request path succeeded.' : 'The Python knowledge index answered through deterministic retrieval.',
            'error_type' => '',
        );
    }

    public static function public_error_snapshot( $error ) {
        if ( ! is_wp_error( $error ) ) {
            return array( 'state' => 'unknown-error', 'label' => 'Unknown endpoint error', 'message' => 'The endpoint failed without a structured WordPress error.', 'error_type' => 'unknown', 'http_status' => 0 );
        }
        $data = $error->get_error_data();
        $data = is_array( $data ) ? $data : array();
        $status = absint( isset( $data['http_status'] ) ? $data['http_status'] : ( isset( $data['status'] ) ? $data['status'] : 0 ) );
        $type = sanitize_key( isset( $data['error_type'] ) ? $data['error_type'] : '' );
        $message = sanitize_text_field( $error->get_error_message() );
        $lower = strtolower( $message );
        if ( ! $type ) {
            if ( 401 === $status || 403 === $status ) {
                $type = 'integration-key-mismatch';
            } elseif ( 429 === $status ) {
                $type = 'backend-rate-limited';
            } elseif ( 503 === $status && false !== strpos( $lower, 'api_key' ) ) {
                $type = 'backend-not-configured';
            } elseif ( $status >= 500 ) {
                $type = 'backend-unavailable';
            } elseif ( false !== strpos( $lower, 'timed out' ) || false !== strpos( $lower, 'timeout' ) ) {
                $type = 'backend-cold-start';
            } elseif ( false !== strpos( $lower, 'json' ) ) {
                $type = 'backend-invalid-response';
            } else {
                $type = 'backend-unreachable';
            }
        }
        $map = array(
            'integration-key-mismatch' => array( 'integration-key-mismatch', 'Backend integration key mismatch', 'WordPress reached the Python service, but the shared integration key was rejected.' ),
            'backend-not-configured' => array( 'backend-not-configured', 'Python backend not configured', 'The Python service is running, but its server-side integration key is missing.' ),
            'backend-rate-limited' => array( 'backend-rate-limited', 'Python backend rate-limited', 'The Python service temporarily rejected the request because of a rate limit.' ),
            'backend-cold-start' => array( 'backend-warming', 'Python backend is warming up', 'The free Render service may still be starting. Verified WordPress fallback remains available.' ),
            'backend-invalid-response' => array( 'backend-invalid-response', 'Python backend returned invalid data', 'WordPress reached the service but could not parse a valid JSON response.' ),
            'backend-unavailable' => array( 'backend-unavailable', 'Python backend unavailable', 'The Python service returned a temporary server error.' ),
            'backend-unreachable' => array( 'backend-unreachable', 'Python backend unreachable', 'WordPress could not establish a successful connection to the Python service.' ),
            'index-empty' => array( 'index-empty', 'Knowledge index empty', 'The backend is reachable but needs a full Knowledge Library synchronization.' ),
        );
        $selected = isset( $map[ $type ] ) ? $map[ $type ] : array( 'backend-unavailable', 'Python endpoint unavailable', $message );
        return array(
            'state' => $selected[0],
            'label' => $selected[1],
            'message' => $selected[2],
            'error_type' => $type,
            'http_status' => $status,
            'technical_message' => $message,
            'checked_utc' => gmdate( 'c' ),
        );
    }

    private static function public_ai_status_from_backend( $status ) {
        $state = sanitize_key( isset( $status['state'] ) ? $status['state'] : 'offline' );
        $ai_configured = ! empty( $status['ai_configured'] );
        $index_ready = ! empty( $status['index_ready'] );
        $public_state = 'offline';
        if ( in_array( $state, array( 'online', 'ready', 'retrieval-only', 'index-empty', 'indexing', 'backend-warming' ), true ) ) {
            $public_state = $state;
        } elseif ( $index_ready ) {
            $public_state = $ai_configured ? 'ready' : 'retrieval-only';
        } elseif ( $ai_configured ) {
            $public_state = 'index-empty';
        }
        return array(
            'version' => self::VERSION,
            'state' => $public_state,
            'label' => sanitize_text_field( isset( $status['label'] ) ? $status['label'] : 'Python Intelligence Status' ),
            'provider' => sanitize_key( isset( $status['provider'] ) ? $status['provider'] : 'python' ),
            'configured' => $ai_configured,
            'model' => sanitize_text_field( isset( $status['model'] ) ? $status['model'] : '' ),
            'fallback_active' => true,
            'semantic_retrieval' => sanitize_text_field( isset( $status['semantic_retrieval'] ) ? $status['semantic_retrieval'] : 'title-aware-hybrid' ),
            'indexed_records' => absint( isset( $status['indexed_records'] ) ? $status['indexed_records'] : 0 ),
            'indexed_titles' => absint( isset( $status['indexed_titles'] ) ? $status['indexed_titles'] : 0 ),
            'last_sync_utc' => sanitize_text_field( isset( $status['last_sync_utc'] ) ? $status['last_sync_utc'] : '' ),
            'generation_state' => sanitize_key( $status['generation_state'] ?? ( $ai_configured ? 'configured' : 'not-configured' ) ),
            'index_state' => sanitize_key( $status['index_state'] ?? ( $index_ready ? 'ready' : 'empty' ) ),
            'embedding_state' => sanitize_key( $status['embedding_state'] ?? 'unknown' ),
            'pending_chunks' => absint( $status['pending_chunks'] ?? 0 ),
            'readiness_percent' => max( 0, min( 100, absint( $status['readiness_percent'] ?? 0 ) ) ),
            'recommended_action' => sanitize_key( $status['recommended_action'] ?? '' ),
            'backend' => 'render-python',
        );
    }

    public static function backend_status( $admin = true ) {
        if ( ! self::enabled() ) {
            return new WP_Error( 'sc_rl_v621_not_configured', 'The Python backend is not configured.', array( 'status' => 503, 'error_type' => 'backend-not-configured' ) );
        }
        $status = self::request( '/status', 'GET' );
        if ( is_wp_error( $status ) ) {
            return $status;
        }
        if ( empty( $status['indexed_records'] ) ) {
            $status['state'] = 'index-empty';
            $status['label'] = ! empty( $status['ai_configured'] ) ? 'Gemini connected — build the knowledge index' : 'Build the knowledge index';
            $status['index_state'] = 'empty';
            $status['recommended_action'] = 'build-index';
            $status['endpoint_status'] = array( 'state' => 'index-empty', 'error_type' => 'index-empty' );
        }
        if ( ! $admin && isset( $status['last_ai_error'] ) ) {
            unset( $status['last_ai_error'] );
        }
        return $status;
    }

    public static function test_backend() {
        $options = self::options();
        if ( empty( $options['backend_url'] ) ) {
            return new WP_Error( 'sc_rl_v621_missing_url', 'Enter a Python backend URL first.', array( 'status' => 400, 'error_type' => 'backend-not-configured' ) );
        }
        $url = trailingslashit( untrailingslashit( $options['backend_url'] ) ) . 'health';
        $started = microtime( true );
        $response = wp_remote_get( $url, array( 'timeout' => max( 10, absint( $options['request_timeout'] ) ), 'redirection' => 3 ) );
        if ( is_wp_error( $response ) ) {
            $message = $response->get_error_message();
            $type = false !== strpos( strtolower( $message ), 'timed out' ) ? 'backend-cold-start' : 'backend-unreachable';
            return new WP_Error( 'sc_rl_v621_health_transport', $message, array( 'status' => 502, 'error_type' => $type ) );
        }
        $code = wp_remote_retrieve_response_code( $response );
        $body = json_decode( wp_remote_retrieve_body( $response ), true );
        if ( $code < 200 || $code >= 300 || ! is_array( $body ) || empty( $body['ok'] ) ) {
            return new WP_Error( 'sc_rl_v621_health_failed', 'The backend health check failed with HTTP ' . absint( $code ) . '.', array( 'status' => $code ? $code : 502, 'http_status' => $code, 'error_type' => $code >= 500 ? 'backend-unavailable' : 'backend-invalid-response' ) );
        }
        $authenticated = self::request( '/v1/knowledge/summary', 'GET' );
        if ( is_wp_error( $authenticated ) ) {
            return $authenticated;
        }
        return array(
            'ok' => true,
            'version' => sanitize_text_field( isset( $body['version'] ) ? $body['version'] : self::VERSION ),
            'environment' => sanitize_text_field( isset( $body['environment'] ) ? $body['environment'] : '' ),
            'latency_ms' => max( 0, (int) round( ( microtime( true ) - $started ) * 1000 ) ),
            'authenticated' => true,
            'indexed_records' => absint( isset( $authenticated['indexed_records'] ) ? $authenticated['indexed_records'] : 0 ),
            'indexed_titles' => absint( isset( $authenticated['indexed_titles'] ) ? $authenticated['indexed_titles'] : 0 ),
            'state' => sanitize_key( isset( $authenticated['state'] ) ? $authenticated['state'] : '' ),
        );
    }

    private static function request( $path, $method = 'GET', $payload = null ) {
        $options = self::options();
        $base = untrailingslashit( trim( (string) $options['backend_url'] ) );
        if ( ! $base ) {
            return new WP_Error( 'sc_rl_v621_missing_backend_url', 'Python backend URL is missing.', array( 'status' => 503, 'error_type' => 'backend-not-configured' ) );
        }
        $url = $base . '/' . ltrim( $path, '/' );
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
        $started = microtime( true );
        $response = wp_remote_request( $url, $args );
        $latency = max( 0, (int) round( ( microtime( true ) - $started ) * 1000 ) );
        if ( is_wp_error( $response ) ) {
            $message = $response->get_error_message();
            $lower = strtolower( $message );
            $type = ( false !== strpos( $lower, 'timed out' ) || false !== strpos( $lower, 'timeout' ) ) ? 'backend-cold-start' : 'backend-unreachable';
            $error = new WP_Error( 'sc_rl_v621_backend_transport', $message, array( 'status' => 502, 'error_type' => $type, 'latency_ms' => $latency, 'transport_error' => $response->get_error_code() ) );
            self::record_status( 'offline', $error->get_error_message(), self::public_error_snapshot( $error ) );
            return $error;
        }
        $code = wp_remote_retrieve_response_code( $response );
        $body_text = wp_remote_retrieve_body( $response );
        $body = json_decode( $body_text, true );
        if ( $code < 200 || $code >= 300 ) {
            $detail = is_array( $body ) && isset( $body['detail'] ) ? ( is_string( $body['detail'] ) ? $body['detail'] : wp_json_encode( $body['detail'] ) ) : $body_text;
            $type = ( 401 === $code || 403 === $code ) ? 'integration-key-mismatch' : ( 429 === $code ? 'backend-rate-limited' : ( $code >= 500 ? 'backend-unavailable' : 'backend-request-rejected' ) );
            if ( 503 === $code && false !== strpos( strtolower( (string) $detail ), 'api_key' ) ) {
                $type = 'backend-not-configured';
            }
            $error = new WP_Error( 'sc_rl_v621_backend_http', 'Python backend request failed: ' . sanitize_text_field( $detail ), array( 'status' => $code, 'http_status' => $code, 'error_type' => $type, 'latency_ms' => $latency ) );
            self::record_status( 'offline', $error->get_error_message(), self::public_error_snapshot( $error ) );
            return $error;
        }
        if ( ! is_array( $body ) ) {
            $error = new WP_Error( 'sc_rl_v621_backend_json', 'Python backend returned invalid JSON.', array( 'status' => 502, 'error_type' => 'backend-invalid-response', 'latency_ms' => $latency ) );
            self::record_status( 'offline', $error->get_error_message(), self::public_error_snapshot( $error ) );
            return $error;
        }
        self::record_status( 'online', '', array( 'latency_ms' => $latency, 'path' => sanitize_text_field( $path ) ) );
        return $body;
    }

    private static function record_status( $state, $error = '', $details = array() ) {
        $current = get_option( self::STATUS_OPTION, array() );
        $current = is_array( $current ) ? $current : array();
        $current['state'] = sanitize_key( $state );
        $current['last_checked_utc'] = gmdate( 'c' );
        $current['endpoint_details'] = is_array( $details ) ? $details : array();
        if ( 'online' === $state ) {
            $current['last_success_utc'] = gmdate( 'c' );
            $current['last_error'] = '';
        } else {
            $current['last_failure_utc'] = gmdate( 'c' );
            $current['last_error'] = sanitize_text_field( $error );
        }
        update_option( self::STATUS_OPTION, $current, false );
    }

    public static function sync_all_records() {
        if ( ! self::enabled() ) {
            return new WP_Error( 'sc_rl_v621_sync_disabled', 'Enable and configure the Python backend before syncing.', array( 'status' => 400, 'error_type' => 'backend-not-configured' ) );
        }
        $options = self::options();
        $collection = array();
        $records = self::collect_records( absint( $options['max_records'] ), $collection );
        $job_id = 'sync-' . gmdate( 'Ymd-His' ) . '-' . wp_generate_password( 6, false, false );
        $report = array_merge( array(
            'version' => self::VERSION,
            'job_id' => $job_id,
            'state' => 'running',
            'started_utc' => gmdate( 'c' ),
            'completed_utc' => '',
            'synced_records' => 0,
            'accepted_records' => 0,
            'rejected_records' => 0,
            'batches' => array(),
            'source_site' => home_url( '/' ),
        ), is_array( $collection ) ? $collection : array() );
        self::save_sync_report( $report );
        if ( ! $records ) {
            $report['state'] = 'failed';
            $report['completed_utc'] = gmdate( 'c' );
            $report['error'] = 'No public Sustainable Catalyst records were found for synchronization.';
            self::save_sync_report( $report );
            return new WP_Error( 'sc_rl_v621_no_records', $report['error'], array( 'status' => 400, 'error_type' => 'index-empty', 'sync_report' => $report ) );
        }
        $batch_size = max( 25, min( 250, absint( $options['sync_batch_size'] ) ) );
        $chunks = array_chunk( $records, $batch_size );
        $last = array();
        foreach ( $chunks as $index => $chunk ) {
            $batch = array(
                'batch' => $index + 1,
                'batch_count' => count( $chunks ),
                'mode' => 0 === $index ? 'replace' : 'upsert',
                'records_sent' => count( $chunk ),
                'started_utc' => gmdate( 'c' ),
                'state' => 'running',
            );
            $last = self::request( '/v1/knowledge/sync', 'POST', array(
                'records' => $chunk,
                'mode' => $batch['mode'],
                'source_site' => home_url( '/' ),
                'generated_utc' => gmdate( 'c' ),
                'job_id' => $job_id,
                'batch_index' => $index + 1,
                'batch_count' => count( $chunks ),
            ) );
            if ( is_wp_error( $last ) ) {
                $batch['state'] = 'failed';
                $batch['completed_utc'] = gmdate( 'c' );
                $batch['error'] = $last->get_error_message();
                $report['batches'][] = $batch;
                $report['state'] = 'failed';
                $report['completed_utc'] = gmdate( 'c' );
                $report['error'] = $last->get_error_message();
                $report['rejected_records'] += count( $chunk );
                self::save_sync_report( $report );
                return new WP_Error( $last->get_error_code(), $last->get_error_message(), array_merge( (array) $last->get_error_data(), array( 'sync_report' => $report ) ) );
            }
            $accepted = absint( isset( $last['accepted'] ) ? $last['accepted'] : ( isset( $last['received'] ) ? $last['received'] : count( $chunk ) ) );
            $batch['state'] = 'completed';
            $batch['completed_utc'] = gmdate( 'c' );
            $batch['accepted_records'] = $accepted;
            $batch['rejected_records'] = max( 0, count( $chunk ) - $accepted );
            $batch['backend_total_records'] = absint( isset( $last['total_records'] ) ? $last['total_records'] : 0 );
            $report['batches'][] = $batch;
            $report['accepted_records'] += $accepted;
            $report['rejected_records'] += $batch['rejected_records'];
            $report['synced_records'] += count( $chunk );
            self::save_sync_report( $report );
        }
        $report['state'] = 'completed';
        $report['completed_utc'] = gmdate( 'c' );
        $report['batch_count'] = count( $chunks );
        $report['backend_result'] = $last;
        self::save_sync_report( $report );
        $status = array(
            'state' => 'online',
            'last_sync_utc' => $report['completed_utc'],
            'synced_records' => count( $records ),
            'accepted_records' => $report['accepted_records'],
            'rejected_records' => $report['rejected_records'],
            'batches' => count( $chunks ),
            'job_id' => $job_id,
            'backend_result' => $last,
            'sync_report' => $report,
        );
        update_option( self::STATUS_OPTION, array_merge( (array) get_option( self::STATUS_OPTION, array() ), $status ), false );
        return $status;
    }

    private static function save_sync_report( $report ) {
        update_option( self::SYNC_REPORT_OPTION, $report, false );
        if ( isset( $report['state'] ) && in_array( $report['state'], array( 'completed', 'failed' ), true ) ) {
            $history = get_option( self::SYNC_HISTORY_OPTION, array() );
            $history = is_array( $history ) ? $history : array();
            $history[] = $report;
            if ( count( $history ) > 20 ) {
                $history = array_slice( $history, -20 );
            }
            update_option( self::SYNC_HISTORY_OPTION, $history, false );
        }
    }

    public static function latest_sync_report() {
        $report = get_option( self::SYNC_REPORT_OPTION, array() );
        return is_array( $report ) ? $report : array();
    }

    public static function sync_history() {
        $history = get_option( self::SYNC_HISTORY_OPTION, array() );
        return is_array( $history ) ? $history : array();
    }

    public static function collect_records( $max_records = 5000, &$report = null ) {
        $max_records = max( 100, min( 10000, absint( $max_records ) ) );
        $records = array();
        $seen_urls = array();
        $report = array(
            'eligible_post_types' => array(),
            'unsupported_post_types' => array(),
            'expected_post_types_missing' => array(),
            'eligible_public_posts' => 0,
            'legacy_index_records' => 0,
            'collected_records' => 0,
            'skipped_records' => 0,
            'duplicate_urls' => 0,
            'records_by_post_type' => array(),
        );

        // v6.2.1 indexes canonical published WordPress records first. The older
        // route/index registry is appended only when it contributes a unique URL.
        // This prevents a summary-only legacy entry from masking the full article.
        $all_public_post_types = get_post_types( array( 'public' => true ), 'names' );
        $all_public_post_types = is_array( $all_public_post_types ) ? $all_public_post_types : array();
        $excluded = array( 'attachment', 'revision', 'nav_menu_item', 'wp_block', 'wp_template', 'wp_template_part', 'wp_navigation', 'custom_css', 'customize_changeset' );
        $post_types = array_values( array_diff( $all_public_post_types, $excluded ) );
        $report['eligible_post_types'] = $post_types;
        $report['unsupported_post_types'] = array_values( array_intersect( $all_public_post_types, $excluded ) );
        $expected = array( 'post', 'page', 'article', 'library', 'foundation_document', 'channel' );
        $registered = get_post_types( array(), 'names' );
        $registered = is_array( $registered ) ? array_values( $registered ) : array();
        $report['expected_post_types_missing'] = array_values( array_diff( $expected, $registered ) );

        foreach ( $post_types as $post_type ) {
            $counts = wp_count_posts( $post_type );
            if ( is_object( $counts ) && isset( $counts->publish ) ) {
                $report['eligible_public_posts'] += absint( $counts->publish );
            }
            if ( count( $records ) >= $max_records ) {
                continue;
            }
            $paged = 1;
            do {
                $query = new WP_Query( array(
                    'post_type' => $post_type,
                    'post_status' => 'publish',
                    'posts_per_page' => 200,
                    'paged' => $paged,
                    'orderby' => 'ID',
                    'order' => 'ASC',
                    'fields' => 'ids',
                    'no_found_rows' => false,
                    'ignore_sticky_posts' => true,
                    'suppress_filters' => false,
                ) );
                if ( ! $query->posts ) {
                    break;
                }
                foreach ( $query->posts as $post_id ) {
                    if ( count( $records ) >= $max_records ) {
                        break 2;
                    }
                    $record = self::build_post_record( $post_id );
                    if ( ! $record ) {
                        $report['skipped_records']++;
                        continue;
                    }
                    $canonical_url = untrailingslashit( esc_url_raw( $record['url'] ) );
                    if ( ! $canonical_url ) {
                        $report['skipped_records']++;
                        continue;
                    }
                    if ( isset( $seen_urls[ $canonical_url ] ) ) {
                        $report['duplicate_urls']++;
                        continue;
                    }
                    $record['url'] = esc_url_raw( $record['url'] );
                    $seen_urls[ $canonical_url ] = true;
                    $records[] = $record;
                    if ( ! isset( $report['records_by_post_type'][ $post_type ] ) ) {
                        $report['records_by_post_type'][ $post_type ] = 0;
                    }
                    $report['records_by_post_type'][ $post_type ]++;
                }
                $paged++;
            } while ( $paged <= (int) $query->max_num_pages );
        }

        $saved_index = get_option( SC_RL6_Core::INDEX_OPTION, array() );
        if ( is_array( $saved_index ) && ! empty( $saved_index['records'] ) && is_array( $saved_index['records'] ) ) {
            foreach ( $saved_index['records'] as $item ) {
                if ( count( $records ) >= $max_records ) {
                    break;
                }
                if ( empty( $item['title'] ) || empty( $item['url'] ) ) {
                    $report['skipped_records']++;
                    continue;
                }
                $url = esc_url_raw( $item['url'] );
                $canonical_url = untrailingslashit( $url );
                if ( ! $canonical_url ) {
                    $report['skipped_records']++;
                    continue;
                }
                if ( isset( $seen_urls[ $canonical_url ] ) ) {
                    $report['duplicate_urls']++;
                    continue;
                }
                $seen_urls[ $canonical_url ] = true;
                $report['legacy_index_records']++;
                $records[] = array(
                    'id' => 'legacy:' . sanitize_key( isset( $item['id'] ) ? $item['id'] : md5( $url ) ),
                    'title' => sanitize_text_field( $item['title'] ),
                    'url' => $url,
                    'slug' => sanitize_title( wp_parse_url( $url, PHP_URL_PATH ) ),
                    'summary' => sanitize_textarea_field( isset( $item['summary'] ) ? $item['summary'] : '' ),
                    'content' => '',
                    'headings' => array(),
                    'post_type' => sanitize_key( isset( $item['type'] ) ? $item['type'] : 'route' ),
                    'taxonomies' => array( 'topics' => isset( $item['topics'] ) && is_array( $item['topics'] ) ? array_map( 'sanitize_text_field', $item['topics'] ) : array() ),
                    'series' => '',
                    'article_map' => '',
                    'parent_title' => '',
                    'modified_utc' => sanitize_text_field( isset( $item['modified_utc'] ) ? $item['modified_utc'] : '' ),
                    'source' => 'wordpress-index',
                    'route_id' => sanitize_key( isset( $item['route_id'] ) ? $item['route_id'] : '' ),
                    'metadata' => array( 'source_kind' => isset( $item['source_kind'] ) ? sanitize_key( $item['source_kind'] ) : '' ),
                );
            }
        }

        $report['collected_records'] = count( $records );
        $report['capacity_reached'] = count( $records ) >= $max_records;
        $report['max_records'] = $max_records;
        return $records;
    }

    private static function is_public_post_type( $post_type ) {
        $object = get_post_type_object( $post_type );
        return $object && ! empty( $object->public ) && 'attachment' !== $post_type;
    }

    private static function build_post_record( $post_id ) {
        $post = get_post( $post_id );
        if ( ! $post || 'publish' !== $post->post_status || ! self::is_public_post_type( $post->post_type ) ) {
            return null;
        }
        $url = get_permalink( $post );
        $title = get_the_title( $post );
        if ( ! $url || ! $title ) {
            return null;
        }
        $options = self::options();
        $raw_content = (string) $post->post_content;
        $headings = array();
        if ( preg_match_all( '/<h[1-4][^>]*>(.*?)<\/h[1-4]>/is', $raw_content, $matches ) ) {
            foreach ( array_slice( $matches[1], 0, 80 ) as $heading ) {
                $heading = trim( wp_strip_all_tags( $heading ) );
                if ( $heading ) {
                    $headings[] = $heading;
                }
            }
        }
        $plain_content = trim( preg_replace( '/\s+/', ' ', wp_strip_all_tags( strip_shortcodes( $raw_content ) ) ) );
        $limit = max( 2000, min( 60000, absint( $options['content_character_limit'] ) ) );
        if ( '1' !== (string) $options['include_content'] ) {
            $plain_content = '';
        } else {
            $plain_content = function_exists( 'mb_substr' ) ? mb_substr( $plain_content, 0, $limit ) : substr( $plain_content, 0, $limit );
        }
        $excerpt = trim( preg_replace( '/\s+/', ' ', wp_strip_all_tags( get_the_excerpt( $post ) ) ) );
        if ( ! $excerpt ) {
            $excerpt = wp_trim_words( $plain_content, 45, '' );
        }
        $taxonomies = array();
        foreach ( get_object_taxonomies( $post->post_type, 'names' ) as $taxonomy ) {
            $terms = wp_get_post_terms( $post_id, $taxonomy, array( 'fields' => 'names' ) );
            if ( ! is_wp_error( $terms ) && $terms ) {
                $taxonomies[ $taxonomy ] = array_values( array_map( 'sanitize_text_field', $terms ) );
            }
        }
        $series = '';
        foreach ( $taxonomies as $taxonomy => $terms ) {
            if ( false !== strpos( $taxonomy, 'series' ) && $terms ) {
                $series = $terms[0];
                break;
            }
        }
        if ( ! $series && ! empty( $taxonomies['category'] ) ) {
            $series = $taxonomies['category'][0];
        }
        $article_map = '';
        foreach ( array( 'sc_article_map', '_sc_article_map', 'article_map', 'series_map' ) as $meta_key ) {
            $candidate = get_post_meta( $post_id, $meta_key, true );
            if ( is_scalar( $candidate ) && trim( (string) $candidate ) ) {
                $article_map = sanitize_text_field( $candidate );
                break;
            }
        }
        $parent_title = $post->post_parent ? get_the_title( $post->post_parent ) : '';
        return array(
            'id' => 'wp:' . $post->post_type . ':' . absint( $post_id ),
            'title' => sanitize_text_field( $title ),
            'url' => esc_url_raw( $url ),
            'slug' => sanitize_title( $post->post_name ),
            'summary' => sanitize_textarea_field( $excerpt ),
            'content' => sanitize_textarea_field( $plain_content ),
            'headings' => array_values( array_unique( array_map( 'sanitize_text_field', $headings ) ) ),
            'post_type' => sanitize_key( $post->post_type ),
            'taxonomies' => $taxonomies,
            'series' => sanitize_text_field( $series ),
            'article_map' => sanitize_text_field( $article_map ),
            'parent_title' => sanitize_text_field( $parent_title ),
            'modified_utc' => get_post_modified_time( 'c', true, $post ),
            'source' => 'wordpress',
            'route_id' => '',
            'metadata' => array(
                'post_id' => absint( $post_id ),
                'author_id' => absint( $post->post_author ),
                'menu_order' => absint( $post->menu_order ),
            ),
        );
    }

    public static function diagnostics_snapshot() {
        $options = self::options();
        $status = self::backend_status( true );
        $stored = get_option( self::STATUS_OPTION, array() );
        $next = wp_next_scheduled( self::SYNC_HOOK );
        $report = self::latest_sync_report();
        return array(
            'version' => self::VERSION,
            'wordpress' => array(
                'home_url' => home_url( '/' ),
                'rest_url' => rest_url( self::REST_NAMESPACE . '/ask' ),
                'rest_enabled' => function_exists( 'rest_get_server' ),
                'permalink_structure' => (string) get_option( 'permalink_structure', '' ),
            ),
            'configuration' => array(
                'enabled' => self::enabled(),
                'backend_url_configured' => ! empty( $options['backend_url'] ),
                'integration_key_configured' => ! empty( $options['backend_api_key'] ),
                'auto_sync' => '1' === (string) $options['auto_sync'],
                'sync_frequency' => sanitize_key( $options['sync_frequency'] ),
            ),
            'cron' => array(
                'scheduled' => (bool) $next,
                'next_run_utc' => $next ? gmdate( 'c', $next ) : '',
                'hook' => self::SYNC_HOOK,
                'wp_cron_disabled' => defined( 'DISABLE_WP_CRON' ) && DISABLE_WP_CRON,
            ),
            'backend' => is_wp_error( $status ) ? self::public_error_snapshot( $status ) : $status,
            'stored_status' => is_array( $stored ) ? $stored : array(),
            'latest_sync_report' => $report,
            'generated_utc' => gmdate( 'c' ),
        );
    }

    public static function render_admin_page() {
        if ( ! current_user_can( 'manage_options' ) ) {
            return;
        }
        $notice = '';
        $notice_type = 'success';
        if ( 'POST' === strtoupper( isset( $_SERVER['REQUEST_METHOD'] ) ? $_SERVER['REQUEST_METHOD'] : '' ) ) {
            check_admin_referer( 'sc_rl_v620_admin_action' );
            if ( isset( $_POST['sc_rl_v620_save'] ) ) {
                $input = isset( $_POST['sc_rl_v620'] ) && is_array( $_POST['sc_rl_v620'] ) ? wp_unslash( $_POST['sc_rl_v620'] ) : array();
                self::save_options( $input );
                self::sync_cron();
                $notice = 'Python intelligence settings saved.';
            } elseif ( isset( $_POST['sc_rl_v620_test'] ) ) {
                $input = isset( $_POST['sc_rl_v620'] ) && is_array( $_POST['sc_rl_v620'] ) ? wp_unslash( $_POST['sc_rl_v620'] ) : array();
                self::save_options( $input );
                $test = self::test_backend();
                if ( is_wp_error( $test ) ) {
                    $notice_type = 'error';
                    $notice = $test->get_error_message();
                } else {
                    $notice = 'Python backend health check succeeded. Version ' . sanitize_text_field( isset( $test['version'] ) ? $test['version'] : self::VERSION ) . '.';
                }
            } elseif ( isset( $_POST['sc_rl_v620_sync'] ) ) {
                $input = isset( $_POST['sc_rl_v620'] ) && is_array( $_POST['sc_rl_v620'] ) ? wp_unslash( $_POST['sc_rl_v620'] ) : array();
                self::save_options( $input );
                $sync = self::sync_all_records();
                if ( is_wp_error( $sync ) ) {
                    $notice_type = 'error';
                    $notice = $sync->get_error_message();
                } else {
                    $notice = 'Knowledge sync completed: ' . absint( $sync['synced_records'] ) . ' records across ' . absint( $sync['batches'] ) . ' batches.';
                }
            } elseif ( isset( $_POST['sc_rl_v621_reset_rate_limits'] ) ) {
                if ( class_exists( 'SC_RL6_Core' ) ) {
                    $reset = SC_RL6_Core::instance()->reset_rate_limits();
                    $notice = 'Public rate-limit windows reset: ' . absint( isset( $reset['removed'] ) ? $reset['removed'] : 0 ) . ' active window(s) removed.';
                } else {
                    $notice_type = 'error';
                    $notice = 'The Research Librarian core was unavailable, so rate limits could not be reset.';
                }
            } elseif ( isset( $_POST['sc_rl_v621_repair'] ) ) {
                $input = isset( $_POST['sc_rl_v620'] ) && is_array( $_POST['sc_rl_v620'] ) ? wp_unslash( $_POST['sc_rl_v620'] ) : array();
                self::save_options( $input );
                $repair = self::repair_and_resync();
                if ( is_wp_error( $repair ) ) {
                    $notice_type = 'error';
                    $repair_data = $repair->get_error_data();
                    $repair_stage = is_array( $repair_data ) && ! empty( $repair_data['repair_stage'] ) ? sanitize_text_field( $repair_data['repair_stage'] ) : 'diagnostics';
                    $notice = 'Repair stopped during ' . $repair_stage . ': ' . $repair->get_error_message();
                } else {
                    $notice = $repair['message'];
                }
            }
        }
        $options = self::options();
        $status = self::backend_status( true );
        $local_status = get_option( self::STATUS_OPTION, array() );
        $diagnostics = self::diagnostics_snapshot();
        $sync_report = self::latest_sync_report();
        $rate_status = class_exists( 'SC_RL6_Core' ) ? SC_RL6_Core::instance()->rate_limit_status() : array();
        ?>
        <div class="wrap">
            <h1>Python Intelligence</h1>
            <p>Research Librarian AI v6.2.1 uses WordPress as the public interface and publishing source while a FastAPI service on Render performs full-library title-aware retrieval, grounded Gemini synthesis, related-title discovery, and short conversational continuity.</p>
            <?php if ( $notice ) : ?><div class="notice notice-<?php echo esc_attr( $notice_type ); ?> is-dismissible"><p><?php echo esc_html( $notice ); ?></p></div><?php endif; ?>

            <div class="sc-rl-admin-grid">
                <article class="sc-rl-admin-card" data-state="<?php echo esc_attr( is_wp_error( $status ) ? 'offline' : ( isset( $status['state'] ) ? $status['state'] : 'unknown' ) ); ?>">
                    <h2><?php echo esc_html( is_wp_error( $status ) ? 'Backend unavailable' : ( isset( $status['label'] ) ? $status['label'] : 'Backend status' ) ); ?></h2>
                    <span class="sc-rl-admin-metric"><?php echo esc_html( is_wp_error( $status ) ? 'Offline' : ( isset( $status['version'] ) ? 'v' . $status['version'] : 'Online' ) ); ?></span>
                    <p><?php echo esc_html( is_wp_error( $status ) ? $status->get_error_message() : ( isset( $status['model'] ) ? $status['model'] : '' ) ); ?></p>
                </article>
                <article class="sc-rl-admin-card"><h2>Indexed titles</h2><span class="sc-rl-admin-metric"><?php echo esc_html( is_wp_error( $status ) ? 0 : absint( isset( $status['indexed_titles'] ) ? $status['indexed_titles'] : 0 ) ); ?></span><p><?php echo esc_html( is_wp_error( $status ) ? 'Run a full sync.' : absint( isset( $status['indexed_records'] ) ? $status['indexed_records'] : 0 ) . ' total records' ); ?></p></article>
                <article class="sc-rl-admin-card"><h2>Last knowledge sync</h2><span class="sc-rl-admin-metric"><?php echo esc_html( ! is_wp_error( $status ) && ! empty( $status['last_sync_utc'] ) ? 'Synced' : 'Not synced' ); ?></span><p><?php echo esc_html( ! is_wp_error( $status ) && ! empty( $status['last_sync_utc'] ) ? $status['last_sync_utc'] : ( isset( $local_status['last_sync_utc'] ) ? $local_status['last_sync_utc'] : 'Run Sync Full Knowledge Library.' ) ); ?></p></article>
                <article class="sc-rl-admin-card"><h2>Architecture</h2><span class="sc-rl-admin-metric">WordPress + Python</span><p>WordPress publishing and UI · Render FastAPI intelligence.</p></article>
            </div>

            <form method="post">
                <?php wp_nonce_field( 'sc_rl_v620_admin_action' ); ?>
                <table class="form-table sc-rl-provider-table" role="presentation">
                    <tr><th>Enable Python intelligence</th><td><input type="hidden" name="sc_rl_v620[enabled]" value="0"><label><input type="checkbox" name="sc_rl_v620[enabled]" value="1" <?php checked( $options['enabled'], '1' ); ?>> Use the Render/FastAPI backend for public answers and title-aware retrieval</label></td></tr>
                    <tr><th><label for="sc-rl-v620-url">Backend URL</label></th><td><input id="sc-rl-v620-url" class="regular-text" type="url" name="sc_rl_v620[backend_url]" value="<?php echo esc_attr( $options['backend_url'] ); ?>" placeholder="https://sustainable-catalyst-research-librarian-ai.onrender.com"><p class="description">Do not add a trailing endpoint path.</p></td></tr>
                    <tr><th><label for="sc-rl-v620-key">Shared integration key</label></th><td><input id="sc-rl-v620-key" class="regular-text" type="password" name="sc_rl_v620[backend_api_key_new]" value="" autocomplete="new-password" placeholder="<?php echo esc_attr( $options['backend_api_key'] ? 'Key saved. Paste only to replace.' : 'Paste SC_RL_BACKEND_API_KEY' ); ?>"><p class="description">Use the same long random value in Render and WordPress. The key is sent only server-to-server.</p><?php if ( $options['backend_api_key'] ) : ?><label><input type="checkbox" name="sc_rl_v620[backend_api_key_clear]" value="1"> Clear saved integration key</label><?php endif; ?></td></tr>
                    <tr><th><label for="sc-rl-v620-timeout">Request timeout</label></th><td><input id="sc-rl-v620-timeout" type="number" min="10" max="120" name="sc_rl_v620[request_timeout]" value="<?php echo esc_attr( $options['request_timeout'] ); ?>"> seconds</td></tr>
                    <tr><th><label for="sc-rl-v620-batch">Sync batch size</label></th><td><input id="sc-rl-v620-batch" type="number" min="25" max="250" name="sc_rl_v620[sync_batch_size]" value="<?php echo esc_attr( $options['sync_batch_size'] ); ?>"></td></tr>
                    <tr><th><label for="sc-rl-v620-max">Maximum public records</label></th><td><input id="sc-rl-v620-max" type="number" min="100" max="10000" name="sc_rl_v620[max_records]" value="<?php echo esc_attr( $options['max_records'] ); ?>"><p class="description">The default supports the full Sustainable Catalyst library instead of the previous 250-record cap.</p></td></tr>
                    <tr><th>Content indexing</th><td><input type="hidden" name="sc_rl_v620[include_content]" value="0"><label><input type="checkbox" name="sc_rl_v620[include_content]" value="1" <?php checked( $options['include_content'], '1' ); ?>> Include cleaned public body text, headings, taxonomies, series, article-map metadata, and parent relationships</label></td></tr>
                    <tr><th><label for="sc-rl-v620-char-limit">Content characters per record</label></th><td><input id="sc-rl-v620-char-limit" type="number" min="2000" max="60000" name="sc_rl_v620[content_character_limit]" value="<?php echo esc_attr( $options['content_character_limit'] ); ?>"></td></tr>
                    <tr><th>Automatic synchronization</th><td><input type="hidden" name="sc_rl_v620[auto_sync]" value="0"><label><input type="checkbox" name="sc_rl_v620[auto_sync]" value="1" <?php checked( $options['auto_sync'], '1' ); ?>> Synchronize after public content changes and on a recurring schedule</label></td></tr>
                    <tr><th><label for="sc-rl-v620-frequency">Recurring frequency</label></th><td><select id="sc-rl-v620-frequency" name="sc_rl_v620[sync_frequency]"><?php foreach ( array( 'hourly' => 'Hourly', 'sc_rl_six_hourly' => 'Every six hours', 'twicedaily' => 'Twice daily', 'daily' => 'Daily' ) as $value => $label ) : ?><option value="<?php echo esc_attr( $value ); ?>" <?php selected( $options['sync_frequency'], $value ); ?>><?php echo esc_html( $label ); ?></option><?php endforeach; ?></select></td></tr>
                </table>
                <p class="submit"><button class="button button-primary" type="submit" name="sc_rl_v620_save" value="1">Save Python Intelligence Settings</button> <button class="button" type="submit" name="sc_rl_v620_test" value="1">Test Backend and Integration Key</button> <button class="button button-secondary" type="submit" name="sc_rl_v620_sync" value="1">Sync Full Knowledge Library</button> <button class="button button-secondary" type="submit" name="sc_rl_v621_repair" value="1">Repair Endpoint and Resynchronize</button> <button class="button" type="submit" name="sc_rl_v621_reset_rate_limits" value="1">Reset Public Rate Limits</button></p>
            </form>
            <h2>Endpoint and Synchronization Diagnostics</h2>
            <table class="widefat striped" style="max-width:1100px;margin-bottom:18px"><tbody>
                <tr><th>WordPress REST endpoint</th><td><code><?php echo esc_html( $diagnostics['wordpress']['rest_url'] ); ?></code></td></tr>
                <tr><th>Permalink structure</th><td><code><?php echo esc_html( $diagnostics['wordpress']['permalink_structure'] ? $diagnostics['wordpress']['permalink_structure'] : 'Plain / not configured' ); ?></code></td></tr>
                <tr><th>WP-Cron</th><td><?php echo esc_html( $diagnostics['cron']['wp_cron_disabled'] ? 'Disabled by configuration' : ( $diagnostics['cron']['scheduled'] ? 'Scheduled' : 'Not scheduled' ) ); ?><?php if ( $diagnostics['cron']['next_run_utc'] ) : ?> · next run <?php echo esc_html( $diagnostics['cron']['next_run_utc'] ); ?><?php endif; ?></td></tr>
                <tr><th>Public rate limit</th><td><?php echo esc_html( absint( isset( $rate_status['limit'] ) ? $rate_status['limit'] : 0 ) ); ?> questions per <?php echo esc_html( absint( isset( $rate_status['window_minutes'] ) ? $rate_status['window_minutes'] : 0 ) ); ?> minutes · <?php echo esc_html( absint( isset( $rate_status['active_visitors'] ) ? $rate_status['active_visitors'] : 0 ) ); ?> active visitor window(s)</td></tr>
                <tr><th>Latest sync job</th><td><?php echo esc_html( ! empty( $sync_report['job_id'] ) ? $sync_report['job_id'] . ' · ' . $sync_report['state'] : 'No v6.2.1 sync report yet' ); ?></td></tr>
                <tr><th>Eligible / collected / skipped</th><td><?php echo esc_html( absint( isset( $sync_report['eligible_public_posts'] ) ? $sync_report['eligible_public_posts'] : 0 ) . ' / ' . absint( isset( $sync_report['collected_records'] ) ? $sync_report['collected_records'] : 0 ) . ' / ' . absint( isset( $sync_report['skipped_records'] ) ? $sync_report['skipped_records'] : 0 ) ); ?></td></tr>
                <tr><th>Duplicates / rejected</th><td><?php echo esc_html( absint( isset( $sync_report['duplicate_urls'] ) ? $sync_report['duplicate_urls'] : 0 ) . ' / ' . absint( isset( $sync_report['rejected_records'] ) ? $sync_report['rejected_records'] : 0 ) ); ?></td></tr>
                <tr><th>Expected post types not registered</th><td><?php echo esc_html( ! empty( $sync_report['expected_post_types_missing'] ) ? implode( ', ', $sync_report['expected_post_types_missing'] ) : 'None reported' ); ?></td></tr>
            </tbody></table>
            <?php if ( ! empty( $sync_report['batches'] ) ) : ?>
                <h3>Last Sync Batches</h3>
                <table class="widefat striped" style="max-width:1100px;margin-bottom:18px"><thead><tr><th>Batch</th><th>Mode</th><th>Sent</th><th>Accepted</th><th>Rejected</th><th>State</th></tr></thead><tbody>
                <?php foreach ( $sync_report['batches'] as $batch ) : ?><tr><td><?php echo esc_html( absint( $batch['batch'] ) . ' / ' . absint( $batch['batch_count'] ) ); ?></td><td><?php echo esc_html( $batch['mode'] ); ?></td><td><?php echo esc_html( absint( $batch['records_sent'] ) ); ?></td><td><?php echo esc_html( absint( isset( $batch['accepted_records'] ) ? $batch['accepted_records'] : 0 ) ); ?></td><td><?php echo esc_html( absint( isset( $batch['rejected_records'] ) ? $batch['rejected_records'] : 0 ) ); ?></td><td><?php echo esc_html( $batch['state'] ); ?></td></tr><?php endforeach; ?>
                </tbody></table>
            <?php endif; ?>
            <div class="sc-rl-admin-note"><strong>Render boundary:</strong> Put the Gemini key in Render as <code>SC_RL_GEMINI_API_KEY</code>, not in the public page. WordPress sends public library records and questions to the backend through an authenticated server-to-server request. The public browser never receives the integration key or Gemini key.</div>
        </div>
        <?php
    }

    private static function save_options( $input ) {
        $old = self::options();
        $new_key = isset( $input['backend_api_key_new'] ) ? trim( sanitize_text_field( $input['backend_api_key_new'] ) ) : '';
        $clear = ! empty( $input['backend_api_key_clear'] );
        $saved = array(
            'enabled' => ! empty( $input['enabled'] ) ? '1' : '0',
            'backend_url' => isset( $input['backend_url'] ) ? esc_url_raw( untrailingslashit( $input['backend_url'] ) ) : $old['backend_url'],
            'backend_api_key' => $clear ? '' : ( $new_key ? $new_key : $old['backend_api_key'] ),
            'request_timeout' => max( 10, min( 120, absint( isset( $input['request_timeout'] ) ? $input['request_timeout'] : $old['request_timeout'] ) ) ),
            'sync_batch_size' => max( 25, min( 250, absint( isset( $input['sync_batch_size'] ) ? $input['sync_batch_size'] : $old['sync_batch_size'] ) ) ),
            'max_records' => max( 100, min( 10000, absint( isset( $input['max_records'] ) ? $input['max_records'] : $old['max_records'] ) ) ),
            'auto_sync' => ! empty( $input['auto_sync'] ) ? '1' : '0',
            'sync_frequency' => in_array( isset( $input['sync_frequency'] ) ? $input['sync_frequency'] : '', array( 'hourly', 'sc_rl_six_hourly', 'twicedaily', 'daily' ), true ) ? $input['sync_frequency'] : 'twicedaily',
            'include_content' => ! empty( $input['include_content'] ) ? '1' : '0',
            'content_character_limit' => max( 2000, min( 60000, absint( isset( $input['content_character_limit'] ) ? $input['content_character_limit'] : $old['content_character_limit'] ) ) ),
            'public_title_suggestions' => '1',
        );
        update_option( self::OPTION_NAME, $saved, false );
        return $saved;
    }
}

// Backward-compatible class alias for v6.2.0 integrations and cached admin code.
if ( ! class_exists( 'SC_RL6_V620_Knowledge_Intelligence', false ) ) {
    class_alias( 'SC_RL6_V621_Endpoint_Reliability', 'SC_RL6_V620_Knowledge_Intelligence' );
}
