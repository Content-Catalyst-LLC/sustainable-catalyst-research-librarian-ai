<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class SC_RL_V1205_Identity_Session_Access_Adapter {
    const VERSION = '12.0.5';
    const CONTRACT = 'sc-research-librarian-access-context/1.0';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ), 124 );
    }

    public static function register_routes() {
        register_rest_route(
            'sc-research-librarian-ai/v1',
            '/identity-session-access',
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
                'schema'                       => self::CONTRACT,
                'version'                      => self::VERSION,
                'identity_authority'           => 'python-fastapi-backend',
                'identity_sessions'            => true,
                'identity_owned_research'      => true,
                'wordpress_required'           => false,
                'wordpress_identity_authority' => false,
                'wordpress_session_authority'  => false,
                'wordpress_role'               => 'optional-thin-adapter',
                'legacy_api_key'               => 'server-integration-only',
                'next_boundary'                => 'thin-wordpress-adapter',
            )
        );
    }
}
