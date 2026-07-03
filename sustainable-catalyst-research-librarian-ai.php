<?php
/**
 * Plugin Name: Sustainable Catalyst Research Librarian AI
 * Plugin URI: https://sustainablecatalyst.com/platform/research-librarian/
 * Description: AI-enabled Sustainable Catalyst Research Librarian with OpenAI file search, server-side REST endpoint, admin settings, strict boundaries, and deterministic fallback routing.
 * Version: 2.1.1
 * Author: Content Catalyst LLC / Tariq Ahmad
 * Author URI: https://sustainablecatalyst.com/
 * License: GPL-2.0-or-later
 * Text Domain: sustainable-catalyst-research-librarian-ai
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class Sustainable_Catalyst_Research_Librarian_AI {
    const OPTION_NAME = 'sc_rl_ai_options';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';
    const REST_ROUTE = '/ask';
    const VERSION = '2.1.1';

    private static $instance = null;

    public static function instance() {
        if ( null === self::$instance ) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        add_action( 'init', array( $this, 'register_shortcode' ) );
        add_action( 'rest_api_init', array( $this, 'register_rest_routes' ) );
        add_action( 'admin_menu', array( $this, 'register_admin_page' ) );
        add_action( 'admin_init', array( $this, 'register_settings' ) );
        add_filter( 'plugin_action_links_' . plugin_basename( __FILE__ ), array( $this, 'add_settings_link' ) );
        add_action( 'admin_post_sc_rl_ai_upload_knowledge_base', array( $this, 'handle_knowledge_base_upload' ) );
        add_action( 'admin_notices', array( $this, 'render_admin_notices' ) );
    }

    public static function activate() {
        $existing = get_option( self::OPTION_NAME, array() );
        update_option( self::OPTION_NAME, wp_parse_args( $existing, self::defaults() ), false );
    }

    public static function defaults() {
        return array(
            'api_key'                 => '',
            'model'                   => 'gpt-5.5',
            'vector_store_id'         => '',
            'max_file_search_results' => 6,
            'max_output_tokens'       => 850,
            'rate_limit'              => 10,
            'system_instructions'     => self::default_system_instructions(),
        );
    }

    public static function default_system_instructions() {
        return "You are the Sustainable Catalyst Research Librarian, an AI-enabled guide for Sustainable Catalyst, an open knowledge lab by Tariq Ahmad / Content Catalyst.\n\nYour purpose is to help visitors identify what they are trying to do, recommend the best Sustainable Catalyst starting point, explain why, provide relevant links, and suggest related routes.\n\nUse Sustainable Catalyst knowledge-base material when available. If the knowledge base is incomplete or a requested feature does not exist, say so plainly and route the visitor to /platform/feature-suggestions/. Do not invent pages, claims, credentials, certifications, client results, or services.\n\nStrict boundaries:\n- Do not provide legal advice.\n- Do not provide financial or investment advice.\n- Do not provide medical or mental health advice.\n- Do not provide tax advice.\n- Do not provide compliance opinions, assurance, audit findings, or certification.\n- Do not claim ESG, SDG, sustainability, or regulatory certification.\n- Do not request, process, or invite confidential, regulated, personal, proprietary, legal, medical, tax, or financial information.\n\nWhen a boundary is relevant, briefly state the boundary and redirect to educational, non-advisory Sustainable Catalyst resources.\n\nPreferred answer shape:\n1. What you seem to be trying to do\n2. Best starting point\n3. Why this route fits\n4. Relevant links\n5. Related next steps\n\nKeep answers concise, practical, and route-oriented. Use Markdown links. Use an institutional, calm, research-librarian tone.";
    }

    private function get_options() {
        return wp_parse_args( get_option( self::OPTION_NAME, array() ), self::defaults() );
    }

    public function add_settings_link( $links ) {
        $url = admin_url( 'options-general.php?page=sc-research-librarian-ai' );
        $links[] = '<a href="' . esc_url( $url ) . '">' . esc_html__( 'Settings', 'sustainable-catalyst-research-librarian-ai' ) . '</a>';
        return $links;
    }

    public function register_shortcode() {
        add_shortcode( 'sustainable_catalyst_research_librarian_ai', array( $this, 'render_shortcode' ) );
    }

    public function render_shortcode( $atts = array() ) {
        wp_enqueue_style(
            'sc-research-librarian-ai',
            plugins_url( 'assets/sc-research-librarian-ai.css', __FILE__ ),
            array(),
            self::VERSION
        );

        wp_enqueue_script(
            'sc-research-librarian-ai',
            plugins_url( 'assets/sc-research-librarian-ai.js', __FILE__ ),
            array(),
            self::VERSION,
            true
        );

        $root_id = wp_unique_id( 'sc-rl-ai-' );
        $endpoint = rest_url( self::REST_NAMESPACE . self::REST_ROUTE );
        $nonce = wp_create_nonce( 'wp_rest' );

        ob_start();
        ?>
        <section id="<?php echo esc_attr( $root_id ); ?>" class="sc-rl-ai" data-endpoint="<?php echo esc_url( $endpoint ); ?>" data-nonce="<?php echo esc_attr( $nonce ); ?>">
            <div class="sc-rl-ai__grid">
                <div class="sc-rl-ai__card sc-rl-ai__ask-card">
                    <p class="sc-rl-ai__eyebrow">Sustainable Catalyst Research Librarian</p>
                    <h2 class="sc-rl-ai__title">Find the right starting point.</h2>
                    <p class="sc-rl-ai__intro">Ask a question about Sustainable Catalyst, the platform modules, article libraries, demos, methodology, support, or where to send a new feature idea.</p>

                    <label class="sc-rl-ai__label" for="<?php echo esc_attr( $root_id ); ?>-question">Your question</label>
                    <textarea class="sc-rl-ai__textarea" id="<?php echo esc_attr( $root_id ); ?>-question" rows="5" maxlength="1200" placeholder="Example: Which Catalyst demo should I start with if I want to organize research into a reusable system?"></textarea>
                    <input type="text" class="sc-rl-ai__hp" value="" tabindex="-1" autocomplete="off" aria-hidden="true" />

                    <div class="sc-rl-ai__actions">
                        <button type="button" class="sc-rl-ai__button sc-rl-ai__button--primary" data-sc-rl-submit>Ask the Librarian</button>
                        <button type="button" class="sc-rl-ai__button sc-rl-ai__button--secondary" data-sc-rl-clear>Clear</button>
                    </div>

                    <div class="sc-rl-ai__examples" aria-label="Example questions">
                        <button type="button" data-sc-rl-example="Where should I start if I am new to Sustainable Catalyst?">New visitor</button>
                        <button type="button" data-sc-rl-example="Which demo helps me organize research into a reusable system?">Research system</button>
                        <button type="button" data-sc-rl-example="Where should I go for SDG-oriented impact analysis?">Impact analysis</button>
                        <button type="button" data-sc-rl-example="Which module helps with narrative risk, trust, and institutional communication?">Narrative risk</button>
                        <button type="button" data-sc-rl-example="I have an idea for a feature that does not exist yet. Where should I send it?">Feature idea</button>
                    </div>
                </div>

                <div class="sc-rl-ai__card sc-rl-ai__answer-card" aria-live="polite">
                    <div class="sc-rl-ai__answer-header">
                        <p class="sc-rl-ai__eyebrow">Answer</p>
                        <span class="sc-rl-ai__status" data-sc-rl-status>Ready</span>
                    </div>
                    <div class="sc-rl-ai__answer" data-sc-rl-answer>
                        <p>Ask a question or choose an example. The librarian will recommend a route, explain why it fits, and suggest next steps.</p>
                    </div>
                    <div class="sc-rl-ai__boundary-note">
                        Educational routing only. No legal, financial, medical, tax, compliance, ESG/SDG certification, or regulated-information advice.
                    </div>
                </div>
            </div>
        </section>
        <?php
        return ob_get_clean();
    }

    public function register_rest_routes() {
        register_rest_route(
            self::REST_NAMESPACE,
            self::REST_ROUTE,
            array(
                'methods'             => WP_REST_Server::CREATABLE,
                'callback'            => array( $this, 'handle_ask_request' ),
                'permission_callback' => '__return_true',
                'args'                => array(
                    'question' => array(
                        'required'          => true,
                        'type'              => 'string',
                        'sanitize_callback' => 'sanitize_textarea_field',
                    ),
                ),
            )
        );
    }

    public function handle_ask_request( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'x_wp_nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_ai_bad_nonce', __( 'Security check failed. Refresh the page and try again.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 403 ) );
        }

        $params = $request->get_json_params();
        $honeypot = isset( $params['hp'] ) ? sanitize_text_field( wp_unslash( $params['hp'] ) ) : '';
        if ( '' !== $honeypot ) {
            return new WP_REST_Response(
                array(
                    'answer' => $this->fallback_response( 'general' ),
                    'source' => 'fallback',
                ),
                200
            );
        }

        $question = isset( $params['question'] ) ? sanitize_textarea_field( wp_unslash( $params['question'] ) ) : '';
        $question = trim( preg_replace( '/\s+/', ' ', $question ) );

        if ( '' === $question ) {
            return new WP_Error( 'sc_rl_ai_empty_question', __( 'Please enter a question.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 400 ) );
        }

        if ( strlen( $question ) > 1200 ) {
            return new WP_Error( 'sc_rl_ai_question_too_long', __( 'Please keep the question under 1,200 characters.', 'sustainable-catalyst-research-librarian-ai' ), array( 'status' => 400 ) );
        }

        $options = $this->get_options();
        $rate_check = $this->check_rate_limit( absint( $options['rate_limit'] ) );
        if ( is_wp_error( $rate_check ) ) {
            return $rate_check;
        }

        $boundary = $this->boundary_response_if_needed( $question );
        if ( $boundary ) {
            return new WP_REST_Response(
                array(
                    'answer' => $boundary,
                    'source' => 'boundary',
                ),
                200
            );
        }

        $has_ai = ! empty( $options['api_key'] ) && ! empty( $options['model'] );
        if ( ! $has_ai ) {
            return new WP_REST_Response(
                array(
                    'answer' => $this->fallback_response( $question ),
                    'source' => 'fallback',
                ),
                200
            );
        }

        $ai_answer = $this->call_openai( $question, $options );
        if ( is_wp_error( $ai_answer ) ) {
            return new WP_REST_Response(
                array(
                    'answer' => "The AI route is temporarily unavailable, so I am using the deterministic route system.\n\n" . $this->fallback_response( $question ),
                    'source' => 'fallback',
                    'error'  => $ai_answer->get_error_message(),
                ),
                200
            );
        }

        return new WP_REST_Response(
            array(
                'answer' => $ai_answer,
                'source' => ! empty( $options['vector_store_id'] ) ? 'ai_file_search' : 'ai',
            ),
            200
        );
    }

    private function check_rate_limit( $limit ) {
        $limit = max( 1, min( 100, $limit ? $limit : 10 ) );
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
        $candidates = array(
            'HTTP_CF_CONNECTING_IP',
            'HTTP_X_FORWARDED_FOR',
            'REMOTE_ADDR',
        );

        foreach ( $candidates as $key ) {
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
            'legal'      => array( '/\b(can i sue|lawsuit|legal advice|is it legal|contract dispute|liable|liability|attorney|lawyer)\b/' ),
            'financial'  => array( '/\b(should i invest|buy stock|sell stock|investment advice|portfolio allocation|financial advice|retirement account|crypto trade)\b/' ),
            'medical'    => array( '/\b(diagnose|diagnosis|treatment plan|medication|mental health advice|therapy advice|self-harm|suicidal)\b/' ),
            'tax'        => array( '/\b(tax advice|tax deduction|tax return|irs|hmrc|revenue service|tax liability)\b/' ),
            'compliance' => array( '/\b(certify|certification|assurance|audit opinion|compliance opinion|regulatory approval|esg certification|sdg certification)\b/' ),
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
            'legal'      => 'legal advice',
            'financial'  => 'financial or investment advice',
            'medical'    => 'medical or mental health advice',
            'tax'        => 'tax advice',
            'compliance' => 'compliance, assurance, or ESG/SDG certification',
        );

        $label = isset( $labels[ $area ] ) ? $labels[ $area ] : 'professional advice';

        return "I can help with educational routing, but I cannot provide {$label}.\n\n**Best starting point:** [Platform Methodology](/platform/methodology/) if you want to understand how Sustainable Catalyst frames research, evidence, systems thinking, and responsible interpretation.\n\n**Related routes:**\n- [Knowledge Libraries](/knowledge-libraries/) for educational article maps and research context.\n- [Research Librarian](/platform/research-librarian/) for site navigation.\n- [Feature Suggestions](/platform/feature-suggestions/) if you need a capability that does not exist yet.\n\nPlease avoid sharing confidential, regulated, personal, legal, medical, tax, or financial information here.";
    }

    private function call_openai( $question, $options ) {
        $api_key = trim( $options['api_key'] );
        $model = sanitize_text_field( $options['model'] );
        $vector_store_id = sanitize_text_field( $options['vector_store_id'] );
        $max_results = max( 1, min( 20, absint( $options['max_file_search_results'] ) ) );
        $max_output_tokens = max( 150, min( 4000, absint( $options['max_output_tokens'] ) ) );
        $instructions = $this->build_instructions( $options );

        $input = "Visitor question:\n" . $question . "\n\nAnswer as the Sustainable Catalyst Research Librarian. Use Markdown links. Do not request confidential information. If the requested route does not exist, route to /platform/feature-suggestions/.";

        $body = array(
            'model'             => $model,
            'instructions'      => $instructions,
            'input'             => $input,
            'max_output_tokens' => $max_output_tokens,
        );

        if ( '' !== $vector_store_id ) {
            $body['tools'] = array(
                array(
                    'type'             => 'file_search',
                    'vector_store_ids' => array( $vector_store_id ),
                    'max_num_results'  => $max_results,
                ),
            );
        }

        $response = wp_remote_post(
            'https://api.openai.com/v1/responses',
            array(
                'headers' => array(
                    'Authorization' => 'Bearer ' . $api_key,
                    'Content-Type'  => 'application/json',
                ),
                'body'    => wp_json_encode( $body ),
                'timeout' => 30,
            )
        );

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

        $text = $this->extract_response_text( $data );
        if ( '' === trim( $text ) ) {
            return new WP_Error( 'sc_rl_ai_empty_ai_response', __( 'The AI response did not include readable text.', 'sustainable-catalyst-research-librarian-ai' ) );
        }

        return trim( wp_strip_all_tags( $text, false ) );
    }

    private function build_instructions( $options ) {
        $admin_instructions = isset( $options['system_instructions'] ) ? trim( wp_strip_all_tags( $options['system_instructions'] ) ) : '';
        $route_context = "\n\nCore Sustainable Catalyst routes:\n- /platform/\n- /platform/demos/\n- /platform/methodology/\n- /platform/research-librarian/\n- /platform/feature-suggestions/\n- /knowledge-libraries/\n- /publications/\n- /support/\n- /consulting/\n- /contact/\n- https://github.com/Content-Catalyst-LLC\n\nModules:\n- Catalyst Canvas: /catalyst-canvas/#demo ; GitHub catalyst-canvas\n- Catalyst Data: /catalyst-data/#demo ; GitHub catalyst-data\n- Catalyst Analytics R: /catalyst-analytics-r/#demo ; GitHub catalystanalyticsr\n- Global Impact Catalyst: /global-impact-catalyst/#demo ; GitHub global-impact-catalyst\n- Narrative Risk: /narrative-risk/#demo ; GitHub catalyst-narrative-risk\n- Catalyst Finance: /catalyst-finance/#demo ; GitHub catalyst-finance\n- Catalyst Grit: /human-systems/catalyst-grit/#demo ; GitHub catalyst-grit";

        return ( $admin_instructions ? $admin_instructions : self::default_system_instructions() ) . $route_context;
    }

    private function extract_response_text( $data ) {
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

    private function fallback_response( $question ) {
        $q = strtolower( $question );
        $match = $this->match_route( $q );

        $answer = "**What you seem to be trying to do**\n" . $match['intent'] . "\n\n";
        $answer .= "**Best starting point**\n[" . $match['title'] . "](" . $match['url'] . ")\n\n";
        $answer .= "**Why this route fits**\n" . $match['why'] . "\n\n";
        $answer .= "**Related routes**\n";
        foreach ( $match['related'] as $label => $url ) {
            $answer .= "- [" . $label . "](" . $url . ")\n";
        }
        $answer .= "\nIf you are looking for something that does not exist yet, use [Feature Suggestions](/platform/feature-suggestions/).";

        return $answer;
    }

    private function match_route( $q ) {
        $routes = array(
            array(
                'keys'    => array( 'canvas', 'map', 'framework', 'model', 'system map', 'organize research', 'structure research' ),
                'intent'  => 'You are trying to turn research, concepts, or project material into a structured reusable system.',
                'title'   => 'Catalyst Canvas Demo',
                'url'     => '/catalyst-canvas/#demo',
                'why'     => 'Catalyst Canvas is the best starting point for organizing ideas, relationships, assumptions, and interpretive structure before moving into data, analytics, or publication.',
                'related' => array(
                    'Platform Demos' => '/platform/demos/',
                    'Methodology' => '/platform/methodology/',
                    'GitHub: catalyst-canvas' => 'https://github.com/Content-Catalyst-LLC/catalyst-canvas',
                ),
            ),
            array(
                'keys'    => array( 'data', 'dataset', 'csv', 'clean', 'evidence', 'source', 'provenance' ),
                'intent'  => 'You are trying to prepare, structure, or reason about data and evidence.',
                'title'   => 'Catalyst Data Demo',
                'url'     => '/catalyst-data/#demo',
                'why'     => 'Catalyst Data fits questions about source handling, evidence organization, data preparation, and turning raw material into a reusable research workflow.',
                'related' => array(
                    'Platform Demos' => '/platform/demos/',
                    'Knowledge Libraries' => '/knowledge-libraries/',
                    'GitHub: catalyst-data' => 'https://github.com/Content-Catalyst-LLC/catalyst-data',
                ),
            ),
            array(
                'keys'    => array( 'r ', 'analytics r', 'statistics', 'statistical', 'chart', 'visualization', 'regression', 'analysis' ),
                'intent'  => 'You are trying to perform statistical analysis or create an analytical workflow.',
                'title'   => 'Catalyst Analytics R Demo',
                'url'     => '/catalyst-analytics-r/#demo',
                'why'     => 'Catalyst Analytics R is the best fit for R-based analysis, charts, statistical reasoning, and reproducible analytics demos.',
                'related' => array(
                    'Platform Demos' => '/platform/demos/',
                    'Catalyst Data' => '/catalyst-data/#demo',
                    'GitHub: catalystanalyticsr' => 'https://github.com/Content-Catalyst-LLC/catalystanalyticsr',
                ),
            ),
            array(
                'keys'    => array( 'sdg', 'sustainability', 'impact', 'global impact', 'development', 'climate', 'policy' ),
                'intent'  => 'You are trying to explore sustainability, development, SDG-oriented, or impact-analysis material.',
                'title'   => 'Global Impact Catalyst Demo',
                'url'     => '/global-impact-catalyst/#demo',
                'why'     => 'Global Impact Catalyst is the clearest starting point for educational, non-certifying sustainability and global impact analysis.',
                'related' => array(
                    'Methodology' => '/platform/methodology/',
                    'Knowledge Libraries' => '/knowledge-libraries/',
                    'GitHub: global-impact-catalyst' => 'https://github.com/Content-Catalyst-LLC/global-impact-catalyst',
                ),
            ),
            array(
                'keys'    => array( 'narrative risk', 'risk', 'trust', 'misinformation', 'message', 'communication', 'reputation', 'institutional' ),
                'intent'  => 'You are trying to understand narrative, trust, risk, communication, or institutional interpretation.',
                'title'   => 'Narrative Risk Demo',
                'url'     => '/narrative-risk/#demo',
                'why'     => 'Narrative Risk fits questions about how stories, claims, institutions, and public meaning can create or reduce risk.',
                'related' => array(
                    'Platform Methodology' => '/platform/methodology/',
                    'Publications' => '/publications/',
                    'GitHub: catalyst-narrative-risk' => 'https://github.com/Content-Catalyst-LLC/catalyst-narrative-risk',
                ),
            ),
            array(
                'keys'    => array( 'finance', 'budget', 'roi', 'cost', 'scenario', 'market', 'forecast' ),
                'intent'  => 'You are trying to model costs, scenarios, or financial structure at an educational level.',
                'title'   => 'Catalyst Finance Demo',
                'url'     => '/catalyst-finance/#demo',
                'why'     => 'Catalyst Finance is useful for educational scenario modeling and financial structure, but it does not provide investment, tax, or financial advice.',
                'related' => array(
                    'Platform Demos' => '/platform/demos/',
                    'Catalyst Data' => '/catalyst-data/#demo',
                    'GitHub: catalyst-finance' => 'https://github.com/Content-Catalyst-LLC/catalyst-finance',
                ),
            ),
            array(
                'keys'    => array( 'grit', 'resilience', 'habit', 'human systems', 'motivation', 'behavior' ),
                'intent'  => 'You are trying to explore resilience, motivation, habits, or human-systems learning.',
                'title'   => 'Catalyst Grit Demo',
                'url'     => '/human-systems/catalyst-grit/#demo',
                'why'     => 'Catalyst Grit fits human-systems questions about learning, perseverance, behavior, and reflective development.',
                'related' => array(
                    'Platform Demos' => '/platform/demos/',
                    'Knowledge Libraries' => '/knowledge-libraries/',
                    'GitHub: catalyst-grit' => 'https://github.com/Content-Catalyst-LLC/catalyst-grit',
                ),
            ),
            array(
                'keys'    => array( 'demo', 'demos', 'try', 'example', 'tool' ),
                'intent'  => 'You are trying to compare working modules or find a hands-on starting point.',
                'title'   => 'Platform Demos',
                'url'     => '/platform/demos/',
                'why'     => 'The demos page lets you compare the available modules and choose the one that matches your task.',
                'related' => array(
                    'Platform' => '/platform/',
                    'Methodology' => '/platform/methodology/',
                    'Feature Suggestions' => '/platform/feature-suggestions/',
                ),
            ),
            array(
                'keys'    => array( 'library', 'article', 'articles', 'publications', 'research', 'reading', 'learn' ),
                'intent'  => 'You are trying to find educational research material, article maps, or publications.',
                'title'   => 'Knowledge Libraries',
                'url'     => '/knowledge-libraries/',
                'why'     => 'The Knowledge Libraries page is the best entry point for article maps, research libraries, and conceptual learning paths.',
                'related' => array(
                    'Publications' => '/publications/',
                    'Research Librarian' => '/platform/research-librarian/',
                    'Platform Methodology' => '/platform/methodology/',
                ),
            ),
            array(
                'keys'    => array( 'consulting', 'hire', 'work with', 'support', 'help me', 'contact' ),
                'intent'  => 'You are trying to contact Sustainable Catalyst or understand support/consulting routes.',
                'title'   => 'Consulting',
                'url'     => '/consulting/',
                'why'     => 'The consulting and contact routes are the appropriate starting points for project inquiries or direct collaboration questions.',
                'related' => array(
                    'Support' => '/support/',
                    'Contact' => '/contact/',
                    'Platform' => '/platform/',
                ),
            ),
            array(
                'keys'    => array( 'feature', 'suggestion', 'does not exist', 'new capability', 'request' ),
                'intent'  => 'You are looking for a capability, module, or route that may not exist yet.',
                'title'   => 'Feature Suggestions',
                'url'     => '/platform/feature-suggestions/',
                'why'     => 'Feature Suggestions is the right place to route requests for new modules, improvements, or missing functionality.',
                'related' => array(
                    'Research Librarian' => '/platform/research-librarian/',
                    'Platform Demos' => '/platform/demos/',
                    'GitHub Organization' => 'https://github.com/Content-Catalyst-LLC',
                ),
            ),
        );

        foreach ( $routes as $route ) {
            foreach ( $route['keys'] as $key ) {
                if ( false !== strpos( $q, $key ) ) {
                    return $route;
                }
            }
        }

        return array(
            'intent'  => 'You are trying to orient yourself inside Sustainable Catalyst and choose a starting point.',
            'title'   => 'Platform',
            'url'     => '/platform/',
            'why'     => 'The platform page gives the broadest orientation before you choose a demo, methodology page, knowledge library, or support route.',
            'related' => array(
                'Platform Demos' => '/platform/demos/',
                'Research Librarian' => '/platform/research-librarian/',
                'Knowledge Libraries' => '/knowledge-libraries/',
                'Feature Suggestions' => '/platform/feature-suggestions/',
            ),
        );
    }

    public function render_admin_notices() {
        if ( ! current_user_can( 'manage_options' ) ) {
            return;
        }

        $notice = get_transient( 'sc_rl_ai_admin_notice_' . get_current_user_id() );
        if ( ! is_array( $notice ) || empty( $notice['message'] ) ) {
            return;
        }

        delete_transient( 'sc_rl_ai_admin_notice_' . get_current_user_id() );
        $type = isset( $notice['type'] ) && in_array( $notice['type'], array( 'success', 'error', 'warning', 'info' ), true ) ? $notice['type'] : 'info';
        echo '<div class="notice notice-' . esc_attr( $type ) . ' is-dismissible"><p>' . wp_kses_post( $notice['message'] ) . '</p></div>';
    }

    private function redirect_admin_with_notice( $type, $message ) {
        set_transient(
            'sc_rl_ai_admin_notice_' . get_current_user_id(),
            array(
                'type'    => $type,
                'message' => $message,
            ),
            60
        );

        wp_safe_redirect( admin_url( 'options-general.php?page=sc-research-librarian-ai' ) );
        exit;
    }

    public function handle_knowledge_base_upload() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( esc_html__( 'You do not have permission to update this knowledge base.', 'sustainable-catalyst-research-librarian-ai' ) );
        }

        check_admin_referer( 'sc_rl_ai_upload_knowledge_base', 'sc_rl_ai_upload_nonce' );

        $options = $this->get_options();
        $api_key = isset( $options['api_key'] ) ? trim( $options['api_key'] ) : '';

        if ( '' === $api_key ) {
            $this->redirect_admin_with_notice( 'error', __( 'Upload failed: no OpenAI API key is saved in the plugin settings.', 'sustainable-catalyst-research-librarian-ai' ) );
        }

        if ( empty( $_FILES['sc_rl_ai_knowledge_file'] ) || ! isset( $_FILES['sc_rl_ai_knowledge_file']['error'] ) ) {
            $this->redirect_admin_with_notice( 'error', __( 'Upload failed: no knowledge file was selected.', 'sustainable-catalyst-research-librarian-ai' ) );
        }

        $file = $_FILES['sc_rl_ai_knowledge_file'];
        if ( UPLOAD_ERR_OK !== absint( $file['error'] ) ) {
            $this->redirect_admin_with_notice( 'error', sprintf( __( 'Upload failed: WordPress reported upload error code %d.', 'sustainable-catalyst-research-librarian-ai' ), absint( $file['error'] ) ) );
        }

        $filename = isset( $file['name'] ) ? sanitize_file_name( wp_unslash( $file['name'] ) ) : 'sustainable-catalyst-knowledge.md';
        $tmp_name = isset( $file['tmp_name'] ) ? $file['tmp_name'] : '';
        $size     = isset( $file['size'] ) ? absint( $file['size'] ) : 0;

        if ( '' === $tmp_name || ! is_uploaded_file( $tmp_name ) ) {
            $this->redirect_admin_with_notice( 'error', __( 'Upload failed: the temporary uploaded file could not be read.', 'sustainable-catalyst-research-librarian-ai' ) );
        }

        if ( $size <= 0 || $size > 5 * MB_IN_BYTES ) {
            $this->redirect_admin_with_notice( 'error', __( 'Upload failed: please upload a non-empty Markdown or text file under 5 MB.', 'sustainable-catalyst-research-librarian-ai' ) );
        }

        $extension = strtolower( pathinfo( $filename, PATHINFO_EXTENSION ) );
        if ( ! in_array( $extension, array( 'md', 'markdown', 'txt' ), true ) ) {
            $this->redirect_admin_with_notice( 'error', __( 'Upload failed: please upload a .md, .markdown, or .txt knowledge file.', 'sustainable-catalyst-research-librarian-ai' ) );
        }

        $create_new      = ! empty( $_POST['sc_rl_ai_create_new_vector_store'] );
        $vector_store_id = isset( $options['vector_store_id'] ) ? trim( $options['vector_store_id'] ) : '';

        if ( $create_new || '' === $vector_store_id ) {
            $created = $this->openai_create_vector_store( $api_key );
            if ( is_wp_error( $created ) ) {
                $this->redirect_admin_with_notice( 'error', esc_html__( 'Vector store creation failed: ', 'sustainable-catalyst-research-librarian-ai' ) . esc_html( $created->get_error_message() ) );
            }
            $vector_store_id = $created;
        }

        $uploaded_file_id = $this->openai_upload_file( $api_key, $tmp_name, $filename );
        if ( is_wp_error( $uploaded_file_id ) ) {
            $this->redirect_admin_with_notice( 'error', esc_html__( 'Knowledge file upload to OpenAI failed: ', 'sustainable-catalyst-research-librarian-ai' ) . esc_html( $uploaded_file_id->get_error_message() ) );
        }

        $attached = $this->openai_attach_file_to_vector_store( $api_key, $vector_store_id, $uploaded_file_id );
        if ( is_wp_error( $attached ) ) {
            $this->redirect_admin_with_notice( 'error', esc_html__( 'File uploaded but could not be attached to the vector store: ', 'sustainable-catalyst-research-librarian-ai' ) . esc_html( $attached->get_error_message() ) );
        }

        $options['vector_store_id'] = $vector_store_id;
        update_option( self::OPTION_NAME, wp_parse_args( $options, self::defaults() ), false );

        $message  = esc_html__( 'Knowledge base uploaded successfully.', 'sustainable-catalyst-research-librarian-ai' );
        $message .= '<br><strong>' . esc_html__( 'Vector Store ID:', 'sustainable-catalyst-research-librarian-ai' ) . '</strong> <code>' . esc_html( $vector_store_id ) . '</code>';
        $message .= '<br><strong>' . esc_html__( 'OpenAI File ID:', 'sustainable-catalyst-research-librarian-ai' ) . '</strong> <code>' . esc_html( $uploaded_file_id ) . '</code>';
        $message .= '<br>' . esc_html__( 'OpenAI may need a short moment to finish indexing the file before file search returns the new content.', 'sustainable-catalyst-research-librarian-ai' );

        $this->redirect_admin_with_notice( 'success', $message );
    }

    private function openai_create_vector_store( $api_key ) {
        $body = array(
            'name' => 'Sustainable Catalyst Research Librarian Knowledge Base ' . gmdate( 'Y-m-d H:i:s' ) . ' UTC',
        );

        $response = wp_remote_post(
            'https://api.openai.com/v1/vector_stores',
            array(
                'headers' => array(
                    'Authorization' => 'Bearer ' . $api_key,
                    'Content-Type'  => 'application/json',
                ),
                'body'    => wp_json_encode( $body ),
                'timeout' => 45,
            )
        );

        $data = $this->parse_openai_response( $response );
        if ( is_wp_error( $data ) ) {
            return $data;
        }

        if ( empty( $data['id'] ) || ! is_string( $data['id'] ) ) {
            return new WP_Error( 'sc_rl_ai_no_vector_store_id', __( 'OpenAI did not return a vector store ID.', 'sustainable-catalyst-research-librarian-ai' ) );
        }

        return sanitize_text_field( $data['id'] );
    }

    private function openai_upload_file( $api_key, $tmp_name, $filename ) {
        $file_contents = file_get_contents( $tmp_name );
        if ( false === $file_contents || '' === $file_contents ) {
            return new WP_Error( 'sc_rl_ai_empty_upload', __( 'The uploaded knowledge file could not be read.', 'sustainable-catalyst-research-librarian-ai' ) );
        }

        $boundary = 'sc_rl_ai_' . wp_generate_password( 24, false, false );
        $eol      = "\r\n";
        $mime     = 'text/markdown';

        $body  = '--' . $boundary . $eol;
        $body .= 'Content-Disposition: form-data; name="purpose"' . $eol . $eol;
        $body .= 'assistants' . $eol;
        $body .= '--' . $boundary . $eol;
        $body .= 'Content-Disposition: form-data; name="file"; filename="' . str_replace( '"', '', $filename ) . '"' . $eol;
        $body .= 'Content-Type: ' . $mime . $eol . $eol;
        $body .= $file_contents . $eol;
        $body .= '--' . $boundary . '--' . $eol;

        $response = wp_remote_post(
            'https://api.openai.com/v1/files',
            array(
                'headers' => array(
                    'Authorization' => 'Bearer ' . $api_key,
                    'Content-Type'  => 'multipart/form-data; boundary=' . $boundary,
                ),
                'body'    => $body,
                'timeout' => 60,
            )
        );

        $data = $this->parse_openai_response( $response );
        if ( is_wp_error( $data ) ) {
            return $data;
        }

        if ( empty( $data['id'] ) || ! is_string( $data['id'] ) ) {
            return new WP_Error( 'sc_rl_ai_no_file_id', __( 'OpenAI did not return a file ID.', 'sustainable-catalyst-research-librarian-ai' ) );
        }

        return sanitize_text_field( $data['id'] );
    }

    private function openai_attach_file_to_vector_store( $api_key, $vector_store_id, $file_id ) {
        $vector_store_id = sanitize_text_field( $vector_store_id );
        $file_id         = sanitize_text_field( $file_id );

        if ( '' === $vector_store_id || '' === $file_id ) {
            return new WP_Error( 'sc_rl_ai_missing_ids', __( 'Missing vector store ID or file ID.', 'sustainable-catalyst-research-librarian-ai' ) );
        }

        $response = wp_remote_post(
            'https://api.openai.com/v1/vector_stores/' . rawurlencode( $vector_store_id ) . '/files',
            array(
                'headers' => array(
                    'Authorization' => 'Bearer ' . $api_key,
                    'Content-Type'  => 'application/json',
                ),
                'body'    => wp_json_encode( array( 'file_id' => $file_id ) ),
                'timeout' => 45,
            )
        );

        $data = $this->parse_openai_response( $response );
        if ( is_wp_error( $data ) ) {
            return $data;
        }

        return true;
    }

    private function parse_openai_response( $response ) {
        if ( is_wp_error( $response ) ) {
            return $response;
        }

        $code = wp_remote_retrieve_response_code( $response );
        $raw  = wp_remote_retrieve_body( $response );
        $data = json_decode( $raw, true );

        if ( $code < 200 || $code >= 300 ) {
            $message = is_array( $data ) && isset( $data['error']['message'] ) ? $data['error']['message'] : 'OpenAI request failed.';
            return new WP_Error( 'sc_rl_ai_openai_error', sanitize_text_field( $message ) );
        }

        if ( ! is_array( $data ) ) {
            return new WP_Error( 'sc_rl_ai_bad_openai_json', __( 'OpenAI returned an unreadable response.', 'sustainable-catalyst-research-librarian-ai' ) );
        }

        return $data;
    }

    public function register_admin_page() {
        add_options_page(
            __( 'Research Librarian AI', 'sustainable-catalyst-research-librarian-ai' ),
            __( 'Research Librarian AI', 'sustainable-catalyst-research-librarian-ai' ),
            'manage_options',
            'sc-research-librarian-ai',
            array( $this, 'render_admin_page' )
        );
    }

    public function register_settings() {
        register_setting(
            'sc_rl_ai_settings_group',
            self::OPTION_NAME,
            array(
                'type'              => 'array',
                'sanitize_callback' => array( $this, 'sanitize_options' ),
                'default'           => self::defaults(),
            )
        );

        add_settings_section(
            'sc_rl_ai_main',
            __( 'OpenAI and Knowledge Base Settings', 'sustainable-catalyst-research-librarian-ai' ),
            array( $this, 'settings_section_intro' ),
            'sc-research-librarian-ai'
        );

        $fields = array(
            'api_key'                 => __( 'OpenAI API Key', 'sustainable-catalyst-research-librarian-ai' ),
            'model'                   => __( 'Model Name', 'sustainable-catalyst-research-librarian-ai' ),
            'vector_store_id'         => __( 'Vector Store ID', 'sustainable-catalyst-research-librarian-ai' ),
            'max_file_search_results' => __( 'Max File-Search Results', 'sustainable-catalyst-research-librarian-ai' ),
            'max_output_tokens'       => __( 'Max Output Tokens', 'sustainable-catalyst-research-librarian-ai' ),
            'rate_limit'              => __( 'Rate Limit', 'sustainable-catalyst-research-librarian-ai' ),
            'system_instructions'     => __( 'System Instructions', 'sustainable-catalyst-research-librarian-ai' ),
        );

        foreach ( $fields as $field => $label ) {
            add_settings_field(
                'sc_rl_ai_' . $field,
                $label,
                array( $this, 'render_field' ),
                'sc-research-librarian-ai',
                'sc_rl_ai_main',
                array( 'field' => $field )
            );
        }
    }

    public function sanitize_options( $input ) {
        $old = $this->get_options();
        $input = is_array( $input ) ? $input : array();

        $api_key_raw = isset( $input['api_key'] ) ? trim( sanitize_text_field( wp_unslash( $input['api_key'] ) ) ) : '';
        if ( '-' === $api_key_raw ) {
            $api_key = '';
        } elseif ( '' === $api_key_raw ) {
            $api_key = $old['api_key'];
        } else {
            $api_key = $api_key_raw;
        }

        return array(
            'api_key'                 => $api_key,
            'model'                   => isset( $input['model'] ) ? sanitize_text_field( wp_unslash( $input['model'] ) ) : self::defaults()['model'],
            'vector_store_id'         => isset( $input['vector_store_id'] ) ? sanitize_text_field( wp_unslash( $input['vector_store_id'] ) ) : '',
            'max_file_search_results' => max( 1, min( 20, absint( $input['max_file_search_results'] ?? self::defaults()['max_file_search_results'] ) ) ),
            'max_output_tokens'       => max( 150, min( 4000, absint( $input['max_output_tokens'] ?? self::defaults()['max_output_tokens'] ) ) ),
            'rate_limit'              => max( 1, min( 100, absint( $input['rate_limit'] ?? self::defaults()['rate_limit'] ) ) ),
            'system_instructions'     => isset( $input['system_instructions'] ) ? sanitize_textarea_field( wp_unslash( $input['system_instructions'] ) ) : self::default_system_instructions(),
        );
    }

    public function settings_section_intro() {
        echo '<p>' . esc_html__( 'The browser calls only the WordPress REST endpoint. The OpenAI API key is used server-side and is never localized into JavaScript.', 'sustainable-catalyst-research-librarian-ai' ) . '</p>';
        echo '<p><code>[sustainable_catalyst_research_librarian_ai]</code></p>';
    }

    public function render_field( $args ) {
        $field = $args['field'];
        $options = $this->get_options();
        $name = self::OPTION_NAME . '[' . $field . ']';

        switch ( $field ) {
            case 'api_key':
                $has_key = ! empty( $options['api_key'] );
                echo '<input type="password" class="regular-text" name="' . esc_attr( $name ) . '" value="" autocomplete="off" placeholder="' . esc_attr( $has_key ? 'Key saved. Leave blank to keep it.' : 'YOUR_OPENAI_API_KEY' ) . '" />';
                echo '<p class="description">' . esc_html__( 'Leave blank to keep the existing key. Enter a single hyphen (-) and save to clear it.', 'sustainable-catalyst-research-librarian-ai' ) . '</p>';
                break;
            case 'model':
            case 'vector_store_id':
                echo '<input type="text" class="regular-text" name="' . esc_attr( $name ) . '" value="' . esc_attr( $options[ $field ] ) . '" />';
                if ( 'model' === $field ) {
                    echo '<p class="description">' . esc_html__( 'Example: gpt-5.5. Use any model available to your OpenAI project that supports Responses API text generation and file search.', 'sustainable-catalyst-research-librarian-ai' ) . '</p>';
                } else {
                    echo '<p class="description">' . esc_html__( 'Optional. When set, the assistant uses this Sustainable Catalyst vector store through OpenAI file search.', 'sustainable-catalyst-research-librarian-ai' ) . '</p>';
                }
                break;
            case 'max_file_search_results':
                echo '<input type="number" min="1" max="20" name="' . esc_attr( $name ) . '" value="' . esc_attr( absint( $options[ $field ] ) ) . '" />';
                break;
            case 'max_output_tokens':
                echo '<input type="number" min="150" max="4000" name="' . esc_attr( $name ) . '" value="' . esc_attr( absint( $options[ $field ] ) ) . '" />';
                break;
            case 'rate_limit':
                echo '<input type="number" min="1" max="100" name="' . esc_attr( $name ) . '" value="' . esc_attr( absint( $options[ $field ] ) ) . '" />';
                echo '<p class="description">' . esc_html__( 'Maximum questions per visitor/IP per hour.', 'sustainable-catalyst-research-librarian-ai' ) . '</p>';
                break;
            case 'system_instructions':
                echo '<textarea class="large-text code" rows="14" name="' . esc_attr( $name ) . '">' . esc_textarea( $options[ $field ] ) . '</textarea>';
                break;
        }
    }

    public function render_admin_page() {
        if ( ! current_user_can( 'manage_options' ) ) {
            return;
        }

        $options = $this->get_options();
        ?>
        <div class="wrap">
            <h1><?php esc_html_e( 'Sustainable Catalyst Research Librarian AI', 'sustainable-catalyst-research-librarian-ai' ); ?></h1>
            <p><?php esc_html_e( 'Configure the AI-enabled Research Librarian. If the API key or model is missing, the frontend automatically uses the deterministic route system.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
            <p><strong><?php esc_html_e( 'AI status:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <?php echo ( ! empty( $options['api_key'] ) && ! empty( $options['model'] ) ) ? esc_html__( 'Configured', 'sustainable-catalyst-research-librarian-ai' ) : esc_html__( 'Fallback only', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
            <form action="options.php" method="post">
                <?php
                settings_fields( 'sc_rl_ai_settings_group' );
                do_settings_sections( 'sc-research-librarian-ai' );
                submit_button();
                ?>
            </form>

            <hr />

            <h2><?php esc_html_e( 'Knowledge Base Upload', 'sustainable-catalyst-research-librarian-ai' ); ?></h2>
            <p><?php esc_html_e( 'Upload a Markdown or text seed file directly from WordPress. The plugin will use the saved OpenAI API key server-side, create or reuse a vector store, upload the file to OpenAI, attach it to the vector store, and save the Vector Store ID for you.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
            <p><strong><?php esc_html_e( 'Current Vector Store ID:', 'sustainable-catalyst-research-librarian-ai' ); ?></strong> <code><?php echo esc_html( ! empty( $options['vector_store_id'] ) ? $options['vector_store_id'] : __( 'None yet', 'sustainable-catalyst-research-librarian-ai' ) ); ?></code></p>

            <form action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" method="post" enctype="multipart/form-data">
                <?php wp_nonce_field( 'sc_rl_ai_upload_knowledge_base', 'sc_rl_ai_upload_nonce' ); ?>
                <input type="hidden" name="action" value="sc_rl_ai_upload_knowledge_base" />

                <table class="form-table" role="presentation">
                    <tr>
                        <th scope="row">
                            <label for="sc_rl_ai_knowledge_file"><?php esc_html_e( 'Knowledge File', 'sustainable-catalyst-research-librarian-ai' ); ?></label>
                        </th>
                        <td>
                            <input type="file" id="sc_rl_ai_knowledge_file" name="sc_rl_ai_knowledge_file" accept=".md,.markdown,.txt,text/markdown,text/plain" required />
                            <p class="description"><?php esc_html_e( 'Upload the expanded Sustainable Catalyst knowledge seed as a .md, .markdown, or .txt file. Maximum size: 5 MB.', 'sustainable-catalyst-research-librarian-ai' ); ?></p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row"><?php esc_html_e( 'Vector Store Behavior', 'sustainable-catalyst-research-librarian-ai' ); ?></th>
                        <td>
                            <label>
                                <input type="checkbox" name="sc_rl_ai_create_new_vector_store" value="1" <?php checked( empty( $options['vector_store_id'] ) ); ?> />
                                <?php esc_html_e( 'Create a new vector store and save its ID. Leave unchecked to add this file to the existing vector store ID above.', 'sustainable-catalyst-research-librarian-ai' ); ?>
                            </label>
                        </td>
                    </tr>
                </table>

                <?php submit_button( __( 'Upload Knowledge Base to OpenAI', 'sustainable-catalyst-research-librarian-ai' ), 'secondary' ); ?>
            </form>
        </div>
        <?php
    }
}

register_activation_hook( __FILE__, array( 'Sustainable_Catalyst_Research_Librarian_AI', 'activate' ) );
Sustainable_Catalyst_Research_Librarian_AI::instance();
