<?php
/**
 * Research Librarian v5.4.0 Decision Studio / Workbench deep-link actions.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class SC_RL_V540_Deep_Links {
    const VERSION = '5.4.0';
    const REST_NAMESPACE = 'sc-research-librarian/v1';
    const EVENT_SCHEMA = 'sc-platform-event/1.0';
    const HANDOFF_SCHEMA = 'sc-research-handoff/1.1';
    const TOKEN_TTL = 1800;

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ) );
        add_action( 'admin_menu', array( __CLASS__, 'register_admin_page' ), 80 );
        add_shortcode( 'sc_research_librarian_deep_link_status', array( __CLASS__, 'render_status_shortcode' ) );
        add_filter( 'sc_rl_integration_capabilities', array( __CLASS__, 'capabilities' ) );
    }

    public static function register_routes() {
        register_rest_route( self::REST_NAMESPACE, '/integration/capabilities', array(
            'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_capabilities' ), 'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/integration/health', array(
            'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_health' ),
            'permission_callback' => function() { return current_user_can( 'manage_options' ); },
        ) );
        register_rest_route( self::REST_NAMESPACE, '/handoff/typed', array(
            'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_typed_handoff' ), 'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/handoff/deep-link', array(
            'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_deep_link' ), 'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/handoff/resolve/(?P<token>[A-Za-z0-9_-]{24,80})', array(
            'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_resolve' ), 'permission_callback' => '__return_true',
        ) );
        register_rest_route( self::REST_NAMESPACE, '/events/schema', array(
            'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_event_schema' ), 'permission_callback' => '__return_true',
        ) );
    }

    public static function capabilities( $caps = array() ) {
        return array_merge( is_array( $caps ) ? $caps : array(), array(
            'research_librarian_version' => self::VERSION,
            'deep_link_actions' => true,
            'typed_handoffs' => true,
            'handoff_schema' => self::HANDOFF_SCHEMA,
            'destination_checks' => true,
            'tokenized_handoff_resolution' => true,
            'token_ttl_seconds' => self::TOKEN_TTL,
            'supported_actions' => self::action_catalog(),
            'destinations' => self::destination_status(),
            'privacy' => array(
                'raw_conversation_exported' => false,
                'api_keys_exported' => false,
                'personal_data_required' => false,
            ),
        ) );
    }

    private static function action_catalog() {
        return array(
            'workbench' => array(
                'analyze' => 'Analyze in Workbench',
                'calculate' => 'Run a calculation',
                'graph' => 'Build a graph',
                'compare' => 'Compare scenarios',
            ),
            'decision_studio' => array(
                'brief' => 'Create a decision brief',
                'assumptions' => 'Review assumptions',
                'tradeoffs' => 'Compare tradeoffs',
                'scenario' => 'Build a scenario packet',
            ),
        );
    }

    private static function destination_status() {
        return array(
            'workbench' => array(
                'available' => (bool) apply_filters( 'sc_rl_workbench_available', true ),
                'url' => esc_url_raw( apply_filters( 'sc_rl_workbench_url', home_url( '/modeling-analytics/workbench/' ) ) ),
            ),
            'decision_studio' => array(
                'available' => (bool) apply_filters( 'sc_rl_decision_studio_available', true ),
                'url' => esc_url_raw( apply_filters( 'sc_rl_decision_studio_url', home_url( '/platform/decision-studio/' ) ) ),
            ),
        );
    }

    private static function sanitize_context( $input ) {
        $out = array();
        $text = array( 'route_id','route_label','query_topic','article_map','session_reference','answer_reference','prompt_reference','confidence','requested_action' );
        foreach ( $text as $key ) if ( isset( $input[$key] ) ) $out[$key] = sanitize_text_field( $input[$key] );
        if ( isset( $input['page_id'] ) ) $out['page_id'] = absint( $input['page_id'] );
        if ( isset( $input['page_url'] ) ) $out['page_url'] = esc_url_raw( $input['page_url'] );
        if ( isset( $input['question'] ) ) $out['question'] = sanitize_textarea_field( mb_substr( (string) $input['question'], 0, 1400 ) );
        if ( isset( $input['sources'] ) && is_array( $input['sources'] ) ) {
            $out['sources'] = array();
            foreach ( array_slice( $input['sources'], 0, 8 ) as $source ) {
                if ( ! is_array( $source ) ) continue;
                $out['sources'][] = array_filter( array(
                    'id' => sanitize_text_field( $source['id'] ?? $source['source_id'] ?? '' ),
                    'title' => sanitize_text_field( $source['title'] ?? '' ),
                    'url' => esc_url_raw( $source['url'] ?? '' ),
                    'type' => sanitize_text_field( $source['type'] ?? '' ),
                ) );
            }
        }
        return $out;
    }

    private static function correlation_id( $context ) {
        return 'rl_' . substr( hash( 'sha256', wp_json_encode( $context ) . microtime( true ) . wp_rand() ), 0, 24 );
    }

    private static function publish_event( $type, $context, $extra = array() ) {
        $event = array_merge( array(
            'schema' => self::EVENT_SCHEMA,
            'event_type' => sanitize_key( $type ),
            'source' => 'research_librarian',
            'source_version' => self::VERSION,
            'occurred_at' => gmdate( 'c' ),
            'correlation_id' => $context['correlation_id'] ?? self::correlation_id( $context ),
            'context' => array_filter( array(
                'route_id' => $context['route_id'] ?? '',
                'query_topic' => $context['query_topic'] ?? '',
                'destination' => $context['destination'] ?? '',
                'requested_action' => $context['requested_action'] ?? '',
                'page_id' => $context['page_id'] ?? 0,
            ) ),
            'privacy' => array( 'contains_raw_conversation'=>false, 'contains_api_key'=>false, 'contains_email'=>false, 'contains_ip'=>false ),
        ), $extra );
        do_action( 'sc_rl_event', $event );
        do_action( 'sc_platform_event', $event );
        return $event;
    }

    private static function build_payload( $input ) {
        $destination = sanitize_key( $input['destination'] ?? '' );
        $actions = self::action_catalog();
        if ( ! isset( $actions[$destination] ) ) return new WP_Error( 'invalid_destination', 'Destination must be workbench or decision_studio.', array('status'=>400) );
        $action = sanitize_key( $input['requested_action'] ?? '' );
        if ( ! isset( $actions[$destination][$action] ) ) return new WP_Error( 'invalid_action', 'The requested action is not supported for this destination.', array('status'=>400) );
        $status = self::destination_status();
        if ( empty( $status[$destination]['available'] ) ) return new WP_Error( 'destination_unavailable', 'The requested destination is unavailable.', array('status'=>503) );
        $context = self::sanitize_context( $input );
        $correlation = self::correlation_id( $context );
        return array(
            'schema' => self::HANDOFF_SCHEMA,
            'source' => 'research_librarian',
            'source_version' => self::VERSION,
            'destination' => $destination,
            'destination_url' => $status[$destination]['url'],
            'requested_action' => $action,
            'requested_action_label' => $actions[$destination][$action],
            'correlation_id' => $correlation,
            'created_at' => gmdate( 'c' ),
            'expires_at' => gmdate( 'c', time() + self::TOKEN_TTL ),
            'question' => $context['question'] ?? '',
            'route' => array_filter( array(
                'id' => $context['route_id'] ?? '', 'label' => $context['route_label'] ?? '',
                'topic' => $context['query_topic'] ?? '', 'confidence' => $context['confidence'] ?? '',
            ) ),
            'sources' => $context['sources'] ?? array(),
            'article_context' => array_filter( array(
                'article_map' => $context['article_map'] ?? '', 'page_id' => $context['page_id'] ?? 0, 'page_url' => $context['page_url'] ?? '',
            ) ),
            'references' => array_filter( array(
                'session' => $context['session_reference'] ?? '', 'answer' => $context['answer_reference'] ?? '', 'prompt' => $context['prompt_reference'] ?? '',
            ) ),
            'boundary' => 'Educational and analytical handoff only. Destination tools must revalidate inputs and retain their own professional-advice boundaries.',
        );
    }

    public static function rest_typed_handoff( WP_REST_Request $request ) {
        $payload = self::build_payload( (array) $request->get_json_params() );
        if ( is_wp_error( $payload ) ) return $payload;
        $event = self::publish_event( 'librarian.handoff_prepared', array_merge( $payload['route'], array(
            'destination'=>$payload['destination'], 'requested_action'=>$payload['requested_action'], 'correlation_id'=>$payload['correlation_id'],
        ) ), array( 'handoff_schema'=>self::HANDOFF_SCHEMA ) );
        return rest_ensure_response( array( 'ok'=>true, 'payload'=>$payload, 'event'=>$event ) );
    }

    public static function rest_deep_link( WP_REST_Request $request ) {
        $payload = self::build_payload( (array) $request->get_json_params() );
        if ( is_wp_error( $payload ) ) return $payload;
        $token = wp_generate_password( 40, false, false );
        set_transient( 'sc_rl_handoff_' . hash( 'sha256', $token ), $payload, self::TOKEN_TTL );
        $deep_link = add_query_arg( array(
            'sc_rl_handoff' => rawurlencode( $token ),
            'sc_rl_action' => rawurlencode( $payload['requested_action'] ),
            'sc_rl_source' => 'research_librarian',
        ), $payload['destination_url'] );
        $event = self::publish_event( 'librarian.deep_link_created', array_merge( $payload['route'], array(
            'destination'=>$payload['destination'], 'requested_action'=>$payload['requested_action'], 'correlation_id'=>$payload['correlation_id'],
        ) ), array( 'handoff_schema'=>self::HANDOFF_SCHEMA, 'token_ttl'=>self::TOKEN_TTL ) );
        return rest_ensure_response( array(
            'ok'=>true, 'deep_link'=>esc_url_raw($deep_link), 'destination'=>$payload['destination'],
            'requested_action'=>$payload['requested_action'], 'expires_at'=>$payload['expires_at'],
            'fallback_url'=>$payload['destination_url'], 'event'=>$event,
        ) );
    }

    public static function rest_resolve( WP_REST_Request $request ) {
        $token = sanitize_text_field( $request['token'] );
        $key = 'sc_rl_handoff_' . hash( 'sha256', $token );
        $payload = get_transient( $key );
        if ( ! is_array( $payload ) ) return new WP_Error( 'handoff_expired', 'This handoff has expired or is invalid.', array('status'=>404) );
        self::publish_event( 'librarian.deep_link_resolved', array_merge( $payload['route'], array(
            'destination'=>$payload['destination'], 'requested_action'=>$payload['requested_action'], 'correlation_id'=>$payload['correlation_id'],
        ) ) );
        return rest_ensure_response( array( 'ok'=>true, 'payload'=>$payload ) );
    }

    public static function rest_capabilities() { return rest_ensure_response( array('ok'=>true,'capabilities'=>self::capabilities(),'destinations'=>self::destination_status()) ); }
    public static function rest_health() { return rest_ensure_response( array(
        'ok'=>true,'version'=>self::VERSION,'handoff_schema'=>self::HANDOFF_SCHEMA,'destinations'=>self::destination_status(),
        'deep_link_actions'=>true,'token_ttl_seconds'=>self::TOKEN_TTL,'release_boundary'=>'Public Workbench and Decision Studio deep-link actions are enabled.',
    ) ); }
    public static function rest_event_schema() { return rest_ensure_response( array(
        'schema'=>self::EVENT_SCHEMA,
        'event_types'=>array('librarian.handoff_prepared','librarian.deep_link_created','librarian.deep_link_resolved','librarian.deep_link_failed'),
    ) ); }

    public static function register_admin_page() {
        add_submenu_page( 'options-general.php', 'Research Librarian Deep Links', 'Research Librarian Deep Links', 'manage_options', 'sc-rl-deep-links', array(__CLASS__,'render_admin_page') );
    }
    public static function render_admin_page() {
        if ( ! current_user_can('manage_options') ) return;
        $d=self::destination_status(); ?>
        <div class="wrap"><h1>Research Librarian Deep-Link Actions</h1>
        <p>Version <?php echo esc_html(self::VERSION); ?> enables typed, tokenized handoffs from public Research Librarian answers into Workbench and Decision Studio.</p>
        <table class="widefat striped" style="max-width:900px"><thead><tr><th>Destination</th><th>Status</th><th>URL</th></tr></thead><tbody>
        <?php foreach($d as $key=>$row): ?><tr><td><code><?php echo esc_html($key); ?></code></td><td><?php echo $row['available']?'Available':'Unavailable'; ?></td><td><?php echo esc_html($row['url']); ?></td></tr><?php endforeach; ?>
        </tbody></table><h2>Endpoints</h2>
        <p><code><?php echo esc_html(rest_url(self::REST_NAMESPACE.'/handoff/deep-link')); ?></code></p>
        <p><code><?php echo esc_html(rest_url(self::REST_NAMESPACE.'/handoff/resolve/{token}')); ?></code></p>
        <p>Handoff tokens expire after <?php echo esc_html(self::TOKEN_TTL/60); ?> minutes. Destination tools must resolve and revalidate the payload.</p></div><?php
    }
    public static function render_status_shortcode() {
        $d=self::destination_status(); ob_start(); ?>
        <section class="sc-rl-integration-status"><p class="sc-rl-product__eyebrow">Deep-Link Actions</p><h2>Workbench and Decision Studio Handoffs</h2>
        <p>Typed, time-limited handoffs are available from Research Librarian route results.</p><ul>
        <li>Workbench: <?php echo $d['workbench']['available']?'available':'unavailable'; ?></li>
        <li>Decision Studio: <?php echo $d['decision_studio']['available']?'available':'unavailable'; ?></li></ul></section><?php return ob_get_clean();
    }
}
