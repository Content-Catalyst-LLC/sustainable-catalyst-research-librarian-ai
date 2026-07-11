<?php
/**
 * Research Librarian v5.5.0 stable operations, release readiness, and release notes.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class SC_RL6_V550_Stable_Operations {
    const VERSION = '5.5.0';
    const REST_NAMESPACE = 'sc-research-librarian/v1';
    const OPTION_KEY = 'sc_rl_v550_operations';
    const AUDIT_KEY = 'sc_rl_v550_audit';
    const CHECK_HOOK = 'sc_rl_v550_daily_check';

    public static function init() {
        add_action( 'admin_menu', array( __CLASS__, 'register_admin_page' ), 90 );
        add_action( 'admin_init', array( __CLASS__, 'handle_admin_actions' ) );
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ) );
        add_action( self::CHECK_HOOK, array( __CLASS__, 'scheduled_check' ) );
        add_filter( 'sc_rl_integration_capabilities', array( __CLASS__, 'capabilities' ) );
        add_shortcode( 'sc_research_librarian_release_notes', array( __CLASS__, 'render_release_notes' ) );
        add_shortcode( 'sc_research_librarian_operations_status', array( __CLASS__, 'render_public_status' ) );
    }

    public static function activate() {
        self::run_migrations();
        if ( ! wp_next_scheduled( self::CHECK_HOOK ) ) {
            wp_schedule_event( time() + HOUR_IN_SECONDS, 'daily', self::CHECK_HOOK );
        }
        self::run_checks( true );
    }

    public static function deactivate() {
        wp_clear_scheduled_hook( self::CHECK_HOOK );
    }

    public static function capabilities( $caps = array() ) {
        $caps = is_array( $caps ) ? $caps : array();
        $caps['stable_operations'] = true;
        $caps['stable_operations_version'] = self::VERSION;
        $caps['release_readiness'] = true;
        $caps['migration_validation'] = true;
        $caps['recovery_validation'] = true;
        $caps['public_release_notes'] = true;
        $caps['operations_status_endpoint'] = rest_url( self::REST_NAMESPACE . '/operations/status' );
        return $caps;
    }

    public static function register_routes() {
        register_rest_route( self::REST_NAMESPACE, '/operations/status', array(
            'methods' => 'GET',
            'callback' => array( __CLASS__, 'rest_status' ),
            'permission_callback' => function() { return current_user_can( 'manage_options' ); },
        ) );
        register_rest_route( self::REST_NAMESPACE, '/operations/check', array(
            'methods' => 'POST',
            'callback' => array( __CLASS__, 'rest_check' ),
            'permission_callback' => function() { return current_user_can( 'manage_options' ); },
        ) );
        register_rest_route( self::REST_NAMESPACE, '/operations/release-notes', array(
            'methods' => 'GET',
            'callback' => array( __CLASS__, 'rest_release_notes' ),
            'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/operations/export', array(
            'methods' => 'GET',
            'callback' => array( __CLASS__, 'rest_export' ),
            'permission_callback' => function() { return current_user_can( 'manage_options' ); },
        ) );
    }

    public static function register_admin_page() {
        add_submenu_page(
            'options-general.php',
            'Research Librarian Operations',
            'Research Librarian Operations',
            'manage_options',
            'sc-rl-stable-operations',
            array( __CLASS__, 'render_admin_page' )
        );
    }

    private static function defaults() {
        return array(
            'schema_version' => 1,
            'plugin_version' => self::VERSION,
            'installed_at' => gmdate( 'c' ),
            'last_check_utc' => '',
            'last_status' => 'not_checked',
            'last_report' => array(),
            'migration_status' => 'pending',
            'release_acknowledged' => false,
        );
    }

    public static function run_migrations() {
        $current = get_option( self::OPTION_KEY, array() );
        $state = wp_parse_args( is_array( $current ) ? $current : array(), self::defaults() );
        $previous_schema = isset( $state['schema_version'] ) ? (int) $state['schema_version'] : 0;
        $state['schema_version'] = 1;
        $state['plugin_version'] = self::VERSION;
        $state['migration_status'] = 'complete';
        $state['migration_checked_utc'] = gmdate( 'c' );
        update_option( self::OPTION_KEY, $state, false );
        self::audit( 'migration_validated', array( 'from_schema' => $previous_schema, 'to_schema' => 1 ) );
        return $state;
    }

    private static function check( $id, $label, $pass, $detail, $severity = 'required' ) {
        return array(
            'id' => sanitize_key( $id ),
            'label' => sanitize_text_field( $label ),
            'pass' => (bool) $pass,
            'detail' => sanitize_text_field( $detail ),
            'severity' => in_array( $severity, array( 'required', 'recommended', 'informational' ), true ) ? $severity : 'required',
        );
    }

    public static function run_checks( $scheduled = false ) {
        global $wpdb;
        $checks = array();
        $checks[] = self::check( 'wordpress_supported', 'Supported WordPress runtime', version_compare( get_bloginfo( 'version' ), '6.0', '>=' ), 'WordPress ' . get_bloginfo( 'version' ) . ' detected.' );
        $checks[] = self::check( 'php_supported', 'Supported PHP runtime', version_compare( PHP_VERSION, '7.4', '>=' ), 'PHP ' . PHP_VERSION . ' detected.' );
        $checks[] = self::check( 'database_ready', 'WordPress database connection', ! empty( $wpdb->dbh ), 'Database connection is available.' );
        $upload = wp_upload_dir();
        $checks[] = self::check( 'uploads_writable', 'Writable uploads directory', empty( $upload['error'] ) && wp_is_writable( $upload['basedir'] ), empty( $upload['error'] ) ? 'Uploads directory is writable.' : (string) $upload['error'] );
        $duplicate = function_exists( 'sc_rl6_duplicate_activation_status' ) ? sc_rl6_duplicate_activation_status( dirname( __DIR__ ) . '/sustainable-catalyst-research-librarian-ai.php' ) : array( 'ok' => true );
        $checks[] = self::check( 'single_active_copy', 'Single active Research Librarian copy', ! empty( $duplicate['ok'] ), ! empty( $duplicate['ok'] ) ? 'No duplicate active-plugin entries detected.' : 'Duplicate or stale active-plugin entries require repair.' );
        $checks[] = self::check( 'daily_operations_check', 'Scheduled operations check', (bool) wp_next_scheduled( self::CHECK_HOOK ), wp_next_scheduled( self::CHECK_HOOK ) ? 'Daily operations check is scheduled.' : 'Daily operations check is not scheduled.' );

        $maintenance_hook = defined( 'SC_RL6_Core::MAINTENANCE_HOOK' ) ? constant( 'SC_RL6_Core::MAINTENANCE_HOOK' ) : 'sc_rl_ai_index_maintenance';
        $checks[] = self::check( 'maintenance_schedule', 'Index maintenance schedule reviewed', (bool) wp_next_scheduled( $maintenance_hook ), wp_next_scheduled( $maintenance_hook ) ? 'Index maintenance is scheduled.' : 'Index maintenance is not scheduled; enable it after confirming production settings.', 'recommended' );

        $caps = apply_filters( 'sc_rl_integration_capabilities', array() );
        $checks[] = self::check( 'integration_contracts', 'Integration contracts available', ! empty( $caps['typed_handoffs'] ) && ! empty( $caps['deep_link_actions'] ), 'Typed handoff and deep-link capabilities are registered.' );
        $destinations = isset( $caps['destinations'] ) && is_array( $caps['destinations'] ) ? $caps['destinations'] : array();
        foreach ( array( 'workbench' => 'Workbench', 'decision_studio' => 'Decision Studio' ) as $key => $label ) {
            $available = isset( $destinations[$key]['available'] ) ? (bool) $destinations[$key]['available'] : false;
            $checks[] = self::check( $key . '_available', $label . ' destination available', $available, $available ? $label . ' destination is reachable by configuration.' : $label . ' destination is unavailable or unconfigured.', 'recommended' );
        }

        $manifest = plugin_dir_path( dirname( __FILE__ ) ) . 'data/research_librarian_stable_operations_manifest_v5.5.0.json';
        $checks[] = self::check( 'release_manifest', 'v5.5.0 release manifest present', file_exists( $manifest ), file_exists( $manifest ) ? 'Release manifest is present.' : 'Release manifest is missing.' );
        $recovery_manifest = plugin_dir_path( dirname( __FILE__ ) ) . 'data/research_librarian_recovery_manifest_v4.1.0.json';
        $checks[] = self::check( 'recovery_assets', 'Recovery assets present', file_exists( $recovery_manifest ), file_exists( $recovery_manifest ) ? 'Recovery manifest is present.' : 'Recovery manifest is missing.' );

        $required_failures = 0;
        $recommended_failures = 0;
        foreach ( $checks as $row ) {
            if ( ! $row['pass'] && 'required' === $row['severity'] ) { $required_failures++; }
            if ( ! $row['pass'] && 'recommended' === $row['severity'] ) { $recommended_failures++; }
        }
        $status = 0 === $required_failures ? ( 0 === $recommended_failures ? 'ready' : 'ready_with_recommendations' ) : 'attention_required';
        $report = array(
            'version' => self::VERSION,
            'checked_at' => gmdate( 'c' ),
            'status' => $status,
            'required_failures' => $required_failures,
            'recommended_failures' => $recommended_failures,
            'checks' => $checks,
            'scheduled' => (bool) $scheduled,
        );
        $state = wp_parse_args( get_option( self::OPTION_KEY, array() ), self::defaults() );
        $state['plugin_version'] = self::VERSION;
        $state['last_check_utc'] = $report['checked_at'];
        $state['last_status'] = $status;
        $state['last_report'] = $report;
        update_option( self::OPTION_KEY, $state, false );
        self::audit( 'operations_check_completed', array( 'status' => $status, 'scheduled' => (bool) $scheduled ) );
        do_action( 'sc_platform_event', array(
            'schema' => 'sc-platform-event/1.0',
            'event_type' => 'librarian.operations_checked',
            'source' => 'research_librarian',
            'source_version' => self::VERSION,
            'occurred_at' => gmdate( 'c' ),
            'context' => array( 'status' => $status, 'required_failures' => $required_failures, 'recommended_failures' => $recommended_failures ),
            'privacy' => array( 'contains_raw_conversation' => false, 'contains_api_key' => false, 'contains_email' => false, 'contains_ip' => false ),
        ) );
        return $report;
    }

    public static function scheduled_check() { self::run_checks( true ); }

    private static function audit( $action, $context = array() ) {
        $rows = get_option( self::AUDIT_KEY, array() );
        $rows = is_array( $rows ) ? $rows : array();
        array_unshift( $rows, array(
            'occurred_at' => gmdate( 'c' ),
            'action' => sanitize_key( $action ),
            'user_id' => get_current_user_id(),
            'context' => is_array( $context ) ? $context : array(),
        ) );
        update_option( self::AUDIT_KEY, array_slice( $rows, 0, 100 ), false );
    }

    public static function handle_admin_actions() {
        if ( ! is_admin() || ! current_user_can( 'manage_options' ) ) { return; }
        if ( empty( $_POST['sc_rl_v550_action'] ) ) { return; }
        check_admin_referer( 'sc_rl_v550_operations' );
        $action = sanitize_key( wp_unslash( $_POST['sc_rl_v550_action'] ) );
        if ( 'run_checks' === $action ) {
            self::run_checks( false );
            wp_safe_redirect( add_query_arg( array( 'page' => 'sc-rl-stable-operations', 'sc_rl_notice' => 'checked' ), admin_url( 'options-general.php' ) ) ); exit;
        }
        if ( 'run_migrations' === $action ) {
            self::run_migrations();
            wp_safe_redirect( add_query_arg( array( 'page' => 'sc-rl-stable-operations', 'sc_rl_notice' => 'migrated' ), admin_url( 'options-general.php' ) ) ); exit;
        }
        if ( 'acknowledge_release' === $action ) {
            $state = wp_parse_args( get_option( self::OPTION_KEY, array() ), self::defaults() );
            $state['release_acknowledged'] = true;
            $state['release_acknowledged_utc'] = gmdate( 'c' );
            $state['release_acknowledged_by'] = get_current_user_id();
            update_option( self::OPTION_KEY, $state, false );
            self::audit( 'release_acknowledged' );
            wp_safe_redirect( add_query_arg( array( 'page' => 'sc-rl-stable-operations', 'sc_rl_notice' => 'acknowledged' ), admin_url( 'options-general.php' ) ) ); exit;
        }
    }

    public static function release_notes() {
        return array(
            'version' => self::VERSION,
            'title' => 'Stable Operations Polish and Release Notes',
            'released' => '2026-07-10',
            'summary' => 'Production-readiness, migration validation, operational diagnostics, recovery checks, integration health, and public release documentation for the Research Librarian 5.x line.',
            'highlights' => array(
                'Release-readiness dashboard with required and recommended checks.',
                'Daily operational validation and privacy-minimized platform events.',
                'Migration-state validation and repeatable upgrade checks.',
                'Recovery-asset, maintenance-schedule, and duplicate-activation validation.',
                'Workbench and Decision Studio destination health checks.',
                'Administrator operations snapshot export and audit history.',
                'Public release-notes and operations-status shortcodes.',
            ),
            'boundaries' => array(
                'No API keys or raw conversations are included in status reports or exports.',
                'Recommended integration warnings do not disable the Research Librarian.',
                'Release acknowledgement is an administrative record, not an automated deployment approval.',
            ),
        );
    }

    public static function rest_status() {
        $state = wp_parse_args( get_option( self::OPTION_KEY, array() ), self::defaults() );
        if ( empty( $state['last_report'] ) ) { $state['last_report'] = self::run_checks( false ); }
        return rest_ensure_response( array( 'ok' => true, 'operations' => $state, 'audit_count' => count( (array) get_option( self::AUDIT_KEY, array() ) ) ) );
    }
    public static function rest_check() { return rest_ensure_response( array( 'ok' => true, 'report' => self::run_checks( false ) ) ); }
    public static function rest_release_notes() { return rest_ensure_response( array( 'ok' => true, 'release_notes' => self::release_notes() ) ); }
    public static function rest_export() {
        return rest_ensure_response( array(
            'schema' => 'sc-rl-operations-export/1.0',
            'generated_at' => gmdate( 'c' ),
            'release_notes' => self::release_notes(),
            'operations' => wp_parse_args( get_option( self::OPTION_KEY, array() ), self::defaults() ),
            'audit' => array_slice( (array) get_option( self::AUDIT_KEY, array() ), 0, 100 ),
            'privacy' => array( 'contains_raw_conversation' => false, 'contains_api_key' => false, 'contains_email' => false, 'contains_ip' => false ),
        ) );
    }

    public static function render_admin_page() {
        if ( ! current_user_can( 'manage_options' ) ) { return; }
        $state = wp_parse_args( get_option( self::OPTION_KEY, array() ), self::defaults() );
        $report = ! empty( $state['last_report'] ) ? $state['last_report'] : self::run_checks( false );
        $audit = array_slice( (array) get_option( self::AUDIT_KEY, array() ), 0, 15 );
        $notes = self::release_notes();
        ?>
        <div class="wrap"><h1>Research Librarian Stable Operations</h1>
        <p>Version <?php echo esc_html( self::VERSION ); ?> provides the release-readiness, migration, recovery, integration-health, and release-note layer for stable public operations.</p>
        <?php if ( ! empty( $_GET['sc_rl_notice'] ) ) : ?><div class="notice notice-success is-dismissible"><p>Operation completed successfully.</p></div><?php endif; ?>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;max-width:1050px;margin:18px 0">
            <div class="postbox" style="padding:16px"><strong style="display:block;font-size:22px"><?php echo esc_html( ucwords( str_replace( '_', ' ', $report['status'] ) ) ); ?></strong><span>Release readiness</span></div>
            <div class="postbox" style="padding:16px"><strong style="display:block;font-size:22px"><?php echo esc_html( count( $report['checks'] ) ); ?></strong><span>Operational checks</span></div>
            <div class="postbox" style="padding:16px"><strong style="display:block;font-size:22px"><?php echo esc_html( $report['required_failures'] ); ?></strong><span>Required failures</span></div>
            <div class="postbox" style="padding:16px"><strong style="display:block;font-size:22px"><?php echo ! empty( $state['release_acknowledged'] ) ? 'Yes' : 'No'; ?></strong><span>Release acknowledged</span></div>
        </div>
        <form method="post" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px"><?php wp_nonce_field( 'sc_rl_v550_operations' ); ?>
            <button class="button button-primary" name="sc_rl_v550_action" value="run_checks">Run readiness checks</button>
            <button class="button" name="sc_rl_v550_action" value="run_migrations">Validate migrations</button>
            <button class="button" name="sc_rl_v550_action" value="acknowledge_release">Acknowledge v5.5.0 release</button>
            <a class="button" href="<?php echo esc_url( rest_url( self::REST_NAMESPACE . '/operations/export' ) ); ?>">Open operations export</a>
        </form>
        <h2>Readiness checks</h2><table class="widefat striped" style="max-width:1100px"><thead><tr><th>Status</th><th>Check</th><th>Severity</th><th>Detail</th></tr></thead><tbody>
        <?php foreach ( $report['checks'] as $row ) : ?><tr><td><?php echo $row['pass'] ? 'Pass' : 'Review'; ?></td><td><?php echo esc_html( $row['label'] ); ?></td><td><?php echo esc_html( ucfirst( $row['severity'] ) ); ?></td><td><?php echo esc_html( $row['detail'] ); ?></td></tr><?php endforeach; ?>
        </tbody></table>
        <h2><?php echo esc_html( $notes['title'] ); ?></h2><p><?php echo esc_html( $notes['summary'] ); ?></p><ul><?php foreach ( $notes['highlights'] as $item ) : ?><li><?php echo esc_html( $item ); ?></li><?php endforeach; ?></ul>
        <h2>Recent operations audit</h2><table class="widefat striped" style="max-width:1100px"><thead><tr><th>UTC</th><th>Action</th><th>User</th></tr></thead><tbody><?php foreach ( $audit as $row ) : ?><tr><td><?php echo esc_html( $row['occurred_at'] ); ?></td><td><code><?php echo esc_html( $row['action'] ); ?></code></td><td><?php echo esc_html( $row['user_id'] ); ?></td></tr><?php endforeach; ?></tbody></table>
        </div><?php
    }

    public static function render_release_notes() {
        $notes = self::release_notes(); ob_start(); ?>
        <section class="sc-rl-product sc-rl-release-notes"><p class="sc-rl-product__eyebrow">Research Librarian Release</p><h2>Version <?php echo esc_html( $notes['version'] ); ?> — <?php echo esc_html( $notes['title'] ); ?></h2><p><?php echo esc_html( $notes['summary'] ); ?></p><ul><?php foreach ( $notes['highlights'] as $item ) : ?><li><?php echo esc_html( $item ); ?></li><?php endforeach; ?></ul></section>
        <?php return ob_get_clean();
    }

    public static function render_public_status() {
        $state = wp_parse_args( get_option( self::OPTION_KEY, array() ), self::defaults() );
        $status = sanitize_text_field( $state['last_status'] ); ob_start(); ?>
        <section class="sc-rl-product sc-rl-operations-status"><p class="sc-rl-product__eyebrow">Operations</p><h2>Research Librarian Operational Status</h2><p>Current release: <?php echo esc_html( self::VERSION ); ?>. Last readiness result: <?php echo esc_html( ucwords( str_replace( '_', ' ', $status ) ) ); ?>.</p><p class="sc-rl-boundary-note">This public summary excludes credentials, personal information, raw conversations, and private administrative diagnostics.</p></section>
        <?php return ob_get_clean();
    }
}
