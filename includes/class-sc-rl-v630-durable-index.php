<?php
/**
 * Research Librarian AI v6.6.0 — Platform Intelligence and Typed Research Handoffs.
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class SC_RL6_V630_Durable_Index {
    const VERSION = '6.6.0';
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

    public static function init() {
        add_action( 'admin_menu', array( __CLASS__, 'register_admin_menu' ), 1010 );
        add_action( 'rest_api_init', array( __CLASS__, 'register_rest_routes' ), 110 );
        add_action( self::SYNC_HOOK, array( __CLASS__, 'run_scheduled_sync' ) );
        add_action( self::RECOVERY_HOOK, array( __CLASS__, 'run_backend_recovery' ) );
        add_action( self::INCREMENTAL_HOOK, array( __CLASS__, 'run_incremental_sync' ) );
        add_action( self::SYNC_RETRY_HOOK, array( __CLASS__, 'run_sync_retry' ) );
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
            self::sync_all_records();
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
        $result = self::sync_all_records( 'automatic-retry' );
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
            'schema' => 'sc-research-librarian-sync-recovery-export/6.6.0',
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
            'schema' => 'sc-research-librarian-route-note/6.6.0',
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
        if ( empty( $status['indexed_records'] ) && 'warming' !== sanitize_key( $status['startup_state'] ?? '' ) ) {
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
            'schema' => 'sc-rl-sync-report/6.6.0',
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
        return $status;
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
                $embedding_result = self::request( '/v1/knowledge/embeddings/process', 'POST', array( 'limit' => 20, 'delay_ms' => 200 ) );
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
        $retrieval_config_response = self::request( '/v1/retrieval/config', 'GET' );
        $benchmark_history_response = self::request( '/v1/retrieval/benchmark/history', 'GET' );
        $retrieval_config = ! is_wp_error( $retrieval_config_response ) && isset( $retrieval_config_response['config'] ) ? $retrieval_config_response['config'] : array();
        $benchmark_runs = ! is_wp_error( $benchmark_history_response ) && isset( $benchmark_history_response['runs'] ) && is_array( $benchmark_history_response['runs'] ) ? $benchmark_history_response['runs'] : array();
        $export_url = wp_nonce_url( admin_url( 'admin-post.php?action=sc_rl_v631_export_sync_log' ), 'sc_rl_v631_export_sync_log' );
        ?>
        <div class="wrap">
            <h1>Python Intelligence, Retrieval Calibration, and Durable Index</h1>
            <p>Research Librarian AI v6.5.1 retains benchmark-driven retrieval calibration, minimum-evidence gates, near-duplicate-title protection, unsupported-answer detection, source weighting, exclusions, and latency diagnostics to the v6.4.0 hybrid retrieval engine.</p>
            <?php if ( $notice ) : ?><div class="notice notice-<?php echo esc_attr( $notice_type ); ?> is-dismissible"><p><?php echo esc_html( $notice ); ?></p></div><?php endif; ?>

            <div class="sc-rl-admin-grid">
                <article class="sc-rl-admin-card" data-state="<?php echo esc_attr( is_wp_error( $status ) ? 'offline' : ( $status['state'] ?? 'unknown' ) ); ?>">
                    <h2><?php echo esc_html( is_wp_error( $status ) ? 'Backend unavailable' : ( $status['label'] ?? 'Backend status' ) ); ?></h2>
                    <span class="sc-rl-admin-metric"><?php echo esc_html( is_wp_error( $status ) ? 'Offline' : 'v' . ( $status['version'] ?? self::VERSION ) ); ?></span>
                    <p><?php echo esc_html( is_wp_error( $status ) ? $status->get_error_message() : ( ( $status['storage_engine'] ?? 'sqlite' ) . ' · index v' . absint( $status['index_version'] ?? 0 ) . ' · ' . sanitize_text_field( $status['startup_phase'] ?? 'ready' ) . ' ' . absint( $status['startup_progress'] ?? 100 ) . '%' ) ); ?></p>
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
                <p class="submit"><button class="button button-primary" type="submit" name="sc_rl_v620_save" value="1">Save Settings</button> <button class="button" type="submit" name="sc_rl_v620_test" value="1">Test Backend</button> <button class="button button-secondary" type="submit" name="sc_rl_v620_sync" value="1">Transactional Full Sync</button> <button class="button" type="submit" name="sc_rl_v630_sync_incremental" value="1">Process Incremental Queue</button> <button class="button" type="submit" name="sc_rl_v630_create_snapshot" value="1">Create WordPress Snapshot</button> <button class="button button-secondary" type="submit" name="sc_rl_v630_recover" value="1">Recover Empty Backend</button> <button class="button" type="submit" name="sc_rl_v631_repair_stalled" value="1">Repair Stalled Jobs</button> <button class="button" type="submit" name="sc_rl_v631_validate_snapshots" value="1">Validate Snapshots</button> <button class="button" type="submit" name="sc_rl_v631_clear_retries" value="1">Clear Pending Retries</button> <button class="button button-secondary" type="submit" name="sc_rl_v640_process_embeddings" value="1">Process Embedding Batch</button> <button class="button button-secondary" type="submit" name="sc_rl_v650_run_benchmark" value="1">Run Retrieval Benchmark</button> <button class="button" type="submit" name="sc_rl_v621_repair" value="1">Repair and Resynchronize</button> <button class="button" type="submit" name="sc_rl_v621_reset_rate_limits" value="1">Reset Public Rate Limits</button> <a class="button" href="<?php echo esc_url( $export_url ); ?>">Export Sync and Recovery Log</a></p>

                <?php if ( $backend_snapshots ) : ?>
                    <h2>Runtime Rollback</h2>
                    <p><select name="sc_rl_v630_snapshot_id"><option value="">Choose a backend snapshot</option><?php foreach ( $backend_snapshots as $snapshot ) : ?><option value="<?php echo esc_attr( $snapshot['snapshot_id'] ?? '' ); ?>"><?php echo esc_html( ( $snapshot['created_utc'] ?? '' ) . ' · ' . absint( $snapshot['record_count'] ?? 0 ) . ' records · ' . ( $snapshot['reason'] ?? '' ) ); ?></option><?php endforeach; ?></select> <button class="button" type="submit" name="sc_rl_v630_rollback" value="1">Rollback Runtime Index</button></p>
                <?php endif; ?>
            </form>

            <h2>Durability and Synchronization Diagnostics</h2>
            <table class="widefat striped" style="max-width:1100px;margin-bottom:18px"><tbody>
                <tr><th>Runtime storage</th><td><?php echo esc_html( is_wp_error( $status ) ? 'Unavailable' : ( $status['storage_engine'] ?? 'sqlite' ) ); ?><?php if ( ! is_wp_error( $status ) ) : ?> · schema <?php echo esc_html( absint( $status['schema_version'] ?? 0 ) ); ?> · index version <?php echo esc_html( absint( $status['index_version'] ?? 0 ) ); ?><?php endif; ?></td></tr>
                <tr><th>Retrieval chunks</th><td><?php echo esc_html( is_wp_error( $status ) ? 'Unavailable' : absint( $status['indexed_chunks'] ?? 0 ) . ' section-aware chunk(s)' ); ?></td></tr>
                <tr><th>Semantic coverage</th><td><?php echo esc_html( is_wp_error( $embedding_status ) ? $embedding_status->get_error_message() : ( number_format_i18n( (float) ( $embedding_status['semantic_coverage'] ?? 0 ), 2 ) . '% · ' . absint( $embedding_status['embedded_chunks'] ?? 0 ) . '/' . absint( $embedding_status['indexed_chunks'] ?? 0 ) . ' chunks · ' . sanitize_text_field( $embedding_status['embedding_model'] ?? '' ) ) ); ?></td></tr>
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
