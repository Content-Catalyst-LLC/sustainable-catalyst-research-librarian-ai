<?php
/**
 * Research Librarian AI v6.2.0 — Python knowledge intelligence and production UX bridge.
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class SC_RL6_V620_Knowledge_Intelligence {
    const VERSION = '6.2.0';
    const OPTION_NAME = 'sc_rl_v620_python_options';
    const STATUS_OPTION = 'sc_rl_v620_python_status';
    const SYNC_HOOK = 'sc_rl_v620_python_sync_event';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';

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
        register_rest_route( self::REST_NAMESPACE, '/python/sync', array(
            'methods' => WP_REST_Server::CREATABLE,
            'callback' => array( __CLASS__, 'handle_admin_sync' ),
            'permission_callback' => array( __CLASS__, 'can_manage' ),
        ) );
    }

    public static function can_manage() {
        return current_user_can( 'manage_options' );
    }

    public static function handle_public_status() {
        $status = self::backend_status( false );
        if ( is_wp_error( $status ) ) {
            return new WP_REST_Response( array(
                'version' => self::VERSION,
                'enabled' => self::enabled(),
                'state' => self::enabled() ? 'offline' : 'disabled',
                'label' => self::enabled() ? 'Python Intelligence Offline' : 'Python Intelligence Not Configured',
                'indexed_records' => 0,
                'indexed_titles' => 0,
            ), 200 );
        }
        unset( $status['last_ai_error'] );
        $status['enabled'] = self::enabled();
        return new WP_REST_Response( $status, 200 );
    }

    public static function handle_suggestions( WP_REST_Request $request ) {
        if ( ! self::enabled() ) {
            return new WP_REST_Response( array( 'suggestions' => array() ), 200 );
        }
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_v620_bad_nonce', 'Security check failed.', array( 'status' => 403 ) );
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

    public static function ask( $question, $route_hint = array(), $wordpress_status = array(), $session_id = '' ) {
        if ( ! self::enabled() ) {
            return new WP_Error( 'sc_rl_v620_disabled', 'The Python intelligence backend is not enabled.' );
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
            return new WP_Error( 'sc_rl_v620_invalid_response', 'The Python backend returned an invalid answer.' );
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
            'schema' => 'sc-research-librarian-route-note/6.2',
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
        );
    }

    private static function public_ai_status_from_backend( $status ) {
        $state = sanitize_key( isset( $status['state'] ) ? $status['state'] : 'offline' );
        $ai_configured = ! empty( $status['ai_configured'] );
        $index_ready = ! empty( $status['index_ready'] );
        $public_state = 'offline';
        if ( 'online' === $state && $ai_configured && $index_ready ) {
            $public_state = 'online';
        } elseif ( 'ready' === $state && $ai_configured && $index_ready ) {
            $public_state = 'not-tested';
        } elseif ( $index_ready ) {
            $public_state = 'retrieval-only';
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
            'backend' => 'render-python',
        );
    }

    public static function backend_status( $admin = true ) {
        if ( ! self::enabled() ) {
            return new WP_Error( 'sc_rl_v620_not_configured', 'The Python backend is not configured.' );
        }
        $status = self::request( '/status', 'GET' );
        if ( is_wp_error( $status ) ) {
            return $status;
        }
        if ( ! $admin && isset( $status['last_ai_error'] ) ) {
            unset( $status['last_ai_error'] );
        }
        return $status;
    }

    public static function test_backend() {
        $options = self::options();
        if ( empty( $options['backend_url'] ) ) {
            return new WP_Error( 'sc_rl_v620_missing_url', 'Enter a Python backend URL first.' );
        }
        $url = trailingslashit( untrailingslashit( $options['backend_url'] ) ) . 'health';
        $response = wp_remote_get( $url, array( 'timeout' => max( 10, absint( $options['request_timeout'] ) ) ) );
        if ( is_wp_error( $response ) ) {
            return $response;
        }
        $code = wp_remote_retrieve_response_code( $response );
        $body = json_decode( wp_remote_retrieve_body( $response ), true );
        if ( $code < 200 || $code >= 300 || ! is_array( $body ) || empty( $body['ok'] ) ) {
            return new WP_Error( 'sc_rl_v620_health_failed', 'The backend health check failed with HTTP ' . absint( $code ) . '.' );
        }
        return $body;
    }

    private static function request( $path, $method = 'GET', $payload = null ) {
        $options = self::options();
        $base = untrailingslashit( trim( (string) $options['backend_url'] ) );
        if ( ! $base ) {
            return new WP_Error( 'sc_rl_v620_missing_backend_url', 'Python backend URL is missing.' );
        }
        $url = $base . '/' . ltrim( $path, '/' );
        $args = array(
            'method' => strtoupper( $method ),
            'timeout' => max( 10, min( 120, absint( $options['request_timeout'] ) ) ),
            'headers' => array(
                'Accept' => 'application/json',
                'Content-Type' => 'application/json',
                'X-SC-RL-Key' => (string) $options['backend_api_key'],
            ),
        );
        if ( null !== $payload ) {
            $args['body'] = wp_json_encode( $payload );
        }
        $response = wp_remote_request( $url, $args );
        if ( is_wp_error( $response ) ) {
            self::record_status( 'offline', $response->get_error_message() );
            return $response;
        }
        $code = wp_remote_retrieve_response_code( $response );
        $body_text = wp_remote_retrieve_body( $response );
        $body = json_decode( $body_text, true );
        if ( $code < 200 || $code >= 300 ) {
            $detail = is_array( $body ) && isset( $body['detail'] ) ? ( is_string( $body['detail'] ) ? $body['detail'] : wp_json_encode( $body['detail'] ) ) : $body_text;
            $error = new WP_Error( 'sc_rl_v620_backend_http', 'Python backend request failed: ' . sanitize_text_field( $detail ), array( 'status' => $code ) );
            self::record_status( 'offline', $error->get_error_message() );
            return $error;
        }
        if ( ! is_array( $body ) ) {
            return new WP_Error( 'sc_rl_v620_backend_json', 'Python backend returned invalid JSON.' );
        }
        self::record_status( 'online', '' );
        return $body;
    }

    private static function record_status( $state, $error = '' ) {
        $current = get_option( self::STATUS_OPTION, array() );
        $current = is_array( $current ) ? $current : array();
        $current['state'] = sanitize_key( $state );
        $current['last_checked_utc'] = gmdate( 'c' );
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
            return new WP_Error( 'sc_rl_v620_sync_disabled', 'Enable and configure the Python backend before syncing.' );
        }
        $options = self::options();
        $records = self::collect_records( absint( $options['max_records'] ) );
        if ( ! $records ) {
            return new WP_Error( 'sc_rl_v620_no_records', 'No public Sustainable Catalyst records were found for synchronization.' );
        }
        $batch_size = max( 25, min( 250, absint( $options['sync_batch_size'] ) ) );
        $chunks = array_chunk( $records, $batch_size );
        $last = array();
        foreach ( $chunks as $index => $chunk ) {
            $last = self::request( '/v1/knowledge/sync', 'POST', array(
                'records' => $chunk,
                'mode' => 0 === $index ? 'replace' : 'upsert',
                'source_site' => home_url( '/' ),
                'generated_utc' => gmdate( 'c' ),
            ) );
            if ( is_wp_error( $last ) ) {
                return $last;
            }
        }
        $status = array(
            'state' => 'online',
            'last_sync_utc' => gmdate( 'c' ),
            'synced_records' => count( $records ),
            'batches' => count( $chunks ),
            'backend_result' => $last,
        );
        update_option( self::STATUS_OPTION, $status, false );
        return $status;
    }

    public static function collect_records( $max_records = 5000 ) {
        $max_records = max( 100, min( 10000, absint( $max_records ) ) );
        $records = array();
        $seen_urls = array();

        $saved_index = get_option( SC_RL6_Core::INDEX_OPTION, array() );
        if ( is_array( $saved_index ) && ! empty( $saved_index['records'] ) && is_array( $saved_index['records'] ) ) {
            foreach ( $saved_index['records'] as $item ) {
                if ( count( $records ) >= $max_records || empty( $item['title'] ) || empty( $item['url'] ) ) {
                    continue;
                }
                $url = esc_url_raw( $item['url'] );
                if ( isset( $seen_urls[ $url ] ) ) {
                    continue;
                }
                $seen_urls[ $url ] = true;
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

        $post_types = get_post_types( array( 'public' => true ), 'names' );
        $excluded = array( 'attachment', 'revision', 'nav_menu_item', 'wp_block', 'wp_template', 'wp_template_part', 'wp_navigation', 'custom_css', 'customize_changeset' );
        $post_types = array_values( array_diff( $post_types, $excluded ) );
        foreach ( $post_types as $post_type ) {
            if ( count( $records ) >= $max_records ) {
                break;
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
                    if ( ! $record || isset( $seen_urls[ $record['url'] ] ) ) {
                        continue;
                    }
                    $seen_urls[ $record['url'] ] = true;
                    $records[] = $record;
                }
                $paged++;
            } while ( $paged <= (int) $query->max_num_pages );
        }
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
            }
        }
        $options = self::options();
        $status = self::backend_status( true );
        $local_status = get_option( self::STATUS_OPTION, array() );
        ?>
        <div class="wrap">
            <h1>Python Intelligence</h1>
            <p>Research Librarian AI v6.2.0 uses WordPress as the public interface and publishing source while a FastAPI service on Render performs full-library title-aware retrieval, grounded Gemini synthesis, related-title discovery, and short conversational continuity.</p>
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
                <p class="submit"><button class="button button-primary" type="submit" name="sc_rl_v620_save" value="1">Save Python Intelligence Settings</button> <button class="button" type="submit" name="sc_rl_v620_test" value="1">Test Backend Health</button> <button class="button button-secondary" type="submit" name="sc_rl_v620_sync" value="1">Sync Full Knowledge Library</button></p>
            </form>
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
