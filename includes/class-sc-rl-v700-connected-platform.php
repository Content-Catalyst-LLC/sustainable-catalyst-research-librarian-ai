<?php
/**
 * Research Librarian AI v7.0.5 — Connected Research Intelligence Platform.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class SC_RL6_V700_Connected_Platform {
    const VERSION = '7.0.5';
    const OPTION_NAME = 'sc_rl_v700_platform_options';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';
    const API_SCHEMA = 'sc-connected-research-api/1.0';
    const WORKSPACE_SCHEMA = 'sc-research-librarian-public-workspace/2.0';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_rest_routes' ), 140 );
        add_action( 'admin_menu', array( __CLASS__, 'register_admin_menu' ), 1050 );
        add_shortcode( 'sc_connected_research_workspace', array( __CLASS__, 'render_workspace' ) );
        add_shortcode( 'sc_research_projects_summary', array( __CLASS__, 'render_summary' ) );
        add_shortcode( 'sc_connected_research_platform_status', array( __CLASS__, 'render_status' ) );
    }

    public static function activate() {
        update_option( self::OPTION_NAME, wp_parse_args( get_option( self::OPTION_NAME, array() ), self::defaults() ), false );
    }

    public static function defaults() {
        return array(
            'workspace_mode' => 'public',
            'persistent_projects' => '1',
            'portable_backups' => '1',
            'contradiction_analysis' => '1',
            'uncertainty_registers' => '1',
            'workflow_templates' => '1',
            'human_publication_review' => '1',
            'api_public_status' => '1',
            'default_visibility' => 'private',
        );
    }

    public static function options() { return wp_parse_args( get_option( self::OPTION_NAME, array() ), self::defaults() ); }
    public static function can_manage() { return current_user_can( 'manage_options' ); }
    public static function can_research() { return is_user_logged_in() && current_user_can( 'read' ); }

    private static function backend_options() {
        return wp_parse_args( get_option( 'sc_rl_v620_python_options', array() ), array( 'enabled' => '0', 'backend_url' => '', 'backend_api_key' => '', 'request_timeout' => 45 ) );
    }

    private static function backend_request( $path, $method = 'GET', $payload = null ) {
        $o = self::backend_options();
        if ( '1' !== (string) $o['enabled'] || empty( $o['backend_url'] ) || empty( $o['backend_api_key'] ) ) {
            return new WP_Error( 'sc_rl_v700_backend_disabled', 'The connected research backend is not configured.', array( 'status' => 503 ) );
        }
        $args = array(
            'method' => strtoupper( $method ),
            'timeout' => max( 10, min( 120, absint( $o['request_timeout'] ) ) ),
            'headers' => array( 'Accept' => 'application/json', 'Content-Type' => 'application/json', 'X-SC-RL-Key' => (string) $o['backend_api_key'], 'User-Agent' => 'Sustainable-Catalyst-Research-Librarian/' . self::VERSION ),
        );
        if ( null !== $payload ) { $args['body'] = wp_json_encode( $payload ); }
        $response = wp_remote_request( untrailingslashit( $o['backend_url'] ) . '/' . ltrim( $path, '/' ), $args );
        if ( is_wp_error( $response ) ) { return $response; }
        $code = wp_remote_retrieve_response_code( $response );
        $body = json_decode( wp_remote_retrieve_body( $response ), true );
        if ( $code < 200 || $code >= 300 || ! is_array( $body ) ) {
            return new WP_Error( 'sc_rl_v700_backend_failed', 'The connected research platform request failed.', array( 'status' => $code ? $code : 502, 'response' => $body ) );
        }
        return $body;
    }

    public static function register_rest_routes() {
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/status', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_status' ), 'permission_callback' => '__return_true' ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/projects', array(
            array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_projects' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
            array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_save_project' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/projects/(?P<project_id>[A-Za-z0-9._-]+)', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_project' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/investigations', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_investigation' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/entities', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_entity' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/workflows', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_workflow' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/contradictions', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_contradictions' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/uncertainties', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_uncertainties' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/projects/(?P<project_id>[A-Za-z0-9._-]+)/backup', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_backup' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/export', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_export' ), 'permission_callback' => array( __CLASS__, 'can_manage' ) ) );
    }

    private static function checked_json( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'X-WP-Nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) { return new WP_Error( 'sc_rl_v700_invalid_nonce', 'The research workspace security token expired.', array( 'status' => 403 ) ); }
        return is_array( $request->get_json_params() ) ? $request->get_json_params() : array();
    }

    private static function respond( $value ) { return is_wp_error( $value ) ? $value : new WP_REST_Response( $value, 200 ); }

    public static function rest_status() {
        $summary = self::backend_request( '/v1/platform/summary', 'GET' );
        if ( is_wp_error( $summary ) ) {
            return new WP_REST_Response( array( 'schema' => 'sc-connected-research-platform-status/1.0', 'version' => self::VERSION, 'state' => 'wordpress-fallback', 'workspace_schema' => self::WORKSPACE_SCHEMA, 'persistent_projects' => false, 'message' => $summary->get_error_message() ), 200 );
        }
        return new WP_REST_Response( array( 'schema' => 'sc-connected-research-platform-status/1.0', 'version' => self::VERSION, 'state' => 'connected', 'workspace_schema' => self::WORKSPACE_SCHEMA, 'summary' => $summary ), 200 );
    }

    public static function rest_projects( WP_REST_Request $request ) { $query = '/v1/projects?limit=' . max( 1, min( 200, absint( $request->get_param( 'limit' ) ?: 100 ) ) ) . '&owner_ref=' . rawurlencode( 'wp-user-' . get_current_user_id() ); return self::respond( self::backend_request( $query, 'GET' ) ); }
    private static function authorized_project( $project_id, $write = false ) {
        $bundle = self::backend_request( '/v1/projects/' . rawurlencode( sanitize_text_field( $project_id ) ), 'GET' );
        if ( is_wp_error( $bundle ) ) { return $bundle; }
        $project = is_array( $bundle['project'] ?? null ) ? $bundle['project'] : array();
        $owner = (string) ( $project['owner_ref'] ?? '' );
        $mine = 'wp-user-' . get_current_user_id();
        $public = 'public' === (string) ( $project['visibility'] ?? 'private' );
        if ( current_user_can( 'manage_options' ) || $owner === $mine || ( ! $write && $public ) ) { return $bundle; }
        return new WP_Error( 'sc_rl_v700_project_forbidden', 'You do not have access to this research project.', array( 'status' => 403 ) );
    }

    public static function rest_project( WP_REST_Request $request ) { return self::respond( self::authorized_project( sanitize_text_field( $request['project_id'] ), false ) ); }

    public static function rest_save_project( WP_REST_Request $request ) {
        $p = self::checked_json( $request ); if ( is_wp_error( $p ) ) { return $p; }
        $payload = array( 'project_id' => sanitize_text_field( $p['project_id'] ?? '' ), 'title' => sanitize_text_field( $p['title'] ?? '' ), 'objective' => sanitize_textarea_field( $p['objective'] ?? '' ), 'status' => sanitize_key( $p['status'] ?? 'active' ), 'visibility' => sanitize_key( $p['visibility'] ?? self::options()['default_visibility'] ), 'tags' => array_map( 'sanitize_text_field', array_slice( is_array( $p['tags'] ?? null ) ? $p['tags'] : array(), 0, 30 ) ), 'owner_ref' => 'wp-user-' . get_current_user_id(), 'governance' => array( 'human_control' => true, 'publication_requires_review' => true ) );
        return self::respond( self::backend_request( '/v1/projects', 'POST', $payload ) );
    }

    public static function rest_investigation( WP_REST_Request $request ) { $p=self::checked_json($request); if(is_wp_error($p)){return $p;} $access=self::authorized_project($p['project_id']??'',true); if(is_wp_error($access)){return $access;} return self::respond(self::backend_request('/v1/investigations','POST',array('investigation_id'=>sanitize_text_field($p['investigation_id']??''),'project_id'=>sanitize_text_field($p['project_id']??''),'title'=>sanitize_text_field($p['title']??''),'question'=>sanitize_textarea_field($p['question']??''),'status'=>sanitize_key($p['status']??'open'),'steps'=>is_array($p['steps']??null)?$p['steps']:array()))); }
    public static function rest_entity( WP_REST_Request $request ) { $p=self::checked_json($request); if(is_wp_error($p)){return $p;} $access=self::authorized_project($p['project_id']??'',true); if(is_wp_error($access)){return $access;} return self::respond(self::backend_request('/v1/projects/entities','POST',array('project_id'=>sanitize_text_field($p['project_id']??''),'entity_id'=>sanitize_text_field($p['entity_id']??''),'entity_type'=>sanitize_key($p['entity_type']??'evidence'),'title'=>sanitize_text_field($p['title']??''),'payload'=>is_array($p['payload']??null)?$p['payload']:array()))); }
    public static function rest_workflow( WP_REST_Request $request ) { $p=self::checked_json($request); if(is_wp_error($p)){return $p;} $access=self::authorized_project($p['project_id']??'',true); if(is_wp_error($access)){return $access;} return self::respond(self::backend_request('/v1/workflows/template','POST',array('project_id'=>sanitize_text_field($p['project_id']??''),'investigation_id'=>sanitize_text_field($p['investigation_id']??''),'kind'=>sanitize_key($p['kind']??'evidence-review'),'title'=>sanitize_text_field($p['title']??''),'persist'=>true))); }
    public static function rest_contradictions( WP_REST_Request $request ) { $p=self::checked_json($request); if(is_wp_error($p)){return $p;} $access=self::authorized_project($p['project_id']??'',true); if(is_wp_error($access)){return $access;} return self::respond(self::backend_request('/v1/research/contradictions','POST',array('project_id'=>sanitize_text_field($p['project_id']??''),'items'=>is_array($p['items']??null)?array_slice($p['items'],0,500):array(),'persist'=>true))); }
    public static function rest_uncertainties( WP_REST_Request $request ) { $p=self::checked_json($request); if(is_wp_error($p)){return $p;} $access=self::authorized_project($p['project_id']??'',true); if(is_wp_error($access)){return $access;} return self::respond(self::backend_request('/v1/research/uncertainties','POST',array('project_id'=>sanitize_text_field($p['project_id']??''),'items'=>is_array($p['items']??null)?array_slice($p['items'],0,200):array(),'persist'=>true))); }
    public static function rest_backup( WP_REST_Request $request ) { $p=self::checked_json($request); if(is_wp_error($p)){return $p;} $access=self::authorized_project($request['project_id'],true); if(is_wp_error($access)){return $access;} return self::respond(self::backend_request('/v1/projects/'.rawurlencode(sanitize_text_field($request['project_id'])).'/backup','POST',array())); }
    public static function rest_export() { return self::respond( self::backend_request( '/v1/platform/backups?limit=100', 'GET' ) ); }

    public static function register_admin_menu() {
        add_submenu_page( 'options-general.php', 'Connected Research Intelligence Platform', 'Connected Research Platform', 'manage_options', 'sc-connected-research-platform', array( __CLASS__, 'render_admin' ) );
    }

    public static function render_admin() {
        if ( ! self::can_manage() ) { return; }
        if ( isset( $_POST['sc_rl_v700_save'] ) && check_admin_referer( 'sc_rl_v700_save' ) ) {
            $d=self::defaults(); $clean=array();
            foreach($d as $key=>$value){ if('workspace_mode'===$key){$candidate=sanitize_key($_POST[$key]??$value);$clean[$key]=in_array($candidate,array('public','editorial','institutional'),true)?$candidate:'public';} elseif('default_visibility'===$key){$candidate=sanitize_key($_POST[$key]??$value);$clean[$key]=in_array($candidate,array('private','shared','public'),true)?$candidate:'private';} else {$clean[$key]=isset($_POST[$key])?'1':'0';} }
            update_option(self::OPTION_NAME,$clean,false); echo '<div class="notice notice-success"><p>Connected Research Platform settings saved.</p></div>';
        }
        $o=self::options(); $status=self::backend_request('/v1/platform/summary','GET'); $api=self::backend_request('/v1/platform/api','GET'); ?>
        <div class="wrap"><h1>Connected Research Intelligence Platform</h1><p>v7.0.5 consolidates verified retrieval, persistent projects, investigations, evidence, workflows, cross-product handoffs, artifact history, governance, and portable recovery into one human-controlled research environment.</p>
        <div class="card"><h2>Platform state</h2><p><strong>Backend:</strong> <?php echo is_wp_error($status)?esc_html($status->get_error_message()):'Connected'; ?></p><p><strong>Stable API:</strong> <?php echo is_wp_error($api)?'Unavailable':esc_html($api['schema']??self::API_SCHEMA); ?></p><?php if(!is_wp_error($status)&&!empty($status['counts'])):?><ul><?php foreach($status['counts'] as $key=>$value):?><li><strong><?php echo esc_html(ucwords(str_replace('_',' ',$key))); ?>:</strong> <?php echo esc_html(absint($value)); ?></li><?php endforeach;?></ul><?php endif;?></div>
        <form method="post"><?php wp_nonce_field('sc_rl_v700_save');?><table class="form-table"><tbody><tr><th>Workspace mode</th><td><select name="workspace_mode"><?php foreach(array('public'=>'Public','editorial'=>'Editorial','institutional'=>'Institutional') as $value=>$label):?><option value="<?php echo esc_attr($value);?>" <?php selected($o['workspace_mode'],$value);?>><?php echo esc_html($label);?></option><?php endforeach;?></select></td></tr><tr><th>Default visibility</th><td><select name="default_visibility"><?php foreach(array('private'=>'Private','shared'=>'Shared','public'=>'Public') as $value=>$label):?><option value="<?php echo esc_attr($value);?>" <?php selected($o['default_visibility'],$value);?>><?php echo esc_html($label);?></option><?php endforeach;?></select></td></tr><tr><th>Capabilities</th><td><?php foreach(array('persistent_projects'=>'Persistent projects','portable_backups'=>'Portable backup and recovery','contradiction_analysis'=>'Contradiction tracking','uncertainty_registers'=>'Uncertainty registers','workflow_templates'=>'Reusable workflow templates','human_publication_review'=>'Human publication review','api_public_status'=>'Public platform status') as $key=>$label):?><label style="display:block;margin:0 0 8px"><input type="checkbox" name="<?php echo esc_attr($key);?>" <?php checked($o[$key],'1');?>> <?php echo esc_html($label);?></label><?php endforeach;?></td></tr></tbody></table><?php submit_button('Save Platform Settings','primary','sc_rl_v700_save');?></form>
        <p><code>[sc_connected_research_workspace]</code> renders the authenticated project workspace. <code>[sc_research_projects_summary]</code> and <code>[sc_connected_research_platform_status]</code> render compact summaries.</p></div><?php
    }

    private static function enqueue_workspace_assets() {
        wp_enqueue_style( 'sc-research-librarian-ai' );
        wp_enqueue_script( 'sc-rl-v700-connected-platform', plugins_url( '../assets/sc-research-platform-v7.js', __FILE__ ), array(), self::VERSION, true );
        wp_localize_script( 'sc-rl-v700-connected-platform', 'SCRLPlatformV7', array( 'root' => esc_url_raw( rest_url( self::REST_NAMESPACE . '/platform/v7/' ) ), 'nonce' => wp_create_nonce( 'wp_rest' ), 'authenticated' => is_user_logged_in(), 'workspaceMode' => self::options()['workspace_mode'] ) );
    }

    public static function render_workspace() {
        self::enqueue_workspace_assets(); ob_start(); ?>
        <section class="sc-rl-v7-platform" data-sc-rl-v7-workspace>
          <header><p class="sc-rl-product__eyebrow">Connected Research Intelligence Platform</p><h2>Research Projects</h2><p>Create persistent investigations, collect verified evidence, preserve uncertainty, prepare cross-product workflows, and export portable research packages. Publication and external actions remain human-controlled.</p></header>
          <?php if(!is_user_logged_in()):?><div class="sc-rl-v7-notice"><strong>Browser-local mode</strong><p>Sign in to create persistent cross-device projects. The public Research Librarian remains available without an account.</p></div><?php else:?><div class="sc-rl-v7-layout"><aside class="sc-rl-v7-create"><h3>New project</h3><form data-sc-rl-v7-project-form><label>Project title<input name="title" required maxlength="240"></label><label>Research objective<textarea name="objective" rows="5" maxlength="4000"></textarea></label><button type="submit">Create project</button><p role="status" aria-live="polite" data-sc-rl-v7-form-status></p></form></aside><div><div class="sc-rl-v7-toolbar"><h3>Your projects</h3><button type="button" data-sc-rl-v7-refresh>Refresh</button></div><div data-sc-rl-v7-projects role="region" aria-live="polite"><p>Loading research projects…</p></div></div></div><?php endif;?>
        </section><?php return ob_get_clean();
    }

    public static function render_summary() { $status=self::backend_request('/v1/platform/summary','GET'); $counts=is_wp_error($status)?array('projects'=>0,'investigations'=>0,'entities'=>0,'backups'=>0):($status['counts']??array()); ob_start();?><section class="sc-rl-v7-summary"><p class="sc-rl-product__eyebrow">Connected Research Platform</p><h2>Research Workspace Summary</h2><div class="sc-rl-product__grid"><?php foreach($counts as $key=>$value):?><article><span><?php echo esc_html(absint($value));?></span><strong><?php echo esc_html(ucwords(str_replace('_',' ',$key)));?></strong></article><?php endforeach;?></div></section><?php return ob_get_clean(); }
    public static function render_status() { $status=self::backend_request('/v1/platform/summary','GET'); $connected=!is_wp_error($status); ob_start();?><section class="sc-rl-governance sc-rl-governance--status"><p class="sc-rl-product__eyebrow">Platform Status</p><h2>Connected Research Intelligence</h2><div class="sc-rl-product__grid"><article><span><?php echo $connected?'Connected':'Fallback';?></span><strong>Platform state</strong><p><?php echo $connected?'Persistent project services are available.':'The public Librarian remains available; persistent projects require the backend.';?></p></article><article><span>v7.0.5</span><strong>Stable API</strong><p><?php echo esc_html(self::API_SCHEMA);?></p></article><article><span>Human</span><strong>Publication control</strong><p>No autonomous publication or external action.</p></article></div></section><?php return ob_get_clean(); }
}
