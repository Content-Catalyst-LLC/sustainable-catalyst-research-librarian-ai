<?php
/**
 * Plugin Name: Sustainable Catalyst Research Librarian
 * Plugin URI: https://sustainablecatalyst.com/platform/research-librarian/
 * Description: Site-scoped routing and retrieval layer for Sustainable Catalyst with source-aware recommendations, a knowledge indexer, admin crawl dashboard, grounded route notes, confidence scoring, Decision Studio and Workbench handoffs, AI-assisted answers, deterministic fallback, and exports.
 * Version: 3.2.0
 * Author: Content Catalyst LLC / Tariq Ahmad
 * Author URI: https://sustainablecatalyst.com/
 * License: GPL-2.0-or-later
 * Text Domain: sustainable-catalyst-research-librarian-ai
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class Sustainable_Catalyst_Research_Librarian_AI {
    const OPTION_NAME    = 'sc_rl_ai_options';
    const INDEX_OPTION   = 'sc_rl_ai_knowledge_index';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';
    const VERSION        = '3.2.0';

    private static $instance = null;

    public static function instance() {
        if ( null === self::$instance ) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        add_action( 'init', array( $this, 'register_shortcodes' ) );
        add_action( 'rest_api_init', array( $this, 'register_rest_routes' ) );
        add_action( 'admin_menu', array( $this, 'register_admin_page' ) );
        add_action( 'admin_init', array( $this, 'register_settings' ) );
        add_filter( 'plugin_action_links_' . plugin_basename( __FILE__ ), array( $this, 'add_settings_link' ) );
    }

    public static function activate() {
        $existing = get_option( self::OPTION_NAME, array() );
        update_option( self::OPTION_NAME, wp_parse_args( $existing, self::defaults() ), false );
        if ( ! get_option( self::INDEX_OPTION, false ) ) {
            update_option( self::INDEX_OPTION, self::build_default_index(), false );
        }
    }

    public static function defaults() {
        return array(
            'provider'                => 'disabled',
            'openai_api_key'          => '',
            'openai_model'            => 'gpt-5.5',
            'openai_vector_store_id'  => '',
            'gemini_api_key'          => '',
            'gemini_model'            => 'gemini-2.5-flash',
            'max_file_search_results' => 6,
            'max_output_tokens'       => 900,
            'temperature'             => '0.2',
            'rate_limit'              => 20,
            'source_result_limit'     => 5,
            'index_max_posts'         => 250,
            'stale_after_days'        => 180,
            'system_instructions'     => self::default_system_instructions(),
        );
    }

    public static function default_system_instructions() {
        return "You are the Sustainable Catalyst Research Librarian, a site-scoped routing and research navigation assistant for Sustainable Catalyst, an open knowledge lab by Tariq Ahmad / Content Catalyst.\n\nYour task is not to be a general chatbot. Help visitors choose the right Sustainable Catalyst route: Knowledge Library, Workbench, Decision Studio, Platform Demos, Catalyst Canvas, Catalyst Data, Analytics R, Global Impact Catalyst, Narrative Risk, Catalyst Finance, Catalyst Grit, methodology, GitHub repositories, consulting, support, or feature suggestions.\n\nAnswer shape:
1. What the visitor appears to need
2. Recommended route
3. Why this route fits
4. Source-aware support from Sustainable Catalyst pages/modules
5. Suggested handoff to Workbench, Decision Studio, or a module when relevant
6. Confidence and unresolved ambiguity
7. Suggested next step

Use only the Sustainable Catalyst routes and source context provided by the plugin. Do not invent pages, capabilities, citations, or repositories. When the match is weak, say that the route is low-confidence and suggest Research Librarian clarification or Feature Suggestions.

Boundaries: educational routing only. Do not provide legal, financial, investment, medical, mental health, tax, compliance, assurance, engineering, architecture, ESG/SDG certification, or regulated-information advice. Do not request confidential, proprietary, sensitive personal, legal, medical, tax, financial, or safety-critical information. If a capability does not exist, say so and route to /platform/feature-suggestions/.";
    }

    private function get_options() {
        $options = wp_parse_args( get_option( self::OPTION_NAME, array() ), self::defaults() );
        // Backward compatibility with v2.1.1 option names.
        if ( empty( $options['openai_api_key'] ) && ! empty( $options['api_key'] ) ) {
            $options['openai_api_key'] = $options['api_key'];
        }
        if ( empty( $options['openai_model'] ) && ! empty( $options['model'] ) ) {
            $options['openai_model'] = $options['model'];
        }
        if ( empty( $options['openai_vector_store_id'] ) && ! empty( $options['vector_store_id'] ) ) {
            $options['openai_vector_store_id'] = $options['vector_store_id'];
        }
        return $options;
    }

    public function add_settings_link( $links ) {
        $url = admin_url( 'options-general.php?page=sc-research-librarian-ai' );
        $links[] = '<a href="' . esc_url( $url ) . '">' . esc_html__( 'Settings', 'sustainable-catalyst-research-librarian-ai' ) . '</a>';
        return $links;
    }

    public function register_shortcodes() {
        add_shortcode( 'sustainable_catalyst_research_librarian_ai', array( $this, 'render_shortcode' ) );
        add_shortcode( 'sc_research_librarian', array( $this, 'render_shortcode' ) );
    }

    public function render_shortcode( $atts = array() ) {
        $atts = shortcode_atts(
            array(
                'mode'        => 'full',
                'title'       => 'Sustainable Catalyst Research Librarian',
                'display'     => 'standard',
                'show_routes' => 'true',
            ),
            $atts,
            'sustainable_catalyst_research_librarian_ai'
        );

        wp_enqueue_style( 'sc-research-librarian-ai', plugins_url( 'assets/sc-research-librarian-ai.css', __FILE__ ), array(), self::VERSION );
        wp_enqueue_script( 'sc-research-librarian-ai', plugins_url( 'assets/sc-research-librarian-ai.js', __FILE__ ), array(), self::VERSION, true );

        $mode = sanitize_key( $atts['mode'] );
        if ( 'landing' === $mode ) {
            return $this->render_landing( $atts );
        }
        if ( 'route-map' === $mode || 'routes' === $mode ) {
            return $this->render_route_map( $atts );
        }
        if ( 'index' === $mode || 'index-summary' === $mode ) {
            return $this->render_index_summary( $atts );
        }
        return $this->render_assistant( $atts );
    }

    private function render_landing( $atts ) {
        ob_start();
        ?>
        <section class="sc-rl-product" data-sc-rl-product="landing">
            <p class="sc-rl-product__eyebrow">Sustainable Catalyst Platform</p>
            <h2><?php echo esc_html( $atts['title'] ); ?></h2>
            <p class="sc-rl-product__lede">The Research Librarian is the source-aware routing and knowledge-index layer for Sustainable Catalyst. It helps visitors move from a question to the right library, module, demo, repository, Workbench tool, or Decision Studio workflow while showing route evidence, confidence, source status, and next handoff.</p>
            <div class="sc-rl-product__grid">
                <article><span>Route</span><strong>Find the right starting point</strong><p>Choose between Knowledge Library, Platform, Demos, Workbench, Decision Studio, modules, methodology, support, and feature suggestions.</p></article>
                <article><span>Connect</span><strong>Explain platform fit</strong><p>Show how Canvas, Data, Analytics R, Global Impact, Narrative Risk, Finance, Grit, Workbench, and Decision Studio connect.</p></article>
                <article><span>Ground</span><strong>Show sources and confidence</strong><p>Turn a question into a structured route note with source records, confidence, reason codes, handoffs, and boundaries.</p></article>
                <article><span>Index</span><strong>Maintain source coverage</strong><p>Use the knowledge indexer to track pages, modules, stale records, missing summaries, duplicate URLs, failed crawl items, and exportable index JSON.</p></article>
            </div>
            <div class="sc-rl-product__actions">
                <a href="/platform/research-librarian/#assistant">Ask the Research Librarian →</a>
                <a href="/platform/">Platform →</a>
                <a href="/platform/demos/">Demos →</a>
            </div>
        </section>
        <?php
        return ob_get_clean();
    }

    private function render_route_map( $atts ) {
        $routes = $this->routes();
        ob_start();
        ?>
        <section class="sc-rl-routes" data-sc-rl-product="routes">
            <p class="sc-rl-routes__eyebrow">Research Librarian Route Map</p>
            <h2><?php echo esc_html( $atts['title'] ); ?></h2>
            <div class="sc-rl-routes__grid">
                <?php foreach ( $routes as $route ) : ?>
                    <article class="sc-rl-route-card">
                        <span><?php echo esc_html( $route['category'] ); ?></span>
                        <h3><?php echo esc_html( $route['title'] ); ?></h3>
                        <p><?php echo esc_html( $route['description'] ); ?></p>
                        <a href="<?php echo esc_url( $route['url'] ); ?>"><?php esc_html_e( 'Open route →', 'sustainable-catalyst-research-librarian-ai' ); ?></a>
                    </article>
                <?php endforeach; ?>
            </div>
        </section>
        <?php
        return ob_get_clean();
    }


    private function render_index_summary( $atts ) {
        $index = $this->knowledge_index();
        $summary = isset( $index['summary'] ) ? $index['summary'] : $this->knowledge_index_summary( isset( $index['records'] ) ? $index['records'] : array() );
        ob_start();
        ?>
        <section class="sc-rl-index-summary" data-sc-rl-product="index-summary">
            <p class="sc-rl-routes__eyebrow">Research Librarian Knowledge Index</p>
            <h2><?php echo esc_html( $atts['title'] ); ?></h2>
            <p>The knowledge index tracks Sustainable Catalyst routes, source records, module pages, and recent public content so route recommendations can show coverage, confidence, and source status.</p>
            <div class="sc-rl-index-summary__grid">
                <article><span><?php echo esc_html( absint( $summary['total_records'] ) ); ?></span><strong>Indexed records</strong></article>
                <article><span><?php echo esc_html( absint( $summary['route_count'] ) ); ?></span><strong>Route groups</strong></article>
                <article><span><?php echo esc_html( absint( $summary['stale_records'] ) ); ?></span><strong>Stale records</strong></article>
                <article><span><?php echo esc_html( absint( $summary['metadata_warnings'] ) ); ?></span><strong>Metadata warnings</strong></article>
            </div>
            <p class="sc-rl-index-summary__meta">Last indexed: <?php echo esc_html( isset( $index['last_indexed_utc'] ) ? $index['last_indexed_utc'] : 'seed only' ); ?></p>
        </section>
        <?php
        return ob_get_clean();
    }

    private function render_assistant( $atts ) {
        $root_id = wp_unique_id( 'sc-rl-ai-' );
        $endpoint = rest_url( self::REST_NAMESPACE . '/ask' );
        $routes_endpoint = rest_url( self::REST_NAMESPACE . '/routes' );
        $note_endpoint = rest_url( self::REST_NAMESPACE . '/route-note' );
        $nonce = wp_create_nonce( 'wp_rest' );
        $compact = ( 'compact' === sanitize_key( $atts['display'] ) || 'compact' === sanitize_key( $atts['mode'] ) );

        ob_start();
        ?>
        <section id="<?php echo esc_attr( $root_id ); ?>" class="sc-rl-ai<?php echo $compact ? ' sc-rl-ai--compact' : ''; ?>" data-endpoint="<?php echo esc_url( $endpoint ); ?>" data-routes-endpoint="<?php echo esc_url( $routes_endpoint ); ?>" data-note-endpoint="<?php echo esc_url( $note_endpoint ); ?>" data-nonce="<?php echo esc_attr( $nonce ); ?>">
            <div class="sc-rl-ai__shell">
                <div class="sc-rl-ai__card sc-rl-ai__ask-card">
                    <p class="sc-rl-ai__eyebrow">Sustainable Catalyst Research Librarian</p>
                    <h2 class="sc-rl-ai__title"><?php echo esc_html( $atts['title'] ); ?></h2>
                    <p class="sc-rl-ai__intro">Ask where to start, which module fits, how Workbench and Decision Studio connect, or how to turn a question into a route through the Sustainable Catalyst platform.</p>

                    <label class="sc-rl-ai__label" for="<?php echo esc_attr( $root_id ); ?>-question">Question or goal</label>
                    <textarea class="sc-rl-ai__textarea" id="<?php echo esc_attr( $root_id ); ?>-question" rows="5" maxlength="1400" placeholder="Example: I need to compare sustainability options, document evidence, and produce an auditable brief. Where should I start?"></textarea>
                    <input type="text" class="sc-rl-ai__hp" value="" tabindex="-1" autocomplete="off" aria-hidden="true" />

                    <div class="sc-rl-ai__actions">
                        <button type="button" class="sc-rl-ai__button sc-rl-ai__button--primary" data-sc-rl-submit>Ask the Librarian</button>
                        <button type="button" class="sc-rl-ai__button sc-rl-ai__button--secondary" data-sc-rl-copy>Copy route note</button>
                        <button type="button" class="sc-rl-ai__button sc-rl-ai__button--secondary" data-sc-rl-download>Download JSON</button>
                        <button type="button" class="sc-rl-ai__button sc-rl-ai__button--ghost" data-sc-rl-clear>Clear</button>
                    </div>

                    <div class="sc-rl-ai__examples" aria-label="Example questions">
                        <button type="button" data-sc-rl-example="I need a sustainability decision brief with assumptions, scenarios, risks, and exports. Where should I start?">Decision brief</button>
                        <button type="button" data-sc-rl-example="I need to calculate, graph, or inspect a formula. Which tool should I use?">Calculation</button>
                        <button type="button" data-sc-rl-example="I need to create a traceable data or evidence record. Where should I go?">Evidence record</button>
                        <button type="button" data-sc-rl-example="I need to review a claim, uncertainty, and narrative risk. Which module fits?">Claim review</button>
                        <button type="button" data-sc-rl-example="I am new to Sustainable Catalyst. What is the best route through the platform?">New visitor</button>
                    </div>
                </div>

                <div class="sc-rl-ai__card sc-rl-ai__answer-card" aria-live="polite">
                    <div class="sc-rl-ai__answer-header">
                        <p class="sc-rl-ai__eyebrow">Route note</p>
                        <span class="sc-rl-ai__status" data-sc-rl-status>Ready</span>
                    </div>
                    <div class="sc-rl-ai__answer" data-sc-rl-answer>
                        <p>Ask a question or choose an example. The librarian will recommend a route, explain why it fits, show related links, and produce an exportable route note.</p>
                    </div>
                    <div class="sc-rl-ai__route-summary" data-sc-rl-route-summary hidden></div>
                    <div class="sc-rl-ai__boundary-note">Educational routing only. No legal, financial, medical, tax, engineering, compliance, assurance, ESG/SDG certification, or regulated-information advice.</div>
                </div>
            </div>

            <?php if ( 'true' === strtolower( (string) $atts['show_routes'] ) ) : ?>
                <div class="sc-rl-ai__route-strip" data-sc-rl-route-strip aria-label="Common routes"></div>
            <?php endif; ?>
        </section>
        <?php
        return ob_get_clean();
    }

    public function register_rest_routes() {
        register_rest_route( self::REST_NAMESPACE, '/ask', array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => array( $this, 'handle_ask_request' ),
            'permission_callback' => '__return_true',
            'args'                => array( 'question' => array( 'required' => true, 'type' => 'string', 'sanitize_callback' => 'sanitize_textarea_field' ) ),
        ) );

        register_rest_route( self::REST_NAMESPACE, '/routes', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_routes_request' ),
            'permission_callback' => '__return_true',
        ) );

        register_rest_route( self::REST_NAMESPACE, '/sources', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_sources_request' ),
            'permission_callback' => '__return_true',
        ) );

        register_rest_route( self::REST_NAMESPACE, '/grounded-route', array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => array( $this, 'handle_grounded_route_request' ),
            'permission_callback' => '__return_true',
        ) );

        register_rest_route( self::REST_NAMESPACE, '/route-note', array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => array( $this, 'handle_route_note_request' ),
            'permission_callback' => '__return_true',
        ) );



        register_rest_route( self::REST_NAMESPACE, '/index/summary', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_index_summary_request' ),
            'permission_callback' => '__return_true',
        ) );

        register_rest_route( self::REST_NAMESPACE, '/index/records', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_index_records_request' ),
            'permission_callback' => '__return_true',
        ) );

        register_rest_route( self::REST_NAMESPACE, '/index/rebuild', array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => array( $this, 'handle_index_rebuild_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );

        register_rest_route( self::REST_NAMESPACE, '/index/export', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_index_export_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );

        register_rest_route( self::REST_NAMESPACE, '/health', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_health_request' ),
            'permission_callback' => '__return_true',
        ) );
    }

    public function handle_health_request() {
        $options = $this->get_options();
        return new WP_REST_Response( array(
            'ok'       => true,
            'version'  => self::VERSION,
            'provider' => $this->configured_provider( $options ),
            'routes'   => count( $this->routes() ),
            'sources'  => count( $this->source_records() ),
            'index'    => $this->knowledge_index_summary( $this->knowledge_index_records() ),
        ), 200 );
    }

    public function handle_routes_request() {
        return new WP_REST_Response( array( 'routes' => $this->routes(), 'version' => self::VERSION ), 200 );
    }

    public function handle_sources_request() {
        return new WP_REST_Response( array( 'sources' => $this->source_records(), 'index' => $this->knowledge_index_summary( $this->knowledge_index_records() ), 'version' => self::VERSION ), 200 );
    }


    public function can_manage_options() {
        return current_user_can( 'manage_options' );
    }

    public function handle_index_summary_request() {
        $index = $this->knowledge_index();
        return new WP_REST_Response( array(
            'version' => self::VERSION,
            'last_indexed_utc' => isset( $index['last_indexed_utc'] ) ? $index['last_indexed_utc'] : null,
            'summary' => isset( $index['summary'] ) ? $index['summary'] : $this->knowledge_index_summary( $this->knowledge_index_records() ),
        ), 200 );
    }

    public function handle_index_records_request() {
        $records = $this->knowledge_index_records();
        $public = array();
        foreach ( $records as $record ) {
            $public[] = array(
                'id' => $record['id'],
                'title' => $record['title'],
                'url' => $record['url'],
                'type' => $record['type'],
                'route_id' => $record['route_id'],
                'summary' => $record['summary'],
                'topics' => $record['topics'],
                'status' => isset( $record['status'] ) ? $record['status'] : 'indexed',
                'metadata_flags' => isset( $record['metadata_flags'] ) ? $record['metadata_flags'] : array(),
                'last_seen_utc' => isset( $record['last_seen_utc'] ) ? $record['last_seen_utc'] : '',
            );
        }
        return new WP_REST_Response( array( 'version' => self::VERSION, 'records' => $public, 'summary' => $this->knowledge_index_summary( $records ) ), 200 );
    }

    public function handle_index_rebuild_request( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_ai_bad_nonce', __( 'Security check failed. Refresh the page and try again.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 403 ) );
        }
        $index = $this->rebuild_knowledge_index();
        return new WP_REST_Response( $index, 200 );
    }

    public function handle_index_export_request() {
        return new WP_REST_Response( $this->knowledge_index(), 200 );
    }

    public function handle_grounded_route_request( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_ai_bad_nonce', __( 'Security check failed. Refresh the page and try again.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 403 ) );
        }
        $params = $request->get_json_params();
        $question = isset( $params['question'] ) ? sanitize_textarea_field( wp_unslash( $params['question'] ) ) : '';
        $route = $this->match_route( strtolower( $question ) );
        $grounding = $this->grounding_context( $question, $route );
        return new WP_REST_Response( array( 'route' => $route, 'grounding' => $grounding, 'route_note' => $this->build_route_note( $question, $route, 'grounded-route', $grounding ) ), 200 );
    }

    public function handle_route_note_request( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_ai_bad_nonce', __( 'Security check failed. Refresh the page and try again.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 403 ) );
        }

        $params = $request->get_json_params();
        $question = isset( $params['question'] ) ? sanitize_textarea_field( wp_unslash( $params['question'] ) ) : '';
        $route = $this->match_route( strtolower( $question ) );
        $grounding = $this->grounding_context( $question, $route );
        $note = $this->build_route_note( $question, $route, 'manual', $grounding );
        return new WP_REST_Response( $note, 200 );
    }

    public function handle_ask_request( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_ai_bad_nonce', __( 'Security check failed. Refresh the page and try again.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 403 ) );
        }

        $params = $request->get_json_params();
        $honeypot = isset( $params['hp'] ) ? sanitize_text_field( wp_unslash( $params['hp'] ) ) : '';
        if ( '' !== $honeypot ) {
            $route = $this->match_route( 'general' );
            $grounding = $this->grounding_context( 'general', $route );
            return new WP_REST_Response( array( 'answer' => $this->fallback_response( 'general', $grounding ), 'source' => 'fallback', 'route' => $route, 'grounding' => $grounding, 'route_note' => $this->build_route_note( 'general', $route, 'fallback', $grounding ) ), 200 );
        }

        $question = isset( $params['question'] ) ? trim( sanitize_textarea_field( wp_unslash( $params['question'] ) ) ) : '';
        if ( '' === $question || strlen( $question ) < 3 ) {
            return new WP_Error( 'sc_rl_ai_empty_question', __( 'Please enter a question.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 400 ) );
        }

        $options = $this->get_options();
        $rate_check = $this->check_rate_limit( absint( $options['rate_limit'] ) );
        if ( is_wp_error( $rate_check ) ) {
            return $rate_check;
        }

        $boundary = $this->boundary_response_if_needed( $question );
        $route = $this->match_route( strtolower( $question ) );
        $grounding = $this->grounding_context( $question, $route );
        if ( $boundary ) {
            return new WP_REST_Response( array( 'answer' => $boundary, 'source' => 'boundary', 'route' => $route, 'grounding' => $grounding, 'route_note' => $this->build_route_note( $question, $route, 'boundary', $grounding ) ), 200 );
        }

        $provider = $this->configured_provider( $options );
        if ( 'disabled' === $provider ) {
            return new WP_REST_Response( array( 'answer' => $this->fallback_response( $question, $grounding ), 'source' => 'fallback', 'route' => $route, 'grounding' => $grounding, 'route_note' => $this->build_route_note( $question, $route, 'fallback', $grounding ) ), 200 );
        }

        $ai_answer = $this->call_ai( $question, $options, $provider, $grounding );
        if ( is_wp_error( $ai_answer ) ) {
            $fallback = "The AI route is temporarily unavailable, so I am using the deterministic route system.\n\n" . $this->fallback_response( $question );
            return new WP_REST_Response( array( 'answer' => $fallback, 'source' => 'fallback', 'error' => $ai_answer->get_error_message(), 'route' => $route, 'route_note' => $this->build_route_note( $question, $route, 'fallback' ) ), 200 );
        }

        $ai_answer = $this->append_grounding_footer( $ai_answer, $grounding );
        return new WP_REST_Response( array( 'answer' => $ai_answer, 'source' => $provider, 'route' => $route, 'grounding' => $grounding, 'route_note' => $this->build_route_note( $question, $route, $provider, $grounding ) ), 200 );
    }

    private function configured_provider( $options ) {
        $provider = isset( $options['provider'] ) ? sanitize_key( $options['provider'] ) : 'disabled';
        if ( 'openai' === $provider && ! empty( $options['openai_api_key'] ) && ! empty( $options['openai_model'] ) ) {
            return 'openai';
        }
        if ( 'gemini' === $provider && ! empty( $options['gemini_api_key'] ) && ! empty( $options['gemini_model'] ) ) {
            return 'gemini';
        }
        return 'disabled';
    }

    private function check_rate_limit( $limit ) {
        $limit = max( 1, min( 100, $limit ? $limit : 20 ) );
        $ip = $this->visitor_ip();
        $key = 'sc_rl_ai_' . md5( $ip . '|' . gmdate( 'YmdH' ) );
        $count = absint( get_transient( $key ) );
        if ( $count >= $limit ) {
            return new WP_Error( 'sc_rl_ai_rate_limit', __( 'Too many questions in a short period. Please try again later.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 429 ) );
        }
        set_transient( $key, $count + 1, HOUR_IN_SECONDS );
        return true;
    }

    private function visitor_ip() {
        foreach ( array( 'HTTP_CF_CONNECTING_IP', 'HTTP_X_FORWARDED_FOR', 'REMOTE_ADDR' ) as $key ) {
            if ( empty( $_SERVER[ $key ] ) ) {
                continue;
            }
            $value = sanitize_text_field( wp_unslash( $_SERVER[ $key ] ) );
            $parts = explode( ',', $value );
            $ip = trim( $parts[0] );
            if ( filter_var( $ip, FILTER_VALIDATE_IP ) ) {
                return $ip;
            }
        }
        $ua = isset( $_SERVER['HTTP_USER_AGENT'] ) ? sanitize_text_field( wp_unslash( $_SERVER['HTTP_USER_AGENT'] ) ) : 'unknown';
        return 'unknown-' . md5( $ua );
    }

    private function boundary_response_if_needed( $question ) {
        $q = strtolower( $question );
        $patterns = array(
            'legal'       => array( '/\b(can i sue|lawsuit|legal advice|is it legal|contract dispute|liable|liability|attorney|lawyer)\b/' ),
            'financial'   => array( '/\b(should i invest|buy stock|sell stock|investment advice|portfolio allocation|financial advice|retirement account|crypto trade)\b/' ),
            'medical'     => array( '/\b(diagnose|diagnosis|treatment plan|medication|mental health advice|therapy advice|self-harm|suicidal)\b/' ),
            'tax'         => array( '/\b(tax advice|tax deduction|tax return|irs|hmrc|revenue service|tax liability)\b/' ),
            'engineering' => array( '/\b(stamp drawings|structural approval|licensed engineer|final engineering design|safety critical design)\b/' ),
            'compliance'  => array( '/\b(certify|certification|assurance|audit opinion|compliance opinion|regulatory approval|esg certification|sdg certification)\b/' ),
        );
        foreach ( $patterns as $area => $regexes ) {
            foreach ( $regexes as $regex ) {
                if ( preg_match( $regex, $q ) ) {
                    return $this->boundary_message( $area );
                }
            }
        }
        return null;
    }

    private function boundary_message( $area ) {
        $labels = array(
            'legal'       => 'legal advice',
            'financial'   => 'financial or investment advice',
            'medical'     => 'medical or mental health advice',
            'tax'         => 'tax advice',
            'engineering' => 'licensed engineering or safety-critical design approval',
            'compliance'  => 'compliance, assurance, or ESG/SDG certification',
        );
        $label = isset( $labels[ $area ] ) ? $labels[ $area ] : 'professional advice';
        return "I can help with educational routing, but I cannot provide {$label}.\n\n**Best starting point**\n[Platform Methodology](/platform/methodology/) for how Sustainable Catalyst handles evidence, assumptions, responsible interpretation, and boundaries.\n\n**Related routes**\n- [Knowledge Libraries](/knowledge-libraries/) for educational article maps and research context.\n- [Research Librarian](/platform/research-librarian/) for site navigation.\n- [Feature Suggestions](/platform/feature-suggestions/) if you need a capability that does not exist yet.\n\nPlease avoid sharing confidential, regulated, personal, legal, medical, tax, financial, or safety-critical information here.";
    }

    private function call_ai( $question, $options, $provider, $grounding = array() ) {
        if ( 'openai' === $provider ) {
            return $this->call_openai( $question, $options, $grounding );
        }
        if ( 'gemini' === $provider ) {
            return $this->call_gemini( $question, $options, $grounding );
        }
        return new WP_Error( 'sc_rl_ai_no_provider', __( 'No AI provider is configured.', 'sustainable-catalyst-research-librarian-ai' ) );
    }

    private function build_instructions( $options, $grounding = array() ) {
        $admin = isset( $options['system_instructions'] ) ? trim( wp_strip_all_tags( $options['system_instructions'] ) ) : '';
        $routes = $this->routes();
        $route_lines = array();
        foreach ( $routes as $route ) {
            $route_lines[] = '- ' . $route['title'] . ': ' . $route['url'] . ' — ' . $route['description'];
        }
        return ( $admin ? $admin : self::default_system_instructions() ) . "\n\nCurrent route map:\n" . implode( "\n", $route_lines );
    }

    private function call_openai( $question, $options, $grounding = array() ) {
        $api_key = trim( $options['openai_api_key'] );
        $model = sanitize_text_field( $options['openai_model'] );
        $vector_store_id = sanitize_text_field( $options['openai_vector_store_id'] );
        $max_results = max( 1, min( 20, absint( $options['max_file_search_results'] ) ) );
        $max_output_tokens = max( 150, min( 4000, absint( $options['max_output_tokens'] ) ) );
        $instructions = $this->build_instructions( $options, $grounding );
        $input = "Visitor question:\n" . $question . "\n\nAnswer as the Sustainable Catalyst Research Librarian. Use Markdown links. Do not request confidential information. If the requested route does not exist, route to /platform/feature-suggestions/.";

        $body = array(
            'model'             => $model,
            'instructions'      => $instructions,
            'input'             => $input,
            'max_output_tokens' => $max_output_tokens,
        );
        if ( '' !== $vector_store_id ) {
            $body['tools'] = array( array( 'type' => 'file_search', 'vector_store_ids' => array( $vector_store_id ), 'max_num_results' => $max_results ) );
        }
        $response = wp_remote_post( 'https://api.openai.com/v1/responses', array(
            'headers' => array( 'Authorization' => 'Bearer ' . $api_key, 'Content-Type' => 'application/json' ),
            'body'    => wp_json_encode( $body ),
            'timeout' => 30,
        ) );
        if ( is_wp_error( $response ) ) {
            return $response;
        }
        $code = wp_remote_retrieve_response_code( $response );
        $raw = wp_remote_retrieve_body( $response );
        $data = json_decode( $raw, true );
        if ( $code < 200 || $code >= 300 ) {
            $message = isset( $data['error']['message'] ) ? $data['error']['message'] : 'OpenAI request failed.';
            return new WP_Error( 'sc_rl_ai_openai_error', sanitize_text_field( $message ) );
        }
        $text = $this->extract_openai_text( $data );
        if ( '' === trim( $text ) ) {
            return new WP_Error( 'sc_rl_ai_empty_ai_response', __( 'The AI response did not include readable text.', 'sustainable-catalyst-research-librarian-ai' ) );
        }
        return trim( wp_strip_all_tags( $text, false ) );
    }

    private function extract_openai_text( $data ) {
        if ( isset( $data['output_text'] ) && is_string( $data['output_text'] ) ) {
            return $data['output_text'];
        }
        $parts = array();
        if ( isset( $data['output'] ) && is_array( $data['output'] ) ) {
            foreach ( $data['output'] as $item ) {
                if ( isset( $item['content'] ) && is_array( $item['content'] ) ) {
                    foreach ( $item['content'] as $content ) {
                        if ( isset( $content['text'] ) && is_string( $content['text'] ) ) {
                            $parts[] = $content['text'];
                        } elseif ( isset( $content['output_text'] ) && is_string( $content['output_text'] ) ) {
                            $parts[] = $content['output_text'];
                        }
                    }
                }
            }
        }
        return implode( "\n\n", $parts );
    }

    private function call_gemini( $question, $options, $grounding = array() ) {
        $api_key = trim( $options['gemini_api_key'] );
        $model = sanitize_text_field( $options['gemini_model'] );
        $max_output_tokens = max( 150, min( 4000, absint( $options['max_output_tokens'] ) ) );
        $temperature = is_numeric( $options['temperature'] ) ? (float) $options['temperature'] : 0.2;
        $instructions = $this->build_instructions( $options, $grounding );
        $prompt = $instructions . "\n\nVisitor question:\n" . $question . "\n\nAnswer as the Sustainable Catalyst Research Librarian using concise Markdown links.";
        $url = 'https://generativelanguage.googleapis.com/v1beta/models/' . rawurlencode( $model ) . ':generateContent?key=' . rawurlencode( $api_key );
        $body = array(
            'contents' => array( array( 'role' => 'user', 'parts' => array( array( 'text' => $prompt ) ) ) ),
            'generationConfig' => array( 'maxOutputTokens' => $max_output_tokens, 'temperature' => $temperature ),
        );
        $response = wp_remote_post( $url, array( 'headers' => array( 'Content-Type' => 'application/json' ), 'body' => wp_json_encode( $body ), 'timeout' => 30 ) );
        if ( is_wp_error( $response ) ) {
            return $response;
        }
        $code = wp_remote_retrieve_response_code( $response );
        $raw = wp_remote_retrieve_body( $response );
        $data = json_decode( $raw, true );
        if ( $code < 200 || $code >= 300 ) {
            $message = isset( $data['error']['message'] ) ? $data['error']['message'] : 'Gemini request failed.';
            return new WP_Error( 'sc_rl_ai_gemini_error', sanitize_text_field( $message ) );
        }
        $parts = array();
        if ( isset( $data['candidates'][0]['content']['parts'] ) && is_array( $data['candidates'][0]['content']['parts'] ) ) {
            foreach ( $data['candidates'][0]['content']['parts'] as $part ) {
                if ( isset( $part['text'] ) && is_string( $part['text'] ) ) {
                    $parts[] = $part['text'];
                }
            }
        }
        $text = implode( "\n\n", $parts );
        if ( '' === trim( $text ) ) {
            return new WP_Error( 'sc_rl_ai_empty_gemini_response', __( 'The Gemini response did not include readable text.', 'sustainable-catalyst-research-librarian-ai' ) );
        }
        return trim( wp_strip_all_tags( $text, false ) );
    }

    private function fallback_response( $question, $grounding = array() ) {
        $route = $this->match_route( strtolower( $question ) );
        $answer = "**What you seem to be trying to do**\n" . $route['intent'] . "\n\n";
        $answer .= "**Best starting point**\n[" . $route['title'] . "](" . $route['url'] . ")\n\n";
        $answer .= "**Why this route fits**\n" . $route['why'] . "\n\n";
        $answer .= "**How it connects to the platform**\n" . $route['platform_fit'] . "\n\n";
        $answer .= "**Relevant links**\n";
        foreach ( $route['related'] as $label => $url ) {
            $answer .= "- [" . $label . "](" . $url . ")\n";
        }
        $answer .= "\n**Suggested next step**\n" . $route['next_step'] . "\n\nIf you are looking for a capability that does not exist yet, use [Feature Suggestions](/platform/feature-suggestions/).";
        return $answer;
    }

    private function build_route_note( $question, $route, $source, $grounding = array() ) {
        return array(
            'version'        => self::VERSION,
            'created_at_utc' => gmdate( 'c' ),
            'source'         => $source,
            'question'       => $question,
            'recommended_route' => array(
                'id'          => $route['id'],
                'title'       => $route['title'],
                'url'         => $route['url'],
                'category'    => $route['category'],
                'description' => $route['description'],
            ),
            'intent'       => $route['intent'],
            'why'          => $route['why'],
            'platform_fit' => $route['platform_fit'],
            'related'      => $route['related'],
            'next_step'    => $route['next_step'],
            'confidence'   => isset( $grounding['confidence'] ) ? $grounding['confidence'] : array(),
            'reason_codes' => isset( $grounding['reason_codes'] ) ? $grounding['reason_codes'] : array(),
            'sources'      => isset( $grounding['sources'] ) ? $grounding['sources'] : array(),
            'handoffs'     => isset( $grounding['handoffs'] ) ? $grounding['handoffs'] : array(),
            'ambiguity'    => isset( $grounding['ambiguity'] ) ? $grounding['ambiguity'] : array(),
            'boundaries'   => array(
                'Educational routing only.',
                'No legal, financial, medical, tax, engineering, compliance, assurance, or ESG/SDG certification advice.',
                'Do not submit confidential, regulated, proprietary, sensitive personal, or safety-critical information.',
            ),
        );
    }


    private function append_grounding_footer( $answer, $grounding ) {
        if ( empty( $grounding ) || ! is_array( $grounding ) ) {
            return $answer;
        }
        $footer = "\n\n**Grounding note**\n";
        if ( ! empty( $grounding['confidence']['level'] ) ) {
            $footer .= 'Route confidence: ' . ucfirst( $grounding['confidence']['level'] ) . ' — ' . $grounding['confidence']['explanation'] . "\n";
        }
        if ( ! empty( $grounding['sources'] ) ) {
            $footer .= "\n**Relevant Sustainable Catalyst sources**\n";
            foreach ( $grounding['sources'] as $source ) {
                $footer .= '- [' . $source['title'] . '](' . $source['url'] . ') — ' . $source['summary'] . "\n";
            }
        }
        if ( ! empty( $grounding['handoffs'] ) ) {
            $footer .= "\n**Possible handoffs**\n";
            foreach ( $grounding['handoffs'] as $handoff ) {
                $footer .= '- ' . $handoff['label'] . ': ' . $handoff['reason'] . ' ([open](' . $handoff['url'] . "))\n";
            }
        }
        return trim( $answer ) . $footer;
    }

    private function grounding_context( $question, $route ) {
        $sources = $this->match_sources( $question, $route );
        $reason_codes = $this->reason_codes( $question, $route, $sources );
        $confidence = $this->route_confidence( $question, $route, $sources, $reason_codes );
        return array(
            'sources'      => $sources,
            'reason_codes' => $reason_codes,
            'confidence'   => $confidence,
            'handoffs'     => $this->route_handoffs( $route ),
            'ambiguity'    => $this->route_ambiguity( $route, $confidence ),
        );
    }

    private function normalize_terms( $text ) {
        $text = strtolower( wp_strip_all_tags( (string) $text ) );
        $text = preg_replace( '/[^a-z0-9\s\-]/', ' ', $text );
        $parts = preg_split( '/\s+/', $text );
        $stop = array( 'the', 'and', 'for', 'with', 'that', 'this', 'from', 'into', 'about', 'where', 'what', 'when', 'how', 'why', 'need', 'needs', 'use', 'using', 'can', 'should', 'would', 'could', 'are', 'you', 'your', 'our', 'their', 'there', 'here' );
        $terms = array();
        foreach ( $parts as $part ) {
            $part = trim( $part );
            if ( strlen( $part ) < 3 || in_array( $part, $stop, true ) ) {
                continue;
            }
            $terms[] = $part;
        }
        return array_values( array_unique( $terms ) );
    }

    private function match_sources( $question, $route ) {
        $terms = $this->normalize_terms( $question . ' ' . $route['title'] . ' ' . $route['category'] );
        $scored = array();
        foreach ( $this->knowledge_index_records() as $record ) {
            $haystack = strtolower( ( $record['title'] ?? '' ) . ' ' . ( $record['type'] ?? '' ) . ' ' . ( $record['summary'] ?? '' ) . ' ' . implode( ' ', isset( $record['topics'] ) && is_array( $record['topics'] ) ? $record['topics'] : array() ) . ' ' . ( $record['route_id'] ?? '' ) );
            $score = 0;
            if ( isset( $record['route_id'] ) && $record['route_id'] === $route['id'] ) {
                $score += 12;
            }
            foreach ( $terms as $term ) {
                if ( false !== strpos( $haystack, $term ) ) {
                    $score += 2;
                }
            }
            if ( ! empty( $record['priority'] ) ) {
                $score += (int) $record['priority'];
            }
            if ( $score > 0 ) {
                $record['score'] = $score;
                $scored[] = $record;
            }
        }
        usort( $scored, function( $a, $b ) { return $b['score'] <=> $a['score']; } );
        $options = $this->get_options();
        $limit = max( 3, min( 8, absint( isset( $options['source_result_limit'] ) ? $options['source_result_limit'] : 5 ) ) );
        return array_slice( $scored, 0, $limit );
    }

    private function reason_codes( $question, $route, $sources ) {
        $codes = array();
        $q = strtolower( $question );
        foreach ( $route['keys'] as $key ) {
            if ( false !== strpos( $q, $key ) ) {
                $codes[] = 'keyword:' . $key;
            }
        }
        if ( ! empty( $sources ) ) {
            $codes[] = 'source-match:' . count( $sources );
        }
        if ( ! empty( $route['related'] ) ) {
            $codes[] = 'related-routes:' . count( $route['related'] );
        }
        if ( empty( $codes ) ) {
            $codes[] = 'default-platform-route';
        }
        return array_values( array_unique( $codes ) );
    }

    private function route_confidence( $question, $route, $sources, $reason_codes ) {
        $top = ! empty( $sources[0]['score'] ) ? (int) $sources[0]['score'] : 0;
        $keyword_hits = 0;
        foreach ( $reason_codes as $code ) {
            if ( 0 === strpos( $code, 'keyword:' ) ) {
                $keyword_hits++;
            }
        }
        $score = min( 100, ( $keyword_hits * 18 ) + ( min( $top, 30 ) * 2 ) + ( count( $sources ) * 3 ) );
        $level = 'low';
        if ( $score >= 75 ) {
            $level = 'high';
        } elseif ( $score >= 45 ) {
            $level = 'medium';
        }
        $explanation = 'Matched ' . count( $sources ) . ' source record(s) and ' . $keyword_hits . ' route keyword signal(s).';
        if ( 'platform' === $route['id'] && $keyword_hits < 1 ) {
            $level = 'low';
            $explanation = 'The question is broad or ambiguous, so the platform overview is the safest starting route.';
        }
        return array( 'level' => $level, 'score' => $score, 'explanation' => $explanation );
    }

    private function route_ambiguity( $route, $confidence ) {
        if ( isset( $confidence['level'] ) && 'high' === $confidence['level'] ) {
            return array();
        }
        $items = array();
        if ( 'low' === $confidence['level'] ) {
            $items[] = 'The request may need one more detail about the intended output: learning route, calculation, module artifact, or decision brief.';
        }
        if ( 'platform' === $route['id'] ) {
            $items[] = 'Defaulted to Platform because no specialized module clearly dominated the route match.';
        }
        return $items;
    }

    private function route_handoffs( $route ) {
        $id = $route['id'];
        if ( 'decision-studio' === $id ) {
            return array(
                array( 'id' => 'workbench', 'label' => 'Workbench', 'url' => 'https://sustainablecatalyst.com/modeling-analytics/workbench/', 'reason' => 'Use when the decision packet needs deeper calculation, graphing, symbolic review, or model inspection.' ),
                array( 'id' => 'demos', 'label' => 'Platform Demos', 'url' => '/platform/demos/', 'reason' => 'Use to create module artifacts before synthesizing a packet.' ),
            );
        }
        if ( 'workbench' === $id ) {
            return array(
                array( 'id' => 'decision-studio', 'label' => 'Decision Studio', 'url' => '/platform/#decision-studio', 'reason' => 'Use when calculator results need to become part of a broader Decision Packet.' ),
                array( 'id' => 'modeling', 'label' => 'Modeling & Analytics', 'url' => '/modeling-analytics/', 'reason' => 'Use for related article maps and modeling context.' ),
            );
        }
        if ( in_array( $id, array( 'canvas', 'data', 'analytics-r', 'impact', 'narrative-risk', 'finance', 'grit' ), true ) ) {
            return array(
                array( 'id' => 'decision-studio', 'label' => 'Decision Studio', 'url' => '/platform/#decision-studio', 'reason' => 'Import or summarize this module output into a Decision Packet.' ),
            );
        }
        return array(
            array( 'id' => 'research-librarian', 'label' => 'Research Librarian', 'url' => '/platform/research-librarian/', 'reason' => 'Ask a more specific follow-up if the route needs narrowing.' ),
        );
    }


    public static function build_default_index() {
        $now = gmdate( 'c' );
        $records = array(
            array( 'id' => 'platform', 'route_id' => 'platform', 'type' => 'architecture-page', 'title' => 'Platform', 'url' => '/platform/', 'summary' => 'Architecture page connecting Decision Studio, Workbench, modules, methodology, demos, and open development.', 'topics' => array( 'platform', 'architecture', 'decision studio', 'workbench', 'modules' ), 'priority' => 5 ),
            array( 'id' => 'demos', 'route_id' => 'demos', 'type' => 'demo-hub', 'title' => 'Platform Demos', 'url' => '/platform/demos/', 'summary' => 'Workflow demo hub for Canvas, Data, Analytics R, Global Impact, Narrative Risk, Finance, Grit, Workbench, and Decision Studio.', 'topics' => array( 'demos', 'workflow', 'modules', 'artifacts' ), 'priority' => 5 ),
            array( 'id' => 'research-librarian', 'route_id' => 'platform', 'type' => 'routing-page', 'title' => 'Research Librarian', 'url' => '/platform/research-librarian/', 'summary' => 'Site-scoped routing assistant for choosing Sustainable Catalyst pages, modules, tools, repositories, and workflows.', 'topics' => array( 'routing', 'assistant', 'research librarian', 'navigation' ), 'priority' => 4 ),
            array( 'id' => 'decision-studio', 'route_id' => 'decision-studio', 'type' => 'platform-module', 'title' => 'Sustainable Catalyst Decision Studio', 'url' => '/platform/#decision-studio', 'summary' => 'Decision Packet workspace for artifact imports, four-pillar review, scenarios, audit/provenance, readiness, handoffs, saved packets, and exportable briefs.', 'topics' => array( 'decision packet', 'brief', 'audit', 'readiness', 'scenario comparison', 'sustainability' ), 'priority' => 6 ),
            array( 'id' => 'workbench', 'route_id' => 'workbench', 'type' => 'analytical-workspace', 'title' => 'Sustainable Catalyst Workbench', 'url' => 'https://sustainablecatalyst.com/modeling-analytics/workbench/', 'summary' => 'Analytical layer for symbolic math, graphing, engineering notes, advanced calculators, article embeds, and exportable reports.', 'topics' => array( 'calculator', 'formula', 'graph', 'symbolic math', 'engineering', 'analysis' ), 'priority' => 6 ),
            array( 'id' => 'knowledge-library', 'route_id' => 'knowledge-library', 'type' => 'library', 'title' => 'Open Knowledge Library', 'url' => '/knowledge-libraries/', 'summary' => 'Article maps and research paths across sustainability, governance, infrastructure, AI, economics, risk, law, modeling, and meaning.', 'topics' => array( 'library', 'article map', 'research', 'knowledge', 'publications' ), 'priority' => 5 ),
            array( 'id' => 'methodology', 'route_id' => 'methodology', 'type' => 'methodology', 'title' => 'Platform Methodology', 'url' => '/platform/methodology/', 'summary' => 'Operating standards for traceability, assumptions, responsible AI, reproducibility, boundaries, and human review.', 'topics' => array( 'methodology', 'traceability', 'assumptions', 'responsible ai', 'review' ), 'priority' => 5 ),
        );
        foreach ( $records as &$record ) {
            $record['source_kind'] = 'seed';
            $record['status'] = 'indexed';
            $record['metadata_flags'] = array();
            $record['last_seen_utc'] = $now;
            $record['last_indexed_utc'] = $now;
        }
        unset( $record );
        return array(
            'version' => self::VERSION,
            'last_indexed_utc' => $now,
            'crawl_mode' => 'seed',
            'records' => $records,
            'failed' => array(),
            'summary' => self::static_index_summary( $records ),
        );
    }

    public static function static_index_summary( $records ) {
        $route_ids = array();
        $types = array();
        $stale = 0;
        $warnings = 0;
        $duplicates = 0;
        $seen = array();
        foreach ( is_array( $records ) ? $records : array() as $record ) {
            if ( ! empty( $record['route_id'] ) ) { $route_ids[ $record['route_id'] ] = true; }
            if ( ! empty( $record['type'] ) ) { $types[ $record['type'] ] = true; }
            if ( ! empty( $record['metadata_flags'] ) && is_array( $record['metadata_flags'] ) ) {
                $warnings += count( $record['metadata_flags'] );
                if ( in_array( 'stale', $record['metadata_flags'], true ) ) { $stale++; }
            }
            $url = isset( $record['url'] ) ? $record['url'] : '';
            if ( $url && isset( $seen[ $url ] ) ) { $duplicates++; }
            if ( $url ) { $seen[ $url ] = true; }
        }
        return array(
            'total_records' => count( is_array( $records ) ? $records : array() ),
            'route_count' => count( $route_ids ),
            'type_count' => count( $types ),
            'stale_records' => $stale,
            'metadata_warnings' => $warnings,
            'duplicate_urls' => $duplicates,
            'failed_records' => 0,
        );
    }

    private function knowledge_index() {
        $index = get_option( self::INDEX_OPTION, false );
        if ( ! is_array( $index ) || empty( $index['records'] ) ) {
            $index = self::build_default_index();
            update_option( self::INDEX_OPTION, $index, false );
        }
        return $index;
    }

    private function knowledge_index_records() {
        $index = $this->knowledge_index();
        $records = isset( $index['records'] ) && is_array( $index['records'] ) ? $index['records'] : array();
        if ( count( $records ) < count( $this->source_records() ) ) {
            $records = array_merge( $this->source_records(), $records );
        }
        return $this->dedupe_index_records( $records );
    }

    private function rebuild_knowledge_index() {
        $records = $this->build_knowledge_index_records();
        $summary = $this->knowledge_index_summary( $records );
        $index = array(
            'version' => self::VERSION,
            'last_indexed_utc' => gmdate( 'c' ),
            'crawl_mode' => 'seed-plus-wordpress-content',
            'records' => $records,
            'failed' => array(),
            'summary' => $summary,
        );
        update_option( self::INDEX_OPTION, $index, false );
        return $index;
    }

    private function build_knowledge_index_records() {
        $now = gmdate( 'c' );
        $records = array();
        foreach ( $this->source_records() as $record ) {
            $record['source_kind'] = 'seed';
            $record['status'] = 'indexed';
            $record['metadata_flags'] = $this->index_metadata_flags( $record );
            $record['last_seen_utc'] = $now;
            $record['last_indexed_utc'] = $now;
            $records[] = $record;
        }
        $records = array_merge( $records, $this->wordpress_content_index_records() );
        return $this->dedupe_index_records( $records );
    }

    private function wordpress_content_index_records() {
        if ( ! function_exists( 'get_posts' ) ) {
            return array();
        }
        $options = $this->get_options();
        $max_posts = max( 25, min( 1000, absint( isset( $options['index_max_posts'] ) ? $options['index_max_posts'] : 250 ) ) );
        $posts = get_posts( array(
            'post_type' => array( 'page', 'post' ),
            'post_status' => 'publish',
            'numberposts' => $max_posts,
            'orderby' => 'modified',
            'order' => 'DESC',
            'suppress_filters' => true,
        ) );
        $records = array();
        foreach ( $posts as $post ) {
            $url = get_permalink( $post );
            if ( ! $url ) { continue; }
            $title = get_the_title( $post );
            $content = wp_strip_all_tags( $post->post_excerpt ? $post->post_excerpt : $post->post_content );
            $summary = trim( preg_replace( '/\s+/', ' ', wp_trim_words( $content, 34, '' ) ) );
            $topics = $this->derive_topics_from_text( $title . ' ' . $summary . ' ' . $post->post_name );
            $route_id = $this->detect_route_id_from_record( $title, $url, $summary, $topics );
            $modified_utc = get_gmt_from_date( $post->post_modified, 'c' );
            $record = array(
                'id' => 'wp-' . $post->ID,
                'route_id' => $route_id,
                'type' => $post->post_type,
                'title' => $title ? $title : '(untitled)',
                'url' => $url,
                'summary' => $summary,
                'topics' => $topics,
                'priority' => 1,
                'source_kind' => 'wordpress-content',
                'status' => 'indexed',
                'last_seen_utc' => gmdate( 'c' ),
                'last_indexed_utc' => gmdate( 'c' ),
                'modified_utc' => $modified_utc,
            );
            $record['metadata_flags'] = $this->index_metadata_flags( $record );
            $records[] = $record;
        }
        return $records;
    }

    private function derive_topics_from_text( $text ) {
        $terms = $this->normalize_terms( $text );
        $topics = array_slice( $terms, 0, 10 );
        return array_values( array_unique( $topics ) );
    }

    private function detect_route_id_from_record( $title, $url, $summary, $topics ) {
        $haystack = strtolower( $title . ' ' . $url . ' ' . $summary . ' ' . implode( ' ', $topics ) );
        $best = array( 'id' => 'platform', 'score' => 0 );
        foreach ( $this->routes() as $route ) {
            $score = 0;
            if ( false !== strpos( $haystack, strtolower( trim( $route['url'], '/' ) ) ) ) { $score += 8; }
            foreach ( $route['keys'] as $key ) {
                if ( false !== strpos( $haystack, strtolower( $key ) ) ) { $score += 3; }
            }
            if ( $score > $best['score'] ) { $best = array( 'id' => $route['id'], 'score' => $score ); }
        }
        return $best['id'];
    }

    private function index_metadata_flags( $record ) {
        $flags = array();
        if ( empty( $record['summary'] ) || strlen( wp_strip_all_tags( $record['summary'] ) ) < 35 ) { $flags[] = 'missing-or-short-summary'; }
        if ( empty( $record['topics'] ) || ! is_array( $record['topics'] ) || count( $record['topics'] ) < 2 ) { $flags[] = 'missing-topics'; }
        if ( ! empty( $record['modified_utc'] ) ) {
            $options = $this->get_options();
            $days = max( 30, min( 1095, absint( isset( $options['stale_after_days'] ) ? $options['stale_after_days'] : 180 ) ) );
            $modified = strtotime( $record['modified_utc'] );
            if ( $modified && $modified < ( time() - ( $days * DAY_IN_SECONDS ) ) ) { $flags[] = 'stale'; }
        }
        return array_values( array_unique( $flags ) );
    }

    private function dedupe_index_records( $records ) {
        $deduped = array();
        $seen = array();
        foreach ( is_array( $records ) ? $records : array() as $record ) {
            if ( empty( $record['url'] ) ) { continue; }
            $key = strtolower( untrailingslashit( $record['url'] ) );
            if ( isset( $seen[ $key ] ) ) { continue; }
            $seen[ $key ] = true;
            $record['topics'] = isset( $record['topics'] ) && is_array( $record['topics'] ) ? array_values( array_unique( $record['topics'] ) ) : array();
            $deduped[] = $record;
        }
        return $deduped;
    }

    private function knowledge_index_summary( $records ) {
        $summary = self::static_index_summary( $records );
        $failed = 0;
        $index = get_option( self::INDEX_OPTION, array() );
        if ( isset( $index['failed'] ) && is_array( $index['failed'] ) ) { $failed = count( $index['failed'] ); }
        $summary['failed_records'] = $failed;
        return $summary;
    }

    private function process_admin_index_actions() {
        if ( empty( $_POST['sc_rl_index_action'] ) ) { return ''; }
        if ( ! current_user_can( 'manage_options' ) ) { return ''; }
        check_admin_referer( 'sc_rl_index_action', 'sc_rl_index_nonce' );
        $action = sanitize_key( wp_unslash( $_POST['sc_rl_index_action'] ) );
        if ( 'rebuild' === $action ) {
            $this->rebuild_knowledge_index();
            return 'rebuilt';
        }
        if ( 'reset' === $action ) {
            update_option( self::INDEX_OPTION, self::build_default_index(), false );
            return 'reset';
        }
        return '';
    }

    private function source_records() {
        return array(
            array( 'id' => 'platform', 'route_id' => 'platform', 'type' => 'architecture-page', 'title' => 'Platform', 'url' => '/platform/', 'summary' => 'Architecture page connecting Decision Studio, Workbench, modules, methodology, demos, and open development.', 'topics' => array( 'platform', 'architecture', 'decision studio', 'workbench', 'modules' ), 'priority' => 5 ),
            array( 'id' => 'demos', 'route_id' => 'demos', 'type' => 'demo-hub', 'title' => 'Platform Demos', 'url' => '/platform/demos/', 'summary' => 'Workflow demo hub for Canvas, Data, Analytics R, Global Impact, Narrative Risk, Finance, Grit, Workbench, and Decision Studio.', 'topics' => array( 'demos', 'workflow', 'modules', 'artifacts' ), 'priority' => 5 ),
            array( 'id' => 'research-librarian', 'route_id' => 'platform', 'type' => 'routing-page', 'title' => 'Research Librarian', 'url' => '/platform/research-librarian/', 'summary' => 'Site-scoped routing assistant for choosing Sustainable Catalyst pages, modules, tools, repositories, and workflows.', 'topics' => array( 'routing', 'assistant', 'research librarian', 'navigation' ), 'priority' => 4 ),
            array( 'id' => 'decision-studio', 'route_id' => 'decision-studio', 'type' => 'platform-module', 'title' => 'Sustainable Catalyst Decision Studio', 'url' => '/platform/#decision-studio', 'summary' => 'Decision Packet workspace for artifact imports, four-pillar review, scenarios, audit/provenance, readiness, handoffs, saved packets, and exportable briefs.', 'topics' => array( 'decision packet', 'brief', 'audit', 'readiness', 'scenario comparison', 'sustainability' ), 'priority' => 6 ),
            array( 'id' => 'workbench', 'route_id' => 'workbench', 'type' => 'analytical-workspace', 'title' => 'Sustainable Catalyst Workbench', 'url' => 'https://sustainablecatalyst.com/modeling-analytics/workbench/', 'summary' => 'Analytical layer for symbolic math, graphing, engineering notes, advanced calculators, article embeds, and exportable reports.', 'topics' => array( 'calculator', 'formula', 'graph', 'symbolic math', 'engineering', 'analysis' ), 'priority' => 6 ),
            array( 'id' => 'knowledge-library', 'route_id' => 'knowledge-library', 'type' => 'library', 'title' => 'Open Knowledge Library', 'url' => '/knowledge-libraries/', 'summary' => 'Article maps and research paths across sustainability, governance, infrastructure, AI, economics, risk, law, modeling, and meaning.', 'topics' => array( 'library', 'article map', 'research', 'knowledge', 'publications' ), 'priority' => 5 ),
            array( 'id' => 'methodology', 'route_id' => 'methodology', 'type' => 'methodology', 'title' => 'Platform Methodology', 'url' => '/platform/methodology/', 'summary' => 'Operating standards for traceability, assumptions, responsible AI, reproducibility, boundaries, and human review.', 'topics' => array( 'methodology', 'traceability', 'assumptions', 'responsible ai', 'review' ), 'priority' => 5 ),
            array( 'id' => 'canvas', 'route_id' => 'canvas', 'type' => 'module-demo', 'title' => 'Catalyst Canvas', 'url' => '/catalyst-canvas/#demo', 'summary' => 'Problem-framing module for audience, POV, HMW prompts, prototype direction, and test planning.', 'topics' => array( 'problem framing', 'canvas', 'prototype', 'audience', 'test plan' ), 'priority' => 4 ),
            array( 'id' => 'data', 'route_id' => 'data', 'type' => 'module-demo', 'title' => 'Catalyst Data', 'url' => '/catalyst-data/#demo', 'summary' => 'Traceable data records for entities, indicators, periods, sources, confidence, methods, and review status.', 'topics' => array( 'data', 'source', 'provenance', 'indicator', 'measurement', 'sql' ), 'priority' => 4 ),
            array( 'id' => 'analytics-r', 'route_id' => 'analytics-r', 'type' => 'module-demo', 'title' => 'Catalyst Analytics R', 'url' => '/catalyst-analytics-r/#demo', 'summary' => 'Scenario analysis and reproducible outputs for assumptions, emissions budgets, capital values, and interpretation notes.', 'topics' => array( 'analytics', 'scenario', 'r', 'emissions', 'reproducible' ), 'priority' => 4 ),
            array( 'id' => 'impact', 'route_id' => 'impact', 'type' => 'module-demo', 'title' => 'Global Impact Catalyst', 'url' => '/global-impact-catalyst/#demo', 'summary' => 'Impact records with initiative, goal, SDG-style theme, indicator, baseline, current value, target, source, and progress notes.', 'topics' => array( 'impact', 'sdg', 'indicator', 'baseline', 'target', 'progress' ), 'priority' => 4 ),
            array( 'id' => 'narrative-risk', 'route_id' => 'narrative-risk', 'type' => 'module-demo', 'title' => 'Narrative Risk', 'url' => '/narrative-risk/#demo', 'summary' => 'Claim review by evidence strength, uncertainty, source type, stakeholder pressure, narrative volatility, and consequence level.', 'topics' => array( 'claim', 'narrative risk', 'evidence', 'uncertainty', 'stakeholder', 'volatility' ), 'priority' => 4 ),
            array( 'id' => 'finance', 'route_id' => 'finance', 'type' => 'module-demo', 'title' => 'Catalyst Finance', 'url' => '/catalyst-finance/#demo', 'summary' => 'Tradeoff calculations for NPV, ROI, payback, benefit-cost ratio, carbon cost per ton, and risk-adjusted score.', 'topics' => array( 'finance', 'npv', 'roi', 'payback', 'cost', 'benefit', 'tradeoff' ), 'priority' => 4 ),
            array( 'id' => 'grit', 'route_id' => 'grit', 'type' => 'module-demo', 'title' => 'Catalyst Grit', 'url' => '/human-systems/catalyst-grit/#demo', 'summary' => 'Recovery and execution tracking for setbacks, pressure, energy, support, clarity, actions, and resilience signals.', 'topics' => array( 'grit', 'recovery', 'resilience', 'setback', 'execution', 'human systems' ), 'priority' => 4 ),
            array( 'id' => 'feature-suggestions', 'route_id' => 'feature-suggestions', 'type' => 'open-development', 'title' => 'Feature Suggestions', 'url' => '/platform/feature-suggestions/', 'summary' => 'Structured route for missing capabilities, bug reports, module ideas, Workbench calculator requests, and documentation improvements.', 'topics' => array( 'feature', 'suggestion', 'bug', 'improvement', 'missing capability' ), 'priority' => 4 ),
            array( 'id' => 'github', 'route_id' => 'platform', 'type' => 'repository-index', 'title' => 'Content Catalyst GitHub Organization', 'url' => 'https://github.com/Content-Catalyst-LLC', 'summary' => 'Open-source repositories for Sustainable Catalyst platform modules, plugins, schemas, documentation, and roadmaps.', 'topics' => array( 'github', 'repository', 'open source', 'documentation', 'code' ), 'priority' => 2 ),
        );
    }

    private function match_route( $q ) {
        foreach ( $this->routes() as $route ) {
            foreach ( $route['keys'] as $key ) {
                if ( false !== strpos( $q, $key ) ) {
                    return $route;
                }
            }
        }
        return $this->route_by_id( 'platform' );
    }

    private function route_by_id( $id ) {
        foreach ( $this->routes() as $route ) {
            if ( $id === $route['id'] ) {
                return $route;
            }
        }
        $routes = $this->routes();
        return $routes[0];
    }

    private function routes() {
        return array(
            array(
                'id' => 'decision-studio', 'category' => 'Decision support', 'title' => 'Sustainable Catalyst Decision Studio', 'url' => '/platform/#decision-studio',
                'description' => 'Decision Packet workspace for sustainability briefs, scenario comparison, artifact imports, audit/provenance, readiness review, exports, and Workbench handoffs.',
                'keys' => array( 'decision', 'brief', 'decision packet', 'scenario comparison', 'audit', 'readiness', 'tradeoff', 'sustainability decision', 'four pillar', 'four-pillar' ),
                'intent' => 'You are trying to synthesize a decision, compare options, preserve assumptions, or produce a reviewable brief.',
                'why' => 'Decision Studio is the right starting point when the output should be an auditable Decision Packet or sustainability decision brief.',
                'platform_fit' => 'It sits above the module layer and can import artifacts from Canvas, Data, Analytics R, Global Impact, Narrative Risk, Finance, Grit, and Workbench.',
                'next_step' => 'Open Decision Studio, start a packet, then import or manually add the relevant module artifacts.',
                'related' => array( 'Platform' => '/platform/', 'Demos' => '/platform/demos/', 'Methodology' => '/platform/methodology/', 'GitHub' => 'https://github.com/Content-Catalyst-LLC/sustainable-catalyst-decision-studio' ),
            ),
            array(
                'id' => 'workbench', 'category' => 'Analysis layer', 'title' => 'Sustainable Catalyst Workbench', 'url' => 'https://sustainablecatalyst.com/modeling-analytics/workbench/',
                'description' => 'Symbolic analysis, graphing, unit-aware calculation, engineering notes, article formula embeds, reports, and advanced domain calculators.',
                'keys' => array( 'workbench', 'calculate', 'calculator', 'formula', 'graph', 'visualize', 'symbolic', 'engineering', 'model', 'math', 'equation', 'astrophysics', 'econometrics', 'psychometrics' ),
                'intent' => 'You need calculation, formula review, graphing, model inspection, or a technical analytical workspace.',
                'why' => 'Workbench is the analytical layer for turning formulas, models, units, assumptions, and graphs into inspectable outputs.',
                'platform_fit' => 'Decision Studio can hand deeper calculations to Workbench; articles can embed Workbench formula calculators near equations.',
                'next_step' => 'Open Workbench and choose Chalkboard, Graph Studio, Engineering Mode, Advanced Calculators, or Article Embeds.',
                'related' => array( 'Modeling & Analytics' => '/modeling-analytics/', 'Decision Studio' => '/platform/#decision-studio', 'GitHub' => 'https://github.com/Content-Catalyst-LLC/sustainable-catalyst-workbench' ),
            ),
            array(
                'id' => 'knowledge-library', 'category' => 'Knowledge system', 'title' => 'Open Knowledge Library', 'url' => '/knowledge-libraries/',
                'description' => 'Article maps, long-form research, topic libraries, references, and structured learning paths.',
                'keys' => array( 'library', 'article', 'articles', 'research', 'learn', 'knowledge', 'publication', 'publications', 'map', 'topic' ),
                'intent' => 'You are trying to learn, explore a topic, or find Sustainable Catalyst research paths.',
                'why' => 'The Knowledge Library is the best route when the next step is orientation, reading, research, or article-map navigation.',
                'platform_fit' => 'The Library supplies the knowledge context that Workbench and Decision Studio can support with tools and workflows.',
                'next_step' => 'Open the Knowledge Library or ask the Librarian for a more specific route.',
                'related' => array( 'Publications' => '/publications/', 'Research Librarian' => '/platform/research-librarian/', 'Platform' => '/platform/' ),
            ),
            array(
                'id' => 'demos', 'category' => 'Demo hub', 'title' => 'Platform Demos', 'url' => '/platform/demos/',
                'description' => 'Demo hub for Canvas, Data, Analytics R, Global Impact, Narrative Risk, Finance, Grit, Workbench, and Decision Studio.',
                'keys' => array( 'demo', 'demos', 'try', 'example', 'prototype', 'module' ),
                'intent' => 'You want a hands-on example or a way to compare available Sustainable Catalyst modules.',
                'why' => 'The Demos page shows the full workflow and lets you choose a practical module entry point.',
                'platform_fit' => 'Demos are artifact-producing examples that can feed Decision Studio or point to Workbench for deeper analysis.',
                'next_step' => 'Open the Demo Hub and choose the module that matches the work.',
                'related' => array( 'Platform' => '/platform/', 'Decision Studio' => '/platform/#decision-studio', 'Feature Suggestions' => '/platform/feature-suggestions/' ),
            ),
            array(
                'id' => 'canvas', 'category' => 'Problem framing', 'title' => 'Catalyst Canvas', 'url' => '/catalyst-canvas/#demo',
                'description' => 'Problem framing, audience definition, POV/HMW prompts, prototype shape, test plans, and structured briefs.',
                'keys' => array( 'canvas', 'frame', 'framing', 'problem', 'audience', 'prototype', 'test plan', 'hmw', 'point of view' ),
                'intent' => 'You need to frame a problem before moving into data, analysis, or decision synthesis.',
                'why' => 'Catalyst Canvas structures the problem, audience, assumptions, prototype direction, and test logic.',
                'platform_fit' => 'Canvas artifacts can feed the framing section of a Decision Packet.',
                'next_step' => 'Try Catalyst Canvas, export or copy the framing output, then import it into Decision Studio if needed.',
                'related' => array( 'Decision Studio' => '/platform/#decision-studio', 'Demos' => '/platform/demos/', 'GitHub' => 'https://github.com/Content-Catalyst-LLC/catalyst-canvas' ),
            ),
            array(
                'id' => 'data', 'category' => 'Data records', 'title' => 'Catalyst Data', 'url' => '/catalyst-data/#demo',
                'description' => 'Traceable records for entities, indicators, sources, periods, confidence, method notes, and review status.',
                'keys' => array( 'data', 'dataset', 'record', 'source', 'evidence', 'provenance', 'measurement', 'indicator', 'sql' ),
                'intent' => 'You need to structure evidence, indicators, sources, or measurement records.',
                'why' => 'Catalyst Data provides the shared record structure for values, provenance, and review status.',
                'platform_fit' => 'Data artifacts can populate the evidence and source ledger in Decision Studio.',
                'next_step' => 'Create a Catalyst Data record before running analysis or writing a decision brief.',
                'related' => array( 'Decision Studio' => '/platform/#decision-studio', 'Analytics R' => '/catalyst-analytics-r/#demo', 'GitHub' => 'https://github.com/Content-Catalyst-LLC/catalyst-data' ),
            ),
            array(
                'id' => 'analytics-r', 'category' => 'Scenario analysis', 'title' => 'Catalyst Analytics R', 'url' => '/catalyst-analytics-r/#demo',
                'description' => 'Scenario analysis, assumptions, capital values, emissions budgets, interpretation notes, and reproducible outputs.',
                'keys' => array( 'analytics r', 'r ', 'scenario', 'statistics', 'statistical', 'trajectory', 'emissions budget', 'reproducible' ),
                'intent' => 'You need scenario analysis or reproducible analytical outputs.',
                'why' => 'Catalyst Analytics R fits scenario logic, analytical notes, and quantitative interpretation.',
                'platform_fit' => 'Analytics artifacts can feed scenario comparison and assumptions in Decision Studio.',
                'next_step' => 'Run the Analytics R demo or use Workbench if you need formula-level calculation or graphing first.',
                'related' => array( 'Workbench' => 'https://sustainablecatalyst.com/modeling-analytics/workbench/', 'Decision Studio' => '/platform/#decision-studio', 'GitHub' => 'https://github.com/Content-Catalyst-LLC/catalystanalyticsr' ),
            ),
            array(
                'id' => 'impact', 'category' => 'Impact measurement', 'title' => 'Global Impact Catalyst', 'url' => '/global-impact-catalyst/#demo',
                'description' => 'Impact records with initiative, goal, SDG-style theme, indicator, baseline, current value, target, source, and progress notes.',
                'keys' => array( 'impact', 'global impact', 'sdg', 'sustainability', 'development', 'indicator', 'target', 'baseline', 'progress' ),
                'intent' => 'You need to structure an impact record or sustainability indicator.',
                'why' => 'Global Impact Catalyst is the clearest module for educational, non-certifying impact measurement.',
                'platform_fit' => 'Impact artifacts feed the impact measurement section of a Decision Packet.',
                'next_step' => 'Create an impact record, then use Decision Studio to place it alongside claims, finance, and scenarios.',
                'related' => array( 'Decision Studio' => '/platform/#decision-studio', 'Methodology' => '/platform/methodology/', 'GitHub' => 'https://github.com/Content-Catalyst-LLC/global-impact-catalyst' ),
            ),
            array(
                'id' => 'narrative-risk', 'category' => 'Claim review', 'title' => 'Narrative Risk', 'url' => '/narrative-risk/#demo',
                'description' => 'Claim review by evidence strength, uncertainty, source type, stakeholder pressure, volatility, consequence level, and review status.',
                'keys' => array( 'narrative', 'narrative risk', 'claim', 'claims', 'trust', 'uncertainty', 'evidence strength', 'reputation', 'misinformation', 'stakeholder' ),
                'intent' => 'You need to evaluate a claim, story, uncertainty, stakeholder pressure, or communication risk.',
                'why' => 'Narrative Risk helps review how claims and evidence behave in public, institutional, and strategic contexts.',
                'platform_fit' => 'Narrative Risk artifacts feed the claim trace and risk review sections of Decision Studio.',
                'next_step' => 'Review the claim in Narrative Risk, then use Decision Studio to place it inside a full decision context.',
                'related' => array( 'Decision Studio' => '/platform/#decision-studio', 'Methodology' => '/platform/methodology/', 'GitHub' => 'https://github.com/Content-Catalyst-LLC/catalyst-narrative-risk' ),
            ),
            array(
                'id' => 'finance', 'category' => 'Tradeoff analysis', 'title' => 'Catalyst Finance', 'url' => '/catalyst-finance/#demo',
                'description' => 'NPV, ROI, payback, benefit-cost ratio, carbon cost per ton, risk-adjusted score, flags, and decision notes.',
                'keys' => array( 'finance', 'budget', 'roi', 'npv', 'payback', 'cost', 'benefit', 'carbon cost', 'economic', 'financial' ),
                'intent' => 'You need educational tradeoff, cost, benefit, ROI, or scenario finance structure.',
                'why' => 'Catalyst Finance structures financial assumptions and tradeoff calculations without providing financial advice.',
                'platform_fit' => 'Finance artifacts can feed the financial tradeoff and calculation-trace sections of Decision Studio.',
                'next_step' => 'Use Catalyst Finance for the tradeoff estimate, then review assumptions in Decision Studio.',
                'related' => array( 'Decision Studio' => '/platform/#decision-studio', 'Workbench' => 'https://sustainablecatalyst.com/modeling-analytics/workbench/', 'GitHub' => 'https://github.com/Content-Catalyst-LLC/catalyst-finance' ),
            ),
            array(
                'id' => 'grit', 'category' => 'Recovery tracking', 'title' => 'Catalyst Grit', 'url' => '/human-systems/catalyst-grit/#demo',
                'description' => 'Setbacks, pressure, impact, energy, support, clarity, recovery actions, recovery score, and next actions.',
                'keys' => array( 'grit', 'recovery', 'resilience', 'setback', 'pressure', 'energy', 'support', 'habit', 'motivation', 'human systems' ),
                'intent' => 'You need to track recovery, momentum, execution pressure, or human-systems resilience.',
                'why' => 'Catalyst Grit structures recovery signals and next actions for long-running work.',
                'platform_fit' => 'Grit artifacts can feed the execution and recovery risk section of Decision Studio.',
                'next_step' => 'Use Catalyst Grit to structure the recovery pattern, then add it to a Decision Packet if relevant.',
                'related' => array( 'Decision Studio' => '/platform/#decision-studio', 'Demos' => '/platform/demos/', 'GitHub' => 'https://github.com/Content-Catalyst-LLC/catalyst-grit' ),
            ),
            array(
                'id' => 'methodology', 'category' => 'Method', 'title' => 'Platform Methodology', 'url' => '/platform/methodology/',
                'description' => 'Operating standards for claims, evidence, assumptions, responsible AI, reproducible outputs, boundaries, and human judgment.',
                'keys' => array( 'methodology', 'method', 'standards', 'responsible ai', 'assumptions', 'boundaries', 'review', 'traceability' ),
                'intent' => 'You want to understand how the platform handles evidence, assumptions, AI, and review boundaries.',
                'why' => 'The Methodology page explains the operating logic behind Sustainable Catalyst outputs.',
                'platform_fit' => 'Methodology provides the standards that govern Research Librarian routing, Workbench outputs, and Decision Studio briefs.',
                'next_step' => 'Read the Methodology before relying on any platform output for serious research or decision support.',
                'related' => array( 'Platform' => '/platform/', 'Demos' => '/platform/demos/', 'Foundations' => '/foundations/' ),
            ),
            array(
                'id' => 'feature-suggestions', 'category' => 'Open development', 'title' => 'Feature Suggestions', 'url' => '/platform/feature-suggestions/',
                'description' => 'Structured route for missing modules, improvement ideas, bug reports, workflow requests, documentation upgrades, and repository suggestions.',
                'keys' => array( 'feature', 'suggestion', 'missing', 'does not exist', 'request', 'bug', 'improvement', 'new capability' ),
                'intent' => 'You are looking for a capability, module, or route that may not exist yet.',
                'why' => 'Feature Suggestions is the right place to capture platform improvements and missing capabilities.',
                'platform_fit' => 'Suggestions help shape future Workbench calculators, Decision Studio adapters, demos, and knowledge routes.',
                'next_step' => 'Submit the feature idea with enough context to evaluate where it belongs.',
                'related' => array( 'Platform' => '/platform/', 'Demos' => '/platform/demos/', 'GitHub Organization' => 'https://github.com/Content-Catalyst-LLC' ),
            ),
            array(
                'id' => 'platform', 'category' => 'Platform overview', 'title' => 'Platform', 'url' => '/platform/',
                'description' => 'Architecture page for Sustainable Catalyst: Decision Studio, Workbench, modules, Research Librarian, methodology, and open development.',
                'keys' => array( 'platform', 'sustainable catalyst', 'overview', 'start', 'where do i start', 'new visitor', 'orientation', 'how does it fit' ),
                'intent' => 'You are orienting yourself inside Sustainable Catalyst and need the broadest platform overview.',
                'why' => 'The Platform page shows how the Knowledge Library, Workbench, Decision Studio, demos, modules, methodology, and repositories fit together.',
                'platform_fit' => 'It is the main architecture route before choosing a specific tool or library path.',
                'next_step' => 'Open the Platform page, then choose Decision Studio, Workbench, Demos, or the Knowledge Library.',
                'related' => array( 'Knowledge Library' => '/knowledge-libraries/', 'Demos' => '/platform/demos/', 'Research Librarian' => '/platform/research-librarian/' ),
            ),
        );
    }

    public function register_admin_page() {
        add_options_page( __( 'Research Librarian', 'sustainable-catalyst-research-librarian-ai' ), __( 'Research Librarian', 'sustainable-catalyst-research-librarian-ai' ), 'manage_options', 'sc-research-librarian-ai', array( $this, 'render_admin_page' ) );
    }

    public function register_settings() {
        register_setting( 'sc_rl_ai_settings_group', self::OPTION_NAME, array( 'type' => 'array', 'sanitize_callback' => array( $this, 'sanitize_options' ), 'default' => self::defaults() ) );
        add_settings_section( 'sc_rl_ai_main', __( 'Provider and Routing Settings', 'sustainable-catalyst-research-librarian-ai' ), array( $this, 'settings_section_intro' ), 'sc-research-librarian-ai' );
        $fields = array(
            'provider' => __( 'AI Provider', 'sustainable-catalyst-research-librarian-ai' ),
            'gemini_api_key' => __( 'Gemini API Key', 'sustainable-catalyst-research-librarian-ai' ),
            'gemini_model' => __( 'Gemini Model', 'sustainable-catalyst-research-librarian-ai' ),
            'openai_api_key' => __( 'OpenAI API Key', 'sustainable-catalyst-research-librarian-ai' ),
            'openai_model' => __( 'OpenAI Model', 'sustainable-catalyst-research-librarian-ai' ),
            'openai_vector_store_id' => __( 'OpenAI Vector Store ID', 'sustainable-catalyst-research-librarian-ai' ),
            'max_file_search_results' => __( 'Max File-Search Results', 'sustainable-catalyst-research-librarian-ai' ),
            'max_output_tokens' => __( 'Max Output Tokens', 'sustainable-catalyst-research-librarian-ai' ),
            'temperature' => __( 'Temperature', 'sustainable-catalyst-research-librarian-ai' ),
            'rate_limit' => __( 'Rate Limit', 'sustainable-catalyst-research-librarian-ai' ),
            'source_result_limit' => __( 'Source Result Limit', 'sustainable-catalyst-research-librarian-ai' ),
            'index_max_posts' => __( 'Indexer Max Posts', 'sustainable-catalyst-research-librarian-ai' ),
            'stale_after_days' => __( 'Stale After Days', 'sustainable-catalyst-research-librarian-ai' ),
            'system_instructions' => __( 'System Instructions', 'sustainable-catalyst-research-librarian-ai' ),
        );
        foreach ( $fields as $field => $label ) {
            add_settings_field( 'sc_rl_ai_' . $field, $label, array( $this, 'render_field' ), 'sc-research-librarian-ai', 'sc_rl_ai_main', array( 'field' => $field ) );
        }
    }

    public function sanitize_options( $input ) {
        $old = $this->get_options();
        $input = is_array( $input ) ? $input : array();
        $provider = isset( $input['provider'] ) ? sanitize_key( wp_unslash( $input['provider'] ) ) : 'disabled';
        if ( ! in_array( $provider, array( 'disabled', 'gemini', 'openai' ), true ) ) {
            $provider = 'disabled';
        }
        return array(
            'provider'                => $provider,
            'gemini_api_key'          => $this->sanitize_secret_field( $input, 'gemini_api_key', $old['gemini_api_key'] ),
            'gemini_model'            => isset( $input['gemini_model'] ) ? sanitize_text_field( wp_unslash( $input['gemini_model'] ) ) : self::defaults()['gemini_model'],
            'openai_api_key'          => $this->sanitize_secret_field( $input, 'openai_api_key', $old['openai_api_key'] ),
            'openai_model'            => isset( $input['openai_model'] ) ? sanitize_text_field( wp_unslash( $input['openai_model'] ) ) : self::defaults()['openai_model'],
            'openai_vector_store_id'  => isset( $input['openai_vector_store_id'] ) ? sanitize_text_field( wp_unslash( $input['openai_vector_store_id'] ) ) : '',
            'max_file_search_results' => max( 1, min( 20, absint( isset( $input['max_file_search_results'] ) ? $input['max_file_search_results'] : self::defaults()['max_file_search_results'] ) ) ),
            'max_output_tokens'       => max( 150, min( 4000, absint( isset( $input['max_output_tokens'] ) ? $input['max_output_tokens'] : self::defaults()['max_output_tokens'] ) ) ),
            'temperature'             => isset( $input['temperature'] ) && is_numeric( $input['temperature'] ) ? (string) max( 0, min( 1, (float) $input['temperature'] ) ) : self::defaults()['temperature'],
            'rate_limit'              => max( 1, min( 100, absint( isset( $input['rate_limit'] ) ? $input['rate_limit'] : self::defaults()['rate_limit'] ) ) ),
            'source_result_limit'     => max( 3, min( 8, absint( isset( $input['source_result_limit'] ) ? $input['source_result_limit'] : self::defaults()['source_result_limit'] ) ) ),
            'index_max_posts'         => max( 25, min( 1000, absint( isset( $input['index_max_posts'] ) ? $input['index_max_posts'] : self::defaults()['index_max_posts'] ) ) ),
            'stale_after_days'        => max( 30, min( 1095, absint( isset( $input['stale_after_days'] ) ? $input['stale_after_days'] : self::defaults()['stale_after_days'] ) ) ),
            'system_instructions'     => isset( $input['system_instructions'] ) ? sanitize_textarea_field( wp_unslash( $input['system_instructions'] ) ) : self::default_system_instructions(),
        );
    }

    private function sanitize_secret_field( $input, $field, $old_value ) {
        $raw = isset( $input[ $field ] ) ? trim( sanitize_text_field( wp_unslash( $input[ $field ] ) ) ) : '';
        if ( '-' === $raw ) {
            return '';
        }
        if ( '' === $raw ) {
            return $old_value;
        }
        return $raw;
    }

    public function settings_section_intro() {
        echo '<p>' . esc_html__( 'The Research Librarian is site-scoped routing infrastructure. It can run entirely in deterministic fallback mode, or use Gemini/OpenAI server-side for richer route explanations. API keys are not exposed to JavaScript.', 'sustainable-catalyst-research-librarian-ai' ) . '</p>';
        echo '<p><code>[sustainable_catalyst_research_librarian_ai]</code> <code>[sc_research_librarian mode="landing"]</code> <code>[sc_research_librarian mode="route-map"]</code> <code>[sc_research_librarian mode="index-summary"]</code></p>';
    }

    public function render_field( $args ) {
        $field = $args['field'];
        $options = $this->get_options();
        $name = self::OPTION_NAME . '[' . $field . ']';
        switch ( $field ) {
            case 'provider':
                echo '<select name="' . esc_attr( $name ) . '">';
                foreach ( array( 'disabled' => 'Disabled / deterministic fallback', 'gemini' => 'Gemini', 'openai' => 'OpenAI' ) as $value => $label ) {
                    echo '<option value="' . esc_attr( $value ) . '" ' . selected( $options['provider'], $value, false ) . '>' . esc_html( $label ) . '</option>';
                }
                echo '</select>';
                break;
            case 'gemini_api_key':
            case 'openai_api_key':
                $has_key = ! empty( $options[ $field ] );
                echo '<input type="password" class="regular-text" name="' . esc_attr( $name ) . '" value="" autocomplete="off" placeholder="' . esc_attr( $has_key ? 'Key saved. Leave blank to keep it.' : 'API key' ) . '" />';
                echo '<p class="description">' . esc_html__( 'Leave blank to keep the existing key. Enter a single hyphen (-) and save to clear it.', 'sustainable-catalyst-research-librarian-ai' ) . '</p>';
                break;
            case 'system_instructions':
                echo '<textarea class="large-text code" rows="14" name="' . esc_attr( $name ) . '">' . esc_textarea( $options[ $field ] ) . '</textarea>';
                break;
            case 'max_file_search_results':
            case 'max_output_tokens':
            case 'rate_limit':
            case 'source_result_limit':
            case 'index_max_posts':
            case 'stale_after_days':
                echo '<input type="number" class="small-text" name="' . esc_attr( $name ) . '" value="' . esc_attr( $options[ $field ] ) . '" />';
                break;
            case 'temperature':
                echo '<input type="number" step="0.1" min="0" max="1" class="small-text" name="' . esc_attr( $name ) . '" value="' . esc_attr( $options[ $field ] ) . '" />';
                break;
            default:
                echo '<input type="text" class="regular-text" name="' . esc_attr( $name ) . '" value="' . esc_attr( $options[ $field ] ) . '" />';
                break;
        }
    }

    public function render_admin_page() {
        if ( ! current_user_can( 'manage_options' ) ) {
            return;
        }
        $notice = $this->process_admin_index_actions();
        $options = $this->get_options();
        $provider = $this->configured_provider( $options );
        $index = $this->knowledge_index();
        $records = $this->knowledge_index_records();
        $summary = $this->knowledge_index_summary( $records );
        ?>
        <div class="wrap">
            <h1><?php esc_html_e( 'Sustainable Catalyst Research Librarian', 'sustainable-catalyst-research-librarian-ai' ); ?></h1>
            <p><?php esc_html_e( 'Routing and retrieval infrastructure for Sustainable Catalyst. It helps visitors choose the right library, module, demo, repository, Workbench tool, or Decision Studio workflow.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
            <p><strong><?php esc_html_e( 'Status:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( 'disabled' === $provider ? 'Deterministic fallback only' : 'AI provider configured: ' . $provider ); ?> · <strong><?php esc_html_e( 'Version:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( self::VERSION ); ?></p>
            <?php if ( $notice ) : ?>
                <div class="notice notice-success is-dismissible"><p><?php echo esc_html( 'rebuilt' === $notice ? 'Knowledge index rebuilt.' : 'Knowledge index reset to seed records.' ); ?></p></div>
            <?php endif; ?>

            <h2><?php esc_html_e( 'Knowledge Indexer and Crawl Dashboard', 'sustainable-catalyst-research-librarian-ai' ); ?></h2>
            <p><?php esc_html_e( 'The indexer combines curated source records with recently published WordPress pages/posts. It tracks source coverage, metadata gaps, stale records, duplicate URLs, and route groups for grounded routing.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
            <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:16px 0;max-width:1100px;">
                <div class="postbox" style="padding:14px;"><strong style="font-size:22px;display:block;"><?php echo esc_html( $summary['total_records'] ); ?></strong><span><?php esc_html_e( 'Indexed records', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                <div class="postbox" style="padding:14px;"><strong style="font-size:22px;display:block;"><?php echo esc_html( $summary['route_count'] ); ?></strong><span><?php esc_html_e( 'Route groups', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                <div class="postbox" style="padding:14px;"><strong style="font-size:22px;display:block;"><?php echo esc_html( $summary['metadata_warnings'] ); ?></strong><span><?php esc_html_e( 'Metadata warnings', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                <div class="postbox" style="padding:14px;"><strong style="font-size:22px;display:block;"><?php echo esc_html( $summary['stale_records'] ); ?></strong><span><?php esc_html_e( 'Stale records', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
            </div>
            <p><strong><?php esc_html_e( 'Last indexed:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( isset( $index['last_indexed_utc'] ) ? $index['last_indexed_utc'] : 'seed only' ); ?> · <strong><?php esc_html_e( 'Mode:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( isset( $index['crawl_mode'] ) ? $index['crawl_mode'] : 'unknown' ); ?></p>
            <form method="post" style="display:flex;gap:10px;flex-wrap:wrap;margin:12px 0 22px;">
                <?php wp_nonce_field( 'sc_rl_index_action', 'sc_rl_index_nonce' ); ?>
                <button class="button button-primary" type="submit" name="sc_rl_index_action" value="rebuild"><?php esc_html_e( 'Rebuild Knowledge Index', 'sustainable-catalyst-research-librarian-ai' ); ?></button>
                <button class="button" type="submit" name="sc_rl_index_action" value="reset"><?php esc_html_e( 'Reset to Seed Index', 'sustainable-catalyst-research-librarian-ai' ); ?></button>
                <a class="button" href="<?php echo esc_url( rest_url( self::REST_NAMESPACE . '/index/export' ) ); ?>"><?php esc_html_e( 'Export Index JSON', 'sustainable-catalyst-research-librarian-ai' ); ?></a>
            </form>

            <form action="options.php" method="post">
                <?php settings_fields( 'sc_rl_ai_settings_group' ); do_settings_sections( 'sc-research-librarian-ai' ); submit_button(); ?>
            </form>
            <hr />
            <h2><?php esc_html_e( 'Indexed Source Records', 'sustainable-catalyst-research-librarian-ai' ); ?></h2>
            <p><?php esc_html_e( 'Records used for deterministic grounded routing and AI prompt context. Rebuild the index after major page, module, or navigation updates.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
            <table class="widefat striped"><thead><tr><th><?php esc_html_e( 'Type', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Source', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Route', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Flags', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'URL', 'sustainable-catalyst-research-librarian-ai' ); ?></th></tr></thead><tbody>
            <?php foreach ( array_slice( $records, 0, 120 ) as $source ) : ?>
                <tr><td><?php echo esc_html( $source['type'] ); ?></td><td><?php echo esc_html( $source['title'] ); ?></td><td><code><?php echo esc_html( $source['route_id'] ); ?></code></td><td><?php echo esc_html( empty( $source['metadata_flags'] ) ? 'ok' : implode( ', ', $source['metadata_flags'] ) ); ?></td><td><code><?php echo esc_html( $source['url'] ); ?></code></td></tr>
            <?php endforeach; ?>
            </tbody></table>
            <h2><?php esc_html_e( 'Route Map', 'sustainable-catalyst-research-librarian-ai' ); ?></h2>
            <table class="widefat striped"><thead><tr><th><?php esc_html_e( 'Category', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Route', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'URL', 'sustainable-catalyst-research-librarian-ai' ); ?></th></tr></thead><tbody>
            <?php foreach ( $this->routes() as $route ) : ?>
                <tr><td><?php echo esc_html( $route['category'] ); ?></td><td><?php echo esc_html( $route['title'] ); ?></td><td><code><?php echo esc_html( $route['url'] ); ?></code></td></tr>
            <?php endforeach; ?>
            </tbody></table>
        </div>
        <?php
    }
}

register_activation_hook( __FILE__, array( 'Sustainable_Catalyst_Research_Librarian_AI', 'activate' ) );
Sustainable_Catalyst_Research_Librarian_AI::instance();
