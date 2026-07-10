<?php
/**
 * Research Librarian v5.3.3 pre-v5.4 integration bridge.
 *
 * Provides contextual feedback, shared events, typed handoff preparation,
 * capability discovery, destination availability checks, and integration health.
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class SC_RL_Pre_V54_Integration {
    const VERSION = '5.3.3';
    const REST_NAMESPACE = 'sc-research-librarian/v1';
    const OPTION = 'sc_rl_pre_v54_integration';
    const EVENT_SCHEMA = 'sc-platform-event/1.0';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ) );
        add_action( 'admin_menu', array( __CLASS__, 'register_admin_page' ), 80 );
        add_action( 'admin_post_sc_rl_send_test_event', array( __CLASS__, 'handle_test_event' ) );
        add_shortcode( 'sc_research_librarian_integration_status', array( __CLASS__, 'render_status_shortcode' ) );
        add_filter( 'sc_rl_integration_capabilities', array( __CLASS__, 'capabilities' ) );
    }

    public static function register_routes() {
        register_rest_route( self::REST_NAMESPACE, '/integration/capabilities', array(
            'methods'             => 'GET',
            'callback'            => array( __CLASS__, 'rest_capabilities' ),
            'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/integration/health', array(
            'methods'             => 'GET',
            'callback'            => array( __CLASS__, 'rest_health' ),
            'permission_callback' => function() { return current_user_can( 'manage_options' ); },
        ) );
        register_rest_route( self::REST_NAMESPACE, '/feedback/contextual', array(
            'methods'             => 'POST',
            'callback'            => array( __CLASS__, 'rest_contextual_feedback' ),
            'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/handoff/typed', array(
            'methods'             => 'POST',
            'callback'            => array( __CLASS__, 'rest_typed_handoff' ),
            'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/events/schema', array(
            'methods'             => 'GET',
            'callback'            => array( __CLASS__, 'rest_event_schema' ),
            'permission_callback' => '__return_true',
        ) );
    }

    public static function capabilities( $caps = array() ) {
        $base = array(
            'research_librarian_version' => defined( 'Sustainable_Catalyst_Research_Librarian_AI::VERSION' ) ? Sustainable_Catalyst_Research_Librarian_AI::VERSION : self::VERSION,
            'bridge_version'             => self::VERSION,
            'event_schema'               => self::EVENT_SCHEMA,
            'contextual_feedback'        => true,
            'feature_suggestions_bridge' => self::feature_suggestions_available(),
            'site_intelligence_events'   => true,
            'typed_handoffs'             => true,
            'destination_checks'         => true,
            'supported_destinations'     => array( 'workbench', 'decision_studio', 'feature_suggestions', 'site_intelligence' ),
            'privacy'                    => array(
                'raw_conversation_exported' => false,
                'api_keys_exported'          => false,
                'personal_data_required'     => false,
            ),
        );
        return array_merge( is_array( $caps ) ? $caps : array(), $base );
    }

    private static function feature_suggestions_available() {
        return has_action( 'scfs_research_librarian_feedback' ) || class_exists( 'Sustainable_Catalyst_Feature_Suggestions' ) || post_type_exists( 'sc_feature_request' );
    }

    private static function destination_status() {
        $workbench_url = apply_filters( 'sc_rl_workbench_url', home_url( '/modeling-analytics/workbench/' ) );
        $decision_url  = apply_filters( 'sc_rl_decision_studio_url', home_url( '/platform/decision-studio/' ) );
        return array(
            'workbench' => array(
                'available' => (bool) apply_filters( 'sc_rl_workbench_available', true ),
                'url'       => esc_url_raw( $workbench_url ),
            ),
            'decision_studio' => array(
                'available' => (bool) apply_filters( 'sc_rl_decision_studio_available', true ),
                'url'       => esc_url_raw( $decision_url ),
            ),
            'feature_suggestions' => array(
                'available' => self::feature_suggestions_available(),
                'url'       => esc_url_raw( apply_filters( 'sc_rl_feature_suggestions_url', home_url( '/feature-suggestions/' ) ) ),
            ),
            'site_intelligence' => array(
                'available' => has_action( 'sc_platform_event' ) || class_exists( 'Sustainable_Catalyst_Site_Intelligence' ),
                'url'       => esc_url_raw( apply_filters( 'sc_rl_site_intelligence_url', home_url( '/platform/site-intelligence/' ) ) ),
            ),
        );
    }

    public static function rest_capabilities() {
        return rest_ensure_response( array(
            'ok'           => true,
            'capabilities' => self::capabilities(),
            'destinations' => self::destination_status(),
        ) );
    }

    public static function rest_health() {
        return rest_ensure_response( self::health_payload() );
    }

    private static function health_payload() {
        $destinations = self::destination_status();
        return array(
            'ok'              => true,
            'version'         => self::VERSION,
            'event_schema'    => self::EVENT_SCHEMA,
            'feature_bridge'  => self::feature_suggestions_available(),
            'event_bus'       => has_action( 'sc_platform_event' ) > 0,
            'destinations'    => $destinations,
            'next_release'    => '5.4.0',
            'release_boundary'=> 'Pre-v5.4 bridge only; no public deep-link action center is enabled by this release.',
        );
    }

    private static function sanitize_context( $input ) {
        $allowed = array(
            'route_id', 'route_label', 'query_topic', 'source_id', 'source_title',
            'source_url', 'article_map', 'session_reference', 'answer_reference',
            'prompt_reference', 'destination', 'feedback_type', 'rating',
            'expected_result', 'message', 'page_url', 'page_id', 'confidence',
        );
        $out = array();
        foreach ( $allowed as $key ) {
            if ( ! isset( $input[ $key ] ) ) {
                continue;
            }
            if ( 'source_url' === $key || 'page_url' === $key ) {
                $out[ $key ] = esc_url_raw( $input[ $key ] );
            } elseif ( 'page_id' === $key || 'rating' === $key ) {
                $out[ $key ] = absint( $input[ $key ] );
            } elseif ( 'message' === $key || 'expected_result' === $key ) {
                $out[ $key ] = sanitize_textarea_field( $input[ $key ] );
            } else {
                $out[ $key ] = sanitize_text_field( $input[ $key ] );
            }
        }
        return $out;
    }

    private static function correlation_id( $context ) {
        $seed = wp_json_encode( array(
            $context['route_id'] ?? '',
            $context['source_id'] ?? '',
            $context['session_reference'] ?? '',
            $context['answer_reference'] ?? '',
            microtime( true ),
            wp_rand(),
        ) );
        return 'rl_' . substr( hash( 'sha256', $seed ), 0, 24 );
    }

    private static function event_payload( $type, $context, $extra = array() ) {
        return array_merge( array(
            'schema'         => self::EVENT_SCHEMA,
            'event_type'     => sanitize_key( $type ),
            'source'         => 'research_librarian',
            'source_version' => self::VERSION,
            'occurred_at'    => gmdate( 'c' ),
            'correlation_id' => self::correlation_id( $context ),
            'context'        => array_filter( array(
                'route_id'       => $context['route_id'] ?? '',
                'query_topic'    => $context['query_topic'] ?? '',
                'source_id'      => $context['source_id'] ?? '',
                'article_map'    => $context['article_map'] ?? '',
                'destination'    => $context['destination'] ?? '',
                'page_id'        => $context['page_id'] ?? 0,
                'confidence'     => $context['confidence'] ?? '',
                'feedback_type'  => $context['feedback_type'] ?? '',
                'rating'         => $context['rating'] ?? 0,
            ) ),
            'privacy'        => array(
                'contains_raw_conversation' => false,
                'contains_api_key'          => false,
                'contains_email'            => false,
                'contains_ip'               => false,
            ),
        ), $extra );
    }

    private static function publish_event( $type, $context, $extra = array() ) {
        $event = self::event_payload( $type, $context, $extra );
        do_action( 'sc_rl_event', $event );
        do_action( 'sc_platform_event', $event );
        return $event;
    }

    public static function rest_contextual_feedback( WP_REST_Request $request ) {
        $context = self::sanitize_context( (array) $request->get_json_params() );
        if ( empty( $context['feedback_type'] ) ) {
            return new WP_Error( 'missing_feedback_type', 'A feedback_type is required.', array( 'status' => 400 ) );
        }
        if ( empty( $context['message'] ) && empty( $context['rating'] ) ) {
            return new WP_Error( 'missing_feedback', 'Provide a message or rating.', array( 'status' => 400 ) );
        }

        $receipt = 'rlf_' . wp_generate_password( 24, false, false );
        $payload = array_merge( $context, array(
            'receipt_token' => $receipt,
            'source'        => 'research_librarian',
            'submitted_at'  => gmdate( 'c' ),
        ) );

        if ( self::feature_suggestions_available() ) {
            do_action( 'scfs_research_librarian_feedback', $payload );
        }
        $event = self::publish_event( 'librarian.feedback_submitted', $context, array(
            'receipt_reference' => substr( hash( 'sha256', $receipt ), 0, 16 ),
            'feature_suggestions_available' => self::feature_suggestions_available(),
        ) );

        return rest_ensure_response( array(
            'ok'          => true,
            'receipt'     => $receipt,
            'event'       => $event,
            'forwarded'   => self::feature_suggestions_available(),
            'human_review'=> true,
        ) );
    }

    public static function rest_typed_handoff( WP_REST_Request $request ) {
        $input = (array) $request->get_json_params();
        $context = self::sanitize_context( $input );
        $destination = sanitize_key( $input['destination'] ?? '' );
        if ( ! in_array( $destination, array( 'workbench', 'decision_studio' ), true ) ) {
            return new WP_Error( 'invalid_destination', 'Destination must be workbench or decision_studio.', array( 'status' => 400 ) );
        }
        $statuses = self::destination_status();
        if ( empty( $statuses[ $destination ]['available'] ) ) {
            return new WP_Error( 'destination_unavailable', 'The requested destination is unavailable.', array( 'status' => 503 ) );
        }
        $payload = array(
            'schema'          => 'sc-research-handoff/1.0',
            'source'          => 'research_librarian',
            'source_version'  => self::VERSION,
            'destination'     => $destination,
            'destination_url' => $statuses[ $destination ]['url'],
            'correlation_id'  => self::correlation_id( $context ),
            'created_at'      => gmdate( 'c' ),
            'route'           => array_filter( array(
                'id'         => $context['route_id'] ?? '',
                'label'      => $context['route_label'] ?? '',
                'topic'      => $context['query_topic'] ?? '',
                'confidence' => $context['confidence'] ?? '',
            ) ),
            'source_context'  => array_filter( array(
                'source_id'    => $context['source_id'] ?? '',
                'source_title' => $context['source_title'] ?? '',
                'source_url'   => $context['source_url'] ?? '',
                'article_map'  => $context['article_map'] ?? '',
                'page_id'      => $context['page_id'] ?? 0,
                'page_url'     => $context['page_url'] ?? '',
            ) ),
            'references'      => array_filter( array(
                'session' => $context['session_reference'] ?? '',
                'answer'  => $context['answer_reference'] ?? '',
                'prompt'  => $context['prompt_reference'] ?? '',
            ) ),
            'requested_action' => sanitize_text_field( $input['requested_action'] ?? '' ),
            'boundary'         => 'Prepared payload only. v5.4.0 will add the public deep-link action experience.',
        );
        $event = self::publish_event( 'librarian.handoff_prepared', array_merge( $context, array( 'destination' => $destination ) ), array(
            'handoff_schema' => $payload['schema'],
        ) );
        return rest_ensure_response( array( 'ok' => true, 'payload' => $payload, 'event' => $event ) );
    }

    public static function rest_event_schema() {
        return rest_ensure_response( array(
            'schema' => self::EVENT_SCHEMA,
            'required' => array( 'schema', 'event_type', 'source', 'source_version', 'occurred_at', 'correlation_id', 'context', 'privacy' ),
            'event_types' => array(
                'librarian.feedback_submitted',
                'librarian.handoff_prepared',
                'librarian.integration_tested',
                'librarian.route_low_confidence',
                'librarian.no_result',
                'librarian.source_rated',
                'librarian.answer_rated',
            ),
        ) );
    }

    public static function register_admin_page() {
        add_submenu_page(
            'options-general.php',
            'Research Librarian Integrations',
            'Research Librarian Integrations',
            'manage_options',
            'sc-rl-integrations',
            array( __CLASS__, 'render_admin_page' )
        );
    }

    public static function render_admin_page() {
        if ( ! current_user_can( 'manage_options' ) ) {
            return;
        }
        $health = self::health_payload();
        ?>
        <div class="wrap">
            <h1>Research Librarian Integration Bridge</h1>
            <p>Version <?php echo esc_html( self::VERSION ); ?> prepares contextual feedback, shared events, destination discovery, and typed handoff contracts for the v5.4.0 deep-link release.</p>
            <table class="widefat striped" style="max-width:900px"><tbody>
                <tr><th>Feature Suggestions bridge</th><td><?php echo $health['feature_bridge'] ? 'Available' : 'Not detected'; ?></td></tr>
                <tr><th>Shared platform event listeners</th><td><?php echo $health['event_bus'] ? 'Detected' : 'No listener detected'; ?></td></tr>
                <tr><th>Event schema</th><td><code><?php echo esc_html( self::EVENT_SCHEMA ); ?></code></td></tr>
                <tr><th>Release boundary</th><td><?php echo esc_html( $health['release_boundary'] ); ?></td></tr>
            </tbody></table>
            <h2>Destination readiness</h2>
            <table class="widefat striped" style="max-width:900px"><thead><tr><th>Destination</th><th>Status</th><th>URL</th></tr></thead><tbody>
            <?php foreach ( $health['destinations'] as $key => $row ) : ?>
                <tr><td><code><?php echo esc_html( $key ); ?></code></td><td><?php echo ! empty( $row['available'] ) ? 'Available' : 'Unavailable'; ?></td><td><?php echo esc_html( $row['url'] ); ?></td></tr>
            <?php endforeach; ?>
            </tbody></table>
            <p><a class="button button-primary" href="<?php echo esc_url( wp_nonce_url( admin_url( 'admin-post.php?action=sc_rl_send_test_event' ), 'sc_rl_send_test_event' ) ); ?>">Publish test integration event</a></p>
            <h2>REST endpoints</h2>
            <p><code><?php echo esc_html( rest_url( self::REST_NAMESPACE . '/integration/capabilities' ) ); ?></code></p>
            <p><code><?php echo esc_html( rest_url( self::REST_NAMESPACE . '/feedback/contextual' ) ); ?></code></p>
            <p><code><?php echo esc_html( rest_url( self::REST_NAMESPACE . '/handoff/typed' ) ); ?></code></p>
        </div>
        <?php
    }

    public static function handle_test_event() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( 'Permission denied.' );
        }
        check_admin_referer( 'sc_rl_send_test_event' );
        self::publish_event( 'librarian.integration_tested', array( 'query_topic' => 'integration health' ) );
        wp_safe_redirect( add_query_arg( 'sc_rl_test_event', 'sent', admin_url( 'options-general.php?page=sc-rl-integrations' ) ) );
        exit;
    }

    public static function render_status_shortcode() {
        $health = self::health_payload();
        ob_start();
        ?>
        <section class="sc-rl-integration-status">
            <p class="sc-rl-product__eyebrow">Integration Readiness</p>
            <h2>Research Librarian Integration Bridge</h2>
            <p>Contextual feedback, shared platform events, typed handoffs, and destination checks are available. Public Decision Studio and Workbench deep-link actions arrive in v5.4.0.</p>
            <ul>
                <li>Feature Suggestions: <?php echo $health['feature_bridge'] ? 'connected' : 'optional bridge not detected'; ?></li>
                <li>Workbench: <?php echo ! empty( $health['destinations']['workbench']['available'] ) ? 'available' : 'unavailable'; ?></li>
                <li>Decision Studio: <?php echo ! empty( $health['destinations']['decision_studio']['available'] ) ? 'available' : 'unavailable'; ?></li>
            </ul>
        </section>
        <?php
        return ob_get_clean();
    }
}
