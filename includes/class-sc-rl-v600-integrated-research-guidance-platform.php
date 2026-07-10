<?php
/**
 * Research Librarian v6.0.0 Integrated Research Guidance Platform.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class SC_RL_V600_Integrated_Research_Guidance_Platform {
    const VERSION = '6.0.0';
    const REST_NAMESPACE = 'sc-research-librarian/v1';
    const PLATFORM_SCHEMA = 'sc-integrated-research-guidance/1.0';
    const JOURNEY_SCHEMA = 'sc-research-guidance-journey/1.0';
    const AUDIT_OPTION = 'sc_rl_v600_platform_audit';
    const SETTINGS_OPTION = 'sc_rl_v600_platform_settings';

    public static function init() {
        add_action( 'admin_menu', array( __CLASS__, 'register_admin_page' ), 89 );
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ) );
        add_filter( 'sc_rl_integration_capabilities', array( __CLASS__, 'capabilities' ) );
        add_shortcode( 'sc_research_guidance_platform', array( __CLASS__, 'render_public_platform' ) );
        add_shortcode( 'sc_research_guidance_journey', array( __CLASS__, 'render_public_journey' ) );
    }

    public static function capabilities( $caps = array() ) {
        return array_merge( is_array( $caps ) ? $caps : array(), array(
            'research_librarian_version' => self::VERSION,
            'integrated_research_guidance_platform' => true,
            'guidance_platform_schema' => self::PLATFORM_SCHEMA,
            'guidance_journey_schema' => self::JOURNEY_SCHEMA,
            'source_aware_routing' => true,
            'article_map_guidance' => true,
            'workbench_decision_studio_actions' => true,
            'feature_suggestions_feedback_bridge' => true,
            'research_demand_intelligence' => true,
            'adaptive_prompt_surveys' => true,
            'closed_loop_route_improvement' => true,
            'human_approval_gates' => true,
            'privacy_minimized_events' => true,
        ) );
    }

    private static function settings() {
        return wp_parse_args( get_option( self::SETTINGS_OPTION, array() ), array(
            'public_platform_summary' => true,
            'public_journey' => true,
            'max_audit_rows' => 250,
        ) );
    }

    private static function option_count( $option ) {
        $rows = get_option( $option, array() );
        return is_array( $rows ) ? count( $rows ) : 0;
    }

    private static function module_status() {
        $modules = array(
            'routing_retrieval' => array(
                'label' => 'Source-aware routing and retrieval',
                'available' => class_exists( 'Sustainable_Catalyst_Research_Librarian_AI' ),
                'version' => defined( 'Sustainable_Catalyst_Research_Librarian_AI::VERSION' ) ? Sustainable_Catalyst_Research_Librarian_AI::VERSION : self::VERSION,
            ),
            'article_maps' => array(
                'label' => 'Article-map research guidance',
                'available' => class_exists( 'Sustainable_Catalyst_Research_Librarian_AI_V530_Article_Map_Embeds' ),
                'version' => '5.3.x',
            ),
            'deep_links' => array(
                'label' => 'Workbench and Decision Studio actions',
                'available' => class_exists( 'SC_RL_V540_Deep_Links' ),
                'version' => '5.4.0',
            ),
            'operations' => array(
                'label' => 'Stable operations and release readiness',
                'available' => class_exists( 'SC_RL_V550_Stable_Operations' ),
                'version' => '5.5.0',
            ),
            'feedback_bridge' => array(
                'label' => 'Feature Suggestions feedback bridge',
                'available' => class_exists( 'SC_RL_V560_Feature_Suggestions_Bridge' ),
                'version' => '5.6.0',
                'records' => self::option_count( 'sc_rl_v560_bridge_records' ),
            ),
            'demand_intelligence' => array(
                'label' => 'Research demand and knowledge-gap intelligence',
                'available' => class_exists( 'SC_RL_V570_Research_Demand_Intelligence' ),
                'version' => '5.7.0',
            ),
            'adaptive_experiences' => array(
                'label' => 'Adaptive prompts and surveys',
                'available' => class_exists( 'SC_RL_V580_Adaptive_Prompt_Surveys' ),
                'version' => '5.8.0',
            ),
            'closed_loop_improvement' => array(
                'label' => 'Closed-loop route improvement',
                'available' => class_exists( 'SC_RL_V590_Closed_Loop_Route_Improvement' ),
                'version' => '5.9.0',
                'proposals' => self::option_count( 'sc_rl_v590_route_improvement_proposals' ),
            ),
        );
        foreach ( $modules as $key => $module ) {
            $modules[ $key ]['status'] = ! empty( $module['available'] ) ? 'ready' : 'unavailable';
        }
        return $modules;
    }

    private static function guidance_journey() {
        return array(
            'schema' => self::JOURNEY_SCHEMA,
            'version' => self::VERSION,
            'steps' => array(
                array( 'id'=>'ask', 'label'=>'Ask', 'description'=>'Start with a site-scoped research question or article context.' ),
                array( 'id'=>'route', 'label'=>'Route', 'description'=>'Match the question to the strongest Sustainable Catalyst route and article map.' ),
                array( 'id'=>'source', 'label'=>'Source', 'description'=>'Review ranked source cards, confidence, and coverage notes.' ),
                array( 'id'=>'path', 'label'=>'Continue', 'description'=>'Follow a guided research path or an on-page article-map embed.' ),
                array( 'id'=>'act', 'label'=>'Act', 'description'=>'Open Workbench calculations or create a Decision Studio packet with typed context.' ),
                array( 'id'=>'feedback', 'label'=>'Improve', 'description'=>'Rate the route, report gaps, or submit a contextual feature request.' ),
                array( 'id'=>'learn', 'label'=>'Learn', 'description'=>'Aggregate demand and gap signals for editorial and platform review.' ),
                array( 'id'=>'validate', 'label'=>'Validate', 'description'=>'Apply only human-approved, regression-tested route improvements.' ),
            ),
            'boundaries' => array(
                'Site-scoped research guidance rather than a general-purpose chatbot.',
                'AI, demand scores, and visitor feedback remain advisory.',
                'Route changes require human review and regression checks.',
                'Shared events exclude raw conversations and required personal data.',
            ),
        );
    }

    public static function platform_status() {
        $modules = self::module_status();
        $ready = 0;
        foreach ( $modules as $module ) { if ( 'ready' === $module['status'] ) { $ready++; } }
        return array(
            'schema' => self::PLATFORM_SCHEMA,
            'version' => self::VERSION,
            'status' => $ready === count( $modules ) ? 'ready' : 'attention',
            'ready_modules' => $ready,
            'total_modules' => count( $modules ),
            'modules' => $modules,
            'journey' => self::guidance_journey(),
            'capabilities' => apply_filters( 'sc_rl_integration_capabilities', array() ),
            'privacy' => array(
                'raw_conversations_in_platform_events' => false,
                'required_personal_data' => false,
                'human_review_required' => true,
            ),
            'generated_at_utc' => gmdate( 'c' ),
        );
    }

    private static function audit( $action, $data = array() ) {
        $rows = get_option( self::AUDIT_OPTION, array() );
        $rows = is_array( $rows ) ? $rows : array();
        array_unshift( $rows, array(
            'occurred_at_utc' => gmdate( 'c' ),
            'action' => sanitize_key( $action ),
            'user_id' => get_current_user_id(),
            'data' => is_array( $data ) ? $data : array(),
        ) );
        update_option( self::AUDIT_OPTION, array_slice( $rows, 0, absint( self::settings()['max_audit_rows'] ) ), false );
    }

    private static function publish_event( $type, $data = array() ) {
        do_action( 'sc_platform_event', array(
            'schema' => 'sc-platform-event/1.0',
            'event_type' => sanitize_key( $type ),
            'source' => 'research_librarian',
            'source_version' => self::VERSION,
            'occurred_at' => gmdate( 'c' ),
            'data' => is_array( $data ) ? $data : array(),
        ) );
    }

    public static function register_admin_page() {
        add_submenu_page( 'options-general.php', 'Integrated Research Guidance', 'Research Guidance Platform', 'manage_options', 'sc-rl-integrated-guidance', array( __CLASS__, 'render_admin_page' ) );
    }

    public static function render_admin_page() {
        if ( ! current_user_can( 'manage_options' ) ) { wp_die( 'You do not have permission to access this page.' ); }
        if ( isset( $_POST['sc_rl_v600_refresh'] ) && check_admin_referer( 'sc_rl_v600_refresh' ) ) {
            $status = self::platform_status();
            self::audit( 'platform_status_refreshed', array( 'status'=>$status['status'], 'ready_modules'=>$status['ready_modules'] ) );
            self::publish_event( 'librarian.guidance_platform_checked', array( 'status'=>$status['status'], 'ready_modules'=>$status['ready_modules'], 'total_modules'=>$status['total_modules'] ) );
            echo '<div class="notice notice-success"><p>Integrated guidance platform status refreshed.</p></div>';
        }
        $status = self::platform_status();
        ?>
        <div class="wrap">
            <h1>Integrated Research Guidance Platform</h1>
            <p>Research Librarian v6.0.0 consolidates source-aware routing, article-map guidance, platform actions, contextual feedback, research-demand intelligence, adaptive experiences, and regression-protected route improvement into one governed workflow.</p>
            <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;max-width:1100px;">
                <div class="postbox" style="padding:14px"><strong style="font-size:24px;display:block"><?php echo esc_html( ucfirst( $status['status'] ) ); ?></strong><span>Platform status</span></div>
                <div class="postbox" style="padding:14px"><strong style="font-size:24px;display:block"><?php echo esc_html( $status['ready_modules'] . '/' . $status['total_modules'] ); ?></strong><span>Modules ready</span></div>
                <div class="postbox" style="padding:14px"><strong style="font-size:24px;display:block"><?php echo esc_html( count( $status['journey']['steps'] ) ); ?></strong><span>Guidance stages</span></div>
                <div class="postbox" style="padding:14px"><strong style="font-size:24px;display:block">Human</strong><span>Approval authority</span></div>
            </div>
            <form method="post" style="margin:16px 0">
                <?php wp_nonce_field( 'sc_rl_v600_refresh' ); ?>
                <button class="button button-primary" name="sc_rl_v600_refresh" type="submit">Refresh Platform Status</button>
                <a class="button" href="<?php echo esc_url( rest_url( self::REST_NAMESPACE . '/platform/guidance/export' ) ); ?>">Export platform snapshot</a>
            </form>
            <h2>Integrated Modules</h2>
            <table class="widefat striped"><thead><tr><th>Module</th><th>Version</th><th>Status</th><th>Purpose</th></tr></thead><tbody>
            <?php foreach ( $status['modules'] as $module ) : ?>
                <tr><td><?php echo esc_html( $module['label'] ); ?></td><td><?php echo esc_html( $module['version'] ); ?></td><td><strong><?php echo esc_html( ucfirst( $module['status'] ) ); ?></strong></td><td><?php echo ! empty( $module['available'] ) ? 'Available to the integrated guidance workflow.' : 'Review plugin loading and dependencies.'; ?></td></tr>
            <?php endforeach; ?>
            </tbody></table>
            <h2>Guidance Journey</h2>
            <ol><?php foreach ( $status['journey']['steps'] as $step ) : ?><li><strong><?php echo esc_html( $step['label'] ); ?>:</strong> <?php echo esc_html( $step['description'] ); ?></li><?php endforeach; ?></ol>
            <h2>Public Shortcodes</h2>
            <p><code>[sc_research_guidance_platform]</code></p>
            <p><code>[sc_research_guidance_journey]</code></p>
        </div>
        <?php
    }

    public static function register_routes() {
        register_rest_route( self::REST_NAMESPACE, '/platform/guidance/status', array(
            'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_status' ),
            'permission_callback' => function() { return current_user_can( 'manage_options' ); },
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/guidance/journey', array(
            'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_journey' ),
            'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/guidance/export', array(
            'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_export' ),
            'permission_callback' => function() { return current_user_can( 'manage_options' ); },
        ) );
    }

    public static function rest_status() { return new WP_REST_Response( self::platform_status(), 200 ); }
    public static function rest_journey() { return new WP_REST_Response( self::guidance_journey(), 200 ); }
    public static function rest_export() {
        self::audit( 'platform_snapshot_exported' );
        return new WP_REST_Response( self::platform_status(), 200 );
    }

    public static function render_public_platform( $atts = array() ) {
        if ( empty( self::settings()['public_platform_summary'] ) ) { return ''; }
        $atts = shortcode_atts( array( 'title'=>'Integrated Research Guidance Platform' ), $atts, 'sc_research_guidance_platform' );
        $status = self::platform_status();
        ob_start(); ?>
        <section class="sc-rl-product sc-rl-guidance-platform" data-sc-rl-product="integrated-guidance-platform">
            <p class="sc-rl-product__eyebrow">Research Librarian v6.0</p>
            <h2><?php echo esc_html( $atts['title'] ); ?></h2>
            <p class="sc-rl-product__lede">A site-scoped research workflow connecting source-aware routes, guided paths, Workbench and Decision Studio actions, contextual feedback, demand intelligence, adaptive surveys, and human-approved route improvement.</p>
            <div class="sc-rl-product__grid">
                <?php foreach ( $status['modules'] as $module ) : ?>
                    <article><span><?php echo esc_html( 'ready' === $module['status'] ? 'Ready' : 'Review' ); ?></span><strong><?php echo esc_html( $module['label'] ); ?></strong><p>Version <?php echo esc_html( $module['version'] ); ?> integrated into the governed guidance workflow.</p></article>
                <?php endforeach; ?>
            </div>
            <p class="sc-rl-boundary-note">Site-scoped research guidance only. AI outputs, demand signals, feedback, and route-change proposals remain advisory and subject to human review.</p>
        </section>
        <?php return ob_get_clean();
    }

    public static function render_public_journey( $atts = array() ) {
        if ( empty( self::settings()['public_journey'] ) ) { return ''; }
        $atts = shortcode_atts( array( 'title'=>'How the Research Guidance Loop Works' ), $atts, 'sc_research_guidance_journey' );
        $journey = self::guidance_journey();
        ob_start(); ?>
        <section class="sc-rl-product sc-rl-guidance-journey" data-sc-rl-product="guidance-journey">
            <p class="sc-rl-product__eyebrow">Integrated Guidance Loop</p>
            <h2><?php echo esc_html( $atts['title'] ); ?></h2>
            <div class="sc-rl-path-steps">
                <?php foreach ( $journey['steps'] as $index => $step ) : ?>
                    <article class="sc-rl-path-step"><span><?php echo esc_html( $index + 1 ); ?></span><h3><?php echo esc_html( $step['label'] ); ?></h3><p><?php echo esc_html( $step['description'] ); ?></p></article>
                <?php endforeach; ?>
            </div>
        </section>
        <?php return ob_get_clean();
    }
}
