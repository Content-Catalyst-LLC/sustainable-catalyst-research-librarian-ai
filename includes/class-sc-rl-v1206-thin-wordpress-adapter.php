<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Research Librarian v12.0.6 — Thin WordPress Adapter.
 *
 * WordPress is presentation/proxy compatibility only. This adapter:
 * - stores no canonical research/project/session/evidence/conversation state;
 * - never accepts arbitrary upstream URLs, paths, or HTTP methods;
 * - keeps the Research Librarian integration key server-side;
 * - requires WordPress cookie + REST nonce authentication for proxy operations;
 * - capability-gates write operations;
 * - forwards a bounded WordPress actor context as provenance metadata only;
 * - fails closed when the Python backend is unavailable.
 */
final class SC_RL_V1206_Thin_WordPress_Adapter {
    const VERSION = '12.0.6';
    const CONTRACT = 'sc-research-librarian-wordpress-thin-adapter/2.0';
    const ACTOR_CONTRACT = 'sc-research-librarian-wordpress-actor-context/1.0';
    const REST_NAMESPACE = 'sc-research-librarian-ai/v1';

    public static function init() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ), 125 );
    }

    public static function register_routes() {
        register_rest_route(
            self::REST_NAMESPACE,
            '/thin-adapter',
            array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array( __CLASS__, 'manifest' ),
                'permission_callback' => '__return_true',
            )
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/thin-adapter/status',
            array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array( __CLASS__, 'status' ),
                'permission_callback' => array( __CLASS__, 'can_proxy' ),
            )
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/thin-adapter/proxy',
            array(
                'methods'             => WP_REST_Server::CREATABLE,
                'callback'            => array( __CLASS__, 'proxy' ),
                'permission_callback' => array( __CLASS__, 'can_proxy' ),
            )
        );
    }

    public static function manifest() {
        $config = self::connection_config();
        return rest_ensure_response(
            array(
                'schema'                       => self::CONTRACT,
                'actor_context_schema'         => self::ACTOR_CONTRACT,
                'version'                      => self::VERSION,
                'adapter_type'                 => 'optional-wordpress-presentation-proxy',
                'backend_authoritative'        => true,
                'wordpress_required'           => false,
                'wordpress_runtime_authority'  => false,
                'wordpress_identity_authority' => false,
                'wordpress_session_authority'  => false,
                'wordpress_canonical_state'    => false,
                'backend_configured'           => ! empty( $config['backend_url'] ) && ! empty( $config['backend_api_key'] ),
                'backend_key_exposed'          => false,
                'arbitrary_proxy_paths'        => false,
                'arbitrary_proxy_hosts'        => false,
                'fixed_operation_allowlist'    => true,
                'backend_failure_behavior'     => 'fail-closed-no-wordpress-research-fallback',
                'read_operations'              => array_keys( self::read_operations() ),
                'write_operations'             => array_keys( self::write_operations() ),
                'next_boundary'                => 'neural-research-intelligence-foundation',
            )
        );
    }

    public static function can_proxy( WP_REST_Request $request ) {
        if ( ! is_user_logged_in() || ! current_user_can( 'read' ) ) {
            return new WP_Error(
                'sc_rl_v1206_auth_required',
                'Authenticated WordPress access is required.',
                array( 'status' => 401 )
            );
        }

        $nonce = (string) $request->get_header( 'x_wp_nonce' );
        if ( '' === $nonce || ! wp_verify_nonce( $nonce, 'wp_rest' ) ) {
            return new WP_Error(
                'sc_rl_v1206_bad_nonce',
                'WordPress REST nonce validation failed.',
                array( 'status' => 403 )
            );
        }
        return true;
    }

    public static function status() {
        $config = self::connection_config();
        $configured = ! empty( $config['backend_url'] ) && ! empty( $config['backend_api_key'] );

        if ( ! $configured ) {
            return new WP_REST_Response(
                array(
                    'version'            => self::VERSION,
                    'state'              => 'not-configured',
                    'backend_configured' => false,
                    'backend_reachable'  => false,
                    'wordpress_fallback' => false,
                ),
                200
            );
        }

        $response = self::backend_request( '/health', 'GET', null, false );
        if ( is_wp_error( $response ) ) {
            return new WP_REST_Response(
                array(
                    'version'            => self::VERSION,
                    'state'              => 'backend-unavailable',
                    'backend_configured' => true,
                    'backend_reachable'  => false,
                    'wordpress_fallback' => false,
                    'error'              => sanitize_text_field( $response->get_error_message() ),
                ),
                200
            );
        }

        return new WP_REST_Response(
            array(
                'version'                 => self::VERSION,
                'state'                   => 'online',
                'backend_configured'      => true,
                'backend_reachable'       => true,
                'backend_version'         => sanitize_text_field( isset( $response['version'] ) ? $response['version'] : '' ),
                'runtime_authority'       => sanitize_key( isset( $response['runtime_authority'] ) ? $response['runtime_authority'] : '' ),
                'thin_wordpress_adapter'  => ! empty( $response['thin_wordpress_adapter'] ),
                'wordpress_required'      => ! empty( $response['wordpress_required'] ),
                'wordpress_fallback'      => false,
            ),
            200
        );
    }

    public static function proxy( WP_REST_Request $request ) {
        $body = $request->get_json_params();
        $body = is_array( $body ) ? $body : array();

        $operation = isset( $body['operation'] ) ? sanitize_key( $body['operation'] ) : '';
        $payload   = isset( $body['payload'] ) && is_array( $body['payload'] ) ? $body['payload'] : array();

        $read_ops  = self::read_operations();
        $write_ops = self::write_operations();

        if ( isset( $read_ops[ $operation ] ) ) {
            $spec = $read_ops[ $operation ];
        } elseif ( isset( $write_ops[ $operation ] ) ) {
            if ( ! current_user_can( 'edit_posts' ) ) {
                return new WP_Error(
                    'sc_rl_v1206_write_forbidden',
                    'This WordPress user does not have Research Librarian write access through the compatibility adapter.',
                    array( 'status' => 403 )
                );
            }
            $spec = $write_ops[ $operation ];
        } else {
            return new WP_Error(
                'sc_rl_v1206_operation_forbidden',
                'The requested adapter operation is not allowed.',
                array( 'status' => 400 )
            );
        }

        $resolved = self::resolve_operation( $operation, $spec, $payload );
        if ( is_wp_error( $resolved ) ) {
            return $resolved;
        }

        $actor = self::actor_context();
        $upstream = self::backend_request(
            $resolved['path'],
            $resolved['method'],
            $resolved['payload'],
            true,
            $actor
        );

        if ( is_wp_error( $upstream ) ) {
            // Fail closed. v12.0.6 deliberately provides no canonical/local
            // WordPress research fallback when the Python backend is unavailable.
            return $upstream;
        }

        return new WP_REST_Response(
            array(
                'ok'        => true,
                'version'   => self::VERSION,
                'operation' => $operation,
                'actor'     => $actor,
                'upstream'  => $upstream,
            ),
            200
        );
    }

    private static function read_operations() {
        return array(
            'status' => array( 'method' => 'GET', 'path' => '/v1/research-librarian/status' ),
            'capabilities' => array( 'method' => 'GET', 'path' => '/v1/research-librarian/capabilities' ),
            'retrieve' => array( 'method' => 'POST', 'path' => '/v1/research-librarian/retrieve' ),
            'projects' => array( 'method' => 'GET', 'path' => '/v1/research-librarian/projects' ),
            'project' => array( 'method' => 'GET', 'path' => '/v1/research-librarian/projects/{project_id}' ),
            'project-investigations' => array( 'method' => 'GET', 'path' => '/v1/research-librarian/projects/{project_id}/investigations' ),
            'sessions' => array( 'method' => 'GET', 'path' => '/v1/research-librarian/sessions' ),
            'session' => array( 'method' => 'GET', 'path' => '/v1/research-librarian/sessions/{session_id}' ),
            'session-turns' => array( 'method' => 'GET', 'path' => '/v1/research-librarian/sessions/{session_id}/turns' ),
            'session-summary' => array( 'method' => 'GET', 'path' => '/v1/research-librarian/sessions/{session_id}/summary' ),
        );
    }

    private static function write_operations() {
        return array(
            'project-create' => array( 'method' => 'POST', 'path' => '/v1/research-librarian/projects' ),
            'session-create' => array( 'method' => 'POST', 'path' => '/v1/research-librarian/sessions' ),
            'session-turn-add' => array( 'method' => 'POST', 'path' => '/v1/research-librarian/sessions/{session_id}/turns' ),
            'session-snapshot-freeze' => array( 'method' => 'POST', 'path' => '/v1/research-librarian/sessions/{session_id}/snapshots/freeze' ),
        );
    }

    private static function resolve_operation( $operation, $spec, $payload ) {
        $path = (string) $spec['path'];
        $method = (string) $spec['method'];

        foreach ( array( 'project_id', 'session_id' ) as $identifier ) {
            $token = '{' . $identifier . '}';
            if ( false === strpos( $path, $token ) ) {
                continue;
            }

            $value = isset( $payload[ $identifier ] ) ? sanitize_text_field( (string) $payload[ $identifier ] ) : '';
            if ( '' === $value || ! preg_match( '/^[A-Za-z0-9._:-]{1,255}$/', $value ) ) {
                return new WP_Error(
                    'sc_rl_v1206_missing_identifier',
                    'A valid ' . $identifier . ' is required for this operation.',
                    array( 'status' => 400 )
                );
            }

            $path = str_replace( $token, rawurlencode( $value ), $path );
            unset( $payload[ $identifier ] );
        }

        if ( 'GET' === $method ) {
            $query = self::sanitize_query_payload( $operation, $payload );
            if ( is_wp_error( $query ) ) {
                return $query;
            }
            if ( ! empty( $query ) ) {
                $path = add_query_arg( $query, $path );
            }
            $payload = null;
        } else {
            $payload = self::sanitize_body_payload( $operation, $payload );
        }

        return array(
            'method'  => $method,
            'path'    => $path,
            'payload' => $payload,
        );
    }

    private static function sanitize_query_payload( $operation, $payload ) {
        $allowed = array();
        if ( 'projects' === $operation ) {
            $allowed = array( 'limit', 'owner_ref' );
        } elseif ( 'project-investigations' === $operation ) {
            $allowed = array( 'limit' );
        } elseif ( 'sessions' === $operation ) {
            $allowed = array( 'limit', 'client_ref', 'project_id', 'state' );
        } elseif ( 'session-turns' === $operation ) {
            $allowed = array( 'limit', 'after_sequence' );
        }

        $query = array();
        foreach ( $allowed as $key ) {
            if ( ! array_key_exists( $key, $payload ) ) {
                continue;
            }
            if ( in_array( $key, array( 'limit', 'after_sequence' ), true ) ) {
                $query[ $key ] = absint( $payload[ $key ] );
            } else {
                $query[ $key ] = sanitize_text_field( (string) $payload[ $key ] );
            }
        }
        return $query;
    }

    private static function sanitize_body_payload( $operation, $payload ) {
        if ( 'retrieve' === $operation ) {
            return array(
                'query'               => sanitize_textarea_field( isset( $payload['query'] ) ? $payload['query'] : '' ),
                'limit'               => min( 50, max( 1, absint( isset( $payload['limit'] ) ? $payload['limit'] : 10 ) ) ),
                'include_semantic'    => ! empty( $payload['include_semantic'] ),
                'include_diagnostics' => ! empty( $payload['include_diagnostics'] ),
                'advanced'            => ! empty( $payload['advanced'] ),
                'filters'             => isset( $payload['filters'] ) && is_array( $payload['filters'] ) ? self::bounded_array( $payload['filters'], 100 ) : array(),
            );
        }

        $clean = self::bounded_array( $payload, 200 );
        if ( isset( $clean['metadata'] ) && ! is_array( $clean['metadata'] ) ) {
            unset( $clean['metadata'] );
        }
        return $clean;
    }

    private static function bounded_array( $value, $max_items ) {
        if ( ! is_array( $value ) ) {
            return array();
        }
        $out = array();
        $count = 0;
        foreach ( $value as $key => $item ) {
            if ( $count >= $max_items ) {
                break;
            }
            $safe_key = is_string( $key ) ? sanitize_key( $key ) : $key;
            if ( is_array( $item ) ) {
                $out[ $safe_key ] = self::bounded_array( $item, 50 );
            } elseif ( is_bool( $item ) || is_int( $item ) || is_float( $item ) ) {
                $out[ $safe_key ] = $item;
            } elseif ( null === $item ) {
                $out[ $safe_key ] = null;
            } else {
                $out[ $safe_key ] = sanitize_textarea_field( (string) $item );
            }
            $count++;
        }
        return $out;
    }

    private static function actor_context() {
        $user = wp_get_current_user();
        $roles = array();
        foreach ( (array) $user->roles as $role ) {
            $roles[] = sanitize_key( $role );
        }

        return array(
            'schema'       => self::ACTOR_CONTRACT,
            'source'       => 'wordpress',
            'site_url'     => esc_url_raw( home_url( '/' ) ),
            'wp_user_id'   => absint( $user->ID ),
            'display_name' => sanitize_text_field( $user->display_name ),
            'roles'        => array_values( array_unique( $roles ) ),
            'authority'    => 'provenance-hint-not-backend-identity',
        );
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

    private static function backend_request( $path, $method = 'GET', $payload = null, $authenticate = true, $actor = array() ) {
        $config = self::connection_config();
        $base = untrailingslashit( $config['backend_url'] );

        if ( '' === $base ) {
            return new WP_Error(
                'sc_rl_v1206_backend_not_configured',
                'Research Librarian backend URL is not configured.',
                array( 'status' => 503 )
            );
        }
        if ( $authenticate && '' === $config['backend_api_key'] ) {
            return new WP_Error(
                'sc_rl_v1206_backend_key_not_configured',
                'Research Librarian server integration key is not configured.',
                array( 'status' => 503 )
            );
        }

        $parsed = wp_parse_url( $base );
        if ( ! is_array( $parsed ) || empty( $parsed['scheme'] ) || empty( $parsed['host'] ) || ! in_array( strtolower( $parsed['scheme'] ), array( 'http', 'https' ), true ) ) {
            return new WP_Error(
                'sc_rl_v1206_invalid_backend_url',
                'Configured Research Librarian backend URL is invalid.',
                array( 'status' => 500 )
            );
        }

        if ( ! preg_match( '#^/(health|v1/research-librarian(?:/|$))#', $path ) ) {
            return new WP_Error(
                'sc_rl_v1206_upstream_path_forbidden',
                'Upstream path is outside the v12.0.6 adapter allowlist.',
                array( 'status' => 500 )
            );
        }

        $headers = array(
            'Accept'       => 'application/json',
            'Content-Type' => 'application/json',
            'User-Agent'   => 'Sustainable-Catalyst-Research-Librarian-WordPress-Adapter/' . self::VERSION . '; ' . home_url( '/' ),
        );
        if ( $authenticate ) {
            $headers['X-SC-RL-Key'] = $config['backend_api_key'];
        }
        if ( ! empty( $actor ) ) {
            $headers['X-SC-RL-WP-Actor'] = base64_encode( wp_json_encode( $actor ) );
        }

        $args = array(
            'method'      => strtoupper( $method ),
            'timeout'     => $config['request_timeout'],
            'redirection' => 0,
            'headers'     => $headers,
        );

        if ( null !== $payload ) {
            $encoded = wp_json_encode( $payload );
            if ( false === $encoded || strlen( $encoded ) > 131072 ) {
                return new WP_Error(
                    'sc_rl_v1206_payload_too_large',
                    'Adapter payload is invalid or exceeds the 128 KiB limit.',
                    array( 'status' => 413 )
                );
            }
            $args['body'] = $encoded;
        }

        $response = wp_remote_request( $base . $path, $args );
        if ( is_wp_error( $response ) ) {
            return new WP_Error(
                'sc_rl_v1206_backend_unreachable',
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
                'sc_rl_v1206_backend_rejected',
                'Research Librarian backend rejected the adapter request' . ( $detail ? ': ' . sanitize_text_field( $detail ) : '.' ),
                array( 'status' => $code ? $code : 502, 'upstream_status' => $code )
            );
        }

        if ( ! is_array( $decoded ) ) {
            return new WP_Error(
                'sc_rl_v1206_backend_invalid_json',
                'Research Librarian backend returned invalid JSON.',
                array( 'status' => 502 )
            );
        }

        return $decoded;
    }
}
