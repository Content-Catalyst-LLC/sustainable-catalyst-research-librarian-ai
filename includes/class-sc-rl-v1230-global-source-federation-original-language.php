<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Research Librarian v12.3.0 — Global Source Federation & Original-Language Research.
 * Passive WordPress-side manifest only; Python/FastAPI is authoritative.
 */
final class SC_RL_V1230_Global_Source_Federation_Original_Language {
    const VERSION = '12.3.0';
    const CONTRACT = 'sc-research-librarian-global-source-federation-original-language/1.0';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ), 130 );
    }

    public static function register_routes() {
        register_rest_route(
            self::REST_NAMESPACE,
            '/global-source-federation',
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
                'schema'                                => self::CONTRACT,
                'version'                               => self::VERSION,
                'name'                                  => 'Global Source Federation & Original-Language Research',
                'runtime_authority'                     => 'python-fastapi-backend',
                'wordpress_required'                    => false,
                'wordpress_runtime_authority'           => false,
                'wordpress_canonical_state'             => false,
                'global_source_federation'              => true,
                'original_language_source_research'     => true,
                'source_quality_trust_separation'       => true,
                'knowledge_library_ingestion_authority' => true,
                'automatic_remote_crawling'             => false,
                'automatic_entity_resolution'           => false,
                'automatic_toponym_resolution'          => false,
                'automatic_citation_resolution'         => false,
                'automatic_evidence_resolution'         => false,
                'automatic_truth_promotion'             => false,
                'backend_manifest_path'                 => '/v1/research-librarian/global-source-federation/manifest',
                'backend_capabilities_path'             => '/v1/research-librarian/global-source-federation/capabilities',
                'next_boundary'                         => 'cross-language-entity-toponym-resolution',
            )
        );
    }
}
