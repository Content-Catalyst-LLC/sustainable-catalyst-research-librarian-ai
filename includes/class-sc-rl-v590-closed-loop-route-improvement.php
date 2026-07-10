<?php
/**
 * Research Librarian v5.9.0 Closed-Loop Route Improvement.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class SC_RL_V590_Closed_Loop_Route_Improvement {
    const VERSION = '5.9.0';
    const REST_NAMESPACE = 'sc-research-librarian/v1';
    const PROPOSAL_SCHEMA = 'sc-route-improvement-proposal/1.0';
    const PROPOSALS_OPTION = 'sc_rl_v590_route_improvement_proposals';
    const AUDIT_OPTION = 'sc_rl_v590_route_improvement_audit';
    const SNAPSHOTS_OPTION = 'sc_rl_v590_route_improvement_snapshots';
    const SETTINGS_OPTION = 'sc_rl_v590_route_improvement_settings';

    public static function init() {
        add_action( 'admin_menu', array( __CLASS__, 'register_admin_page' ), 88 );
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ) );
        add_filter( 'sc_rl_integration_capabilities', array( __CLASS__, 'capabilities' ) );
    }

    public static function capabilities( $caps = array() ) {
        return array_merge( is_array( $caps ) ? $caps : array(), array(
            'research_librarian_version' => self::VERSION,
            'closed_loop_route_improvement' => true,
            'feedback_to_route_review' => true,
            'before_after_evaluation' => true,
            'regression_protection' => true,
            'route_change_provenance' => true,
            'route_change_rollback' => true,
            'proposal_schema' => self::PROPOSAL_SCHEMA,
        ) );
    }

    private static function settings() {
        return wp_parse_args( get_option( self::SETTINGS_OPTION, array() ), array(
            'minimum_evidence_count' => 2,
            'minimum_pass_rate' => 100,
            'require_rationale' => true,
            'max_audit_rows' => 300,
            'max_snapshots' => 30,
        ) );
    }

    private static function rows( $option ) {
        $rows = get_option( $option, array() );
        return is_array( $rows ) ? $rows : array();
    }

    private static function save_rows( $option, $rows ) {
        update_option( $option, array_values( is_array( $rows ) ? $rows : array() ), false );
    }

    private static function audit( $action, $data = array() ) {
        $rows = self::rows( self::AUDIT_OPTION );
        array_unshift( $rows, array(
            'occurred_at_utc' => gmdate( 'c' ),
            'action' => sanitize_key( $action ),
            'user_id' => get_current_user_id(),
            'data' => is_array( $data ) ? $data : array(),
        ) );
        self::save_rows( self::AUDIT_OPTION, array_slice( $rows, 0, absint( self::settings()['max_audit_rows'] ) ) );
    }

    private static function publish_event( $type, $data = array() ) {
        $event = array(
            'schema' => 'sc-platform-event/1.0',
            'event_type' => sanitize_key( $type ),
            'source' => 'research_librarian',
            'source_version' => self::VERSION,
            'occurred_at' => gmdate( 'c' ),
            'data' => is_array( $data ) ? $data : array(),
        );
        do_action( 'sc_platform_event', $event );
    }

    private static function normalize_tests( $text, $expected_route ) {
        $lines = preg_split( '/\r\n|\r|\n/', (string) $text );
        $tests = array();
        foreach ( $lines as $line ) {
            $line = trim( $line );
            if ( '' === $line ) { continue; }
            $parts = array_map( 'trim', explode( '=>', $line, 2 ) );
            $tests[] = array(
                'prompt' => sanitize_text_field( $parts[0] ),
                'expected_route' => sanitize_key( $parts[1] ?? $expected_route ),
            );
        }
        return array_slice( $tests, 0, 30 );
    }

    private static function route_for_prompt( $prompt, $rules = null ) {
        if ( ! class_exists( 'Sustainable_Catalyst_Research_Librarian_AI_V440_Curation' ) ) { return ''; }
        $current = get_option( Sustainable_Catalyst_Research_Librarian_AI_V440_Curation::OPTION, array() );
        if ( is_array( $rules ) ) { update_option( Sustainable_Catalyst_Research_Librarian_AI_V440_Curation::OPTION, $rules, false ); }
        $route = Sustainable_Catalyst_Research_Librarian_AI_V440_Curation::match_override( strtolower( (string) $prompt ), self::route_catalog() );
        if ( is_array( $rules ) ) { update_option( Sustainable_Catalyst_Research_Librarian_AI_V440_Curation::OPTION, $current, false ); }
        return is_array( $route ) ? sanitize_key( $route['id'] ?? '' ) : '';
    }

    private static function route_catalog() {
        return array(
            array( 'id'=>'platform','title'=>'Platform','url'=>'/platform/' ),
            array( 'id'=>'decision-studio','title'=>'Decision Studio','url'=>'/platform/#decision-studio' ),
            array( 'id'=>'workbench','title'=>'Workbench','url'=>'/modeling-analytics/workbench/' ),
            array( 'id'=>'feature-suggestions','title'=>'Feature Suggestions','url'=>'/platform/feature-suggestions/' ),
            array( 'id'=>'methodology','title'=>'Methodology','url'=>'/platform/methodology/' ),
            array( 'id'=>'research-library','title'=>'Research Library','url'=>'/research-library/' ),
            array( 'id'=>'site-intelligence','title'=>'Site Intelligence','url'=>'/platform/site-intelligence/' ),
        );
    }

    private static function proposed_rule( $proposal ) {
        return array(
            'id' => 'closed-loop-' . sanitize_key( $proposal['id'] ),
            'label' => sanitize_text_field( $proposal['title'] ),
            'route_id' => sanitize_key( $proposal['proposed_route'] ),
            'triggers' => sanitize_textarea_field( $proposal['triggers'] ),
            'priority' => max( 1, min( 100, absint( $proposal['priority'] ) ) ),
            'status' => 'active',
            'note' => 'Closed-loop improvement. Proposal ' . sanitize_text_field( $proposal['id'] ) . '. ' . sanitize_textarea_field( $proposal['rationale'] ),
            'provenance' => array(
                'proposal_id' => sanitize_text_field( $proposal['id'] ),
                'evidence_count' => absint( $proposal['evidence_count'] ),
                'approved_by' => get_current_user_id(),
                'approved_at_utc' => gmdate( 'c' ),
                'schema' => self::PROPOSAL_SCHEMA,
            ),
        );
    }

    private static function evaluate( $proposal ) {
        $current_rules = Sustainable_Catalyst_Research_Librarian_AI_V440_Curation::rules();
        $candidate_rules = $current_rules;
        $candidate_rules['route_overrides'][] = self::proposed_rule( $proposal );
        $tests = is_array( $proposal['tests'] ?? null ) ? $proposal['tests'] : array();
        $results = array(); $passed = 0;
        foreach ( $tests as $test ) {
            $before = self::route_for_prompt( $test['prompt'], $current_rules );
            $after = self::route_for_prompt( $test['prompt'], $candidate_rules );
            $ok = sanitize_key( $test['expected_route'] ) === $after;
            if ( $ok ) { $passed++; }
            $results[] = array(
                'prompt' => $test['prompt'],
                'expected_route' => sanitize_key( $test['expected_route'] ),
                'before_route' => $before,
                'after_route' => $after,
                'passed' => $ok,
            );
        }
        $total = count( $tests );
        $rate = $total ? round( ( $passed / $total ) * 100, 1 ) : 0;
        return array(
            'evaluated_at_utc' => gmdate( 'c' ),
            'passed' => $passed,
            'total' => $total,
            'pass_rate' => $rate,
            'required_pass_rate' => absint( self::settings()['minimum_pass_rate'] ),
            'eligible' => $total > 0 && $rate >= absint( self::settings()['minimum_pass_rate'] ),
            'results' => $results,
        );
    }

    private static function save_snapshot( $proposal_id, $rules ) {
        $rows = self::rows( self::SNAPSHOTS_OPTION );
        array_unshift( $rows, array(
            'snapshot_id' => wp_generate_uuid4(),
            'proposal_id' => sanitize_text_field( $proposal_id ),
            'created_at_utc' => gmdate( 'c' ),
            'created_by' => get_current_user_id(),
            'rules' => $rules,
        ) );
        self::save_rows( self::SNAPSHOTS_OPTION, array_slice( $rows, 0, absint( self::settings()['max_snapshots'] ) ) );
        return $rows[0]['snapshot_id'];
    }

    private static function find_proposal( $id, &$index = null ) {
        $rows = self::rows( self::PROPOSALS_OPTION );
        foreach ( $rows as $i => $row ) {
            if ( ( $row['id'] ?? '' ) === $id ) { $index = $i; return array( $row, $rows ); }
        }
        return array( null, $rows );
    }

    private static function create_proposal_from_request() {
        $route = sanitize_key( wp_unslash( $_POST['proposed_route'] ?? '' ) );
        $tests = self::normalize_tests( wp_unslash( $_POST['tests'] ?? '' ), $route );
        return array(
            'schema' => self::PROPOSAL_SCHEMA,
            'id' => wp_generate_uuid4(),
            'title' => sanitize_text_field( wp_unslash( $_POST['title'] ?? 'Route improvement proposal' ) ),
            'status' => 'draft',
            'proposed_route' => $route,
            'triggers' => sanitize_textarea_field( wp_unslash( $_POST['triggers'] ?? '' ) ),
            'priority' => max( 1, min( 100, absint( $_POST['priority'] ?? 70 ) ) ),
            'rationale' => sanitize_textarea_field( wp_unslash( $_POST['rationale'] ?? '' ) ),
            'evidence_count' => absint( $_POST['evidence_count'] ?? 0 ),
            'evidence_refs' => array_values( array_filter( array_map( 'sanitize_text_field', preg_split( '/\r\n|\r|\n/', wp_unslash( $_POST['evidence_refs'] ?? '' ) ) ) ) ),
            'tests' => $tests,
            'evaluation' => array(),
            'created_at_utc' => gmdate( 'c' ),
            'created_by' => get_current_user_id(),
            'updated_at_utc' => gmdate( 'c' ),
        );
    }

    public static function register_admin_page() {
        add_submenu_page( 'options-general.php', 'Closed-Loop Route Improvement', 'Route Improvement', 'manage_options', 'sc-rl-route-improvement', array( __CLASS__, 'render_admin_page' ) );
    }

    public static function render_admin_page() {
        if ( ! current_user_can( 'manage_options' ) ) { wp_die( 'You do not have permission to access this page.' ); }
        $notice = '';
        if ( isset( $_POST['sc_rl_v590_create'] ) && check_admin_referer( 'sc_rl_v590_create' ) ) {
            $proposal = self::create_proposal_from_request();
            $settings = self::settings();
            if ( empty( $proposal['proposed_route'] ) || empty( $proposal['triggers'] ) || empty( $proposal['tests'] ) ) {
                $notice = 'A route, triggers, and at least one test prompt are required.';
            } elseif ( $proposal['evidence_count'] < absint( $settings['minimum_evidence_count'] ) ) {
                $notice = 'The proposal does not meet the configured minimum evidence count.';
            } elseif ( ! empty( $settings['require_rationale'] ) && empty( $proposal['rationale'] ) ) {
                $notice = 'A reviewer rationale is required.';
            } else {
                $rows = self::rows( self::PROPOSALS_OPTION ); array_unshift( $rows, $proposal ); self::save_rows( self::PROPOSALS_OPTION, $rows );
                self::audit( 'proposal_created', array( 'proposal_id'=>$proposal['id'], 'route'=>$proposal['proposed_route'] ) );
                $notice = 'Route improvement proposal created.';
            }
        }
        if ( isset( $_POST['sc_rl_v590_action'] ) && check_admin_referer( 'sc_rl_v590_action' ) ) {
            $id = sanitize_text_field( wp_unslash( $_POST['proposal_id'] ?? '' ) );
            $action = sanitize_key( wp_unslash( $_POST['proposal_action'] ?? '' ) );
            list( $proposal, $rows ) = self::find_proposal( $id, $index );
            if ( $proposal ) {
                if ( 'evaluate' === $action ) {
                    $proposal['evaluation'] = self::evaluate( $proposal );
                    $proposal['status'] = $proposal['evaluation']['eligible'] ? 'validated' : 'needs_revision';
                    $proposal['updated_at_utc'] = gmdate( 'c' ); $rows[$index] = $proposal; self::save_rows( self::PROPOSALS_OPTION, $rows );
                    self::audit( 'proposal_evaluated', array( 'proposal_id'=>$id, 'pass_rate'=>$proposal['evaluation']['pass_rate'] ) );
                    self::publish_event( 'librarian.route_improvement_evaluated', array( 'proposal_id'=>$id, 'route_id'=>$proposal['proposed_route'], 'pass_rate'=>$proposal['evaluation']['pass_rate'], 'eligible'=>$proposal['evaluation']['eligible'] ) );
                    $notice = 'Evaluation completed.';
                } elseif ( 'approve' === $action ) {
                    $evaluation = self::evaluate( $proposal );
                    if ( empty( $evaluation['eligible'] ) ) {
                        $notice = 'Approval blocked because regression tests did not meet the required pass rate.';
                    } else {
                        $rules = Sustainable_Catalyst_Research_Librarian_AI_V440_Curation::rules();
                        $snapshot = self::save_snapshot( $id, $rules );
                        $rules['route_overrides'][] = self::proposed_rule( $proposal );
                        Sustainable_Catalyst_Research_Librarian_AI_V440_Curation::save_rules( $rules );
                        $proposal['evaluation'] = $evaluation; $proposal['status'] = 'applied'; $proposal['snapshot_id'] = $snapshot;
                        $proposal['approved_at_utc'] = gmdate( 'c' ); $proposal['approved_by'] = get_current_user_id(); $proposal['updated_at_utc'] = gmdate( 'c' );
                        $rows[$index] = $proposal; self::save_rows( self::PROPOSALS_OPTION, $rows );
                        self::audit( 'proposal_applied', array( 'proposal_id'=>$id, 'snapshot_id'=>$snapshot, 'route'=>$proposal['proposed_route'] ) );
                        self::publish_event( 'librarian.route_improvement_applied', array( 'proposal_id'=>$id, 'route_id'=>$proposal['proposed_route'], 'evidence_count'=>absint($proposal['evidence_count']), 'pass_rate'=>$evaluation['pass_rate'] ) );
                        $notice = 'Validated route improvement applied.';
                    }
                } elseif ( 'reject' === $action ) {
                    $proposal['status'] = 'rejected'; $proposal['updated_at_utc'] = gmdate( 'c' ); $rows[$index] = $proposal; self::save_rows( self::PROPOSALS_OPTION, $rows );
                    self::audit( 'proposal_rejected', array( 'proposal_id'=>$id ) ); $notice = 'Proposal rejected.';
                } elseif ( 'rollback' === $action && ! empty( $proposal['snapshot_id'] ) ) {
                    foreach ( self::rows( self::SNAPSHOTS_OPTION ) as $snapshot ) {
                        if ( ( $snapshot['snapshot_id'] ?? '' ) === $proposal['snapshot_id'] ) {
                            Sustainable_Catalyst_Research_Librarian_AI_V440_Curation::save_rules( $snapshot['rules'] );
                            $proposal['status'] = 'rolled_back'; $proposal['rolled_back_at_utc'] = gmdate( 'c' ); $proposal['updated_at_utc'] = gmdate( 'c' ); $rows[$index] = $proposal; self::save_rows( self::PROPOSALS_OPTION, $rows );
                            self::audit( 'proposal_rolled_back', array( 'proposal_id'=>$id, 'snapshot_id'=>$proposal['snapshot_id'] ) );
                            self::publish_event( 'librarian.route_improvement_rolled_back', array( 'proposal_id'=>$id, 'route_id'=>$proposal['proposed_route'] ) );
                            $notice = 'Route improvement rolled back to the saved snapshot.'; break;
                        }
                    }
                }
            }
        }
        if ( isset( $_POST['sc_rl_v590_save_settings'] ) && check_admin_referer( 'sc_rl_v590_save_settings' ) ) {
            update_option( self::SETTINGS_OPTION, array(
                'minimum_evidence_count'=>max(1,min(100,absint($_POST['minimum_evidence_count']??2))),
                'minimum_pass_rate'=>max(50,min(100,absint($_POST['minimum_pass_rate']??100))),
                'require_rationale'=>!empty($_POST['require_rationale']),
                'max_audit_rows'=>max(50,min(1000,absint($_POST['max_audit_rows']??300))),
                'max_snapshots'=>max(5,min(100,absint($_POST['max_snapshots']??30))),
            ), false ); self::audit( 'settings_updated' ); $notice = 'Route improvement settings saved.';
        }
        $settings = self::settings(); $proposals = self::rows( self::PROPOSALS_OPTION );
        echo '<div class="wrap"><h1>Closed-Loop Route Improvement</h1><p>Convert reviewed feedback into tested route changes. No rule is applied until an administrator approves it and all configured regression tests pass.</p>';
        if ( $notice ) { echo '<div class="notice notice-info"><p>'.esc_html($notice).'</p></div>'; }
        echo '<details open><summary><strong>Create proposal</strong></summary><form method="post" class="card" style="max-width:900px">'; wp_nonce_field('sc_rl_v590_create');
        echo '<p><label>Title<br><input class="regular-text" name="title" required></label></p><p><label>Proposed route<br><select name="proposed_route" required><option value="">Select route</option>';
        foreach(self::route_catalog() as $route){echo '<option value="'.esc_attr($route['id']).'">'.esc_html($route['title']).'</option>';} echo '</select></label></p>';
        echo '<p><label>Triggers<br><textarea class="large-text" rows="3" name="triggers" required></textarea></label></p><p><label>Priority <input type="number" name="priority" min="1" max="100" value="70"></label></p>';
        echo '<p><label>Evidence count <input type="number" name="evidence_count" min="0" value="2"></label></p><p><label>Evidence references, one per line<br><textarea class="large-text" rows="3" name="evidence_refs"></textarea></label></p>';
        echo '<p><label>Reviewer rationale<br><textarea class="large-text" rows="3" name="rationale"></textarea></label></p><p><label>Regression tests, one per line as <code>prompt =&gt; expected-route</code><br><textarea class="large-text code" rows="6" name="tests" required></textarea></label></p>';
        submit_button('Create route improvement proposal','primary','sc_rl_v590_create'); echo '</form></details>';
        echo '<h2>Proposals</h2><table class="widefat striped"><thead><tr><th>Proposal</th><th>Route</th><th>Evidence</th><th>Status</th><th>Evaluation</th><th>Actions</th></tr></thead><tbody>';
        if(empty($proposals)){echo '<tr><td colspan="6">No proposals yet.</td></tr>';} else foreach($proposals as $p){$ev=$p['evaluation']??array(); echo '<tr><td><strong>'.esc_html($p['title']).'</strong><br><code>'.esc_html($p['id']).'</code><br>'.esc_html($p['rationale']).'</td><td>'.esc_html($p['proposed_route']).'<br><small>'.esc_html($p['triggers']).'</small></td><td>'.absint($p['evidence_count']).'</td><td>'.esc_html($p['status']).'</td><td>'.(isset($ev['pass_rate'])?esc_html($ev['pass_rate'].'% ('.$ev['passed'].'/'.$ev['total'].')'):'Not evaluated').'</td><td><form method="post">';wp_nonce_field('sc_rl_v590_action');echo '<input type="hidden" name="proposal_id" value="'.esc_attr($p['id']).'"><select name="proposal_action"><option value="evaluate">Evaluate</option><option value="approve">Approve and apply</option><option value="reject">Reject</option>';if(!empty($p['snapshot_id'])&&'applied'===$p['status'])echo '<option value="rollback">Rollback</option>';echo '</select> ';submit_button('Run','secondary','sc_rl_v590_action',false);echo '</form></td></tr>';}
        echo '</tbody></table>';
        echo '<details style="margin-top:20px"><summary><strong>Settings</strong></summary><form method="post" class="card" style="max-width:700px">';wp_nonce_field('sc_rl_v590_save_settings');echo '<p><label>Minimum evidence count <input type="number" min="1" max="100" name="minimum_evidence_count" value="'.esc_attr($settings['minimum_evidence_count']).'"></label></p><p><label>Minimum regression pass rate <input type="number" min="50" max="100" name="minimum_pass_rate" value="'.esc_attr($settings['minimum_pass_rate']).'">%</label></p><p><label><input type="checkbox" name="require_rationale" value="1" '.checked($settings['require_rationale'],true,false).'> Require reviewer rationale</label></p><p><label>Maximum audit rows <input type="number" name="max_audit_rows" value="'.esc_attr($settings['max_audit_rows']).'"></label></p><p><label>Maximum rollback snapshots <input type="number" name="max_snapshots" value="'.esc_attr($settings['max_snapshots']).'"></label></p>';submit_button('Save settings','primary','sc_rl_v590_save_settings');echo '</form></details>';
        echo '<p class="description">Applied changes are stored in the existing Research Librarian Curation route-overrides registry. Feedback and AI signals are evidence only; administrators retain final approval.</p></div>';
    }

    public static function register_routes() {
        $admin = function(){ return current_user_can('manage_options'); };
        register_rest_route(self::REST_NAMESPACE,'/route-improvements',array('methods'=>'GET','callback'=>array(__CLASS__,'rest_list'),'permission_callback'=>$admin));
        register_rest_route(self::REST_NAMESPACE,'/route-improvements/(?P<id>[a-zA-Z0-9-]+)',array('methods'=>'GET','callback'=>array(__CLASS__,'rest_get'),'permission_callback'=>$admin));
        register_rest_route(self::REST_NAMESPACE,'/route-improvements/(?P<id>[a-zA-Z0-9-]+)/evaluate',array('methods'=>'POST','callback'=>array(__CLASS__,'rest_evaluate'),'permission_callback'=>$admin));
        register_rest_route(self::REST_NAMESPACE,'/route-improvements/export',array('methods'=>'GET','callback'=>array(__CLASS__,'rest_export'),'permission_callback'=>$admin));
    }
    public static function rest_list(){return new WP_REST_Response(array('schema'=>self::PROPOSAL_SCHEMA,'version'=>self::VERSION,'proposals'=>self::rows(self::PROPOSALS_OPTION)),200);}
    public static function rest_get($request){list($p)=self::find_proposal(sanitize_text_field($request['id']));return $p?new WP_REST_Response($p,200):new WP_Error('not_found','Proposal not found.',array('status'=>404));}
    public static function rest_evaluate($request){list($p,$rows)=self::find_proposal(sanitize_text_field($request['id']),$index);if(!$p)return new WP_Error('not_found','Proposal not found.',array('status'=>404));$p['evaluation']=self::evaluate($p);$p['status']=$p['evaluation']['eligible']?'validated':'needs_revision';$rows[$index]=$p;self::save_rows(self::PROPOSALS_OPTION,$rows);return new WP_REST_Response($p,200);}
    public static function rest_export(){return new WP_REST_Response(array('schema'=>self::PROPOSAL_SCHEMA,'version'=>self::VERSION,'generated_at_utc'=>gmdate('c'),'settings'=>self::settings(),'proposals'=>self::rows(self::PROPOSALS_OPTION),'snapshots'=>self::rows(self::SNAPSHOTS_OPTION),'audit'=>self::rows(self::AUDIT_OPTION),'boundary'=>'Administrator-only export. Raw conversations and credentials are excluded.'),200);}
}
