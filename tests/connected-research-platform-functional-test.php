<?php
/** Functional defaults and contract checks for v7.1.2. */
define('ABSPATH',__DIR__.'/');
$GLOBALS['opts']=array();
function add_action(){} function add_shortcode(){} function get_option($k,$d=array()){return $GLOBALS['opts'][$k]??$d;} function update_option($k,$v){$GLOBALS['opts'][$k]=$v;return true;} function wp_parse_args($a,$d){return array_merge($d,is_array($a)?$a:array());} function current_user_can(){return true;} function is_user_logged_in(){return true;}
require dirname(__DIR__).'/includes/class-sc-rl-v700-connected-platform.php';
SC_RL6_V700_Connected_Platform::activate();
$o=SC_RL6_V700_Connected_Platform::options();
$result=array('version'=>SC_RL6_V700_Connected_Platform::VERSION,'mode'=>$o['workspace_mode'],'visibility'=>$o['default_visibility'],'projects'=>$o['persistent_projects'],'backup'=>$o['portable_backups'],'human_review'=>$o['human_publication_review'],'library_object_model'=>$o['library_object_model'],'contextual_research'=>$o['contextual_research'],'personal_library_separation'=>$o['personal_library_separation'],'source_scope_provenance'=>$o['source_scope_provenance']);
$passed='7.4.0'===$result['version']&&'public'===$result['mode']&&'private'===$result['visibility']&&'1'===$result['projects']&&'1'===$result['backup']&&'1'===$result['human_review']&&'1'===$result['library_object_model']&&'1'===$result['contextual_research']&&'1'===$result['personal_library_separation']&&'1'===$result['source_scope_provenance'];
echo json_encode(array('passed'=>$passed,'result'=>$result),JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES).PHP_EOL;
exit($passed?0:1);
