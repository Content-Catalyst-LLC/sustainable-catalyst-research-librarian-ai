<?php
/** Functional defaults and contract checks for v7.0.0. */
define('ABSPATH',__DIR__.'/');
$GLOBALS['opts']=array();
function add_action(){} function add_shortcode(){} function get_option($k,$d=array()){return $GLOBALS['opts'][$k]??$d;} function update_option($k,$v){$GLOBALS['opts'][$k]=$v;return true;} function wp_parse_args($a,$d){return array_merge($d,is_array($a)?$a:array());} function current_user_can(){return true;} function is_user_logged_in(){return true;}
require dirname(__DIR__).'/includes/class-sc-rl-v700-connected-platform.php';
SC_RL6_V700_Connected_Platform::activate();
$o=SC_RL6_V700_Connected_Platform::options();
$result=array('version'=>SC_RL6_V700_Connected_Platform::VERSION,'mode'=>$o['workspace_mode'],'visibility'=>$o['default_visibility'],'projects'=>$o['persistent_projects'],'backup'=>$o['portable_backups'],'human_review'=>$o['human_publication_review']);
$passed='7.0.0'===$result['version']&&'public'===$result['mode']&&'private'===$result['visibility']&&'1'===$result['projects']&&'1'===$result['backup']&&'1'===$result['human_review'];
echo json_encode(array('passed'=>$passed,'result'=>$result),JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES).PHP_EOL;
exit($passed?0:1);
