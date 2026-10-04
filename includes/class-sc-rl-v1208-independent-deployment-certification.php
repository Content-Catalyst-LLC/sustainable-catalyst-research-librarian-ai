<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Research Librarian v12.0.8 — Independent Deployment & WordPress-Failure Certification.
 *
 * Passive WordPress-side release manifest only. The certification runtime lives
 * in Python/FastAPI. This class does not proxy certification requests, does not
 * hold backend credentials, and does not claim WordPress runtime authority.
 */
final class SC_RL_V1208_Independent_Deployment_Certification {
    const VERSION = '12.0.8';
    const CONTRACT = 'sc-research-librarian-independent-deployment-certification/1.0';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ), 127 );
    }

    public static function register_routes() {
        register_rest_route(
            self::REST_NAMESPACE,
            '/independent-certification',
            array(
                'methods'             => WP_REST_Server::READABLE,
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
                'name'                         => 'Independent Deployment & WordPress-Failure Certification',
                'runtime_authority'            => 'python-fastapi-backend',
                'wordpress_required'           => false,
                'wordpress_optional'           => true,
                'wordpress_runtime_authority'  => false,
                'wordpress_identity_authority' => false,
                'wordpress_session_authority'  => false,
                'wordpress_canonical_state'    => false,
                'backend_certification_path'   => '/v1/research-librarian/independence/report',
                'backend_manifest_path'        => '/v1/research-librarian/independence/manifest',
                'wordpress_proxies_report'     => false,
                'wordpress_holds_credentials'  => false,
                'failure_behavior'             => 'backend-remains-operational-wordpress-surface-unavailable',
                'next_boundary'                => 'neural-research-intelligence-foundation',
            )
        );
    }
}
