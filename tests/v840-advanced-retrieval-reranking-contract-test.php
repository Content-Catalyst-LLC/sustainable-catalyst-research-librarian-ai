<?php
$root = dirname(__DIR__);
$main = file_get_contents($root . '/sustainable-catalyst-research-librarian-ai.php');
$backend = file_get_contents($root . '/backend/app/main.py');
$advanced = file_get_contents($root . '/backend/app/advanced_retrieval.py');
$calibration = file_get_contents($root . '/backend/app/calibration.py');
$models = file_get_contents($root . '/backend/app/models.py');
$manifest = json_decode(file_get_contents($root . '/data/research_librarian_advanced_retrieval_manifest_v8.4.0.json'), true);
$checks = array(
  'version_header' => false !== strpos($main, 'Version: 9.6.0'),
  'version_constant' => false !== strpos($main, "const VERSION        = '9.6.0';"),
  'backend_version' => false !== strpos(file_get_contents($root . '/backend/app/__init__.py'), '__version__ = "9.6.0"'),
  'advanced_module' => false !== strpos($advanced, 'ADVANCED_RETRIEVAL_SCHEMA'),
  'query_plan' => false !== strpos($advanced, 'def build_query_plan'),
  'non_generative' => false !== strpos($advanced, '"generative_expansion": False'),
  'filters' => false !== strpos($advanced, 'def apply_retrieval_filters'),
  'multi_query_fusion' => false !== strpos($advanced, 'advanced_query_fusion'),
  'reranking' => false !== strpos($advanced, 'transparent-rerank'),
  'dedupe' => false !== strpos($advanced, 'near-duplicate-content'),
  'diversity' => false !== strpos($advanced, 'diversity-selected'),
  'advanced_config' => false !== strpos($calibration, '"advanced"'),
  'current_profile' => false !== strpos($calibration, 'advanced-v8.4.0'),
  'legacy_profile_retained' => false !== strpos($calibration, 'balanced-v6.5.0'),
  'typed_filters' => false !== strpos($models, 'class RetrievalFilters(BaseModel)'),
  'plan_endpoint' => false !== strpos($backend, '@app.post("/v1/retrieval/plan"'),
  'advanced_explain' => false !== strpos($backend, 'advanced_retrieve_with_diagnostics'),
  'manifest_release' => isset($manifest['release']) && '8.4.0' === $manifest['release'],
  'core_boundary' => !empty($manifest['governance']['platform_core_governs_evidence']),
);
$failed = array_keys(array_filter($checks, static fn($ok) => !$ok));
if ($failed) { fwrite(STDERR, 'FAILED: ' . implode(', ', $failed) . PHP_EOL); exit(1); }
echo 'PASS: Research Librarian v8.4.0 advanced retrieval + reranking contract.' . PHP_EOL;
