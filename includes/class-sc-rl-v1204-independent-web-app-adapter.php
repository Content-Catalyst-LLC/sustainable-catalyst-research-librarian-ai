<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class SC_RL_V1204_Independent_Web_App_Adapter {
    const VERSION = '12.0.4';
    const CONTRACT = 'sc-research-librarian-independent-web-app/1.0';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ), 123 );
    }

    public static function register_routes() {
        register_rest_route(
            'sc-research-librarian-ai/v1',
            '/independent-web-app',
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
                'schema'                 => self::CONTRACT,
                'version'                => self::VERSION,
                'standalone_app_path'    => '/research-librarian/',
                'backend_authoritative'  => true,
                'wordpress_required'     => false,
                'wordpress_role'         => 'optional-thin-adapter',
                'wordpress_hosts_app'    => false,
                'wordpress_stores_state' => false,
                'identity_sessions'      => false,
                'next_boundary'          => 'identity-session-access-runtime',
            )
        );
    }
}
