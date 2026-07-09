<?php
/**
 * Plugin Name: Sustainable Catalyst Research Librarian
 * Plugin URI: https://sustainablecatalyst.com/platform/research-librarian/
 * Description: Site-scoped routing and retrieval layer for Sustainable Catalyst with source-aware recommendations, a knowledge indexer, Gemini retrieval backend with embeddings, protected key persistence, retrieval evaluation tests, confidence tuning, failure logs, structured Workbench and Decision Studio handoff payloads, saved route sessions, admin analytics, visitor feedback, correction triage, knowledge-gap review, governance controls, privacy summaries, retention policies, admin crawl dashboard, grounded route notes, AI-assisted answers, deterministic fallback, and exports.
 * Version: 3.8.0
 * Author: Content Catalyst LLC / Tariq Ahmad
 * Author URI: https://sustainablecatalyst.com/
 * License: MIT
 * Text Domain: sustainable-catalyst-research-librarian-ai
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class Sustainable_Catalyst_Research_Librarian_AI {
    const OPTION_NAME    = 'sc_rl_ai_options';
    const INDEX_OPTION   = 'sc_rl_ai_knowledge_index';
    const EMBED_OPTION   = 'sc_rl_ai_embedding_status';
    const EVAL_OPTION    = 'sc_rl_ai_evaluation_status';
    const HANDOFF_OPTION = 'sc_rl_ai_handoff_status';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';
    const VERSION        = '3.8.0';

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
            'openai_key_fingerprint'  => '',
            'openai_model'            => 'gpt-5.5',
            'openai_vector_store_id'  => '',
            'gemini_api_key'          => '',
            'gemini_key_fingerprint'  => '',
            'gemini_model'            => 'gemini-2.5-flash',
            'embeddings_provider'     => 'disabled',
            'gemini_embedding_model'  => 'gemini-embedding-001',
            'embedding_source_limit'  => 250,
            'embedding_output_dimensionality' => 0,
            'embedding_retry_limit'   => 3,
            'embedding_batch_delay_ms' => 1200,
            'embedding_retry_after_seconds' => 5,
            'embedding_resume_existing' => '1',
            'semantic_weight'         => '0.65',
            'keyword_weight'          => '0.35',
            'max_file_search_results' => 6,
            'max_output_tokens'       => 900,
            'temperature'             => '0.2',
            'rate_limit'              => 20,
            'source_result_limit'     => 5,
            'index_max_posts'         => 250,
            'stale_after_days'        => 180,
            'eval_high_confidence_threshold' => 75,
            'eval_medium_confidence_threshold' => 45,
            'evaluation_log_limit'    => 100,
            'evaluation_min_source_count' => 1,
            'handoff_log_limit'     => 100,
            'session_log_limit'     => 200,
            'feedback_log_limit'    => 200,
            'governance_enable_public_summary' => '1',
            'governance_redact_questions_in_exports' => '0',
            'governance_session_retention_days' => 90,
            'governance_feedback_retention_days' => 180,
            'governance_evaluation_retention_days' => 180,
            'governance_handoff_retention_days' => 180,
            'governance_admin_export_requires_manage_options' => '1',
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
        if ( 'retrieval' === $mode || 'retrieval-status' === $mode ) {
            return $this->render_retrieval_status( $atts );
        }
        if ( 'evaluation' === $mode || 'evaluation-summary' === $mode ) {
            return $this->render_evaluation_summary( $atts );
        }
        if ( 'handoff' === $mode || 'handoff-summary' === $mode || 'handoffs' === $mode ) {
            return $this->render_handoff_summary( $atts );
        }
        if ( 'sessions' === $mode || 'session-summary' === $mode || 'route-sessions' === $mode ) {
            return $this->render_session_summary( $atts );
        }
        if ( 'analytics' === $mode || 'analytics-summary' === $mode || 'route-analytics' === $mode ) {
            return $this->render_analytics_summary( $atts );
        }
        if ( 'feedback' === $mode || 'feedback-summary' === $mode || 'route-feedback' === $mode || 'triage-summary' === $mode ) {
            return $this->render_feedback_summary( $atts );
        }
        if ( 'governance' === $mode || 'governance-summary' === $mode || 'privacy-summary' === $mode || 'retention-summary' === $mode ) {
            return $this->render_governance_summary( $atts );
        }
        return $this->render_assistant( $atts );
    }

    private function render_landing( $atts ) {
        ob_start();
        ?>
        <section class="sc-rl-product" data-sc-rl-product="landing">
            <p class="sc-rl-product__eyebrow">Sustainable Catalyst Platform</p>
            <h2><?php echo esc_html( $atts['title'] ); ?></h2>
            <p class="sc-rl-product__lede">The Research Librarian is the source-aware routing, indexing, and retrieval layer for Sustainable Catalyst. It helps visitors move from a question to the right library, module, demo, repository, Workbench tool, or Decision Studio workflow while showing route evidence, semantic matches, confidence, source status, and next handoff.</p>
            <div class="sc-rl-product__grid">
                <article><span>Route</span><strong>Find the right starting point</strong><p>Choose between Knowledge Library, Platform, Demos, Workbench, Decision Studio, modules, methodology, support, and feature suggestions.</p></article>
                <article><span>Connect</span><strong>Explain platform fit</strong><p>Show how Canvas, Data, Analytics R, Global Impact, Narrative Risk, Finance, Grit, Workbench, and Decision Studio connect.</p></article>
                <article><span>Ground</span><strong>Show sources and confidence</strong><p>Turn a question into a structured route note with source records, confidence, reason codes, handoffs, and boundaries.</p></article>
                <article><span>Retrieve</span><strong>Use hybrid retrieval</strong><p>Combine deterministic route rules, keyword scoring, source records, and optional Gemini embeddings for semantic source matching.</p></article>
                <article><span>Index</span><strong>Maintain source coverage</strong><p>Use the knowledge indexer to track pages, modules, stale records, missing summaries, duplicate URLs, failed crawl items, embeddings, and exportable index JSON.</p></article>
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


    private function render_retrieval_status( $atts ) {
        $status = $this->retrieval_status();
        ob_start();
        ?>
        <section class="sc-rl-index-summary sc-rl-retrieval-status" data-sc-rl-product="retrieval-status">
            <p class="sc-rl-routes__eyebrow">Gemini Retrieval Backend</p>
            <h2><?php echo esc_html( $atts['title'] ); ?></h2>
            <p>Hybrid retrieval combines route rules, keyword matching, indexed source metadata, and optional Gemini embeddings. Embeddings are generated server-side and used only to improve Sustainable Catalyst source matching.</p>
            <div class="sc-rl-index-summary__grid">
                <article><span><?php echo esc_html( $status['enabled'] ? 'Enabled' : 'Disabled' ); ?></span><strong><?php esc_html_e( 'Semantic retrieval', 'sustainable-catalyst-research-librarian-ai' ); ?></strong></article>
                <article><span><?php echo esc_html( $status['embedding_model'] ); ?></span><strong><?php esc_html_e( 'Embedding model', 'sustainable-catalyst-research-librarian-ai' ); ?></strong></article>
                <article><span><?php echo esc_html( $status['embedded_records'] ); ?></span><strong><?php esc_html_e( 'Embedded records', 'sustainable-catalyst-research-librarian-ai' ); ?></strong></article>
                <article><span><?php echo esc_html( $status['index_records'] ); ?></span><strong><?php esc_html_e( 'Index records', 'sustainable-catalyst-research-librarian-ai' ); ?></strong></article>
            </div>
            <p class="sc-rl-index-summary__meta">Last embedding run: <?php echo esc_html( $status['last_embedding_utc'] ? $status['last_embedding_utc'] : 'not yet generated' ); ?></p>
        </section>
        <?php
        return ob_get_clean();
    }


    private function render_evaluation_summary( $atts ) {
        $evaluation = $this->evaluation_summary();
        $summary = isset( $evaluation['summary'] ) && is_array( $evaluation['summary'] ) ? $evaluation['summary'] : $this->evaluation_summary_defaults();
        ob_start();
        ?>
        <section class="sc-rl-evaluation-summary" data-sc-rl-product="evaluation-summary">
            <p class="sc-rl-routes__eyebrow">Research Librarian Retrieval Evaluation</p>
            <h2><?php echo esc_html( $atts['title'] ); ?></h2>
            <p>Evaluation checks whether the Research Librarian routes standard Sustainable Catalyst questions to the expected product, module, or knowledge path. It reports route accuracy, confidence, source coverage, and weak matches.</p>
            <div class="sc-rl-index-summary__grid">
                <article><span><?php echo esc_html( absint( $summary['total_cases'] ) ); ?></span><strong>Test cases</strong></article>
                <article><span><?php echo esc_html( absint( round( (float) $summary['accuracy'] ) ) ); ?>%</span><strong>Route accuracy</strong></article>
                <article><span><?php echo esc_html( absint( $summary['low_confidence'] ) ); ?></span><strong>Low confidence</strong></article>
                <article><span><?php echo esc_html( absint( $summary['weak_source_matches'] ) ); ?></span><strong>Weak source matches</strong></article>
            </div>
            <p class="sc-rl-index-summary__meta">Last evaluation: <?php echo esc_html( ! empty( $evaluation['last_run_utc'] ) ? $evaluation['last_run_utc'] : 'not run yet' ); ?></p>
        </section>
        <?php
        return ob_get_clean();
    }


    private function render_handoff_summary( $atts ) {
        $summary = $this->handoff_summary();
        ob_start();
        ?>
        <section class="sc-rl-handoff-summary" data-sc-rl-product="handoff-summary">
            <p class="sc-rl-routes__eyebrow">Research Librarian Handoff Layer</p>
            <h2><?php echo esc_html( $atts['title'] ); ?></h2>
            <p>The handoff layer turns Research Librarian route results into structured payloads for Workbench, Decision Studio, and Sustainable Catalyst module workflows. It preserves the question, route, sources, assumptions, confidence, next action, and boundary notes so downstream tools receive usable context instead of an unstructured chat answer.</p>
            <div class="sc-rl-index-summary__grid">
                <article><span><?php echo esc_html( absint( $summary['targets'] ) ); ?></span><strong>Handoff targets</strong></article>
                <article><span><?php echo esc_html( absint( $summary['schemas'] ) ); ?></span><strong>Payload schemas</strong></article>
                <article><span><?php echo esc_html( absint( $summary['last_payload_source_count'] ) ); ?></span><strong>Last source count</strong></article>
                <article><span><?php echo esc_html( esc_html( $summary['last_target'] ) ); ?></span><strong>Last target</strong></article>
            </div>
            <p class="sc-rl-index-summary__meta">Supported targets: Workbench, Decision Studio, module artifact workflow, Feature Suggestions, and knowledge-route follow-up.</p>
        </section>
        <?php
        return ob_get_clean();
    }


    private function render_session_summary( $atts ) {
        $summary = $this->session_analytics_summary();
        ob_start();
        ?>
        <section class="sc-rl-session-summary" data-sc-rl-product="session-summary">
            <p class="sc-rl-routes__eyebrow">Research Librarian Route Sessions</p>
            <h2><?php echo esc_html( $atts['title'] ); ?></h2>
            <p>Saved route sessions preserve a visitor question, recommended route, source count, confidence, handoff target, and downstream next step so useful routing work can be reviewed without exposing API keys or confidential data.</p>
            <div class="sc-rl-index-summary__grid">
                <article><span><?php echo esc_html( absint( $summary['total_sessions'] ) ); ?></span><strong>Saved sessions</strong></article>
                <article><span><?php echo esc_html( absint( $summary['unique_routes'] ) ); ?></span><strong>Routes used</strong></article>
                <article><span><?php echo esc_html( absint( $summary['unique_targets'] ) ); ?></span><strong>Handoff targets</strong></article>
                <article><span><?php echo esc_html( $summary['last_saved_utc'] ? $summary['last_saved_utc'] : 'none' ); ?></span><strong>Last saved</strong></article>
            </div>
            <p class="sc-rl-index-summary__meta">Use the assistant's Save session action after a useful route note is generated.</p>
        </section>
        <?php
        return ob_get_clean();
    }

    private function render_analytics_summary( $atts ) {
        $summary = $this->session_analytics_summary();
        ob_start();
        ?>
        <section class="sc-rl-analytics-summary" data-sc-rl-product="analytics-summary">
            <p class="sc-rl-routes__eyebrow">Research Librarian Route Analytics</p>
            <h2><?php echo esc_html( $atts['title'] ); ?></h2>
            <p>Route analytics summarize saved sessions, common routes, handoff targets, confidence distribution, and recent routing activity. This is lightweight operational telemetry for improving the Research Librarian without turning it into a tracking product.</p>
            <div class="sc-rl-index-summary__grid">
                <article><span><?php echo esc_html( absint( $summary['total_sessions'] ) ); ?></span><strong>Total sessions</strong></article>
                <article><span><?php echo esc_html( $summary['top_route']['label'] ); ?></span><strong>Top route</strong></article>
                <article><span><?php echo esc_html( $summary['top_target']['label'] ); ?></span><strong>Top handoff</strong></article>
                <article><span><?php echo esc_html( absint( $summary['confidence_counts']['low'] ?? 0 ) ); ?></span><strong>Low-confidence saves</strong></article>
            </div>
            <p class="sc-rl-index-summary__meta">Recent saved session count: <?php echo esc_html( absint( count( $summary['recent_sessions'] ) ) ); ?>.</p>
        </section>
        <?php
        return ob_get_clean();
    }


    private function render_feedback_summary( $atts ) {
        $summary = $this->feedback_summary();
        ob_start();
        ?>
        <section class="sc-rl-feedback-summary" data-sc-rl-product="feedback-summary">
            <p class="sc-rl-routes__eyebrow">Research Librarian Feedback and Triage</p>
            <h2><?php echo esc_html( $atts['title'] ); ?></h2>
            <p>The feedback layer helps improve Research Librarian routing quality by collecting route-helpfulness signals, source-correction notes, missing-route reports, and knowledge-gap triage items without exposing API keys or turning the tool into general analytics surveillance.</p>
            <div class="sc-rl-index-summary__grid">
                <article><span><?php echo esc_html( absint( $summary['total_feedback'] ) ); ?></span><strong>Feedback records</strong></article>
                <article><span><?php echo esc_html( absint( $summary['helpful_count'] ) ); ?></span><strong>Helpful marks</strong></article>
                <article><span><?php echo esc_html( absint( $summary['issue_count'] ) ); ?></span><strong>Issues reported</strong></article>
                <article><span><?php echo esc_html( absint( $summary['knowledge_gap_count'] ) ); ?></span><strong>Knowledge gaps</strong></article>
            </div>
            <p class="sc-rl-index-summary__meta">Last feedback: <?php echo esc_html( $summary['last_feedback_utc'] ? $summary['last_feedback_utc'] : 'none' ); ?>.</p>
        </section>
        <?php
        return ob_get_clean();
    }


    private function render_governance_summary( $atts ) {
        $summary = $this->governance_summary();
        ob_start();
        ?>
        <section class="sc-rl-governance-summary" data-sc-rl-product="governance-summary">
            <p class="sc-rl-routes__eyebrow">Research Librarian Governance</p>
            <h2><?php echo esc_html( $atts['title'] ); ?></h2>
            <p>The governance layer summarizes privacy posture, retention policy, export controls, public endpoint boundaries, and operational logs used by the Research Librarian. It is intended to keep routing infrastructure inspectable without exposing API keys or turning route analytics into user surveillance.</p>
            <div class="sc-rl-index-summary__grid">
                <article><span><?php echo esc_html( absint( $summary['logs']['sessions'] ) ); ?></span><strong>Saved sessions</strong></article>
                <article><span><?php echo esc_html( absint( $summary['logs']['feedback'] ) ); ?></span><strong>Feedback records</strong></article>
                <article><span><?php echo esc_html( absint( $summary['logs']['handoffs'] ) ); ?></span><strong>Handoff records</strong></article>
                <article><span><?php echo esc_html( $summary['public_summary_enabled'] ? 'on' : 'off' ); ?></span><strong>Public summary</strong></article>
            </div>
            <p class="sc-rl-index-summary__meta">Retention targets: sessions <?php echo esc_html( absint( $summary['retention_days']['sessions'] ) ); ?> days, feedback <?php echo esc_html( absint( $summary['retention_days']['feedback'] ) ); ?> days, evaluation <?php echo esc_html( absint( $summary['retention_days']['evaluation'] ) ); ?> days, handoffs <?php echo esc_html( absint( $summary['retention_days']['handoffs'] ) ); ?> days.</p>
        </section>
        <?php
        return ob_get_clean();
    }

    private function render_assistant( $atts ) {
        $root_id = wp_unique_id( 'sc-rl-ai-' );
        $endpoint = rest_url( self::REST_NAMESPACE . '/ask' );
        $routes_endpoint = rest_url( self::REST_NAMESPACE . '/routes' );
        $note_endpoint = rest_url( self::REST_NAMESPACE . '/route-note' );
        $handoff_endpoint = rest_url( self::REST_NAMESPACE . '/handoff/prepare' );
        $session_endpoint = rest_url( self::REST_NAMESPACE . '/session/save' );
        $feedback_endpoint = rest_url( self::REST_NAMESPACE . '/feedback/submit' );
        $nonce = wp_create_nonce( 'wp_rest' );
        $compact = ( 'compact' === sanitize_key( $atts['display'] ) || 'compact' === sanitize_key( $atts['mode'] ) );

        ob_start();
        ?>
        <section id="<?php echo esc_attr( $root_id ); ?>" class="sc-rl-ai<?php echo $compact ? ' sc-rl-ai--compact' : ''; ?>" data-endpoint="<?php echo esc_url( $endpoint ); ?>" data-routes-endpoint="<?php echo esc_url( $routes_endpoint ); ?>" data-note-endpoint="<?php echo esc_url( $note_endpoint ); ?>" data-handoff-endpoint="<?php echo esc_url( $handoff_endpoint ); ?>" data-session-endpoint="<?php echo esc_url( $session_endpoint ); ?>" data-feedback-endpoint="<?php echo esc_url( $feedback_endpoint ); ?>" data-nonce="<?php echo esc_attr( $nonce ); ?>">
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
                        <button type="button" class="sc-rl-ai__button sc-rl-ai__button--secondary" data-sc-rl-handoff-download>Download handoff</button>
                        <button type="button" class="sc-rl-ai__button sc-rl-ai__button--secondary" data-sc-rl-save-session>Save session</button>
                        <button type="button" class="sc-rl-ai__button sc-rl-ai__button--secondary" data-sc-rl-feedback-helpful>This helped</button>
                        <button type="button" class="sc-rl-ai__button sc-rl-ai__button--secondary" data-sc-rl-feedback-issue>Report issue</button>
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
                        <p>Ask a question or choose an example. The librarian will recommend a route, explain why it fits, show related links, and produce an exportable route note with a Workbench or Decision Studio handoff payload when relevant.</p>
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


        register_rest_route( self::REST_NAMESPACE, '/retrieval/status', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_retrieval_status_request' ),
            'permission_callback' => '__return_true',
        ) );

        register_rest_route( self::REST_NAMESPACE, '/retrieval/diagnostics', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_retrieval_diagnostics_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );

        register_rest_route( self::REST_NAMESPACE, '/retrieval/test-embedding', array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => array( $this, 'handle_embedding_test_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );

        register_rest_route( self::REST_NAMESPACE, '/retrieval/query', array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => array( $this, 'handle_retrieval_query_request' ),
            'permission_callback' => '__return_true',
        ) );

        register_rest_route( self::REST_NAMESPACE, '/index/embed', array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => array( $this, 'handle_index_embed_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );


        register_rest_route( self::REST_NAMESPACE, '/evaluation/suite', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_evaluation_suite_request' ),
            'permission_callback' => '__return_true',
        ) );

        register_rest_route( self::REST_NAMESPACE, '/evaluation/run', array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => array( $this, 'handle_evaluation_run_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );

        register_rest_route( self::REST_NAMESPACE, '/evaluation/query', array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => array( $this, 'handle_evaluation_query_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );

        register_rest_route( self::REST_NAMESPACE, '/evaluation/logs', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_evaluation_logs_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );

        register_rest_route( self::REST_NAMESPACE, '/evaluation/export', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_evaluation_export_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );


        register_rest_route( self::REST_NAMESPACE, '/handoff/schema', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_handoff_schema_request' ),
            'permission_callback' => '__return_true',
        ) );

        register_rest_route( self::REST_NAMESPACE, '/handoff/prepare', array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => array( $this, 'handle_handoff_prepare_request' ),
            'permission_callback' => '__return_true',
        ) );

        register_rest_route( self::REST_NAMESPACE, '/handoff/logs', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_handoff_logs_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );

        register_rest_route( self::REST_NAMESPACE, '/handoff/export', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_handoff_export_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );


        register_rest_route( self::REST_NAMESPACE, '/session/save', array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => array( $this, 'handle_session_save_request' ),
            'permission_callback' => '__return_true',
        ) );

        register_rest_route( self::REST_NAMESPACE, '/session/logs', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_session_logs_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );

        register_rest_route( self::REST_NAMESPACE, '/session/export', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_session_export_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );

        register_rest_route( self::REST_NAMESPACE, '/analytics/summary', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_analytics_summary_request' ),
            'permission_callback' => '__return_true',
        ) );


        register_rest_route( self::REST_NAMESPACE, '/feedback/submit', array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => array( $this, 'handle_feedback_submit_request' ),
            'permission_callback' => '__return_true',
        ) );

        register_rest_route( self::REST_NAMESPACE, '/feedback/summary', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_feedback_summary_request' ),
            'permission_callback' => '__return_true',
        ) );

        register_rest_route( self::REST_NAMESPACE, '/feedback/logs', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_feedback_logs_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );

        register_rest_route( self::REST_NAMESPACE, '/feedback/export', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_feedback_export_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );

        register_rest_route( self::REST_NAMESPACE, '/governance/status', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_governance_status_request' ),
            'permission_callback' => '__return_true',
        ) );

        register_rest_route( self::REST_NAMESPACE, '/governance/export', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'handle_governance_export_request' ),
            'permission_callback' => array( $this, 'can_manage_options' ),
        ) );

        register_rest_route( self::REST_NAMESPACE, '/governance/purge-expired', array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => array( $this, 'handle_governance_purge_expired_request' ),
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
            'retrieval' => $this->retrieval_status(),
            'evaluation' => $this->evaluation_summary(),
            'handoff' => $this->handoff_summary(),
            'feedback' => $this->feedback_summary(),
            'governance' => $this->governance_summary(),
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


    public function handle_retrieval_status_request() {
        return new WP_REST_Response( array( 'version' => self::VERSION, 'retrieval' => $this->retrieval_status() ), 200 );
    }

    public function handle_retrieval_diagnostics_request() {
        return new WP_REST_Response( array( 'version' => self::VERSION, 'diagnostics' => $this->embedding_diagnostics() ), 200 );
    }

    public function handle_embedding_test_request( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_ai_bad_nonce', __( 'Security check failed. Refresh the page and try again.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 403 ) );
        }
        $result = $this->test_single_embedding();
        if ( is_wp_error( $result ) ) {
            return $result;
        }
        return new WP_REST_Response( $result, 200 );
    }

    public function handle_retrieval_query_request( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_ai_bad_nonce', __( 'Security check failed. Refresh the page and try again.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 403 ) );
        }
        $params = $request->get_json_params();
        $query = isset( $params['query'] ) ? sanitize_textarea_field( wp_unslash( $params['query'] ) ) : '';
        if ( '' === trim( $query ) ) {
            return new WP_Error( 'sc_rl_ai_empty_query', __( 'Please enter a retrieval query.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 400 ) );
        }
        $route = $this->match_route( strtolower( $query ) );
        $matches = $this->match_sources( $query, $route );
        return new WP_REST_Response( array( 'version' => self::VERSION, 'query' => $query, 'route' => $route, 'matches' => $matches, 'retrieval' => $this->retrieval_status() ), 200 );
    }


    public function handle_evaluation_suite_request() {
        return new WP_REST_Response( array( 'version' => self::VERSION, 'suite' => $this->evaluation_suite(), 'summary' => $this->evaluation_summary() ), 200 );
    }

    public function handle_evaluation_run_request( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_ai_bad_nonce', __( 'Security check failed. Refresh the page and try again.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 403 ) );
        }
        $params = $request->get_json_params();
        $cases = array();
        if ( isset( $params['cases'] ) && is_array( $params['cases'] ) ) {
            $cases = $params['cases'];
        }
        $result = $this->run_retrieval_evaluation( $cases, true );
        return new WP_REST_Response( $result, 200 );
    }

    public function handle_evaluation_query_request( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_ai_bad_nonce', __( 'Security check failed. Refresh the page and try again.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 403 ) );
        }
        $params = $request->get_json_params();
        $prompt = isset( $params['query'] ) ? sanitize_textarea_field( wp_unslash( $params['query'] ) ) : '';
        if ( '' === trim( $prompt ) ) {
            return new WP_Error( 'sc_rl_ai_empty_query', __( 'Please enter a retrieval evaluation query.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 400 ) );
        }
        $expected = array();
        if ( ! empty( $params['expected_route'] ) ) {
            $expected[] = sanitize_key( wp_unslash( $params['expected_route'] ) );
        }
        if ( isset( $params['expected_routes'] ) && is_array( $params['expected_routes'] ) ) {
            foreach ( $params['expected_routes'] as $route_id ) { $expected[] = sanitize_key( wp_unslash( $route_id ) ); }
        }
        return new WP_REST_Response( array( 'version' => self::VERSION, 'result' => $this->evaluate_retrieval_query( $prompt, $expected, 'manual' ) ), 200 );
    }

    public function handle_evaluation_logs_request() {
        return new WP_REST_Response( array( 'version' => self::VERSION, 'evaluation' => $this->evaluation_summary(), 'logs' => $this->evaluation_logs() ), 200 );
    }

    public function handle_evaluation_export_request() {
        return new WP_REST_Response( array( 'version' => self::VERSION, 'evaluation' => $this->evaluation_summary(), 'logs' => $this->evaluation_logs(), 'suite' => $this->evaluation_suite(), 'retrieval' => $this->retrieval_status(), 'index' => $this->knowledge_index_summary( $this->knowledge_index_records() ) ), 200 );
    }

    public function handle_index_embed_request( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_ai_bad_nonce', __( 'Security check failed. Refresh the page and try again.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 403 ) );
        }
        $result = $this->generate_index_embeddings();
        if ( is_wp_error( $result ) ) {
            return $result;
        }
        return new WP_REST_Response( $result, 200 );
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
        $source_lines = array();
        if ( ! empty( $grounding['sources'] ) && is_array( $grounding['sources'] ) ) {
            foreach ( $grounding['sources'] as $source ) {
                $source_lines[] = '- ' . $source['title'] . ': ' . $source['url'] . ' — ' . $source['summary'] . ( isset( $source['score'] ) ? ' [score ' . $source['score'] . ']' : '' );
            }
        }
        $handoff_lines = array();
        if ( ! empty( $grounding['handoffs'] ) && is_array( $grounding['handoffs'] ) ) {
            foreach ( $grounding['handoffs'] as $handoff ) {
                $handoff_lines[] = '- ' . $handoff['label'] . ': ' . $handoff['url'] . ' — ' . $handoff['reason'];
            }
        }
        $instructions = ( $admin ? $admin : self::default_system_instructions() ) . "\n\nCurrent route map:\n" . implode( "\n", $route_lines );
        if ( ! empty( $source_lines ) ) {
            $instructions .= "\n\nMatched Sustainable Catalyst source records for this query:\n" . implode( "\n", $source_lines );
        }
        if ( ! empty( $handoff_lines ) ) {
            $instructions .= "\n\nSuggested handoffs:\n" . implode( "\n", $handoff_lines );
        }
        if ( ! empty( $grounding['confidence']['level'] ) ) {
            $instructions .= "\n\nRoute confidence: " . $grounding['confidence']['level'] . " — " . $grounding['confidence']['explanation'];
        }
        return $instructions;
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
            'handoff_payload' => $this->build_handoff_payload( $question, $route, $source, $grounding ),
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
        $options = $this->get_options();
        $records = $this->knowledge_index_records();
        $terms = $this->normalize_terms( $question . ' ' . $route['title'] . ' ' . $route['category'] );
        $query_embedding = null;
        $semantic_enabled = $this->semantic_retrieval_enabled( $options );
        if ( $semantic_enabled ) {
            $embedding_result = $this->get_query_embedding( $question, $options );
            if ( ! is_wp_error( $embedding_result ) && is_array( $embedding_result ) ) {
                $query_embedding = $embedding_result;
            }
        }
        $scored = array();
        foreach ( $records as $record ) {
            $keyword_score = $this->keyword_source_score( $record, $route, $terms );
            $semantic_score = 0.0;
            if ( is_array( $query_embedding ) && ! empty( $record['embedding'] ) && is_array( $record['embedding'] ) ) {
                $semantic_score = $this->cosine_similarity( $query_embedding, $record['embedding'] );
            }
            $priority = ! empty( $record['priority'] ) ? (int) $record['priority'] : 0;
            $keyword_weight = isset( $options['keyword_weight'] ) && is_numeric( $options['keyword_weight'] ) ? (float) $options['keyword_weight'] : 0.35;
            $semantic_weight = isset( $options['semantic_weight'] ) && is_numeric( $options['semantic_weight'] ) ? (float) $options['semantic_weight'] : 0.65;
            $hybrid_score = ( $keyword_score * $keyword_weight ) + ( $semantic_score * 100 * $semantic_weight ) + $priority;
            if ( $keyword_score > 0 || $semantic_score > 0.08 || ( isset( $record['route_id'] ) && $record['route_id'] === $route['id'] ) ) {
                $record['keyword_score'] = round( $keyword_score, 3 );
                $record['semantic_score'] = round( $semantic_score, 4 );
                $record['score'] = round( $hybrid_score, 3 );
                $record['retrieval_mode'] = is_array( $query_embedding ) && ! empty( $record['embedding'] ) ? 'hybrid-gemini-embedding' : 'keyword-source';
                $scored[] = $record;
            }
        }
        usort( $scored, function( $a, $b ) { return $b['score'] <=> $a['score']; } );
        $limit = max( 3, min( 8, absint( isset( $options['source_result_limit'] ) ? $options['source_result_limit'] : 5 ) ) );
        return array_slice( $scored, 0, $limit );
    }

    private function keyword_source_score( $record, $route, $terms ) {
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
        return $score;
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
        $options = $this->get_options();
        $high_threshold = max( 50, min( 95, absint( $options['eval_high_confidence_threshold'] ?? 75 ) ) );
        $medium_threshold = max( 20, min( $high_threshold - 1, absint( $options['eval_medium_confidence_threshold'] ?? 45 ) ) );
        if ( $score >= $high_threshold ) {
            $level = 'high';
        } elseif ( $score >= $medium_threshold ) {
            $level = 'medium';
        }
        $semantic_hits = 0;
        foreach ( $sources as $source ) {
            if ( ! empty( $source['semantic_score'] ) && (float) $source['semantic_score'] > 0.1 ) { $semantic_hits++; }
        }
        $explanation = 'Matched ' . count( $sources ) . ' source record(s), ' . $keyword_hits . ' route keyword signal(s), and ' . $semantic_hits . ' semantic source signal(s).';
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


    public function handle_handoff_schema_request() {
        return new WP_REST_Response( array( 'version' => self::VERSION, 'schema' => $this->handoff_schema(), 'summary' => $this->handoff_summary() ), 200 );
    }

    public function handle_handoff_prepare_request( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_ai_bad_nonce', __( 'Security check failed. Refresh the page and try again.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 403 ) );
        }
        $params = $request->get_json_params();
        $question = isset( $params['question'] ) ? sanitize_textarea_field( wp_unslash( $params['question'] ) ) : '';
        if ( '' === trim( $question ) ) {
            return new WP_Error( 'sc_rl_ai_empty_question', __( 'Please enter a question before preparing a handoff.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 400 ) );
        }
        $route = $this->match_route( strtolower( $question ) );
        $grounding = $this->grounding_context( $question, $route );
        $payload = $this->build_handoff_payload( $question, $route, 'handoff-prepare', $grounding );
        $this->append_handoff_log( $payload );
        return new WP_REST_Response( array( 'version' => self::VERSION, 'handoff_payload' => $payload, 'route' => $route, 'grounding' => $grounding ), 200 );
    }

    public function handle_handoff_logs_request() {
        return new WP_REST_Response( array( 'version' => self::VERSION, 'summary' => $this->handoff_summary(), 'logs' => $this->handoff_logs() ), 200 );
    }

    public function handle_handoff_export_request() {
        return new WP_REST_Response( array( 'version' => self::VERSION, 'summary' => $this->handoff_summary(), 'schema' => $this->handoff_schema(), 'logs' => $this->handoff_logs() ), 200 );
    }


    public function handle_session_save_request( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_ai_bad_nonce', __( 'Security check failed. Refresh the page and try again.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 403 ) );
        }
        $params = $request->get_json_params();
        $note = isset( $params['route_note'] ) && is_array( $params['route_note'] ) ? $this->sanitize_deep( $params['route_note'] ) : array();
        if ( empty( $note ) ) {
            $question = isset( $params['question'] ) ? sanitize_textarea_field( wp_unslash( $params['question'] ) ) : '';
            if ( '' === trim( $question ) ) {
                return new WP_Error( 'sc_rl_ai_empty_session', __( 'Please generate a route note before saving a session.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 400 ) );
            }
            $route = $this->match_route( strtolower( $question ) );
            $grounding = $this->grounding_context( $question, $route );
            $note = $this->build_route_note( $question, $route, 'session-save', $grounding );
        }
        $session = $this->build_saved_session_record( $note );
        $this->append_session_log( $session );
        return new WP_REST_Response( array( 'version' => self::VERSION, 'saved' => true, 'session' => $session, 'analytics' => $this->session_analytics_summary() ), 200 );
    }

    public function handle_session_logs_request() {
        return new WP_REST_Response( array( 'version' => self::VERSION, 'summary' => $this->session_analytics_summary(), 'logs' => $this->session_logs() ), 200 );
    }

    public function handle_session_export_request() {
        return new WP_REST_Response( array( 'version' => self::VERSION, 'summary' => $this->session_analytics_summary(), 'logs' => $this->session_logs(), 'handoffs' => $this->handoff_logs(), 'evaluation' => $this->evaluation_summary() ), 200 );
    }

    public function handle_analytics_summary_request() {
        return new WP_REST_Response( array( 'version' => self::VERSION, 'analytics' => $this->session_analytics_summary(), 'retrieval' => $this->retrieval_status(), 'index' => $this->knowledge_index_summary( $this->knowledge_index_records() ) ), 200 );
    }


    public function handle_governance_status_request() {
        $options = $this->get_options();
        if ( empty( $options['governance_enable_public_summary'] ) || '1' !== (string) $options['governance_enable_public_summary'] ) {
            return new WP_REST_Response( array( 'version' => self::VERSION, 'public_summary_enabled' => false ), 200 );
        }
        return new WP_REST_Response( array( 'version' => self::VERSION, 'governance' => $this->governance_public_summary() ), 200 );
    }

    public function handle_governance_export_request() {
        return new WP_REST_Response( array(
            'version' => self::VERSION,
            'governance' => $this->governance_summary(),
            'options' => $this->governance_option_summary(),
            'retrieval' => $this->retrieval_status(),
            'index' => $this->knowledge_index_summary( $this->knowledge_index_records() ),
            'sessions' => $this->governance_export_logs( $this->session_logs(), 'session' ),
            'feedback' => $this->governance_export_logs( $this->feedback_logs(), 'feedback' ),
            'handoffs' => $this->governance_export_logs( $this->handoff_logs(), 'handoff' ),
            'evaluation' => $this->evaluation_summary(),
        ), 200 );
    }

    public function handle_governance_purge_expired_request() {
        $result = $this->purge_expired_governance_logs();
        return new WP_REST_Response( array( 'version' => self::VERSION, 'purged' => true, 'result' => $result, 'governance' => $this->governance_summary() ), 200 );
    }

    private function governance_public_summary() {
        $summary = $this->governance_summary();
        return array(
            'public_summary_enabled' => $summary['public_summary_enabled'],
            'retention_days' => $summary['retention_days'],
            'logs' => $summary['logs'],
            'privacy_posture' => $summary['privacy_posture'],
            'export_controls' => $summary['export_controls'],
            'last_purge_utc' => $summary['last_purge_utc'],
        );
    }

    private function governance_summary() {
        $options = $this->get_options();
        $status = get_option( 'sc_rl_ai_governance_status', array() );
        return array(
            'public_summary_enabled' => ! empty( $options['governance_enable_public_summary'] ) && '1' === (string) $options['governance_enable_public_summary'],
            'redact_questions_in_exports' => ! empty( $options['governance_redact_questions_in_exports'] ) && '1' === (string) $options['governance_redact_questions_in_exports'],
            'retention_days' => array(
                'sessions' => max( 1, absint( $options['governance_session_retention_days'] ?? 90 ) ),
                'feedback' => max( 1, absint( $options['governance_feedback_retention_days'] ?? 180 ) ),
                'evaluation' => max( 1, absint( $options['governance_evaluation_retention_days'] ?? 180 ) ),
                'handoffs' => max( 1, absint( $options['governance_handoff_retention_days'] ?? 180 ) ),
            ),
            'logs' => array(
                'sessions' => count( $this->session_logs() ),
                'feedback' => count( $this->feedback_logs() ),
                'handoffs' => count( $this->handoff_logs() ),
                'evaluation_failures' => absint( $this->evaluation_summary()['fail_count'] ?? 0 ),
            ),
            'privacy_posture' => array(
                'api_keys_exposed_publicly' => false,
                'admin_exports_require_manage_options' => true,
                'public_endpoints_include_raw_api_keys' => false,
                'semantic_embeddings_store_numeric_vectors_only' => true,
                'professional_advice_boundary' => true,
            ),
            'export_controls' => array(
                'index_export_admin_only' => true,
                'retrieval_diagnostics_admin_only' => true,
                'session_export_admin_only' => true,
                'feedback_export_admin_only' => true,
                'governance_export_admin_only' => true,
            ),
            'last_purge_utc' => ! empty( $status['last_purge_utc'] ) ? $status['last_purge_utc'] : '',
            'last_purge_result' => ! empty( $status['last_purge_result'] ) ? $status['last_purge_result'] : array(),
        );
    }

    private function governance_option_summary() {
        $options = $this->get_options();
        return array(
            'provider' => $this->configured_provider( $options ),
            'embeddings_provider' => sanitize_key( $options['embeddings_provider'] ?? 'disabled' ),
            'gemini_key_fingerprint' => $this->key_fingerprint( $options['gemini_api_key'] ?? '' ),
            'openai_key_fingerprint' => $this->key_fingerprint( $options['openai_api_key'] ?? '' ),
            'semantic_weight' => sanitize_text_field( $options['semantic_weight'] ?? '0.65' ),
            'keyword_weight' => sanitize_text_field( $options['keyword_weight'] ?? '0.35' ),
        );
    }

    private function governance_export_logs( $logs, $kind ) {
        $options = $this->get_options();
        $redact = ! empty( $options['governance_redact_questions_in_exports'] ) && '1' === (string) $options['governance_redact_questions_in_exports'];
        if ( ! is_array( $logs ) ) {
            return array();
        }
        if ( ! $redact ) {
            return $logs;
        }
        $out = array();
        foreach ( $logs as $log ) {
            if ( is_array( $log ) ) {
                if ( isset( $log['question'] ) ) {
                    $log['question'] = '[redacted by governance export policy]';
                }
                if ( isset( $log['note'] ) ) {
                    $log['note'] = '[redacted by governance export policy]';
                }
                if ( isset( $log['route_note']['question'] ) ) {
                    $log['route_note']['question'] = '[redacted by governance export policy]';
                }
            }
            $out[] = $log;
        }
        return $out;
    }

    private function purge_expired_governance_logs() {
        $options = $this->get_options();
        $result = array();
        $session_days = max( 1, absint( $options['governance_session_retention_days'] ?? 90 ) );
        $feedback_days = max( 1, absint( $options['governance_feedback_retention_days'] ?? 180 ) );
        $handoff_days = max( 1, absint( $options['governance_handoff_retention_days'] ?? 180 ) );
        $sessions = $this->filter_logs_by_retention_days( $this->session_logs(), $session_days );
        $feedback = $this->filter_logs_by_retention_days( $this->feedback_logs(), $feedback_days );
        $handoffs = $this->filter_logs_by_retention_days( $this->handoff_logs(), $handoff_days );
        $result['sessions_kept'] = count( $sessions );
        $result['feedback_kept'] = count( $feedback );
        $result['handoffs_kept'] = count( $handoffs );
        update_option( 'sc_rl_ai_session_log', $sessions, false );
        update_option( 'sc_rl_ai_feedback_log', $feedback, false );
        update_option( 'sc_rl_ai_handoff_log', $handoffs, false );
        update_option( 'sc_rl_ai_governance_status', array( 'last_purge_utc' => gmdate( 'c' ), 'last_purge_result' => $result ), false );
        return $result;
    }

    private function filter_logs_by_retention_days( $logs, $days ) {
        if ( ! is_array( $logs ) || empty( $logs ) ) {
            return array();
        }
        $cutoff = time() - ( absint( $days ) * DAY_IN_SECONDS );
        $kept = array();
        foreach ( $logs as $log ) {
            $created = '';
            if ( is_array( $log ) ) {
                $created = $log['created_at_utc'] ?? ( $log['saved_at_utc'] ?? ( $log['timestamp'] ?? '' ) );
            }
            if ( ! $created ) {
                $kept[] = $log;
                continue;
            }
            $ts = strtotime( $created );
            if ( false === $ts || $ts >= $cutoff ) {
                $kept[] = $log;
            }
        }
        return $kept;
    }


    public function handle_feedback_submit_request( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( $nonce && ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_ai_bad_nonce', __( 'Security check failed. Refresh the page and try again.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 403 ) );
        }
        $params = $request->get_json_params();
        if ( ! is_array( $params ) ) {
            $params = array();
        }
        $feedback = $this->build_feedback_record( $params );
        $this->append_feedback_log( $feedback );
        return new WP_REST_Response( array( 'version' => self::VERSION, 'saved' => true, 'feedback' => $feedback, 'summary' => $this->feedback_summary() ), 200 );
    }

    public function handle_feedback_summary_request() {
        return new WP_REST_Response( array( 'version' => self::VERSION, 'summary' => $this->feedback_summary() ), 200 );
    }

    public function handle_feedback_logs_request() {
        return new WP_REST_Response( array( 'version' => self::VERSION, 'summary' => $this->feedback_summary(), 'logs' => $this->feedback_logs() ), 200 );
    }

    public function handle_feedback_export_request() {
        return new WP_REST_Response( array( 'version' => self::VERSION, 'summary' => $this->feedback_summary(), 'logs' => $this->feedback_logs(), 'sessions' => $this->session_logs(), 'evaluation' => $this->evaluation_summary(), 'retrieval' => $this->retrieval_status() ), 200 );
    }

    private function build_feedback_record( $params ) {
        $route_note = isset( $params['route_note'] ) && is_array( $params['route_note'] ) ? $this->sanitize_deep( $params['route_note'] ) : array();
        $type = isset( $params['type'] ) ? sanitize_key( wp_unslash( $params['type'] ) ) : 'issue';
        $allowed_types = array( 'helpful', 'issue', 'wrong_route', 'missing_source', 'knowledge_gap', 'unclear', 'feature_gap' );
        if ( ! in_array( $type, $allowed_types, true ) ) {
            $type = 'issue';
        }
        $note = isset( $params['note'] ) ? sanitize_textarea_field( wp_unslash( $params['note'] ) ) : '';
        $question = '';
        if ( ! empty( $route_note['question'] ) ) {
            $question = sanitize_textarea_field( $route_note['question'] );
        } elseif ( ! empty( $params['question'] ) ) {
            $question = sanitize_textarea_field( wp_unslash( $params['question'] ) );
        }
        $route_id = 'unknown';
        if ( ! empty( $route_note['recommended_route']['id'] ) ) {
            $route_id = sanitize_key( $route_note['recommended_route']['id'] );
        } elseif ( ! empty( $params['route_id'] ) ) {
            $route_id = sanitize_key( wp_unslash( $params['route_id'] ) );
        }
        $handoff_target = 'none';
        if ( ! empty( $route_note['handoff_payload']['target'] ) ) {
            $handoff_target = sanitize_key( $route_note['handoff_payload']['target'] );
        }
        $confidence_level = ! empty( $route_note['confidence']['level'] ) ? sanitize_key( $route_note['confidence']['level'] ) : 'unknown';
        $confidence_score = ! empty( $route_note['confidence']['score'] ) ? absint( $route_note['confidence']['score'] ) : 0;
        $source_count = ! empty( $route_note['sources'] ) && is_array( $route_note['sources'] ) ? count( $route_note['sources'] ) : 0;
        $triage = $this->feedback_triage_label( $type, $route_id, $confidence_level, $source_count );
        return array(
            'feedback_id' => 'sc-rl-feedback-' . gmdate( 'YmdHis' ) . '-' . substr( md5( wp_json_encode( array( $type, $question, $route_id, $note ) ) ), 0, 8 ),
            'created_at_utc' => gmdate( 'c' ),
            'type' => $type,
            'triage_label' => $triage,
            'status' => 'new',
            'question' => wp_trim_words( $question, 80, '' ),
            'route_id' => $route_id,
            'handoff_target' => $handoff_target,
            'confidence_level' => $confidence_level,
            'confidence_score' => $confidence_score,
            'source_count' => $source_count,
            'note' => wp_trim_words( $note, 80, '' ),
            'route_note_id' => ! empty( $route_note['note_id'] ) ? sanitize_text_field( $route_note['note_id'] ) : '',
            'user_agent_hash' => ! empty( $_SERVER['HTTP_USER_AGENT'] ) ? substr( hash( 'sha256', sanitize_text_field( wp_unslash( $_SERVER['HTTP_USER_AGENT'] ) ) ), 0, 12 ) : '',
        );
    }

    private function feedback_triage_label( $type, $route_id, $confidence_level, $source_count ) {
        if ( 'helpful' === $type ) {
            return 'positive-signal';
        }
        if ( 'knowledge_gap' === $type || 'missing_source' === $type || 'feature_gap' === $type ) {
            return 'knowledge-gap-triage';
        }
        if ( 'wrong_route' === $type || 'unknown' === $route_id ) {
            return 'route-correction-review';
        }
        if ( 'low' === $confidence_level || 0 === absint( $source_count ) ) {
            return 'confidence-review';
        }
        return 'editorial-review';
    }

    private function append_feedback_log( $feedback ) {
        $logs = $this->feedback_logs();
        array_unshift( $logs, $feedback );
        $limit = max( 10, min( 1000, absint( $this->get_options()['feedback_log_limit'] ?? 200 ) ) );
        $logs = array_slice( $logs, 0, $limit );
        update_option( 'sc_rl_ai_feedback_log', $logs, false );
        update_option( 'sc_rl_ai_feedback_status', array(
            'last_feedback_utc' => $feedback['created_at_utc'],
            'last_type' => $feedback['type'],
            'last_triage_label' => $feedback['triage_label'],
            'last_route_id' => $feedback['route_id'],
        ), false );
    }

    private function feedback_logs() {
        $logs = get_option( 'sc_rl_ai_feedback_log', array() );
        return is_array( $logs ) ? $logs : array();
    }

    private function clear_feedback_logs() {
        update_option( 'sc_rl_ai_feedback_log', array(), false );
        update_option( 'sc_rl_ai_feedback_status', array(), false );
    }

    private function feedback_summary() {
        $logs = $this->feedback_logs();
        $types = array();
        $triage = array();
        $routes = array();
        $last = get_option( 'sc_rl_ai_feedback_status', array() );
        foreach ( $logs as $log ) {
            $type = $log['type'] ?? 'issue';
            $label = $log['triage_label'] ?? 'editorial-review';
            $route = $log['route_id'] ?? 'unknown';
            $types[ $type ] = ( $types[ $type ] ?? 0 ) + 1;
            $triage[ $label ] = ( $triage[ $label ] ?? 0 ) + 1;
            $routes[ $route ] = ( $routes[ $route ] ?? 0 ) + 1;
        }
        arsort( $routes );
        $top_route_id = $routes ? array_key_first( $routes ) : 'none';
        return array(
            'total_feedback' => count( $logs ),
            'helpful_count' => absint( $types['helpful'] ?? 0 ),
            'issue_count' => count( $logs ) - absint( $types['helpful'] ?? 0 ),
            'knowledge_gap_count' => absint( $types['knowledge_gap'] ?? 0 ) + absint( $types['missing_source'] ?? 0 ) + absint( $types['feature_gap'] ?? 0 ),
            'wrong_route_count' => absint( $types['wrong_route'] ?? 0 ),
            'types' => $types,
            'triage' => $triage,
            'top_route' => array( 'id' => $top_route_id, 'count' => absint( $routes[ $top_route_id ] ?? 0 ) ),
            'last_feedback_utc' => ! empty( $last['last_feedback_utc'] ) ? $last['last_feedback_utc'] : '',
            'recent_feedback' => array_slice( $logs, 0, 10 ),
        );
    }

    private function sanitize_deep( $value ) {
        if ( is_array( $value ) ) {
            $clean = array();
            foreach ( $value as $key => $item ) {
                $clean_key = is_string( $key ) ? sanitize_key( $key ) : $key;
                $clean[ $clean_key ] = $this->sanitize_deep( $item );
            }
            return $clean;
        }
        if ( is_bool( $value ) || is_int( $value ) || is_float( $value ) ) { return $value; }
        return sanitize_textarea_field( wp_unslash( (string) $value ) );
    }

    private function build_saved_session_record( $note ) {
        $route = isset( $note['recommended_route'] ) && is_array( $note['recommended_route'] ) ? $note['recommended_route'] : array();
        $confidence = isset( $note['confidence'] ) && is_array( $note['confidence'] ) ? $note['confidence'] : array();
        $handoff_payload = isset( $note['handoff_payload'] ) && is_array( $note['handoff_payload'] ) ? $note['handoff_payload'] : array();
        $target = isset( $handoff_payload['target'] ) ? sanitize_key( $handoff_payload['target'] ) : 'knowledge_route';
        return array(
            'session_id' => 'sc-rl-session-' . gmdate( 'YmdHis' ) . '-' . substr( md5( wp_json_encode( $note ) ), 0, 8 ),
            'created_at_utc' => gmdate( 'c' ),
            'question' => isset( $note['question'] ) ? sanitize_textarea_field( $note['question'] ) : '',
            'route_id' => isset( $route['id'] ) ? sanitize_key( $route['id'] ) : '',
            'route_title' => isset( $route['title'] ) ? sanitize_text_field( $route['title'] ) : '',
            'route_url' => isset( $route['url'] ) ? esc_url_raw( $route['url'] ) : '',
            'source' => isset( $note['source'] ) ? sanitize_key( $note['source'] ) : '',
            'confidence_level' => isset( $confidence['level'] ) ? sanitize_key( $confidence['level'] ) : 'unknown',
            'confidence_score' => isset( $confidence['score'] ) ? (float) $confidence['score'] : 0,
            'source_count' => isset( $note['sources'] ) && is_array( $note['sources'] ) ? count( $note['sources'] ) : 0,
            'handoff_target' => $target,
            'handoff_payload_id' => isset( $handoff_payload['payload_id'] ) ? sanitize_text_field( $handoff_payload['payload_id'] ) : '',
            'next_step' => isset( $note['next_step'] ) ? sanitize_textarea_field( $note['next_step'] ) : '',
            'route_note' => $note,
        );
    }

    private function append_session_log( $session ) {
        $logs = $this->session_logs();
        array_unshift( $logs, $session );
        $limit = max( 10, min( 1000, absint( $this->get_options()['session_log_limit'] ?? 200 ) ) );
        $logs = array_slice( $logs, 0, $limit );
        update_option( 'sc_rl_ai_session_log', $logs, false );
        update_option( 'sc_rl_ai_session_status', array(
            'last_saved_utc' => $session['created_at_utc'],
            'last_route_id' => $session['route_id'],
            'last_handoff_target' => $session['handoff_target'],
            'last_confidence_level' => $session['confidence_level'],
        ), false );
    }

    private function session_logs() {
        $logs = get_option( 'sc_rl_ai_session_log', array() );
        return is_array( $logs ) ? $logs : array();
    }

    private function clear_session_logs() {
        update_option( 'sc_rl_ai_session_log', array(), false );
        update_option( 'sc_rl_ai_session_status', array(), false );
    }

    private function session_analytics_summary() {
        $logs = $this->session_logs();
        $route_counts = array();
        $target_counts = array();
        $confidence_counts = array( 'high' => 0, 'medium' => 0, 'low' => 0, 'unknown' => 0 );
        foreach ( $logs as $log ) {
            $route_id = isset( $log['route_id'] ) && $log['route_id'] ? $log['route_id'] : 'unknown';
            $target = isset( $log['handoff_target'] ) && $log['handoff_target'] ? $log['handoff_target'] : 'knowledge_route';
            $confidence = isset( $log['confidence_level'] ) && $log['confidence_level'] ? $log['confidence_level'] : 'unknown';
            $route_counts[ $route_id ] = isset( $route_counts[ $route_id ] ) ? $route_counts[ $route_id ] + 1 : 1;
            $target_counts[ $target ] = isset( $target_counts[ $target ] ) ? $target_counts[ $target ] + 1 : 1;
            if ( ! isset( $confidence_counts[ $confidence ] ) ) { $confidence_counts[ $confidence ] = 0; }
            $confidence_counts[ $confidence ]++;
        }
        arsort( $route_counts );
        arsort( $target_counts );
        $top_route_id = key( $route_counts );
        $top_target = key( $target_counts );
        $last = ! empty( $logs[0] ) && is_array( $logs[0] ) ? $logs[0] : array();
        return array(
            'total_sessions' => count( $logs ),
            'unique_routes' => count( $route_counts ),
            'unique_targets' => count( $target_counts ),
            'route_counts' => $route_counts,
            'target_counts' => $target_counts,
            'confidence_counts' => $confidence_counts,
            'top_route' => array( 'id' => $top_route_id ? $top_route_id : 'none', 'label' => $top_route_id ? $top_route_id : 'none', 'count' => $top_route_id && isset( $route_counts[ $top_route_id ] ) ? $route_counts[ $top_route_id ] : 0 ),
            'top_target' => array( 'id' => $top_target ? $top_target : 'none', 'label' => $top_target ? $top_target : 'none', 'count' => $top_target && isset( $target_counts[ $top_target ] ) ? $target_counts[ $top_target ] : 0 ),
            'last_saved_utc' => isset( $last['created_at_utc'] ) ? $last['created_at_utc'] : '',
            'recent_sessions' => array_slice( $logs, 0, 10 ),
        );
    }

    private function handoff_schema() {
        return array(
            'targets' => array(
                'workbench' => array(
                    'label' => 'Sustainable Catalyst Workbench',
                    'use_when' => 'The next step requires calculation, graphing, formula inspection, symbolic review, unit-aware analysis, engineering notes, or exportable analytical reports.',
                    'payload_sections' => array( 'analysis_intent', 'tool_family', 'input_question', 'source_context', 'assumptions', 'variables', 'outputs_requested', 'boundary_notes' ),
                ),
                'decision_studio' => array(
                    'label' => 'Sustainable Catalyst Decision Studio',
                    'use_when' => 'The next step requires option comparison, assumptions, scenarios, audit/provenance, readiness review, module artifacts, or an exportable Decision Packet.',
                    'payload_sections' => array( 'decision_packet_seed', 'decision_question', 'artifact_slots', 'four_pillar_review', 'source_ledger_seed', 'assumptions_register_seed', 'workbench_handoff_needed', 'boundary_notes' ),
                ),
                'module_artifact' => array(
                    'label' => 'Sustainable Catalyst Module Artifact',
                    'use_when' => 'The next step is a specific module output such as Canvas framing, Data evidence, Analytics R scenario notes, Global Impact records, Narrative Risk claim review, Finance tradeoff notes, or Grit recovery tracking.',
                    'payload_sections' => array( 'module_id', 'module_title', 'artifact_intent', 'suggested_fields', 'decision_studio_import_note', 'source_context' ),
                ),
                'feature_suggestion' => array(
                    'label' => 'Feature Suggestions',
                    'use_when' => 'The visitor asks for a missing, unsupported, or not-yet-built capability.',
                    'payload_sections' => array( 'requested_capability', 'gap_reason', 'suggestion_route', 'source_context' ),
                ),
            ),
            'common_fields' => array( 'version', 'created_at_utc', 'payload_id', 'source', 'target', 'question', 'recommended_route', 'confidence', 'reason_codes', 'sources', 'handoffs', 'boundaries' ),
        );
    }

    private function handoff_summary() {
        $schema = $this->handoff_schema();
        $last = get_option( self::HANDOFF_OPTION, array() );
        return array(
            'targets' => count( $schema['targets'] ),
            'schemas' => count( $schema['targets'] ),
            'last_target' => ! empty( $last['last_target'] ) ? sanitize_text_field( $last['last_target'] ) : 'none',
            'last_payload_utc' => ! empty( $last['last_payload_utc'] ) ? sanitize_text_field( $last['last_payload_utc'] ) : '',
            'last_payload_source_count' => isset( $last['last_payload_source_count'] ) ? absint( $last['last_payload_source_count'] ) : 0,
            'log_count' => count( $this->handoff_logs() ),
        );
    }

    private function determine_handoff_target( $question, $route, $grounding ) {
        $id = isset( $route['id'] ) ? $route['id'] : 'platform';
        $q = strtolower( (string) $question );
        if ( 'feature-suggestions' === $id || preg_match( '/\b(missing|does not exist|new feature|feature request|unsupported|build a new)\b/', $q ) ) {
            return 'feature_suggestion';
        }
        if ( 'workbench' === $id || preg_match( '/\b(calculate|calculator|graph|plot|formula|equation|symbolic|unit|units|model inspection|engineering note|diagnostic)\b/', $q ) ) {
            return 'workbench';
        }
        if ( 'decision-studio' === $id || preg_match( '/\b(decision packet|decision brief|compare options|tradeoff|scenario comparison|readiness|audit|provenance|four pillar|four-pillar)\b/', $q ) ) {
            return 'decision_studio';
        }
        if ( in_array( $id, array( 'canvas', 'data', 'analytics-r', 'impact', 'narrative-risk', 'finance', 'grit' ), true ) ) {
            return 'module_artifact';
        }
        return 'knowledge_route';
    }

    private function build_handoff_payload( $question, $route, $source, $grounding = array() ) {
        $target = $this->determine_handoff_target( $question, $route, $grounding );
        $sources = isset( $grounding['sources'] ) && is_array( $grounding['sources'] ) ? $grounding['sources'] : array();
        $confidence = isset( $grounding['confidence'] ) ? $grounding['confidence'] : array();
        $base = array(
            'version' => self::VERSION,
            'payload_id' => 'sc-rl-handoff-' . gmdate( 'YmdHis' ) . '-' . substr( md5( $question . '|' . ( $route['id'] ?? '' ) ), 0, 8 ),
            'created_at_utc' => gmdate( 'c' ),
            'source' => $source,
            'target' => $target,
            'question' => $question,
            'recommended_route' => array(
                'id' => $route['id'],
                'title' => $route['title'],
                'url' => $route['url'],
                'category' => $route['category'],
                'description' => $route['description'],
            ),
            'confidence' => $confidence,
            'reason_codes' => isset( $grounding['reason_codes'] ) ? $grounding['reason_codes'] : array(),
            'sources' => $this->handoff_source_context( $sources ),
            'handoffs' => isset( $grounding['handoffs'] ) ? $grounding['handoffs'] : array(),
            'boundary_notes' => array(
                'Educational routing and structured handoff only.',
                'No legal, financial, medical, tax, engineering, compliance, assurance, ESG/SDG certification, or regulated-information advice.',
                'Human review is required before using any downstream result for consequential decisions.',
            ),
        );
        if ( 'workbench' === $target ) {
            $base['workbench_payload'] = $this->workbench_handoff_body( $question, $route, $sources );
        } elseif ( 'decision_studio' === $target ) {
            $base['decision_studio_payload'] = $this->decision_studio_handoff_body( $question, $route, $sources );
        } elseif ( 'module_artifact' === $target ) {
            $base['module_artifact_payload'] = $this->module_artifact_handoff_body( $question, $route, $sources );
        } elseif ( 'feature_suggestion' === $target ) {
            $base['feature_suggestion_payload'] = array(
                'requested_capability' => $question,
                'gap_reason' => 'The request appears to involve a missing, unsupported, or not-yet-built capability.',
                'suggestion_route' => array( 'title' => 'Feature Suggestions', 'url' => '/platform/feature-suggestions/' ),
                'submission_note' => 'Describe the desired workflow, expected inputs, outputs, and where it should connect to Workbench, Decision Studio, modules, or the Knowledge Library.',
            );
        } else {
            $base['knowledge_route_payload'] = array(
                'research_intent' => $route['intent'],
                'starting_route' => $route['url'],
                'suggested_next_step' => $route['next_step'],
                'clarification_prompt' => 'Clarify whether the next output should be a reading path, calculation, module artifact, or Decision Packet.',
            );
        }
        return $base;
    }

    private function handoff_source_context( $sources ) {
        $context = array();
        foreach ( array_slice( $sources, 0, 6 ) as $source ) {
            $context[] = array(
                'id' => isset( $source['id'] ) ? $source['id'] : '',
                'title' => isset( $source['title'] ) ? $source['title'] : '',
                'url' => isset( $source['url'] ) ? $source['url'] : '',
                'type' => isset( $source['type'] ) ? $source['type'] : '',
                'route_id' => isset( $source['route_id'] ) ? $source['route_id'] : '',
                'summary' => isset( $source['summary'] ) ? $source['summary'] : '',
                'score' => isset( $source['score'] ) ? $source['score'] : 0,
                'keyword_score' => isset( $source['keyword_score'] ) ? $source['keyword_score'] : 0,
                'semantic_score' => isset( $source['semantic_score'] ) ? $source['semantic_score'] : 0,
                'retrieval_mode' => isset( $source['retrieval_mode'] ) ? $source['retrieval_mode'] : 'unknown',
            );
        }
        return $context;
    }

    private function workbench_handoff_body( $question, $route, $sources ) {
        return array(
            'analysis_intent' => 'Turn the routed question into an inspectable calculation, graph, formula review, model note, or domain-calculator task.',
            'input_question' => $question,
            'tool_family' => $this->infer_workbench_tool_family( $question ),
            'formula_or_model_prompt' => '',
            'variables' => array(),
            'assumptions' => array( 'User-provided inputs still need to be reviewed.', 'Units, ranges, and data provenance should be checked before analysis.' ),
            'outputs_requested' => array( 'calculation_note', 'graph_or_visual_output_if_relevant', 'validation_warnings', 'exportable_report' ),
            'decision_studio_return_note' => 'Send the resulting calculation report back to Decision Studio if it should support a Decision Packet.',
        );
    }

    private function infer_workbench_tool_family( $question ) {
        $q = strtolower( $question );
        if ( preg_match( '/\b(graph|plot|visual|curve|sensitivity|slider)\b/', $q ) ) { return 'graph_studio'; }
        if ( preg_match( '/\b(formula|equation|symbolic|latex|derive)\b/', $q ) ) { return 'chalkboard_symbolic'; }
        if ( preg_match( '/\b(unit|units|engineering|structural|mechanical|electrical|calculation note)\b/', $q ) ) { return 'engineering_mode'; }
        if ( preg_match( '/\b(econometrics|psychometrics|biology|chemistry|physics|architecture|infrastructure|music|art|astrophysics)\b/', $q ) ) { return 'advanced_domain_calculator'; }
        return 'general_workbench_analysis';
    }

    private function decision_studio_handoff_body( $question, $route, $sources ) {
        return array(
            'decision_packet_seed' => array(
                'decision_question' => $question,
                'recommended_starting_route' => $route['title'],
                'status' => 'draft_seed',
                'review_stage' => 'intake',
            ),
            'artifact_slots' => array( 'framing', 'evidence', 'scenario', 'impact', 'claim_review', 'finance', 'recovery', 'workbench_calculation' ),
            'four_pillar_review' => array( 'environmental' => '', 'social' => '', 'economic' => '', 'governance_institutional' => '' ),
            'source_ledger_seed' => $this->handoff_source_context( $sources ),
            'assumptions_register_seed' => array( 'Known assumptions should be made explicit before comparing options.', 'Unresolved uncertainties should remain visible in the packet.' ),
            'workbench_handoff_needed' => $this->decision_needs_workbench( $question ),
            'export_targets' => array( 'integrated_brief', 'audit_appendix', 'decision_packet_json' ),
        );
    }

    private function decision_needs_workbench( $question ) {
        return (bool) preg_match( '/\b(calculate|calculator|graph|formula|model|equation|scenario value|sensitivity|diagnostic)\b/i', $question );
    }

    private function module_artifact_handoff_body( $question, $route, $sources ) {
        return array(
            'module_id' => $route['id'],
            'module_title' => $route['title'],
            'artifact_intent' => $route['intent'],
            'suggested_fields' => $this->module_artifact_fields( $route['id'] ),
            'decision_studio_import_note' => 'After the module artifact is created, import or summarize it in Decision Studio if it should support a larger decision brief.',
            'source_context' => $this->handoff_source_context( $sources ),
        );
    }

    private function module_artifact_fields( $route_id ) {
        $fields = array(
            'canvas' => array( 'challenge', 'audience', 'assumptions', 'point_of_view', 'prototype_direction', 'test_plan' ),
            'data' => array( 'entity', 'indicator', 'value', 'time_period', 'source', 'confidence', 'method_note', 'review_status' ),
            'analytics-r' => array( 'scenario_name', 'assumptions', 'input_values', 'outputs', 'interpretation_note', 'export_logic' ),
            'impact' => array( 'initiative', 'indicator', 'baseline', 'current_value', 'target', 'source', 'progress_note' ),
            'narrative-risk' => array( 'claim', 'evidence_strength', 'uncertainty', 'source_type', 'stakeholder_pressure', 'communication_risk' ),
            'finance' => array( 'option', 'cost', 'benefit', 'npv', 'roi', 'payback', 'risk_note', 'decision_note' ),
            'grit' => array( 'setback', 'pressure', 'impact', 'energy', 'support', 'clarity', 'recovery_action', 'next_step' ),
        );
        return isset( $fields[ $route_id ] ) ? $fields[ $route_id ] : array( 'title', 'context', 'inputs', 'outputs', 'source_note', 'review_status' );
    }

    private function append_handoff_log( $payload ) {
        $logs = $this->handoff_logs();
        array_unshift( $logs, array(
            'created_at_utc' => $payload['created_at_utc'],
            'payload_id' => $payload['payload_id'],
            'target' => $payload['target'],
            'route_id' => isset( $payload['recommended_route']['id'] ) ? $payload['recommended_route']['id'] : '',
            'route_title' => isset( $payload['recommended_route']['title'] ) ? $payload['recommended_route']['title'] : '',
            'source_count' => count( $payload['sources'] ),
            'confidence' => isset( $payload['confidence']['level'] ) ? $payload['confidence']['level'] : '',
        ) );
        $limit = max( 10, min( 500, absint( $this->get_options()['handoff_log_limit'] ?? 100 ) ) );
        $logs = array_slice( $logs, 0, $limit );
        update_option( 'sc_rl_ai_handoff_log', $logs, false );
        update_option( self::HANDOFF_OPTION, array(
            'last_target' => $payload['target'],
            'last_payload_utc' => $payload['created_at_utc'],
            'last_payload_source_count' => count( $payload['sources'] ),
        ), false );
    }

    private function handoff_logs() {
        $logs = get_option( 'sc_rl_ai_handoff_log', array() );
        return is_array( $logs ) ? $logs : array();
    }




    private function semantic_retrieval_enabled( $options = null ) {
        $options = $options ? $options : $this->get_options();
        return ( ! empty( $options['gemini_api_key'] ) && 'gemini' === sanitize_key( $options['embeddings_provider'] ?? 'disabled' ) && ! empty( $options['gemini_embedding_model'] ) );
    }

    private function retrieval_status() {
        $options = $this->get_options();
        $records = $this->knowledge_index_records();
        $embedded = 0;
        $dimensions = 0;
        foreach ( $records as $record ) {
            if ( ! empty( $record['embedding'] ) && is_array( $record['embedding'] ) ) {
                $embedded++;
                if ( 0 === $dimensions ) { $dimensions = count( $record['embedding'] ); }
            }
        }
        $status = get_option( self::EMBED_OPTION, array() );
        return array(
            'enabled' => $this->semantic_retrieval_enabled( $options ),
            'provider' => sanitize_key( $options['embeddings_provider'] ?? 'disabled' ),
            'embedding_model' => sanitize_text_field( $options['gemini_embedding_model'] ?? 'gemini-embedding-001' ),
            'embedding_output_dimensionality' => absint( $options['embedding_output_dimensionality'] ?? 0 ),
            'index_records' => count( $records ),
            'embedded_records' => $embedded,
            'embedding_dimensions' => $dimensions,
            'semantic_weight' => isset( $options['semantic_weight'] ) ? (string) $options['semantic_weight'] : '0.65',
            'keyword_weight' => isset( $options['keyword_weight'] ) ? (string) $options['keyword_weight'] : '0.35',
            'last_embedding_utc' => isset( $status['last_embedding_utc'] ) ? $status['last_embedding_utc'] : '',
            'last_error' => isset( $status['last_error'] ) ? $status['last_error'] : '',
            'last_error_code' => isset( $status['last_error_code'] ) ? $status['last_error_code'] : '',
            'last_http_status' => isset( $status['last_http_status'] ) ? absint( $status['last_http_status'] ) : 0,
            'first_failure_title' => isset( $status['first_failure_title'] ) ? $status['first_failure_title'] : '',
            'failure_sample_count' => isset( $status['failure_sample'] ) && is_array( $status['failure_sample'] ) ? count( $status['failure_sample'] ) : 0,
            'api_key_fingerprint_used' => isset( $status['api_key_fingerprint_used'] ) ? $status['api_key_fingerprint_used'] : array(),
            'current_api_key_fingerprint' => $this->secret_fingerprint( $options['gemini_api_key'] ?? '' ),
        );
    }


    private function secret_fingerprint( $secret ) {
        $secret = trim( (string) $secret );
        if ( '' === $secret ) {
            return array( 'present' => false, 'length' => 0, 'last4' => '', 'hash8' => '' );
        }
        return array(
            'present' => true,
            'length' => strlen( $secret ),
            'last4' => substr( $secret, -4 ),
            'hash8' => substr( hash( 'sha256', $secret ), 0, 8 ),
        );
    }

    private function fingerprint_changed( $current, $used ) {
        if ( ! is_array( $current ) || ! is_array( $used ) || empty( $used['present'] ) ) {
            return false;
        }
        return isset( $current['hash8'], $used['hash8'] ) && $current['hash8'] !== $used['hash8'];
    }

    private function secret_looks_plausible( $raw, $field = '' ) {
        $raw = trim( (string) $raw );
        if ( '' === $raw || '-' === $raw ) {
            return true;
        }
        $lower = strtolower( $raw );
        if ( false !== strpos( $lower, 'key saved' ) || false !== strpos( $lower, 'leave blank' ) || false !== strpos( $lower, 'api key' ) ) {
            return false;
        }
        if ( preg_match( '/^[\*\x{2022}\x{25CF}\x{2026}\.]+$/u', $raw ) ) {
            return false;
        }
        if ( preg_match( '/\s/', $raw ) ) {
            return false;
        }
        if ( strlen( $raw ) < 25 ) {
            return false;
        }
        if ( false !== strpos( $field, 'gemini' ) && 0 !== strpos( $raw, 'AIza' ) ) {
            // Preserve existing key on obviously accidental non-Google values, but keep this soft enough for future auth keys.
            return strlen( $raw ) >= 32 && preg_match( '/^[A-Za-z0-9_\-]+$/', $raw );
        }
        return (bool) preg_match( '/^[A-Za-z0-9_\-\.]+$/', $raw );
    }

    private function embedding_diagnostics() {
        $options = $this->get_options();
        $status = get_option( self::EMBED_OPTION, array() );
        $records = $this->knowledge_index_records();
        $diagnostics = array(
            'enabled' => $this->semantic_retrieval_enabled( $options ),
            'provider' => sanitize_key( $options['embeddings_provider'] ?? 'disabled' ),
            'model_setting' => sanitize_text_field( $options['gemini_embedding_model'] ?? 'gemini-embedding-001' ),
            'request_model' => $this->gemini_model_resource_name( sanitize_text_field( $options['gemini_embedding_model'] ?? 'gemini-embedding-001' ) ),
            'endpoint_model' => $this->gemini_model_endpoint_name( sanitize_text_field( $options['gemini_embedding_model'] ?? 'gemini-embedding-001' ) ),
            'uses_header_key' => true,
            'api_key_present' => ! empty( $options['gemini_api_key'] ),
            'api_key_fingerprint' => $this->secret_fingerprint( $options['gemini_api_key'] ?? '' ),
            'api_key_fingerprint_used' => isset( $status['api_key_fingerprint_used'] ) ? $status['api_key_fingerprint_used'] : array(),
            'api_key_fingerprint_changed_since_last_run' => $this->fingerprint_changed( $this->secret_fingerprint( $options['gemini_api_key'] ?? '' ), isset( $status['api_key_fingerprint_used'] ) ? $status['api_key_fingerprint_used'] : array() ),
            'index_records' => count( $records ),
            'last_embedding_utc' => isset( $status['last_embedding_utc'] ) ? $status['last_embedding_utc'] : '',
            'last_error' => isset( $status['last_error'] ) ? $status['last_error'] : '',
            'last_error_code' => isset( $status['last_error_code'] ) ? $status['last_error_code'] : '',
            'last_http_status' => isset( $status['last_http_status'] ) ? absint( $status['last_http_status'] ) : 0,
            'first_failure_id' => isset( $status['first_failure_id'] ) ? $status['first_failure_id'] : '',
            'first_failure_title' => isset( $status['first_failure_title'] ) ? $status['first_failure_title'] : '',
            'failure_sample' => isset( $status['failure_sample'] ) && is_array( $status['failure_sample'] ) ? $status['failure_sample'] : array(),
            'raw_response_excerpt' => isset( $status['raw_response_excerpt'] ) ? $status['raw_response_excerpt'] : '',
            'recommended_next_step' => $this->embedding_recommended_next_step( $status ),
        );
        return $diagnostics;
    }

    private function embedding_recommended_next_step( $status ) {
        $code = isset( $status['last_error_code'] ) ? (string) $status['last_error_code'] : '';
        $http = isset( $status['last_http_status'] ) ? absint( $status['last_http_status'] ) : 0;
        $message = strtolower( isset( $status['last_error'] ) ? (string) $status['last_error'] : '' );
        if ( 401 === $http || 403 === $http || false !== strpos( $message, 'api key' ) || false !== strpos( $message, 'permission' ) ) {
            return 'Check the Gemini API key and any Google AI Studio key restrictions. The key must be allowed to call the Gemini API from this server.';
        }
        if ( 404 === $http || false !== strpos( $message, 'not found' ) || false !== strpos( $message, 'model' ) ) {
            return 'Check the embedding model name. Use gemini-embedding-001 unless Google has changed access for your account.';
        }
        if ( 429 === $http || false !== strpos( $message, 'quota' ) || false !== strpos( $message, 'rate' ) ) {
            return 'Quota or rate limit may be blocking embeddings. Lower the embedding source limit to 1 or 5, wait, then try again.';
        }
        if ( 0 === $http && ! empty( $code ) ) {
            return 'The WordPress server may not be reaching Google. Check outbound HTTPS requests, firewall, DNS, or hosting restrictions.';
        }
        if ( ! empty( $status['last_error'] ) ) {
            return 'Run Test Single Gemini Embedding and review the first error shown below.';
        }
        return 'No embedding error is currently stored. Run Test Single Gemini Embedding or Generate Gemini Embeddings.';
    }

    private function get_query_embedding( $text, $options = null ) {
        $options = $options ? $options : $this->get_options();
        if ( ! $this->semantic_retrieval_enabled( $options ) ) {
            return new WP_Error( 'sc_rl_ai_embeddings_disabled', __( 'Gemini embeddings are not configured.', 'sustainable-catalyst-research-librarian-ai' ) );
        }
        $cache_key = 'sc_rl_qemb_' . md5( sanitize_textarea_field( $text ) . '|' . ( $options['gemini_embedding_model'] ?? '' ) );
        $cached = get_transient( $cache_key );
        if ( is_array( $cached ) ) { return $cached; }
        $embedding = $this->call_gemini_embedding( $text, $options, 'RETRIEVAL_QUERY' );
        if ( is_wp_error( $embedding ) ) { return $embedding; }
        set_transient( $cache_key, $embedding, HOUR_IN_SECONDS );
        return $embedding;
    }

    private function call_gemini_embedding( $text, $options = null, $task_type = 'RETRIEVAL_DOCUMENT', $title = '' ) {
        $options = $options ? $options : $this->get_options();
        $api_key = trim( $options['gemini_api_key'] ?? '' );
        $model_setting = sanitize_text_field( $options['gemini_embedding_model'] ?? 'gemini-embedding-001' );
        if ( '' === $api_key || '' === $model_setting ) {
            return new WP_Error( 'sc_rl_ai_missing_gemini_embedding_config', __( 'Gemini embedding configuration is missing.', 'sustainable-catalyst-research-librarian-ai' ), array( 'http_status' => 0 ) );
        }
        $text = wp_strip_all_tags( (string) $text );
        $text = trim( preg_replace( '/\s+/', ' ', $text ) );
        $text = mb_substr( $text, 0, 7000 );
        if ( '' === $text ) {
            return new WP_Error( 'sc_rl_ai_empty_embedding_input', __( 'The embedding input text is empty.', 'sustainable-catalyst-research-librarian-ai' ), array( 'http_status' => 0 ) );
        }
        $endpoint_model = $this->gemini_model_endpoint_name( $model_setting );
        $request_model = $this->gemini_model_resource_name( $model_setting );
        $url = 'https://generativelanguage.googleapis.com/v1beta/models/' . rawurlencode( $endpoint_model ) . ':embedContent';
        $task_type = in_array( $task_type, array( 'RETRIEVAL_DOCUMENT', 'RETRIEVAL_QUERY', 'SEMANTIC_SIMILARITY' ), true ) ? $task_type : 'RETRIEVAL_DOCUMENT';
        $config = array(
            'taskType' => $task_type,
            'autoTruncate' => true,
        );
        if ( 'RETRIEVAL_DOCUMENT' === $task_type && '' !== trim( $title ) ) {
            $config['title'] = mb_substr( sanitize_text_field( $title ), 0, 500 );
        }
        $dimensionality = absint( $options['embedding_output_dimensionality'] ?? 0 );
        if ( $dimensionality > 0 ) {
            $config['outputDimensionality'] = max( 1, min( 3072, $dimensionality ) );
        }
        $body = array(
            'model' => $request_model,
            'content' => array( 'parts' => array( array( 'text' => $text ) ) ),
            'embedContentConfig' => $config,
        );
        $response = wp_remote_post( $url, array(
            'headers' => array(
                'Content-Type' => 'application/json',
                'x-goog-api-key' => $api_key,
            ),
            'body' => wp_json_encode( $body ),
            'timeout' => 30,
        ) );
        if ( is_wp_error( $response ) ) {
            $response->add_data( array( 'http_status' => 0, 'endpoint_model' => $endpoint_model, 'request_model' => $request_model ), 'sc_rl_ai_gemini_embedding_transport' );
            return $response;
        }
        $code = wp_remote_retrieve_response_code( $response );
        $raw = wp_remote_retrieve_body( $response );
        $data = json_decode( $raw, true );
        if ( $code < 200 || $code >= 300 ) {
            $message = isset( $data['error']['message'] ) ? $data['error']['message'] : 'Gemini embedding request failed.';
            $error_code = isset( $data['error']['status'] ) ? $data['error']['status'] : 'HTTP_' . $code;
            return new WP_Error( 'sc_rl_ai_gemini_embedding_error', sanitize_text_field( $message ), array(
                'http_status' => $code,
                'gemini_error_code' => sanitize_text_field( $error_code ),
                'endpoint_model' => $endpoint_model,
                'request_model' => $request_model,
                'raw_response_excerpt' => mb_substr( wp_strip_all_tags( (string) $raw ), 0, 900 ),
            ) );
        }
        $values = $this->extract_gemini_embedding_values( $data );
        if ( empty( $values ) ) {
            return new WP_Error( 'sc_rl_ai_empty_embedding', __( 'Gemini did not return an embedding vector.', 'sustainable-catalyst-research-librarian-ai' ), array(
                'http_status' => $code,
                'endpoint_model' => $endpoint_model,
                'request_model' => $request_model,
                'raw_response_excerpt' => mb_substr( wp_strip_all_tags( (string) $raw ), 0, 900 ),
            ) );
        }
        return array_map( 'floatval', $values );
    }

    private function gemini_model_endpoint_name( $model ) {
        $model = trim( sanitize_text_field( (string) $model ) );
        $model = preg_replace( '#^models/#', '', $model );
        return '' === $model ? 'gemini-embedding-001' : $model;
    }

    private function gemini_model_resource_name( $model ) {
        return 'models/' . $this->gemini_model_endpoint_name( $model );
    }

    private function extract_gemini_embedding_values( $data ) {
        if ( isset( $data['embedding']['values'] ) && is_array( $data['embedding']['values'] ) ) {
            return $data['embedding']['values'];
        }
        if ( isset( $data['embeddings'][0]['values'] ) && is_array( $data['embeddings'][0]['values'] ) ) {
            return $data['embeddings'][0]['values'];
        }
        if ( isset( $data['embeddings'][0]['embedding']['values'] ) && is_array( $data['embeddings'][0]['embedding']['values'] ) ) {
            return $data['embeddings'][0]['embedding']['values'];
        }
        if ( isset( $data['embedding']['value'] ) && is_array( $data['embedding']['value'] ) ) {
            return $data['embedding']['value'];
        }
        return array();
    }

    private function wp_error_diagnostics( WP_Error $error ) {
        $all_data = $error->get_all_error_data();
        $data = is_array( $all_data ) && ! empty( $all_data ) ? end( $all_data ) : $error->get_error_data();
        $data = is_array( $data ) ? $data : array();
        return array(
            'message' => $error->get_error_message(),
            'code' => $error->get_error_code(),
            'http_status' => isset( $data['http_status'] ) ? absint( $data['http_status'] ) : 0,
            'gemini_error_code' => isset( $data['gemini_error_code'] ) ? sanitize_text_field( $data['gemini_error_code'] ) : '',
            'endpoint_model' => isset( $data['endpoint_model'] ) ? sanitize_text_field( $data['endpoint_model'] ) : '',
            'request_model' => isset( $data['request_model'] ) ? sanitize_text_field( $data['request_model'] ) : '',
            'raw_response_excerpt' => isset( $data['raw_response_excerpt'] ) ? sanitize_textarea_field( $data['raw_response_excerpt'] ) : '',
        );
    }

    private function generate_index_embeddings() {
        $options = $this->get_options();
        if ( ! $this->semantic_retrieval_enabled( $options ) ) {
            update_option( self::EMBED_OPTION, array( 'last_error' => 'Gemini embeddings are not enabled or API key is missing.', 'last_error_code' => 'embeddings_not_configured', 'last_http_status' => 0, 'last_embedding_utc' => gmdate( 'c' ) ), false );
            return new WP_Error( 'sc_rl_ai_embeddings_not_configured', __( 'Set Embeddings Provider to Gemini and save a Gemini API key before generating embeddings.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 400 ) );
        }
        $index = $this->knowledge_index();
        $records = isset( $index['records'] ) && is_array( $index['records'] ) ? $index['records'] : $this->knowledge_index_records();
        $limit = max( 1, min( 1000, absint( $options['embedding_source_limit'] ?? 250 ) ) );
        $retry_limit = max( 1, min( 25, absint( $options['embedding_retry_limit'] ?? 3 ) ) );
        $delay_ms = max( 0, min( 10000, absint( $options['embedding_batch_delay_ms'] ?? 1200 ) ) );
        $retry_after_seconds = max( 1, min( 60, absint( $options['embedding_retry_after_seconds'] ?? 5 ) ) );
        $resume_existing = ! isset( $options['embedding_resume_existing'] ) || '1' === (string) $options['embedding_resume_existing'];
        $model = sanitize_text_field( $options['gemini_embedding_model'] ?? 'gemini-embedding-001' );
        $api_key_fingerprint_used = $this->secret_fingerprint( $options['gemini_api_key'] ?? '' );
        $embedded = 0;
        $attempted = 0;
        $skipped_existing = 0;
        $failed = array();
        $first_error = null;

        foreach ( $records as $i => $record ) {
            if ( $attempted >= $limit ) { break; }

            if ( $resume_existing && ! empty( $record['embedding'] ) && is_array( $record['embedding'] ) && ( empty( $record['embedding_model'] ) || $record['embedding_model'] === $model ) ) {
                $skipped_existing++;
                continue;
            }

            $text = $this->embedding_text_for_record( $record );
            $title = isset( $record['title'] ) ? $record['title'] : '';
            $attempted++;
            $embedding = $this->call_gemini_embedding( $text, $options, 'RETRIEVAL_DOCUMENT', $title );

            if ( is_wp_error( $embedding ) ) {
                $diag = $this->wp_error_diagnostics( $embedding );
                $retryable = in_array( absint( $diag['http_status'] ), array( 429, 500, 502, 503, 504 ), true );
                if ( $retryable ) {
                    sleep( $retry_after_seconds );
                    $embedding = $this->call_gemini_embedding( $text, $options, 'RETRIEVAL_DOCUMENT', $title );
                    if ( is_wp_error( $embedding ) ) {
                        $diag = $this->wp_error_diagnostics( $embedding );
                    }
                }
            }

            if ( is_wp_error( $embedding ) ) {
                $diag = $this->wp_error_diagnostics( $embedding );
                if ( null === $first_error ) { $first_error = $diag; }
                $failed[] = array(
                    'id' => $record['id'] ?? '',
                    'title' => $title,
                    'error' => $diag['message'],
                    'error_code' => $diag['code'],
                    'http_status' => $diag['http_status'],
                    'gemini_error_code' => $diag['gemini_error_code'],
                );

                // Stop immediately for real key/authentication errors. Retrying those only burns time.
                $authish = ( 400 === absint( $diag['http_status'] ) || 401 === absint( $diag['http_status'] ) || 403 === absint( $diag['http_status'] ) ) && false !== stripos( (string) $diag['message'], 'key' );
                if ( $authish ) { break; }
                if ( count( $failed ) >= $retry_limit && 0 === $embedded ) { break; }
                continue;
            }

            $records[ $i ]['embedding'] = $embedding;
            $records[ $i ]['embedding_model'] = $model;
            $records[ $i ]['embedding_updated_utc'] = gmdate( 'c' );
            $embedded++;
            if ( $delay_ms > 0 && $attempted < $limit ) {
                usleep( $delay_ms * 1000 );
            }
        }

        $index['records'] = $records;
        $index['summary'] = $this->knowledge_index_summary( $records );
        $index['last_embedding_utc'] = gmdate( 'c' );
        $index['embedding_model'] = $model;
        $index['embedding_failures'] = array_slice( $failed, 0, 50 );
        update_option( self::INDEX_OPTION, $index, false );

        $last_error = '';
        if ( ! empty( $failed ) && 0 === $embedded ) {
            $last_error = 'No new records embedded in this run. First error: ' . ( $first_error['message'] ?? 'unknown error' );
        } elseif ( ! empty( $failed ) ) {
            $last_error = 'Some records failed to embed. Existing embeddings were preserved. First error: ' . ( $first_error['message'] ?? 'unknown error' );
        }
        $status = array(
            'last_embedding_utc' => gmdate( 'c' ),
            'attempted_records' => $attempted,
            'embedded_records_this_run' => $embedded,
            'skipped_existing' => $skipped_existing,
            'failed_records' => count( $failed ),
            'last_error' => sanitize_text_field( $last_error ),
            'last_error_code' => $first_error['code'] ?? '',
            'last_http_status' => $first_error['http_status'] ?? 0,
            'gemini_error_code' => $first_error['gemini_error_code'] ?? '',
            'first_failure_id' => $failed[0]['id'] ?? '',
            'first_failure_title' => $failed[0]['title'] ?? '',
            'failure_sample' => array_slice( $failed, 0, 5 ),
            'raw_response_excerpt' => $first_error['raw_response_excerpt'] ?? '',
            'delay_ms' => $delay_ms,
            'retry_after_seconds' => $retry_after_seconds,
            'resume_existing' => $resume_existing ? '1' : '0',
            'api_key_fingerprint_used' => $api_key_fingerprint_used,
        );
        update_option( self::EMBED_OPTION, $status, false );
        return array( 'version' => self::VERSION, 'attempted_records' => $attempted, 'embedded_records_this_run' => $embedded, 'skipped_existing' => $skipped_existing, 'failed_records' => count( $failed ), 'failure_sample' => array_slice( $failed, 0, 5 ), 'summary' => $this->knowledge_index_summary( $records ), 'retrieval' => $this->retrieval_status(), 'diagnostics' => $this->embedding_diagnostics() );
    }

    private function test_single_embedding() {
        $options = $this->get_options();
        if ( ! $this->semantic_retrieval_enabled( $options ) ) {
            update_option( self::EMBED_OPTION, array( 'last_error' => 'Gemini embeddings are not enabled or API key is missing.', 'last_error_code' => 'embeddings_not_configured', 'last_http_status' => 0, 'last_embedding_utc' => gmdate( 'c' ) ), false );
            return new WP_Error( 'sc_rl_ai_embeddings_not_configured', __( 'Set Embeddings Provider to Gemini and save a Gemini API key before testing embeddings.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 400 ) );
        }
        $records = $this->knowledge_index_records();
        $record = ! empty( $records ) ? $records[0] : array( 'id' => 'diagnostic', 'title' => 'Research Librarian Diagnostic', 'summary' => 'Diagnostic embedding test for Sustainable Catalyst Research Librarian.', 'topics' => array( 'diagnostic', 'embedding' ), 'route_id' => 'platform', 'url' => '/platform/research-librarian/' );
        $text = $this->embedding_text_for_record( $record );
        $embedding = $this->call_gemini_embedding( $text, $options, 'RETRIEVAL_DOCUMENT', $record['title'] ?? 'Diagnostic' );
        if ( is_wp_error( $embedding ) ) {
            $diag = $this->wp_error_diagnostics( $embedding );
            $status = array(
                'last_embedding_utc' => gmdate( 'c' ),
                'attempted_records' => 1,
                'embedded_records' => 0,
                'failed_records' => 1,
                'last_error' => sanitize_text_field( 'Single embedding test failed: ' . $diag['message'] ),
                'last_error_code' => $diag['code'],
                'last_http_status' => $diag['http_status'],
                'api_key_fingerprint_used' => $this->secret_fingerprint( $options['gemini_api_key'] ?? '' ),
                'gemini_error_code' => $diag['gemini_error_code'],
                'first_failure_id' => $record['id'] ?? '',
                'first_failure_title' => $record['title'] ?? '',
                'failure_sample' => array( array( 'id' => $record['id'] ?? '', 'title' => $record['title'] ?? '', 'error' => $diag['message'], 'error_code' => $diag['code'], 'http_status' => $diag['http_status'], 'gemini_error_code' => $diag['gemini_error_code'] ) ),
                'raw_response_excerpt' => $diag['raw_response_excerpt'],
            );
            update_option( self::EMBED_OPTION, $status, false );
            return new WP_Error( $diag['code'], $diag['message'], array( 'status' => 400, 'diagnostics' => $this->embedding_diagnostics() ) );
        }
        $status = array(
            'last_embedding_utc' => gmdate( 'c' ),
            'attempted_records' => 1,
            'embedded_records' => 1,
            'failed_records' => 0,
            'last_error' => '',
            'last_error_code' => '',
            'last_http_status' => 200,
            'api_key_fingerprint_used' => $this->secret_fingerprint( $options['gemini_api_key'] ?? '' ),
            'first_failure_id' => '',
            'first_failure_title' => '',
            'failure_sample' => array(),
            'raw_response_excerpt' => '',
        );
        update_option( self::EMBED_OPTION, $status, false );
        return array( 'version' => self::VERSION, 'ok' => true, 'record_id' => $record['id'] ?? '', 'record_title' => $record['title'] ?? '', 'embedding_dimensions' => count( $embedding ), 'retrieval' => $this->retrieval_status(), 'diagnostics' => $this->embedding_diagnostics() );
    }

    private function embedding_text_for_record( $record ) {
        $topics = isset( $record['topics'] ) && is_array( $record['topics'] ) ? implode( ', ', $record['topics'] ) : '';
        return trim( ( $record['title'] ?? '' ) . "\n" . ( $record['type'] ?? '' ) . "\n" . ( $record['summary'] ?? '' ) . "\nTopics: " . $topics . "\nRoute: " . ( $record['route_id'] ?? '' ) . "\nURL: " . ( $record['url'] ?? '' ) );
    }

    private function cosine_similarity( $a, $b ) {
        if ( ! is_array( $a ) || ! is_array( $b ) || empty( $a ) || empty( $b ) ) { return 0.0; }
        $n = min( count( $a ), count( $b ) );
        $dot = 0.0; $na = 0.0; $nb = 0.0;
        for ( $i = 0; $i < $n; $i++ ) {
            $av = (float) $a[ $i ]; $bv = (float) $b[ $i ];
            $dot += $av * $bv; $na += $av * $av; $nb += $bv * $bv;
        }
        if ( $na <= 0 || $nb <= 0 ) { return 0.0; }
        return max( 0.0, min( 1.0, $dot / ( sqrt( $na ) * sqrt( $nb ) ) ) );
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
        $embedded = 0;
        foreach ( $records as $record ) {
            if ( ! empty( $record['embedding'] ) && is_array( $record['embedding'] ) ) { $embedded++; }
        }
        $summary['failed_records'] = $failed;
        $summary['embedded_records'] = $embedded;
        return $summary;
    }


    private function evaluation_suite() {
        return array(
            array( 'id' => 'new-visitor', 'prompt' => 'I am new to Sustainable Catalyst. Where should I start?', 'expected_routes' => array( 'platform', 'knowledge-library' ), 'category' => 'orientation' ),
            array( 'id' => 'decision-brief', 'prompt' => 'I need to compare sustainability options and export a decision brief.', 'expected_routes' => array( 'decision-studio' ), 'category' => 'decision-support' ),
            array( 'id' => 'workbench-calc', 'prompt' => 'I need to calculate, graph, or compare a model.', 'expected_routes' => array( 'workbench' ), 'category' => 'analysis' ),
            array( 'id' => 'claim-risk', 'prompt' => 'Which tool helps me review a risky public claim?', 'expected_routes' => array( 'narrative-risk' ), 'category' => 'claim-review' ),
            array( 'id' => 'impact-record', 'prompt' => 'I need a traceable impact record with baseline and target values.', 'expected_routes' => array( 'impact' ), 'category' => 'impact' ),
            array( 'id' => 'problem-framing', 'prompt' => 'I want to frame a sustainability problem before choosing metrics.', 'expected_routes' => array( 'canvas' ), 'category' => 'framing' ),
            array( 'id' => 'data-provenance', 'prompt' => 'I need to structure sources, indicators, evidence, and provenance.', 'expected_routes' => array( 'data' ), 'category' => 'data' ),
            array( 'id' => 'scenario-analysis', 'prompt' => 'I need scenario analysis and reproducible analytical outputs.', 'expected_routes' => array( 'analytics-r', 'workbench' ), 'category' => 'scenario-analysis' ),
            array( 'id' => 'finance-tradeoff', 'prompt' => 'I need educational NPV, ROI, payback, and tradeoff analysis.', 'expected_routes' => array( 'finance' ), 'category' => 'finance' ),
            array( 'id' => 'recovery-grit', 'prompt' => 'I need to track pressure, energy, support, recovery actions, and next steps after a setback.', 'expected_routes' => array( 'grit' ), 'category' => 'human-systems' ),
            array( 'id' => 'missing-feature', 'prompt' => 'I need a capability that does not exist yet. Where should I send the idea?', 'expected_routes' => array( 'feature-suggestions' ), 'category' => 'open-development' ),
            array( 'id' => 'methodology-boundary', 'prompt' => 'Where can I read about assumptions, traceability, responsible AI, and evidence boundaries?', 'expected_routes' => array( 'methodology' ), 'category' => 'methodology' ),
        );
    }

    private function evaluation_summary_defaults() {
        return array( 'total_cases' => 0, 'passed_cases' => 0, 'failed_cases' => 0, 'accuracy' => 0, 'average_confidence_score' => 0, 'low_confidence' => 0, 'weak_source_matches' => 0, 'route_mismatches' => 0, 'last_quality_label' => 'not-run' );
    }

    private function evaluation_summary( $last = null ) {
        if ( null === $last ) { $last = get_option( self::EVAL_OPTION, array() ); }
        $summary = isset( $last['summary'] ) && is_array( $last['summary'] ) ? wp_parse_args( $last['summary'], $this->evaluation_summary_defaults() ) : $this->evaluation_summary_defaults();
        return array(
            'version' => self::VERSION,
            'last_run_utc' => isset( $last['last_run_utc'] ) ? $last['last_run_utc'] : '',
            'summary' => $summary,
        );
    }

    private function run_retrieval_evaluation( $cases = array(), $store = true ) {
        if ( empty( $cases ) || ! is_array( $cases ) ) { $cases = $this->evaluation_suite(); }
        $results = array(); $passed = 0; $low = 0; $weak = 0; $mismatches = 0; $score_total = 0;
        foreach ( $cases as $case ) {
            $prompt = isset( $case['prompt'] ) ? sanitize_textarea_field( $case['prompt'] ) : '';
            if ( '' === trim( $prompt ) ) { continue; }
            $expected = isset( $case['expected_routes'] ) && is_array( $case['expected_routes'] ) ? array_map( 'sanitize_key', $case['expected_routes'] ) : array();
            if ( empty( $expected ) && ! empty( $case['expected_route'] ) ) { $expected = array( sanitize_key( $case['expected_route'] ) ); }
            $result = $this->evaluate_retrieval_query( $prompt, $expected, isset( $case['id'] ) ? sanitize_key( $case['id'] ) : 'case' );
            $result['category'] = isset( $case['category'] ) ? sanitize_key( $case['category'] ) : 'general';
            $results[] = $result;
            if ( ! empty( $result['passed'] ) ) { $passed++; } else { $mismatches++; }
            if ( isset( $result['confidence']['level'] ) && 'low' === $result['confidence']['level'] ) { $low++; }
            if ( isset( $result['source_count'] ) && $result['source_count'] < $this->evaluation_min_source_count() ) { $weak++; }
            $score_total += isset( $result['confidence']['score'] ) ? (float) $result['confidence']['score'] : 0;
        }
        $total = count( $results );
        $summary = array(
            'total_cases' => $total,
            'passed_cases' => $passed,
            'failed_cases' => max( 0, $total - $passed ),
            'accuracy' => $total ? round( ( $passed / $total ) * 100, 2 ) : 0,
            'average_confidence_score' => $total ? round( $score_total / $total, 2 ) : 0,
            'low_confidence' => $low,
            'weak_source_matches' => $weak,
            'route_mismatches' => $mismatches,
            'last_quality_label' => $this->evaluation_quality_label_for_summary( $total, $passed, $low, $weak ),
        );
        $report = array(
            'version' => self::VERSION,
            'last_run_utc' => gmdate( 'c' ),
            'summary' => $summary,
            'results' => $results,
            'retrieval' => $this->retrieval_status(),
            'index' => $this->knowledge_index_summary( $this->knowledge_index_records() ),
        );
        if ( $store ) {
            update_option( self::EVAL_OPTION, $report, false );
            $failures = array_values( array_filter( $results, function( $result ) { return empty( $result['passed'] ) || 'low' === ( $result['confidence']['level'] ?? '' ) || ( isset( $result['source_count'] ) && $result['source_count'] < $this->evaluation_min_source_count() ); } ) );
            $this->append_evaluation_log( $failures, $summary );
        }
        return $report;
    }

    private function evaluate_retrieval_query( $prompt, $expected_routes = array(), $case_id = 'manual' ) {
        $route = $this->match_route( strtolower( $prompt ) );
        $grounding = $this->grounding_context( $prompt, $route );
        $sources = isset( $grounding['sources'] ) && is_array( $grounding['sources'] ) ? $grounding['sources'] : array();
        $confidence = isset( $grounding['confidence'] ) && is_array( $grounding['confidence'] ) ? $grounding['confidence'] : array( 'level' => 'low', 'score' => 0, 'explanation' => 'No confidence data returned.' );
        $expected_routes = array_values( array_unique( array_filter( array_map( 'sanitize_key', (array) $expected_routes ) ) ) );
        $passed = empty( $expected_routes ) ? null : in_array( $route['id'], $expected_routes, true );
        $top = ! empty( $sources[0] ) ? $sources[0] : array();
        $second = ! empty( $sources[1] ) ? $sources[1] : array();
        $top_score = isset( $top['score'] ) ? (float) $top['score'] : 0;
        $second_score = isset( $second['score'] ) ? (float) $second['score'] : 0;
        $margin = round( max( 0, $top_score - $second_score ), 3 );
        $source_count = count( $sources );
        $warnings = array();
        if ( false === $passed ) { $warnings[] = 'expected-route-mismatch'; }
        if ( 'low' === ( $confidence['level'] ?? 'low' ) ) { $warnings[] = 'low-confidence'; }
        if ( $source_count < $this->evaluation_min_source_count() ) { $warnings[] = 'weak-source-coverage'; }
        if ( $top && empty( $top['semantic_score'] ) && $this->semantic_retrieval_enabled() ) { $warnings[] = 'no-semantic-top-match'; }
        return array(
            'case_id' => $case_id,
            'prompt' => $prompt,
            'expected_routes' => $expected_routes,
            'recommended_route' => array( 'id' => $route['id'], 'title' => $route['title'], 'url' => $route['url'] ),
            'passed' => $passed,
            'quality_label' => $this->evaluation_quality_label( $passed, $confidence, $source_count, $margin ),
            'confidence' => $confidence,
            'source_count' => $source_count,
            'top_source' => $top ? array( 'title' => $top['title'] ?? '', 'url' => $top['url'] ?? '', 'route_id' => $top['route_id'] ?? '', 'score' => $top['score'] ?? 0, 'keyword_score' => $top['keyword_score'] ?? 0, 'semantic_score' => $top['semantic_score'] ?? 0, 'retrieval_mode' => $top['retrieval_mode'] ?? '' ) : array(),
            'score_breakdown' => array( 'top_score' => $top_score, 'second_score' => $second_score, 'margin' => $margin, 'semantic_weight' => $this->get_options()['semantic_weight'] ?? '0.65', 'keyword_weight' => $this->get_options()['keyword_weight'] ?? '0.35' ),
            'reason_codes' => isset( $grounding['reason_codes'] ) ? $grounding['reason_codes'] : array(),
            'warnings' => $warnings,
        );
    }

    private function evaluation_min_source_count() {
        $options = $this->get_options();
        return max( 0, min( 5, absint( $options['evaluation_min_source_count'] ?? 1 ) ) );
    }

    private function evaluation_quality_label( $passed, $confidence, $source_count, $margin ) {
        $level = isset( $confidence['level'] ) ? $confidence['level'] : 'low';
        if ( false === $passed ) { return 'route-mismatch'; }
        if ( 'low' === $level ) { return 'low-confidence'; }
        if ( $source_count < $this->evaluation_min_source_count() ) { return 'weak-source-coverage'; }
        if ( 'high' === $level && $margin >= 5 ) { return 'strong'; }
        return 'acceptable';
    }

    private function evaluation_quality_label_for_summary( $total, $passed, $low, $weak ) {
        if ( 0 === $total ) { return 'not-run'; }
        $accuracy = ( $passed / $total ) * 100;
        if ( $accuracy >= 90 && 0 === $low && 0 === $weak ) { return 'strong'; }
        if ( $accuracy >= 75 ) { return 'acceptable'; }
        return 'needs-review';
    }

    private function append_evaluation_log( $failures, $summary ) {
        $log = get_option( 'sc_rl_ai_evaluation_failure_log', array() );
        $log = is_array( $log ) ? $log : array();
        if ( ! empty( $failures ) ) {
            $log[] = array( 'created_at_utc' => gmdate( 'c' ), 'summary' => $summary, 'failures' => array_slice( $failures, 0, 25 ) );
        }
        $limit = max( 10, min( 500, absint( $this->get_options()['evaluation_log_limit'] ?? 100 ) ) );
        $log = array_slice( $log, -1 * $limit );
        update_option( 'sc_rl_ai_evaluation_failure_log', $log, false );
    }

    private function evaluation_logs() {
        $log = get_option( 'sc_rl_ai_evaluation_failure_log', array() );
        return is_array( $log ) ? $log : array();
    }

    private function clear_evaluation_logs() {
        update_option( 'sc_rl_ai_evaluation_failure_log', array(), false );
        update_option( self::EVAL_OPTION, array(), false );
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
        if ( 'embed' === $action ) {
            $result = $this->generate_index_embeddings();
            if ( is_wp_error( $result ) ) {
                set_transient( 'sc_rl_ai_admin_notice', $result->get_error_message(), 60 );
                return 'embedding-error';
            }
            if ( isset( $result['embedded_records'] ) && 0 === absint( $result['embedded_records'] ) ) {
                $diagnostics = isset( $result['diagnostics']['last_error'] ) ? $result['diagnostics']['last_error'] : 'No records embedded. Review diagnostics below.';
                set_transient( 'sc_rl_ai_admin_notice', $diagnostics, 60 );
                return 'embedding-error';
            }
            return 'embedded';
        }
        if ( 'test_embedding' === $action ) {
            $result = $this->test_single_embedding();
            if ( is_wp_error( $result ) ) {
                set_transient( 'sc_rl_ai_admin_notice', 'Single embedding test failed: ' . $result->get_error_message(), 60 );
                return 'embedding-error';
            }
            set_transient( 'sc_rl_ai_admin_success_notice', 'Single embedding test passed. Dimensions: ' . absint( $result['embedding_dimensions'] ?? 0 ), 60 );
            return 'test-embedding-ok';
        }
        if ( 'reset' === $action ) {
            update_option( self::INDEX_OPTION, self::build_default_index(), false );
            update_option( self::EMBED_OPTION, array(), false );
            return 'reset';
        }
        if ( 'run_evaluation' === $action ) {
            $this->run_retrieval_evaluation( array(), true );
            return 'evaluation-run';
        }
        if ( 'clear_evaluation' === $action ) {
            $this->clear_evaluation_logs();
            return 'evaluation-cleared';
        }
        if ( 'clear_sessions' === $action ) {
            $this->clear_session_logs();
            return 'sessions-cleared';
        }
        if ( 'clear_feedback' === $action ) {
            $this->clear_feedback_logs();
            return 'feedback-cleared';
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
            'embeddings_provider' => __( 'Embeddings Provider', 'sustainable-catalyst-research-librarian-ai' ),
            'gemini_embedding_model' => __( 'Gemini Embedding Model', 'sustainable-catalyst-research-librarian-ai' ),
            'embedding_source_limit' => __( 'Embedding Source Limit', 'sustainable-catalyst-research-librarian-ai' ),
            'embedding_output_dimensionality' => __( 'Embedding Output Dimensionality', 'sustainable-catalyst-research-librarian-ai' ),
            'embedding_retry_limit' => __( 'Embedding Failure Stop Limit', 'sustainable-catalyst-research-librarian-ai' ),
            'embedding_batch_delay_ms' => __( 'Embedding Delay Between Requests (ms)', 'sustainable-catalyst-research-librarian-ai' ),
            'embedding_retry_after_seconds' => __( 'Retry Delay for Rate Limits (seconds)', 'sustainable-catalyst-research-librarian-ai' ),
            'embedding_resume_existing' => __( 'Resume Existing Embeddings', 'sustainable-catalyst-research-librarian-ai' ),
            'semantic_weight' => __( 'Semantic Weight', 'sustainable-catalyst-research-librarian-ai' ),
            'keyword_weight' => __( 'Keyword Weight', 'sustainable-catalyst-research-librarian-ai' ),
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
            'eval_high_confidence_threshold' => __( 'High Confidence Threshold', 'sustainable-catalyst-research-librarian-ai' ),
            'eval_medium_confidence_threshold' => __( 'Medium Confidence Threshold', 'sustainable-catalyst-research-librarian-ai' ),
            'evaluation_min_source_count' => __( 'Minimum Source Matches for Evaluation', 'sustainable-catalyst-research-librarian-ai' ),
            'evaluation_log_limit' => __( 'Evaluation Failure Log Limit', 'sustainable-catalyst-research-librarian-ai' ),
            'handoff_log_limit' => __( 'Handoff Log Limit', 'sustainable-catalyst-research-librarian-ai' ),
            'session_log_limit' => __( 'Saved Route Session Log Limit', 'sustainable-catalyst-research-librarian-ai' ),
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
            'gemini_key_fingerprint'  => $this->secret_fingerprint_hash_for_options( $this->sanitize_secret_field( $input, 'gemini_api_key', $old['gemini_api_key'] ) ),
            'gemini_model'            => isset( $input['gemini_model'] ) ? sanitize_text_field( wp_unslash( $input['gemini_model'] ) ) : self::defaults()['gemini_model'],
            'embeddings_provider'     => ( isset( $input['embeddings_provider'] ) && 'gemini' === sanitize_key( wp_unslash( $input['embeddings_provider'] ) ) ) ? 'gemini' : 'disabled',
            'gemini_embedding_model'  => isset( $input['gemini_embedding_model'] ) ? sanitize_text_field( wp_unslash( $input['gemini_embedding_model'] ) ) : self::defaults()['gemini_embedding_model'],
            'embedding_source_limit'  => max( 1, min( 1000, absint( isset( $input['embedding_source_limit'] ) ? $input['embedding_source_limit'] : self::defaults()['embedding_source_limit'] ) ) ),
            'embedding_output_dimensionality' => max( 0, min( 3072, absint( isset( $input['embedding_output_dimensionality'] ) ? $input['embedding_output_dimensionality'] : self::defaults()['embedding_output_dimensionality'] ) ) ),
            'embedding_retry_limit'   => max( 1, min( 25, absint( isset( $input['embedding_retry_limit'] ) ? $input['embedding_retry_limit'] : self::defaults()['embedding_retry_limit'] ) ) ),
            'embedding_batch_delay_ms' => max( 0, min( 10000, absint( isset( $input['embedding_batch_delay_ms'] ) ? $input['embedding_batch_delay_ms'] : self::defaults()['embedding_batch_delay_ms'] ) ) ),
            'embedding_retry_after_seconds' => max( 1, min( 60, absint( isset( $input['embedding_retry_after_seconds'] ) ? $input['embedding_retry_after_seconds'] : self::defaults()['embedding_retry_after_seconds'] ) ) ),
            'embedding_resume_existing' => ( isset( $input['embedding_resume_existing'] ) && '1' === (string) wp_unslash( $input['embedding_resume_existing'] ) ) ? '1' : '0',
            'semantic_weight'         => isset( $input['semantic_weight'] ) && is_numeric( $input['semantic_weight'] ) ? (string) max( 0, min( 1, (float) $input['semantic_weight'] ) ) : self::defaults()['semantic_weight'],
            'keyword_weight'          => isset( $input['keyword_weight'] ) && is_numeric( $input['keyword_weight'] ) ? (string) max( 0, min( 1, (float) $input['keyword_weight'] ) ) : self::defaults()['keyword_weight'],
            'openai_api_key'          => $this->sanitize_secret_field( $input, 'openai_api_key', $old['openai_api_key'] ),
            'openai_key_fingerprint'  => $this->secret_fingerprint_hash_for_options( $this->sanitize_secret_field( $input, 'openai_api_key', $old['openai_api_key'] ) ),
            'openai_model'            => isset( $input['openai_model'] ) ? sanitize_text_field( wp_unslash( $input['openai_model'] ) ) : self::defaults()['openai_model'],
            'openai_vector_store_id'  => isset( $input['openai_vector_store_id'] ) ? sanitize_text_field( wp_unslash( $input['openai_vector_store_id'] ) ) : '',
            'max_file_search_results' => max( 1, min( 20, absint( isset( $input['max_file_search_results'] ) ? $input['max_file_search_results'] : self::defaults()['max_file_search_results'] ) ) ),
            'max_output_tokens'       => max( 150, min( 4000, absint( isset( $input['max_output_tokens'] ) ? $input['max_output_tokens'] : self::defaults()['max_output_tokens'] ) ) ),
            'temperature'             => isset( $input['temperature'] ) && is_numeric( $input['temperature'] ) ? (string) max( 0, min( 1, (float) $input['temperature'] ) ) : self::defaults()['temperature'],
            'rate_limit'              => max( 1, min( 100, absint( isset( $input['rate_limit'] ) ? $input['rate_limit'] : self::defaults()['rate_limit'] ) ) ),
            'source_result_limit'     => max( 3, min( 8, absint( isset( $input['source_result_limit'] ) ? $input['source_result_limit'] : self::defaults()['source_result_limit'] ) ) ),
            'index_max_posts'         => max( 25, min( 1000, absint( isset( $input['index_max_posts'] ) ? $input['index_max_posts'] : self::defaults()['index_max_posts'] ) ) ),
            'stale_after_days'        => max( 30, min( 1095, absint( isset( $input['stale_after_days'] ) ? $input['stale_after_days'] : self::defaults()['stale_after_days'] ) ) ),
            'eval_high_confidence_threshold' => max( 50, min( 95, absint( isset( $input['eval_high_confidence_threshold'] ) ? $input['eval_high_confidence_threshold'] : self::defaults()['eval_high_confidence_threshold'] ) ) ),
            'eval_medium_confidence_threshold' => max( 20, min( 90, absint( isset( $input['eval_medium_confidence_threshold'] ) ? $input['eval_medium_confidence_threshold'] : self::defaults()['eval_medium_confidence_threshold'] ) ) ),
            'evaluation_min_source_count' => max( 0, min( 5, absint( isset( $input['evaluation_min_source_count'] ) ? $input['evaluation_min_source_count'] : self::defaults()['evaluation_min_source_count'] ) ) ),
            'evaluation_log_limit'    => max( 10, min( 500, absint( isset( $input['evaluation_log_limit'] ) ? $input['evaluation_log_limit'] : self::defaults()['evaluation_log_limit'] ) ) ),
            'handoff_log_limit'       => max( 10, min( 500, absint( isset( $input['handoff_log_limit'] ) ? $input['handoff_log_limit'] : self::defaults()['handoff_log_limit'] ) ) ),
            'session_log_limit'       => max( 10, min( 1000, absint( isset( $input['session_log_limit'] ) ? $input['session_log_limit'] : self::defaults()['session_log_limit'] ) ) ),
            'feedback_log_limit'      => max( 10, min( 1000, absint( isset( $input['feedback_log_limit'] ) ? $input['feedback_log_limit'] : self::defaults()['feedback_log_limit'] ) ) ),
            'system_instructions'     => isset( $input['system_instructions'] ) ? sanitize_textarea_field( wp_unslash( $input['system_instructions'] ) ) : self::default_system_instructions(),
        );
    }

    private function sanitize_secret_field( $input, $field, $old_value ) {
        $new_field = $field . '_new';
        $clear_field = $field . '_clear';

        if ( isset( $input[ $clear_field ] ) && '1' === (string) wp_unslash( $input[ $clear_field ] ) ) {
            return '';
        }

        if ( isset( $input[ $new_field ] ) ) {
            $raw = trim( sanitize_text_field( wp_unslash( $input[ $new_field ] ) ) );
        } elseif ( isset( $input[ $field ] ) ) {
            // Backward compatibility with older settings forms.
            $raw = trim( sanitize_text_field( wp_unslash( $input[ $field ] ) ) );
        } else {
            return $old_value;
        }

        if ( '-' === $raw ) {
            return '';
        }
        if ( '' === $raw || '__KEEP__' === $raw ) {
            return $old_value;
        }
        if ( ! $this->secret_looks_plausible( $raw, $field ) ) {
            add_settings_error( self::OPTION_NAME, 'sc_rl_ai_key_preserved_' . $field, __( 'The API key field looked like a placeholder, mask, browser autofill value, or incomplete key. Existing saved key was preserved.', 'sustainable-catalyst-research-librarian-ai' ), 'warning' );
            return $old_value;
        }
        return $raw;
    }

    private function secret_fingerprint_hash_for_options( $secret ) {
        $fp = $this->secret_fingerprint( $secret );
        return ! empty( $fp['present'] ) ? $fp['hash8'] : '';
    }

    public function settings_section_intro() {
        echo '<p>' . esc_html__( 'The Research Librarian is site-scoped routing infrastructure. It can run entirely in deterministic fallback mode, use Gemini/OpenAI server-side for richer route explanations, and use optional Gemini embeddings for semantic retrieval over the Sustainable Catalyst knowledge index. API keys are not exposed to JavaScript.', 'sustainable-catalyst-research-librarian-ai' ) . '</p>';
        echo '<p><code>[sustainable_catalyst_research_librarian_ai]</code> <code>[sc_research_librarian mode="landing"]</code> <code>[sc_research_librarian mode="route-map"]</code> <code>[sc_research_librarian mode="index-summary"]</code> <code>[sc_research_librarian mode="retrieval-status"]</code> <code>[sc_research_librarian mode="evaluation-summary"]</code> <code>[sc_research_librarian mode="handoff-summary"]</code> <code>[sc_research_librarian mode="session-summary"]</code> <code>[sc_research_librarian mode="analytics-summary"]</code> <code>[sc_research_librarian mode="feedback-summary"]</code></p>';
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
            case 'embeddings_provider':
                echo '<select name="' . esc_attr( $name ) . '">';
                foreach ( array( 'disabled' => 'Disabled / keyword-only retrieval', 'gemini' => 'Gemini embeddings' ) as $value => $label ) {
                    echo '<option value="' . esc_attr( $value ) . '" ' . selected( $options['embeddings_provider'], $value, false ) . '>' . esc_html( $label ) . '</option>';
                }
                echo '</select>';
                echo '<p class="description">' . esc_html__( 'When enabled, embeddings are generated server-side for indexed Sustainable Catalyst records and used for hybrid semantic retrieval.', 'sustainable-catalyst-research-librarian-ai' ) . '</p>';
                break;
            case 'gemini_api_key':
            case 'openai_api_key':
                $has_key = ! empty( $options[ $field ] );
                $new_name = self::OPTION_NAME . '[' . $field . '_new]';
                $clear_name = self::OPTION_NAME . '[' . $field . '_clear]';
                $fp = $this->secret_fingerprint( $options[ $field ] ?? '' );
                echo '<input type="password" class="regular-text" name="' . esc_attr( $new_name ) . '" value="" autocomplete="new-password" data-lpignore="true" data-1p-ignore="true" placeholder="' . esc_attr( $has_key ? 'Key saved. Paste only to replace.' : 'Paste API key' ) . '" />';
                echo '<p class="description">' . esc_html__( 'Leave blank to preserve the saved key. The saved key cannot be overwritten by an empty password field. Paste a new key only when replacing it.', 'sustainable-catalyst-research-librarian-ai' ) . '</p>';
                if ( $has_key ) {
                    echo '<p class="description"><strong>' . esc_html__( 'Saved key:', 'sustainable-catalyst-research-librarian-ai' ) . '</strong> ' . esc_html( 'length ' . $fp['length'] . ' · ending ' . $fp['last4'] . ' · fingerprint ' . $fp['hash8'] ) . '</p>';
                    echo '<label><input type="checkbox" name="' . esc_attr( $clear_name ) . '" value="1" /> ' . esc_html__( 'Clear saved key on next save', 'sustainable-catalyst-research-librarian-ai' ) . '</label>';
                }
                break;
            case 'embedding_resume_existing':
                echo '<label><input type="checkbox" name="' . esc_attr( $name ) . '" value="1" ' . checked( $options[ $field ], '1', false ) . ' /> ' . esc_html__( 'Skip records that already have embeddings for the selected model. Recommended.', 'sustainable-catalyst-research-librarian-ai' ) . '</label>';
                echo '<p class="description">' . esc_html__( 'This makes the embedding job resumable and prevents a later failure from destroying existing semantic coverage.', 'sustainable-catalyst-research-librarian-ai' ) . '</p>';
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
            case 'embedding_source_limit':
            case 'embedding_output_dimensionality':
            case 'embedding_retry_limit':
            case 'embedding_batch_delay_ms':
            case 'embedding_retry_after_seconds':
            case 'eval_high_confidence_threshold':
            case 'eval_medium_confidence_threshold':
            case 'evaluation_min_source_count':
            case 'evaluation_log_limit':
            case 'handoff_log_limit':
            case 'session_log_limit':
                echo '<input type="number" class="small-text" name="' . esc_attr( $name ) . '" value="' . esc_attr( $options[ $field ] ) . '" />';
                if ( 'embedding_output_dimensionality' === $field ) { echo '<p class="description">' . esc_html__( 'Use 0 for the model default. Set only if you want reduced dimensions.', 'sustainable-catalyst-research-librarian-ai' ) . '</p>'; }
                if ( 'embedding_retry_limit' === $field ) { echo '<p class="description">' . esc_html__( 'Stops early after this many consecutive failures when no records embed, so diagnostics return quickly.', 'sustainable-catalyst-research-librarian-ai' ) . '</p>'; }
                if ( 'embedding_batch_delay_ms' === $field ) { echo '<p class="description">' . esc_html__( 'Pause between Gemini embedding requests. Use 1000–2500ms for free-tier stability.', 'sustainable-catalyst-research-librarian-ai' ) . '</p>'; }
                if ( 'embedding_retry_after_seconds' === $field ) { echo '<p class="description">' . esc_html__( 'When Gemini returns a rate-limit or temporary server error, wait this many seconds before one retry.', 'sustainable-catalyst-research-librarian-ai' ) . '</p>'; }
                break;
            case 'temperature':
            case 'semantic_weight':
            case 'keyword_weight':
                echo '<input type="number" step="0.05" min="0" max="1" class="small-text" name="' . esc_attr( $name ) . '" value="' . esc_attr( $options[ $field ] ) . '" />';
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
        $retrieval = $this->retrieval_status();
        $embedding_notice = get_transient( 'sc_rl_ai_admin_notice' );
        if ( $embedding_notice ) { delete_transient( 'sc_rl_ai_admin_notice' ); }
        $embedding_success_notice = get_transient( 'sc_rl_ai_admin_success_notice' );
        if ( $embedding_success_notice ) { delete_transient( 'sc_rl_ai_admin_success_notice' ); }
        $diagnostics = $this->embedding_diagnostics();
        $evaluation = $this->evaluation_summary();
        $evaluation_summary = isset( $evaluation['summary'] ) ? $evaluation['summary'] : $this->evaluation_summary_defaults();
        $evaluation_status = get_option( self::EVAL_OPTION, array() );
        $evaluation_results = isset( $evaluation_status['results'] ) && is_array( $evaluation_status['results'] ) ? $evaluation_status['results'] : array();
        $session_summary = $this->session_analytics_summary();
        $session_logs = $this->session_logs();
        $feedback_summary = $this->feedback_summary();
        $feedback_logs = $this->feedback_logs();
        $notice_label = '';
        if ( $notice ) {
            if ( 'rebuilt' === $notice ) { $notice_label = 'Knowledge index rebuilt.'; }
            elseif ( 'embedded' === $notice ) { $notice_label = 'Gemini embeddings generated for indexed records.'; }
            elseif ( 'test-embedding-ok' === $notice ) { $notice_label = 'Single Gemini embedding test passed.'; }
            elseif ( 'evaluation-run' === $notice ) { $notice_label = 'Retrieval evaluation suite completed.'; }
            elseif ( 'evaluation-cleared' === $notice ) { $notice_label = 'Evaluation logs cleared.'; }
            elseif ( 'sessions-cleared' === $notice ) { $notice_label = 'Saved route sessions cleared.'; }
            elseif ( 'feedback-cleared' === $notice ) { $notice_label = 'Feedback and triage logs cleared.'; }
            else { $notice_label = 'Knowledge index reset to seed records.'; }
        }
        ?>
        <div class="wrap">
            <h1><?php esc_html_e( 'Sustainable Catalyst Research Librarian', 'sustainable-catalyst-research-librarian-ai' ); ?></h1>
            <p><?php esc_html_e( 'Routing and retrieval infrastructure for Sustainable Catalyst. It helps visitors choose the right library, module, demo, repository, Workbench tool, or Decision Studio workflow.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
            <p><strong><?php esc_html_e( 'Status:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( 'disabled' === $provider ? 'Deterministic fallback only' : 'AI provider configured: ' . $provider ); ?> · <strong><?php esc_html_e( 'Version:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( self::VERSION ); ?></p>
            <?php if ( $notice && 'embedding-error' !== $notice ) : ?>
                <div class="notice notice-success is-dismissible"><p><?php echo esc_html( $notice_label ); ?></p></div>
            <?php endif; ?>
            <?php if ( $embedding_success_notice ) : ?>
                <div class="notice notice-success is-dismissible"><p><?php echo esc_html( $embedding_success_notice ); ?></p></div>
            <?php endif; ?>
            <?php if ( $embedding_notice ) : ?>
                <div class="notice notice-error is-dismissible"><p><?php echo esc_html( $embedding_notice ); ?></p></div>
            <?php endif; ?>

            <h2><?php esc_html_e( 'Knowledge Indexer and Crawl Dashboard', 'sustainable-catalyst-research-librarian-ai' ); ?></h2>
            <p><?php esc_html_e( 'The indexer combines curated source records with recently published WordPress pages/posts. It tracks source coverage, metadata gaps, stale records, duplicate URLs, and route groups for grounded routing.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
            <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:16px 0;max-width:1100px;">
                <div class="postbox" style="padding:14px;"><strong style="font-size:22px;display:block;"><?php echo esc_html( $summary['total_records'] ); ?></strong><span><?php esc_html_e( 'Indexed records', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                <div class="postbox" style="padding:14px;"><strong style="font-size:22px;display:block;"><?php echo esc_html( $summary['route_count'] ); ?></strong><span><?php esc_html_e( 'Route groups', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                <div class="postbox" style="padding:14px;"><strong style="font-size:22px;display:block;"><?php echo esc_html( $summary['metadata_warnings'] ); ?></strong><span><?php esc_html_e( 'Metadata warnings', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                <div class="postbox" style="padding:14px;"><strong style="font-size:22px;display:block;"><?php echo esc_html( $summary['stale_records'] ); ?></strong><span><?php esc_html_e( 'Stale records', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                <div class="postbox" style="padding:14px;"><strong style="font-size:22px;display:block;"><?php echo esc_html( $retrieval['embedded_records'] ); ?></strong><span><?php esc_html_e( 'Embedded records', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
            </div>
            <p><strong><?php esc_html_e( 'Last indexed:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( isset( $index['last_indexed_utc'] ) ? $index['last_indexed_utc'] : 'seed only' ); ?> · <strong><?php esc_html_e( 'Mode:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( isset( $index['crawl_mode'] ) ? $index['crawl_mode'] : 'unknown' ); ?> · <strong><?php esc_html_e( 'Retrieval:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( $retrieval['enabled'] ? 'Gemini hybrid semantic retrieval enabled' : 'Keyword/source retrieval only' ); ?> · <strong><?php esc_html_e( 'Last embedding run:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( $retrieval['last_embedding_utc'] ? $retrieval['last_embedding_utc'] : 'not generated' ); ?></p>
            <form method="post" style="display:flex;gap:10px;flex-wrap:wrap;margin:12px 0 22px;">
                <?php wp_nonce_field( 'sc_rl_index_action', 'sc_rl_index_nonce' ); ?>
                <button class="button button-primary" type="submit" name="sc_rl_index_action" value="rebuild"><?php esc_html_e( 'Rebuild Knowledge Index', 'sustainable-catalyst-research-librarian-ai' ); ?></button>
                <button class="button" type="submit" name="sc_rl_index_action" value="test_embedding"><?php esc_html_e( 'Test Single Gemini Embedding', 'sustainable-catalyst-research-librarian-ai' ); ?></button>
                <button class="button" type="submit" name="sc_rl_index_action" value="embed"><?php esc_html_e( 'Generate Gemini Embeddings', 'sustainable-catalyst-research-librarian-ai' ); ?></button>
                <button class="button" type="submit" name="sc_rl_index_action" value="reset"><?php esc_html_e( 'Reset to Seed Index', 'sustainable-catalyst-research-librarian-ai' ); ?></button>
                <a class="button" href="<?php echo esc_url( rest_url( self::REST_NAMESPACE . '/index/export' ) ); ?>"><?php esc_html_e( 'Export Index JSON', 'sustainable-catalyst-research-librarian-ai' ); ?></a>
                <a class="button" href="<?php echo esc_url( rest_url( self::REST_NAMESPACE . '/retrieval/diagnostics' ) ); ?>"><?php esc_html_e( 'Embedding Diagnostics JSON', 'sustainable-catalyst-research-librarian-ai' ); ?></a>
                <button class="button" type="submit" name="sc_rl_index_action" value="run_evaluation"><?php esc_html_e( 'Run Retrieval Evaluation', 'sustainable-catalyst-research-librarian-ai' ); ?></button>
                <button class="button" type="submit" name="sc_rl_index_action" value="clear_evaluation"><?php esc_html_e( 'Clear Evaluation Logs', 'sustainable-catalyst-research-librarian-ai' ); ?></button>
                <a class="button" href="<?php echo esc_url( rest_url( self::REST_NAMESPACE . '/evaluation/export' ) ); ?>"><?php esc_html_e( 'Export Evaluation JSON', 'sustainable-catalyst-research-librarian-ai' ); ?></a>
                <a class="button" href="<?php echo esc_url( rest_url( self::REST_NAMESPACE . '/session/export' ) ); ?>"><?php esc_html_e( 'Export Session Analytics JSON', 'sustainable-catalyst-research-librarian-ai' ); ?></a>
                <button class="button" type="submit" name="sc_rl_index_action" value="clear_sessions"><?php esc_html_e( 'Clear Saved Sessions', 'sustainable-catalyst-research-librarian-ai' ); ?></button>
                <a class="button" href="<?php echo esc_url( rest_url( self::REST_NAMESPACE . '/feedback/export' ) ); ?>"><?php esc_html_e( 'Export Feedback JSON', 'sustainable-catalyst-research-librarian-ai' ); ?></a>
                <button class="button" type="submit" name="sc_rl_index_action" value="clear_feedback"><?php esc_html_e( 'Clear Feedback Logs', 'sustainable-catalyst-research-librarian-ai' ); ?></button>
                <a class="button" href="<?php echo esc_url( rest_url( self::REST_NAMESPACE . '/governance/export' ) ); ?>"><?php esc_html_e( 'Export Governance JSON', 'sustainable-catalyst-research-librarian-ai' ); ?></a>
            </form>

            <div class="postbox" style="padding:14px;max-width:1100px;margin:12px 0 22px;">
                <h2 style="margin-top:0;"><?php esc_html_e( 'Gemini Embedding Diagnostics', 'sustainable-catalyst-research-librarian-ai' ); ?></h2>
                <p><strong><?php esc_html_e( 'Model:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <code><?php echo esc_html( $diagnostics['request_model'] ); ?></code> · <strong><?php esc_html_e( 'HTTP:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( $diagnostics['last_http_status'] ? $diagnostics['last_http_status'] : 'n/a' ); ?> · <strong><?php esc_html_e( 'Last error code:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <code><?php echo esc_html( $diagnostics['last_error_code'] ? $diagnostics['last_error_code'] : 'none' ); ?></code></p>
                <?php $fp = isset( $diagnostics['api_key_fingerprint'] ) && is_array( $diagnostics['api_key_fingerprint'] ) ? $diagnostics['api_key_fingerprint'] : array(); ?>
                <p><strong><?php esc_html_e( 'Saved key check:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo ! empty( $fp['present'] ) ? esc_html( 'present · length ' . $fp['length'] . ' · ending ' . $fp['last4'] . ' · fingerprint ' . $fp['hash8'] ) : esc_html__( 'not saved', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
                <?php $used_fp = isset( $diagnostics['api_key_fingerprint_used'] ) && is_array( $diagnostics['api_key_fingerprint_used'] ) ? $diagnostics['api_key_fingerprint_used'] : array(); ?>
                <?php if ( ! empty( $used_fp['present'] ) ) : ?>
                    <p><strong><?php esc_html_e( 'Last run used key:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( 'length ' . $used_fp['length'] . ' · ending ' . $used_fp['last4'] . ' · fingerprint ' . $used_fp['hash8'] ); ?><?php echo ! empty( $diagnostics['api_key_fingerprint_changed_since_last_run'] ) ? esc_html__( ' · changed since last run', 'sustainable-catalyst-research-librarian-ai' ) : ''; ?></p>
                <?php endif; ?>
                <?php if ( ! empty( $diagnostics['last_error'] ) ) : ?>
                    <p><strong><?php esc_html_e( 'Last error:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( $diagnostics['last_error'] ); ?></p>
                    <p><strong><?php esc_html_e( 'Recommended next step:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( $diagnostics['recommended_next_step'] ); ?></p>
                <?php else : ?>
                    <p><?php esc_html_e( 'No embedding error is currently stored. Use Test Single Gemini Embedding before a full embedding run if you are diagnosing setup.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
                <?php endif; ?>
                <?php if ( ! empty( $diagnostics['raw_response_excerpt'] ) ) : ?>
                    <details><summary><?php esc_html_e( 'Raw response excerpt', 'sustainable-catalyst-research-librarian-ai' ); ?></summary><pre style="white-space:pre-wrap;max-height:180px;overflow:auto;"><?php echo esc_html( $diagnostics['raw_response_excerpt'] ); ?></pre></details>
                <?php endif; ?>
            </div>


            <div class="postbox" style="padding:14px;max-width:1100px;margin:12px 0 22px;">
                <h2 style="margin-top:0;"><?php esc_html_e( 'Retrieval Evaluation, Confidence, and Failure Logs', 'sustainable-catalyst-research-librarian-ai' ); ?></h2>
                <p><?php esc_html_e( 'Run the evaluation suite after rebuilding the index or generating embeddings. It checks expected route matches, confidence levels, source coverage, and keyword/semantic score behavior.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
                <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:12px 0;">
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( absint( $evaluation_summary['total_cases'] ) ); ?></strong><span><?php esc_html_e( 'Cases', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( $evaluation_summary['accuracy'] ); ?>%</strong><span><?php esc_html_e( 'Accuracy', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( absint( $evaluation_summary['low_confidence'] ) ); ?></strong><span><?php esc_html_e( 'Low confidence', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( absint( $evaluation_summary['weak_source_matches'] ) ); ?></strong><span><?php esc_html_e( 'Weak sources', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( $evaluation_summary['last_quality_label'] ); ?></strong><span><?php esc_html_e( 'Quality label', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                </div>
                <p><strong><?php esc_html_e( 'Last evaluation:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( ! empty( $evaluation['last_run_utc'] ) ? $evaluation['last_run_utc'] : 'not run yet' ); ?></p>
                <?php if ( ! empty( $evaluation_results ) ) : ?>
                    <table class="widefat striped"><thead><tr><th><?php esc_html_e( 'Case', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Expected', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Recommended', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Confidence', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Top source scores', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Quality', 'sustainable-catalyst-research-librarian-ai' ); ?></th></tr></thead><tbody>
                    <?php foreach ( array_slice( $evaluation_results, 0, 20 ) as $result ) : ?>
                        <tr><td><?php echo esc_html( $result['case_id'] ); ?></td><td><code><?php echo esc_html( implode( ', ', $result['expected_routes'] ) ); ?></code></td><td><code><?php echo esc_html( $result['recommended_route']['id'] ); ?></code></td><td><?php echo esc_html( ( $result['confidence']['level'] ?? 'low' ) . ' / ' . ( $result['confidence']['score'] ?? 0 ) ); ?></td><td><?php echo esc_html( 'keyword ' . ( $result['top_source']['keyword_score'] ?? 0 ) . ' · semantic ' . ( $result['top_source']['semantic_score'] ?? 0 ) . ' · score ' . ( $result['top_source']['score'] ?? 0 ) ); ?></td><td><?php echo esc_html( $result['quality_label'] ); ?></td></tr>
                    <?php endforeach; ?>
                    </tbody></table>
                <?php else : ?>
                    <p><?php esc_html_e( 'No evaluation run has been stored yet. Click Run Retrieval Evaluation after embeddings are generated.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
                <?php endif; ?>
            </div>



            <div class="postbox" style="padding:14px;max-width:1100px;margin:12px 0 22px;">
                <h2 style="margin-top:0;"><?php esc_html_e( 'Feedback, Correction Queue, and Knowledge Gap Triage', 'sustainable-catalyst-research-librarian-ai' ); ?></h2>
                <p><?php esc_html_e( 'Feedback records collect helpful-route signals, wrong-route reports, missing-source notes, knowledge gaps, and feature gaps. Use this queue to tune the route map, improve source metadata, add missing pages, or turn repeated gaps into Feature Suggestions.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
                <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:12px 0;">
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( absint( $feedback_summary['total_feedback'] ) ); ?></strong><span><?php esc_html_e( 'Feedback records', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( absint( $feedback_summary['helpful_count'] ) ); ?></strong><span><?php esc_html_e( 'Helpful marks', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( absint( $feedback_summary['issue_count'] ) ); ?></strong><span><?php esc_html_e( 'Issues', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( absint( $feedback_summary['knowledge_gap_count'] ) ); ?></strong><span><?php esc_html_e( 'Knowledge gaps', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( $feedback_summary['top_route']['id'] ); ?></strong><span><?php esc_html_e( 'Top route', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                </div>
                <p><strong><?php esc_html_e( 'Last feedback:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( $feedback_summary['last_feedback_utc'] ? $feedback_summary['last_feedback_utc'] : 'none' ); ?></p>
                <?php if ( ! empty( $feedback_logs ) ) : ?>
                    <table class="widefat striped"><thead><tr><th><?php esc_html_e( 'Received', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Type', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Triage', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Route', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Confidence', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Question / note', 'sustainable-catalyst-research-librarian-ai' ); ?></th></tr></thead><tbody>
                    <?php foreach ( array_slice( $feedback_logs, 0, 12 ) as $feedback ) : ?>
                        <tr><td><?php echo esc_html( $feedback['created_at_utc'] ?? '' ); ?></td><td><code><?php echo esc_html( $feedback['type'] ?? '' ); ?></code></td><td><code><?php echo esc_html( $feedback['triage_label'] ?? '' ); ?></code></td><td><code><?php echo esc_html( $feedback['route_id'] ?? '' ); ?></code></td><td><?php echo esc_html( ( $feedback['confidence_level'] ?? 'unknown' ) . ' / ' . ( $feedback['confidence_score'] ?? 0 ) ); ?></td><td><?php echo esc_html( wp_trim_words( trim( ( $feedback['question'] ?? '' ) . ' ' . ( $feedback['note'] ?? '' ) ), 22 ) ); ?></td></tr>
                    <?php endforeach; ?>
                    </tbody></table>
                <?php else : ?>
                    <p><?php esc_html_e( 'No feedback has been saved yet. Use This helped or Report issue from the assistant UI after a route answer is generated.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
                <?php endif; ?>
            </div>

            <div class="postbox" style="padding:14px;max-width:1100px;margin:12px 0 22px;">
                <h2 style="margin-top:0;"><?php esc_html_e( 'Saved Route Sessions and Admin Analytics', 'sustainable-catalyst-research-librarian-ai' ); ?></h2>
                <p><?php esc_html_e( 'Saved sessions preserve useful Research Librarian route notes for review. The analytics summary shows common routes, handoff targets, confidence distribution, and recent activity.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
                <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:12px 0;">
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( absint( $session_summary['total_sessions'] ) ); ?></strong><span><?php esc_html_e( 'Saved sessions', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( absint( $session_summary['unique_routes'] ) ); ?></strong><span><?php esc_html_e( 'Routes used', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( absint( $session_summary['unique_targets'] ) ); ?></strong><span><?php esc_html_e( 'Handoff targets', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( $session_summary['top_route']['label'] ); ?></strong><span><?php esc_html_e( 'Top route', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( $session_summary['top_target']['label'] ); ?></strong><span><?php esc_html_e( 'Top target', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                </div>
                <p><strong><?php esc_html_e( 'Last saved:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo esc_html( $session_summary['last_saved_utc'] ? $session_summary['last_saved_utc'] : 'none' ); ?></p>
                <?php if ( ! empty( $session_logs ) ) : ?>
                    <table class="widefat striped"><thead><tr><th><?php esc_html_e( 'Saved', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Route', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Handoff', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Confidence', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Question', 'sustainable-catalyst-research-librarian-ai' ); ?></th></tr></thead><tbody>
                    <?php foreach ( array_slice( $session_logs, 0, 12 ) as $session ) : ?>
                        <tr><td><?php echo esc_html( $session['created_at_utc'] ?? '' ); ?></td><td><code><?php echo esc_html( $session['route_id'] ?? '' ); ?></code></td><td><code><?php echo esc_html( $session['handoff_target'] ?? '' ); ?></code></td><td><?php echo esc_html( ( $session['confidence_level'] ?? 'unknown' ) . ' / ' . ( $session['confidence_score'] ?? 0 ) ); ?></td><td><?php echo esc_html( wp_trim_words( $session['question'] ?? '', 18 ) ); ?></td></tr>
                    <?php endforeach; ?>
                    </tbody></table>
                <?php else : ?>
                    <p><?php esc_html_e( 'No sessions have been saved yet. Ask the public assistant a route question and click Save session.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
                <?php endif; ?>
            </div>

            <div class="postbox" style="padding:14px;max-width:1100px;margin:12px 0 22px;">
                <h2 style="margin-top:0;"><?php esc_html_e( 'Governance, Privacy, and Retention', 'sustainable-catalyst-research-librarian-ai' ); ?></h2>
                <?php $governance = $this->governance_summary(); ?>
                <p><?php esc_html_e( 'This layer summarizes retention targets, log counts, export boundaries, public summary status, and privacy posture for route sessions, feedback, handoffs, evaluation, and retrieval diagnostics.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
                <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:12px 0;">
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( absint( $governance['retention_days']['sessions'] ) ); ?></strong><span><?php esc_html_e( 'Session retention days', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( absint( $governance['retention_days']['feedback'] ) ); ?></strong><span><?php esc_html_e( 'Feedback retention days', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( $governance['redact_questions_in_exports'] ? 'on' : 'off' ); ?></strong><span><?php esc_html_e( 'Export redaction', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                    <div class="postbox" style="padding:10px;"><strong style="font-size:20px;display:block;"><?php echo esc_html( $governance['last_purge_utc'] ? $governance['last_purge_utc'] : 'none' ); ?></strong><span><?php esc_html_e( 'Last purge', 'sustainable-catalyst-research-librarian-ai' ); ?></span></div>
                </div>
                <p><a class="button" href="<?php echo esc_url( rest_url( self::REST_NAMESPACE . '/governance/status' ) ); ?>"><?php esc_html_e( 'View Governance Status JSON', 'sustainable-catalyst-research-librarian-ai' ); ?></a> <a class="button" href="<?php echo esc_url( rest_url( self::REST_NAMESPACE . '/governance/export' ) ); ?>"><?php esc_html_e( 'Export Governance JSON', 'sustainable-catalyst-research-librarian-ai' ); ?></a></p>
            </div>

            <form action="options.php" method="post">
                <?php settings_fields( 'sc_rl_ai_settings_group' ); do_settings_sections( 'sc-research-librarian-ai' ); submit_button(); ?>
            </form>
            <hr />
            <h2><?php esc_html_e( 'Indexed Source Records', 'sustainable-catalyst-research-librarian-ai' ); ?></h2>
            <p><?php esc_html_e( 'Records used for deterministic grounded routing and AI prompt context. Rebuild the index after major page, module, or navigation updates.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
            <table class="widefat striped"><thead><tr><th><?php esc_html_e( 'Type', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Source', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Route', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Flags', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'Embedding', 'sustainable-catalyst-research-librarian-ai' ); ?></th><th><?php esc_html_e( 'URL', 'sustainable-catalyst-research-librarian-ai' ); ?></th></tr></thead><tbody>
            <?php foreach ( array_slice( $records, 0, 120 ) as $source ) : ?>
                <tr><td><?php echo esc_html( $source['type'] ); ?></td><td><?php echo esc_html( $source['title'] ); ?></td><td><code><?php echo esc_html( $source['route_id'] ); ?></code></td><td><?php echo esc_html( empty( $source['metadata_flags'] ) ? 'ok' : implode( ', ', $source['metadata_flags'] ) ); ?></td><td><?php echo esc_html( ! empty( $source['embedding'] ) && is_array( $source['embedding'] ) ? 'embedded' : 'none' ); ?></td><td><code><?php echo esc_html( $source['url'] ); ?></code></td></tr>
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
