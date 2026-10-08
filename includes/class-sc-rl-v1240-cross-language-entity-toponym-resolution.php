<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Research Librarian v12.4.0 — Cross-Language Entity & Toponym Resolution.
 * Passive WordPress-side manifest only; Python/FastAPI is authoritative.
 */
final class SC_RL_V1240_Cross_Language_Entity_Toponym_Resolution {
    const VERSION = '12.4.0';
    const CONTRACT = 'sc-research-librarian-cross-language-entity-toponym-resolution/1.0';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ), 140 );
    }

    public static function register_routes() {
        register_rest_route(
            self::REST_NAMESPACE,
            '/cross-language-entity-toponym-resolution',
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
                'schema'                              => self::CONTRACT,
                'version'                             => self::VERSION,
                'name'                                => 'Cross-Language Entity & Toponym Resolution',
                'runtime_authority'                   => 'python-fastapi-backend',
                'wordpress_required'                  => false,
                'wordpress_runtime_authority'         => false,
                'wordpress_canonical_state'           => false,
                'cross_language_entity_resolution'    => true,
                'cross_language_toponym_resolution'   => true,
                'alias_alignment'                     => true,
                'human_review_required'               => true,
                'automatic_identity_promotion'        => false,
                'automatic_remote_geocoding'          => false,
                'automatic_citation_resolution'       => false,
                'automatic_evidence_resolution'       => false,
                'automatic_truth_promotion'           => false,
                'backend_manifest_path'               => '/v1/research-librarian/cross-language-entity-toponym-resolution/manifest',
                'backend_capabilities_path'           => '/v1/research-librarian/cross-language-entity-toponym-resolution/capabilities',
                'next_boundary'                       => 'cross-language-citation-evidence-resolution',
            )
        );
    }
}
