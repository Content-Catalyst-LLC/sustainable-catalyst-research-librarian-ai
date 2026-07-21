<?php
/**
 * Research Librarian AI v7.0.8 — Transaction-State Reconciliation and Durable Recovery.
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class SC_RL6_V630_Durable_Index {
    const VERSION = '7.0.8';
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
    const SYNC_RETRY_HOOK = 'sc_rl_v631_sync_retry_event';
    const SYNC_RETRY_OPTION = 'sc_rl_v631_sync_retry_state';
    const RECOVERY_STATE_OPTION = 'sc_rl_v631_recovery_state';
    const ALERT_STATE_OPTION = 'sc_rl_v631_public_alert_state';
    const EMBEDDING_HOOK = 'sc_rl_v701_embedding_queue_event';
    const EMBEDDING_STATE_OPTION = 'sc_rl_v701_embedding_queue_state';
    const BUILD_STATE_OPTION = 'sc_rl_v703_index_build_state';
    const BUILD_HOOK = 'sc_rl_v703_index_build_event';
    const BUILD_LOCK_OPTION = 'sc_rl_v703_index_build_lock';

    public static function init() {
        add_action( 'admin_menu', array( __CLASS__, 'register_admin_menu' ), 1010 );
        add_action( 'rest_api_init', array( __CLASS__, 'register_rest_routes' ), 110 );
        add_action( self::SYNC_HOOK, array( __CLASS__, 'run_scheduled_sync' ) );
        add_action( self::RECOVERY_HOOK, array( __CLASS__, 'run_backend_recovery' ) );
        add_action( self::INCREMENTAL_HOOK, array( __CLASS__, 'run_incremental_sync' ) );
        add_action( self::SYNC_RETRY_HOOK, array( __CLASS__, 'run_sync_retry' ) );
        add_action( self::EMBEDDING_HOOK, array( __CLASS__, 'run_embedding_queue' ) );
        add_action( self::BUILD_HOOK, array( __CLASS__, 'run_index_build_job' ), 10, 1 );
        add_action( 'admin_post_sc_rl_v631_export_sync_log', array( __CLASS__, 'export_sync_log' ) );
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
        wp_clear_scheduled_hook( self::SYNC_RETRY_HOOK );
        wp_clear_scheduled_hook( self::EMBEDDING_HOOK );
        wp_clear_scheduled_hook( self::BUILD_HOOK );
        delete_option( self::BUILD_LOCK_OPTION );
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
            'auto_embed_after_sync' => '1',
            'embedding_batch_size' => 50,
            'embedding_delay_ms' => 200,
            'embedding_retry_seconds' => 300,
            'source_batch_size' => 40,
            'build_stale_minutes' => 20,
            'max_wordpress_snapshots' => 5,
            'max_retry_attempts' => 5,
            'retry_base_seconds' => 30,
            'retry_max_seconds' => 900,
            'stalled_job_minutes' => 30,
            'alert_suppression_minutes' => 15,
            'retrieval_structural_weight' => 1.0,
            'retrieval_lexical_weight' => 24.0,
            'retrieval_semantic_weight' => 160.0,
            'retrieval_rrf_weight' => 1400.0,
            'retrieval_rrf_k' => 60,
            'retrieval_minimum_score' => 8.0,
            'retrieval_minimum_sources' => 1,
            'retrieval_ambiguity_margin' => 40.0,
            'retrieval_unsupported_overlap' => 0.06,
            'retrieval_minimum_citation_coverage' => 0.80,
            'retrieval_max_sources' => 10,
            'retrieval_max_context_characters' => 18000,
            'retrieval_max_passage_characters' => 1800,
            'retrieval_post_type_weights' => 'article:1.08,post:1.05,page:1.0,document:1.04,pdf:1.04',
            'retrieval_source_weights' => 'wordpress:1.0',
            'retrieval_excluded_post_types' => '',
            'retrieval_excluded_sources' => '',
            'retrieval_excluded_url_prefixes' => '',
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
            self::start_index_build( 'scheduled-verification' );
        }
    }

    public static function run_incremental_sync() {
        if ( self::enabled() && self::incremental_queue() ) {
            self::sync_incremental_queue();
        }
    }

    private static function retry_delay( $attempt ) {
        $options = self::options();
        $base = max( 10, min( 300, absint( $options['retry_base_seconds'] ) ) );
        $maximum = max( $base, min( 3600, absint( $options['retry_max_seconds'] ) ) );
        return min( $maximum, $base * pow( 2, max( 0, absint( $attempt ) - 1 ) ) );
    }

    private static function schedule_full_retry( $error = '' ) {
        $options = self::options();
        $state = get_option( self::SYNC_RETRY_OPTION, array() );
        $state = is_array( $state ) ? $state : array();
        $attempt = absint( isset( $state['attempt'] ) ? $state['attempt'] : 0 ) + 1;
        $maximum = max( 1, min( 10, absint( $options['max_retry_attempts'] ) ) );
        if ( $attempt > $maximum ) {
            update_option( self::SYNC_RETRY_OPTION, array(
                'state' => 'exhausted',
                'attempt' => $attempt - 1,
                'max_attempts' => $maximum,
                'last_error' => sanitize_text_field( $error ),
                'updated_utc' => gmdate( 'c' ),
            ), false );
            return false;
        }
        if ( wp_next_scheduled( self::SYNC_RETRY_HOOK ) ) {
            return true;
        }
        $delay = self::retry_delay( $attempt );
        wp_schedule_single_event( time() + $delay, self::SYNC_RETRY_HOOK );
        update_option( self::SYNC_RETRY_OPTION, array(
            'state' => 'scheduled',
            'attempt' => $attempt,
            'max_attempts' => $maximum,
            'delay_seconds' => $delay,
            'next_run_utc' => gmdate( 'c', time() + $delay ),
            'last_error' => sanitize_text_field( $error ),
            'updated_utc' => gmdate( 'c' ),
        ), false );
        return true;
    }

    public static function run_sync_retry() {
        $state = get_option( self::SYNC_RETRY_OPTION, array() );
        $state = is_array( $state ) ? $state : array();
        $state['state'] = 'running';
        $state['started_utc'] = gmdate( 'c' );
        update_option( self::SYNC_RETRY_OPTION, $state, false );
        $build = self::build_state();
        $result = self::build_is_active( $build ) ? self::resume_index_build() : self::start_index_build( 'automatic-retry' );
        if ( ! is_wp_error( $result ) ) {
            self::clear_sync_retry();
        }
    }

    private static function clear_sync_retry() {
        wp_clear_scheduled_hook( self::SYNC_RETRY_HOOK );
        delete_option( self::SYNC_RETRY_OPTION );
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
        register_rest_route( self::REST_NAMESPACE, '/python/maintenance', array(
            'methods' => WP_REST_Server::CREATABLE,
            'callback' => array( __CLASS__, 'handle_maintenance' ),
            'permission_callback' => array( __CLASS__, 'can_manage' ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/python/snapshot-validation', array(
            'methods' => WP_REST_Server::READABLE,
            'callback' => array( __CLASS__, 'handle_snapshot_validation' ),
            'permission_callback' => array( __CLASS__, 'can_manage' ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/python/log-export', array(
            'methods' => WP_REST_Server::READABLE,
            'callback' => array( __CLASS__, 'handle_log_export' ),
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
                'suppress_notice' => ! empty( $error['suppress_notice'] ),
                'alert_occurrences' => absint( $error['alert_occurrences'] ?? 0 ),
                'suppressed_until_utc' => sanitize_text_field( $error['suppressed_until_utc'] ?? '' ),
                'recovery_progress' => self::recovery_state(),
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
        $status['recovery_progress'] = self::recovery_state();
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
        $backend_validation = self::request( '/v1/knowledge/snapshots/validate', 'GET' );
        return new WP_REST_Response( array(
            'version' => self::VERSION,
            'wordpress_snapshots' => self::wordpress_snapshots(),
            'wordpress_validation' => self::validate_wordpress_snapshots(),
            'backend' => is_wp_error( $backend ) ? self::public_error_snapshot( $backend ) : $backend,
            'backend_validation' => is_wp_error( $backend_validation ) ? self::public_error_snapshot( $backend_validation ) : $backend_validation,
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

    public static function handle_maintenance() {
        $options = self::options();
        $result = self::request( '/v1/knowledge/maintenance', 'POST', array(
            'max_age_seconds' => max( 300, absint( $options['stalled_job_minutes'] ) * MINUTE_IN_SECONDS ),
            'purge_staging' => true,
        ) );
        if ( ! is_wp_error( $result ) ) {
            self::append_recovery_log( 'stalled-jobs-repaired', $result );
        }
        return is_wp_error( $result ) ? $result : new WP_REST_Response( $result, 200 );
    }

    public static function handle_snapshot_validation() {
        $backend = self::request( '/v1/knowledge/snapshots/validate', 'GET' );
        return new WP_REST_Response( array(
            'version' => self::VERSION,
            'wordpress' => self::validate_wordpress_snapshots(),
            'backend' => is_wp_error( $backend ) ? self::public_error_snapshot( $backend ) : $backend,
        ), 200 );
    }

    public static function log_export_payload() {
        $status = self::backend_status( true );
        $manifest = self::request( '/v1/knowledge/manifest', 'GET' );
        $backend_snapshot_validation = self::request( '/v1/knowledge/snapshots/validate', 'GET' );
        $retrieval_config = self::request( '/v1/retrieval/config', 'GET' );
        $benchmark_history = self::request( '/v1/retrieval/benchmark/history', 'GET' );
        $ledger = self::sync_ledger();
        $sync_next = wp_next_scheduled( self::SYNC_HOOK );
        $recovery_next = wp_next_scheduled( self::RECOVERY_HOOK );
        $retry_next = wp_next_scheduled( self::SYNC_RETRY_HOOK );
        return array(
            'schema' => 'sc-research-librarian-sync-recovery-export/7.0.8',
            'version' => self::VERSION,
            'site' => home_url( '/' ),
            'generated_utc' => gmdate( 'c' ),
            'backend_status' => is_wp_error( $status ) ? self::public_error_snapshot( $status ) : $status,
            'backend_manifest' => is_wp_error( $manifest ) ? self::public_error_snapshot( $manifest ) : $manifest,
            'latest_sync_report' => self::latest_sync_report(),
            'sync_history' => self::sync_history(),
            'recovery_log' => self::recovery_log(),
            'sync_retry_state' => get_option( self::SYNC_RETRY_OPTION, array() ),
            'recovery_state' => self::recovery_state(),
            'public_alert_state' => get_option( self::ALERT_STATE_OPTION, array() ),
            'wordpress_ledger' => array(
                'record_count' => count( $ledger['records'] ),
                'checksum' => sanitize_text_field( $ledger['checksum'] ),
                'index_version' => absint( $ledger['index_version'] ),
                'updated_utc' => sanitize_text_field( $ledger['updated_utc'] ),
            ),
            'incremental_queue' => array_values( self::incremental_queue() ),
            'cron' => array(
                'sync_next_utc' => $sync_next ? gmdate( 'c', $sync_next ) : '',
                'recovery_next_utc' => $recovery_next ? gmdate( 'c', $recovery_next ) : '',
                'retry_next_utc' => $retry_next ? gmdate( 'c', $retry_next ) : '',
                'wp_cron_disabled' => defined( 'DISABLE_WP_CRON' ) && DISABLE_WP_CRON,
            ),
            'wordpress_snapshot_validation' => self::validate_wordpress_snapshots(),
            'backend_snapshot_validation' => is_wp_error( $backend_snapshot_validation ) ? self::public_error_snapshot( $backend_snapshot_validation ) : $backend_snapshot_validation,
            'retrieval_config' => is_wp_error( $retrieval_config ) ? self::public_error_snapshot( $retrieval_config ) : $retrieval_config,
            'retrieval_benchmark_history' => is_wp_error( $benchmark_history ) ? self::public_error_snapshot( $benchmark_history ) : $benchmark_history,
        );
    }

    public static function handle_log_export() {
        return new WP_REST_Response( self::log_export_payload(), 200 );
    }

    public static function export_sync_log() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( esc_html__( 'You are not allowed to export Research Librarian logs.', 'sustainable-catalyst-research-librarian-ai' ) );
        }
        check_admin_referer( 'sc_rl_v631_export_sync_log' );
        $payload = self::log_export_payload();
        nocache_headers();
        header( 'Content-Type: application/json; charset=utf-8' );
        header( 'Content-Disposition: attachment; filename="research-librarian-sync-recovery-' . gmdate( 'Ymd-His' ) . '.json"' );
        echo wp_json_encode( $payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
        exit;
    }

    public static function handle_suggestions( WP_REST_Request $request ) {
        if ( ! self::enabled() ) {
            return new WP_REST_Response( array( 'suggestions' => array(), 'cached' => false ), 200 );
        }
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_v621_bad_nonce', 'Security check failed.', array( 'status' => 403 ) );
        }
        $query = trim( sanitize_text_field( $request->get_param( 'query' ) ) );
        if ( strlen( $query ) < 2 ) {
            return new WP_REST_Response( array( 'suggestions' => array(), 'cached' => false ), 200 );
        }

        // v6.5.1 caches title suggestions against the current canonical ledger checksum.
        // A full or incremental sync changes the checksum, naturally invalidating old suggestions.
        $ledger = get_option( self::LEDGER_OPTION, array() );
        $ledger_checksum = sanitize_text_field( isset( $ledger['checksum'] ) ? $ledger['checksum'] : '' );
        $normalized_query = strtolower( preg_replace( '/\s+/', ' ', $query ) );
        $cache_key = 'sc_rl_v651_suggest_' . md5( self::VERSION . '|' . $ledger_checksum . '|' . $normalized_query );
        $cached = get_transient( $cache_key );
        if ( is_array( $cached ) ) {
            $response = new WP_REST_Response( array(
                'suggestions' => $cached,
                'cached' => true,
                'cache_ttl' => 300,
            ), 200 );
            $response->header( 'Cache-Control', 'private, max-age=60, stale-while-revalidate=240' );
            $response->header( 'X-SC-RL-Suggestion-Cache', 'HIT' );
            return $response;
        }

        $response = self::request( '/v1/retrieve', 'POST', array( 'query' => $query, 'limit' => 8 ) );
        if ( is_wp_error( $response ) ) {
            return new WP_REST_Response( array( 'suggestions' => array(), 'cached' => false ), 200 );
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
        set_transient( $cache_key, $suggestions, 5 * MINUTE_IN_SECONDS );
        $rest_response = new WP_REST_Response( array(
            'suggestions' => $suggestions,
            'cached' => false,
            'cache_ttl' => 300,
        ), 200 );
        $rest_response->header( 'Cache-Control', 'private, max-age=60, stale-while-revalidate=240' );
        $rest_response->header( 'X-SC-RL-Suggestion-Cache', 'MISS' );
        return $rest_response;
    }

    public static function handle_admin_sync() {
        $result = self::start_index_build( 'rest-admin-sync' );
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
        $build = self::start_index_build( 'repair-and-resync' );
        if ( is_wp_error( $build ) ) {
            return new WP_Error(
                $build->get_error_code(),
                $build->get_error_message(),
                array_merge( (array) $build->get_error_data(), array( 'repair_stage' => 'queue-index-build' ) )
            );
        }
        return array(
            'version' => self::VERSION,
            'ok' => true,
            'message' => 'Endpoint verification completed and an asynchronous, resumable knowledge-index rebuild was queued.',
            'health' => $health,
            'build' => $build,
            'diagnostics' => self::diagnostics_snapshot(),
            'repaired_utc' => gmdate( 'c' ),
        );
    }

    public static function ask( $question, $route_hint = array(), $wordpress_status = array(), $session_id = '', $research_mode = 'auto' ) {
        if ( ! self::enabled() ) {
            return new WP_Error( 'sc_rl_v621_disabled', 'The Python intelligence backend is not enabled.' );
        }
        $payload = array(
            'question' => sanitize_textarea_field( $question ),
            'research_mode' => in_array( sanitize_key( $research_mode ), array( 'auto', 'title', 'subject', 'path', 'evidence', 'analyze', 'compare', 'decision' ), true ) ? sanitize_key( $research_mode ) : 'auto',
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
                'evidence_id' => sanitize_text_field( isset( $item['evidence_id'] ) ? $item['evidence_id'] : '' ),
                'citation_label' => sanitize_text_field( isset( $item['citation_label'] ) ? $item['citation_label'] : '' ),
                'section' => sanitize_text_field( isset( $item['section'] ) ? $item['section'] : '' ),
                'page' => isset( $item['page'] ) && null !== $item['page'] ? absint( $item['page'] ) : null,
                'passage' => sanitize_textarea_field( isset( $item['passage'] ) ? $item['passage'] : '' ),
                'lexical_score' => isset( $item['lexical_score'] ) ? round( (float) $item['lexical_score'], 5 ) : 0,
                'semantic_score' => isset( $item['semantic_score'] ) ? round( (float) $item['semantic_score'], 5 ) : 0,
                'fusion_score' => isset( $item['fusion_score'] ) ? round( (float) $item['fusion_score'], 5 ) : 0,
                'retrieval_reasons' => isset( $item['retrieval_reasons'] ) && is_array( $item['retrieval_reasons'] ) ? array_values( array_map( 'sanitize_key', $item['retrieval_reasons'] ) ) : array(),
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
        $grounding['evidence'] = isset( $backend['evidence'] ) && is_array( $backend['evidence'] ) ? array_values( array_map( array( __CLASS__, 'sanitize_evidence_record' ), $backend['evidence'] ) ) : array();
        $grounding['citation_verification'] = isset( $backend['citation_verification'] ) && is_array( $backend['citation_verification'] ) ? self::sanitize_diagnostic_map( $backend['citation_verification'] ) : array();
        $grounding['retrieval_diagnostics'] = isset( $backend['retrieval_diagnostics'] ) && is_array( $backend['retrieval_diagnostics'] ) ? self::sanitize_diagnostic_map( $backend['retrieval_diagnostics'] ) : array();
        $grounding['research_mode'] = sanitize_key( isset( $backend['research_mode'] ) ? $backend['research_mode'] : 'auto' );
        $grounding['follow_up_prompts'] = isset( $backend['follow_up_prompts'] ) && is_array( $backend['follow_up_prompts'] ) ? array_values( array_map( 'sanitize_text_field', $backend['follow_up_prompts'] ) ) : array();
        $grounding['workspace'] = isset( $backend['workspace'] ) && is_array( $backend['workspace'] ) ? self::sanitize_diagnostic_map( $backend['workspace'] ) : array();
        $grounding['session_turns'] = absint( isset( $backend['session_turns'] ) ? $backend['session_turns'] : 0 );
        $grounding['evidence_gate'] = isset( $backend['evidence_gate'] ) && is_array( $backend['evidence_gate'] ) ? self::sanitize_diagnostic_map( $backend['evidence_gate'] ) : array();
        $grounding['capabilities'] = isset( $backend['capabilities'] ) && is_array( $backend['capabilities'] ) ? self::sanitize_diagnostic_map( $backend['capabilities'] ) : array();
        $grounding['typed_handoffs'] = isset( $backend['typed_handoffs'] ) && is_array( $backend['typed_handoffs'] ) ? self::sanitize_diagnostic_map( $backend['typed_handoffs'] ) : array();
        $grounding['provenance'] = isset( $backend['provenance'] ) && is_array( $backend['provenance'] ) ? self::sanitize_diagnostic_map( $backend['provenance'] ) : array();
        $grounding['reason_codes'] = array_values( array_unique( array_merge( $grounding['reason_codes'], array( 'bm25-section-retrieval', 'citation-verification' ), ! empty( $grounding['retrieval_diagnostics']['semantic_used'] ) ? array( 'semantic-retrieval' ) : array() ) ) );

        $note = array(
            'schema' => 'sc-research-librarian-route-note/7.0.8',
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
            'evidence' => $grounding['evidence'],
            'citation_verification' => $grounding['citation_verification'],
            'retrieval_diagnostics' => $grounding['retrieval_diagnostics'],
            'evidence_gate' => $grounding['evidence_gate'],
            'capabilities' => $grounding['capabilities'],
            'typed_handoffs' => $grounding['typed_handoffs'],
            'provenance' => $grounding['provenance'],
            'handoffs' => array_values( array_map( function( $handoff ) {
                return array(
                    'id' => sanitize_text_field( isset( $handoff['handoff_id'] ) ? $handoff['handoff_id'] : '' ),
                    'label' => sanitize_text_field( isset( $handoff['route']['destination_label'] ) ? $handoff['route']['destination_label'] : ( isset( $handoff['destination'] ) ? $handoff['destination'] : 'Platform handoff' ) ),
                    'url' => esc_url_raw( isset( $handoff['route']['destination_url'] ) ? $handoff['route']['destination_url'] : '' ),
                    'reason' => sanitize_text_field( isset( $handoff['route']['reason'] ) ? $handoff['route']['reason'] : 'Typed platform handoff available.' ),
                    'target' => sanitize_key( isset( $handoff['destination'] ) ? $handoff['destination'] : '' ),
                );
            }, $grounding['typed_handoffs'] ) ),
            'handoff_payload' => ! empty( $grounding['typed_handoffs'][0] ) ? $grounding['typed_handoffs'][0] : array(),
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
                'research_mode' => $grounding['research_mode'],
                'follow_up_prompts' => $grounding['follow_up_prompts'],
                'workspace' => $grounding['workspace'],
                'session_turns' => $grounding['session_turns'],
                'capabilities' => $grounding['capabilities'],
                'typed_handoffs' => $grounding['typed_handoffs'],
                'provenance' => $grounding['provenance'],
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
            'evidence' => $grounding['evidence'],
            'citation_verification' => $grounding['citation_verification'],
            'retrieval_diagnostics' => $grounding['retrieval_diagnostics'],
            'evidence_gate' => $grounding['evidence_gate'],
            'research_mode' => $grounding['research_mode'],
            'follow_up_prompts' => $grounding['follow_up_prompts'],
            'workspace' => $grounding['workspace'],
            'session_turns' => $grounding['session_turns'],
            'capabilities' => $grounding['capabilities'],
            'typed_handoffs' => $grounding['typed_handoffs'],
            'provenance' => $grounding['provenance'],
            'clarification' => sanitize_textarea_field( isset( $backend['clarification'] ) ? $backend['clarification'] : '' ),
            'endpoint_status' => self::endpoint_status_from_backend( isset( $backend['status'] ) && is_array( $backend['status'] ) ? $backend['status'] : array(), ! empty( $backend['ai_used'] ) ),
        );
    }

    public static function sanitize_evidence_record( $item ) {
        $item = is_array( $item ) ? $item : array();
        return array(
            'id' => sanitize_text_field( $item['id'] ?? '' ),
            'record_id' => sanitize_text_field( $item['record_id'] ?? '' ),
            'chunk_id' => sanitize_text_field( $item['chunk_id'] ?? '' ),
            'title' => sanitize_text_field( $item['title'] ?? '' ),
            'url' => esc_url_raw( $item['url'] ?? '' ),
            'section' => sanitize_text_field( $item['section'] ?? '' ),
            'page' => isset( $item['page'] ) && null !== $item['page'] ? absint( $item['page'] ) : null,
            'passage' => sanitize_textarea_field( $item['passage'] ?? '' ),
            'source_type' => sanitize_key( $item['source_type'] ?? '' ),
            'record_version' => sanitize_text_field( $item['record_version'] ?? '' ),
            'reason' => sanitize_text_field( $item['reason'] ?? '' ),
        );
    }

    private static function sanitize_diagnostic_value( $value, $depth = 0 ) {
        if ( $depth > 5 ) {
            return '[depth-limited]';
        }
        if ( is_bool( $value ) || is_numeric( $value ) || null === $value ) {
            return $value;
        }
        if ( is_array( $value ) ) {
            $clean = array();
            foreach ( $value as $key => $child ) {
                $clean_key = is_int( $key ) ? $key : sanitize_key( $key );
                $clean[ $clean_key ] = self::sanitize_diagnostic_value( $child, $depth + 1 );
            }
            return $clean;
        }
        return sanitize_text_field( $value );
    }

    private static function sanitize_diagnostic_map( $map ) {
        return is_array( $map ) ? self::sanitize_diagnostic_value( $map ) : array();
    }

    private static function endpoint_status_from_backend( $status, $ai_used = false ) {
        $indexed = absint( isset( $status['indexed_records'] ) ? $status['indexed_records'] : 0 );
        if ( 'backend-warming' === sanitize_key( $status['state'] ?? '' ) || 'warming' === sanitize_key( $status['startup_state'] ?? '' ) ) {
            return array(
                'state' => 'backend-warming',
                'label' => 'Python backend is warming up',
                'message' => 'Render is opening the service and runtime index. Verified WordPress fallback remains available.',
                'error_type' => 'backend-cold-start',
                'startup_phase' => sanitize_key( $status['startup_phase'] ?? 'warming' ),
                'startup_progress' => absint( $status['startup_progress'] ?? 0 ),
            );
        }
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

    private static function register_public_alert( $type ) {
        $transient = in_array( $type, array( 'backend-cold-start', 'backend-unavailable', 'backend-unreachable' ), true );
        if ( ! $transient ) {
            return array( 'suppress_notice' => false, 'alert_occurrences' => 1, 'suppressed_until_utc' => '' );
        }
        $options = self::options();
        $minutes = max( 1, min( 120, absint( $options['alert_suppression_minutes'] ) ) );
        $now = time();
        $fingerprint = hash( 'sha256', $type . '|' . (string) $options['backend_url'] );
        $state = get_option( self::ALERT_STATE_OPTION, array() );
        $state = is_array( $state ) ? $state : array();
        $same_window = ! empty( $state['fingerprint'] ) && hash_equals( (string) $state['fingerprint'], $fingerprint ) && $now < absint( $state['suppressed_until'] ?? 0 );
        $occurrences = $same_window ? absint( $state['occurrences'] ?? 1 ) + 1 : 1;
        $until = $same_window ? absint( $state['suppressed_until'] ) : $now + ( $minutes * MINUTE_IN_SECONDS );
        update_option( self::ALERT_STATE_OPTION, array(
            'fingerprint' => $fingerprint,
            'type' => sanitize_key( $type ),
            'occurrences' => $occurrences,
            'first_seen_utc' => $same_window ? sanitize_text_field( $state['first_seen_utc'] ?? gmdate( 'c' ) ) : gmdate( 'c' ),
            'last_seen_utc' => gmdate( 'c' ),
            'suppressed_until' => $until,
            'suppressed_until_utc' => gmdate( 'c', $until ),
        ), false );
        return array(
            'suppress_notice' => $same_window,
            'alert_occurrences' => $occurrences,
            'suppressed_until_utc' => gmdate( 'c', $until ),
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
        $alert = self::register_public_alert( $type );
        return array(
            'state' => $selected[0],
            'label' => $selected[1],
            'message' => $selected[2],
            'error_type' => $type,
            'http_status' => $status,
            'technical_message' => $message,
            'checked_utc' => gmdate( 'c' ),
            'suppress_notice' => ! empty( $alert['suppress_notice'] ),
            'alert_occurrences' => absint( $alert['alert_occurrences'] ?? 1 ),
            'suppressed_until_utc' => sanitize_text_field( $alert['suppressed_until_utc'] ?? '' ),
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
        if ( empty( $status['indexed_records'] ) && 'warming' !== sanitize_key( $status['startup_state'] ?? '' ) ) {
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
            'startup_state' => sanitize_key( $body['startup_state'] ?? $authenticated['startup_state'] ?? 'ready' ),
            'startup_phase' => sanitize_key( $body['startup_phase'] ?? $authenticated['startup_phase'] ?? 'ready' ),
            'startup_progress' => absint( $body['startup_progress'] ?? $authenticated['startup_progress'] ?? 100 ),
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
            if ( '' === trim( (string) $detail ) ) {
                $detail = 'HTTP ' . absint( $code ) . ' returned an empty response for ' . sanitize_text_field( $path ) . '.';
            }
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
            delete_option( self::ALERT_STATE_OPTION );
        } else {
            $current['last_failure_utc'] = gmdate( 'c' );
            $current['last_error'] = sanitize_text_field( $error );
        }
        update_option( self::STATUS_OPTION, $current, false );
    }

    public static function sync_all_records( $trigger = 'manual' ) {
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
            'schema' => 'sc-rl-sync-report/7.0.8',
            'job_id' => $job_id,
            'state' => 'running',
            'mode' => 'transactional-replace',
            'trigger' => sanitize_key( $trigger ),
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
                $report['retry_scheduled'] = self::schedule_full_retry( $last->get_error_message() );
                $report['retry_exhausted'] = ! $report['retry_scheduled'];
                self::save_sync_report( $report );
                return new WP_Error( $last->get_error_code(), $last->get_error_message(), array_merge( (array) $last->get_error_data(), array( 'sync_report' => $report ) ) );
            }
            $batch['state'] = ! empty( $last['committed'] ) ? 'committed' : 'staged';
            $batch['completed_utc'] = gmdate( 'c' );
            $batch['accepted_records'] = absint( isset( $last['accepted'] ) ? $last['accepted'] : count( $chunk ) );
            $batch['rejected_records'] = absint( isset( $last['rejected'] ) ? $last['rejected'] : 0 );
            $batch['rejection_details'] = isset( $last['rejected_records'] ) && is_array( $last['rejected_records'] ) ? array_slice( $last['rejected_records'], 0, 25 ) : array();
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
            $report['retry_scheduled'] = self::schedule_full_retry( $report['error'] );
            $report['retry_exhausted'] = ! $report['retry_scheduled'];
            self::save_sync_report( $report );
            return new WP_Error( 'sc_rl_v630_not_committed', $report['error'], array( 'status' => 502, 'sync_report' => $report ) );
        }
        $report['state'] = ! empty( $last['rejected'] ) ? 'completed-with-rejections' : 'completed';
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
        $report['rejection_details'] = isset( $last['rejected_records'] ) && is_array( $last['rejected_records'] ) ? array_slice( $last['rejected_records'], 0, 100 ) : array();
        $report['backend_result'] = $last;
        self::save_sync_report( $report );
        $rejected_ids = array();
        foreach ( $report['rejection_details'] as $rejection ) {
            if ( ! empty( $rejection['id'] ) ) {
                $rejected_ids[] = sanitize_text_field( $rejection['id'] );
            }
        }
        $ledger_records = array_values( array_filter( $records, function( $record ) use ( $rejected_ids ) {
            return empty( $record['id'] ) || ! in_array( $record['id'], $rejected_ids, true );
        } ) );
        self::save_ledger( $ledger_records, $last );
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
        self::clear_sync_retry();
        if ( '1' === (string) self::options()['auto_embed_after_sync'] ) {
            self::schedule_embedding_queue( 'sync-complete', 10 );
        }
        return $status;
    }

    public static function provider_diagnostics() {
        return self::request( '/v1/provider/diagnostics', 'GET' );
    }

    public static function test_backend_embeddings() {
        return self::request( '/v1/knowledge/embeddings/test', 'POST', array() );
    }

    public static function embedding_queue_state() {
        $state = get_option( self::EMBEDDING_STATE_OPTION, array() );
        return is_array( $state ) ? $state : array();
    }

    public static function schedule_embedding_queue( $reason = 'manual', $delay_seconds = 10 ) {
        if ( ! self::enabled() ) {
            return new WP_Error( 'sc_rl_v701_backend_not_configured', 'Python Intelligence is not configured.' );
        }
        $status = self::request( '/v1/knowledge/embeddings/status', 'GET' );
        if ( is_wp_error( $status ) ) {
            return $status;
        }
        $pending = absint( $status['pending_chunks'] ?? 0 );
        $state = array(
            'state' => $pending ? 'scheduled' : 'complete',
            'reason' => sanitize_key( $reason ),
            'pending_chunks' => $pending,
            'processed_chunks' => absint( $status['embedded_chunks'] ?? 0 ),
            'embedding_model' => sanitize_text_field( $status['embedding_model'] ?? '' ),
            'updated_utc' => gmdate( 'c' ),
            'last_error' => '',
        );
        update_option( self::EMBEDDING_STATE_OPTION, $state, false );
        if ( $pending && ! wp_next_scheduled( self::EMBEDDING_HOOK ) ) {
            wp_schedule_single_event( time() + max( 1, absint( $delay_seconds ) ), self::EMBEDDING_HOOK );
        }
        return $state;
    }

    public static function process_embedding_batch( $schedule_remaining = true ) {
        $options = self::options();
        $limit = max( 1, min( 250, absint( $options['embedding_batch_size'] ?? 50 ) ) );
        $delay_ms = max( 0, min( 5000, absint( $options['embedding_delay_ms'] ?? 200 ) ) );
        $result = self::request( '/v1/knowledge/embeddings/process', 'POST', array( 'limit' => $limit, 'delay_ms' => $delay_ms ) );
        if ( ! is_wp_error( $result ) && isset( $result['ok'] ) && ! $result['ok'] ) {
            $result = new WP_Error(
                'sc_rl_v701_embedding_provider_error',
                sanitize_text_field( $result['error'] ?? 'The embedding provider rejected the batch.' ),
                array(
                    'http_status' => absint( $result['http_status'] ?? 502 ),
                    'pending_chunks' => absint( $result['pending_chunks'] ?? 0 ),
                )
            );
        }
        if ( is_wp_error( $result ) ) {
            $data = $result->get_error_data();
            $http = is_array( $data ) ? absint( $data['http_status'] ?? $data['status'] ?? 0 ) : 0;
            $message = $result->get_error_message();
            $auth_failure = in_array( $http, array( 400, 401, 403 ), true )
                || false !== stripos( $message, 'api key' )
                || false !== stripos( $message, 'credential' )
                || false !== stripos( $message, 'invalid argument' );
            update_option( self::EMBEDDING_STATE_OPTION, array(
                'state' => $auth_failure ? 'configuration-error' : 'retry-scheduled',
                'pending_chunks' => is_array( $data ) && isset( $data['pending_chunks'] ) ? absint( $data['pending_chunks'] ) : absint( self::embedding_queue_state()['pending_chunks'] ?? 0 ),
                'last_error' => sanitize_text_field( $message ),
                'http_status' => $http,
                'credential_source' => 'SC_RL_GEMINI_API_KEY',
                'updated_utc' => gmdate( 'c' ),
            ), false );
            if ( $schedule_remaining && ! $auth_failure && ! wp_next_scheduled( self::EMBEDDING_HOOK ) ) {
                wp_schedule_single_event( time() + max( 60, absint( $options['embedding_retry_seconds'] ?? 300 ) ), self::EMBEDDING_HOOK );
            }
            return $result;
        }
        $pending = absint( $result['pending_chunks'] ?? 0 );
        $state = array(
            'state' => $pending ? 'running' : 'complete',
            'run_id' => sanitize_text_field( $result['run_id'] ?? '' ),
            'processed_this_batch' => absint( $result['processed'] ?? 0 ),
            'failed_this_batch' => absint( $result['failed'] ?? 0 ),
            'embedded_chunks' => absint( $result['embedded_chunks'] ?? 0 ),
            'indexed_chunks' => absint( $result['indexed_chunks'] ?? 0 ),
            'pending_chunks' => $pending,
            'semantic_coverage' => (float) ( $result['semantic_coverage'] ?? 0 ),
            'embedding_model' => sanitize_text_field( $result['embedding_model'] ?? '' ),
            'last_error' => sanitize_text_field( $result['error'] ?? '' ),
            'credential_source' => 'SC_RL_GEMINI_API_KEY',
            'updated_utc' => gmdate( 'c' ),
        );
        update_option( self::EMBEDDING_STATE_OPTION, $state, false );
        if ( $schedule_remaining && $pending && ! wp_next_scheduled( self::EMBEDDING_HOOK ) ) {
            wp_schedule_single_event( time() + 15, self::EMBEDDING_HOOK );
        }
        return $result;
    }

    public static function run_embedding_queue() {
        return self::process_embedding_batch( true );
    }

    public static function build_state() {
        $state = get_option( self::BUILD_STATE_OPTION, array() );
        return is_array( $state ) ? $state : array();
    }

    private static function update_build_state( $values ) {
        $state = array_merge( self::build_state(), is_array( $values ) ? $values : array() );
        $state['updated_utc'] = gmdate( 'c' );
        update_option( self::BUILD_STATE_OPTION, $state, false );
        return $state;
    }

    public static function build_index_pipeline() {
        return self::start_index_build( 'manual-v7.0.8-index-build' );
    }

    private static function replace_build_state( $state ) {
        $state = is_array( $state ) ? $state : array();
        $state['updated_utc'] = gmdate( 'c' );
        update_option( self::BUILD_STATE_OPTION, $state, false );
        return $state;
    }

    private static function build_is_active( $state ) {
        return is_array( $state ) && in_array( sanitize_key( $state['state'] ?? '' ), array( 'queued', 'running', 'retry-scheduled', 'paused' ), true );
    }

    private static function build_is_stale( $state ) {
        if ( ! self::build_is_active( $state ) ) {
            return false;
        }
        $updated = strtotime( (string) ( $state['updated_utc'] ?? '' ) );
        $minutes = max( 5, min( 120, absint( self::options()['build_stale_minutes'] ?? 20 ) ) );
        return ! $updated || ( time() - $updated ) > ( $minutes * MINUTE_IN_SECONDS );
    }

    private static function build_directory() {
        $directory = self::ensure_snapshot_directory();
        if ( is_wp_error( $directory ) ) {
            return $directory;
        }
        $directory = trailingslashit( dirname( $directory ) ) . 'index-builds';
        if ( ! wp_mkdir_p( $directory ) ) {
            return new WP_Error( 'sc_rl_v703_build_directory', 'The private asynchronous index-build directory could not be created.' );
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

    private static function build_file_path( $state ) {
        $directory = self::build_directory();
        if ( is_wp_error( $directory ) ) {
            return $directory;
        }
        $filename = sanitize_file_name( (string) ( $state['build_filename'] ?? '' ) );
        if ( ! $filename ) {
            return new WP_Error( 'sc_rl_v703_build_file_missing', 'The asynchronous index build has no private staging filename.' );
        }
        return trailingslashit( $directory ) . $filename;
    }

    private static function cleanup_build_files( $state ) {
        $path = self::build_file_path( $state );
        if ( ! is_wp_error( $path ) && is_file( $path ) ) {
            @unlink( $path );
        }
    }

    private static function schedule_index_build( $job_id, $delay_seconds = 2 ) {
        $job_id = sanitize_text_field( $job_id );
        if ( ! $job_id ) {
            return false;
        }
        $args = array( $job_id );
        if ( ! wp_next_scheduled( self::BUILD_HOOK, $args ) ) {
            wp_schedule_single_event( time() + max( 1, absint( $delay_seconds ) ), self::BUILD_HOOK, $args );
        }
        return true;
    }

    private static function clear_index_build_schedule( $job_id = '' ) {
        $job_id = sanitize_text_field( $job_id );
        if ( $job_id ) {
            wp_clear_scheduled_hook( self::BUILD_HOOK, array( $job_id ) );
        } else {
            wp_clear_scheduled_hook( self::BUILD_HOOK );
        }
    }

    private static function acquire_build_lock( $job_id ) {
        $job_id = sanitize_text_field( $job_id );
        $lock = get_option( self::BUILD_LOCK_OPTION, array() );
        $lock = is_array( $lock ) ? $lock : array();
        $locked_at = absint( $lock['locked_at'] ?? 0 );
        if ( ! empty( $lock['job_id'] ) && $lock['job_id'] !== $job_id && $locked_at && ( time() - $locked_at ) < 300 ) {
            return false;
        }
        update_option( self::BUILD_LOCK_OPTION, array( 'job_id' => $job_id, 'locked_at' => time(), 'locked_utc' => gmdate( 'c' ) ), false );
        return true;
    }

    private static function release_build_lock( $job_id ) {
        $lock = get_option( self::BUILD_LOCK_OPTION, array() );
        if ( is_array( $lock ) && sanitize_text_field( $lock['job_id'] ?? '' ) === sanitize_text_field( $job_id ) ) {
            delete_option( self::BUILD_LOCK_OPTION );
        }
    }

    public static function start_index_build( $trigger = 'manual' ) {
        if ( ! self::enabled() ) {
            return new WP_Error( 'sc_rl_v703_backend_not_configured', 'Enable and configure Python Intelligence before starting the knowledge-index rebuild.' );
        }
        $existing = self::build_state();
        if ( self::build_is_active( $existing ) && ! self::build_is_stale( $existing ) ) {
            self::schedule_index_build( $existing['job_id'] ?? '', 2 );
            $existing['already_running'] = true;
            return $existing;
        }
        if ( self::build_is_stale( $existing ) ) {
            self::clear_index_build_schedule( $existing['job_id'] ?? '' );
            self::cleanup_build_files( $existing );
        } elseif ( ! self::build_is_active( $existing ) && ! empty( $existing['build_filename'] ) ) {
            self::cleanup_build_files( $existing );
        }
        $directory = self::build_directory();
        if ( is_wp_error( $directory ) ) {
            return $directory;
        }
        $job_id = 'async-' . gmdate( 'Ymd-His' ) . '-' . wp_generate_password( 10, false, false );
        $filename = sanitize_file_name( $job_id . '.jsonl' );
        $path = trailingslashit( $directory ) . $filename;
        if ( false === @file_put_contents( $path, '', LOCK_EX ) ) {
            return new WP_Error( 'sc_rl_v703_build_file_create', 'The private asynchronous index staging file could not be created.' );
        }
        $state = array(
            'schema' => 'sc-rl-async-index-build/7.0.8',
            'version' => self::VERSION,
            'job_id' => $job_id,
            'backend_job_id' => $job_id,
            'trigger' => sanitize_key( $trigger ),
            'state' => 'queued',
            'stage' => 'testing-backend',
            'progress' => 1,
            'message' => 'Index rebuild queued. The browser can be closed while background batches continue.',
            'last_error' => '',
            'warnings' => array(),
            'build_filename' => $filename,
            'started_utc' => gmdate( 'c' ),
            'next_run_utc' => gmdate( 'c', time() + 2 ),
            'post_types' => array(),
            'post_type_index' => 0,
            'source_page' => 1,
            'legacy_offset' => 0,
            'legacy_total' => 0,
            'seen_url_hashes' => array(),
            'records_discovered' => 0,
            'records_synced' => 0,
            'records_by_post_type' => array(),
            'skipped_records' => 0,
            'duplicate_urls' => 0,
            'sync_batch_index' => 0,
            'sync_batch_count' => 0,
            'sync_offset' => 0,
            'retry_count' => 0,
            'failed_records' => 0,
            'migrate_legacy' => false,
            'legacy_skipped' => 0,
            'finalization_offset' => 0,
            'finalization_records' => 0,
            'finalization_hashes' => array(),
            'finalization_posts' => array(),
            'finalization_bytes' => 0,
            'transaction_replay_count' => 0,
            'transaction_replay_limit' => 3,
            'backend_transaction_status' => array(),
            'backend_missing_batches' => array(),
            'backend_received_batches' => array(),
            'reconciliation_started_utc' => '',
            'reconciliation_completed_utc' => '',
            'recovery_generation' => 0,
            'sync_batch_offsets' => array(),
            'replay_batch_numbers' => array(),
            'replay_batch_cursor' => 0,
        );
        self::clear_index_build_schedule();
        self::replace_build_state( $state );
        self::schedule_index_build( $job_id, 2 );
        return $state;
    }

    public static function pause_index_build() {
        $state = self::build_state();
        if ( ! self::build_is_active( $state ) ) {
            return new WP_Error( 'sc_rl_v703_build_not_running', 'There is no active knowledge-index build to pause.' );
        }
        self::clear_index_build_schedule( $state['job_id'] ?? '' );
        $state['state'] = 'paused';
        $state['message'] = 'Index rebuild paused. The current durable index remains available.';
        $state['paused_utc'] = gmdate( 'c' );
        return self::replace_build_state( $state );
    }

    public static function resume_index_build() {
        $state = self::build_state();
        if ( empty( $state['job_id'] ) || ! in_array( sanitize_key( $state['state'] ?? '' ), array( 'paused', 'failed', 'retry-scheduled', 'queued', 'running' ), true ) ) {
            return new WP_Error( 'sc_rl_v703_build_not_resumable', 'There is no paused or recoverable knowledge-index build to resume.' );
        }
        $path = self::build_file_path( $state );
        if ( is_wp_error( $path ) || ! is_file( $path ) ) {
            return new WP_Error( 'sc_rl_v703_build_staging_missing', 'The private staging file is missing. Start a new rebuild.' );
        }
        $state['state'] = 'queued';
        $last_error = strtolower( (string) ( $state['last_error'] ?? '' ) );
        $reconciliation_exhausted = false !== strpos( $last_error, 'could not be reconciled' ) || false !== strpos( $last_error, 'missing batch(es)' );
        if ( $reconciliation_exhausted ) {
            $state['transaction_replay_count'] = 0;
            $state['transaction_replay_limit'] = max( 3, absint( $state['transaction_replay_limit'] ?? 0 ) );
            $state['recovery_generation'] = absint( $state['recovery_generation'] ?? 0 ) + 1;
            $state['stage'] = 'reconciling-transaction';
            $state['message'] = 'Durable recovery restarted with a fresh reconciliation generation. The complete WordPress staging file remains intact.';
        } elseif ( 'synchronizing-records' === sanitize_key( $state['stage'] ?? '' ) && false !== strpos( $last_error, 'did not commit the replacement transaction' ) ) {
            $state['stage'] = 'reconciling-transaction';
            $state['message'] = 'The saved source file is intact. Research Librarian will reconcile the backend transaction before replaying any missing work.';
        } else {
            $state['message'] = 'Index rebuild resumed from the last completed batch.';
        }
        $state['last_error'] = '';
        $state['next_run_utc'] = gmdate( 'c', time() + 2 );
        self::replace_build_state( $state );
        self::schedule_index_build( $state['job_id'], 2 );
        return $state;
    }

    public static function cancel_index_build() {
        $state = self::build_state();
        if ( empty( $state['job_id'] ) ) {
            return new WP_Error( 'sc_rl_v703_build_not_found', 'There is no knowledge-index build to cancel.' );
        }
        self::clear_index_build_schedule( $state['job_id'] );
        self::cleanup_build_files( $state );
        $state['state'] = 'cancelled';
        $state['stage'] = 'cancelled';
        $state['message'] = 'Index rebuild cancelled. The previously committed durable index was not replaced.';
        $state['cancelled_utc'] = gmdate( 'c' );
        unset( $state['seen_url_hashes'] );
        return self::replace_build_state( $state );
    }

    private static function build_error_retryable( $error ) {
        if ( ! is_wp_error( $error ) ) {
            return false;
        }
        $data = $error->get_error_data();
        $data = is_array( $data ) ? $data : array();
        $status = absint( $data['http_status'] ?? $data['status'] ?? 0 );
        $message = strtolower( $error->get_error_message() );
        return 429 === $status || $status >= 500 || false !== strpos( $message, 'timeout' ) || false !== strpos( $message, 'temporar' ) || false !== strpos( $message, 'unreachable' ) || false !== strpos( $message, 'cold start' );
    }

    private static function handle_build_error( $state, $error ) {
        $state = is_array( $state ) ? $state : array();
        $message = is_wp_error( $error ) ? $error->get_error_message() : 'Unknown asynchronous index-build error.';
        $retry_count = absint( $state['retry_count'] ?? 0 ) + 1;
        $maximum = max( 1, min( 10, absint( self::options()['max_retry_attempts'] ?? 5 ) ) );
        if ( is_wp_error( $error ) && self::build_error_retryable( $error ) && $retry_count <= $maximum ) {
            $delay = self::retry_delay( $retry_count );
            $state['state'] = 'retry-scheduled';
            $state['retry_count'] = $retry_count;
            $state['last_error'] = sanitize_text_field( $message );
            $state['message'] = 'A temporary service error interrupted this batch. The rebuild will resume automatically.';
            $state['next_run_utc'] = gmdate( 'c', time() + $delay );
            self::replace_build_state( $state );
            self::schedule_index_build( $state['job_id'] ?? '', $delay );
            return $error;
        }
        $state['state'] = 'failed';
        $state['last_error'] = sanitize_text_field( $message );
        $state['message'] = 'The rebuild stopped safely. The previous durable index remains active; correct the error and choose Resume.';
        $state['failed_utc'] = gmdate( 'c' );
        self::replace_build_state( $state );
        return is_wp_error( $error ) ? $error : new WP_Error( 'sc_rl_v703_build_failed', $message );
    }

    private static function append_build_record( &$state, $record ) {
        if ( ! is_array( $record ) || empty( $record['id'] ) || empty( $record['title'] ) || empty( $record['url'] ) ) {
            $state['skipped_records'] = absint( $state['skipped_records'] ?? 0 ) + 1;
            return false;
        }
        $canonical_url = untrailingslashit( esc_url_raw( $record['url'] ) );
        if ( ! $canonical_url ) {
            $state['skipped_records'] = absint( $state['skipped_records'] ?? 0 ) + 1;
            return false;
        }
        $url_hash = hash( 'sha256', strtolower( $canonical_url ) );
        $seen = isset( $state['seen_url_hashes'] ) && is_array( $state['seen_url_hashes'] ) ? $state['seen_url_hashes'] : array();
        if ( isset( $seen[ $url_hash ] ) ) {
            $state['duplicate_urls'] = absint( $state['duplicate_urls'] ?? 0 ) + 1;
            return false;
        }
        $path = self::build_file_path( $state );
        if ( is_wp_error( $path ) ) {
            return $path;
        }
        $json = wp_json_encode( $record, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
        if ( ! is_string( $json ) || false === @file_put_contents( $path, $json . "\n", FILE_APPEND | LOCK_EX ) ) {
            return new WP_Error( 'sc_rl_v703_build_write', 'A source record could not be written to the private asynchronous staging file.' );
        }
        $seen[ $url_hash ] = 1;
        $state['seen_url_hashes'] = $seen;
        $state['records_discovered'] = absint( $state['records_discovered'] ?? 0 ) + 1;
        $post_type = sanitize_key( $record['post_type'] ?? 'unknown' );
        if ( ! isset( $state['records_by_post_type'][ $post_type ] ) ) {
            $state['records_by_post_type'][ $post_type ] = 0;
        }
        $state['records_by_post_type'][ $post_type ]++;
        return true;
    }

    private static function legacy_record_from_item( $item ) {
        if ( ! is_array( $item ) || empty( $item['title'] ) || empty( $item['url'] ) ) {
            return null;
        }
        $url = esc_url_raw( $item['url'] );
        if ( ! $url ) {
            return null;
        }
        $record = array(
            'id' => 'legacy:' . sanitize_key( isset( $item['id'] ) ? $item['id'] : md5( $url ) ),
            'title' => sanitize_text_field( $item['title'] ),
            'url' => $url,
            'slug' => sanitize_title( wp_parse_url( $url, PHP_URL_PATH ) ),
            'summary' => sanitize_textarea_field( $item['summary'] ?? '' ),
            'content' => '',
            'headings' => array(),
            'post_type' => sanitize_key( $item['type'] ?? 'route' ),
            'taxonomies' => array( 'topics' => isset( $item['topics'] ) && is_array( $item['topics'] ) ? array_map( 'sanitize_text_field', $item['topics'] ) : array() ),
            'series' => '',
            'article_map' => '',
            'parent_title' => '',
            'modified_utc' => sanitize_text_field( $item['modified_utc'] ?? '' ),
            'source' => 'wordpress-index',
            'route_id' => sanitize_key( $item['route_id'] ?? '' ),
            'metadata' => array( 'source_kind' => sanitize_key( $item['source_kind'] ?? '' ) ),
        );
        $record['content_hash'] = self::record_content_hash( $record );
        return $record;
    }

    private static function finalize_build_discovery( $state ) {
        $record_count = absint( $state['records_discovered'] ?? 0 );
        if ( ! $record_count ) {
            return self::handle_build_error( $state, new WP_Error( 'sc_rl_v704_no_sources', 'No published, indexable WordPress records were discovered.' ) );
        }
        // Persist the transition before scanning. Finalization is deliberately bounded so
        // a large staging file can never recreate the synchronous rebuild fatal.
        $state['state'] = 'running';
        $state['stage'] = 'finalizing-discovery';
        $state['progress'] = 48;
        $state['message'] = 'Source discovery complete. Validating the staging file in bounded passes before synchronization.';
        $state['finalization_offset'] = 0;
        $state['finalization_records'] = 0;
        $state['finalization_hashes'] = array();
        $state['finalization_posts'] = array();
        $state['finalization_bytes'] = 0;
        $state['retry_count'] = 0;
        unset( $state['seen_url_hashes'] );
        self::replace_build_state( $state );
        self::schedule_index_build( $state['job_id'], 2 );
        return $state;
    }

    private static function process_build_finalization_step( $state ) {
        $limit = max( 25, min( 250, absint( self::options()['sync_batch_size'] ?? 100 ) ) );
        $batch = self::read_build_batch( $state, absint( $state['finalization_offset'] ?? 0 ), $limit );
        if ( is_wp_error( $batch ) ) {
            return self::handle_build_error( $state, $batch );
        }
        $hashes = isset( $state['finalization_hashes'] ) && is_array( $state['finalization_hashes'] ) ? $state['finalization_hashes'] : array();
        $posts = isset( $state['finalization_posts'] ) && is_array( $state['finalization_posts'] ) ? $state['finalization_posts'] : array();
        foreach ( $batch['records'] as $record ) {
            if ( empty( $record['id'] ) || empty( $record['title'] ) || empty( $record['url'] ) ) {
                return self::handle_build_error( $state, new WP_Error( 'sc_rl_v704_build_record_invalid', 'The private staging file contains an invalid record.' ) );
            }
            $record_id = sanitize_text_field( $record['id'] );
            $hashes[ $record_id ] = sanitize_text_field( $record['content_hash'] ?? self::record_content_hash( $record ) );
            if ( ! empty( $record['metadata']['post_id'] ) ) {
                $posts[ absint( $record['metadata']['post_id'] ) ] = $record_id;
            }
        }
        $state['finalization_hashes'] = $hashes;
        $state['finalization_posts'] = $posts;
        $state['finalization_records'] = absint( $state['finalization_records'] ?? 0 ) + count( $batch['records'] );
        $state['finalization_offset'] = absint( $batch['offset'] );
        $state['finalization_bytes'] = absint( $batch['offset'] );
        $total = max( 1, absint( $state['records_discovered'] ?? 0 ) );
        $state['progress'] = min( 55, 48 + (int) floor( 7 * min( 1, $state['finalization_records'] / $total ) ) );
        $state['message'] = 'Validated ' . $state['finalization_records'] . ' of ' . $total . ' staged record(s) in bounded passes.';
        if ( ! $batch['eof'] ) {
            self::replace_build_state( $state );
            self::schedule_index_build( $state['job_id'], 2 );
            return $state;
        }
        ksort( $hashes );
        $ledger = self::sync_ledger();
        $deleted_ids = array_values( array_diff( array_keys( $ledger['records'] ?? array() ), array_keys( $hashes ) ) );
        $batch_size = max( 25, min( 250, absint( self::options()['sync_batch_size'] ?? 100 ) ) );
        $state['records_discovered'] = absint( $state['finalization_records'] );
        $state['finalization_hashes'] = $hashes;
        $state['deleted_ids'] = $deleted_ids;
        $state['sync_batch_count'] = max( 1, (int) ceil( $state['records_discovered'] / $batch_size ) );
        $state['sync_batch_index'] = 0;
        $state['sync_offset'] = 0;
        $state['stage'] = 'synchronizing-records';
        $state['progress'] = 56;
        $state['message'] = 'Bounded finalization complete. Record batches are staging in Python while the current index remains live.';
        $report = array(
            'version' => self::VERSION,
            'schema' => 'sc-rl-sync-report/7.0.8',
            'job_id' => $state['backend_job_id'],
            'state' => 'running',
            'mode' => 'transactional-replace-async',
            'trigger' => sanitize_key( $state['trigger'] ?? 'manual' ),
            'started_utc' => sanitize_text_field( $state['started_utc'] ?? gmdate( 'c' ) ),
            'completed_utc' => '',
            'synced_records' => 0,
            'accepted_records' => 0,
            'rejected_records' => 0,
            'deleted_records' => count( $deleted_ids ),
            'batches' => array(),
            'source_site' => home_url( '/' ),
            'retry_scheduled' => false,
            'collected_records' => $state['records_discovered'],
            'records_by_post_type' => $state['records_by_post_type'] ?? array(),
            'skipped_records' => absint( $state['skipped_records'] ?? 0 ),
            'duplicate_urls' => absint( $state['duplicate_urls'] ?? 0 ),
            'legacy_skipped' => absint( $state['legacy_skipped'] ?? 0 ),
        );
        self::save_sync_report( $report );
        self::replace_build_state( $state );
        self::schedule_index_build( $state['job_id'], 2 );
        return $state;
    }

    private static function process_build_discovery_step( $state ) {
        $options = self::options();
        $max_records = max( 100, min( 10000, absint( $options['max_records'] ?? 5000 ) ) );
        $batch_size = max( 5, min( 100, absint( $options['source_batch_size'] ?? 40 ) ) );
        if ( empty( $state['post_types'] ) ) {
            $summary = self::source_discovery_summary();
            $saved_index = get_option( SC_RL6_Core::INDEX_OPTION, array() );
            $legacy_total = is_array( $saved_index ) && isset( $saved_index['records'] ) && is_array( $saved_index['records'] ) ? count( $saved_index['records'] ) : 0;
            $state['source_summary'] = $summary;
            $state['post_types'] = array_values( $summary['post_types'] ?? array() );
            $state['legacy_total'] = $legacy_total;
            $state['state'] = 'running';
            $state['stage'] = 'discovering-sources';
            $state['progress'] = 8;
            $state['message'] = 'Discovering public WordPress sources in bounded background batches.';
        }
        if ( absint( $state['records_discovered'] ?? 0 ) >= $max_records ) {
            $state['capacity_reached'] = true;
            return self::finalize_build_discovery( $state );
        }
        $type_index = absint( $state['post_type_index'] ?? 0 );
        $post_types = $state['post_types'];
        if ( $type_index < count( $post_types ) ) {
            $post_type = sanitize_key( $post_types[ $type_index ] );
            $page = max( 1, absint( $state['source_page'] ?? 1 ) );
            $query = new WP_Query( array(
                'post_type' => $post_type,
                'post_status' => 'publish',
                'posts_per_page' => $batch_size,
                'paged' => $page,
                'orderby' => 'ID',
                'order' => 'ASC',
                'fields' => 'ids',
                'no_found_rows' => false,
                'ignore_sticky_posts' => true,
                'suppress_filters' => false,
            ) );
            foreach ( (array) $query->posts as $post_id ) {
                if ( absint( $state['records_discovered'] ?? 0 ) >= $max_records ) {
                    break;
                }
                $record = self::build_post_record( $post_id );
                $appended = self::append_build_record( $state, $record );
                if ( is_wp_error( $appended ) ) {
                    return self::handle_build_error( $state, $appended );
                }
            }
            $max_pages = max( 1, absint( $query->max_num_pages ?? 1 ) );
            if ( ! $query->posts || $page >= $max_pages ) {
                $state['post_type_index'] = $type_index + 1;
                $state['source_page'] = 1;
            } else {
                $state['source_page'] = $page + 1;
            }
        } else {
            $saved_index = get_option( SC_RL6_Core::INDEX_OPTION, array() );
            $legacy = is_array( $saved_index ) && isset( $saved_index['records'] ) && is_array( $saved_index['records'] ) ? array_values( $saved_index['records'] ) : array();
            if ( empty( $state['migrate_legacy'] ) ) {
                $state['legacy_skipped'] = count( $legacy );
                $state['legacy_offset'] = count( $legacy );
                $state['message'] = 'Current WordPress sources are complete. Legacy fallback records were skipped to prevent duplicate discovery and synchronous transition failures.';
                self::replace_build_state( $state );
                return self::finalize_build_discovery( $state );
            }
            $state['stage'] = 'discovering-legacy';
            $offset = absint( $state['legacy_offset'] ?? 0 );
            foreach ( array_slice( $legacy, $offset, $batch_size ) as $item ) {
                if ( absint( $state['records_discovered'] ?? 0 ) >= $max_records ) { break; }
                $appended = self::append_build_record( $state, self::legacy_record_from_item( $item ) );
                if ( is_wp_error( $appended ) ) { return self::handle_build_error( $state, $appended ); }
            }
            $state['legacy_offset'] = min( count( $legacy ), $offset + $batch_size );
            if ( $state['legacy_offset'] >= count( $legacy ) || absint( $state['records_discovered'] ?? 0 ) >= $max_records ) {
                return self::finalize_build_discovery( $state );
            }
        }
        $expected = max( 1, min( $max_records, absint( $state['source_summary']['published_records'] ?? 0 ) + absint( $state['legacy_total'] ?? 0 ) ) );
        $state['progress'] = min( 48, 8 + (int) floor( 40 * min( 1, absint( $state['records_discovered'] ?? 0 ) / $expected ) ) );
        $state['message'] = 'Discovered ' . absint( $state['records_discovered'] ?? 0 ) . ' indexable record(s); the next bounded source batch is queued.';
        $state['next_run_utc'] = gmdate( 'c', time() + 2 );
        self::replace_build_state( $state );
        self::schedule_index_build( $state['job_id'], 2 );
        return $state;
    }

    private static function scan_build_file( $state ) {
        $path = self::build_file_path( $state );
        if ( is_wp_error( $path ) ) {
            return $path;
        }
        $handle = @fopen( $path, 'rb' );
        if ( ! $handle ) {
            return new WP_Error( 'sc_rl_v703_build_read', 'The private asynchronous staging file could not be opened.' );
        }
        $hashes = array();
        $posts = array();
        $count = 0;
        while ( false !== ( $line = fgets( $handle ) ) ) {
            $record = json_decode( trim( $line ), true );
            if ( ! is_array( $record ) || empty( $record['id'] ) ) {
                fclose( $handle );
                return new WP_Error( 'sc_rl_v703_build_record_invalid', 'The private staging file contains an invalid record.' );
            }
            $record_id = sanitize_text_field( $record['id'] );
            $hashes[ $record_id ] = sanitize_text_field( $record['content_hash'] ?? self::record_content_hash( $record ) );
            if ( ! empty( $record['metadata']['post_id'] ) ) {
                $posts[ absint( $record['metadata']['post_id'] ) ] = $record_id;
            }
            $count++;
        }
        fclose( $handle );
        ksort( $hashes );
        return array( 'record_count' => $count, 'hashes' => $hashes, 'posts' => $posts, 'checksum' => self::ledger_checksum( $hashes ) );
    }

    private static function read_build_batch( $state, $offset, $limit ) {
        $path = self::build_file_path( $state );
        if ( is_wp_error( $path ) ) {
            return $path;
        }
        $handle = @fopen( $path, 'rb' );
        if ( ! $handle ) {
            return new WP_Error( 'sc_rl_v703_build_read', 'The private asynchronous staging file could not be opened for synchronization.' );
        }
        if ( $offset > 0 && 0 !== fseek( $handle, $offset ) ) {
            fclose( $handle );
            return new WP_Error( 'sc_rl_v703_build_seek', 'The asynchronous rebuild could not resume from its saved file cursor.' );
        }
        $records = array();
        while ( count( $records ) < $limit && false !== ( $line = fgets( $handle ) ) ) {
            $record = json_decode( trim( $line ), true );
            if ( ! is_array( $record ) ) {
                fclose( $handle );
                return new WP_Error( 'sc_rl_v703_build_record_invalid', 'The private staging file contains invalid JSON.' );
            }
            $records[] = $record;
        }
        $new_offset = ftell( $handle );
        $eof = feof( $handle );
        fclose( $handle );
        return array( 'records' => $records, 'offset' => max( 0, (int) $new_offset ), 'eof' => $eof );
    }

    private static function save_ledger_from_build_file( $state, $backend_result ) {
        $hashes = isset( $state['finalization_hashes'] ) && is_array( $state['finalization_hashes'] ) ? $state['finalization_hashes'] : array();
        $posts = isset( $state['finalization_posts'] ) && is_array( $state['finalization_posts'] ) ? $state['finalization_posts'] : array();
        if ( ! $hashes ) {
            return new WP_Error( 'sc_rl_v704_finalization_ledger_missing', 'The bounded finalization ledger is missing; the committed index was left intact.' );
        }
        ksort( $hashes );
        $checksum = self::ledger_checksum( $hashes );
        update_option( self::LEDGER_OPTION, array(
            'schema' => 'sc-rl-sync-ledger/1.0',
            'records' => $hashes,
            'posts' => $posts,
            'checksum' => sanitize_text_field( $backend_result['checksum'] ?? $checksum ),
            'index_version' => absint( $backend_result['index_version'] ?? 0 ),
            'updated_utc' => gmdate( 'c' ),
        ), false );
        return array( 'record_count' => count( $hashes ), 'hashes' => $hashes, 'posts' => $posts, 'checksum' => $checksum );
    }

    private static function backend_sync_job_status( $job_id ) {
        $job_id = sanitize_text_field( $job_id );
        if ( ! $job_id ) {
            return new WP_Error( 'sc_rl_v705_missing_backend_job', 'The backend transaction ID is missing.' );
        }
        return self::request( '/v1/knowledge/sync/jobs/' . rawurlencode( $job_id ), 'GET' );
    }

    private static function backend_reconcile_sync_job( $job_id, $expected_batch_count, $recovery_generation = 0 ) {
        $job_id = sanitize_text_field( $job_id );
        if ( ! $job_id ) {
            return new WP_Error( 'sc_rl_v708_missing_backend_job', 'The backend transaction ID is missing.' );
        }
        return self::request( '/v1/knowledge/sync/jobs/' . rawurlencode( $job_id ) . '/reconcile', 'POST', array(
            'expected_batch_count' => absint( $expected_batch_count ),
            'recovery_generation' => absint( $recovery_generation ),
        ) );
    }

    private static function backend_queue_sync_commit( $job_id ) {
        $job_id = sanitize_text_field( $job_id );
        if ( ! $job_id ) {
            return new WP_Error( 'sc_rl_v707_missing_backend_job', 'The backend transaction ID is missing.' );
        }
        return self::request( '/v1/knowledge/sync/jobs/' . rawurlencode( $job_id ) . '/commit', 'POST', array() );
    }

    private static function backend_advance_sync_commit( $job_id ) {
        $job_id = sanitize_text_field( $job_id );
        if ( ! $job_id ) {
            return new WP_Error( 'sc_rl_v707_missing_backend_job', 'The backend transaction ID is missing.' );
        }
        return self::request( '/v1/knowledge/sync/jobs/' . rawurlencode( $job_id ) . '/commit/step', 'POST', array() );
    }

    private static function activate_committed_build( $state, $backend_status = array() ) {
        $summary = self::request( '/v1/knowledge/summary', 'GET' );
        if ( is_wp_error( $summary ) ) {
            return self::handle_build_error( $state, $summary );
        }
        if ( empty( $summary['total_records'] ) ) {
            return self::handle_build_error( $state, new WP_Error( 'sc_rl_v706_committed_index_empty', 'The backend reported a committed transaction but the active index is empty.' ) );
        }
        $ledger = self::save_ledger_from_build_file( $state, $summary );
        if ( is_wp_error( $ledger ) ) {
            return self::handle_build_error( $state, $ledger );
        }
        update_option( self::QUEUE_OPTION, array(), false );
        $report = self::latest_sync_report();
        $report = is_array( $report ) ? $report : array();
        $report['state'] = absint( $backend_status['rejected_records'] ?? $report['rejected_records'] ?? 0 ) ? 'completed-with-rejections' : 'completed';
        $report['completed_utc'] = gmdate( 'c' );
        $report['synced_records'] = absint( $state['records_synced'] ?? $state['records_discovered'] ?? 0 );
        $report['accepted_records'] = max( absint( $report['accepted_records'] ?? 0 ), absint( $backend_status['staged_records'] ?? $state['records_synced'] ?? 0 ) );
        $report['rejected_records'] = absint( $backend_status['rejected_records'] ?? $report['rejected_records'] ?? 0 );
        $report['index_version'] = absint( $summary['index_version'] ?? 0 );
        $report['checksum'] = sanitize_text_field( $summary['checksum'] ?? '' );
        $report['backend_commit'] = array(
            'state' => sanitize_key( $backend_status['state'] ?? 'completed' ),
            'phase' => sanitize_key( $backend_status['commit_phase'] ?? 'completed' ),
            'progress' => absint( $backend_status['commit_progress'] ?? 100 ),
            'activation_records' => absint( $backend_status['activation_records'] ?? $summary['total_records'] ?? 0 ),
            'indexed_chunks' => absint( $backend_status['indexed_chunks'] ?? $summary['indexed_chunks'] ?? 0 ),
        );
        self::save_sync_report( $report );
        update_option( self::STATUS_OPTION, array_merge( (array) get_option( self::STATUS_OPTION, array() ), array(
            'state' => 'online',
            'last_sync_utc' => gmdate( 'c' ),
            'synced_records' => absint( $state['records_synced'] ?? 0 ),
            'accepted_records' => absint( $report['accepted_records'] ?? 0 ),
            'rejected_records' => absint( $report['rejected_records'] ?? 0 ),
            'job_id' => sanitize_text_field( $state['backend_job_id'] ?? '' ),
            'index_version' => absint( $summary['index_version'] ?? 0 ),
            'checksum' => sanitize_text_field( $summary['checksum'] ?? '' ),
            'storage_engine' => 'sqlite',
            'backend_result' => $summary,
            'sync_report' => $report,
        ) ), false );
        $state['backend_transaction_status'] = is_array( $backend_status ) ? $backend_status : array();
        $state['backend_result'] = $summary;
        $state['stage'] = 'verifying-index';
        $state['state'] = 'queued';
        $state['progress'] = 90;
        $state['message'] = 'The backend activated the replacement index outside the WordPress request. Verifying the committed knowledge index.';
        $state['last_error'] = '';
        self::replace_build_state( $state );
        self::schedule_index_build( $state['job_id'], 2 );
        return $state;
    }

    private static function local_reconciliation_status( $state, $status ) {
        $state = is_array( $state ) ? $state : array();
        $status = is_array( $status ) ? $status : array();
        $expected = max( 0, absint( $state['sync_batch_count'] ?? 0 ) );
        $actual = max( 0, absint( $status['batch_count'] ?? 0 ) );
        $received = isset( $status['received_batches'] ) && is_array( $status['received_batches'] ) ? array_values( array_unique( array_filter( array_map( 'absint', $status['received_batches'] ) ) ) ) : array();
        sort( $received, SORT_NUMERIC );
        $missing = isset( $status['missing_batches'] ) && is_array( $status['missing_batches'] ) ? array_values( array_unique( array_filter( array_map( 'absint', $status['missing_batches'] ) ) ) ) : array();
        if ( ! empty( $status['committed'] ) ) {
            $action = 'committed';
            $transaction_state = 'committed';
        } elseif ( empty( $status['exists'] ) ) {
            $action = 'replay-all';
            $transaction_state = 'missing';
        } elseif ( $expected > 0 && $actual === $expected && count( $received ) === $expected && empty( $missing ) ) {
            $action = 'activate';
            $transaction_state = 'complete';
        } elseif ( 0 === $actual && empty( $received ) ) {
            $action = 'replay-all';
            $transaction_state = 'empty-shell';
        } elseif ( $expected > 0 && $actual !== $expected ) {
            $action = 'replay-all';
            $transaction_state = 'batch-count-mismatch';
        } elseif ( ! empty( $missing ) ) {
            $action = 'replay-missing';
            $transaction_state = 'incomplete';
        } else {
            $action = 'replay-all';
            $transaction_state = 'indeterminate';
        }
        return array_merge( $status, array(
            'reconciliation_action' => $action,
            'transaction_state' => $transaction_state,
            'expected_batch_count' => $expected,
            'backend_batch_count' => $actual,
            'received_batch_count' => count( $received ),
            'received_batches' => $received,
            'missing_batches' => $missing,
        ) );
    }

    private static function reconciliation_status( $state, $status = array() ) {
        $expected = absint( $state['sync_batch_count'] ?? 0 );
        $remote = self::backend_reconcile_sync_job( $state['backend_job_id'] ?? '', $expected, absint( $state['recovery_generation'] ?? 0 ) );
        if ( ! is_wp_error( $remote ) && is_array( $remote ) ) {
            return $remote;
        }
        return self::local_reconciliation_status( $state, $status );
    }

    private static function continue_after_complete_reconciliation( $state, $status ) {
        $state['backend_transaction_status'] = $status;
        $state['backend_missing_batches'] = array();
        $state['backend_received_batches'] = isset( $status['received_batches'] ) && is_array( $status['received_batches'] ) ? array_values( array_map( 'absint', $status['received_batches'] ) ) : array();
        $state['backend_transaction_state'] = sanitize_key( $status['transaction_state'] ?? 'complete' );
        $state['backend_reconciliation_action'] = sanitize_key( $status['reconciliation_action'] ?? 'activate' );
        $state['transaction_replay_count'] = 0;
        $state['reconciliation_completed_utc'] = gmdate( 'c' );
        $state['last_error'] = '';
        $backend_state = sanitize_key( $status['state'] ?? '' );
        $state['stage'] = in_array( $backend_state, array( 'commit-queued', 'committing', 'commit-stalled' ), true ) ? 'waiting-backend-commit' : 'queuing-backend-commit';
        $state['state'] = 'queued';
        $state['progress'] = 87;
        $state['message'] = 'Backend reconciliation confirms that every expected source batch is retained. Continuing with durable index activation.';
        self::replace_build_state( $state );
        self::schedule_index_build( $state['job_id'], 2 );
        return $state;
    }

    private static function process_build_backend_commit_step( $state ) {
        $job_id = sanitize_text_field( $state['backend_job_id'] ?? '' );
        $status = self::backend_sync_job_status( $job_id );
        if ( is_wp_error( $status ) ) {
            return self::handle_build_error( $state, $status );
        }
        if ( empty( $status['exists'] ) ) {
            return self::begin_transaction_replay( $state, $status, 'backend-ephemeral-state-lost-before-activation' );
        }
        $reconciliation = self::local_reconciliation_status( $state, $status );
        $state['backend_transaction_state'] = sanitize_key( $reconciliation['transaction_state'] ?? '' );
        $state['backend_reconciliation_action'] = sanitize_key( $reconciliation['reconciliation_action'] ?? '' );
        if ( in_array( sanitize_key( $reconciliation['reconciliation_action'] ?? '' ), array( 'replay-all', 'replay-missing' ), true ) ) {
            $state['stage'] = 'reconciling-transaction';
            $state['state'] = 'queued';
            $state['progress'] = 86;
            $state['backend_transaction_status'] = $reconciliation;
            $state['message'] = 'Backend transaction state requires reconciliation before activation can continue.';
            self::replace_build_state( $state );
            self::schedule_index_build( $state['job_id'], 2 );
            return $state;
        }

        $state['backend_transaction_status'] = $status;
        $state['backend_missing_batches'] = isset( $status['missing_batches'] ) && is_array( $status['missing_batches'] ) ? array_values( array_map( 'absint', $status['missing_batches'] ) ) : array();
        $state['backend_received_batches'] = isset( $status['received_batches'] ) && is_array( $status['received_batches'] ) ? array_values( array_map( 'absint', $status['received_batches'] ) ) : array();
        $state['backend_commit_phase'] = sanitize_key( $status['commit_phase'] ?? $status['state'] ?? '' );
        $state['backend_commit_progress'] = absint( $status['commit_progress'] ?? 0 );
        $state['backend_activation_records'] = absint( $status['activation_records'] ?? 0 );
        $state['backend_activation_total'] = absint( $status['activation_total'] ?? $status['staged_records'] ?? 0 );
        $state['backend_chunk_records_processed'] = absint( $status['chunk_records_processed'] ?? 0 );
        $state['backend_checksum_records'] = absint( $status['checksum_records'] ?? 0 );
        $state['backend_indexed_chunks'] = absint( $status['indexed_chunks'] ?? 0 );
        $state['backend_activation_steps'] = absint( $status['activation_step_count'] ?? 0 );
        $state['backend_activation_restarts'] = absint( $status['activation_restart_count'] ?? 0 );
        $state['backend_storage_persistent'] = ! empty( $status['storage_persistent'] );

        if ( ! empty( $status['committed'] ) ) {
            return self::activate_committed_build( $state, $status );
        }
        if ( ! empty( $state['backend_missing_batches'] ) ) {
            $state['stage'] = 'reconciling-transaction';
            $state['state'] = 'queued';
            $state['progress'] = 86;
            $state['message'] = 'The backend is missing staged batches. Research Librarian will replay the durable WordPress staging file before activation.';
            self::replace_build_state( $state );
            self::schedule_index_build( $state['job_id'], 2 );
            return $state;
        }

        $stage = sanitize_key( $state['stage'] ?? '' );
        $backend_state = sanitize_key( $status['state'] ?? '' );
        $phase = sanitize_key( $status['commit_phase'] ?? '' );
        if ( 'queuing-backend-commit' === $stage || in_array( $backend_state, array( 'ready-to-commit', 'ready-to-commit-with-rejections' ), true ) || ! $phase || in_array( $phase, array( 'staged', 'activating' ), true ) ) {
            $queued = self::backend_queue_sync_commit( $job_id );
            if ( is_wp_error( $queued ) ) {
                $after = self::backend_sync_job_status( $job_id );
                if ( is_wp_error( $after ) || empty( $after['exists'] ) ) {
                    return self::begin_transaction_replay( $state, is_wp_error( $after ) ? array() : $after, 'backend-queue-state-lost' );
                }
                $status = $after;
            } elseif ( is_array( $queued ) ) {
                $status = array_merge( $status, $queued );
            }
            if ( ! empty( $status['committed'] ) ) {
                return self::activate_committed_build( $state, $status );
            }
        }

        // v7.0.8 advances exactly one bounded backend step per WordPress job
        // iteration. There is no in-process FastAPI background worker to lose.
        $advanced = self::backend_advance_sync_commit( $job_id );
        if ( is_wp_error( $advanced ) ) {
            $after = self::backend_sync_job_status( $job_id );
            if ( ! is_wp_error( $after ) && ! empty( $after['committed'] ) ) {
                return self::activate_committed_build( $state, $after );
            }
            if ( ! is_wp_error( $after ) && empty( $after['exists'] ) ) {
                return self::begin_transaction_replay( $state, $after, 'backend-state-lost-during-activation-step' );
            }
            $message = ! is_wp_error( $after ) && ! empty( $after['error'] ) ? sanitize_text_field( $after['error'] ) : $advanced->get_error_message();
            return self::handle_build_error( $state, new WP_Error( 'sc_rl_v707_activation_step_failed', $message ) );
        }
        $status = is_array( $advanced ) ? $advanced : self::backend_sync_job_status( $job_id );
        if ( is_wp_error( $status ) ) {
            return self::handle_build_error( $state, $status );
        }
        if ( ! empty( $status['committed'] ) ) {
            return self::activate_committed_build( $state, $status );
        }

        $state['backend_transaction_status'] = $status;
        $state['backend_commit_phase'] = sanitize_key( $status['commit_phase'] ?? $status['state'] ?? '' );
        $state['backend_commit_progress'] = absint( $status['commit_progress'] ?? 0 );
        $state['backend_activation_records'] = absint( $status['activation_records'] ?? 0 );
        $state['backend_activation_total'] = absint( $status['activation_total'] ?? $status['staged_records'] ?? 0 );
        $state['backend_chunk_records_processed'] = absint( $status['chunk_records_processed'] ?? 0 );
        $state['backend_checksum_records'] = absint( $status['checksum_records'] ?? 0 );
        $state['backend_indexed_chunks'] = absint( $status['indexed_chunks'] ?? 0 );
        $state['backend_activation_steps'] = absint( $status['activation_step_count'] ?? 0 );
        $state['backend_activation_restarts'] = absint( $status['activation_restart_count'] ?? 0 );
        $state['backend_storage_persistent'] = ! empty( $status['storage_persistent'] );

        $phase_labels = array(
            'preparing' => 'Preparing a restart-safe shadow index',
            'copying-records' => 'Copying records into the shadow index',
            'building-chunks' => 'Building retrieval chunks in bounded groups',
            'checksumming' => 'Verifying the replacement index',
            'ready-to-switch' => 'Replacement verified; preparing the atomic switch',
            'switching' => 'Switching the verified replacement into service',
        );
        $phase = sanitize_key( $state['backend_commit_phase'] );
        $label = $phase_labels[ $phase ] ?? 'Advancing durable index activation';
        $progress = max( 0, min( 100, absint( $state['backend_commit_progress'] ) ) );
        $state['stage'] = 'waiting-backend-commit';
        $state['state'] = 'queued';
        $state['progress'] = min( 89, 87 + (int) floor( $progress / 50 ) );
        $state['message'] = $label . ' · ' . $progress . '%. Each step saves a durable cursor before the next request.';
        $state['next_run_utc'] = gmdate( 'c', time() + 2 );
        self::replace_build_state( $state );
        self::schedule_index_build( $state['job_id'], 2 );
        return $state;
    }

    private static function begin_transaction_replay( $state, $backend_status = array(), $reason = '' ) {
        $state = is_array( $state ) ? $state : array();
        $backend_status = self::local_reconciliation_status( $state, is_array( $backend_status ) ? $backend_status : array() );
        $action = sanitize_key( $backend_status['reconciliation_action'] ?? '' );
        if ( in_array( $action, array( 'activate', 'committed' ), true ) ) {
            if ( 'committed' === $action || ! empty( $backend_status['committed'] ) ) {
                return self::activate_committed_build( $state, $backend_status );
            }
            return self::continue_after_complete_reconciliation( $state, $backend_status );
        }

        $attempt = absint( $state['transaction_replay_count'] ?? 0 ) + 1;
        $limit = max( 1, min( 5, absint( $state['transaction_replay_limit'] ?? 3 ) ) );
        if ( $attempt > $limit ) {
            $missing_values = isset( $backend_status['missing_batches'] ) && is_array( $backend_status['missing_batches'] ) ? array_values( array_filter( array_map( 'absint', $backend_status['missing_batches'] ) ) ) : array();
            $missing = $missing_values ? implode( ', ', $missing_values ) : 'none reported';
            $transaction_state = sanitize_key( $backend_status['transaction_state'] ?? $backend_status['state'] ?? 'unknown' );
            $expected = absint( $backend_status['expected_batch_count'] ?? $state['sync_batch_count'] ?? 0 );
            $actual = absint( $backend_status['backend_batch_count'] ?? $backend_status['batch_count'] ?? 0 );
            $retained = absint( $backend_status['received_batch_count'] ?? count( $backend_status['received_batches'] ?? array() ) );
            return self::handle_build_error( $state, new WP_Error(
                'sc_rl_v708_reconciliation_exhausted',
                'The backend transaction could not be reconciled after ' . $limit . ' replay attempt(s). Transaction state: ' . $transaction_state . '; expected batches: ' . $expected . '; backend batch count: ' . $actual . '; retained batches: ' . $retained . '; missing batches: ' . $missing . '.'
            ) );
        }

        $previous_job_id = sanitize_text_field( $state['backend_job_id'] ?? $state['job_id'] ?? '' );
        $generation = max( 1, absint( $state['recovery_generation'] ?? 0 ) );
        $state['previous_backend_job_id'] = $previous_job_id;
        $state['backend_job_id'] = sanitize_text_field( ( $state['job_id'] ?? 'async-sync' ) . '-recovery-' . $generation . '-replay-' . $attempt . '-' . gmdate( 'His' ) );
        $state['transaction_replay_count'] = $attempt;
        $state['backend_transaction_status'] = $backend_status;
        $state['backend_transaction_state'] = sanitize_key( $backend_status['transaction_state'] ?? 'unknown' );
        $state['backend_reconciliation_action'] = 'replay-all';
        $state['backend_missing_batches'] = isset( $backend_status['missing_batches'] ) && is_array( $backend_status['missing_batches'] ) ? array_values( array_map( 'absint', $backend_status['missing_batches'] ) ) : array();
        $state['backend_received_batches'] = isset( $backend_status['received_batches'] ) && is_array( $backend_status['received_batches'] ) ? array_values( array_map( 'absint', $backend_status['received_batches'] ) ) : array();
        $state['reconciliation_started_utc'] = gmdate( 'c' );
        $state['stage'] = 'synchronizing-records';
        $state['state'] = 'queued';
        $state['sync_batch_index'] = 0;
        $state['sync_offset'] = 0;
        $state['records_synced'] = 0;
        $state['failed_records'] = 0;
        $state['retry_count'] = 0;
        $state['progress'] = 56;
        $state['replay_batch_numbers'] = array();
        $state['replay_batch_cursor'] = 0;
        $transaction_state = sanitize_key( $backend_status['transaction_state'] ?? 'unknown' );
        $state['message'] = 'Backend transaction recovery started from the durable WordPress staging file. Recovery state: ' . str_replace( '-', ' ', $transaction_state ) . '; replaying all source batches as a fresh transaction.';
        if ( $reason ) {
            $state['reconciliation_reason'] = sanitize_text_field( $reason );
        }
        self::replace_build_state( $state );
        self::schedule_index_build( $state['job_id'], 2 );
        return $state;
    }

    private static function process_build_missing_batch_replay_step( $state ) {
        $numbers = isset( $state['replay_batch_numbers'] ) && is_array( $state['replay_batch_numbers'] ) ? array_values( array_filter( array_map( 'absint', $state['replay_batch_numbers'] ) ) ) : array();
        $cursor = absint( $state['replay_batch_cursor'] ?? 0 );
        if ( $cursor >= count( $numbers ) ) {
            $state['stage'] = 'reconciling-transaction';
            $state['state'] = 'queued';
            $state['progress'] = 86;
            $state['message'] = 'Missing source batches were replayed. Verifying backend transaction completeness.';
            self::replace_build_state( $state );
            self::schedule_index_build( $state['job_id'], 2 );
            return $state;
        }
        $batch_number = absint( $numbers[ $cursor ] );
        $offsets = isset( $state['sync_batch_offsets'] ) && is_array( $state['sync_batch_offsets'] ) ? $state['sync_batch_offsets'] : array();
        $offset = isset( $offsets[ $batch_number ]['start'] ) ? absint( $offsets[ $batch_number ]['start'] ) : null;
        if ( null === $offset ) {
            return self::begin_transaction_replay( $state, $state['backend_transaction_status'] ?? array(), 'missing-batch-offset-ledger-unavailable' );
        }
        $batch_size = max( 25, min( 250, absint( self::options()['sync_batch_size'] ?? 100 ) ) );
        $batch_data = self::read_build_batch( $state, $offset, $batch_size );
        if ( is_wp_error( $batch_data ) ) {
            return self::handle_build_error( $state, $batch_data );
        }
        $batch_count = max( 1, absint( $state['sync_batch_count'] ?? 1 ) );
        $response = self::request( '/v1/knowledge/sync', 'POST', array(
            'records' => $batch_data['records'],
            'deleted_ids' => $batch_number === $batch_count ? array_values( $state['deleted_ids'] ?? array() ) : array(),
            'mode' => 'replace',
            'source_site' => home_url( '/' ),
            'generated_utc' => gmdate( 'c' ),
            'job_id' => sanitize_text_field( $state['backend_job_id'] ),
            'batch_index' => $batch_number,
            'batch_count' => $batch_count,
            'reason' => 'wordpress-missing-batch-replay-v7.0.8',
            'defer_commit' => true,
        ) );
        if ( is_wp_error( $response ) ) {
            return self::handle_build_error( $state, $response );
        }
        $state['replay_batch_cursor'] = $cursor + 1;
        $state['retry_count'] = 0;
        $state['message'] = 'Replayed missing backend batch ' . $batch_number . ' · ' . $state['replay_batch_cursor'] . ' of ' . count( $numbers ) . ' recovery batch(es).';
        self::replace_build_state( $state );
        self::schedule_index_build( $state['job_id'], 2 );
        return $state;
    }

    private static function process_build_reconciliation_step( $state ) {
        $status = self::backend_sync_job_status( $state['backend_job_id'] ?? '' );
        if ( is_wp_error( $status ) ) {
            $status = array( 'exists' => false, 'state' => 'unreachable', 'error' => $status->get_error_message() );
        }
        $status = self::reconciliation_status( $state, $status );
        $state['backend_transaction_status'] = $status;
        $state['backend_transaction_state'] = sanitize_key( $status['transaction_state'] ?? 'unknown' );
        $state['backend_reconciliation_action'] = sanitize_key( $status['reconciliation_action'] ?? 'replay-all' );
        $state['backend_missing_batches'] = isset( $status['missing_batches'] ) && is_array( $status['missing_batches'] ) ? array_values( array_map( 'absint', $status['missing_batches'] ) ) : array();
        $state['backend_received_batches'] = isset( $status['received_batches'] ) && is_array( $status['received_batches'] ) ? array_values( array_map( 'absint', $status['received_batches'] ) ) : array();

        $action = sanitize_key( $status['reconciliation_action'] ?? '' );
        if ( 'committed' === $action || ! empty( $status['committed'] ) ) {
            return self::activate_committed_build( $state, $status );
        }
        if ( 'activate' === $action ) {
            return self::continue_after_complete_reconciliation( $state, $status );
        }
        if ( 'replay-missing' === $action ) {
            $offsets = isset( $state['sync_batch_offsets'] ) && is_array( $state['sync_batch_offsets'] ) ? $state['sync_batch_offsets'] : array();
            $missing = $state['backend_missing_batches'];
            $can_replay_missing = ! empty( $missing );
            foreach ( $missing as $batch_number ) {
                if ( ! isset( $offsets[ $batch_number ]['start'] ) ) {
                    $can_replay_missing = false;
                    break;
                }
            }
            if ( $can_replay_missing ) {
                $state['stage'] = 'replaying-missing-batches';
                $state['state'] = 'queued';
                $state['replay_batch_numbers'] = $missing;
                $state['replay_batch_cursor'] = 0;
                $state['progress'] = 86;
                $state['message'] = 'The backend retained part of the transaction. Replaying only ' . count( $missing ) . ' missing batch(es) from the WordPress offset ledger.';
                self::replace_build_state( $state );
                self::schedule_index_build( $state['job_id'], 2 );
                return $state;
            }
        }
        return self::begin_transaction_replay( $state, $status, 'backend-' . sanitize_key( $status['transaction_state'] ?? 'state-lost' ) );
    }

    private static function process_build_sync_step( $state ) {
        $options = self::options();
        $batch_size = max( 25, min( 250, absint( $options['sync_batch_size'] ?? 100 ) ) );
        $batch_index = absint( $state['sync_batch_index'] ?? 0 ) + 1;
        $batch_start_offset = absint( $state['sync_offset'] ?? 0 );
        $batch_count = max( 1, absint( $state['sync_batch_count'] ?? 1 ) );
        $batch_data = self::read_build_batch( $state, absint( $state['sync_offset'] ?? 0 ), $batch_size );
        if ( is_wp_error( $batch_data ) ) {
            return self::handle_build_error( $state, $batch_data );
        }
        $records = $batch_data['records'];
        if ( ! $records ) {
            return self::handle_build_error( $state, new WP_Error( 'sc_rl_v703_empty_sync_batch', 'The asynchronous rebuild reached an empty synchronization batch before completion.' ) );
        }
        $is_final = $batch_index >= $batch_count;
        $response = self::request( '/v1/knowledge/sync', 'POST', array(
            'records' => $records,
            'deleted_ids' => $is_final ? array_values( $state['deleted_ids'] ?? array() ) : array(),
            'mode' => 'replace',
            'source_site' => home_url( '/' ),
            'generated_utc' => gmdate( 'c' ),
            'job_id' => sanitize_text_field( $state['backend_job_id'] ),
            'batch_index' => $batch_index,
            'batch_count' => $batch_count,
            'reason' => 'wordpress-async-full-sync-v7.0.8',
            'defer_commit' => true,
        ) );

        if ( is_wp_error( $response ) ) {
            if ( $is_final ) {
                $transaction_status = self::backend_sync_job_status( $state['backend_job_id'] );
                if ( ! is_wp_error( $transaction_status ) ) {
                    $transaction_status = self::reconciliation_status( $state, $transaction_status );
                    $state['backend_transaction_status'] = $transaction_status;
                    $state['backend_transaction_state'] = sanitize_key( $transaction_status['transaction_state'] ?? '' );
                    $state['backend_reconciliation_action'] = sanitize_key( $transaction_status['reconciliation_action'] ?? '' );
                    $state['backend_missing_batches'] = isset( $transaction_status['missing_batches'] ) && is_array( $transaction_status['missing_batches'] ) ? array_values( array_map( 'absint', $transaction_status['missing_batches'] ) ) : array();
                    $state['backend_received_batches'] = isset( $transaction_status['received_batches'] ) && is_array( $transaction_status['received_batches'] ) ? array_values( array_map( 'absint', $transaction_status['received_batches'] ) ) : array();
                    $action = sanitize_key( $transaction_status['reconciliation_action'] ?? '' );
                    if ( 'committed' === $action || ! empty( $transaction_status['committed'] ) ) {
                        $state['sync_batch_index'] = $batch_index;
                        $state['sync_offset'] = absint( $batch_data['offset'] );
                        $state['records_synced'] = max( absint( $state['records_synced'] ?? 0 ), absint( $transaction_status['activation_records'] ?? $transaction_status['staged_records'] ?? 0 ) );
                        return self::activate_committed_build( $state, $transaction_status );
                    }
                    if ( 'activate' === $action ) {
                        $state['sync_batch_index'] = $batch_index;
                        $state['sync_offset'] = absint( $batch_data['offset'] );
                        $state['records_synced'] = max( absint( $state['records_synced'] ?? 0 ), absint( $transaction_status['staged_records'] ?? 0 ) );
                        return self::continue_after_complete_reconciliation( $state, $transaction_status );
                    }
                    $state['stage'] = 'reconciling-transaction';
                    $state['state'] = 'queued';
                    $state['progress'] = 86;
                    $state['message'] = 'The final staging response was ambiguous. Transaction-state reconciliation will determine whether to replay missing work or recreate the backend transaction.';
                    self::replace_build_state( $state );
                    self::schedule_index_build( $state['job_id'], 2 );
                    return $state;
                }
            }
            return self::handle_build_error( $state, $response );
        }

        $report = self::latest_sync_report();
        $report = is_array( $report ) ? $report : array();
        $report['batches'] = isset( $report['batches'] ) && is_array( $report['batches'] ) ? $report['batches'] : array();
        $report['batches'][] = array(
            'batch' => $batch_index,
            'batch_count' => $batch_count,
            'mode' => 'replace',
            'records_sent' => count( $records ),
            'deleted_ids_sent' => $is_final ? count( $state['deleted_ids'] ?? array() ) : 0,
            'state' => ! empty( $response['committed'] ) ? 'committed' : ( $is_final ? 'ready-to-commit' : 'staged' ),
            'accepted_records' => absint( $response['accepted'] ?? count( $records ) ),
            'rejected_records' => absint( $response['rejected'] ?? 0 ),
            'backend_total_records' => absint( $response['total_records'] ?? 0 ),
            'backend_state' => sanitize_key( $response['state'] ?? '' ),
            'completed_utc' => gmdate( 'c' ),
        );
        if ( count( $report['batches'] ) > 100 ) {
            $report['batches'] = array_slice( $report['batches'], -100 );
        }
        $report['synced_records'] = absint( $report['synced_records'] ?? 0 ) + count( $records );
        $report['accepted_records'] = absint( $report['accepted_records'] ?? 0 ) + absint( $response['accepted'] ?? count( $records ) );
        $report['rejected_records'] = absint( $report['rejected_records'] ?? 0 ) + absint( $response['rejected'] ?? 0 );
        self::save_sync_report( $report );

        $state['sync_batch_index'] = $batch_index;
        $state['sync_offset'] = absint( $batch_data['offset'] );
        $state['sync_batch_offsets'] = isset( $state['sync_batch_offsets'] ) && is_array( $state['sync_batch_offsets'] ) ? $state['sync_batch_offsets'] : array();
        $state['sync_batch_offsets'][ $batch_index ] = array(
            'start' => $batch_start_offset,
            'end' => absint( $batch_data['offset'] ),
            'records' => count( $records ),
        );
        $state['records_synced'] = absint( $state['records_synced'] ?? 0 ) + count( $records );
        $state['failed_records'] = absint( $state['failed_records'] ?? 0 ) + absint( $response['rejected'] ?? 0 );
        $state['retry_count'] = 0;
        $state['progress'] = min( 86, 56 + (int) floor( 30 * min( 1, $batch_index / $batch_count ) ) );
        $state['message'] = 'Staged batch ' . $batch_index . ' of ' . $batch_count . ' · ' . $state['records_synced'] . ' record(s) processed.';

        if ( $is_final ) {
            if ( ! empty( $response['committed'] ) ) {
                // Backward-compatible path for a pre-v7.0.8 backend.
                return self::activate_committed_build( $state, $response );
            }
            $transaction_status = self::backend_sync_job_status( $state['backend_job_id'] );
            if ( is_wp_error( $transaction_status ) ) {
                return self::handle_build_error( $state, $transaction_status );
            }
            $transaction_status = self::reconciliation_status( $state, $transaction_status );
            $state['backend_transaction_status'] = $transaction_status;
            $state['backend_transaction_state'] = sanitize_key( $transaction_status['transaction_state'] ?? '' );
            $state['backend_reconciliation_action'] = sanitize_key( $transaction_status['reconciliation_action'] ?? '' );
            $state['backend_received_batches'] = isset( $transaction_status['received_batches'] ) && is_array( $transaction_status['received_batches'] ) ? array_values( array_map( 'absint', $transaction_status['received_batches'] ) ) : array();
            $state['backend_missing_batches'] = isset( $transaction_status['missing_batches'] ) && is_array( $transaction_status['missing_batches'] ) ? array_values( array_map( 'absint', $transaction_status['missing_batches'] ) ) : array();
            $action = sanitize_key( $transaction_status['reconciliation_action'] ?? '' );
            if ( 'committed' === $action || ! empty( $transaction_status['committed'] ) ) {
                return self::activate_committed_build( $state, $transaction_status );
            }
            if ( 'activate' === $action ) {
                return self::continue_after_complete_reconciliation( $state, $transaction_status );
            }
            $state['stage'] = 'reconciling-transaction';
            $state['state'] = 'queued';
            $state['progress'] = 86;
            $state['message'] = 'Source staging completed, but the backend transaction manifest is not complete. Starting deterministic transaction reconciliation.';
        }
        $state['next_run_utc'] = gmdate( 'c', time() + 2 );
        self::replace_build_state( $state );
        self::schedule_index_build( $state['job_id'], 2 );
        return $state;
    }

    private static function create_wordpress_snapshot_from_build_file( $state, $reason ) {
        $hashes = isset( $state['finalization_hashes'] ) && is_array( $state['finalization_hashes'] ) ? $state['finalization_hashes'] : array();
        if ( ! $hashes ) {
            return new WP_Error( 'sc_rl_v704_snapshot_ledger_missing', 'The bounded finalization ledger is unavailable for snapshot creation.' );
        }
        $scan = array( 'record_count' => count( $hashes ), 'checksum' => self::ledger_checksum( $hashes ) );
        $directory = self::ensure_snapshot_directory();
        if ( is_wp_error( $directory ) ) {
            return $directory;
        }
        $snapshot_id = 'wp-' . gmdate( 'Ymd-His' ) . '-' . wp_generate_password( 8, false, false );
        $created = gmdate( 'c' );
        $compressed = function_exists( 'gzopen' ) && function_exists( 'gzwrite' );
        $filename = sanitize_file_name( $snapshot_id . ( $compressed ? '.json.gz' : '.json' ) );
        $path = trailingslashit( $directory ) . $filename;
        $handle = $compressed ? @gzopen( $path, 'wb6' ) : @fopen( $path, 'wb' );
        if ( ! $handle ) {
            return new WP_Error( 'sc_rl_v703_snapshot_write', 'The canonical snapshot file could not be opened for streaming.' );
        }
        $writer = static function ( $data ) use ( $compressed, $handle ) {
            return $compressed ? gzwrite( $handle, $data ) : fwrite( $handle, $data );
        };
        $header = array(
            'schema' => 'sc-research-librarian-wordpress-snapshot/3.1',
            'snapshot_id' => $snapshot_id,
            'created_utc' => $created,
            'reason' => sanitize_text_field( $reason ),
            'source_site' => home_url( '/' ),
            'manifest' => array(
                'record_count' => absint( $scan['record_count'] ),
                'checksum' => sanitize_text_field( $scan['checksum'] ),
                'plugin_version' => self::VERSION,
                'generated_by' => 'wordpress-canonical-source-async',
            ),
        );
        $header_json = wp_json_encode( $header, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
        $prefix = substr( $header_json, 0, -1 ) . ',"records":[';
        if ( false === $writer( $prefix ) ) {
            $compressed ? gzclose( $handle ) : fclose( $handle );
            @unlink( $path );
            return new WP_Error( 'sc_rl_v703_snapshot_write', 'The canonical snapshot header could not be written.' );
        }
        $build_path = self::build_file_path( $state );
        if ( is_wp_error( $build_path ) ) {
            $compressed ? gzclose( $handle ) : fclose( $handle );
            @unlink( $path );
            return $build_path;
        }
        $source = @fopen( $build_path, 'rb' );
        if ( ! $source ) {
            $compressed ? gzclose( $handle ) : fclose( $handle );
            @unlink( $path );
            return new WP_Error( 'sc_rl_v703_snapshot_source', 'The asynchronous staging file could not be opened for snapshot creation.' );
        }
        $first = true;
        while ( false !== ( $line = fgets( $source ) ) ) {
            $line = trim( $line );
            if ( '' === $line ) {
                continue;
            }
            if ( ! is_array( json_decode( $line, true ) ) ) {
                fclose( $source );
                $compressed ? gzclose( $handle ) : fclose( $handle );
                @unlink( $path );
                return new WP_Error( 'sc_rl_v703_snapshot_record', 'An invalid staging record prevented canonical snapshot creation.' );
            }
            if ( false === $writer( ( $first ? '' : ',' ) . $line ) ) {
                fclose( $source );
                $compressed ? gzclose( $handle ) : fclose( $handle );
                @unlink( $path );
                return new WP_Error( 'sc_rl_v703_snapshot_write', 'A canonical snapshot record could not be written.' );
            }
            $first = false;
        }
        fclose( $source );
        $writer( ']}' );
        $compressed ? gzclose( $handle ) : fclose( $handle );
        $manifest = array(
            'snapshot_id' => $snapshot_id,
            'filename' => $filename,
            'created_utc' => $created,
            'reason' => sanitize_text_field( $reason ),
            'record_count' => absint( $scan['record_count'] ),
            'checksum' => sanitize_text_field( $scan['checksum'] ),
            'file_sha256' => hash_file( 'sha256', $path ),
            'size_bytes' => absint( filesize( $path ) ),
            'compressed' => $compressed,
            'schema' => 'sc-research-librarian-wordpress-snapshot/3.1',
        );
        $snapshots = self::wordpress_snapshots();
        array_unshift( $snapshots, $manifest );
        $limit = max( 1, min( 20, absint( self::options()['max_wordpress_snapshots'] ?? 5 ) ) );
        $removed = array_slice( $snapshots, $limit );
        update_option( self::SNAPSHOT_OPTION, array_slice( $snapshots, 0, $limit ), false );
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

    private static function process_build_verification_step( $state ) {
        if ( 'verifying-index' === $state['stage'] ) {
            $summary = self::request( '/v1/knowledge/summary', 'GET' );
            if ( is_wp_error( $summary ) || empty( $summary['total_records'] ) ) {
                $error = is_wp_error( $summary ) ? $summary : new WP_Error( 'sc_rl_v703_index_verification_failed', 'The backend committed the transaction but reports an empty knowledge index.' );
                return self::handle_build_error( $state, $error );
            }
            $state['indexed_records'] = absint( $summary['total_records'] ?? 0 );
            $state['indexed_chunks'] = absint( $summary['indexed_chunks'] ?? 0 );
            $state['stage'] = 'creating-snapshot';
            $state['progress'] = 92;
            $state['message'] = 'The durable index is verified. Creating a private canonical recovery snapshot without loading the full index into memory.';
            self::replace_build_state( $state );
            self::schedule_index_build( $state['job_id'], 2 );
            return $state;
        }
        if ( 'creating-snapshot' === $state['stage'] ) {
            $snapshot = self::create_wordpress_snapshot_from_build_file( $state, 'async-full-sync:' . sanitize_text_field( $state['job_id'] ) );
            if ( is_wp_error( $snapshot ) ) {
                $warnings = isset( $state['warnings'] ) && is_array( $state['warnings'] ) ? $state['warnings'] : array();
                $warnings[] = 'The index is live, but the canonical recovery snapshot could not be written: ' . $snapshot->get_error_message();
                $state['warnings'] = $warnings;
            } else {
                $state['wordpress_snapshot'] = self::snapshot_manifest_summary( $snapshot );
            }
            $state['stage'] = 'starting-embeddings';
            $state['progress'] = 96;
            $state['message'] = 'Knowledge records are ready. Testing and scheduling the resumable semantic-index queue.';
            self::replace_build_state( $state );
            self::schedule_index_build( $state['job_id'], 2 );
            return $state;
        }
        $embedding_test = self::test_backend_embeddings();
        $warnings = isset( $state['warnings'] ) && is_array( $state['warnings'] ) ? $state['warnings'] : array();
        if ( is_wp_error( $embedding_test ) ) {
            $warnings[] = 'Knowledge records are ready, but semantic embeddings need attention: ' . $embedding_test->get_error_message();
            $state['embedding_state'] = array( 'state' => 'configuration-error', 'last_error' => $embedding_test->get_error_message() );
        } else {
            $embedding_state = self::schedule_embedding_queue( 'v7.0.8-async-index-build', 10 );
            if ( is_wp_error( $embedding_state ) ) {
                $warnings[] = 'Knowledge records are ready, but the semantic queue could not be scheduled: ' . $embedding_state->get_error_message();
                $state['embedding_state'] = array( 'state' => 'manual-continuation-required', 'last_error' => $embedding_state->get_error_message() );
            } else {
                $state['embedding_state'] = $embedding_state;
            }
        }
        $state['warnings'] = $warnings;
        $state['state'] = $warnings ? 'ready-with-warnings' : 'ready';
        $state['stage'] = 'ready';
        $state['progress'] = 100;
        $state['message'] = $warnings ? 'Knowledge index ready; review the warning before semantic search reaches full coverage.' : 'Knowledge index ready. Semantic indexing will continue in resumable background batches.';
        $state['last_error'] = '';
        $state['completed_utc'] = gmdate( 'c' );
        unset( $state['deleted_ids'], $state['seen_url_hashes'], $state['finalization_hashes'], $state['finalization_posts'] );
        self::cleanup_build_files( $state );
        self::clear_index_build_schedule( $state['job_id'] );
        return self::replace_build_state( $state );
    }

    public static function run_index_build_job( $job_id = '' ) {
        $state = self::build_state();
        $job_id = sanitize_text_field( $job_id ?: ( $state['job_id'] ?? '' ) );
        if ( ! $job_id || sanitize_text_field( $state['job_id'] ?? '' ) !== $job_id ) {
            return false;
        }
        if ( 'paused' === sanitize_key( $state['state'] ?? '' ) || in_array( sanitize_key( $state['state'] ?? '' ), array( 'ready', 'ready-with-warnings', 'cancelled' ), true ) ) {
            return $state;
        }
        if ( ! self::acquire_build_lock( $job_id ) ) {
            self::schedule_index_build( $job_id, 30 );
            return $state;
        }
        try {
            $state['state'] = 'running';
            $state['next_run_utc'] = '';
            self::replace_build_state( $state );
            switch ( sanitize_key( $state['stage'] ?? 'testing-backend' ) ) {
                case 'testing-backend':
                    $test = self::test_backend();
                    if ( is_wp_error( $test ) ) {
                        return self::handle_build_error( $state, $test );
                    }
                    $state['stage'] = 'discovering-sources';
                    $state['progress'] = 5;
                    $state['message'] = 'Authenticated Python connection verified. Beginning bounded source discovery.';
                    $state['retry_count'] = 0;
                    self::replace_build_state( $state );
                    self::schedule_index_build( $job_id, 2 );
                    return $state;
                case 'discovering-sources':
                case 'discovering-legacy':
                    return self::process_build_discovery_step( $state );
                case 'finalizing-discovery':
                    return self::process_build_finalization_step( $state );
                case 'synchronizing-records':
                    return self::process_build_sync_step( $state );
                case 'reconciling-transaction':
                    return self::process_build_reconciliation_step( $state );
                case 'replaying-missing-batches':
                    return self::process_build_missing_batch_replay_step( $state );
                case 'queuing-backend-commit':
                case 'waiting-backend-commit':
                    return self::process_build_backend_commit_step( $state );
                case 'verifying-index':
                case 'creating-snapshot':
                case 'starting-embeddings':
                    return self::process_build_verification_step( $state );
                default:
                    return self::handle_build_error( $state, new WP_Error( 'sc_rl_v703_unknown_stage', 'The asynchronous rebuild reached an unknown workflow stage.' ) );
            }
        } catch ( Throwable $exception ) {
            return self::handle_build_error( $state, new WP_Error( 'sc_rl_v703_unhandled_exception', $exception->getMessage() ) );
        } finally {
            self::release_build_lock( $job_id );
        }
    }

    public static function run_next_index_build_step() {
        $state = self::build_state();
        if ( empty( $state['job_id'] ) ) {
            return new WP_Error( 'sc_rl_v703_build_not_found', 'No asynchronous knowledge-index build is available.' );
        }
        self::clear_index_build_schedule( $state['job_id'] );
        return self::run_index_build_job( $state['job_id'] );
    }

    public static function sync_and_complete_embeddings() {
        $sync = self::sync_all_records( 'manual-v7.0.8-repair' );
        if ( is_wp_error( $sync ) ) {
            return $sync;
        }
        $test = self::test_backend_embeddings();
        if ( is_wp_error( $test ) ) {
            update_option( self::EMBEDDING_STATE_OPTION, array(
                'state' => 'configuration-error',
                'last_error' => sanitize_text_field( $test->get_error_message() ),
                'credential_source' => 'SC_RL_GEMINI_API_KEY',
                'updated_utc' => gmdate( 'c' ),
            ), false );
            return $test;
        }
        $batch = self::process_embedding_batch( true );
        if ( is_wp_error( $batch ) ) {
            return $batch;
        }
        return array( 'sync' => $sync, 'embedding_test' => $test, 'embedding_batch' => $batch );
    }

    private static function save_sync_report( $report ) {
        update_option( self::SYNC_REPORT_OPTION, $report, false );
        if ( isset( $report['state'] ) && in_array( $report['state'], array( 'completed', 'completed-with-rejections', 'failed' ), true ) ) {
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


    private static function indexable_post_types( &$details = null ) {
        $objects = get_post_types( array(), 'objects' );
        $objects = is_array( $objects ) ? $objects : array();
        $excluded = array( 'attachment', 'revision', 'nav_menu_item', 'wp_block', 'wp_template', 'wp_template_part', 'wp_navigation', 'custom_css', 'customize_changeset', 'oembed_cache', 'user_request' );
        $types = array();
        $reasons = array();
        foreach ( $objects as $name => $object ) {
            $name = sanitize_key( $name );
            if ( ! $name || in_array( $name, $excluded, true ) || ! is_object( $object ) ) {
                continue;
            }
            $reason = '';
            if ( ! empty( $object->public ) ) {
                $reason = 'public';
            } elseif ( ! empty( $object->publicly_queryable ) ) {
                $reason = 'publicly-queryable';
            } elseif ( ! empty( $object->show_in_rest ) && false !== $object->rewrite ) {
                // Several Sustainable Catalyst document products intentionally use a
                // conservative CPT registration while still publishing public permalinks.
                $reason = 'rest-and-rewrite';
            }
            if ( ! $reason ) {
                continue;
            }
            $types[] = $name;
            $reasons[ $name ] = $reason;
        }
        $types = apply_filters( 'sc_rl_indexable_post_types', array_values( array_unique( $types ) ), $objects );
        $types = array_values( array_filter( array_unique( array_map( 'sanitize_key', (array) $types ) ), function( $type ) use ( $objects, $excluded ) {
            return isset( $objects[ $type ] ) && ! in_array( $type, $excluded, true );
        } ) );
        if ( is_array( $details ) ) {
            $details['eligibility_reasons'] = $reasons;
        } else {
            $details = array( 'eligibility_reasons' => $reasons );
        }
        return $types;
    }

    public static function source_discovery_summary() {
        $details = array();
        $types = self::indexable_post_types( $details );
        $counts = array();
        $total = 0;
        foreach ( $types as $post_type ) {
            $published = wp_count_posts( $post_type );
            $count = is_object( $published ) && isset( $published->publish ) ? absint( $published->publish ) : 0;
            $counts[ $post_type ] = $count;
            $total += $count;
        }
        arsort( $counts );
        return array(
            'post_types' => $types,
            'published_records' => $total,
            'records_by_post_type' => $counts,
            'eligibility_reasons' => $details['eligibility_reasons'] ?? array(),
            'generated_utc' => gmdate( 'c' ),
        );
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

        // v6.5.0 continues to index canonical published WordPress records first. The older
        // route/index registry is appended only when it contributes a unique URL.
        // This prevents a summary-only legacy entry from masking the full article.
        $type_details = array();
        $post_types = self::indexable_post_types( $type_details );
        $all_registered_post_types = get_post_types( array(), 'names' );
        $all_registered_post_types = is_array( $all_registered_post_types ) ? $all_registered_post_types : array();
        $report['eligible_post_types'] = $post_types;
        $report['post_type_eligibility_reasons'] = $type_details['eligibility_reasons'] ?? array();
        $report['unsupported_post_types'] = array_values( array_diff( $all_registered_post_types, $post_types ) );
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
        static $types = null;
        if ( null === $types ) {
            $details = array();
            $types = self::indexable_post_types( $details );
        }
        return in_array( sanitize_key( $post_type ), $types, true );
    }

    private static function extract_content_sections( $raw_content, $character_limit = 60000 ) {
        $sections = array();
        $remaining = max( 0, min( 60000, absint( $character_limit ) ) );
        if ( ! $remaining ) {
            return $sections;
        }
        $parts = preg_split( '/(<h[1-4][^>]*>.*?<\/h[1-4]>)/is', (string) $raw_content, -1, PREG_SPLIT_DELIM_CAPTURE | PREG_SPLIT_NO_EMPTY );
        $heading = 'Introduction';
        $buffer = '';
        $flush = static function () use ( &$sections, &$heading, &$buffer, &$remaining ) {
            if ( $remaining <= 0 ) {
                $buffer = '';
                return;
            }
            $text = trim( preg_replace( '/\s+/', ' ', wp_strip_all_tags( strip_shortcodes( $buffer ) ) ) );
            if ( $text ) {
                $section_limit = min( 12000, $remaining );
                $text = function_exists( 'mb_substr' ) ? mb_substr( $text, 0, $section_limit ) : substr( $text, 0, $section_limit );
                if ( $text ) {
                    $sections[] = array(
                        'heading' => sanitize_text_field( $heading ),
                        'text' => sanitize_textarea_field( $text ),
                    );
                    $length = function_exists( 'mb_strlen' ) ? mb_strlen( $text ) : strlen( $text );
                    $remaining = max( 0, $remaining - $length );
                }
            }
            $buffer = '';
        };
        foreach ( (array) $parts as $part ) {
            if ( preg_match( '/^<h[1-4][^>]*>(.*?)<\/h[1-4]>$/is', trim( $part ), $match ) ) {
                $flush();
                $heading = trim( wp_strip_all_tags( $match[1] ) );
                if ( ! $heading ) {
                    $heading = 'Document section';
                }
            } else {
                $buffer .= ' ' . $part;
            }
            if ( count( $sections ) >= 80 || $remaining <= 0 ) {
                break;
            }
        }
        $flush();
        return array_slice( $sections, 0, 80 );
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
                'sections' => '1' === (string) $options['include_content'] ? self::extract_content_sections( $raw_content, $limit ) : array(),
                'retrieval_schema' => 'section-aware/1.0',
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
            'schema' => 'sc-research-librarian-wordpress-snapshot/3.1',
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
            'schema' => 'sc-research-librarian-wordpress-snapshot/3.1',
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
        $expected_count = absint( $payload['manifest']['record_count'] ?? $manifest['record_count'] ?? 0 );
        if ( $expected_count && $expected_count !== count( $payload['records'] ) ) {
            return new WP_Error( 'sc_rl_v631_snapshot_record_count', 'The canonical WordPress snapshot failed its record-count validation.' );
        }
        $hashes = array();
        $seen = array();
        foreach ( $payload['records'] as $position => $record ) {
            if ( ! is_array( $record ) || empty( $record['id'] ) || empty( $record['title'] ) || empty( $record['url'] ) ) {
                return new WP_Error( 'sc_rl_v631_snapshot_record_invalid', 'The canonical WordPress snapshot contains an invalid record at position ' . absint( $position ) . '.' );
            }
            $record_id = sanitize_text_field( $record['id'] );
            if ( isset( $seen[ $record_id ] ) ) {
                return new WP_Error( 'sc_rl_v631_snapshot_duplicate_record', 'The canonical WordPress snapshot contains a duplicate record identifier: ' . $record_id . '.' );
            }
            $seen[ $record_id ] = true;
            $calculated_record_hash = self::record_content_hash( $record );
            if ( ! empty( $record['content_hash'] ) && ! hash_equals( (string) $record['content_hash'], $calculated_record_hash ) ) {
                return new WP_Error( 'sc_rl_v631_snapshot_record_hash', 'A canonical WordPress snapshot record failed its content-hash validation: ' . $record_id . '.' );
            }
            $hashes[ $record_id ] = $calculated_record_hash;
            $payload['records'][ $position ]['content_hash'] = $calculated_record_hash;
        }
        $calculated = self::ledger_checksum( $hashes );
        $expected = sanitize_text_field( $payload['manifest']['checksum'] ?? $manifest['checksum'] ?? '' );
        if ( $expected && ! hash_equals( $expected, $calculated ) ) {
            return new WP_Error( 'sc_rl_v630_snapshot_checksum', 'The canonical WordPress snapshot failed its record checksum validation.' );
        }
        $payload['integrity'] = array( 'ok' => true, 'record_count' => count( $payload['records'] ), 'checksum' => $calculated, 'validated_utc' => gmdate( 'c' ) );
        return $payload;
    }

    public static function validate_wordpress_snapshots() {
        $results = array();
        foreach ( self::wordpress_snapshots() as $manifest ) {
            $payload = self::read_wordpress_snapshot( $manifest );
            $results[] = array(
                'snapshot_id' => sanitize_text_field( $manifest['snapshot_id'] ?? '' ),
                'ok' => ! is_wp_error( $payload ),
                'record_count' => is_wp_error( $payload ) ? 0 : absint( $payload['integrity']['record_count'] ?? count( $payload['records'] ) ),
                'checksum' => is_wp_error( $payload ) ? '' : sanitize_text_field( $payload['integrity']['checksum'] ?? '' ),
                'error' => is_wp_error( $payload ) ? $payload->get_error_message() : '',
            );
        }
        $invalid = array_filter( $results, function( $row ) { return empty( $row['ok'] ); } );
        return array(
            'ok' => empty( $invalid ),
            'snapshot_count' => count( $results ),
            'invalid_count' => count( $invalid ),
            'snapshots' => $results,
            'validated_utc' => gmdate( 'c' ),
        );
    }

    private static function should_schedule_recovery( $status ) {
        $options = self::options();
        return '1' === (string) $options['auto_recover']
            && is_array( $status )
            && 0 === absint( $status['indexed_records'] ?? 0 )
            && ! empty( self::latest_wordpress_snapshot() );
    }

    private static function recovery_state() {
        $state = get_option( self::RECOVERY_STATE_OPTION, array() );
        return is_array( $state ) ? $state : array();
    }

    private static function update_recovery_state( $values ) {
        $state = array_merge( self::recovery_state(), is_array( $values ) ? $values : array() );
        $state['updated_utc'] = gmdate( 'c' );
        update_option( self::RECOVERY_STATE_OPTION, $state, false );
        return $state;
    }

    private static function clear_recovery_state() {
        wp_clear_scheduled_hook( self::RECOVERY_HOOK );
        delete_option( self::RECOVERY_STATE_OPTION );
    }

    private static function schedule_backend_recovery( $trigger = 'automatic-cold-start', $error = '' ) {
        $options = self::options();
        $state = self::recovery_state();
        $attempt = absint( $state['attempt'] ?? 0 ) + 1;
        $maximum = max( 1, min( 10, absint( $options['max_retry_attempts'] ) ) );
        if ( $attempt > $maximum ) {
            self::update_recovery_state( array(
                'state' => 'exhausted',
                'phase' => 'manual-review-required',
                'progress' => 0,
                'attempt' => $attempt - 1,
                'max_attempts' => $maximum,
                'trigger' => sanitize_key( $trigger ),
                'last_error' => sanitize_text_field( $error ),
            ) );
            self::append_recovery_log( 'recovery-exhausted', array( 'trigger' => $trigger, 'attempts' => $attempt - 1, 'error' => $error ) );
            return false;
        }
        if ( wp_next_scheduled( self::RECOVERY_HOOK ) ) {
            return true;
        }
        $delay = 1 === $attempt ? 10 : self::retry_delay( $attempt - 1 );
        wp_schedule_single_event( time() + $delay, self::RECOVERY_HOOK );
        self::update_recovery_state( array(
            'state' => 'scheduled',
            'phase' => 'waiting-for-backend',
            'progress' => 5,
            'attempt' => $attempt,
            'max_attempts' => $maximum,
            'delay_seconds' => $delay,
            'next_run_utc' => gmdate( 'c', time() + $delay ),
            'trigger' => sanitize_key( $trigger ),
            'last_error' => sanitize_text_field( $error ),
        ) );
        return true;
    }

    public static function run_backend_recovery() {
        if ( ! self::enabled() ) {
            return;
        }
        $state = self::recovery_state();
        $trigger = sanitize_key( $state['trigger'] ?? 'automatic-cold-start' );
        self::update_recovery_state( array( 'state' => 'running', 'phase' => 'verifying-snapshot', 'progress' => 10, 'started_utc' => gmdate( 'c' ) ) );
        $result = self::recover_backend_from_snapshot( $trigger );
        if ( ! is_wp_error( $result ) ) {
            self::clear_recovery_state();
        }
    }

    public static function recover_backend_from_snapshot( $trigger = 'manual' ) {
        if ( ! self::enabled() ) {
            return new WP_Error( 'sc_rl_v630_recovery_disabled', 'Enable and configure the Python backend before recovery.', array( 'status' => 400 ) );
        }
        self::update_recovery_state( array( 'state' => 'running', 'phase' => 'verifying-snapshot', 'progress' => 10, 'trigger' => sanitize_key( $trigger ) ) );
        $snapshot = self::read_wordpress_snapshot();
        if ( is_wp_error( $snapshot ) ) {
            self::append_recovery_log( 'recovery-failed', array( 'trigger' => $trigger, 'phase' => 'snapshot-validation', 'error' => $snapshot->get_error_message() ) );
            self::schedule_backend_recovery( $trigger, $snapshot->get_error_message() );
            return $snapshot;
        }
        $records = $snapshot['records'];
        $options = self::options();
        $chunks = array_chunk( $records, max( 25, min( 250, absint( $options['sync_batch_size'] ) ) ) );
        $job_id = 'recovery-' . gmdate( 'Ymd-His' ) . '-' . wp_generate_password( 8, false, false );
        $last = array();
        self::append_recovery_log( 'recovery-started', array( 'trigger' => $trigger, 'job_id' => $job_id, 'record_count' => count( $records ), 'batch_count' => count( $chunks ) ) );
        foreach ( $chunks as $index => $chunk ) {
            $progress = 20 + (int) floor( ( ( $index + 1 ) / max( 1, count( $chunks ) ) ) * 65 );
            self::update_recovery_state( array(
                'state' => 'running',
                'phase' => 'sending-snapshot-batches',
                'progress' => min( 85, $progress ),
                'job_id' => $job_id,
                'batch' => $index + 1,
                'batch_count' => count( $chunks ),
            ) );
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
                self::update_recovery_state( array( 'state' => 'failed', 'phase' => 'batch-failed', 'progress' => $progress, 'last_error' => $last->get_error_message() ) );
                self::schedule_backend_recovery( $trigger, $last->get_error_message() );
                return $last;
            }
        }
        self::update_recovery_state( array( 'state' => 'running', 'phase' => 'verifying-commit', 'progress' => 92 ) );
        if ( empty( $last['committed'] ) ) {
            $error = new WP_Error( 'sc_rl_v630_recovery_not_committed', 'The backend staged the recovery snapshot but did not commit it.', array( 'status' => 502 ) );
            self::append_recovery_log( 'recovery-failed', array( 'trigger' => $trigger, 'job_id' => $job_id, 'error' => $error->get_error_message() ) );
            self::schedule_backend_recovery( $trigger, $error->get_error_message() );
            return $error;
        }
        $rejected = isset( $last['rejected_records'] ) && is_array( $last['rejected_records'] ) ? $last['rejected_records'] : array();
        $rejected_ids = array();
        foreach ( $rejected as $row ) {
            if ( ! empty( $row['id'] ) ) {
                $rejected_ids[] = sanitize_text_field( $row['id'] );
            }
        }
        $ledger_records = array_values( array_filter( $records, function( $record ) use ( $rejected_ids ) {
            return empty( $record['id'] ) || ! in_array( $record['id'], $rejected_ids, true );
        } ) );
        self::save_ledger( $ledger_records, $last );
        $result = array(
            'ok' => true,
            'version' => self::VERSION,
            'state' => $rejected ? 'recovered-with-rejections' : 'recovered',
            'trigger' => sanitize_key( $trigger ),
            'job_id' => $job_id,
            'snapshot' => self::snapshot_manifest_summary( self::latest_wordpress_snapshot() ),
            'snapshot_integrity' => $snapshot['integrity'] ?? array(),
            'rejected_records' => $rejected,
            'backend_result' => $last,
            'recovered_utc' => gmdate( 'c' ),
        );
        self::update_recovery_state( array( 'state' => 'completed', 'phase' => 'complete', 'progress' => 100, 'completed_utc' => $result['recovered_utc'], 'last_error' => '' ) );
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
        update_option( self::RECOVERY_LOG_OPTION, array_slice( $rows, 0, 100 ), false );
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
        $sync_retry_next = wp_next_scheduled( self::SYNC_RETRY_HOOK );
        $report = self::latest_sync_report();
        $manifest = is_wp_error( $status ) ? $status : self::request( '/v1/knowledge/manifest', 'GET' );
        $backend_snapshot_validation = is_wp_error( $status ) ? $status : self::request( '/v1/knowledge/snapshots/validate', 'GET' );
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
                'max_retry_attempts' => absint( $options['max_retry_attempts'] ),
                'retry_base_seconds' => absint( $options['retry_base_seconds'] ),
                'retry_max_seconds' => absint( $options['retry_max_seconds'] ),
                'stalled_job_minutes' => absint( $options['stalled_job_minutes'] ),
                'alert_suppression_minutes' => absint( $options['alert_suppression_minutes'] ),
            ),
            'cron' => array(
                'scheduled' => (bool) $next,
                'next_run_utc' => $next ? gmdate( 'c', $next ) : '',
                'hook' => self::SYNC_HOOK,
                'recovery_scheduled' => (bool) $recovery_next,
                'recovery_next_run_utc' => $recovery_next ? gmdate( 'c', $recovery_next ) : '',
                'recovery_hook' => self::RECOVERY_HOOK,
                'sync_retry_scheduled' => (bool) $sync_retry_next,
                'sync_retry_next_run_utc' => $sync_retry_next ? gmdate( 'c', $sync_retry_next ) : '',
                'sync_retry_hook' => self::SYNC_RETRY_HOOK,
                'wp_cron_disabled' => defined( 'DISABLE_WP_CRON' ) && DISABLE_WP_CRON,
            ),
            'backend' => is_wp_error( $status ) ? self::public_error_snapshot( $status ) : $status,
            'backend_manifest' => is_wp_error( $manifest ) ? self::public_error_snapshot( $manifest ) : $manifest,
            'wordpress_snapshot' => self::snapshot_manifest_summary( $snapshot ),
            'wordpress_snapshot_count' => count( self::wordpress_snapshots() ),
            'wordpress_snapshot_validation' => self::validate_wordpress_snapshots(),
            'backend_snapshot_validation' => is_wp_error( $backend_snapshot_validation ) ? self::public_error_snapshot( $backend_snapshot_validation ) : $backend_snapshot_validation,
            'sync_retry_state' => get_option( self::SYNC_RETRY_OPTION, array() ),
            'recovery_state' => self::recovery_state(),
            'public_alert_state' => get_option( self::ALERT_STATE_OPTION, array() ),
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

    private static function parse_weight_map( $value ) {
        $output = array();
        foreach ( preg_split( '/[\r\n,]+/', (string) $value ) as $pair ) {
            $parts = array_map( 'trim', explode( ':', $pair, 2 ) );
            if ( 2 !== count( $parts ) || '' === $parts[0] ) {
                continue;
            }
            $key = sanitize_key( $parts[0] );
            if ( $key ) {
                $output[ $key ] = max( 0, min( 5, (float) $parts[1] ) );
            }
        }
        return $output;
    }

    private static function parse_list( $value ) {
        $output = array();
        foreach ( preg_split( '/[\r\n,]+/', (string) $value ) as $item ) {
            $item = trim( sanitize_text_field( $item ) );
            if ( '' !== $item ) {
                $output[] = $item;
            }
        }
        return array_values( array_unique( array_slice( $output, 0, 250 ) ) );
    }

    public static function retrieval_config_payload( $options = null ) {
        $options = is_array( $options ) ? $options : self::options();
        return array(
            'profile' => 'balanced-v6.5.0',
            'weights' => array(
                'structural' => (float) $options['retrieval_structural_weight'],
                'lexical' => (float) $options['retrieval_lexical_weight'],
                'semantic' => (float) $options['retrieval_semantic_weight'],
                'rrf' => (float) $options['retrieval_rrf_weight'],
            ),
            'rrf_k' => absint( $options['retrieval_rrf_k'] ),
            'thresholds' => array(
                'minimum_score' => (float) $options['retrieval_minimum_score'],
                'minimum_sources' => absint( $options['retrieval_minimum_sources'] ),
                'ambiguity_margin' => (float) $options['retrieval_ambiguity_margin'],
                'unsupported_overlap' => (float) $options['retrieval_unsupported_overlap'],
                'minimum_citation_coverage' => (float) $options['retrieval_minimum_citation_coverage'],
            ),
            'limits' => array(
                'max_sources' => absint( $options['retrieval_max_sources'] ),
                'max_context_characters' => absint( $options['retrieval_max_context_characters'] ),
                'max_passage_characters' => absint( $options['retrieval_max_passage_characters'] ),
                'benchmark_cases' => 25,
            ),
            'post_type_weights' => self::parse_weight_map( $options['retrieval_post_type_weights'] ),
            'source_weights' => self::parse_weight_map( $options['retrieval_source_weights'] ),
            'exclusions' => array(
                'record_ids' => array(),
                'post_types' => self::parse_list( $options['retrieval_excluded_post_types'] ),
                'sources' => self::parse_list( $options['retrieval_excluded_sources'] ),
                'url_prefixes' => self::parse_list( $options['retrieval_excluded_url_prefixes'] ),
            ),
        );
    }

    public static function apply_retrieval_config( $options = null ) {
        return self::request( '/v1/retrieval/config', 'POST', self::retrieval_config_payload( $options ) );
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
                $applied = self::enabled() ? self::apply_retrieval_config() : array();
                if ( is_wp_error( $applied ) ) {
                    $notice_type = 'error';
                    $notice = 'Settings were saved, but retrieval calibration could not be applied: ' . $applied->get_error_message();
                } else {
                    $notice = 'Python intelligence, durable-index, and retrieval-calibration settings saved.';
                }
            } elseif ( isset( $_POST['sc_rl_v620_test'] ) ) {
                self::save_options( $input );
                $test = self::test_backend();
                if ( is_wp_error( $test ) ) {
                    $notice_type = 'error';
                    $notice = $test->get_error_message();
                } else {
                    $notice = 'Python backend health check succeeded. Version ' . sanitize_text_field( isset( $test['version'] ) ? $test['version'] : self::VERSION ) . '.';
                    if ( self::should_schedule_recovery( $test ) ) {
                        self::schedule_backend_recovery( 'admin-health-check' );
                        $notice .= ' The runtime index is empty, so automatic snapshot recovery was scheduled.';
                    }
                }
            } elseif ( isset( $_POST['sc_rl_v702_build_index'] ) || isset( $_POST['sc_rl_v703_start_build'] ) ) {
                if ( $input ) {
                    self::save_options( $input );
                    self::sync_cron();
                }
                $build = self::start_index_build( 'manual-admin' );
                if ( is_wp_error( $build ) ) {
                    $notice_type = 'error';
                    $notice = 'Index rebuild could not start: ' . $build->get_error_message();
                } elseif ( ! empty( $build['already_running'] ) ) {
                    $notice_type = 'warning';
                    $notice = 'An asynchronous index rebuild is already active. Its next background batch has been scheduled.';
                } else {
                    $notice = 'Asynchronous index rebuild started. You may leave this page; the current durable index remains available until the replacement transaction is verified.';
                }
            } elseif ( isset( $_POST['sc_rl_v703_pause_build'] ) ) {
                $build = self::pause_index_build();
                if ( is_wp_error( $build ) ) {
                    $notice_type = 'error';
                    $notice = $build->get_error_message();
                } else {
                    $notice = 'Asynchronous index rebuild paused after its last completed batch.';
                }
            } elseif ( isset( $_POST['sc_rl_v703_resume_build'] ) ) {
                $build = self::resume_index_build();
                if ( is_wp_error( $build ) ) {
                    $notice_type = 'error';
                    $notice = $build->get_error_message();
                } else {
                    $notice = 'Asynchronous index rebuild resumed from its saved cursor.';
                }
            } elseif ( isset( $_POST['sc_rl_v703_cancel_build'] ) ) {
                $build = self::cancel_index_build();
                if ( is_wp_error( $build ) ) {
                    $notice_type = 'error';
                    $notice = $build->get_error_message();
                } else {
                    $notice = 'Asynchronous index rebuild cancelled. The previous committed index remains active.';
                }
            } elseif ( isset( $_POST['sc_rl_v703_run_next_batch'] ) ) {
                $build = self::run_next_index_build_step();
                if ( is_wp_error( $build ) ) {
                    $notice_type = 'error';
                    $notice = 'The bounded rebuild step stopped: ' . $build->get_error_message();
                } else {
                    $notice = 'One bounded rebuild step completed. Remaining work is still queued in the background.';
                }
            } elseif ( isset( $_POST['sc_rl_v701_sync_embed'] ) || isset( $_POST['sc_rl_v620_sync'] ) ) {
                self::save_options( $input );
                $build = self::start_index_build( 'advanced-admin-sync' );
                if ( is_wp_error( $build ) ) {
                    $notice_type = 'error';
                    $notice = 'Asynchronous synchronization could not start: ' . $build->get_error_message();
                } else {
                    $notice = 'Asynchronous transactional synchronization queued. Semantic indexing will start only after the new durable index is verified.';
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
                    self::clear_recovery_state();
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
            } elseif ( isset( $_POST['sc_rl_v631_repair_stalled'] ) ) {
                $maintenance = self::request( '/v1/knowledge/maintenance', 'POST', array(
                    'max_age_seconds' => max( 300, absint( self::options()['stalled_job_minutes'] ) * MINUTE_IN_SECONDS ),
                    'purge_staging' => true,
                ) );
                if ( is_wp_error( $maintenance ) ) {
                    $notice_type = 'error';
                    $notice = $maintenance->get_error_message();
                } else {
                    self::append_recovery_log( 'stalled-jobs-repaired', $maintenance );
                    $notice = 'Stalled transaction repair completed: ' . absint( $maintenance['count'] ?? 0 ) . ' job(s) repaired.';
                }
            } elseif ( isset( $_POST['sc_rl_v631_validate_snapshots'] ) ) {
                $wordpress_validation = self::validate_wordpress_snapshots();
                $backend_validation = self::request( '/v1/knowledge/snapshots/validate', 'GET' );
                if ( ! empty( $wordpress_validation['invalid_count'] ) || is_wp_error( $backend_validation ) || ! empty( $backend_validation['invalid_count'] ) ) {
                    $notice_type = 'error';
                    $notice = 'Snapshot validation found an integrity problem. Review the diagnostics below before recovery or rollback.';
                } else {
                    $notice = 'All available WordPress and backend runtime snapshots passed integrity validation.';
                }
            } elseif ( isset( $_POST['sc_rl_v631_clear_retries'] ) ) {
                self::clear_sync_retry();
                self::clear_recovery_state();
                $notice = 'Pending synchronization and recovery retries were cleared.';
            } elseif ( isset( $_POST['sc_rl_v640_process_embeddings'] ) ) {
                $embedding_result = self::process_embedding_batch( true );
                if ( is_wp_error( $embedding_result ) ) {
                    $notice_type = 'error';
                    $notice = $embedding_result->get_error_message();
                } else {
                    $notice = 'Embedding batch processed: ' . absint( $embedding_result['processed'] ?? 0 ) . ' completed, ' . absint( $embedding_result['pending_chunks'] ?? 0 ) . ' remaining.';
                }
            } elseif ( isset( $_POST['sc_rl_v650_run_benchmark'] ) ) {
                self::save_options( $input );
                $applied = self::apply_retrieval_config();
                $benchmark = is_wp_error( $applied ) ? $applied : self::request( '/v1/retrieval/benchmark', 'POST', array( 'cases' => array(), 'include_semantic' => true, 'limit' => 5, 'persist' => true ) );
                if ( is_wp_error( $benchmark ) ) {
                    $notice_type = 'error';
                    $notice = $benchmark->get_error_message();
                } else {
                    $lexical = $benchmark['metrics']['lexical'] ?? array();
                    $hybrid = $benchmark['metrics']['hybrid'] ?? array();
                    $notice = 'Retrieval benchmark completed: lexical MRR ' . round( (float) ( $lexical['mrr'] ?? 0 ), 3 ) . ', hybrid MRR ' . round( (float) ( $hybrid['mrr'] ?? 0 ), 3 ) . ' across ' . absint( $benchmark['case_count'] ?? 0 ) . ' case(s).';
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
        $sync_retry_state = get_option( self::SYNC_RETRY_OPTION, array() );
        $sync_retry_state = is_array( $sync_retry_state ) ? $sync_retry_state : array();
        $recovery_state = self::recovery_state();
        $wordpress_snapshot_validation = self::validate_wordpress_snapshots();
        $backend_snapshot_validation = self::request( '/v1/knowledge/snapshots/validate', 'GET' );
        $embedding_status = self::request( '/v1/knowledge/embeddings/status', 'GET' );
        $provider_diagnostics = self::provider_diagnostics();
        $embedding_queue_state = self::embedding_queue_state();
        $build_state = self::build_state();
        $source_discovery = self::source_discovery_summary();
        $retrieval_config_response = self::request( '/v1/retrieval/config', 'GET' );
        $benchmark_history_response = self::request( '/v1/retrieval/benchmark/history', 'GET' );
        $retrieval_config = ! is_wp_error( $retrieval_config_response ) && isset( $retrieval_config_response['config'] ) ? $retrieval_config_response['config'] : array();
        $benchmark_runs = ! is_wp_error( $benchmark_history_response ) && isset( $benchmark_history_response['runs'] ) && is_array( $benchmark_history_response['runs'] ) ? $benchmark_history_response['runs'] : array();
        $export_url = wp_nonce_url( admin_url( 'admin-post.php?action=sc_rl_v631_export_sync_log' ), 'sc_rl_v631_export_sync_log' );
        $backend_connected = ! is_wp_error( $status );
        $provider_connected = $backend_connected && in_array( sanitize_key( $status['generation_state'] ?? '' ), array( 'online', 'configured' ), true );
        $indexed_records = $backend_connected ? absint( $status['indexed_records'] ?? 0 ) : 0;
        $indexed_chunks = $backend_connected ? absint( $status['indexed_chunks'] ?? 0 ) : 0;
        $embedded_chunks = $backend_connected ? absint( $status['embedded_chunks'] ?? 0 ) : 0;
        $pending_chunks = $backend_connected ? absint( $status['pending_chunks'] ?? max( 0, $indexed_chunks - $embedded_chunks ) ) : 0;
        $source_count = absint( $source_discovery['published_records'] ?? 0 );
        $build_status_key = sanitize_key( $build_state['state'] ?? '' );
        $build_stage = sanitize_key( $build_state['stage'] ?? '' );
        $build_active = self::build_is_active( $build_state );
        $build_progress = max( 0, min( 100, absint( $build_state['progress'] ?? 0 ) ) );
        $readiness = $build_active ? $build_progress : ( $backend_connected ? max( 0, min( 100, absint( $status['readiness_percent'] ?? ( $indexed_records ? 75 : 50 ) ) ) ) : 10 );
        $build_message = sanitize_text_field( $build_state['message'] ?? '' );
        $primary_state = $build_active ? 'indexing' : ( $indexed_records ? ( $pending_chunks ? 'indexing' : 'ready' ) : ( $backend_connected ? 'action-required' : 'offline' ) );
        $build_badge = $build_active ? 'Background rebuild · ' . str_replace( '-', ' ', $build_stage ?: 'queued' ) : ( 'failed' === $build_status_key ? 'Rebuild paused by an error · previous index retained' : ( $indexed_records ? ( $pending_chunks ? 'Index ready · semantic indexing in progress' : 'Research service ready' ) : ( $backend_connected ? 'Connection ready · index build required' : 'Python connection needs attention' ) ) );
        $last_error_text = strtolower( (string) ( $build_state['last_error'] ?? '' ) );
        $transaction_recovery_ready = in_array( $build_stage, array( 'reconciling-transaction', 'replaying-missing-batches' ), true ) || false !== strpos( $last_error_text, 'did not commit the replacement transaction' ) || false !== strpos( $last_error_text, 'could not be reconciled' );
        $backend_commit_active = in_array( $build_stage, array( 'queuing-backend-commit', 'waiting-backend-commit' ), true );
        $resume_label = $transaction_recovery_ready ? 'Repair and Resume Commit' : ( $backend_commit_active ? 'Resume Activation Check' : 'Resume Rebuild' );
        $validated_display = absint( $build_state['finalization_records'] ?? 0 );
        if ( ! $validated_display && in_array( $build_stage, array( 'synchronizing-records', 'reconciling-transaction', 'replaying-missing-batches', 'queuing-backend-commit', 'waiting-backend-commit', 'verifying-index', 'creating-snapshot', 'starting-embeddings', 'ready' ), true ) ) {
            $validated_display = absint( $build_state['records_discovered'] ?? 0 );
        }
        $finalization_bytes = absint( $build_state['finalization_bytes'] ?? 0 );
        if ( ! $finalization_bytes && ! empty( $build_state['build_filename'] ) ) {
            $build_path_for_size = self::build_file_path( $build_state );
            if ( ! is_wp_error( $build_path_for_size ) && is_file( $build_path_for_size ) ) {
                $finalization_bytes = absint( filesize( $build_path_for_size ) );
            }
        }
        $backend_received = isset( $build_state['backend_received_batches'] ) && is_array( $build_state['backend_received_batches'] ) ? array_values( array_filter( array_map( 'absint', $build_state['backend_received_batches'] ) ) ) : array();
        $backend_missing = isset( $build_state['backend_missing_batches'] ) && is_array( $build_state['backend_missing_batches'] ) ? array_values( array_filter( array_map( 'absint', $build_state['backend_missing_batches'] ) ) ) : array();
        $backend_batch_count = absint( $build_state['backend_transaction_status']['batch_count'] ?? $build_state['sync_batch_count'] ?? 0 );
        $backend_commit_phase = sanitize_key( $build_state['backend_commit_phase'] ?? $build_state['backend_transaction_status']['commit_phase'] ?? '' );
        $backend_commit_progress = absint( $build_state['backend_commit_progress'] ?? $build_state['backend_transaction_status']['commit_progress'] ?? 0 );
        $backend_activation_records = absint( $build_state['backend_activation_records'] ?? $build_state['backend_transaction_status']['activation_records'] ?? 0 );
        $backend_activation_total = absint( $build_state['backend_activation_total'] ?? $build_state['backend_transaction_status']['activation_total'] ?? 0 );
        $backend_indexed_chunks = absint( $build_state['backend_indexed_chunks'] ?? $build_state['backend_transaction_status']['indexed_chunks'] ?? 0 );
        $backend_chunk_records_processed = absint( $build_state['backend_chunk_records_processed'] ?? $build_state['backend_transaction_status']['chunk_records_processed'] ?? 0 );
        $backend_checksum_records = absint( $build_state['backend_checksum_records'] ?? $build_state['backend_transaction_status']['checksum_records'] ?? 0 );
        $backend_activation_steps = absint( $build_state['backend_activation_steps'] ?? $build_state['backend_transaction_status']['activation_step_count'] ?? 0 );
        $backend_storage_persistent = ! empty( $build_state['backend_storage_persistent'] ?? $build_state['backend_transaction_status']['storage_persistent'] ?? false );
        $backend_transaction_state = sanitize_key( $build_state['backend_transaction_state'] ?? $build_state['backend_transaction_status']['transaction_state'] ?? $build_state['backend_transaction_status']['state'] ?? '' );
        $backend_reconciliation_action = sanitize_key( $build_state['backend_reconciliation_action'] ?? $build_state['backend_transaction_status']['reconciliation_action'] ?? '' );
        $backend_job_id = sanitize_text_field( $build_state['backend_job_id'] ?? '' );
        $recovery_generation = absint( $build_state['recovery_generation'] ?? 0 );
        ?>
        <div class="wrap sc-rl-v702-admin">
            <style>
                .sc-rl-v702-admin{max-width:1320px}.sc-rl-v702-hero{background:#111;color:#fff;border-radius:18px;padding:28px 30px;margin:18px 0;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:24px;align-items:center}.sc-rl-v702-hero h1{color:#fff;font-size:30px;line-height:1.15;margin:4px 0 10px}.sc-rl-v702-hero p{color:#d7d7d7;max-width:760px;font-size:15px}.sc-rl-v702-eyebrow{font-size:12px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#ff6b6b}.sc-rl-v702-badge{display:inline-flex;align-items:center;gap:8px;border:1px solid rgba(255,255,255,.25);border-radius:999px;padding:8px 12px;font-weight:700}.sc-rl-v702-badge:before{content:"";width:9px;height:9px;border-radius:50%;background:#d63638}.sc-rl-v702-hero[data-state="ready"] .sc-rl-v702-badge:before{background:#00a32a}.sc-rl-v702-hero[data-state="indexing"] .sc-rl-v702-badge:before,.sc-rl-v702-hero[data-state="action-required"] .sc-rl-v702-badge:before{background:#dba617}.sc-rl-v702-progress{height:8px;background:rgba(255,255,255,.16);border-radius:999px;overflow:hidden;margin-top:18px}.sc-rl-v702-progress span{display:block;height:100%;background:#fff;border-radius:999px}.sc-rl-v702-primary{min-width:260px;text-align:right}.sc-rl-v702-primary .button{min-height:46px;padding:8px 18px;font-size:15px;font-weight:800}.sc-rl-v702-primary small{display:block;color:#bdbdbd;margin-top:10px;max-width:280px}.sc-rl-v702-stages{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:18px 0}.sc-rl-v702-stage{background:#fff;border:1px solid #dcdcde;border-radius:14px;padding:18px;box-shadow:0 1px 2px rgba(0,0,0,.03)}.sc-rl-v702-stage span{display:block;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:#646970}.sc-rl-v702-stage strong{display:block;font-size:25px;line-height:1.15;margin:8px 0}.sc-rl-v702-stage p{margin:0;color:#50575e}.sc-rl-v702-stage[data-state="ready"]{border-top:4px solid #00a32a}.sc-rl-v702-stage[data-state="attention"],.sc-rl-v702-stage[data-state="running"]{border-top:4px solid #dba617}.sc-rl-v702-stage[data-state="offline"]{border-top:4px solid #d63638}.sc-rl-v702-source-panel{background:#fff;border:1px solid #dcdcde;border-radius:14px;padding:18px 20px;margin:18px 0}.sc-rl-v702-source-panel h2{margin:0 0 4px}.sc-rl-v702-source-grid{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.sc-rl-v702-source-grid span{background:#f0f0f1;border-radius:999px;padding:7px 10px;font-weight:700}.sc-rl-v702-settings,.sc-rl-v702-diagnostics{background:#fff;border:1px solid #dcdcde;border-radius:14px;padding:0 20px;margin:18px 0}.sc-rl-v702-settings>summary,.sc-rl-v702-diagnostics>summary{cursor:pointer;font-size:16px;font-weight:800;padding:18px 0}.sc-rl-v702-actions{display:flex;flex-wrap:wrap;gap:8px;padding:16px 0 20px;border-top:1px solid #eee}.sc-rl-v702-callout{border-left:4px solid #b00000;background:#fff;padding:14px 16px;margin:16px 0}.sc-rl-v702-build-message{margin-top:10px;color:#d7d7d7}.sc-rl-v702-admin .form-table th{width:250px}.sc-rl-v702-admin code{word-break:break-all}.sc-rl-v703-job{background:#fff;border:1px solid #dcdcde;border-radius:14px;padding:18px 20px;margin:18px 0}.sc-rl-v703-job__head{display:flex;justify-content:space-between;gap:18px;align-items:flex-start}.sc-rl-v703-job__head h2{margin:0 0 4px}.sc-rl-v703-job__grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:16px}.sc-rl-v703-job__metric{background:#f6f7f7;border-radius:10px;padding:12px}.sc-rl-v703-job__metric span{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#646970;font-weight:800}.sc-rl-v703-job__metric strong{display:block;font-size:20px;margin-top:5px}.sc-rl-v703-controls{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}.sc-rl-v703-error{border-left:4px solid #d63638;background:#fcf0f1;padding:12px 14px;margin-top:14px}.sc-rl-v703-cron{border-left:4px solid #dba617;background:#fff8e5;padding:12px 14px;margin-top:14px}@media(max-width:900px){.sc-rl-v702-hero{grid-template-columns:1fr}.sc-rl-v702-primary{text-align:left}.sc-rl-v702-stages{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:760px){.sc-rl-v703-job__grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:560px){.sc-rl-v702-stages,.sc-rl-v703-job__grid{grid-template-columns:1fr}.sc-rl-v702-hero{padding:22px}}
            </style>
            <?php if ( $notice ) : ?><div class="notice notice-<?php echo esc_attr( $notice_type ); ?> is-dismissible"><p><?php echo esc_html( $notice ); ?></p></div><?php endif; ?>

            <section class="sc-rl-v702-hero" data-state="<?php echo esc_attr( $primary_state ); ?>">
                <div>
                    <div class="sc-rl-v702-eyebrow">Research Librarian v7.0.8</div>
                    <h1>Knowledge Index and AI Readiness</h1>
                    <p>One operational view for the Python connection, WordPress source discovery, durable knowledge synchronization, and Gemini semantic indexing.</p>
                    <div class="sc-rl-v702-badge"><?php echo esc_html( $build_badge ); ?></div>
                    <div class="sc-rl-v702-progress" aria-label="Research Librarian readiness" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="<?php echo esc_attr( $readiness ); ?>"><span style="width:<?php echo esc_attr( $readiness ); ?>%"></span></div>
                    <?php if ( $build_message ) : ?><div class="sc-rl-v702-build-message"><?php echo esc_html( $build_message ); ?></div><?php endif; ?>
                </div>
                <div class="sc-rl-v702-primary">
                    <form method="post">
                        <?php wp_nonce_field( 'sc_rl_v620_admin_action' ); ?>
                        <?php if ( $build_active && 'paused' !== $build_status_key ) : ?>
                            <button class="button" type="submit" name="sc_rl_v703_pause_build" value="1">Pause Rebuild</button>
                            <button class="button button-primary" type="submit" name="sc_rl_v703_run_next_batch" value="1">Run Next Batch Now</button>
                        <?php elseif ( in_array( $build_status_key, array( 'paused', 'failed', 'retry-scheduled' ), true ) ) : ?>
                            <button class="button button-primary" type="submit" name="sc_rl_v703_resume_build" value="1"><?php echo esc_html( $resume_label ); ?></button>
                        <?php else : ?>
                            <button class="button button-primary" type="submit" name="sc_rl_v703_start_build" value="1"><?php echo esc_html( $indexed_records ? 'Rebuild Index in Background' : 'Build Knowledge Index' ); ?></button>
                        <?php endif; ?>
                    </form>
                    <small>Every request is bounded. WordPress and Python persist a cursor after each discovery, synchronization, activation, verification, snapshot, and embedding step.</small>
                </div>
            </section>

            <?php if ( $build_state ) : ?>
                <section class="sc-rl-v703-job" aria-live="polite">
                    <div class="sc-rl-v703-job__head">
                        <div>
                            <h2>Asynchronous rebuild job</h2>
                            <p><?php echo esc_html( $build_message ?: 'No background index rebuild is active.' ); ?></p>
                        </div>
                        <strong><?php echo esc_html( $build_progress . '%' ); ?></strong>
                    </div>
                    <div class="sc-rl-v702-progress" role="progressbar" aria-label="Asynchronous index rebuild progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="<?php echo esc_attr( $build_progress ); ?>"><span style="width:<?php echo esc_attr( $build_progress ); ?>%"></span></div>
                    <div class="sc-rl-v703-job__grid">
                        <div class="sc-rl-v703-job__metric"><span>Stage</span><strong><?php echo esc_html( ucwords( str_replace( '-', ' ', $build_stage ?: 'idle' ) ) ); ?></strong></div>
                        <div class="sc-rl-v703-job__metric"><span>Discovered</span><strong><?php echo esc_html( number_format_i18n( absint( $build_state['records_discovered'] ?? 0 ) ) ); ?></strong></div>
                        <div class="sc-rl-v703-job__metric"><span>Synchronized</span><strong><?php echo esc_html( number_format_i18n( absint( $build_state['records_synced'] ?? 0 ) ) ); ?></strong></div>
                        <div class="sc-rl-v703-job__metric"><span>Batch</span><strong><?php echo esc_html( absint( $build_state['sync_batch_index'] ?? 0 ) . '/' . absint( $build_state['sync_batch_count'] ?? 0 ) ); ?></strong></div>
                        <div class="sc-rl-v703-job__metric"><span>Validated</span><strong><?php echo esc_html( number_format_i18n( $validated_display ) ); ?></strong></div>
                        <div class="sc-rl-v703-job__metric"><span>Staging file</span><strong><?php echo esc_html( $finalization_bytes ? size_format( $finalization_bytes ) : 'Available' ); ?></strong></div>
                        <?php if ( $backend_commit_active || $backend_commit_phase ) : ?>
                            <div class="sc-rl-v703-job__metric"><span>Backend activation</span><strong><?php echo esc_html( $backend_commit_phase ? ucwords( str_replace( '-', ' ', $backend_commit_phase ) ) : 'Queued' ); ?></strong></div>
                            <div class="sc-rl-v703-job__metric"><span>Activation progress</span><strong><?php echo esc_html( $backend_commit_progress . '%' ); ?></strong></div>
                            <div class="sc-rl-v703-job__metric"><span>Shadow records</span><strong><?php echo esc_html( number_format_i18n( $backend_activation_records ) . ( $backend_activation_total ? '/' . number_format_i18n( $backend_activation_total ) : '' ) ); ?></strong></div>
                            <div class="sc-rl-v703-job__metric"><span>Chunked records</span><strong><?php echo esc_html( number_format_i18n( $backend_chunk_records_processed ) . ( $backend_activation_total ? '/' . number_format_i18n( $backend_activation_total ) : '' ) ); ?></strong></div>
                            <div class="sc-rl-v703-job__metric"><span>Verified records</span><strong><?php echo esc_html( number_format_i18n( $backend_checksum_records ) . ( $backend_activation_total ? '/' . number_format_i18n( $backend_activation_total ) : '' ) ); ?></strong></div>
                            <div class="sc-rl-v703-job__metric"><span>Retrieval chunks</span><strong><?php echo esc_html( number_format_i18n( $backend_indexed_chunks ) ); ?></strong></div>
                            <div class="sc-rl-v703-job__metric"><span>Durable steps</span><strong><?php echo esc_html( number_format_i18n( $backend_activation_steps ) ); ?></strong></div>
                        <?php endif; ?>
                        <?php if ( $transaction_recovery_ready || $backend_received || $backend_missing ) : ?>
                            <div class="sc-rl-v703-job__metric"><span>Backend retained</span><strong><?php echo esc_html( count( $backend_received ) . '/' . $backend_batch_count ); ?></strong></div>
                            <div class="sc-rl-v703-job__metric"><span>Missing batches</span><strong><?php echo esc_html( $backend_missing ? implode( ', ', array_slice( $backend_missing, 0, 8 ) ) : 'Checking' ); ?></strong></div>
                            <div class="sc-rl-v703-job__metric"><span>Transaction state</span><strong><?php echo esc_html( $backend_transaction_state ? ucwords( str_replace( '-', ' ', $backend_transaction_state ) ) : 'Checking' ); ?></strong></div>
                            <div class="sc-rl-v703-job__metric"><span>Recovery action</span><strong><?php echo esc_html( $backend_reconciliation_action ? ucwords( str_replace( '-', ' ', $backend_reconciliation_action ) ) : 'Checking' ); ?></strong></div>
                            <div class="sc-rl-v703-job__metric"><span>Transaction ID</span><strong title="<?php echo esc_attr( $backend_job_id ); ?>"><?php echo esc_html( $backend_job_id ? substr( $backend_job_id, 0, 28 ) . ( strlen( $backend_job_id ) > 28 ? '…' : '' ) : 'Unavailable' ); ?></strong></div>
                            <div class="sc-rl-v703-job__metric"><span>Recovery generation</span><strong><?php echo esc_html( number_format_i18n( $recovery_generation ) ); ?></strong></div>
                            <div class="sc-rl-v703-job__metric"><span>Replay attempt</span><strong><?php echo esc_html( absint( $build_state['transaction_replay_count'] ?? 0 ) . '/' . max( 1, absint( $build_state['transaction_replay_limit'] ?? 3 ) ) ); ?></strong></div>
                        <?php endif; ?>
                    </div>
                    <?php if ( $backend_commit_active ) : ?><div class="sc-rl-v703-cron"><strong>All source batches are staged.</strong> WordPress is advancing one bounded Python activation step at a time. Every record, chunk, and verification cursor is saved before the next request.</div><?php endif; ?>
                    <?php if ( $transaction_recovery_ready ) : ?><div class="sc-rl-v703-cron"><strong>Commit recovery is ready.</strong> The complete WordPress staging file is still available. Choose “Repair and Resume Commit” to replay the transaction without rediscovering the 2,000-plus source records.</div><?php endif; ?>
                    <?php if ( $backend_commit_active && ! $backend_storage_persistent ) : ?><div class="sc-rl-v703-cron"><strong>Persistent Render storage is recommended.</strong> Set <code>SC_RL_DATA_DIR=/var/data/sc-research-librarian</code> and attach a Render persistent disk. The WordPress staging file can still replay the transaction after an ephemeral restart.</div><?php endif; ?>
                    <?php if ( ! empty( $build_state['last_error'] ) ) : ?><div class="sc-rl-v703-error"><strong>Last error:</strong> <?php echo esc_html( $build_state['last_error'] ); ?></div><?php endif; ?>
                    <?php if ( defined( 'DISABLE_WP_CRON' ) && DISABLE_WP_CRON ) : ?><div class="sc-rl-v703-cron"><strong>WP-Cron is disabled.</strong> Use “Run Next Batch Now,” or configure a real server cron request to <code>wp-cron.php</code>.</div><?php endif; ?>
                    <form method="post" class="sc-rl-v703-controls">
                        <?php wp_nonce_field( 'sc_rl_v620_admin_action' ); ?>
                        <?php if ( $build_active && 'paused' !== $build_status_key ) : ?><button class="button" type="submit" name="sc_rl_v703_pause_build" value="1">Pause</button><?php endif; ?>
                        <?php if ( in_array( $build_status_key, array( 'paused', 'failed', 'retry-scheduled' ), true ) ) : ?><button class="button button-primary" type="submit" name="sc_rl_v703_resume_build" value="1"><?php echo esc_html( $transaction_recovery_ready ? 'Repair and Resume Commit' : 'Resume' ); ?></button><?php endif; ?>
                        <?php if ( $build_active || in_array( $build_status_key, array( 'paused', 'failed' ), true ) ) : ?><button class="button" type="submit" name="sc_rl_v703_run_next_batch" value="1">Run Next Batch Now</button><button class="button button-link-delete" type="submit" name="sc_rl_v703_cancel_build" value="1" onclick="return confirm('Cancel this rebuild? The previously committed index will remain active.');">Cancel</button><?php endif; ?>
                    </form>
                    <?php if ( $build_active && 'paused' !== $build_status_key ) : ?><script>window.setTimeout(function(){window.location.reload();},12000);</script><?php endif; ?>
                </section>
            <?php endif; ?>

            <div class="sc-rl-v702-stages">
                <article class="sc-rl-v702-stage" data-state="<?php echo esc_attr( $backend_connected ? 'ready' : 'offline' ); ?>"><span>1 · Python connection</span><strong><?php echo esc_html( $backend_connected ? 'Connected' : 'Offline' ); ?></strong><p><?php echo esc_html( $backend_connected ? ( 'Backend v' . sanitize_text_field( $status['version'] ?? self::VERSION ) ) : $status->get_error_message() ); ?></p></article>
                <article class="sc-rl-v702-stage" data-state="<?php echo esc_attr( $source_count ? 'ready' : 'attention' ); ?>"><span>2 · WordPress sources</span><strong><?php echo esc_html( number_format_i18n( $source_count ) ); ?></strong><p><?php echo esc_html( count( $source_discovery['post_types'] ?? array() ) . ' indexable content type(s) discovered' ); ?></p></article>
                <article class="sc-rl-v702-stage" data-state="<?php echo esc_attr( $indexed_records ? 'ready' : 'attention' ); ?>"><span>3 · Knowledge index</span><strong><?php echo esc_html( number_format_i18n( $indexed_records ) ); ?></strong><p><?php echo esc_html( $indexed_records ? absint( $status['indexed_titles'] ?? 0 ) . ' distinct titles in Python' : 'Build the index to activate retrieval' ); ?></p></article>
                <article class="sc-rl-v702-stage" data-state="<?php echo esc_attr( $pending_chunks ? 'running' : ( $indexed_records ? 'ready' : 'attention' ) ); ?>"><span>4 · Semantic search</span><strong><?php echo esc_html( $indexed_chunks ? number_format_i18n( $embedded_chunks ) . '/' . number_format_i18n( $indexed_chunks ) : 'Waiting' ); ?></strong><p><?php echo esc_html( $pending_chunks ? number_format_i18n( $pending_chunks ) . ' chunk(s) remaining' : ( $indexed_records ? 'Embedding queue complete or not required' : 'Starts after the knowledge sync' ) ); ?></p></article>
            </div>

            <section class="sc-rl-v702-source-panel">
                <h2>Source coverage</h2>
                <p>The index now includes public, publicly queryable, and published REST/rewrite document types instead of only standard posts and pages.</p>
                <div class="sc-rl-v702-source-grid">
                    <?php foreach ( array_slice( $source_discovery['records_by_post_type'] ?? array(), 0, 16, true ) as $post_type => $count ) : ?><span><?php echo esc_html( $post_type . ' · ' . number_format_i18n( $count ) ); ?></span><?php endforeach; ?>
                    <?php if ( empty( $source_discovery['records_by_post_type'] ) ) : ?><span>No published sources discovered</span><?php endif; ?>
                </div>
            </section>

            <form method="post">
                <?php wp_nonce_field( 'sc_rl_v620_admin_action' ); ?>
                <details class="sc-rl-v702-settings">
                    <summary>Connection and advanced settings</summary>
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
                    <tr><th>Automatic semantic indexing</th><td><input type="hidden" name="sc_rl_v620[auto_embed_after_sync]" value="0"><label><input type="checkbox" name="sc_rl_v620[auto_embed_after_sync]" value="1" <?php checked( $options['auto_embed_after_sync'], '1' ); ?>> Continue resumable Python embedding batches automatically after every successful sync</label></td></tr>
                    <tr><th><label for="sc-rl-v701-embedding-batch">Embedding batch size</label></th><td><input id="sc-rl-v701-embedding-batch" type="number" min="1" max="250" name="sc_rl_v620[embedding_batch_size]" value="<?php echo esc_attr( $options['embedding_batch_size'] ); ?>"><p class="description">Each cron pass persists completed vectors, then schedules the next pass until pending chunks reach zero.</p></td></tr>
                    <tr><th><label for="sc-rl-v703-source-batch">Source discovery batch size</label></th><td><input id="sc-rl-v703-source-batch" type="number" min="5" max="100" name="sc_rl_v620[source_batch_size]" value="<?php echo esc_attr( $options['source_batch_size'] ); ?>"><p class="description">Published records processed per asynchronous discovery pass. Smaller batches reduce PHP memory and execution-time risk.</p></td></tr>
                    <tr><th><label for="sc-rl-v703-build-stale">Rebuild stale threshold</label></th><td><input id="sc-rl-v703-build-stale" type="number" min="5" max="120" name="sc_rl_v620[build_stale_minutes]" value="<?php echo esc_attr( $options['build_stale_minutes'] ); ?>"> minutes<p class="description">A build with no saved progress beyond this threshold can be safely resumed or replaced.</p></td></tr>
                    <tr><th><label for="sc-rl-v630-snapshots">WordPress snapshot retention</label></th><td><input id="sc-rl-v630-snapshots" type="number" min="1" max="20" name="sc_rl_v620[max_wordpress_snapshots]" value="<?php echo esc_attr( $options['max_wordpress_snapshots'] ); ?>"> snapshots</td></tr>
                    <tr><th><label for="sc-rl-v631-retries">Maximum automatic retries</label></th><td><input id="sc-rl-v631-retries" type="number" min="1" max="10" name="sc_rl_v620[max_retry_attempts]" value="<?php echo esc_attr( $options['max_retry_attempts'] ); ?>"> attempts</td></tr>
                    <tr><th><label for="sc-rl-v631-base-delay">Retry base delay</label></th><td><input id="sc-rl-v631-base-delay" type="number" min="10" max="300" name="sc_rl_v620[retry_base_seconds]" value="<?php echo esc_attr( $options['retry_base_seconds'] ); ?>"> seconds</td></tr>
                    <tr><th><label for="sc-rl-v631-max-delay">Retry maximum delay</label></th><td><input id="sc-rl-v631-max-delay" type="number" min="30" max="3600" name="sc_rl_v620[retry_max_seconds]" value="<?php echo esc_attr( $options['retry_max_seconds'] ); ?>"> seconds</td></tr>
                    <tr><th><label for="sc-rl-v631-stalled">Stalled transaction threshold</label></th><td><input id="sc-rl-v631-stalled" type="number" min="5" max="1440" name="sc_rl_v620[stalled_job_minutes]" value="<?php echo esc_attr( $options['stalled_job_minutes'] ); ?>"> minutes</td></tr>
                    <tr><th><label for="sc-rl-v631-alerts">Repeated public-alert suppression</label></th><td><input id="sc-rl-v631-alerts" type="number" min="1" max="120" name="sc_rl_v620[alert_suppression_minutes]" value="<?php echo esc_attr( $options['alert_suppression_minutes'] ); ?>"> minutes</td></tr>
                    <tr><th colspan="2"><h2>Retrieval Calibration</h2><p class="description">These controls are persisted by the backend and applied to public retrieval, evidence gating, and citation verification.</p></th></tr>
                    <tr><th>Ranking weights</th><td>Structural <input type="number" step="0.1" min="0" max="10" name="sc_rl_v620[retrieval_structural_weight]" value="<?php echo esc_attr( $options['retrieval_structural_weight'] ); ?>"> Lexical <input type="number" step="0.1" min="0" max="500" name="sc_rl_v620[retrieval_lexical_weight]" value="<?php echo esc_attr( $options['retrieval_lexical_weight'] ); ?>"> Semantic <input type="number" step="0.1" min="0" max="500" name="sc_rl_v620[retrieval_semantic_weight]" value="<?php echo esc_attr( $options['retrieval_semantic_weight'] ); ?>"> RRF <input type="number" step="1" min="0" max="5000" name="sc_rl_v620[retrieval_rrf_weight]" value="<?php echo esc_attr( $options['retrieval_rrf_weight'] ); ?>"></td></tr>
                    <tr><th>Fusion and evidence gates</th><td>RRF k <input type="number" min="1" max="500" name="sc_rl_v620[retrieval_rrf_k]" value="<?php echo esc_attr( $options['retrieval_rrf_k'] ); ?>"> Minimum score <input type="number" step="0.1" min="0" max="5000" name="sc_rl_v620[retrieval_minimum_score]" value="<?php echo esc_attr( $options['retrieval_minimum_score'] ); ?>"> Minimum sources <input type="number" min="1" max="10" name="sc_rl_v620[retrieval_minimum_sources]" value="<?php echo esc_attr( $options['retrieval_minimum_sources'] ); ?>"> Ambiguity margin <input type="number" step="0.1" min="0" max="1000" name="sc_rl_v620[retrieval_ambiguity_margin]" value="<?php echo esc_attr( $options['retrieval_ambiguity_margin'] ); ?>"></td></tr>
                    <tr><th>Answer verification</th><td>Minimum evidence overlap <input type="number" step="0.01" min="0" max="1" name="sc_rl_v620[retrieval_unsupported_overlap]" value="<?php echo esc_attr( $options['retrieval_unsupported_overlap'] ); ?>"> Minimum citation coverage <input type="number" step="0.01" min="0" max="1" name="sc_rl_v620[retrieval_minimum_citation_coverage]" value="<?php echo esc_attr( $options['retrieval_minimum_citation_coverage'] ); ?>"></td></tr>
                    <tr><th>Context limits</th><td>Maximum sources <input type="number" min="1" max="25" name="sc_rl_v620[retrieval_max_sources]" value="<?php echo esc_attr( $options['retrieval_max_sources'] ); ?>"> Context characters <input type="number" min="2000" max="60000" name="sc_rl_v620[retrieval_max_context_characters]" value="<?php echo esc_attr( $options['retrieval_max_context_characters'] ); ?>"> Passage characters <input type="number" min="300" max="5000" name="sc_rl_v620[retrieval_max_passage_characters]" value="<?php echo esc_attr( $options['retrieval_max_passage_characters'] ); ?>"></td></tr>
                    <tr><th><label for="sc-rl-v650-post-type-weights">Post-type weights</label></th><td><input id="sc-rl-v650-post-type-weights" class="large-text" name="sc_rl_v620[retrieval_post_type_weights]" value="<?php echo esc_attr( $options['retrieval_post_type_weights'] ); ?>"><p class="description">Comma-separated key:value pairs, such as article:1.08,document:1.04.</p></td></tr>
                    <tr><th><label for="sc-rl-v650-source-weights">Source weights</label></th><td><input id="sc-rl-v650-source-weights" class="large-text" name="sc_rl_v620[retrieval_source_weights]" value="<?php echo esc_attr( $options['retrieval_source_weights'] ); ?>"></td></tr>
                    <tr><th><label for="sc-rl-v650-excluded-post-types">Excluded post types</label></th><td><input id="sc-rl-v650-excluded-post-types" class="large-text" name="sc_rl_v620[retrieval_excluded_post_types]" value="<?php echo esc_attr( $options['retrieval_excluded_post_types'] ); ?>"><p class="description">Comma-separated. Exact-title results are also excluded when their post type is listed.</p></td></tr>
                    <tr><th><label for="sc-rl-v650-excluded-sources">Excluded sources</label></th><td><input id="sc-rl-v650-excluded-sources" class="large-text" name="sc_rl_v620[retrieval_excluded_sources]" value="<?php echo esc_attr( $options['retrieval_excluded_sources'] ); ?>"></td></tr>
                    <tr><th><label for="sc-rl-v650-excluded-prefixes">Excluded URL prefixes</label></th><td><textarea id="sc-rl-v650-excluded-prefixes" class="large-text" rows="3" name="sc_rl_v620[retrieval_excluded_url_prefixes]"><?php echo esc_textarea( $options['retrieval_excluded_url_prefixes'] ); ?></textarea><p class="description">One prefix per line.</p></td></tr>
                </table>
                <div class="sc-rl-v702-actions"><button class="button button-primary" type="submit" name="sc_rl_v620_save" value="1">Save Settings</button><button class="button" type="submit" name="sc_rl_v620_test" value="1">Test Python Connection</button><button class="button button-secondary" type="submit" name="sc_rl_v640_process_embeddings" value="1">Continue Semantic Indexing</button></div>
                </details>
                <details class="sc-rl-v702-settings">
                    <summary>Maintenance and recovery tools</summary>
                    <div class="sc-rl-v702-actions"><button class="button" type="submit" name="sc_rl_v620_sync" value="1">Queue Asynchronous Full Sync</button><button class="button" type="submit" name="sc_rl_v630_sync_incremental" value="1">Process Incremental Queue</button><button class="button" type="submit" name="sc_rl_v630_create_snapshot" value="1">Create WordPress Snapshot</button><button class="button" type="submit" name="sc_rl_v630_recover" value="1">Recover Empty Backend</button><button class="button" type="submit" name="sc_rl_v631_repair_stalled" value="1">Repair Stalled Jobs</button><button class="button" type="submit" name="sc_rl_v631_validate_snapshots" value="1">Validate Snapshots</button><button class="button" type="submit" name="sc_rl_v631_clear_retries" value="1">Clear Pending Retries</button><button class="button" type="submit" name="sc_rl_v650_run_benchmark" value="1">Run Retrieval Benchmark</button><button class="button" type="submit" name="sc_rl_v621_repair" value="1">Verify and Queue Repair</button><button class="button" type="submit" name="sc_rl_v621_reset_rate_limits" value="1">Reset Public Rate Limits</button><a class="button" href="<?php echo esc_url( $export_url ); ?>">Export Diagnostics</a></div>
                </details>

                <?php if ( $backend_snapshots ) : ?>
                    <h2>Runtime Rollback</h2>
                    <p><select name="sc_rl_v630_snapshot_id"><option value="">Choose a backend snapshot</option><?php foreach ( $backend_snapshots as $snapshot ) : ?><option value="<?php echo esc_attr( $snapshot['snapshot_id'] ?? '' ); ?>"><?php echo esc_html( ( $snapshot['created_utc'] ?? '' ) . ' · ' . absint( $snapshot['record_count'] ?? 0 ) . ' records · ' . ( $snapshot['reason'] ?? '' ) ); ?></option><?php endforeach; ?></select> <button class="button" type="submit" name="sc_rl_v630_rollback" value="1">Rollback Runtime Index</button></p>
                <?php endif; ?>
            </form>

            <details class="sc-rl-v702-diagnostics">
                <summary>Technical diagnostics and transaction history</summary>
            <table class="widefat striped" style="margin-bottom:18px"><tbody>
                <tr><th>Runtime storage</th><td><?php echo esc_html( is_wp_error( $status ) ? 'Unavailable' : ( $status['storage_engine'] ?? 'sqlite' ) ); ?><?php if ( ! is_wp_error( $status ) ) : ?> · schema <?php echo esc_html( absint( $status['schema_version'] ?? 0 ) ); ?> · index version <?php echo esc_html( absint( $status['index_version'] ?? 0 ) ); ?><?php endif; ?></td></tr>
                <tr><th>Retrieval chunks</th><td><?php echo esc_html( is_wp_error( $status ) ? 'Unavailable' : absint( $status['indexed_chunks'] ?? 0 ) . ' section-aware chunk(s)' ); ?></td></tr>
                <tr><th>Semantic coverage</th><td><?php echo esc_html( is_wp_error( $embedding_status ) ? $embedding_status->get_error_message() : ( number_format_i18n( (float) ( $embedding_status['semantic_coverage'] ?? 0 ), 2 ) . '% · ' . absint( $embedding_status['embedded_chunks'] ?? 0 ) . '/' . absint( $embedding_status['indexed_chunks'] ?? 0 ) . ' chunks · ' . sanitize_text_field( $embedding_status['embedding_model'] ?? '' ) ) ); ?></td></tr>
                <tr><th>Embedding queue</th><td><?php echo esc_html( $embedding_queue_state ? ( sanitize_text_field( $embedding_queue_state['state'] ?? 'unknown' ) . ' · ' . absint( $embedding_queue_state['pending_chunks'] ?? 0 ) . ' pending · updated ' . sanitize_text_field( $embedding_queue_state['updated_utc'] ?? '' ) ) : 'Idle' ); ?></td></tr>
                <tr><th>Gemini credential source</th><td><?php echo esc_html( is_wp_error( $provider_diagnostics ) ? $provider_diagnostics->get_error_message() : ( sanitize_text_field( $provider_diagnostics['credential_source'] ?? 'SC_RL_GEMINI_API_KEY' ) . ' · ' . ( ! empty( $provider_diagnostics['credential_present'] ) ? 'present' : 'missing' ) . ( ! empty( $provider_diagnostics['credential_fingerprint'] ) ? ' · fingerprint ' . sanitize_text_field( $provider_diagnostics['credential_fingerprint'] ) : '' ) ) ); ?></td></tr>
                <tr><th>Retrieval profile</th><td><?php echo esc_html( $retrieval_config ? sanitize_text_field( $retrieval_config['profile'] ?? 'balanced-v6.5.0' ) . ' · RRF k ' . absint( $retrieval_config['rrf_k'] ?? 60 ) : 'Backend calibration unavailable' ); ?></td></tr>
                <tr><th>Evidence gate</th><td><?php echo esc_html( $retrieval_config ? 'Minimum score ' . (float) ( $retrieval_config['thresholds']['minimum_score'] ?? 0 ) . ' · minimum sources ' . absint( $retrieval_config['thresholds']['minimum_sources'] ?? 1 ) . ' · citation coverage ' . (float) ( $retrieval_config['thresholds']['minimum_citation_coverage'] ?? 0 ) : 'Unavailable' ); ?></td></tr>
                <tr><th>Benchmark history</th><td><?php echo esc_html( count( $benchmark_runs ) . ' persisted run(s)' ); ?><?php if ( $benchmark_runs ) : $latest_benchmark = $benchmark_runs[0]; ?> · latest lexical MRR <?php echo esc_html( round( (float) ( $latest_benchmark['metrics']['lexical']['mrr'] ?? 0 ), 3 ) ); ?> · hybrid MRR <?php echo esc_html( round( (float) ( $latest_benchmark['metrics']['hybrid']['mrr'] ?? 0 ), 3 ) ); ?><?php endif; ?></td></tr>
                <tr><th>Backend startup</th><td><?php echo esc_html( is_wp_error( $status ) ? 'Unavailable' : ( sanitize_text_field( $status['startup_state'] ?? 'ready' ) . ' · ' . sanitize_text_field( $status['startup_phase'] ?? 'ready' ) . ' · ' . absint( $status['startup_progress'] ?? 100 ) . '% · uptime ' . absint( $status['uptime_seconds'] ?? 0 ) . 's' ) ); ?></td></tr>
                <tr><th>Stalled backend jobs</th><td><?php echo esc_html( is_wp_error( $status ) ? 'Unknown' : absint( $status['stalled_jobs'] ?? 0 ) ); ?></td></tr>
                <tr><th>Sync retry</th><td><?php echo esc_html( $sync_retry_state ? ( sanitize_text_field( $sync_retry_state['state'] ?? 'unknown' ) . ' · attempt ' . absint( $sync_retry_state['attempt'] ?? 0 ) . '/' . absint( $sync_retry_state['max_attempts'] ?? $options['max_retry_attempts'] ) . ( ! empty( $sync_retry_state['next_run_utc'] ) ? ' · next ' . $sync_retry_state['next_run_utc'] : '' ) ) : 'No pending retry' ); ?></td></tr>
                <tr><th>Recovery progress</th><td><?php echo esc_html( $recovery_state ? ( sanitize_text_field( $recovery_state['state'] ?? 'unknown' ) . ' · ' . sanitize_text_field( $recovery_state['phase'] ?? '' ) . ' · ' . absint( $recovery_state['progress'] ?? 0 ) . '% · attempt ' . absint( $recovery_state['attempt'] ?? 0 ) . '/' . absint( $recovery_state['max_attempts'] ?? $options['max_retry_attempts'] ) ) : 'Idle' ); ?></td></tr>
                <tr><th>Runtime checksum</th><td><code><?php echo esc_html( is_wp_error( $status ) ? '' : ( $status['checksum'] ?? '' ) ); ?></code></td></tr>
                <tr><th>WordPress ledger</th><td><?php echo esc_html( count( $ledger['records'] ) ); ?> records · index v<?php echo esc_html( absint( $ledger['index_version'] ) ); ?> · <code><?php echo esc_html( $ledger['checksum'] ); ?></code></td></tr>
                <tr><th>Canonical snapshot</th><td><?php echo esc_html( $wp_snapshots ? ( $wp_snapshots[0]['snapshot_id'] . ' · ' . $wp_snapshots[0]['record_count'] . ' records · ' . $wp_snapshots[0]['created_utc'] ) : 'No canonical snapshot available' ); ?></td></tr>
                <tr><th>WordPress snapshot integrity</th><td><?php echo esc_html( empty( $wordpress_snapshot_validation['invalid_count'] ) ? 'Passed · ' . absint( $wordpress_snapshot_validation['snapshot_count'] ?? 0 ) . ' snapshot(s)' : 'Failed · ' . absint( $wordpress_snapshot_validation['invalid_count'] ) . ' invalid snapshot(s)' ); ?></td></tr>
                <tr><th>Runtime snapshot integrity</th><td><?php echo esc_html( is_wp_error( $backend_snapshot_validation ) ? $backend_snapshot_validation->get_error_message() : ( empty( $backend_snapshot_validation['invalid_count'] ) ? 'Passed · ' . absint( $backend_snapshot_validation['snapshot_count'] ?? 0 ) . ' snapshot(s)' : 'Failed · ' . absint( $backend_snapshot_validation['invalid_count'] ) . ' invalid snapshot(s)' ) ); ?></td></tr>
                <tr><th>Runtime snapshots</th><td><?php echo esc_html( count( $backend_snapshots ) ); ?> available for rollback</td></tr>
                <tr><th>Incremental queue</th><td><?php echo esc_html( count( $queue ) ); ?> pending change(s)</td></tr>
                <tr><th>Automatic recovery</th><td><?php echo esc_html( '1' === $options['auto_recover'] ? 'Enabled' : 'Disabled' ); ?><?php if ( $diagnostics['cron']['recovery_scheduled'] ) : ?> · scheduled for <?php echo esc_html( $diagnostics['cron']['recovery_next_run_utc'] ); ?><?php endif; ?></td></tr>
                <tr><th>WP-Cron</th><td><?php echo esc_html( $diagnostics['cron']['wp_cron_disabled'] ? 'Disabled by configuration' : ( $diagnostics['cron']['scheduled'] ? 'Scheduled' : 'Not scheduled' ) ); ?><?php if ( $diagnostics['cron']['next_run_utc'] ) : ?> · next run <?php echo esc_html( $diagnostics['cron']['next_run_utc'] ); ?><?php endif; ?></td></tr>
                <tr><th>Public rate limit</th><td><?php echo esc_html( absint( $rate_status['limit'] ?? 0 ) ); ?> questions per <?php echo esc_html( absint( $rate_status['window_minutes'] ?? 0 ) ); ?> minutes · <?php echo esc_html( absint( $rate_status['active_visitors'] ?? 0 ) ); ?> active visitor window(s)</td></tr>
                <tr><th>Latest sync job</th><td><?php echo esc_html( ! empty( $sync_report['job_id'] ) ? $sync_report['job_id'] . ' · ' . $sync_report['state'] : 'No v6.5.1 sync report yet' ); ?></td></tr>
                <tr><th>Inserted / updated / unchanged / deleted</th><td><?php echo esc_html( absint( $sync_report['inserted_records'] ?? 0 ) . ' / ' . absint( $sync_report['updated_records'] ?? 0 ) . ' / ' . absint( $sync_report['unchanged_records'] ?? 0 ) . ' / ' . absint( $sync_report['backend_deleted_records'] ?? 0 ) ); ?></td></tr>
            </tbody></table>
            <?php if ( ! empty( $sync_report['batches'] ) ) : ?>
                <h3>Last Transaction Batches</h3>
                <table class="widefat striped" style="max-width:1100px;margin-bottom:18px"><thead><tr><th>Batch</th><th>Mode</th><th>Sent</th><th>Rejected</th><th>Backend state</th><th>Transaction state</th></tr></thead><tbody>
                <?php foreach ( $sync_report['batches'] as $batch ) : ?><tr><td><?php echo esc_html( absint( $batch['batch'] ) . ' / ' . absint( $batch['batch_count'] ) ); ?></td><td><?php echo esc_html( $batch['mode'] ); ?></td><td><?php echo esc_html( absint( $batch['records_sent'] ) ); ?></td><td><?php echo esc_html( absint( $batch['rejected_records'] ?? 0 ) ); ?></td><td><?php echo esc_html( $batch['backend_state'] ?? '' ); ?></td><td><?php echo esc_html( $batch['state'] ); ?></td></tr><?php endforeach; ?>
                </tbody></table>
            <?php endif; ?>
            <div class="sc-rl-admin-note"><strong>Free-tier recovery boundary:</strong> Render's local SQLite file may be replaced when an instance restarts. WordPress retains the canonical compressed snapshot and automatically rehydrates an empty runtime index.</div>
            </details>
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
            'auto_embed_after_sync' => ! empty( $input['auto_embed_after_sync'] ) ? '1' : '0',
            'embedding_batch_size' => max( 1, min( 250, absint( $input['embedding_batch_size'] ?? $old['embedding_batch_size'] ) ) ),
            'embedding_delay_ms' => max( 0, min( 5000, absint( $input['embedding_delay_ms'] ?? $old['embedding_delay_ms'] ) ) ),
            'embedding_retry_seconds' => max( 60, min( 3600, absint( $input['embedding_retry_seconds'] ?? $old['embedding_retry_seconds'] ) ) ),
            'source_batch_size' => max( 5, min( 100, absint( $input['source_batch_size'] ?? $old['source_batch_size'] ) ) ),
            'build_stale_minutes' => max( 5, min( 120, absint( $input['build_stale_minutes'] ?? $old['build_stale_minutes'] ) ) ),
            'max_wordpress_snapshots' => max( 1, min( 20, absint( isset( $input['max_wordpress_snapshots'] ) ? $input['max_wordpress_snapshots'] : $old['max_wordpress_snapshots'] ) ) ),
            'max_retry_attempts' => max( 1, min( 10, absint( isset( $input['max_retry_attempts'] ) ? $input['max_retry_attempts'] : $old['max_retry_attempts'] ) ) ),
            'retry_base_seconds' => max( 10, min( 300, absint( isset( $input['retry_base_seconds'] ) ? $input['retry_base_seconds'] : $old['retry_base_seconds'] ) ) ),
            'retry_max_seconds' => max( 30, min( 3600, absint( isset( $input['retry_max_seconds'] ) ? $input['retry_max_seconds'] : $old['retry_max_seconds'] ) ) ),
            'stalled_job_minutes' => max( 5, min( 1440, absint( isset( $input['stalled_job_minutes'] ) ? $input['stalled_job_minutes'] : $old['stalled_job_minutes'] ) ) ),
            'alert_suppression_minutes' => max( 1, min( 120, absint( isset( $input['alert_suppression_minutes'] ) ? $input['alert_suppression_minutes'] : $old['alert_suppression_minutes'] ) ) ),
            'retrieval_structural_weight' => max( 0, min( 10, (float) ( $input['retrieval_structural_weight'] ?? $old['retrieval_structural_weight'] ) ) ),
            'retrieval_lexical_weight' => max( 0, min( 500, (float) ( $input['retrieval_lexical_weight'] ?? $old['retrieval_lexical_weight'] ) ) ),
            'retrieval_semantic_weight' => max( 0, min( 500, (float) ( $input['retrieval_semantic_weight'] ?? $old['retrieval_semantic_weight'] ) ) ),
            'retrieval_rrf_weight' => max( 0, min( 5000, (float) ( $input['retrieval_rrf_weight'] ?? $old['retrieval_rrf_weight'] ) ) ),
            'retrieval_rrf_k' => max( 1, min( 500, absint( $input['retrieval_rrf_k'] ?? $old['retrieval_rrf_k'] ) ) ),
            'retrieval_minimum_score' => max( 0, min( 5000, (float) ( $input['retrieval_minimum_score'] ?? $old['retrieval_minimum_score'] ) ) ),
            'retrieval_minimum_sources' => max( 1, min( 10, absint( $input['retrieval_minimum_sources'] ?? $old['retrieval_minimum_sources'] ) ) ),
            'retrieval_ambiguity_margin' => max( 0, min( 1000, (float) ( $input['retrieval_ambiguity_margin'] ?? $old['retrieval_ambiguity_margin'] ) ) ),
            'retrieval_unsupported_overlap' => max( 0, min( 1, (float) ( $input['retrieval_unsupported_overlap'] ?? $old['retrieval_unsupported_overlap'] ) ) ),
            'retrieval_minimum_citation_coverage' => max( 0, min( 1, (float) ( $input['retrieval_minimum_citation_coverage'] ?? $old['retrieval_minimum_citation_coverage'] ) ) ),
            'retrieval_max_sources' => max( 1, min( 25, absint( $input['retrieval_max_sources'] ?? $old['retrieval_max_sources'] ) ) ),
            'retrieval_max_context_characters' => max( 2000, min( 60000, absint( $input['retrieval_max_context_characters'] ?? $old['retrieval_max_context_characters'] ) ) ),
            'retrieval_max_passage_characters' => max( 300, min( 5000, absint( $input['retrieval_max_passage_characters'] ?? $old['retrieval_max_passage_characters'] ) ) ),
            'retrieval_post_type_weights' => sanitize_text_field( $input['retrieval_post_type_weights'] ?? $old['retrieval_post_type_weights'] ),
            'retrieval_source_weights' => sanitize_text_field( $input['retrieval_source_weights'] ?? $old['retrieval_source_weights'] ),
            'retrieval_excluded_post_types' => sanitize_text_field( $input['retrieval_excluded_post_types'] ?? $old['retrieval_excluded_post_types'] ),
            'retrieval_excluded_sources' => sanitize_text_field( $input['retrieval_excluded_sources'] ?? $old['retrieval_excluded_sources'] ),
            'retrieval_excluded_url_prefixes' => sanitize_textarea_field( $input['retrieval_excluded_url_prefixes'] ?? $old['retrieval_excluded_url_prefixes'] ),
        );
        update_option( self::OPTION_NAME, $saved, false );
        return $saved;
    }
}

// Backward-compatible aliases preserve cached admin code and v6.2.x integrations.
if ( ! class_exists( 'SC_RL6_V631_Cold_Start_Recovery_Hardening', false ) ) {
    class_alias( 'SC_RL6_V630_Durable_Index', 'SC_RL6_V631_Cold_Start_Recovery_Hardening' );
}
if ( ! class_exists( 'SC_RL6_V621_Endpoint_Reliability', false ) ) {
    class_alias( 'SC_RL6_V630_Durable_Index', 'SC_RL6_V621_Endpoint_Reliability' );
}
if ( ! class_exists( 'SC_RL6_V620_Knowledge_Intelligence', false ) ) {
    class_alias( 'SC_RL6_V630_Durable_Index', 'SC_RL6_V620_Knowledge_Intelligence' );
}
