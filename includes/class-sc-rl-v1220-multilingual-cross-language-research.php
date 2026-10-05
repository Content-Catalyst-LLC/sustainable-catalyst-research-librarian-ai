<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Research Librarian v12.2.0 — Multilingual & Cross-Language Research Intelligence.
 *
 * Passive WordPress-side manifest only. Language identity, original-language
 * research context, derived representation provenance, alignments, query plans,
 * retrieval receipts, and snapshots are authoritative in Python/FastAPI.
 */
final class SC_RL_V1220_Multilingual_Cross_Language_Research {
    const VERSION = '12.2.0';
    const CONTRACT = 'sc-research-librarian-multilingual-cross-language-research/1.0';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ), 129 );
    }

    public static function register_routes() {
        register_rest_route(
            self::REST_NAMESPACE,
            '/multilingual-research',
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
                'name'                                => 'Multilingual & Cross-Language Research Intelligence',
                'runtime_authority'                   => 'python-fastapi-backend',
                'wordpress_required'                  => false,
                'wordpress_runtime_authority'         => false,
                'wordpress_canonical_state'           => false,
                'analyze_original_language_first'     => true,
                'translation_is_derived'              => true,
                'transliteration_is_derived'          => true,
                'preserve_transformation_provenance'  => true,
                'platform_core_language_authority'    => true,
                'global_source_federation'            => false,
                'automatic_entity_resolution'         => false,
                'automatic_citation_resolution'       => false,
                'automatic_evidence_resolution'       => false,
                'automatic_truth_promotion'           => false,
                'backend_manifest_path'               => '/v1/research-librarian/multilingual-research/manifest',
                'backend_capabilities_path'           => '/v1/research-librarian/multilingual-research/capabilities',
                'next_boundary'                       => 'global-source-federation-original-language-research',
            )
        );
    }
}
