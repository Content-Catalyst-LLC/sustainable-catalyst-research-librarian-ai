<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class SC_RL_V1202_Independent_API_Adapter {
    const VERSION = '12.0.2';
    const CONTRACT = 'sc-research-librarian-independent-api/1.0';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ), 121 );
    }

    public static function register_routes() {
        register_rest_route(
            'sc-research-librarian-ai/v1',
            '/independent-api',
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
                'schema'                => self::CONTRACT,
                'version'               => self::VERSION,
                'api_version'           => 'v1',
                'backend_base_path'     => '/v1/research-librarian',
                'backend_authoritative' => true,
                'wordpress_required'    => false,
                'wordpress_role'        => 'optional-thin-adapter',
                'persistent_sessions'   => false,
                'identity_sessions'     => false,
                'next_boundary'         => 'persistent-research-session-and-conversation-runtime',
            )
        );
    }
}
