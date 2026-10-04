<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Research Librarian v12.0.7 — WordPress State Migration & Compatibility Layer.
 *
 * This class is intentionally read-only against legacy WordPress state.
 * It inventories bounded Research Librarian option/user-meta state, strips
 * secret-bearing fields, prepares explicit backend migration runs, applies only
 * administrator-confirmed runs, and resolves durable backend compatibility
 * aliases. It never deletes legacy state and never makes WordPress canonical.
 */
final class SC_RL_V1207_WordPress_State_Migration_Compatibility {
    const VERSION = '12.0.7';
    const CONTRACT = 'sc-research-librarian-wordpress-state-migration/1.0';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';
    const MAX_CANDIDATES = 5000;
    const MAX_VALUE_BYTES = 262144;

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ), 126 );
    }

    public static function register_routes() {
        register_rest_route(
            self::REST_NAMESPACE,
            '/state-migration',
            array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array( __CLASS__, 'manifest' ),
                'permission_callback' => '__return_true',
            )
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/state-migration/inventory',
            array(
                'methods'             => WP_REST_Server::CREATABLE,
                'callback'            => array( __CLASS__, 'inventory_endpoint' ),
                'permission_callback' => array( __CLASS__, 'can_migrate' ),
            )
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/state-migration/prepare',
            array(
                'methods'             => WP_REST_Server::CREATABLE,
                'callback'            => array( __CLASS__, 'prepare_endpoint' ),
                'permission_callback' => array( __CLASS__, 'can_migrate' ),
            )
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/state-migration/runs/(?P<run_id>[A-Za-z0-9._:-]+)',
            array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array( __CLASS__, 'run_endpoint' ),
                'permission_callback' => array( __CLASS__, 'can_migrate' ),
            )
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/state-migration/runs/(?P<run_id>[A-Za-z0-9._:-]+)/apply',
            array(
                'methods'             => WP_REST_Server::CREATABLE,
                'callback'            => array( __CLASS__, 'apply_endpoint' ),
                'permission_callback' => array( __CLASS__, 'can_migrate' ),
            )
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/state-migration/resolve',
            array(
                'methods'             => WP_REST_Server::CREATABLE,
                'callback'            => array( __CLASS__, 'resolve_endpoint' ),
                'permission_callback' => array( __CLASS__, 'can_read_compatibility' ),
            )
        );
    }

    public static function manifest() {
        return rest_ensure_response(
            array(
                'schema'                          => self::CONTRACT,
                'version'                         => self::VERSION,
                'migration_mode'                  => 'explicit-prepare-apply',
                'automatic_migration'              => false,
                'legacy_state_deleted'             => false,
                'wordpress_required'               => false,
                'wordpress_runtime_authority'      => false,
                'wordpress_canonical_state'        => false,
                'backend_authoritative'            => true,
                'inventory_sources'                => array( 'allowlisted-options', 'allowlisted-user-meta' ),
                'secret_fields_exported'           => false,
                'fixed_source_prefixes'            => array( 'sc_rl_', 'sc_research_librarian_' ),
                'supported_candidate_types'        => array(
                    'project',
                    'research-context',
                    'research-room',
                    'library-object',
                    'persistent-session',
                    'persistent-turn',
                    'compatibility-record',
                ),
                'owner_mapping'                    => 'explicit',
                'conflict_behavior'                => 'fail-closed',
                'compatibility_aliases_authorize'  => false,
                'next_boundary'                    => 'independent-deployment-wordpress-failure-certification',
            )
        );
    }

    public static function can_migrate( WP_REST_Request $request ) {
        if ( ! is_user_logged_in() || ! current_user_can( 'manage_options' ) ) {
            return new WP_Error(
                'sc_rl_v1207_admin_required',
                'WordPress administrator access is required for state migration.',
                array( 'status' => 403 )
            );
        }
        return self::verify_rest_nonce( $request );
    }

    public static function can_read_compatibility( WP_REST_Request $request ) {
        if ( ! is_user_logged_in() || ! current_user_can( 'read' ) ) {
            return new WP_Error(
                'sc_rl_v1207_auth_required',
                'Authenticated WordPress access is required.',
                array( 'status' => 401 )
            );
        }
        return self::verify_rest_nonce( $request );
    }

    private static function verify_rest_nonce( WP_REST_Request $request ) {
        $nonce = (string) $request->get_header( 'x_wp_nonce' );
        if ( '' === $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error(
                'sc_rl_v1207_bad_nonce',
                'WordPress REST nonce validation failed.',
                array( 'status' => 403 )
            );
        }
        return true;
    }

    public static function inventory_endpoint() {
        return rest_ensure_response( self::inventory() );
    }

    public static function prepare_endpoint( WP_REST_Request $request ) {
        $body = $request->get_json_params();
        $body = is_array( $body ) ? $body : array();

        $inventory = self::inventory();
        $owner_map = array();
        if ( isset( $body['owner_map'] ) && is_array( $body['owner_map'] ) ) {
            foreach ( $body['owner_map'] as $legacy_owner => $identity_ref ) {
                $legacy_owner = sanitize_text_field( (string) $legacy_owner );
                $identity_ref = sanitize_text_field( (string) $identity_ref );
                if ( '' !== $legacy_owner && preg_match( '/^identity:[A-Za-z0-9._:-]{1,220}$/', $identity_ref ) ) {
                    $owner_map[ $legacy_owner ] = $identity_ref;
                }
            }
        }

        $actor_ref = isset( $body['actor_ref'] ) ? sanitize_text_field( (string) $body['actor_ref'] ) : '';
        if ( '' !== $actor_ref && ! preg_match( '/^identity:[A-Za-z0-9._:-]{1,220}$/', $actor_ref ) ) {
            return new WP_Error(
                'sc_rl_v1207_invalid_actor_ref',
                'actor_ref must be an explicit Research Librarian identity reference.',
                array( 'status' => 400 )
            );
        }

        $payload = array(
            'source_site'     => home_url( '/' ),
            'source_instance' => self::source_instance(),
            'actor_ref'       => $actor_ref,
            'owner_map'       => $owner_map,
            'inventory_hash'  => '',
            'candidates'      => $inventory['candidates'],
            'note'            => isset( $body['note'] ) ? sanitize_textarea_field( (string) $body['note'] ) : '',
        );

        $upstream = self::backend_request(
            '/v1/research-librarian/wordpress-migration/prepare',
            'POST',
            $payload
        );
        if ( is_wp_error( $upstream ) ) {
            return $upstream;
        }
        return rest_ensure_response( $upstream );
    }

    public static function run_endpoint( WP_REST_Request $request ) {
        $run_id = sanitize_text_field( (string) $request['run_id'] );
        return self::backend_request(
            '/v1/research-librarian/wordpress-migration/runs/' . rawurlencode( $run_id ),
            'GET',
            null
        );
    }

    public static function apply_endpoint( WP_REST_Request $request ) {
        $run_id = sanitize_text_field( (string) $request['run_id'] );
        $body = $request->get_json_params();
        $body = is_array( $body ) ? $body : array();

        $confirmation = isset( $body['confirmation'] ) ? strtoupper( trim( (string) $body['confirmation'] ) ) : '';
        if ( 'MIGRATE' !== $confirmation ) {
            return new WP_Error(
                'sc_rl_v1207_confirmation_required',
                'Type MIGRATE to explicitly apply a prepared migration run.',
                array( 'status' => 400 )
            );
        }

        $candidate_ids = array();
        if ( isset( $body['candidate_ids'] ) && is_array( $body['candidate_ids'] ) ) {
            foreach ( array_slice( $body['candidate_ids'], 0, self::MAX_CANDIDATES ) as $candidate_id ) {
                $candidate_id = sanitize_text_field( (string) $candidate_id );
                if ( preg_match( '/^wpc-[a-f0-9]{32}$/', $candidate_id ) ) {
                    $candidate_ids[] = $candidate_id;
                }
            }
        }

        $payload = array(
            'confirm'       => true,
            'candidate_ids' => array_values( array_unique( $candidate_ids ) ),
            'note'          => isset( $body['note'] ) ? sanitize_textarea_field( (string) $body['note'] ) : '',
        );

        $upstream = self::backend_request(
            '/v1/research-librarian/wordpress-migration/runs/' . rawurlencode( $run_id ) . '/apply',
            'POST',
            $payload
        );
        if ( is_wp_error( $upstream ) ) {
            return $upstream;
        }
        return rest_ensure_response( $upstream );
    }

    public static function resolve_endpoint( WP_REST_Request $request ) {
        $body = $request->get_json_params();
        $body = is_array( $body ) ? $body : array();

        $source_type = isset( $body['source_type'] ) ? sanitize_key( (string) $body['source_type'] ) : '';
        $legacy_id = isset( $body['legacy_id'] ) ? sanitize_text_field( (string) $body['legacy_id'] ) : '';

        if ( ! in_array( $source_type, self::supported_types(), true ) || '' === $legacy_id ) {
            return new WP_Error(
                'sc_rl_v1207_invalid_legacy_reference',
                'A supported source_type and legacy_id are required.',
                array( 'status' => 400 )
            );
        }

        $upstream = self::backend_request(
            '/v1/research-librarian/wordpress-migration/resolve',
            'POST',
            array(
                'source_site' => home_url( '/' ),
                'source_type' => $source_type,
                'legacy_id'   => $legacy_id,
            )
        );
        if ( is_wp_error( $upstream ) ) {
            return $upstream;
        }
        return rest_ensure_response( $upstream );
    }

    public static function resolve_legacy_reference( $source_type, $legacy_id ) {
        $source_type = sanitize_key( (string) $source_type );
        $legacy_id = sanitize_text_field( (string) $legacy_id );
        if ( ! in_array( $source_type, self::supported_types(), true ) || '' === $legacy_id ) {
            return new WP_Error( 'sc_rl_v1207_invalid_legacy_reference', 'Invalid legacy reference.' );
        }
        return self::backend_request(
            '/v1/research-librarian/wordpress-migration/resolve',
            'POST',
            array(
                'source_site' => home_url( '/' ),
                'source_type' => $source_type,
                'legacy_id'   => $legacy_id,
            )
        );
    }

    public static function inventory() {
        global $wpdb;

        $candidates = array();
        $summary = array(
            'option_rows_scanned'    => 0,
            'user_meta_rows_scanned' => 0,
            'candidate_count'        => 0,
            'secret_fields_removed'  => 0,
            'truncated_values'       => 0,
        );

        $like_rl = $wpdb->esc_like( 'sc_rl_' ) . '%';
        $like_long = $wpdb->esc_like( 'sc_research_librarian_' ) . '%';

        $option_sql = $wpdb->prepare(
            "SELECT option_name, option_value
             FROM {$wpdb->options}
             WHERE option_name LIKE %s OR option_name LIKE %s
             ORDER BY option_name ASC
             LIMIT 2000",
            $like_rl,
            $like_long
        );
        $option_rows = $wpdb->get_results( $option_sql, ARRAY_A );
        if ( ! is_array( $option_rows ) ) {
            $option_rows = array();
        }

        foreach ( $option_rows as $row ) {
            if ( count( $candidates ) >= self::MAX_CANDIDATES ) {
                break;
            }
            $summary['option_rows_scanned']++;
            $name = sanitize_key( isset( $row['option_name'] ) ? $row['option_name'] : '' );
            if ( self::is_secret_name( $name ) ) {
                $summary['secret_fields_removed']++;
                continue;
            }
            $value = maybe_unserialize( isset( $row['option_value'] ) ? $row['option_value'] : '' );
            $value = self::sanitize_legacy_value( $value, $summary );
            self::extract_candidates(
                $value,
                'wp-option:' . $name,
                '',
                'option:' . $name,
                '',
                $candidates,
                $summary,
                0
            );
        }

        $meta_sql = $wpdb->prepare(
            "SELECT umeta_id, user_id, meta_key, meta_value
             FROM {$wpdb->usermeta}
             WHERE meta_key LIKE %s OR meta_key LIKE %s
             ORDER BY umeta_id ASC
             LIMIT 5000",
            $like_rl,
            $like_long
        );
        $meta_rows = $wpdb->get_results( $meta_sql, ARRAY_A );
        if ( ! is_array( $meta_rows ) ) {
            $meta_rows = array();
        }

        foreach ( $meta_rows as $row ) {
            if ( count( $candidates ) >= self::MAX_CANDIDATES ) {
                break;
            }
            $summary['user_meta_rows_scanned']++;
            $key = sanitize_key( isset( $row['meta_key'] ) ? $row['meta_key'] : '' );
            if ( self::is_secret_name( $key ) ) {
                $summary['secret_fields_removed']++;
                continue;
            }
            $user_id = absint( isset( $row['user_id'] ) ? $row['user_id'] : 0 );
            $owner_key = 'wp-user:' . $user_id;
            $value = maybe_unserialize( isset( $row['meta_value'] ) ? $row['meta_value'] : '' );
            $value = self::sanitize_legacy_value( $value, $summary );
            self::extract_candidates(
                $value,
                'wp-usermeta:' . $user_id . ':' . $key,
                $owner_key,
                'usermeta:' . absint( $row['umeta_id'] ),
                '',
                $candidates,
                $summary,
                0
            );
        }

        /**
         * Extensions may provide additional already-sanitized legacy state.
         * The final normalizer below still enforces the fixed candidate schema,
         * supported type allowlist, size cap, and secret-key rejection.
         */
        $extensions = apply_filters( 'sc_rl_v1207_legacy_state_candidates', array() );
        if ( is_array( $extensions ) ) {
            foreach ( $extensions as $candidate ) {
                if ( count( $candidates ) >= self::MAX_CANDIDATES ) {
                    break;
                }
                $normalized = self::normalize_candidate( $candidate, $summary );
                if ( is_array( $normalized ) ) {
                    $candidates[] = $normalized;
                }
            }
        }

        $summary['candidate_count'] = count( $candidates );

        return array(
            'schema'          => self::CONTRACT,
            'version'         => self::VERSION,
            'source_site'     => home_url( '/' ),
            'source_instance' => self::source_instance(),
            'summary'         => $summary,
            'candidates'      => array_values( $candidates ),
            'governance'      => array(
                'read_only_inventory'        => true,
                'legacy_state_deleted'       => false,
                'secret_fields_exported'     => false,
                'automatic_migration'        => false,
                'wordpress_canonical_state'  => false,
            ),
        );
    }

    private static function extract_candidates(
        $value,
        $locator,
        $owner_key,
        $fallback_legacy_id,
        $parent_legacy_id,
        &$out,
        &$summary,
        $depth
    ) {
        if ( count( $out ) >= self::MAX_CANDIDATES || $depth > 6 ) {
            return;
        }

        if ( is_array( $value ) && self::is_list_array( $value ) ) {
            foreach ( array_slice( $value, 0, 500 ) as $index => $item ) {
                self::extract_candidates(
                    $item,
                    $locator . ':' . absint( $index ),
                    $owner_key,
                    $fallback_legacy_id . ':' . absint( $index ),
                    $parent_legacy_id,
                    $out,
                    $summary,
                    $depth + 1
                );
            }
            return;
        }

        if ( ! is_array( $value ) ) {
            $candidate = self::normalize_candidate(
                array(
                    'source_type'     => 'compatibility-record',
                    'legacy_id'       => $fallback_legacy_id,
                    'owner_key'       => $owner_key,
                    'parent_legacy_id'=> $parent_legacy_id,
                    'source_locator'  => $locator,
                    'payload'         => array( 'value' => $value ),
                ),
                $summary
            );
            if ( is_array( $candidate ) ) {
                $out[] = $candidate;
            }
            return;
        }

        $type = self::detect_type( $value );
        $legacy_id = self::detect_legacy_id( $type, $value, $fallback_legacy_id );
        $parent = $parent_legacy_id;
        if ( 'persistent-turn' === $type && ! empty( $value['session_id'] ) ) {
            $parent = sanitize_text_field( (string) $value['session_id'] );
        }

        $candidate = self::normalize_candidate(
            array(
                'source_type'      => $type,
                'legacy_id'        => $legacy_id,
                'owner_key'        => $owner_key,
                'parent_legacy_id' => $parent,
                'source_locator'   => $locator,
                'payload'          => $value,
            ),
            $summary
        );
        if ( is_array( $candidate ) ) {
            $out[] = $candidate;
        }

        // Preserve nested session turns as individually receipted candidates.
        if ( 'persistent-session' === $type && isset( $value['turns'] ) && is_array( $value['turns'] ) ) {
            foreach ( array_slice( $value['turns'], 0, 2000 ) as $index => $turn ) {
                if ( count( $out ) >= self::MAX_CANDIDATES ) {
                    break;
                }
                self::extract_candidates(
                    $turn,
                    $locator . ':turn:' . absint( $index ),
                    $owner_key,
                    $legacy_id . ':turn:' . absint( $index ),
                    $legacy_id,
                    $out,
                    $summary,
                    $depth + 1
                );
            }
        }
    }

    private static function detect_type( $value ) {
        if ( ! is_array( $value ) ) {
            return 'compatibility-record';
        }
        if ( isset( $value['turn_id'] ) || ( isset( $value['session_id'] ) && isset( $value['content'] ) && isset( $value['role'] ) ) ) {
            return 'persistent-turn';
        }
        if ( isset( $value['session_id'] ) ) {
            return 'persistent-session';
        }
        if ( isset( $value['context_id'] ) ) {
            return 'research-context';
        }
        if ( isset( $value['room_id'] ) ) {
            return 'research-room';
        }
        if ( isset( $value['object_id'] ) && isset( $value['object_type'] ) ) {
            return 'library-object';
        }
        if ( isset( $value['project_id'] ) && ( isset( $value['objective'] ) || isset( $value['visibility'] ) || isset( $value['title'] ) ) ) {
            return 'project';
        }
        return 'compatibility-record';
    }

    private static function detect_legacy_id( $type, $value, $fallback ) {
        $map = array(
            'project'            => 'project_id',
            'research-context'   => 'context_id',
            'research-room'      => 'room_id',
            'library-object'     => 'object_id',
            'persistent-session' => 'session_id',
            'persistent-turn'    => 'turn_id',
        );
        if ( isset( $map[ $type ] ) && ! empty( $value[ $map[ $type ] ] ) ) {
            return substr( sanitize_text_field( (string) $value[ $map[ $type ] ] ), 0, 500 );
        }
        return substr( sanitize_text_field( (string) $fallback ), 0, 500 );
    }

    private static function normalize_candidate( $candidate, &$summary ) {
        if ( ! is_array( $candidate ) ) {
            return null;
        }
        $type = isset( $candidate['source_type'] ) ? sanitize_key( (string) $candidate['source_type'] ) : 'compatibility-record';
        if ( ! in_array( $type, self::supported_types(), true ) ) {
            $type = 'compatibility-record';
        }
        $legacy_id = isset( $candidate['legacy_id'] ) ? sanitize_text_field( (string) $candidate['legacy_id'] ) : '';
        if ( '' === $legacy_id ) {
            return null;
        }
        $payload = isset( $candidate['payload'] ) && is_array( $candidate['payload'] )
            ? self::sanitize_legacy_value( $candidate['payload'], $summary )
            : array( 'value' => self::sanitize_legacy_value( isset( $candidate['payload'] ) ? $candidate['payload'] : '', $summary ) );

        if ( self::contains_secret_key( $payload ) ) {
            $summary['secret_fields_removed']++;
            return null;
        }

        $encoded = wp_json_encode( $payload );
        if ( false === $encoded ) {
            return null;
        }
        if ( strlen( $encoded ) > self::MAX_VALUE_BYTES ) {
            $summary['truncated_values']++;
            $payload = array(
                'migration_notice' => 'Legacy payload exceeded v12.0.7 inventory size limit and was not exported.',
                'original_bytes'   => strlen( $encoded ),
            );
            $type = 'compatibility-record';
        }

        return array(
            'source_type'      => $type,
            'legacy_id'        => substr( $legacy_id, 0, 500 ),
            'owner_key'        => substr( sanitize_text_field( isset( $candidate['owner_key'] ) ? (string) $candidate['owner_key'] : '' ), 0, 500 ),
            'parent_legacy_id' => substr( sanitize_text_field( isset( $candidate['parent_legacy_id'] ) ? (string) $candidate['parent_legacy_id'] : '' ), 0, 500 ),
            'source_locator'   => substr( sanitize_text_field( isset( $candidate['source_locator'] ) ? (string) $candidate['source_locator'] : '' ), 0, 2000 ),
            'payload'          => $payload,
        );
    }

    private static function sanitize_legacy_value( $value, &$summary, $depth = 0 ) {
        if ( $depth > 8 ) {
            return '[depth-limit]';
        }
        if ( is_array( $value ) ) {
            $out = array();
            $count = 0;
            foreach ( $value as $key => $item ) {
                if ( $count >= 500 ) {
                    $summary['truncated_values']++;
                    break;
                }
                $key_text = is_string( $key ) ? sanitize_key( $key ) : $key;
                if ( is_string( $key_text ) && self::is_secret_name( $key_text ) ) {
                    $summary['secret_fields_removed']++;
                    continue;
                }
                $out[ $key_text ] = self::sanitize_legacy_value( $item, $summary, $depth + 1 );
                $count++;
            }
            return $out;
        }
        if ( is_object( $value ) ) {
            return self::sanitize_legacy_value( get_object_vars( $value ), $summary, $depth + 1 );
        }
        if ( is_bool( $value ) || is_int( $value ) || is_float( $value ) || null === $value ) {
            return $value;
        }
        $text = (string) $value;
        if ( strlen( $text ) > 20000 ) {
            $summary['truncated_values']++;
            $text = substr( $text, 0, 20000 );
        }
        return sanitize_textarea_field( $text );
    }

    private static function contains_secret_key( $value ) {
        if ( ! is_array( $value ) ) {
            return false;
        }
        foreach ( $value as $key => $item ) {
            if ( is_string( $key ) && self::is_secret_name( $key ) ) {
                return true;
            }
            if ( is_array( $item ) && self::contains_secret_key( $item ) ) {
                return true;
            }
        }
        return false;
    }

    private static function is_secret_name( $name ) {
        return (bool) preg_match(
            '/(?:^|[_-])(password|passwd|secret|token|api[_-]?key|private[_-]?key|nonce)(?:$|[_-])/i',
            (string) $name
        );
    }

    private static function is_list_array( $value ) {
        if ( ! is_array( $value ) ) {
            return false;
        }
        $index = 0;
        foreach ( array_keys( $value ) as $key ) {
            if ( $key !== $index ) {
                return false;
            }
            $index++;
        }
        return true;
    }

    private static function supported_types() {
        return array(
            'project',
            'research-context',
            'research-room',
            'library-object',
            'persistent-session',
            'persistent-turn',
            'compatibility-record',
        );
    }

    private static function source_instance() {
        return 'wordpress:' . get_current_blog_id() . ':' . substr( hash( 'sha256', home_url( '/' ) ), 0, 16 );
    }

    private static function connection_config() {
        if ( class_exists( 'SC_RL6_V621_Endpoint_Reliability' ) && method_exists( 'SC_RL6_V621_Endpoint_Reliability', 'options' ) ) {
            $options = SC_RL6_V621_Endpoint_Reliability::options();
        } else {
            $options = get_option( 'sc_rl_v620_python_options', array() );
        }
        $options = is_array( $options ) ? $options : array();

        return array(
            'backend_url'     => isset( $options['backend_url'] ) ? esc_url_raw( trim( (string) $options['backend_url'] ) ) : '',
            'backend_api_key' => isset( $options['backend_api_key'] ) ? trim( (string) $options['backend_api_key'] ) : '',
            'request_timeout' => min( 120, max( 10, absint( isset( $options['request_timeout'] ) ? $options['request_timeout'] : 45 ) ) ),
        );
    }

    private static function backend_request( $path, $method = 'GET', $payload = null ) {
        $config = self::connection_config();
        $base = untrailingslashit( $config['backend_url'] );

        if ( '' === $base || '' === $config['backend_api_key'] ) {
            return new WP_Error(
                'sc_rl_v1207_backend_not_configured',
                'Research Librarian backend URL or integration key is not configured.',
                array( 'status' => 503 )
            );
        }

        if ( ! preg_match( '#^/v1/research-librarian/wordpress-migration(?:/|$)#', $path ) ) {
            return new WP_Error(
                'sc_rl_v1207_path_forbidden',
                'Migration request path is outside the fixed v12.0.7 backend boundary.',
                array( 'status' => 500 )
            );
        }

        $args = array(
            'method'      => strtoupper( $method ),
            'timeout'     => $config['request_timeout'],
            'redirection' => 0,
            'headers'     => array(
                'Accept'        => 'application/json',
                'Content-Type'  => 'application/json',
                'X-SC-RL-Key'   => $config['backend_api_key'],
                'User-Agent'    => 'Sustainable-Catalyst-RL-WP-Migration/' . self::VERSION,
            ),
        );

        if ( null !== $payload ) {
            $encoded = wp_json_encode( $payload );
            if ( false === $encoded || strlen( $encoded ) > 2097152 ) {
                return new WP_Error(
                    'sc_rl_v1207_payload_invalid',
                    'Migration request is invalid or exceeds the 2 MiB request limit.',
                    array( 'status' => 413 )
                );
            }
            $args['body'] = $encoded;
        }

        $response = wp_remote_request( $base . $path, $args );
        if ( is_wp_error( $response ) ) {
            return new WP_Error(
                'sc_rl_v1207_backend_unreachable',
                'Research Librarian backend is unavailable: ' . sanitize_text_field( $response->get_error_message() ),
                array( 'status' => 502 )
            );
        }

        $code = absint( wp_remote_retrieve_response_code( $response ) );
        $raw = wp_remote_retrieve_body( $response );
        $decoded = json_decode( $raw, true );

        if ( $code < 200 || $code >= 300 ) {
            $detail = is_array( $decoded ) && isset( $decoded['detail'] )
                ? ( is_string( $decoded['detail'] ) ? $decoded['detail'] : wp_json_encode( $decoded['detail'] ) )
                : '';
            return new WP_Error(
                'sc_rl_v1207_backend_rejected',
                'Research Librarian backend rejected the migration request' . ( $detail ? ': ' . sanitize_text_field( $detail ) : '.' ),
                array( 'status' => $code ? $code : 502 )
            );
        }

        if ( ! is_array( $decoded ) ) {
            return new WP_Error(
                'sc_rl_v1207_invalid_backend_json',
                'Research Librarian backend returned invalid JSON.',
                array( 'status' => 502 )
            );
        }

        return $decoded;
    }
}
