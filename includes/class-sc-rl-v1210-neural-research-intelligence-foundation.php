<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Research Librarian v12.1.0 — Neural Research Intelligence Foundation.
 *
 * Passive WordPress-side manifest only. Neural research state, model/data/
 * representation lineage, runtime handoffs, and snapshots are authoritative in
 * the Python/FastAPI backend. WordPress does not execute neural workloads.
 */
final class SC_RL_V1210_Neural_Research_Intelligence_Foundation {
    const VERSION = '12.1.0';
    const CONTRACT = 'sc-research-librarian-neural-research-intelligence/1.0';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ), 128 );
    }

    public static function register_routes() {
        register_rest_route(
            self::REST_NAMESPACE,
            '/neural-research-foundation',
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
                'name'                         => 'Neural Research Intelligence Foundation',
                'runtime_authority'            => 'python-fastapi-backend',
                'wordpress_required'           => false,
                'wordpress_runtime_authority'  => false,
                'wordpress_canonical_state'    => false,
                'wordpress_neural_execution'   => false,
                'backend_manifest_path'        => '/v1/research-librarian/neural-research/manifest',
                'backend_capabilities_path'    => '/v1/research-librarian/neural-research/capabilities',
                'model_weights_stored'         => false,
                'secrets_stored'               => false,
                'automatic_model_ranking'      => false,
                'automatic_truth_promotion'    => false,
                'platform_core_authority'       => true,
                'specialist_runtime_execution' => true,
                'next_boundary'                => 'multilingual-cross-language-research-intelligence',
            )
        );
    }
}
