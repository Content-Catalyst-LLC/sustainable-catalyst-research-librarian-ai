<?php
/**
 * Research Librarian AI v6.3.0 — Durable Knowledge Index, Sync Ledger, and Recovery.
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class SC_RL6_V630_Durable_Index {
    const VERSION = '6.3.0';
    const OPTION_NAME = 'sc_rl_v620_python_options';
    const STATUS_OPTION = 'sc_rl_v620_python_status';
    const SYNC_HOOK = 'sc_rl_v620_python_sync_event';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';
    const SYNC_REPORT_OPTION = 'sc_rl_v621_sync_report';
    const SYNC_HISTORY_OPTION = 'sc_rl_v621_sync_history';
    const LEDGER_OPTION = 'sc_rl_v630_sync_ledger';
    const QUEUE_OPTION = 'sc_rl_v630_incremental_queue';
    const SNAPSHOT_OPTION = 'sc_rl_v630_wordpress_snapshots';
    const RECOVERY_LOG_OPTION = 'sc_rl_v630_recovery_log';
    const RECOVERY_HOOK = 'sc_rl_v630_backend_recovery_event';
    const INCREMENTAL_HOOK = 'sc_rl_v630_incremental_sync_event';

    public static function init() {
        add_action( 'admin_menu', array( __CLASS__, 'register_admin_menu' ), 1010 );
        add_action( 'rest_api_init', array( __CLASS__, 'register_rest_routes' ), 110 );
        add_action( self::SYNC_HOOK, array( __CLASS__, 'run_scheduled_sync' ) );
        add_action( self::RECOVERY_HOOK, array( __CLASS__, 'run_backend_recovery' ) );
        add_action( self::INCREMENTAL_HOOK, array( __CLASS__, 'run_incremental_sync' ) );
        add_action( 'save_post', array( __CLASS__, 'schedule_incremental_sync' ), 30, 3 );
        add_action( 'before_delete_post', array( __CLASS__, 'schedule_sync_after_delete' ), 30, 1 );
        add_action( 'transition_post_status', array( __CLASS__, 'schedule_transition_sync' ), 30, 3 );
        add_filter( 'cron_schedules', array( __CLASS__, 'cron_schedules' ) );
    }

    public static function activate() {
        $existing = get_option( self::OPTION_NAME, array() );
        update_option( self::OPTION_NAME, wp_parse_args( $existing, self::defaults() ), false );
        self::ensure_snapshot_directory();
        self::sync_cron();
    }

    public static function deactivate() {
        wp_clear_scheduled_hook( self::SYNC_HOOK );
        wp_clear_scheduled_hook( self::RECOVERY_HOOK );
        wp_clear_scheduled_hook( self::INCREMENTAL_HOOK );
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
            'auto_recover' => '1',
            'max_wordpress_snapshots' => 5,
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
        if ( ! is_object( $post ) || ! self::is_public_post_type( $post->post_type ) ) {
            return;
        }
        if ( 'publish' === $post->post_status ) {
            self::queue_change( 'upsert', $post_id, 'wp:' . $post->post_type . ':' . absint( $post_id ) );
        }
        self::schedule_single_sync();
    }

    public static function schedule_transition_sync( $new_status, $old_status, $post ) {
        if ( $new_status === $old_status || ! self::enabled() || ! is_object( $post ) || ! self::is_public_post_type( $post->post_type ) ) {
            return;
        }
        $record_id = 'wp:' . $post->post_type . ':' . absint( $post->ID );
        if ( 'publish' === $new_status ) {
            self::queue_change( 'upsert', $post->ID, $record_id );
        } elseif ( 'publish' === $old_status ) {
            self::queue_change( 'delete', $post->ID, $record_id );
        }
        self::schedule_single_sync();
    }

    public static function schedule_sync_after_delete( $post_id ) {
        if ( ! self::enabled() ) {
            return;
        }
        $post = get_post( $post_id );
        $ledger = self::sync_ledger();
        $record_id = '';
        if ( $post && self::is_public_post_type( $post->post_type ) ) {
            $record_id = 'wp:' . $post->post_type . ':' . absint( $post_id );
        } elseif ( ! empty( $ledger['posts'][ absint( $post_id ) ] ) ) {
            $record_id = sanitize_text_field( $ledger['posts'][ absint( $post_id ) ] );
        }
        if ( $record_id ) {
            self::queue_change( 'delete', $post_id, $record_id );
            self::schedule_single_sync();
        }
    }

    private static function schedule_single_sync() {
        if ( ! wp_next_scheduled( self::INCREMENTAL_HOOK ) ) {
            wp_schedule_single_event( time() + 5 * MINUTE_IN_SECONDS, self::INCREMENTAL_HOOK );
        }
    }

    public static function run_scheduled_sync() {
        if ( self::enabled() ) {
            self::sync_all_records();
        }
    }

    public static function run_incremental_sync() {
        if ( self::enabled() && self::incremental_queue() ) {
            self::sync_incremental_queue();
        }
    }

    private static function schedule_full_retry() {
        wp_schedule_single_event( time() + 15 * MINUTE_IN_SECONDS, self::SYNC_HOOK );
    }

    private static function queue_change( $operation, $post_id, $record_id ) {
        $queue = self::incremental_queue();
        $record_id = sanitize_text_field( $record_id );
        if ( ! $record_id ) {
            return;
        }
        $queue[ $record_id ] = array(
            'operation' => 'delete' === $operation ? 'delete' : 'upsert',
            'post_id' => absint( $post_id ),
            'record_id' => $record_id,
            'queued_utc' => gmdate( 'c' ),
            'attempts' => isset( $queue[ $record_id ]['attempts'] ) ? absint( $queue[ $record_id ]['attempts'] ) : 0,
        );
        update_option( self::QUEUE_OPTION, $queue, false );
    }

    public static function incremental_queue() {
        $queue = get_option( self::QUEUE_OPTION, array() );
        return is_array( $queue ) ? $queue : array();
    }

    public static function sync_ledger() {
        $ledger = get_option( self::LEDGER_OPTION, array() );
        return is_array( $ledger ) ? wp_parse_args( $ledger, array( 'schema' => 'sc-rl-sync-ledger/1.0', 'records' => array(), 'posts' => array(), 'checksum' => '', 'index_version' => 0, 'updated_utc' => '' ) ) : array( 'schema' => 'sc-rl-sync-ledger/1.0', 'records' => array(), 'posts' => array(), 'checksum' => '', 'index_version' => 0, 'updated_utc' => '' );
    }

    private static function save_ledger( $records, $backend_result = array() ) {
        $hashes = array();
        $posts = array();
        foreach ( $records as $record ) {
            if ( empty( $record['id'] ) ) {
                continue;
            }
            $hashes[ $record['id'] ] = sanitize_text_field( isset( $record['content_hash'] ) ? $record['content_hash'] : self::record_content_hash( $record ) );
            if ( ! empty( $record['metadata']['post_id'] ) ) {
                $posts[ absint( $record['metadata']['post_id'] ) ] = sanitize_text_field( $record['id'] );
            }
        }
        ksort( $hashes );
        update_option( self::LEDGER_OPTION, array(
            'schema' => 'sc-rl-sync-ledger/1.0',
            'records' => $hashes,
            'posts' => $posts,
            'checksum' => sanitize_text_field( isset( $backend_result['checksum'] ) ? $backend_result['checksum'] : self::ledger_checksum( $hashes ) ),
            'index_version' => absint( isset( $backend_result['index_version'] ) ? $backend_result['index_version'] : 0 ),
            'updated_utc' => gmdate( 'c' ),
        ), false );
    }

    private static function ledger_checksum( $hashes ) {
        ksort( $hashes );
        $lines = array();
        foreach ( $hashes as $id => $hash ) {
            $lines[] = $id . ':' . $hash;
        }
        return hash( 'sha256', implode( "
", $lines ) . ( $lines ? "
" : '' ) );
    }

    private static function record_content_hash( $record ) {
        $copy = is_array( $record ) ? $record : array();
        unset( $copy['embedding'], $copy['content_hash'] );
        return hash( 'sha256', wp_json_encode( $copy, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) );
    }

    public static function sync_incremental_queue() {
        if ( ! self::enabled() ) {
            return new WP_Error( 'sc_rl_v630_sync_disabled', 'Enable and configure the Python backend before syncing.', array( 'status' => 400, 'error_type' => 'backend-not-configured' ) );
        }
        $queue = self::incremental_queue();
        if ( ! $queue ) {
            return array( 'ok' => true, 'state' => 'empty', 'message' => 'No incremental changes are queued.' );
        }
        $records = array();
        $deleted_ids = array();
        foreach ( $queue as $record_id => $item ) {
            if ( 'delete' === ( $item['operation'] ?? '' ) ) {
                $deleted_ids[] = sanitize_text_field( $record_id );
                continue;
            }
            $record = self::build_post_record( absint( $item['post_id'] ?? 0 ) );
            if ( $record ) {
                $records[] = $record;
            } else {
                $deleted_ids[] = sanitize_text_field( $record_id );
            }
        }
        $job_id = 'incremental-' . gmdate( 'Ymd-His' ) . '-' . wp_generate_password( 6, false, false );
        $response = self::request( '/v1/knowledge/sync', 'POST', array(
            'records' => $records,
            'deleted_ids' => array_values( array_unique( $deleted_ids ) ),
            'mode' => $records ? 'upsert' : 'delete',
            'source_site' => home_url( '/' ),
            'generated_utc' => gmdate( 'c' ),
            'job_id' => $job_id,
            'batch_index' => 1,
            'batch_count' => 1,
            'reason' => 'wordpress-incremental',
        ) );
        if ( is_wp_error( $response ) ) {
            foreach ( $queue as &$item ) {
                $item['attempts'] = absint( $item['attempts'] ?? 0 ) + 1;
                $item['last_error'] = $response->get_error_message();
            }
            unset( $item );
            update_option( self::QUEUE_OPTION, $queue, false );
            self::schedule_single_sync();
            return $response;
        }
        update_option( self::QUEUE_OPTION, array(), false );
        $ledger = self::sync_ledger();
        foreach ( $deleted_ids as $id ) {
            unset( $ledger['records'][ $id ] );
            foreach ( $ledger['posts'] as $post_id => $mapped_id ) {
                if ( $mapped_id === $id ) {
                    unset( $ledger['posts'][ $post_id ] );
                }
            }
        }
        foreach ( $records as $record ) {
            $ledger['records'][ $record['id'] ] = $record['content_hash'];
            if ( ! empty( $record['metadata']['post_id'] ) ) {
                $ledger['posts'][ absint( $record['metadata']['post_id'] ) ] = $record['id'];
            }
        }
        $ledger['checksum'] = sanitize_text_field( $response['checksum'] ?? self::ledger_checksum( $ledger['records'] ) );
        $ledger['index_version'] = absint( $response['index_version'] ?? 0 );
        $ledger['updated_utc'] = gmdate( 'c' );
        update_option( self::LEDGER_OPTION, $ledger, false );
        return array( 'ok' => true, 'job_id' => $job_id, 'records' => count( $records ), 'deleted' => count( $deleted_ids ), 'backend_result' => $response );
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
        register_rest_route( self::REST_NAMESPACE, '/python/manifest', array(
            'methods' => WP_REST_Server::READABLE,
            'callback' => array( __CLASS__, 'handle_manifest' ),
            'permission_callback' => array( __CLASS__, 'can_manage' ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/python/snapshots', array(
            'methods' => WP_REST_Server::READABLE,
            'callback' => array( __CLASS__, 'handle_snapshots' ),
            'permission_callback' => array( __CLASS__, 'can_manage' ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/python/recover', array(
            'methods' => WP_REST_Server::CREATABLE,
            'callback' => array( __CLASS__, 'handle_recover' ),
            'permission_callback' => array( __CLASS__, 'can_manage' ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/python/rollback', array(
            'methods' => WP_REST_Server::CREATABLE,
            'callback' => array( __CLASS__, 'handle_rollback' ),
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
                'recovery_available' => (bool) self::latest_wordpress_snapshot(),
            ), 200 );
        }
        if ( self::should_schedule_recovery( $status ) ) {
            self::schedule_backend_recovery();
            $status['recovery_scheduled'] = true;
            $status['detail'] = 'The runtime index is empty. WordPress scheduled automatic rehydration from the latest verified snapshot.';
        }
        unset( $status['last_ai_error'] );
        $status['enabled'] = self::enabled();
        $status['fallback_active'] = true;
        $status['wordpress_snapshot'] = self::snapshot_manifest_summary( self::latest_wordpress_snapshot() );
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

    public static function handle_manifest() {
        $manifest = self::request( '/v1/knowledge/manifest', 'GET' );
        return is_wp_error( $manifest ) ? $manifest : new WP_REST_Response( $manifest, 200 );
    }

    public static function handle_snapshots() {
        $backend = self::request( '/v1/knowledge/snapshots', 'GET' );
        return new WP_REST_Response( array(
            'version' => self::VERSION,
            'wordpress_snapshots' => self::wordpress_snapshots(),
            'backend' => is_wp_error( $backend ) ? self::public_error_snapshot( $backend ) : $backend,
        ), 200 );
    }

    public static function handle_recover() {
        $result = self::recover_backend_from_snapshot( 'manual-rest' );
        return is_wp_error( $result ) ? $result : new WP_REST_Response( $result, 200 );
    }

    public static function handle_rollback( WP_REST_Request $request ) {
        $snapshot_id = sanitize_text_field( $request->get_param( 'snapshot_id' ) );
        if ( ! $snapshot_id ) {
            return new WP_Error( 'sc_rl_v630_missing_snapshot', 'Choose a backend runtime snapshot to roll back to.', array( 'status' => 400 ) );
        }
        $result = self::request( '/v1/knowledge/rollback', 'POST', array( 'snapshot_id' => $snapshot_id ) );
        if ( is_wp_error( $result ) ) {
            return $result;
        }
        self::append_recovery_log( 'backend-rollback', array( 'snapshot_id' => $snapshot_id, 'result' => $result ) );
        return new WP_REST_Response( $result, 200 );
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
            'schema' => 'sc-research-librarian-route-note/6.3.0',
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
            return new WP_Error( 'sc_rl_v621_not_configured', 'The Python backend is not configured.', array( 'status' => 503, 'error_type' => 'backend-not-configured' ) );
        }
        $status = self::request( '/status', 'GET' );
        if ( is_wp_error( $status ) ) {
            return $status;
        }
        if ( empty( $status['indexed_records'] ) ) {
            $status['state'] = 'needs-sync';
            $status['label'] = 'Knowledge Index Needs Sync';
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
            return new WP_Error( 'sc_rl_v630_sync_disabled', 'Enable and configure the Python backend before syncing.', array( 'status' => 400, 'error_type' => 'backend-not-configured' ) );
        }
        $options = self::options();
        $collection = array();
        $records = self::collect_records( absint( $options['max_records'] ), $collection );
        $job_id = 'sync-' . gmdate( 'Ymd-His' ) . '-' . wp_generate_password( 8, false, false );
        $ledger = self::sync_ledger();
        $current_ids = array();
        foreach ( $records as $record ) {
            if ( ! empty( $record['id'] ) ) {
                $current_ids[ $record['id'] ] = true;
            }
        }
        $deleted_ids = array_values( array_diff( array_keys( $ledger['records'] ), array_keys( $current_ids ) ) );
        $report = array_merge( array(
            'version' => self::VERSION,
            'schema' => 'sc-rl-sync-report/6.3.0',
            'job_id' => $job_id,
            'state' => 'running',
            'mode' => 'transactional-replace',
            'started_utc' => gmdate( 'c' ),
            'completed_utc' => '',
            'synced_records' => 0,
            'accepted_records' => 0,
            'rejected_records' => 0,
            'deleted_records' => count( $deleted_ids ),
            'batches' => array(),
            'source_site' => home_url( '/' ),
            'retry_scheduled' => false,
        ), is_array( $collection ) ? $collection : array() );
        self::save_sync_report( $report );
        if ( ! $records ) {
            $report['state'] = 'failed';
            $report['completed_utc'] = gmdate( 'c' );
            $report['error'] = 'No public Sustainable Catalyst records were found for synchronization.';
            self::save_sync_report( $report );
            return new WP_Error( 'sc_rl_v630_no_records', $report['error'], array( 'status' => 400, 'error_type' => 'index-empty', 'sync_report' => $report ) );
        }
        $snapshot = self::create_wordpress_snapshot( $records, 'full-sync:' . $job_id );
        if ( is_wp_error( $snapshot ) ) {
            $report['snapshot_warning'] = $snapshot->get_error_message();
        } else {
            $report['wordpress_snapshot'] = self::snapshot_manifest_summary( $snapshot );
        }
        $batch_size = max( 25, min( 250, absint( $options['sync_batch_size'] ) ) );
        $chunks = array_chunk( $records, $batch_size );
        $last = array();
        foreach ( $chunks as $index => $chunk ) {
            $is_final = ( $index + 1 ) === count( $chunks );
            $batch = array(
                'batch' => $index + 1,
                'batch_count' => count( $chunks ),
                'mode' => 'replace',
                'records_sent' => count( $chunk ),
                'deleted_ids_sent' => $is_final ? count( $deleted_ids ) : 0,
                'started_utc' => gmdate( 'c' ),
                'state' => 'running',
            );
            $last = self::request( '/v1/knowledge/sync', 'POST', array(
                'records' => $chunk,
                'deleted_ids' => $is_final ? $deleted_ids : array(),
                'mode' => 'replace',
                'source_site' => home_url( '/' ),
                'generated_utc' => gmdate( 'c' ),
                'job_id' => $job_id,
                'batch_index' => $index + 1,
                'batch_count' => count( $chunks ),
                'reason' => 'wordpress-full-sync',
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
                $report['retry_scheduled'] = true;
                self::save_sync_report( $report );
                self::schedule_full_retry();
                return new WP_Error( $last->get_error_code(), $last->get_error_message(), array_merge( (array) $last->get_error_data(), array( 'sync_report' => $report ) ) );
            }
            $batch['state'] = ! empty( $last['committed'] ) ? 'committed' : 'staged';
            $batch['completed_utc'] = gmdate( 'c' );
            $batch['accepted_records'] = absint( isset( $last['received'] ) ? $last['received'] : count( $chunk ) );
            $batch['backend_total_records'] = absint( isset( $last['total_records'] ) ? $last['total_records'] : 0 );
            $batch['backend_state'] = sanitize_key( isset( $last['state'] ) ? $last['state'] : '' );
            $batch['staged_records'] = absint( isset( $last['staged_records'] ) ? $last['staged_records'] : 0 );
            $report['batches'][] = $batch;
            $report['synced_records'] += count( $chunk );
            self::save_sync_report( $report );
        }
        if ( empty( $last['committed'] ) ) {
            $report['state'] = 'failed';
            $report['completed_utc'] = gmdate( 'c' );
            $report['error'] = 'The backend received all batches but did not commit the staged transaction.';
            $report['retry_scheduled'] = true;
            self::save_sync_report( $report );
            self::schedule_full_retry();
            return new WP_Error( 'sc_rl_v630_not_committed', $report['error'], array( 'status' => 502, 'sync_report' => $report ) );
        }
        $report['state'] = 'completed';
        $report['completed_utc'] = gmdate( 'c' );
        $report['batch_count'] = count( $chunks );
        $report['accepted_records'] = absint( isset( $last['accepted'] ) ? $last['accepted'] : count( $records ) );
        $report['rejected_records'] = absint( isset( $last['rejected'] ) ? $last['rejected'] : 0 );
        $report['inserted_records'] = absint( isset( $last['inserted'] ) ? $last['inserted'] : 0 );
        $report['updated_records'] = absint( isset( $last['updated'] ) ? $last['updated'] : 0 );
        $report['unchanged_records'] = absint( isset( $last['unchanged'] ) ? $last['unchanged'] : 0 );
        $report['backend_deleted_records'] = absint( isset( $last['deleted'] ) ? $last['deleted'] : 0 );
        $report['index_version'] = absint( isset( $last['index_version'] ) ? $last['index_version'] : 0 );
        $report['checksum'] = sanitize_text_field( isset( $last['checksum'] ) ? $last['checksum'] : '' );
        $report['backend_result'] = $last;
        self::save_sync_report( $report );
        self::save_ledger( $records, $last );
        update_option( self::QUEUE_OPTION, array(), false );
        $status = array(
            'state' => 'online',
            'last_sync_utc' => $report['completed_utc'],
            'synced_records' => count( $records ),
            'accepted_records' => $report['accepted_records'],
            'rejected_records' => $report['rejected_records'],
            'batches' => count( $chunks ),
            'job_id' => $job_id,
            'index_version' => $report['index_version'],
            'checksum' => $report['checksum'],
            'storage_engine' => 'sqlite',
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

        // v6.3.0 continues to index canonical published WordPress records first. The older
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
                $legacy_index = count( $records ) - 1;
                $records[ $legacy_index ]['content_hash'] = self::record_content_hash( $records[ $legacy_index ] );
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
        $record = array(
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
        $record['content_hash'] = self::record_content_hash( $record );
        return $record;
    }

    private static function snapshot_directory() {
        $uploads = wp_upload_dir();
        if ( ! empty( $uploads['error'] ) || empty( $uploads['basedir'] ) ) {
            return '';
        }
        return trailingslashit( $uploads['basedir'] ) . 'sc-research-librarian-private/index-snapshots';
    }

    private static function ensure_snapshot_directory() {
        $directory = self::snapshot_directory();
        if ( ! $directory ) {
            return new WP_Error( 'sc_rl_v630_uploads_unavailable', 'WordPress uploads storage is unavailable for the canonical knowledge snapshot.' );
        }
        if ( ! wp_mkdir_p( $directory ) ) {
            return new WP_Error( 'sc_rl_v630_snapshot_directory', 'The private Research Librarian snapshot directory could not be created.' );
        }
        $protections = array(
            '.htaccess' => "Order deny,allow\nDeny from all\n<IfModule mod_authz_core.c>\nRequire all denied\n</IfModule>\n",
            'index.php' => "<?php\n// Silence is golden.\n",
            'web.config' => "<?xml version=\"1.0\" encoding=\"UTF-8\"?><configuration><system.webServer><security><authorization><remove users=\"*\" roles=\"\" verbs=\"\"/><add accessType=\"Deny\" users=\"*\"/></authorization></security></system.webServer></configuration>",
        );
        foreach ( $protections as $filename => $contents ) {
            $path = trailingslashit( $directory ) . $filename;
            if ( ! file_exists( $path ) ) {
                @file_put_contents( $path, $contents, LOCK_EX );
            }
        }
        return $directory;
    }

    public static function create_wordpress_snapshot( $records, $reason = 'manual' ) {
        $directory = self::ensure_snapshot_directory();
        if ( is_wp_error( $directory ) ) {
            return $directory;
        }
        $records = is_array( $records ) ? array_values( $records ) : array();
        $hashes = array();
        foreach ( $records as &$record ) {
            if ( empty( $record['content_hash'] ) ) {
                $record['content_hash'] = self::record_content_hash( $record );
            }
            if ( ! empty( $record['id'] ) ) {
                $hashes[ $record['id'] ] = $record['content_hash'];
            }
        }
        unset( $record );
        $checksum = self::ledger_checksum( $hashes );
        $created = gmdate( 'c' );
        $snapshot_id = 'wp-' . gmdate( 'Ymd-His' ) . '-' . wp_generate_password( 8, false, false );
        $payload = array(
            'schema' => 'sc-research-librarian-wordpress-snapshot/3.0',
            'snapshot_id' => $snapshot_id,
            'created_utc' => $created,
            'reason' => sanitize_text_field( $reason ),
            'source_site' => home_url( '/' ),
            'manifest' => array(
                'record_count' => count( $records ),
                'checksum' => $checksum,
                'plugin_version' => self::VERSION,
                'generated_by' => 'wordpress-canonical-source',
            ),
            'records' => $records,
        );
        $json = wp_json_encode( $payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
        if ( ! is_string( $json ) || '' === $json ) {
            return new WP_Error( 'sc_rl_v630_snapshot_encode', 'The canonical knowledge snapshot could not be encoded.' );
        }
        $compressed = function_exists( 'gzencode' ) ? gzencode( $json, 6 ) : $json;
        $extension = function_exists( 'gzencode' ) ? '.json.gz' : '.json';
        $filename = sanitize_file_name( $snapshot_id . $extension );
        $path = trailingslashit( $directory ) . $filename;
        $written = @file_put_contents( $path, $compressed, LOCK_EX );
        if ( false === $written ) {
            return new WP_Error( 'sc_rl_v630_snapshot_write', 'The canonical knowledge snapshot could not be written to private WordPress storage.' );
        }
        $manifest = array(
            'snapshot_id' => $snapshot_id,
            'filename' => $filename,
            'created_utc' => $created,
            'reason' => sanitize_text_field( $reason ),
            'record_count' => count( $records ),
            'checksum' => $checksum,
            'file_sha256' => hash_file( 'sha256', $path ),
            'size_bytes' => absint( filesize( $path ) ),
            'compressed' => '.json.gz' === $extension,
            'schema' => 'sc-research-librarian-wordpress-snapshot/3.0',
        );
        $snapshots = self::wordpress_snapshots();
        array_unshift( $snapshots, $manifest );
        $limit = max( 1, min( 20, absint( self::options()['max_wordpress_snapshots'] ) ) );
        $removed = array_slice( $snapshots, $limit );
        $snapshots = array_slice( $snapshots, 0, $limit );
        update_option( self::SNAPSHOT_OPTION, $snapshots, false );
        foreach ( $removed as $old ) {
            if ( ! empty( $old['filename'] ) ) {
                $old_path = trailingslashit( $directory ) . basename( $old['filename'] );
                if ( is_file( $old_path ) ) {
                    @unlink( $old_path );
                }
            }
        }
        return $manifest;
    }

    public static function wordpress_snapshots() {
        $snapshots = get_option( self::SNAPSHOT_OPTION, array() );
        return is_array( $snapshots ) ? array_values( $snapshots ) : array();
    }

    public static function latest_wordpress_snapshot() {
        $snapshots = self::wordpress_snapshots();
        return $snapshots ? $snapshots[0] : array();
    }

    private static function snapshot_manifest_summary( $snapshot ) {
        if ( ! is_array( $snapshot ) || empty( $snapshot['snapshot_id'] ) ) {
            return array();
        }
        return array(
            'snapshot_id' => sanitize_text_field( $snapshot['snapshot_id'] ),
            'created_utc' => sanitize_text_field( $snapshot['created_utc'] ?? '' ),
            'record_count' => absint( $snapshot['record_count'] ?? 0 ),
            'checksum' => sanitize_text_field( $snapshot['checksum'] ?? '' ),
            'size_bytes' => absint( $snapshot['size_bytes'] ?? 0 ),
            'reason' => sanitize_text_field( $snapshot['reason'] ?? '' ),
        );
    }

    private static function read_wordpress_snapshot( $manifest = array() ) {
        $manifest = $manifest ? $manifest : self::latest_wordpress_snapshot();
        if ( empty( $manifest['filename'] ) ) {
            return new WP_Error( 'sc_rl_v630_snapshot_missing', 'No canonical WordPress knowledge snapshot is available.' );
        }
        $directory = self::ensure_snapshot_directory();
        if ( is_wp_error( $directory ) ) {
            return $directory;
        }
        $path = trailingslashit( $directory ) . basename( $manifest['filename'] );
        if ( ! is_file( $path ) ) {
            return new WP_Error( 'sc_rl_v630_snapshot_file_missing', 'The canonical WordPress snapshot manifest exists, but its private file is missing.' );
        }
        if ( ! empty( $manifest['file_sha256'] ) && ! hash_equals( (string) $manifest['file_sha256'], (string) hash_file( 'sha256', $path ) ) ) {
            return new WP_Error( 'sc_rl_v630_snapshot_integrity', 'The canonical WordPress snapshot failed its file-integrity check.' );
        }
        $contents = file_get_contents( $path );
        if ( false === $contents ) {
            return new WP_Error( 'sc_rl_v630_snapshot_read', 'The canonical WordPress snapshot could not be read.' );
        }
        if ( ! empty( $manifest['compressed'] ) ) {
            if ( ! function_exists( 'gzdecode' ) ) {
                return new WP_Error( 'sc_rl_v630_gzip_unavailable', 'PHP gzip support is required to read the canonical knowledge snapshot.' );
            }
            $contents = gzdecode( $contents );
        }
        $payload = json_decode( (string) $contents, true );
        if ( ! is_array( $payload ) || empty( $payload['records'] ) || ! is_array( $payload['records'] ) ) {
            return new WP_Error( 'sc_rl_v630_snapshot_invalid', 'The canonical WordPress snapshot contains invalid JSON or no records.' );
        }
        $hashes = array();
        foreach ( $payload['records'] as $record ) {
            if ( ! empty( $record['id'] ) ) {
                $hashes[ $record['id'] ] = ! empty( $record['content_hash'] ) ? $record['content_hash'] : self::record_content_hash( $record );
            }
        }
        $calculated = self::ledger_checksum( $hashes );
        $expected = sanitize_text_field( $payload['manifest']['checksum'] ?? $manifest['checksum'] ?? '' );
        if ( $expected && ! hash_equals( $expected, $calculated ) ) {
            return new WP_Error( 'sc_rl_v630_snapshot_checksum', 'The canonical WordPress snapshot failed its record checksum validation.' );
        }
        return $payload;
    }

    private static function should_schedule_recovery( $status ) {
        $options = self::options();
        return '1' === (string) $options['auto_recover']
            && is_array( $status )
            && 0 === absint( $status['indexed_records'] ?? 0 )
            && ! empty( self::latest_wordpress_snapshot() );
    }

    private static function schedule_backend_recovery() {
        if ( ! wp_next_scheduled( self::RECOVERY_HOOK ) ) {
            wp_schedule_single_event( time() + 10, self::RECOVERY_HOOK );
        }
    }

    public static function run_backend_recovery() {
        if ( self::enabled() ) {
            self::recover_backend_from_snapshot( 'automatic-cold-start' );
        }
    }

    public static function recover_backend_from_snapshot( $trigger = 'manual' ) {
        if ( ! self::enabled() ) {
            return new WP_Error( 'sc_rl_v630_recovery_disabled', 'Enable and configure the Python backend before recovery.', array( 'status' => 400 ) );
        }
        $snapshot = self::read_wordpress_snapshot();
        if ( is_wp_error( $snapshot ) ) {
            self::append_recovery_log( 'recovery-failed', array( 'trigger' => $trigger, 'error' => $snapshot->get_error_message() ) );
            return $snapshot;
        }
        $records = $snapshot['records'];
        $options = self::options();
        $chunks = array_chunk( $records, max( 25, min( 250, absint( $options['sync_batch_size'] ) ) ) );
        $job_id = 'recovery-' . gmdate( 'Ymd-His' ) . '-' . wp_generate_password( 8, false, false );
        $last = array();
        foreach ( $chunks as $index => $chunk ) {
            $last = self::request( '/v1/knowledge/sync', 'POST', array(
                'records' => $chunk,
                'deleted_ids' => array(),
                'mode' => 'replace',
                'source_site' => home_url( '/' ),
                'generated_utc' => gmdate( 'c' ),
                'job_id' => $job_id,
                'batch_index' => $index + 1,
                'batch_count' => count( $chunks ),
                'reason' => 'wordpress-snapshot-recovery:' . sanitize_key( $trigger ),
            ) );
            if ( is_wp_error( $last ) ) {
                self::append_recovery_log( 'recovery-failed', array( 'trigger' => $trigger, 'job_id' => $job_id, 'batch' => $index + 1, 'error' => $last->get_error_message() ) );
                self::schedule_backend_recovery();
                return $last;
            }
        }
        if ( empty( $last['committed'] ) ) {
            $error = new WP_Error( 'sc_rl_v630_recovery_not_committed', 'The backend staged the recovery snapshot but did not commit it.', array( 'status' => 502 ) );
            self::append_recovery_log( 'recovery-failed', array( 'trigger' => $trigger, 'job_id' => $job_id, 'error' => $error->get_error_message() ) );
            return $error;
        }
        self::save_ledger( $records, $last );
        $result = array(
            'ok' => true,
            'version' => self::VERSION,
            'state' => 'recovered',
            'trigger' => sanitize_key( $trigger ),
            'job_id' => $job_id,
            'snapshot' => self::snapshot_manifest_summary( self::latest_wordpress_snapshot() ),
            'backend_result' => $last,
            'recovered_utc' => gmdate( 'c' ),
        );
        self::append_recovery_log( 'recovery-completed', $result );
        return $result;
    }

    private static function append_recovery_log( $event, $details = array() ) {
        $rows = get_option( self::RECOVERY_LOG_OPTION, array() );
        $rows = is_array( $rows ) ? $rows : array();
        array_unshift( $rows, array(
            'event' => sanitize_key( $event ),
            'created_utc' => gmdate( 'c' ),
            'details' => is_array( $details ) ? $details : array(),
        ) );
        update_option( self::RECOVERY_LOG_OPTION, array_slice( $rows, 0, 50 ), false );
    }

    public static function recovery_log() {
        $rows = get_option( self::RECOVERY_LOG_OPTION, array() );
        return is_array( $rows ) ? $rows : array();
    }

    public static function diagnostics_snapshot() {
        $options = self::options();
        $status = self::backend_status( true );
        $stored = get_option( self::STATUS_OPTION, array() );
        $next = wp_next_scheduled( self::SYNC_HOOK );
        $recovery_next = wp_next_scheduled( self::RECOVERY_HOOK );
        $report = self::latest_sync_report();
        $manifest = is_wp_error( $status ) ? $status : self::request( '/v1/knowledge/manifest', 'GET' );
        $snapshot = self::latest_wordpress_snapshot();
        $ledger = self::sync_ledger();
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
                'auto_recover' => '1' === (string) $options['auto_recover'],
                'max_wordpress_snapshots' => absint( $options['max_wordpress_snapshots'] ),
            ),
            'cron' => array(
                'scheduled' => (bool) $next,
                'next_run_utc' => $next ? gmdate( 'c', $next ) : '',
                'hook' => self::SYNC_HOOK,
                'recovery_scheduled' => (bool) $recovery_next,
                'recovery_next_run_utc' => $recovery_next ? gmdate( 'c', $recovery_next ) : '',
                'recovery_hook' => self::RECOVERY_HOOK,
                'wp_cron_disabled' => defined( 'DISABLE_WP_CRON' ) && DISABLE_WP_CRON,
            ),
            'backend' => is_wp_error( $status ) ? self::public_error_snapshot( $status ) : $status,
            'backend_manifest' => is_wp_error( $manifest ) ? self::public_error_snapshot( $manifest ) : $manifest,
            'wordpress_snapshot' => self::snapshot_manifest_summary( $snapshot ),
            'wordpress_snapshot_count' => count( self::wordpress_snapshots() ),
            'sync_ledger' => array(
                'record_count' => count( $ledger['records'] ),
                'checksum' => sanitize_text_field( $ledger['checksum'] ),
                'index_version' => absint( $ledger['index_version'] ),
                'updated_utc' => sanitize_text_field( $ledger['updated_utc'] ),
            ),
            'incremental_queue' => array(
                'count' => count( self::incremental_queue() ),
                'records' => array_values( self::incremental_queue() ),
            ),
            'recovery_log' => array_slice( self::recovery_log(), 0, 10 ),
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
            $input = isset( $_POST['sc_rl_v620'] ) && is_array( $_POST['sc_rl_v620'] ) ? wp_unslash( $_POST['sc_rl_v620'] ) : array();
            if ( isset( $_POST['sc_rl_v620_save'] ) ) {
                self::save_options( $input );
                self::sync_cron();
                $notice = 'Python intelligence and durable-index settings saved.';
            } elseif ( isset( $_POST['sc_rl_v620_test'] ) ) {
                self::save_options( $input );
                $test = self::test_backend();
                if ( is_wp_error( $test ) ) {
                    $notice_type = 'error';
                    $notice = $test->get_error_message();
                } else {
                    $notice = 'Python backend health check succeeded. Version ' . sanitize_text_field( isset( $test['version'] ) ? $test['version'] : self::VERSION ) . '.';
                    if ( self::should_schedule_recovery( $test ) ) {
                        self::schedule_backend_recovery();
                        $notice .= ' The runtime index is empty, so automatic snapshot recovery was scheduled.';
                    }
                }
            } elseif ( isset( $_POST['sc_rl_v620_sync'] ) ) {
                self::save_options( $input );
                $sync = self::sync_all_records();
                if ( is_wp_error( $sync ) ) {
                    $notice_type = 'error';
                    $notice = $sync->get_error_message();
                } else {
                    $notice = 'Transactional knowledge sync committed: ' . absint( $sync['synced_records'] ) . ' records across ' . absint( $sync['batches'] ) . ' batches.';
                }
            } elseif ( isset( $_POST['sc_rl_v630_sync_incremental'] ) ) {
                $sync = self::sync_incremental_queue();
                if ( is_wp_error( $sync ) ) {
                    $notice_type = 'error';
                    $notice = $sync->get_error_message();
                } else {
                    $notice = 'Incremental queue processed: ' . absint( $sync['records'] ?? 0 ) . ' upsert(s), ' . absint( $sync['deleted'] ?? 0 ) . ' deletion(s).';
                }
            } elseif ( isset( $_POST['sc_rl_v630_create_snapshot'] ) ) {
                $collection = array();
                $records = self::collect_records( absint( self::options()['max_records'] ), $collection );
                $snapshot = self::create_wordpress_snapshot( $records, 'manual-admin' );
                if ( is_wp_error( $snapshot ) ) {
                    $notice_type = 'error';
                    $notice = $snapshot->get_error_message();
                } else {
                    $notice = 'Canonical WordPress snapshot created: ' . sanitize_text_field( $snapshot['snapshot_id'] );
                }
            } elseif ( isset( $_POST['sc_rl_v630_recover'] ) ) {
                $recovery = self::recover_backend_from_snapshot( 'manual-admin' );
                if ( is_wp_error( $recovery ) ) {
                    $notice_type = 'error';
                    $notice = $recovery->get_error_message();
                } else {
                    $notice = 'Backend runtime index recovered from the canonical WordPress snapshot.';
                }
            } elseif ( isset( $_POST['sc_rl_v630_rollback'] ) ) {
                $snapshot_id = sanitize_text_field( isset( $_POST['sc_rl_v630_snapshot_id'] ) ? wp_unslash( $_POST['sc_rl_v630_snapshot_id'] ) : '' );
                $rollback = $snapshot_id ? self::request( '/v1/knowledge/rollback', 'POST', array( 'snapshot_id' => $snapshot_id ) ) : new WP_Error( 'sc_rl_v630_missing_snapshot', 'Choose a backend runtime snapshot first.' );
                if ( is_wp_error( $rollback ) ) {
                    $notice_type = 'error';
                    $notice = $rollback->get_error_message();
                } else {
                    self::append_recovery_log( 'backend-rollback', array( 'snapshot_id' => $snapshot_id, 'result' => $rollback ) );
                    $notice = 'Backend runtime index rolled back to ' . $snapshot_id . '.';
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
        $wp_snapshots = self::wordpress_snapshots();
        $backend_snapshots_response = self::request( '/v1/knowledge/snapshots', 'GET' );
        $backend_snapshots = ! is_wp_error( $backend_snapshots_response ) && ! empty( $backend_snapshots_response['snapshots'] ) && is_array( $backend_snapshots_response['snapshots'] ) ? $backend_snapshots_response['snapshots'] : array();
        $ledger = self::sync_ledger();
        $queue = self::incremental_queue();
        ?>
        <div class="wrap">
            <h1>Python Intelligence and Durable Index</h1>
            <p>Research Librarian AI v6.3.0 keeps WordPress as the canonical publishing and recovery source while FastAPI uses a transactional SQLite runtime index for title-aware retrieval and grounded Gemini synthesis. The design remains compatible with free Render infrastructure.</p>
            <?php if ( $notice ) : ?><div class="notice notice-<?php echo esc_attr( $notice_type ); ?> is-dismissible"><p><?php echo esc_html( $notice ); ?></p></div><?php endif; ?>

            <div class="sc-rl-admin-grid">
                <article class="sc-rl-admin-card" data-state="<?php echo esc_attr( is_wp_error( $status ) ? 'offline' : ( $status['state'] ?? 'unknown' ) ); ?>">
                    <h2><?php echo esc_html( is_wp_error( $status ) ? 'Backend unavailable' : ( $status['label'] ?? 'Backend status' ) ); ?></h2>
                    <span class="sc-rl-admin-metric"><?php echo esc_html( is_wp_error( $status ) ? 'Offline' : 'v' . ( $status['version'] ?? self::VERSION ) ); ?></span>
                    <p><?php echo esc_html( is_wp_error( $status ) ? $status->get_error_message() : ( ( $status['storage_engine'] ?? 'sqlite' ) . ' · index v' . absint( $status['index_version'] ?? 0 ) ) ); ?></p>
                </article>
                <article class="sc-rl-admin-card"><h2>Indexed records</h2><span class="sc-rl-admin-metric"><?php echo esc_html( is_wp_error( $status ) ? 0 : absint( $status['indexed_records'] ?? 0 ) ); ?></span><p><?php echo esc_html( is_wp_error( $status ) ? 'Run a full sync or recovery.' : absint( $status['indexed_titles'] ?? 0 ) . ' distinct titles' ); ?></p></article>
                <article class="sc-rl-admin-card"><h2>Canonical snapshots</h2><span class="sc-rl-admin-metric"><?php echo esc_html( count( $wp_snapshots ) ); ?></span><p><?php echo esc_html( $wp_snapshots ? ( $wp_snapshots[0]['record_count'] . ' records · ' . $wp_snapshots[0]['created_utc'] ) : 'Create a snapshot or run a full sync.' ); ?></p></article>
                <article class="sc-rl-admin-card"><h2>Incremental queue</h2><span class="sc-rl-admin-metric"><?php echo esc_html( count( $queue ) ); ?></span><p><?php echo esc_html( count( $ledger['records'] ) . ' records in the WordPress sync ledger' ); ?></p></article>
            </div>

            <form method="post">
                <?php wp_nonce_field( 'sc_rl_v620_admin_action' ); ?>
                <table class="form-table sc-rl-provider-table" role="presentation">
                    <tr><th>Enable Python intelligence</th><td><input type="hidden" name="sc_rl_v620[enabled]" value="0"><label><input type="checkbox" name="sc_rl_v620[enabled]" value="1" <?php checked( $options['enabled'], '1' ); ?>> Use the Render/FastAPI backend for public answers and title-aware retrieval</label></td></tr>
                    <tr><th><label for="sc-rl-v620-url">Backend URL</label></th><td><input id="sc-rl-v620-url" class="regular-text" type="url" name="sc_rl_v620[backend_url]" value="<?php echo esc_attr( $options['backend_url'] ); ?>" placeholder="https://sustainable-catalyst-research-librarian-ai.onrender.com"><p class="description">Do not add a trailing endpoint path.</p></td></tr>
                    <tr><th><label for="sc-rl-v620-key">Shared integration key</label></th><td><input id="sc-rl-v620-key" class="regular-text" type="password" name="sc_rl_v620[backend_api_key_new]" value="" autocomplete="new-password" placeholder="<?php echo esc_attr( $options['backend_api_key'] ? 'Key saved. Paste only to replace.' : 'Paste SC_RL_BACKEND_API_KEY' ); ?>"><p class="description">Use the same long random value in Render and WordPress. The key is sent only server-to-server.</p><?php if ( $options['backend_api_key'] ) : ?><label><input type="checkbox" name="sc_rl_v620[backend_api_key_clear]" value="1"> Clear saved integration key</label><?php endif; ?></td></tr>
                    <tr><th><label for="sc-rl-v620-timeout">Request timeout</label></th><td><input id="sc-rl-v620-timeout" type="number" min="10" max="120" name="sc_rl_v620[request_timeout]" value="<?php echo esc_attr( $options['request_timeout'] ); ?>"> seconds</td></tr>
                    <tr><th><label for="sc-rl-v620-batch">Sync batch size</label></th><td><input id="sc-rl-v620-batch" type="number" min="25" max="250" name="sc_rl_v620[sync_batch_size]" value="<?php echo esc_attr( $options['sync_batch_size'] ); ?>"></td></tr>
                    <tr><th><label for="sc-rl-v620-max">Maximum public records</label></th><td><input id="sc-rl-v620-max" type="number" min="100" max="10000" name="sc_rl_v620[max_records]" value="<?php echo esc_attr( $options['max_records'] ); ?>"></td></tr>
                    <tr><th>Content indexing</th><td><input type="hidden" name="sc_rl_v620[include_content]" value="0"><label><input type="checkbox" name="sc_rl_v620[include_content]" value="1" <?php checked( $options['include_content'], '1' ); ?>> Include cleaned public body text, headings, taxonomies, series, article-map metadata, and parent relationships</label></td></tr>
                    <tr><th><label for="sc-rl-v620-char-limit">Content characters per record</label></th><td><input id="sc-rl-v620-char-limit" type="number" min="2000" max="60000" name="sc_rl_v620[content_character_limit]" value="<?php echo esc_attr( $options['content_character_limit'] ); ?>"></td></tr>
                    <tr><th>Automatic synchronization</th><td><input type="hidden" name="sc_rl_v620[auto_sync]" value="0"><label><input type="checkbox" name="sc_rl_v620[auto_sync]" value="1" <?php checked( $options['auto_sync'], '1' ); ?>> Process saved, unpublished, and deleted records incrementally and run recurring verification syncs</label></td></tr>
                    <tr><th><label for="sc-rl-v620-frequency">Recurring frequency</label></th><td><select id="sc-rl-v620-frequency" name="sc_rl_v620[sync_frequency]"><?php foreach ( array( 'hourly' => 'Hourly', 'sc_rl_six_hourly' => 'Every six hours', 'twicedaily' => 'Twice daily', 'daily' => 'Daily' ) as $value => $label ) : ?><option value="<?php echo esc_attr( $value ); ?>" <?php selected( $options['sync_frequency'], $value ); ?>><?php echo esc_html( $label ); ?></option><?php endforeach; ?></select></td></tr>
                    <tr><th>Automatic cold-start recovery</th><td><input type="hidden" name="sc_rl_v620[auto_recover]" value="0"><label><input type="checkbox" name="sc_rl_v620[auto_recover]" value="1" <?php checked( $options['auto_recover'], '1' ); ?>> Rehydrate an empty backend from the latest verified WordPress snapshot</label></td></tr>
                    <tr><th><label for="sc-rl-v630-snapshots">WordPress snapshot retention</label></th><td><input id="sc-rl-v630-snapshots" type="number" min="1" max="20" name="sc_rl_v620[max_wordpress_snapshots]" value="<?php echo esc_attr( $options['max_wordpress_snapshots'] ); ?>"> snapshots</td></tr>
                </table>
                <p class="submit"><button class="button button-primary" type="submit" name="sc_rl_v620_save" value="1">Save Settings</button> <button class="button" type="submit" name="sc_rl_v620_test" value="1">Test Backend</button> <button class="button button-secondary" type="submit" name="sc_rl_v620_sync" value="1">Transactional Full Sync</button> <button class="button" type="submit" name="sc_rl_v630_sync_incremental" value="1">Process Incremental Queue</button> <button class="button" type="submit" name="sc_rl_v630_create_snapshot" value="1">Create WordPress Snapshot</button> <button class="button button-secondary" type="submit" name="sc_rl_v630_recover" value="1">Recover Empty Backend</button> <button class="button" type="submit" name="sc_rl_v621_repair" value="1">Repair and Resynchronize</button> <button class="button" type="submit" name="sc_rl_v621_reset_rate_limits" value="1">Reset Public Rate Limits</button></p>

                <?php if ( $backend_snapshots ) : ?>
                    <h2>Runtime Rollback</h2>
                    <p><select name="sc_rl_v630_snapshot_id"><option value="">Choose a backend snapshot</option><?php foreach ( $backend_snapshots as $snapshot ) : ?><option value="<?php echo esc_attr( $snapshot['snapshot_id'] ?? '' ); ?>"><?php echo esc_html( ( $snapshot['created_utc'] ?? '' ) . ' · ' . absint( $snapshot['record_count'] ?? 0 ) . ' records · ' . ( $snapshot['reason'] ?? '' ) ); ?></option><?php endforeach; ?></select> <button class="button" type="submit" name="sc_rl_v630_rollback" value="1">Rollback Runtime Index</button></p>
                <?php endif; ?>
            </form>

            <h2>Durability and Synchronization Diagnostics</h2>
            <table class="widefat striped" style="max-width:1100px;margin-bottom:18px"><tbody>
                <tr><th>Runtime storage</th><td><?php echo esc_html( is_wp_error( $status ) ? 'Unavailable' : ( $status['storage_engine'] ?? 'sqlite' ) ); ?><?php if ( ! is_wp_error( $status ) ) : ?> · schema <?php echo esc_html( absint( $status['schema_version'] ?? 0 ) ); ?> · index version <?php echo esc_html( absint( $status['index_version'] ?? 0 ) ); ?><?php endif; ?></td></tr>
                <tr><th>Runtime checksum</th><td><code><?php echo esc_html( is_wp_error( $status ) ? '' : ( $status['checksum'] ?? '' ) ); ?></code></td></tr>
                <tr><th>WordPress ledger</th><td><?php echo esc_html( count( $ledger['records'] ) ); ?> records · index v<?php echo esc_html( absint( $ledger['index_version'] ) ); ?> · <code><?php echo esc_html( $ledger['checksum'] ); ?></code></td></tr>
                <tr><th>Canonical snapshot</th><td><?php echo esc_html( $wp_snapshots ? ( $wp_snapshots[0]['snapshot_id'] . ' · ' . $wp_snapshots[0]['record_count'] . ' records · ' . $wp_snapshots[0]['created_utc'] ) : 'No canonical snapshot available' ); ?></td></tr>
                <tr><th>Runtime snapshots</th><td><?php echo esc_html( count( $backend_snapshots ) ); ?> available for rollback</td></tr>
                <tr><th>Incremental queue</th><td><?php echo esc_html( count( $queue ) ); ?> pending change(s)</td></tr>
                <tr><th>Automatic recovery</th><td><?php echo esc_html( '1' === $options['auto_recover'] ? 'Enabled' : 'Disabled' ); ?><?php if ( $diagnostics['cron']['recovery_scheduled'] ) : ?> · scheduled for <?php echo esc_html( $diagnostics['cron']['recovery_next_run_utc'] ); ?><?php endif; ?></td></tr>
                <tr><th>WP-Cron</th><td><?php echo esc_html( $diagnostics['cron']['wp_cron_disabled'] ? 'Disabled by configuration' : ( $diagnostics['cron']['scheduled'] ? 'Scheduled' : 'Not scheduled' ) ); ?><?php if ( $diagnostics['cron']['next_run_utc'] ) : ?> · next run <?php echo esc_html( $diagnostics['cron']['next_run_utc'] ); ?><?php endif; ?></td></tr>
                <tr><th>Public rate limit</th><td><?php echo esc_html( absint( $rate_status['limit'] ?? 0 ) ); ?> questions per <?php echo esc_html( absint( $rate_status['window_minutes'] ?? 0 ) ); ?> minutes · <?php echo esc_html( absint( $rate_status['active_visitors'] ?? 0 ) ); ?> active visitor window(s)</td></tr>
                <tr><th>Latest sync job</th><td><?php echo esc_html( ! empty( $sync_report['job_id'] ) ? $sync_report['job_id'] . ' · ' . $sync_report['state'] : 'No v6.3.0 sync report yet' ); ?></td></tr>
                <tr><th>Inserted / updated / unchanged / deleted</th><td><?php echo esc_html( absint( $sync_report['inserted_records'] ?? 0 ) . ' / ' . absint( $sync_report['updated_records'] ?? 0 ) . ' / ' . absint( $sync_report['unchanged_records'] ?? 0 ) . ' / ' . absint( $sync_report['backend_deleted_records'] ?? 0 ) ); ?></td></tr>
            </tbody></table>
            <?php if ( ! empty( $sync_report['batches'] ) ) : ?>
                <h3>Last Transaction Batches</h3>
                <table class="widefat striped" style="max-width:1100px;margin-bottom:18px"><thead><tr><th>Batch</th><th>Mode</th><th>Sent</th><th>Backend state</th><th>Transaction state</th></tr></thead><tbody>
                <?php foreach ( $sync_report['batches'] as $batch ) : ?><tr><td><?php echo esc_html( absint( $batch['batch'] ) . ' / ' . absint( $batch['batch_count'] ) ); ?></td><td><?php echo esc_html( $batch['mode'] ); ?></td><td><?php echo esc_html( absint( $batch['records_sent'] ) ); ?></td><td><?php echo esc_html( $batch['backend_state'] ?? '' ); ?></td><td><?php echo esc_html( $batch['state'] ); ?></td></tr><?php endforeach; ?>
                </tbody></table>
            <?php endif; ?>
            <div class="sc-rl-admin-note"><strong>Free-tier recovery boundary:</strong> Render's local SQLite file may be replaced when an instance restarts. WordPress therefore retains the canonical compressed snapshot and automatically rehydrates an empty runtime index. No paid database is required for this release.</div>
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
            'auto_recover' => ! empty( $input['auto_recover'] ) ? '1' : '0',
            'max_wordpress_snapshots' => max( 1, min( 20, absint( isset( $input['max_wordpress_snapshots'] ) ? $input['max_wordpress_snapshots'] : $old['max_wordpress_snapshots'] ) ) ),
        );
        update_option( self::OPTION_NAME, $saved, false );
        return $saved;
    }
}

// Backward-compatible aliases preserve cached admin code and v6.2.x integrations.
if ( ! class_exists( 'SC_RL6_V621_Endpoint_Reliability', false ) ) {
    class_alias( 'SC_RL6_V630_Durable_Index', 'SC_RL6_V621_Endpoint_Reliability' );
}
if ( ! class_exists( 'SC_RL6_V620_Knowledge_Intelligence', false ) ) {
    class_alias( 'SC_RL6_V630_Durable_Index', 'SC_RL6_V620_Knowledge_Intelligence' );
}
