<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class SC_RL_V1203_Persistent_Session_Adapter {
    const VERSION = '12.0.3';
    const CONTRACT = 'sc-research-librarian-persistent-research-session/1.0';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ), 122 );
    }

    public static function register_routes() {
        register_rest_route(
            'sc-research-librarian-ai/v1',
            '/persistent-sessions',
            array(
                'methods'             => 'GET',
                'callback'            => array( __CLASS__, 'manifest' ),
                'permission_callback' => '__return_true',
            )
        );
    }

    public static function manifest() {
        return rest_ensure_response(
            array(
                'schema'                  => self::CONTRACT,
                'version'                 => self::VERSION,
                'backend_base_path'       => '/v1/research-librarian/sessions',
                'backend_authoritative'   => true,
                'wordpress_required'      => false,
                'wordpress_stores_turns'  => false,
                'persistent_sessions'     => true,
                'persistent_conversations'=> true,
                'identity_sessions'       => false,
                'client_ref_is_identity'  => false,
                'next_boundary'           => 'independent-web-app-foundation',
            )
        );
    }
}
