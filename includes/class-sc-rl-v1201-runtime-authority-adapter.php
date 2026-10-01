<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * v12.0.1 WordPress thin-adapter declaration.
 *
 * This class does not move canonical runtime state into WordPress. It exposes
 * the transition contract so WordPress can remain an optional presentation and
 * proxy surface while the Python backend remains authoritative.
 */
final class SC_RL_V1201_Runtime_Authority_Adapter {
    const VERSION = '12.0.1';
    const CONTRACT = 'sc-research-librarian-wordpress-thin-adapter/1.0';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ), 120 );
    }

    public static function register_routes() {
        register_rest_route(
            'sc-research-librarian-ai/v1',
            '/runtime-authority',
            array(
                'methods'             => 'GET',
                'callback'            => array( __CLASS__, 'runtime_authority' ),
                'permission_callback' => '__return_true',
            )
        );
    }

    public static function runtime_authority() {
        return rest_ensure_response(
            array(
                'schema'                      => self::CONTRACT,
                'version'                     => self::VERSION,
                'adapter_type'                => 'optional-wordpress-interface',
                'backend_authoritative'       => true,
                'wordpress_runtime_authority' => false,
                'wordpress_required'          => false,
                'backend_health_source'       => '/health',
                'backend_runtime_authority_source' => '/v1/core/runtime-authority/manifest',
                'canonical_state_location'    => 'python-backend-and-governed-platform-services',
                'transition'                  => 'progressive-decoupling',
            )
        );
    }
}
