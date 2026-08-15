<?php
/**
 * Research Librarian AI v7.5.0 — Connected Research Intelligence Platform.
 *
 * v7.5.0 adds collaborative Research Rooms with explicit membership, shared evidence
 * state, attributable questions/disagreements, participant activity, and room synthesis.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class SC_RL6_V700_Connected_Platform {
    const VERSION = '7.5.0';
    const OPTION_NAME = 'sc_rl_v700_platform_options';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';
    const API_SCHEMA = 'sc-connected-research-api/1.4';
    const WORKSPACE_SCHEMA = 'sc-research-librarian-public-workspace/2.4';
    const OBJECT_MODEL_SCHEMA = 'sc-research-library-object-model/1.0';
    const CONTEXT_SCHEMA = 'sc-research-context/1.0';
    const QUALITY_SCHEMA = 'sc-research-quality-signals/1.0';
    const STATE_SCHEMA = 'sc-research-state-summary/1.0';
    const ROOM_SCHEMA = 'sc-research-room/1.0';
    const ROOM_SYNTHESIS_SCHEMA = 'sc-research-room-synthesis/1.0';

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
            'library_object_model' => '1',
            'contextual_research' => '1',
            'personal_library_separation' => '1',
            'source_scope_provenance' => '1',
            'human_publication_review' => '1',
            'source_evaluation' => '1',
            'evidence_comparison' => '1',
            'evidence_gap_detection' => '1',
            'persistent_research_state' => '1',
            'reading_review_history' => '1',
            'open_question_register' => '1',
            'research_rooms' => '1',
            'room_membership_roles' => '1',
            'shared_evidence_state' => '1',
            'collaborative_questions' => '1',
            'room_disagreements' => '1',
            'participant_activity' => '1',
            'room_synthesis' => '1',
            'api_public_status' => '1',
            'default_visibility' => 'private',
        );
    }

    public static function options() { return wp_parse_args( get_option( self::OPTION_NAME, array() ), self::defaults() ); }
    public static function can_manage() { return current_user_can( 'manage_options' ); }
    public static function can_research() { return is_user_logged_in() && current_user_can( 'read' ); }
    private static function owner_ref() { return 'wp-user-' . get_current_user_id(); }

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

    private static function checked_json( WP_REST_Request $request ) {
        $nonce = $request->get_header( 'X-WP-Nonce' );
        if ( ! $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error( 'sc_rl_v700_invalid_nonce', 'The research workspace security token expired.', array( 'status' => 403 ) );
        }
        return is_array( $request->get_json_params() ) ? $request->get_json_params() : array();
    }

    private static function respond( $value ) { return is_wp_error( $value ) ? $value : new WP_REST_Response( $value, 200 ); }

    private static function sanitize_list( $value, $limit = 100 ) {
        if ( ! is_array( $value ) ) { return array(); }
        return array_values( array_filter( array_map( 'sanitize_text_field', array_slice( $value, 0, $limit ) ) ) );
    }

    private static function sanitize_tree( $value, $depth = 0 ) {
        if ( $depth > 6 ) { return null; }
        if ( is_array( $value ) ) {
            $clean = array();
            $count = 0;
            foreach ( $value as $key => $item ) {
                if ( $count++ >= 250 ) { break; }
                $safe_key = is_int( $key ) ? $key : sanitize_key( (string) $key );
                $clean[ $safe_key ] = self::sanitize_tree( $item, $depth + 1 );
            }
            return $clean;
        }
        if ( is_bool( $value ) || is_int( $value ) || is_float( $value ) || null === $value ) { return $value; }
        return sanitize_textarea_field( (string) $value );
    }

    public static function register_rest_routes() {
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/status', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_status' ), 'permission_callback' => '__return_true' ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/object-model', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_object_model' ), 'permission_callback' => '__return_true' ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/projects', array(
            array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_projects' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
            array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_save_project' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/projects/(?P<project_id>[A-Za-z0-9._-]+)', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_project' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/projects/(?P<project_id>[A-Za-z0-9._-]+)/library-objects', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_project_library_objects' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/investigations', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_investigation' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/entities', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_entity' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/library/objects', array(
            array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_library_objects' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
            array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_save_library_object' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/library/objects/(?P<object_id>[A-Za-z0-9._-]+)', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_library_object' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/library/objects/(?P<object_id>[A-Za-z0-9._-]+)/projects/(?P<project_id>[A-Za-z0-9._-]+)', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_link_library_object' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/contexts', array(
            array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_contexts' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
            array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_save_context' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/contexts/(?P<context_id>[A-Za-z0-9._-]+)', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_context' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/contexts/(?P<context_id>[A-Za-z0-9._-]+)/resolve', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_resolve_context' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/contexts/(?P<context_id>[A-Za-z0-9._-]+)/evidence-quality', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_context_quality' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/evidence/evaluate', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_source_evaluate' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/evidence/compare', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_evidence_compare' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/evidence/gaps', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_evidence_gaps' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/state', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_state_summary' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/state/activity', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_state_activity' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/state/object', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_state_object' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/state/questions', array(
            array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_state_questions' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
            array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_state_question_save' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/rooms', array(
            array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_rooms' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
            array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_save_room' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/rooms/(?P<room_id>[A-Za-z0-9._-]+)', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_room' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/rooms/(?P<room_id>[A-Za-z0-9._-]+)/members', array(
            array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_room_members' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
            array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_room_member_save' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/rooms/(?P<room_id>[A-Za-z0-9._-]+)/evidence', array(
            array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_room_evidence' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
            array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_room_evidence_save' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/rooms/(?P<room_id>[A-Za-z0-9._-]+)/questions', array(
            array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_room_questions' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
            array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_room_question_save' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/rooms/(?P<room_id>[A-Za-z0-9._-]+)/disagreements', array(
            array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_room_disagreements' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
            array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_room_disagreement_save' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ),
        ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/rooms/(?P<room_id>[A-Za-z0-9._-]+)/activity', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_room_activity' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/rooms/(?P<room_id>[A-Za-z0-9._-]+)/synthesis', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_room_synthesis' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/workflows', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_workflow' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/contradictions', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_contradictions' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/uncertainties', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_uncertainties' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/projects/(?P<project_id>[A-Za-z0-9._-]+)/backup', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_backup' ), 'permission_callback' => array( __CLASS__, 'can_research' ) ) );
        register_rest_route( self::REST_NAMESPACE, '/platform/v7/export', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_export' ), 'permission_callback' => array( __CLASS__, 'can_manage' ) ) );
    }

    public static function rest_status() {
        $summary = self::backend_request( '/v1/platform/summary', 'GET' );
        if ( is_wp_error( $summary ) ) {
            return new WP_REST_Response( array( 'schema' => 'sc-connected-research-platform-status/1.1', 'version' => self::VERSION, 'state' => 'wordpress-fallback', 'workspace_schema' => self::WORKSPACE_SCHEMA, 'object_model_schema' => self::OBJECT_MODEL_SCHEMA, 'persistent_projects' => false, 'message' => $summary->get_error_message() ), 200 );
        }
        return new WP_REST_Response( array( 'schema' => 'sc-connected-research-platform-status/1.1', 'version' => self::VERSION, 'state' => 'connected', 'workspace_schema' => self::WORKSPACE_SCHEMA, 'object_model_schema' => self::OBJECT_MODEL_SCHEMA, 'summary' => $summary ), 200 );
    }

    public static function rest_object_model() { return self::respond( self::backend_request( '/v1/library/object-model', 'GET' ) ); }
    public static function rest_projects( WP_REST_Request $request ) { $query = '/v1/projects?limit=' . max( 1, min( 200, absint( $request->get_param( 'limit' ) ?: 100 ) ) ) . '&owner_ref=' . rawurlencode( self::owner_ref() ); return self::respond( self::backend_request( $query, 'GET' ) ); }

    private static function authorized_project( $project_id, $write = false ) {
        $bundle = self::backend_request( '/v1/projects/' . rawurlencode( sanitize_text_field( $project_id ) ), 'GET' );
        if ( is_wp_error( $bundle ) ) { return $bundle; }
        $project = is_array( $bundle['project'] ?? null ) ? $bundle['project'] : array();
        $owner = (string) ( $project['owner_ref'] ?? '' );
        $public = 'public' === (string) ( $project['visibility'] ?? 'private' );
        if ( current_user_can( 'manage_options' ) || $owner === self::owner_ref() || ( ! $write && $public ) ) { return $bundle; }
        return new WP_Error( 'sc_rl_v700_project_forbidden', 'You do not have access to this research project.', array( 'status' => 403 ) );
    }

    private static function authorized_library_object( $object_id ) {
        $item = self::backend_request( '/v1/library/objects/' . rawurlencode( sanitize_text_field( $object_id ) ), 'GET' );
        if ( is_wp_error( $item ) ) { return $item; }
        $editorial = 'sustainable-catalyst-collection' === (string) ( $item['source_scope'] ?? '' );
        if ( current_user_can( 'manage_options' ) || (string) ( $item['owner_ref'] ?? '' ) === self::owner_ref() || $editorial ) { return $item; }
        return new WP_Error( 'sc_rl_v720_library_object_forbidden', 'You do not have access to this Library object.', array( 'status' => 403 ) );
    }

    private static function authorized_object_ids( $object_ids ) {
        $clean = self::sanitize_list( is_array( $object_ids ) ? $object_ids : array(), 200 );
        foreach ( $clean as $object_id ) {
            $item = self::authorized_library_object( $object_id );
            if ( is_wp_error( $item ) ) { return $item; }
        }
        return $clean;
    }

    private static function authorized_context( $context_id ) {
        $context = self::backend_request( '/v1/research/contexts/' . rawurlencode( sanitize_text_field( $context_id ) ), 'GET' );
        if ( is_wp_error( $context ) ) { return $context; }
        if ( current_user_can( 'manage_options' ) || (string) ( $context['owner_ref'] ?? '' ) === self::owner_ref() ) { return $context; }
        return new WP_Error( 'sc_rl_v720_context_forbidden', 'You do not have access to this research context.', array( 'status' => 403 ) );
    }

    private static function authorized_room( $room_id, $write = false, $manage = false ) {
        $room_id = sanitize_text_field( $room_id );
        if ( ! $room_id ) { return new WP_Error( 'sc_rl_v750_room_required', 'A Research Room is required.', array( 'status' => 422 ) ); }
        $bundle = self::backend_request( '/v1/research/rooms/' . rawurlencode( $room_id ) . '?member_ref=' . rawurlencode( self::owner_ref() ), 'GET' );
        if ( is_wp_error( $bundle ) ) { return $bundle; }
        $member = array();
        foreach ( is_array( $bundle['members'] ?? null ) ? $bundle['members'] : array() as $candidate ) {
            if ( self::owner_ref() === (string) ( $candidate['member_ref'] ?? '' ) && 'active' === (string) ( $candidate['status'] ?? 'active' ) ) { $member = $candidate; break; }
        }
        if ( ! $member ) { return new WP_Error( 'sc_rl_v750_room_forbidden', 'You are not an active member of this Research Room.', array( 'status' => 403 ) ); }
        $role = (string) ( $member['role'] ?? 'viewer' );
        if ( $manage && ! in_array( $role, array( 'owner', 'editor' ), true ) ) { return new WP_Error( 'sc_rl_v750_room_manage_forbidden', 'Only Research Room owners and editors can manage this room.', array( 'status' => 403 ) ); }
        if ( $write && ! in_array( $role, array( 'owner', 'editor', 'researcher' ), true ) ) { return new WP_Error( 'sc_rl_v750_room_write_forbidden', 'Your Research Room role is read-only.', array( 'status' => 403 ) ); }
        $bundle['current_member'] = $member;
        return $bundle;
    }

    private static function resolve_room_member_identity( $identity ) {
        $identity = trim( sanitize_text_field( $identity ) );
        if ( ! $identity ) { return new WP_Error( 'sc_rl_v750_member_required', 'Enter a WordPress username, email address, or user ID.', array( 'status' => 422 ) ); }
        $user = null;
        if ( ctype_digit( $identity ) ) { $user = get_user_by( 'id', absint( $identity ) ); }
        if ( ! $user && is_email( $identity ) ) { $user = get_user_by( 'email', $identity ); }
        if ( ! $user ) { $user = get_user_by( 'login', sanitize_user( $identity ) ); }
        if ( ! $user ) { return new WP_Error( 'sc_rl_v750_member_unknown', 'That WordPress account could not be found.', array( 'status' => 404 ) ); }
        return array( 'member_ref' => 'wp-user-' . absint( $user->ID ), 'display_name' => sanitize_text_field( $user->display_name ?: $user->user_login ) );
    }

    public static function resolve_context_for_current_user( $context_id ) {
        if ( ! self::can_research() || ! $context_id ) { return array(); }
        $context = self::authorized_context( $context_id );
        if ( is_wp_error( $context ) ) { return $context; }
        return self::backend_request( '/v1/research/contexts/' . rawurlencode( sanitize_text_field( $context_id ) ) . '/resolve', 'GET' );
    }

    public static function rest_project( WP_REST_Request $request ) { return self::respond( self::authorized_project( sanitize_text_field( $request['project_id'] ), false ) ); }
    public static function rest_project_library_objects( WP_REST_Request $request ) { $access=self::authorized_project($request['project_id'],false); if(is_wp_error($access)){return $access;} return self::respond(self::backend_request('/v1/projects/'.rawurlencode(sanitize_text_field($request['project_id'])).'/library-objects','GET')); }

    public static function rest_save_project( WP_REST_Request $request ) {
        $p = self::checked_json( $request ); if ( is_wp_error( $p ) ) { return $p; }
        $payload = array( 'project_id' => sanitize_text_field( $p['project_id'] ?? '' ), 'title' => sanitize_text_field( $p['title'] ?? '' ), 'objective' => sanitize_textarea_field( $p['objective'] ?? '' ), 'status' => sanitize_key( $p['status'] ?? 'active' ), 'visibility' => sanitize_key( $p['visibility'] ?? self::options()['default_visibility'] ), 'tags' => self::sanitize_list( $p['tags'] ?? array(), 30 ), 'owner_ref' => self::owner_ref(), 'governance' => array( 'human_control' => true, 'publication_requires_review' => true ) );
        return self::respond( self::backend_request( '/v1/projects', 'POST', $payload ) );
    }

    public static function rest_investigation( WP_REST_Request $request ) { $p=self::checked_json($request); if(is_wp_error($p)){return $p;} $access=self::authorized_project($p['project_id']??'',true); if(is_wp_error($access)){return $access;} return self::respond(self::backend_request('/v1/investigations','POST',array('investigation_id'=>sanitize_text_field($p['investigation_id']??''),'project_id'=>sanitize_text_field($p['project_id']??''),'title'=>sanitize_text_field($p['title']??''),'question'=>sanitize_textarea_field($p['question']??''),'status'=>sanitize_key($p['status']??'open'),'steps'=>self::sanitize_tree($p['steps']??array()),'evidence_collection_ids'=>self::sanitize_list($p['evidence_collection_ids']??array(),100),'reading_path_ids'=>self::sanitize_list($p['reading_path_ids']??array(),50),'workflow_ids'=>self::sanitize_list($p['workflow_ids']??array(),50),'artifact_ids'=>self::sanitize_list($p['artifact_ids']??array(),200)))); }
    public static function rest_entity( WP_REST_Request $request ) { $p=self::checked_json($request); if(is_wp_error($p)){return $p;} $access=self::authorized_project($p['project_id']??'',true); if(is_wp_error($access)){return $access;} return self::respond(self::backend_request('/v1/projects/entities','POST',array('project_id'=>sanitize_text_field($p['project_id']??''),'entity_id'=>sanitize_text_field($p['entity_id']??''),'entity_type'=>sanitize_key($p['entity_type']??'evidence'),'title'=>sanitize_text_field($p['title']??''),'payload'=>self::sanitize_tree($p['payload']??array())))); }

    public static function rest_library_objects( WP_REST_Request $request ) {
        $query='/v1/library/objects?limit='.max(1,min(500,absint($request->get_param('limit')?:200))).'&owner_ref='.rawurlencode(self::owner_ref());
        $object_type=sanitize_key($request->get_param('object_type')?:''); if($object_type){$query.='&object_type='.rawurlencode($object_type);}
        $source_scope=sanitize_key($request->get_param('source_scope')?:''); if($source_scope){$query.='&source_scope='.rawurlencode($source_scope);}
        return self::respond(self::backend_request($query,'GET'));
    }

    public static function rest_library_object( WP_REST_Request $request ) { return self::respond( self::authorized_library_object( $request['object_id'] ) ); }

    public static function rest_save_library_object( WP_REST_Request $request ) {
        $p=self::checked_json($request); if(is_wp_error($p)){return $p;}
        if(!empty($p['object_id'])){$existing=self::authorized_library_object($p['object_id']);if(is_wp_error($existing)){return $existing;}}
        $requested_scope=sanitize_key($p['source_scope']??'my-library');
        $member_scopes=array('my-library','current-project','current-research-room','external-reference');
        $source_scope=current_user_can('manage_options')?$requested_scope:(in_array($requested_scope,$member_scopes,true)?$requested_scope:'my-library');
        $payload=array(
            'object_id'=>sanitize_text_field($p['object_id']??''),'object_type'=>sanitize_key($p['object_type']??'source'),'title'=>sanitize_text_field($p['title']??''),'description'=>sanitize_textarea_field($p['description']??''),'owner_ref'=>self::owner_ref(),'source_scope'=>$source_scope,'visibility'=>sanitize_key($p['visibility']??'private'),'status'=>sanitize_key($p['status']??'saved'),'tags'=>self::sanitize_list($p['tags']??array(),50),'relationships'=>self::sanitize_tree($p['relationships']??array()),'provenance'=>self::sanitize_tree($p['provenance']??array()),'payload'=>self::sanitize_tree($p['payload']??array()),
        );
        return self::respond(self::backend_request('/v1/library/objects','POST',$payload));
    }

    public static function rest_link_library_object( WP_REST_Request $request ) {
        $p=self::checked_json($request); if(is_wp_error($p)){return $p;}
        $item=self::authorized_library_object($request['object_id']); if(is_wp_error($item)){return $item;}
        $project=self::authorized_project($request['project_id'],true); if(is_wp_error($project)){return $project;}
        return self::respond(self::backend_request('/v1/library/objects/'.rawurlencode(sanitize_text_field($request['object_id'])).'/projects/'.rawurlencode(sanitize_text_field($request['project_id'])),'POST',array()));
    }

    public static function rest_contexts() { return self::respond(self::backend_request('/v1/research/contexts?limit=100&owner_ref='.rawurlencode(self::owner_ref()),'GET')); }
    public static function rest_context( WP_REST_Request $request ) { return self::respond(self::authorized_context($request['context_id'])); }
    public static function rest_resolve_context( WP_REST_Request $request ) { return self::respond(self::resolve_context_for_current_user($request['context_id'])); }

    public static function rest_context_quality( WP_REST_Request $request ) {
        $context=self::authorized_context($request['context_id']); if(is_wp_error($context)){return $context;}
        return self::respond(self::backend_request('/v1/research/contexts/'.rawurlencode(sanitize_text_field($request['context_id'])).'/evidence-quality','GET'));
    }

    private static function evidence_payload( WP_REST_Request $request ) {
        $p=self::checked_json($request); if(is_wp_error($p)){return $p;}
        $ids=self::authorized_object_ids($p['object_ids']??array()); if(is_wp_error($ids)){return $ids;}
        $project_id=sanitize_text_field($p['project_id']??''); $persist=!empty($p['persist']);
        if($project_id){$project=self::authorized_project($project_id,$persist);if(is_wp_error($project)){return $project;}}
        return array('object_ids'=>$ids,'project_id'=>$project_id,'question'=>sanitize_textarea_field($p['question']??''),'persist'=>$persist);
    }

    public static function rest_source_evaluate( WP_REST_Request $request ) { $payload=self::evidence_payload($request); if(is_wp_error($payload)){return $payload;} return self::respond(self::backend_request('/v1/research/sources/evaluate','POST',$payload)); }
    public static function rest_evidence_compare( WP_REST_Request $request ) { $payload=self::evidence_payload($request); if(is_wp_error($payload)){return $payload;} return self::respond(self::backend_request('/v1/research/evidence/compare','POST',$payload)); }
    public static function rest_evidence_gaps( WP_REST_Request $request ) { $payload=self::evidence_payload($request); if(is_wp_error($payload)){return $payload;} return self::respond(self::backend_request('/v1/research/evidence/gaps','POST',$payload)); }

    private static function state_scope_for_current_user( $context_id = '', $project_id = '', $object_id = '' ) {
        $context_id = sanitize_text_field( $context_id );
        $project_id = sanitize_text_field( $project_id );
        $object_id = sanitize_text_field( $object_id );
        if ( $context_id ) {
            $context = self::authorized_context( $context_id );
            if ( is_wp_error( $context ) ) { return $context; }
            if ( ! $project_id ) { $project_id = sanitize_text_field( $context['project_id'] ?? '' ); }
        }
        if ( $project_id ) {
            $project = self::authorized_project( $project_id, false );
            if ( is_wp_error( $project ) ) { return $project; }
        }
        if ( $object_id ) {
            $object = self::authorized_library_object( $object_id );
            if ( is_wp_error( $object ) ) { return $object; }
        }
        return array( 'owner_ref' => self::owner_ref(), 'project_id' => $project_id, 'context_id' => $context_id, 'object_id' => $object_id );
    }

    private static function authorized_question_id( $question_id ) {
        $question_id = sanitize_text_field( $question_id );
        if ( ! $question_id ) { return true; }
        $response = self::backend_request( '/v1/research/questions?limit=1000&owner_ref=' . rawurlencode( self::owner_ref() ), 'GET' );
        if ( is_wp_error( $response ) ) { return $response; }
        foreach ( is_array( $response['questions'] ?? null ) ? $response['questions'] : array() as $question ) {
            if ( $question_id === (string) ( $question['question_id'] ?? '' ) ) { return true; }
        }
        return new WP_Error( 'sc_rl_v740_question_forbidden', 'You do not have access to this research question.', array( 'status' => 403 ) );
    }

    public static function rest_state_summary( WP_REST_Request $request ) {
        $scope = self::state_scope_for_current_user( $request->get_param( 'context_id' ), $request->get_param( 'project_id' ) );
        if ( is_wp_error( $scope ) ) { return $scope; }
        $query = '/v1/research/state/summary?owner_ref=' . rawurlencode( $scope['owner_ref'] );
        if ( $scope['project_id'] ) { $query .= '&project_id=' . rawurlencode( $scope['project_id'] ); }
        if ( $scope['context_id'] ) { $query .= '&context_id=' . rawurlencode( $scope['context_id'] ); }
        return self::respond( self::backend_request( $query, 'GET' ) );
    }

    public static function rest_state_activity( WP_REST_Request $request ) {
        $p = self::checked_json( $request ); if ( is_wp_error( $p ) ) { return $p; }
        $scope = self::state_scope_for_current_user( $p['context_id'] ?? '', $p['project_id'] ?? '', $p['object_id'] ?? '' );
        if ( is_wp_error( $scope ) ) { return $scope; }
        return self::respond( self::backend_request( '/v1/research/activity', 'POST', array(
            'owner_ref' => $scope['owner_ref'], 'project_id' => $scope['project_id'], 'context_id' => $scope['context_id'], 'object_id' => $scope['object_id'],
            'event_type' => sanitize_key( $p['event_type'] ?? 'note' ), 'query' => sanitize_textarea_field( $p['query'] ?? '' ),
            'note' => sanitize_textarea_field( $p['note'] ?? '' ), 'metadata' => self::sanitize_tree( $p['metadata'] ?? array() ),
        ) ) );
    }

    public static function rest_state_object( WP_REST_Request $request ) {
        $p = self::checked_json( $request ); if ( is_wp_error( $p ) ) { return $p; }
        $scope = self::state_scope_for_current_user( $p['context_id'] ?? '', $p['project_id'] ?? '', $p['object_id'] ?? '' );
        if ( is_wp_error( $scope ) ) { return $scope; }
        if ( ! $scope['object_id'] ) { return new WP_Error( 'sc_rl_v740_object_required', 'A Library object is required.', array( 'status' => 422 ) ); }
        return self::respond( self::backend_request( '/v1/research/object-states', 'POST', array(
            'owner_ref' => $scope['owner_ref'], 'project_id' => $scope['project_id'], 'context_id' => $scope['context_id'], 'object_id' => $scope['object_id'],
            'reading_state' => sanitize_key( $p['reading_state'] ?? '' ), 'contradiction_state' => sanitize_key( $p['contradiction_state'] ?? '' ),
            'note' => sanitize_textarea_field( $p['note'] ?? '' ),
        ) ) );
    }

    public static function rest_state_questions( WP_REST_Request $request ) {
        $scope = self::state_scope_for_current_user( $request->get_param( 'context_id' ), $request->get_param( 'project_id' ) );
        if ( is_wp_error( $scope ) ) { return $scope; }
        $query = '/v1/research/questions?limit=200&owner_ref=' . rawurlencode( $scope['owner_ref'] );
        if ( $scope['project_id'] ) { $query .= '&project_id=' . rawurlencode( $scope['project_id'] ); }
        if ( $scope['context_id'] ) { $query .= '&context_id=' . rawurlencode( $scope['context_id'] ); }
        $status = sanitize_key( $request->get_param( 'status' ) ?: '' ); if ( $status ) { $query .= '&status=' . rawurlencode( $status ); }
        return self::respond( self::backend_request( $query, 'GET' ) );
    }

    public static function rest_state_question_save( WP_REST_Request $request ) {
        $p = self::checked_json( $request ); if ( is_wp_error( $p ) ) { return $p; }
        $authorized = self::authorized_question_id( $p['question_id'] ?? '' ); if ( is_wp_error( $authorized ) ) { return $authorized; }
        $scope = self::state_scope_for_current_user( $p['context_id'] ?? '', $p['project_id'] ?? '' );
        if ( is_wp_error( $scope ) ) { return $scope; }
        return self::respond( self::backend_request( '/v1/research/questions', 'POST', array(
            'question_id' => sanitize_text_field( $p['question_id'] ?? '' ), 'owner_ref' => $scope['owner_ref'], 'project_id' => $scope['project_id'], 'context_id' => $scope['context_id'],
            'question' => sanitize_textarea_field( $p['question'] ?? '' ), 'status' => sanitize_key( $p['status'] ?? 'open' ),
            'linked_object_ids' => self::sanitize_list( $p['linked_object_ids'] ?? array(), 100 ), 'resolution' => sanitize_textarea_field( $p['resolution'] ?? '' ),
        ) ) );
    }

    public static function rest_rooms() {
        return self::respond( self::backend_request( '/v1/research/rooms?limit=100&member_ref=' . rawurlencode( self::owner_ref() ), 'GET' ) );
    }

    public static function rest_save_room( WP_REST_Request $request ) {
        $p = self::checked_json( $request ); if ( is_wp_error( $p ) ) { return $p; }
        $room_id = sanitize_text_field( $p['room_id'] ?? '' );
        $existing = null;
        if ( $room_id ) { $existing = self::authorized_room( $room_id, true, true ); if ( is_wp_error( $existing ) ) { return $existing; } }
        $project_id = sanitize_text_field( $p['project_id'] ?? '' );
        if ( $project_id ) { $project = self::authorized_project( $project_id, false ); if ( is_wp_error( $project ) ) { return $project; } }
        $owner_ref = $room_id && is_array( $existing['room'] ?? null ) ? sanitize_text_field( $existing['room']['owner_ref'] ?? self::owner_ref() ) : self::owner_ref();
        return self::respond( self::backend_request( '/v1/research/rooms', 'POST', array(
            'room_id' => $room_id, 'title' => sanitize_text_field( $p['title'] ?? 'Research Room' ), 'objective' => sanitize_textarea_field( $p['objective'] ?? '' ),
            'owner_ref' => $owner_ref, 'actor_ref' => self::owner_ref(), 'project_id' => $project_id, 'status' => sanitize_key( $p['status'] ?? 'active' ), 'tags' => self::sanitize_list( $p['tags'] ?? array(), 40 ),
        ) ) );
    }

    public static function rest_room( WP_REST_Request $request ) { return self::respond( self::authorized_room( $request['room_id'], false, false ) ); }

    public static function rest_room_members( WP_REST_Request $request ) {
        $access = self::authorized_room( $request['room_id'], false, false ); if ( is_wp_error( $access ) ) { return $access; }
        return self::respond( self::backend_request( '/v1/research/rooms/' . rawurlencode( sanitize_text_field( $request['room_id'] ) ) . '/members?member_ref=' . rawurlencode( self::owner_ref() ), 'GET' ) );
    }

    public static function rest_room_member_save( WP_REST_Request $request ) {
        $p = self::checked_json( $request ); if ( is_wp_error( $p ) ) { return $p; }
        $room_id = sanitize_text_field( $request['room_id'] );
        $access = self::authorized_room( $room_id, true, true ); if ( is_wp_error( $access ) ) { return $access; }
        $identity = self::resolve_room_member_identity( $p['member_identity'] ?? '' ); if ( is_wp_error( $identity ) ) { return $identity; }
        $role = sanitize_key( $p['role'] ?? 'researcher' ); if ( ! in_array( $role, array( 'owner', 'editor', 'researcher', 'viewer' ), true ) ) { $role = 'researcher'; }
        $member_status = sanitize_key( $p['status'] ?? 'active' ); if ( ! in_array( $member_status, array( 'active', 'invited', 'removed' ), true ) ) { $member_status = 'active'; }
        return self::respond( self::backend_request( '/v1/research/rooms/' . rawurlencode( $room_id ) . '/members', 'POST', array(
            'room_id' => $room_id, 'member_ref' => $identity['member_ref'], 'display_name' => $identity['display_name'], 'role' => $role, 'status' => $member_status, 'added_by_ref' => self::owner_ref(),
        ) ) );
    }

    public static function rest_room_evidence( WP_REST_Request $request ) {
        $room_id = sanitize_text_field( $request['room_id'] ); $access = self::authorized_room( $room_id, false, false ); if ( is_wp_error( $access ) ) { return $access; }
        return self::respond( self::backend_request( '/v1/research/rooms/' . rawurlencode( $room_id ) . '/evidence?member_ref=' . rawurlencode( self::owner_ref() ), 'GET' ) );
    }

    public static function rest_room_evidence_save( WP_REST_Request $request ) {
        $p = self::checked_json( $request ); if ( is_wp_error( $p ) ) { return $p; }
        $room_id = sanitize_text_field( $request['room_id'] ); $access = self::authorized_room( $room_id, true, false ); if ( is_wp_error( $access ) ) { return $access; }
        $object_id = sanitize_text_field( $p['object_id'] ?? '' ); $object = self::authorized_library_object( $object_id ); if ( is_wp_error( $object ) ) { return $object; }
        $state = sanitize_key( $p['state'] ?? 'proposed' ); if ( ! in_array( $state, array( 'proposed', 'included', 'disputed', 'removed' ), true ) ) { $state = 'proposed'; }
        return self::respond( self::backend_request( '/v1/research/rooms/' . rawurlencode( $room_id ) . '/evidence', 'POST', array(
            'room_id' => $room_id, 'object_id' => $object_id, 'state' => $state, 'note' => sanitize_textarea_field( $p['note'] ?? '' ), 'contributed_by_ref' => self::owner_ref(),
        ) ) );
    }

    public static function rest_room_questions( WP_REST_Request $request ) {
        $room_id = sanitize_text_field( $request['room_id'] ); $access = self::authorized_room( $room_id, false, false ); if ( is_wp_error( $access ) ) { return $access; }
        return self::respond( self::backend_request( '/v1/research/rooms/' . rawurlencode( $room_id ) . '/questions?member_ref=' . rawurlencode( self::owner_ref() ), 'GET' ) );
    }

    public static function rest_room_question_save( WP_REST_Request $request ) {
        $p = self::checked_json( $request ); if ( is_wp_error( $p ) ) { return $p; }
        $room_id = sanitize_text_field( $request['room_id'] ); $access = self::authorized_room( $room_id, true, false ); if ( is_wp_error( $access ) ) { return $access; }
        $status = sanitize_key( $p['status'] ?? 'open' ); if ( ! in_array( $status, array( 'open', 'resolved', 'deferred', 'dismissed' ), true ) ) { $status = 'open'; }
        $payload = array( 'question_id' => sanitize_text_field( $p['question_id'] ?? '' ), 'room_id' => $room_id, 'question' => sanitize_textarea_field( $p['question'] ?? '' ), 'status' => $status, 'linked_object_ids' => self::sanitize_list( $p['linked_object_ids'] ?? array(), 100 ), 'created_by_ref' => self::owner_ref(), 'resolution' => sanitize_textarea_field( $p['resolution'] ?? '' ) );
        if ( ! empty( $p['question_id'] ) && 'open' !== $status ) { $payload['resolved_by_ref'] = self::owner_ref(); }
        return self::respond( self::backend_request( '/v1/research/rooms/' . rawurlencode( $room_id ) . '/questions', 'POST', $payload ) );
    }

    public static function rest_room_disagreements( WP_REST_Request $request ) {
        $room_id = sanitize_text_field( $request['room_id'] ); $access = self::authorized_room( $room_id, false, false ); if ( is_wp_error( $access ) ) { return $access; }
        return self::respond( self::backend_request( '/v1/research/rooms/' . rawurlencode( $room_id ) . '/disagreements?member_ref=' . rawurlencode( self::owner_ref() ), 'GET' ) );
    }

    public static function rest_room_disagreement_save( WP_REST_Request $request ) {
        $p = self::checked_json( $request ); if ( is_wp_error( $p ) ) { return $p; }
        $room_id = sanitize_text_field( $request['room_id'] ); $access = self::authorized_room( $room_id, true, false ); if ( is_wp_error( $access ) ) { return $access; }
        $status = sanitize_key( $p['status'] ?? 'open' ); if ( ! in_array( $status, array( 'open', 'resolved', 'deferred', 'dismissed' ), true ) ) { $status = 'open'; }
        $position = sanitize_textarea_field( $p['position'] ?? '' );
        $positions = $position ? array( array( 'participant_ref' => self::owner_ref(), 'position' => $position, 'note' => sanitize_textarea_field( $p['position_note'] ?? '' ) ) ) : array();
        $payload = array( 'disagreement_id' => sanitize_text_field( $p['disagreement_id'] ?? '' ), 'room_id' => $room_id, 'statement' => sanitize_textarea_field( $p['statement'] ?? '' ), 'status' => $status, 'linked_object_ids' => self::sanitize_list( $p['linked_object_ids'] ?? array(), 100 ), 'created_by_ref' => self::owner_ref(), 'positions' => $positions, 'resolution' => sanitize_textarea_field( $p['resolution'] ?? '' ) );
        if ( ! empty( $p['disagreement_id'] ) && 'resolved' === $status ) { $payload['resolved_by_ref'] = self::owner_ref(); }
        return self::respond( self::backend_request( '/v1/research/rooms/' . rawurlencode( $room_id ) . '/disagreements', 'POST', $payload ) );
    }

    public static function rest_room_activity( WP_REST_Request $request ) {
        $room_id = sanitize_text_field( $request['room_id'] ); $access = self::authorized_room( $room_id, false, false ); if ( is_wp_error( $access ) ) { return $access; }
        return self::respond( self::backend_request( '/v1/research/rooms/' . rawurlencode( $room_id ) . '/activity?member_ref=' . rawurlencode( self::owner_ref() ) . '&limit=200', 'GET' ) );
    }

    public static function rest_room_synthesis( WP_REST_Request $request ) {
        $room_id = sanitize_text_field( $request['room_id'] ); $access = self::authorized_room( $room_id, false, false ); if ( is_wp_error( $access ) ) { return $access; }
        return self::respond( self::backend_request( '/v1/research/rooms/' . rawurlencode( $room_id ) . '/synthesis?member_ref=' . rawurlencode( self::owner_ref() ), 'GET' ) );
    }

    public static function rest_save_context( WP_REST_Request $request ) {
        $p=self::checked_json($request); if(is_wp_error($p)){return $p;}
        if(!empty($p['context_id'])){$existing=self::authorized_context($p['context_id']);if(is_wp_error($existing)){return $existing;}}
        $project_id=sanitize_text_field($p['project_id']??''); if($project_id){$project=self::authorized_project($project_id,false);if(is_wp_error($project)){return $project;}}
        $room_id=sanitize_text_field($p['room_id']??''); if($room_id){$room=self::authorized_room($room_id,false,false);if(is_wp_error($room)){return $room;}}
        $payload=array('context_id'=>sanitize_text_field($p['context_id']??''),'title'=>sanitize_text_field($p['title']??'Research context'),'owner_ref'=>self::owner_ref(),'scopes'=>self::sanitize_list($p['scopes']??array(),4),'project_id'=>$project_id,'room_id'=>$room_id,'selected_object_ids'=>self::sanitize_list($p['selected_object_ids']??array(),200),'filters'=>self::sanitize_tree($p['filters']??array()),'active'=>!isset($p['active'])||!empty($p['active']));
        return self::respond(self::backend_request('/v1/research/contexts','POST',$payload));
    }

    public static function rest_workflow( WP_REST_Request $request ) { $p=self::checked_json($request); if(is_wp_error($p)){return $p;} $access=self::authorized_project($p['project_id']??'',true); if(is_wp_error($access)){return $access;} return self::respond(self::backend_request('/v1/workflows/template','POST',array('project_id'=>sanitize_text_field($p['project_id']??''),'investigation_id'=>sanitize_text_field($p['investigation_id']??''),'kind'=>sanitize_key($p['kind']??'evidence-review'),'title'=>sanitize_text_field($p['title']??''),'persist'=>true))); }
    public static function rest_contradictions( WP_REST_Request $request ) { $p=self::checked_json($request); if(is_wp_error($p)){return $p;} $access=self::authorized_project($p['project_id']??'',true); if(is_wp_error($access)){return $access;} return self::respond(self::backend_request('/v1/research/contradictions','POST',array('project_id'=>sanitize_text_field($p['project_id']??''),'items'=>self::sanitize_tree(array_slice(is_array($p['items']??null)?$p['items']:array(),0,500)),'persist'=>true))); }
    public static function rest_uncertainties( WP_REST_Request $request ) { $p=self::checked_json($request); if(is_wp_error($p)){return $p;} $access=self::authorized_project($p['project_id']??'',true); if(is_wp_error($access)){return $access;} return self::respond(self::backend_request('/v1/research/uncertainties','POST',array('project_id'=>sanitize_text_field($p['project_id']??''),'items'=>self::sanitize_tree(array_slice(is_array($p['items']??null)?$p['items']:array(),0,200)),'persist'=>true))); }
    public static function rest_backup( WP_REST_Request $request ) { $p=self::checked_json($request); if(is_wp_error($p)){return $p;} $access=self::authorized_project($request['project_id'],true); if(is_wp_error($access)){return $access;} return self::respond(self::backend_request('/v1/projects/'.rawurlencode(sanitize_text_field($request['project_id'])).'/backup','POST',array())); }
    public static function rest_export() { return self::respond( self::backend_request( '/v1/platform/backups?limit=100', 'GET' ) ); }

    public static function register_admin_menu() { add_submenu_page( 'options-general.php', 'Connected Research Intelligence Platform', 'Connected Research Platform', 'manage_options', 'sc-connected-research-platform', array( __CLASS__, 'render_admin' ) ); }

    public static function render_admin() {
        if ( ! self::can_manage() ) { return; }
        if ( isset( $_POST['sc_rl_v700_save'] ) && check_admin_referer( 'sc_rl_v700_save' ) ) {
            $d=self::defaults(); $clean=array();
            foreach($d as $key=>$value){if('workspace_mode'===$key){$candidate=sanitize_key($_POST[$key]??$value);$clean[$key]=in_array($candidate,array('public','editorial','institutional'),true)?$candidate:'public';}elseif('default_visibility'===$key){$candidate=sanitize_key($_POST[$key]??$value);$clean[$key]=in_array($candidate,array('private','shared','public'),true)?$candidate:'private';}else{$clean[$key]=isset($_POST[$key])?'1':'0';}}
            update_option(self::OPTION_NAME,$clean,false); echo '<div class="notice notice-success"><p>Connected Research Platform settings saved.</p></div>';
        }
        $o=self::options(); $status=self::backend_request('/v1/platform/summary','GET'); $api=self::backend_request('/v1/platform/api','GET'); ?>
        <div class="wrap"><h1>Connected Research Intelligence Platform</h1><p>v7.5.0 adds collaborative Research Rooms with explicit membership roles, shared evidence state, attributable questions and disagreements, participant activity, and room-level synthesis. Individual state remains separate from shared room state.</p>
        <div class="card"><h2>Platform state</h2><p><strong>Backend:</strong> <?php echo is_wp_error($status)?esc_html($status->get_error_message()):'Connected'; ?></p><p><strong>Stable API:</strong> <?php echo is_wp_error($api)?'Unavailable':esc_html($api['schema']??self::API_SCHEMA); ?></p><p><strong>Object model:</strong> <?php echo esc_html(self::OBJECT_MODEL_SCHEMA); ?></p><?php if(!is_wp_error($status)&&!empty($status['counts'])):?><ul><?php foreach($status['counts'] as $key=>$value):?><li><strong><?php echo esc_html(ucwords(str_replace('_',' ',$key))); ?>:</strong> <?php echo esc_html(absint($value)); ?></li><?php endforeach;?></ul><?php endif;?></div>
        <form method="post"><?php wp_nonce_field('sc_rl_v700_save');?><table class="form-table"><tbody><tr><th>Workspace mode</th><td><select name="workspace_mode"><?php foreach(array('public'=>'Public','editorial'=>'Editorial','institutional'=>'Institutional') as $value=>$label):?><option value="<?php echo esc_attr($value);?>" <?php selected($o['workspace_mode'],$value);?>><?php echo esc_html($label);?></option><?php endforeach;?></select></td></tr><tr><th>Default visibility</th><td><select name="default_visibility"><?php foreach(array('private'=>'Private','shared'=>'Shared','public'=>'Public') as $value=>$label):?><option value="<?php echo esc_attr($value);?>" <?php selected($o['default_visibility'],$value);?>><?php echo esc_html($label);?></option><?php endforeach;?></select></td></tr><tr><th>Capabilities</th><td><?php foreach(array('persistent_projects'=>'Persistent projects','portable_backups'=>'Portable backup and recovery','contradiction_analysis'=>'Contradiction tracking','uncertainty_registers'=>'Uncertainty registers','workflow_templates'=>'Reusable workflow templates','library_object_model'=>'Library object model','contextual_research'=>'Context-aware research','personal_library_separation'=>'Personal/editorial collection separation','source_scope_provenance'=>'Source-scope provenance','human_publication_review'=>'Human publication review','source_evaluation'=>'Descriptive source evaluation','evidence_comparison'=>'Evidence comparison','evidence_gap_detection'=>'Evidence-gap detection','persistent_research_state'=>'Persistent research state','reading_review_history'=>'Reading and review history','open_question_register'=>'Open-question register','research_rooms'=>'Collaborative Research Rooms','room_membership_roles'=>'Room membership roles','shared_evidence_state'=>'Shared evidence state','collaborative_questions'=>'Collaborative room questions','room_disagreements'=>'Attributed disagreements','participant_activity'=>'Participant activity','room_synthesis'=>'Room-level synthesis','api_public_status'=>'Public platform status') as $key=>$label):?><label style="display:block;margin:0 0 8px"><input type="checkbox" name="<?php echo esc_attr($key);?>" <?php checked($o[$key],'1');?>> <?php echo esc_html($label);?></label><?php endforeach;?></td></tr></tbody></table><?php submit_button('Save Platform Settings','primary','sc_rl_v700_save');?></form>
        <p><code>[sc_connected_research_workspace]</code> renders the authenticated project and research-context workspace. <code>[sc_research_projects_summary]</code> and <code>[sc_connected_research_platform_status]</code> render compact summaries.</p></div><?php
    }

    private static function enqueue_workspace_assets() {
        wp_enqueue_style( 'sc-research-librarian-ai' );
        wp_enqueue_script( 'sc-rl-v700-connected-platform', plugins_url( '../assets/sc-research-platform-v7.js', __FILE__ ), array(), self::VERSION, true );
        wp_enqueue_script( 'sc-rl-v750-research-rooms', plugins_url( '../assets/sc-research-platform-v750-rooms.js', __FILE__ ), array( 'sc-rl-v700-connected-platform' ), self::VERSION, true );
        wp_localize_script( 'sc-rl-v700-connected-platform', 'SCRLPlatformV7', array( 'root' => esc_url_raw( rest_url( self::REST_NAMESPACE . '/platform/v7/' ) ), 'nonce' => wp_create_nonce( 'wp_rest' ), 'authenticated' => is_user_logged_in(), 'workspaceMode' => self::options()['workspace_mode'], 'objectModelSchema' => self::OBJECT_MODEL_SCHEMA, 'contextSchema' => self::CONTEXT_SCHEMA, 'qualitySchema' => self::QUALITY_SCHEMA, 'stateSchema' => self::STATE_SCHEMA, 'roomSchema' => self::ROOM_SCHEMA, 'roomSynthesisSchema' => self::ROOM_SYNTHESIS_SCHEMA ) );
    }

    public static function render_workspace() {
        self::enqueue_workspace_assets(); ob_start(); ?>
        <section class="sc-rl-v7-platform sc-rl-v7-platform--context" data-sc-rl-v7-workspace>
          <header><p class="sc-rl-product__eyebrow">Connected Research Intelligence Platform</p><h2>Research Projects, Context, Evidence Quality, Research State &amp; Rooms</h2><p>Move between Sustainable Catalyst's editorial collection, your private Library, active projects, and collaborative Research Rooms while preserving personal and shared provenance. Room synthesis keeps participant attribution visible and remains separate from factual evidence and editorial approval.</p></header>
          <div class="sc-rl-v720-context-model" aria-label="Research context model">
            <article><span>Editorial</span><strong>Sustainable Catalyst Collection</strong><p>Public knowledge and official editorial recommendations.</p></article>
            <article><span>Private</span><strong>My Library</strong><p>Your saved sources, recommendations, searches, watchlists, and queue.</p></article>
            <article><span>Working</span><strong>Current Project</strong><p>Project-linked evidence, bundles, pathways, and investigations.</p></article>
            <article><span>Collaborative</span><strong>Research Room</strong><p>Shared room context remains distinct from editorial approval.</p></article>
          </div>
          <?php if(!is_user_logged_in()):?><div class="sc-rl-v7-notice"><strong>Public collection context</strong><p>Sign in to use private Library, project, and Research Room context. The public Research Librarian remains available without an account.</p></div><?php else:?>
          <div class="sc-rl-v720-context-toolbar" data-sc-rl-v720-context-toolbar>
            <div><span>Active Librarian context</span><strong data-sc-rl-v720-context-label>Loading…</strong><small data-sc-rl-v720-context-detail>Checking your saved research context.</small></div>
            <label>Context<select data-sc-rl-v720-context-select aria-label="Active Research Librarian context"><option value="">Sustainable Catalyst Collection</option></select></label>
            <button type="button" data-sc-rl-v720-context-new>New context</button>
            <button type="button" data-sc-rl-v730-quality-run>Evaluate context</button>
            <button type="button" data-sc-rl-v740-state-run>Research state</button>
            <button type="button" data-sc-rl-v750-room-run>Research rooms</button>
          </div>
          <form class="sc-rl-v720-context-form" data-sc-rl-v720-context-form hidden>
            <label>Context name<input name="title" maxlength="240" value="My Library research"></label>
            <label>Scope<select name="scope"><option value="my-library">My Library</option><option value="sustainable-catalyst-collection">Sustainable Catalyst Collection</option><option value="current-project">Current Project</option><option value="current-research-room">Current Research Room</option></select></label>
            <label>Project<select name="project_id" data-sc-rl-v720-context-project><option value="">No project</option></select></label>
            <label>Research Room<select name="room_id" data-sc-rl-v750-context-room><option value="">No Research Room</option></select></label>
            <button type="submit">Save context</button><button type="button" data-sc-rl-v720-context-cancel>Cancel</button><p role="status" aria-live="polite" data-sc-rl-v720-context-status></p>
          </form>
          <section class="sc-rl-v730-quality-panel" data-sc-rl-v730-quality-panel hidden aria-live="polite">
            <header><p class="sc-rl-product__eyebrow">Evidence Quality Signals</p><h3>Context evidence review</h3><p>Descriptive source metadata and structural gaps only. No automatic credibility or truth score is assigned.</p></header>
            <div data-sc-rl-v730-quality-content><p>Select an authenticated context and run an evaluation.</p></div>
          </section>
          <section class="sc-rl-v740-state-panel" data-sc-rl-v740-state-panel hidden aria-live="polite">
            <header><p class="sc-rl-product__eyebrow">Persistent Research State</p><h3>Research continuity</h3><p>Inspect recent searches, reading/review state, rejected material, contradiction flags, and unresolved questions. These records describe your workflow; they are not evidence.</p></header>
            <div data-sc-rl-v740-state-content><p>Select an authenticated context and load its research state.</p></div>
            <form class="sc-rl-v740-question-form" data-sc-rl-v740-question-form hidden>
              <label>Open research question<textarea name="question" rows="3" maxlength="3000" required></textarea></label>
              <div><button type="submit">Add open question</button><button type="button" data-sc-rl-v740-question-cancel>Cancel</button></div>
              <p role="status" aria-live="polite" data-sc-rl-v740-question-status></p>
            </form>
          </section>
          <section class="sc-rl-v750-room-panel" data-sc-rl-v750-room-panel hidden aria-live="polite">
            <header><p class="sc-rl-product__eyebrow">Collaborative Research Room Intelligence</p><h3>Shared research with participant attribution</h3><p>Room evidence state, questions, disagreements, and activity are collaborative workflow records. Individual reading history remains personal, and room synthesis is not factual verification or editorial approval.</p></header>
            <div class="sc-rl-v750-room-toolbar"><label>Research Room<select data-sc-rl-v750-room-select><option value="">Choose a room</option></select></label><button type="button" data-sc-rl-v750-room-refresh>Refresh room</button></div>
            <div data-sc-rl-v750-room-content><p>Create or select a Research Room to inspect shared research state.</p></div>
            <div class="sc-rl-v750-room-forms">
              <form data-sc-rl-v750-room-create><h4>New Research Room</h4><label>Room title<input name="title" maxlength="240" required></label><label>Shared objective<textarea name="objective" rows="3" maxlength="5000"></textarea></label><label>Related project<select name="project_id" data-sc-rl-v750-room-project><option value="">No project</option></select></label><button type="submit">Create room</button><p role="status" data-sc-rl-v750-room-create-status></p></form>
              <form data-sc-rl-v750-member-form hidden><h4>Add participant</h4><label>WordPress account<input name="member_identity" placeholder="Username, email, or user ID" required></label><label>Role<select name="role"><option value="researcher">Researcher</option><option value="viewer">Viewer</option><option value="editor">Editor</option></select></label><button type="submit">Add participant</button><p role="status" data-sc-rl-v750-member-status></p></form>
              <form data-sc-rl-v750-evidence-form hidden><h4>Share evidence</h4><label>Library object<select name="object_id" data-sc-rl-v750-room-object required><option value="">Choose a Library object</option></select></label><label>Shared state<select name="state"><option value="proposed">Proposed</option><option value="included">Included</option><option value="disputed">Disputed</option></select></label><label>Note<textarea name="note" rows="2" maxlength="4000"></textarea></label><button type="submit">Share with room</button><p role="status" data-sc-rl-v750-evidence-status></p></form>
              <form data-sc-rl-v750-room-question-form hidden><h4>Collaborative question</h4><label>Question<textarea name="question" rows="3" maxlength="3000" required></textarea></label><button type="submit">Add room question</button><p role="status" data-sc-rl-v750-room-question-status></p></form>
              <form data-sc-rl-v750-disagreement-form hidden><h4>Record a disagreement</h4><label>Issue or statement<textarea name="statement" rows="3" maxlength="4000" required></textarea></label><label>Your position<textarea name="position" rows="3" maxlength="3000" required></textarea></label><button type="submit">Add attributed position</button><p role="status" data-sc-rl-v750-disagreement-status></p></form>
            </div>
          </section>
          <div class="sc-rl-v7-layout"><aside class="sc-rl-v7-create"><h3>New project</h3><form data-sc-rl-v7-project-form><label>Project title<input name="title" required maxlength="240"></label><label>Research objective<textarea name="objective" rows="5" maxlength="4000"></textarea></label><button type="submit">Create project</button><p role="status" aria-live="polite" data-sc-rl-v7-form-status></p></form><div class="sc-rl-v720-library-summary" data-sc-rl-v720-library-summary><strong>Library objects</strong><p>Loading your Library object model…</p></div></aside><div><div class="sc-rl-v7-toolbar"><h3>Your projects</h3><button type="button" data-sc-rl-v7-refresh>Refresh</button></div><div data-sc-rl-v7-projects role="region" aria-live="polite"><p>Loading research projects…</p></div></div></div><?php endif;?>
        </section><?php return ob_get_clean();
    }

    public static function render_summary() { $status=self::backend_request('/v1/platform/summary','GET'); $counts=is_wp_error($status)?array('projects'=>0,'investigations'=>0,'entities'=>0,'library_objects'=>0,'research_contexts'=>0,'backups'=>0):($status['counts']??array()); ob_start();?><section class="sc-rl-v7-summary"><p class="sc-rl-product__eyebrow">Connected Research Platform</p><h2>Research Workspace Summary</h2><div class="sc-rl-product__grid"><?php foreach($counts as $key=>$value):?><article><span><?php echo esc_html(absint($value));?></span><strong><?php echo esc_html(ucwords(str_replace('_',' ',$key)));?></strong></article><?php endforeach;?></div></section><?php return ob_get_clean(); }
    public static function render_status() { $status=self::backend_request('/v1/platform/summary','GET'); $connected=!is_wp_error($status); ob_start();?><section class="sc-rl-governance sc-rl-governance--status"><p class="sc-rl-product__eyebrow">Platform Status</p><h2>Connected Research Intelligence</h2><div class="sc-rl-product__grid"><article><span><?php echo $connected?'Connected':'Fallback';?></span><strong>Platform state</strong><p><?php echo $connected?'Persistent project, Library-context, evidence-quality, research-state, and collaborative room services are available.':'The public Librarian remains available; private research context requires the backend.';?></p></article><article><span>v7.5.0</span><strong>Stable API</strong><p><?php echo esc_html(self::API_SCHEMA);?></p></article><article><span>Collaborative</span><strong>Research Rooms</strong><p>Shared evidence, questions, disagreements, and synthesis preserve participant attribution and remain separate from personal research state.</p></article></div></section><?php return ob_get_clean(); }
}
