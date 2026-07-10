<?php
/**
 * Research Librarian v5.7.0 Research Demand and Knowledge-Gap Intelligence.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class SC_RL_V570_Research_Demand_Intelligence {
    const VERSION = '5.7.0';
    const REST_NAMESPACE = 'sc-research-librarian/v1';
    const EVENT_SCHEMA = 'sc-platform-event/1.0';
    const REPORT_SCHEMA = 'sc-research-demand-intelligence/1.0';
    const CACHE_OPTION = 'sc_rl_v570_demand_intelligence_cache';
    const SETTINGS_OPTION = 'sc_rl_v570_demand_intelligence_settings';
    const AUDIT_OPTION = 'sc_rl_v570_demand_intelligence_audit';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ) );
        add_action( 'admin_menu', array( __CLASS__, 'register_admin_page' ), 86 );
        add_filter( 'sc_rl_integration_capabilities', array( __CLASS__, 'capabilities' ) );
        add_shortcode( 'sc_research_demand_summary', array( __CLASS__, 'render_public_summary' ) );
        add_action( 'sc_rl_v570_daily_refresh', array( __CLASS__, 'refresh' ) );
        add_action( 'admin_init', array( __CLASS__, 'maybe_schedule' ) );
    }

    public static function maybe_schedule() {
        if ( ! wp_next_scheduled( 'sc_rl_v570_daily_refresh' ) ) {
            wp_schedule_event( time() + HOUR_IN_SECONDS, 'daily', 'sc_rl_v570_daily_refresh' );
        }
    }

    public static function capabilities( $caps = array() ) {
        return array_merge( is_array( $caps ) ? $caps : array(), array(
            'research_librarian_version' => self::VERSION,
            'research_demand_intelligence' => true,
            'knowledge_gap_intelligence' => true,
            'demand_coverage_scoring' => true,
            'missing_source_clusters' => true,
            'missing_tool_clusters' => true,
            'low_confidence_clusters' => true,
            'site_intelligence_events' => true,
            'report_schema' => self::REPORT_SCHEMA,
        ) );
    }

    private static function settings() {
        return wp_parse_args( get_option( self::SETTINGS_OPTION, array() ), array(
            'minimum_cluster_count' => 2,
            'low_confidence_threshold' => 50,
            'public_summary_enabled' => false,
            'public_minimum_count' => 5,
            'cache_hours' => 12,
        ) );
    }

    private static function option_array( $name ) {
        $value = get_option( $name, array() );
        return is_array( $value ) ? $value : array();
    }

    private static function stopwords() {
        return array_flip( array( 'the','and','for','that','with','this','from','into','about','what','when','where','which','would','could','should','have','has','had','your','you','our','are','was','were','how','why','who','can','not','but','all','any','more','need','want','help','using','use','please','research','route','source','topic','question','answer','tool','page','site','sustainable','catalyst' ) );
    }

    private static function terms( $text ) {
        $text = strtolower( wp_strip_all_tags( (string) $text ) );
        preg_match_all( '/[a-z][a-z0-9-]{2,}/', $text, $m );
        $stop = self::stopwords(); $terms = array();
        foreach ( array_slice( array_unique( $m[0] ?? array() ), 0, 20 ) as $term ) {
            if ( isset( $stop[ $term ] ) || strlen( $term ) < 3 ) { continue; }
            $terms[] = sanitize_key( $term );
        }
        return $terms;
    }

    private static function increment( &$bucket, $key, $amount = 1 ) {
        $key = sanitize_key( $key ?: 'unknown' );
        $bucket[ $key ] = ( $bucket[ $key ] ?? 0 ) + $amount;
    }

    private static function within_days( $row, $days ) {
        if ( $days <= 0 ) { return true; }
        $date = $row['created_at_utc'] ?? $row['created_at'] ?? $row['occurred_at'] ?? '';
        $ts = $date ? strtotime( $date ) : false;
        return ! $ts || $ts >= ( time() - ( $days * DAY_IN_SECONDS ) );
    }

    private static function analyze_window( $days ) {
        $sessions = self::option_array( 'sc_rl_ai_session_log' );
        $feedback = self::option_array( 'sc_rl_ai_feedback_log' );
        $bridge = self::option_array( 'sc_rl_v560_feedback_bridge_log' );
        $evaluation = self::option_array( 'sc_rl_ai_evaluation_failure_log' );
        $paths = self::option_array( 'sc_rl_ai_guided_path_logs' );

        $routes = array(); $targets = array(); $topics = array(); $low_confidence = array();
        $gap_types = array(); $missing_sources = array(); $missing_tools = array(); $failed_prompts = array();
        $source_coverage = array(); $route_success = array();
        $counts = array( 'sessions'=>0, 'feedback'=>0, 'bridge_feedback'=>0, 'evaluation_failures'=>0, 'guided_paths'=>0 );
        $threshold = absint( self::settings()['low_confidence_threshold'] );

        foreach ( $sessions as $row ) {
            if ( ! self::within_days( $row, $days ) ) { continue; }
            $counts['sessions']++;
            $route = $row['route_id'] ?? 'unknown'; self::increment( $routes, $route );
            self::increment( $targets, $row['handoff_target'] ?? 'knowledge_route' );
            $source_count = absint( $row['source_count'] ?? 0 );
            if ( ! isset( $source_coverage[ $route ] ) ) { $source_coverage[ $route ] = array( 'sessions'=>0, 'sources'=>0, 'zero_source'=>0 ); }
            $source_coverage[ $route ]['sessions']++;
            $source_coverage[ $route ]['sources'] += $source_count;
            if ( 0 === $source_count ) { $source_coverage[ $route ]['zero_source']++; }
            $confidence = isset( $row['confidence_score'] ) ? (float) $row['confidence_score'] : 0;
            if ( $confidence <= 1 ) { $confidence *= 100; }
            if ( $confidence < $threshold || 'low' === ( $row['confidence_level'] ?? '' ) ) { self::increment( $low_confidence, $route ); }
            foreach ( self::terms( $row['question'] ?? '' ) as $term ) { self::increment( $topics, $term ); }
        }

        foreach ( $feedback as $row ) {
            if ( ! self::within_days( $row, $days ) ) { continue; }
            $counts['feedback']++;
            $type = $row['type'] ?? 'issue'; self::increment( $gap_types, $type );
            $route = $row['route_id'] ?? 'unknown';
            if ( 'helpful' === $type ) { self::increment( $route_success, $route ); }
            if ( in_array( $type, array( 'missing_source','knowledge_gap' ), true ) ) { self::increment( $missing_sources, $route ); }
            if ( 'feature_gap' === $type ) { self::increment( $missing_tools, $route ); }
            foreach ( self::terms( ( $row['question'] ?? '' ) . ' ' . ( $row['note'] ?? '' ) ) as $term ) { self::increment( $topics, $term ); }
        }

        foreach ( $bridge as $row ) {
            if ( ! self::within_days( $row, $days ) ) { continue; }
            $counts['bridge_feedback']++;
            $type = $row['feedback_type'] ?? 'issue'; self::increment( $gap_types, $type );
            $route = $row['route_id'] ?? 'unknown';
            if ( in_array( $type, array( 'missing_source','knowledge_gap','missing_topic','answer_grounding' ), true ) ) { self::increment( $missing_sources, $route ); }
            if ( in_array( $type, array( 'missing_tool','feature_gap' ), true ) ) { self::increment( $missing_tools, $row['query_topic'] ?? $route ); }
            foreach ( self::terms( ( $row['query_topic'] ?? '' ) . ' ' . ( $row['question'] ?? '' ) . ' ' . ( $row['note'] ?? '' ) ) as $term ) { self::increment( $topics, $term ); }
        }

        foreach ( $evaluation as $row ) {
            if ( ! self::within_days( $row, $days ) ) { continue; }
            $failures = $row['failures'] ?? array();
            $counts['evaluation_failures'] += is_array( $failures ) ? count( $failures ) : 1;
            foreach ( is_array( $failures ) ? $failures : array( $row ) as $failure ) {
                $route = $failure['actual_route'] ?? $failure['route_id'] ?? 'unknown'; self::increment( $failed_prompts, $route );
                foreach ( self::terms( $failure['prompt'] ?? $failure['question'] ?? '' ) as $term ) { self::increment( $topics, $term ); }
            }
        }

        foreach ( $paths as $row ) {
            if ( ! self::within_days( $row, $days ) ) { continue; }
            $counts['guided_paths']++;
            self::increment( $routes, $row['route_id'] ?? 'guided_path' );
            foreach ( self::terms( $row['question'] ?? $row['title'] ?? '' ) as $term ) { self::increment( $topics, $term ); }
        }

        foreach ( array( &$routes, &$targets, &$topics, &$low_confidence, &$gap_types, &$missing_sources, &$missing_tools, &$failed_prompts, &$route_success ) as &$bucket ) { arsort( $bucket ); }
        unset( $bucket );

        $opportunities = self::opportunities( $routes, $topics, $low_confidence, $missing_sources, $missing_tools, $failed_prompts, $source_coverage );
        return array(
            'window_days'=>$days, 'counts'=>$counts, 'routes'=>$routes, 'handoff_targets'=>$targets,
            'topics'=>$topics, 'low_confidence_routes'=>$low_confidence, 'gap_types'=>$gap_types,
            'missing_source_clusters'=>$missing_sources, 'missing_tool_clusters'=>$missing_tools,
            'evaluation_failure_routes'=>$failed_prompts, 'source_coverage'=>$source_coverage,
            'helpful_routes'=>$route_success, 'opportunities'=>$opportunities,
        );
    }

    private static function opportunities( $routes, $topics, $low, $sources, $tools, $failures, $coverage ) {
        $rows = array(); $keys = array_unique( array_merge( array_keys($routes), array_keys($low), array_keys($sources), array_keys($failures) ) );
        foreach ( $keys as $key ) {
            $demand = absint( $routes[$key] ?? 0 ); $low_count = absint( $low[$key] ?? 0 );
            $source_gap = absint( $sources[$key] ?? 0 ); $failure = absint( $failures[$key] ?? 0 );
            $zero = absint( $coverage[$key]['zero_source'] ?? 0 );
            $score = min( 100, ( $demand * 6 ) + ( $low_count * 12 ) + ( $source_gap * 15 ) + ( $failure * 10 ) + ( $zero * 8 ) );
            if ( $score < 10 ) { continue; }
            $rows[] = array( 'id'=>'route-'.$key, 'kind'=>'route_coverage', 'label'=>$key, 'score'=>$score, 'demand'=>$demand, 'low_confidence'=>$low_count, 'source_gap'=>$source_gap, 'evaluation_failures'=>$failure, 'zero_source_sessions'=>$zero, 'recommended_action'=>$source_gap || $zero ? 'Review source coverage and add or re-rank authoritative records.' : 'Review route quality and prompt-to-route rules.' );
        }
        foreach ( $tools as $key => $count ) {
            $rows[] = array( 'id'=>'tool-'.$key, 'kind'=>'missing_tool', 'label'=>$key, 'score'=>min(100,20+($count*18)), 'demand'=>$count, 'recommended_action'=>'Evaluate a Workbench tool, calculator, or deep-link action for this demand cluster.' );
        }
        foreach ( array_slice( $topics, 0, 20, true ) as $key => $count ) {
            if ( $count < absint( self::settings()['minimum_cluster_count'] ) ) { continue; }
            $rows[] = array( 'id'=>'topic-'.$key, 'kind'=>'topic_demand', 'label'=>$key, 'score'=>min(100,$count*8), 'demand'=>$count, 'recommended_action'=>'Compare topic demand with indexed coverage and the article-map roadmap.' );
        }
        usort( $rows, function($a,$b){ return (int)$b['score'] <=> (int)$a['score']; } );
        return array_slice( $rows, 0, 50 );
    }

    public static function report( $force = false ) {
        $cache = get_option( self::CACHE_OPTION, array() ); $hours = max(1,absint(self::settings()['cache_hours']));
        if ( ! $force && is_array($cache) && !empty($cache['generated_ts']) && (time()-absint($cache['generated_ts'])) < ($hours*HOUR_IN_SECONDS) ) { return $cache; }
        $report = array( 'schema'=>self::REPORT_SCHEMA, 'version'=>self::VERSION, 'generated_at'=>gmdate('c'), 'generated_ts'=>time(), 'methodology'=>array(
            'aggregation_only'=>true, 'raw_conversations_public'=>false, 'scores_advisory'=>true,
            'note'=>'Demand and gap scores combine observed route use, low confidence, source coverage, feedback, and evaluation failures. Human review is required.'
        ), 'windows'=>array( '30_days'=>self::analyze_window(30), '90_days'=>self::analyze_window(90), 'all_time'=>self::analyze_window(0) ) );
        update_option( self::CACHE_OPTION, $report, false );
        self::audit( 'report_refreshed', array( 'total_opportunities'=>count($report['windows']['all_time']['opportunities']) ) );
        self::publish_event( 'librarian.demand_intelligence_refreshed', array( 'opportunity_count'=>count($report['windows']['all_time']['opportunities']), 'session_count'=>$report['windows']['all_time']['counts']['sessions'] ) );
        return $report;
    }

    public static function refresh() { return self::report( true ); }

    private static function audit( $action, $context=array() ) {
        $rows=self::option_array(self::AUDIT_OPTION); array_unshift($rows,array('action'=>sanitize_key($action),'occurred_at'=>gmdate('c'),'user_id'=>get_current_user_id(),'context'=>$context));
        update_option(self::AUDIT_OPTION,array_slice($rows,0,200),false);
    }

    private static function publish_event( $type, $context ) {
        $event=array('schema'=>self::EVENT_SCHEMA,'event_type'=>sanitize_key($type),'source'=>'research_librarian','source_version'=>self::VERSION,'occurred_at'=>gmdate('c'),'context'=>$context,'privacy'=>array('aggregate_only'=>true,'contains_raw_conversation'=>false,'contains_email'=>false,'contains_ip'=>false,'contains_api_key'=>false));
        do_action('sc_rl_event',$event); do_action('sc_platform_event',$event); return $event;
    }

    public static function register_routes() {
        register_rest_route(self::REST_NAMESPACE,'/intelligence/demand',array('methods'=>'GET','callback'=>array(__CLASS__,'rest_report'),'permission_callback'=>function(){return current_user_can('manage_options');}));
        register_rest_route(self::REST_NAMESPACE,'/intelligence/demand/refresh',array('methods'=>'POST','callback'=>array(__CLASS__,'rest_refresh'),'permission_callback'=>function(){return current_user_can('manage_options');}));
        register_rest_route(self::REST_NAMESPACE,'/intelligence/demand/export',array('methods'=>'GET','callback'=>array(__CLASS__,'rest_export'),'permission_callback'=>function(){return current_user_can('manage_options');}));
        register_rest_route(self::REST_NAMESPACE,'/intelligence/demand/public',array('methods'=>'GET','callback'=>array(__CLASS__,'rest_public'),'permission_callback'=>'__return_true'));
    }
    public static function rest_report(){ return new WP_REST_Response(self::report(false),200); }
    public static function rest_refresh(){ return new WP_REST_Response(self::report(true),200); }
    public static function rest_export(){ return new WP_REST_Response(array('report'=>self::report(false),'audit'=>self::option_array(self::AUDIT_OPTION)),200); }
    public static function rest_public(){ if(empty(self::settings()['public_summary_enabled'])) return new WP_Error('public_summary_disabled','Public research-demand summary is disabled.',array('status'=>404)); return new WP_REST_Response(self::public_payload(),200); }

    private static function public_payload() {
        $all=self::report(false)['windows']['all_time']; $min=max(2,absint(self::settings()['public_minimum_count']));
        $filter=function($bucket)use($min){return array_filter(array_slice($bucket,0,10,true),function($count)use($min){return $count>=$min;});};
        return array('schema'=>self::REPORT_SCHEMA,'generated_at'=>self::report(false)['generated_at'],'top_routes'=>$filter($all['routes']),'top_topics'=>$filter($all['topics']),'methodology_note'=>'Aggregated public summary. Small clusters and raw questions are excluded.');
    }

    public static function register_admin_page() {
        add_submenu_page('options-general.php','Research Demand Intelligence','Research Demand Intelligence','manage_options','sc-rl-demand-intelligence',array(__CLASS__,'render_admin_page'));
    }

    private static function table( $title, $rows, $limit=10 ) {
        echo '<section class="card" style="max-width:none;margin:18px 0"><h2>'.esc_html($title).'</h2>';
        if(empty($rows)){echo '<p>No qualifying records yet.</p></section>';return;}
        echo '<table class="widefat striped"><thead><tr><th>Signal</th><th>Count / score</th></tr></thead><tbody>';
        foreach(array_slice($rows,0,$limit,true) as $key=>$value){ $display=is_array($value)?($value['score']??wp_json_encode($value)): $value; echo '<tr><td>'.esc_html($key).'</td><td>'.esc_html($display).'</td></tr>'; }
        echo '</tbody></table></section>';
    }

    public static function render_admin_page() {
        if(!current_user_can('manage_options')){wp_die('You do not have permission to access this page.');}
        if(isset($_POST['sc_rl_v570_refresh']) && check_admin_referer('sc_rl_v570_refresh')){self::report(true); echo '<div class="notice notice-success"><p>Research demand intelligence refreshed.</p></div>';}
        if(isset($_POST['sc_rl_v570_save_settings']) && check_admin_referer('sc_rl_v570_save_settings')){
            update_option(self::SETTINGS_OPTION,array(
                'minimum_cluster_count'=>max(2,min(50,absint($_POST['minimum_cluster_count']??2))),
                'low_confidence_threshold'=>max(1,min(100,absint($_POST['low_confidence_threshold']??50))),
                'public_summary_enabled'=>!empty($_POST['public_summary_enabled']),
                'public_minimum_count'=>max(2,min(100,absint($_POST['public_minimum_count']??5))),
                'cache_hours'=>max(1,min(72,absint($_POST['cache_hours']??12))),
            ),false);
            delete_option(self::CACHE_OPTION); self::audit('settings_updated');
            echo '<div class="notice notice-success"><p>Research demand intelligence settings saved.</p></div>';
        }
        $report=self::report(false); $all=$report['windows']['all_time']; $settings=self::settings();
        echo '<div class="wrap"><h1>Research Demand and Knowledge-Gap Intelligence</h1><p>Aggregate demand, confidence, coverage, feedback, and evaluation signals. Scores are advisory and require human review.</p>';
        echo '<form method="post" style="display:inline-block;margin-right:12px">'; wp_nonce_field('sc_rl_v570_refresh'); submit_button('Refresh intelligence now','primary','sc_rl_v570_refresh',false); echo '</form>';
        echo '<details style="margin:20px 0"><summary><strong>Intelligence settings</strong></summary><form method="post" class="card" style="max-width:720px">'; wp_nonce_field('sc_rl_v570_save_settings');
        echo '<p><label>Minimum cluster count <input type="number" min="2" max="50" name="minimum_cluster_count" value="'.esc_attr($settings['minimum_cluster_count']).'"></label></p>';
        echo '<p><label>Low-confidence threshold (0–100) <input type="number" min="1" max="100" name="low_confidence_threshold" value="'.esc_attr($settings['low_confidence_threshold']).'"></label></p>';
        echo '<p><label>Cache hours <input type="number" min="1" max="72" name="cache_hours" value="'.esc_attr($settings['cache_hours']).'"></label></p>';
        echo '<p><label><input type="checkbox" name="public_summary_enabled" value="1" '.checked(!empty($settings['public_summary_enabled']),true,false).'> Enable thresholded public aggregate summary</label></p>';
        echo '<p><label>Public minimum count <input type="number" min="2" max="100" name="public_minimum_count" value="'.esc_attr($settings['public_minimum_count']).'"></label></p>';
        submit_button('Save intelligence settings','secondary','sc_rl_v570_save_settings'); echo '</form></details>';
        echo '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:20px 0">';
        foreach(array('Saved sessions'=>$all['counts']['sessions'],'Feedback records'=>$all['counts']['feedback']+$all['counts']['bridge_feedback'],'Evaluation failures'=>$all['counts']['evaluation_failures'],'Opportunities'=>count($all['opportunities'])) as $label=>$value){echo '<div class="card"><h2>'.esc_html($value).'</h2><p>'.esc_html($label).'</p></div>';}
        echo '</div>';
        self::table('Highest-demand routes',$all['routes']); self::table('Emerging topics',$all['topics']); self::table('Low-confidence routes',$all['low_confidence_routes']); self::table('Missing-source clusters',$all['missing_source_clusters']); self::table('Missing-tool clusters',$all['missing_tool_clusters']);
        echo '<section class="card" style="max-width:none"><h2>Prioritized opportunities</h2><table class="widefat striped"><thead><tr><th>Opportunity</th><th>Kind</th><th>Score</th><th>Evidence</th><th>Recommended action</th></tr></thead><tbody>';
        foreach(array_slice($all['opportunities'],0,20) as $row){echo '<tr><td>'.esc_html($row['label']).'</td><td>'.esc_html($row['kind']).'</td><td>'.esc_html($row['score']).'</td><td>'.esc_html('Demand '.($row['demand']??0).'; low confidence '.($row['low_confidence']??0).'; source gaps '.($row['source_gap']??0)).'</td><td>'.esc_html($row['recommended_action']).'</td></tr>';}
        echo '</tbody></table></section><p><code>'.esc_html(rest_url(self::REST_NAMESPACE.'/intelligence/demand/export')).'</code></p></div>';
    }

    public static function render_public_summary() {
        if(empty(self::settings()['public_summary_enabled'])) return '';
        $data=self::public_payload(); ob_start(); ?>
        <section class="sc-rl-product sc-rl-demand-summary" data-sc-rl-product="research-demand-summary">
            <p class="sc-rl-product__eyebrow">Research Demand</p><h2>What visitors are exploring</h2>
            <p>Privacy-conscious aggregate signals from Research Librarian routes. Small clusters and raw questions are excluded.</p>
            <div class="sc-rl-product__grid">
                <?php foreach($data['top_routes'] as $route=>$count): ?><article><span><?php echo esc_html($count); ?></span><strong><?php echo esc_html($route); ?></strong><p>Saved research-route sessions.</p></article><?php endforeach; ?>
            </div>
        </section><?php return ob_get_clean();
    }
}
