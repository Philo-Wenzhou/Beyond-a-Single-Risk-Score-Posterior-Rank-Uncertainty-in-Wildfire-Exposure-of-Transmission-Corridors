$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = "C:\anaconda3\python.exe"

Push-Location $Project
try {
  & $Python "scripts_v2\00_audit_project.py"
  & $Python "scripts_v2\01_build_support_aligned_covariates.py"
  & $Python "scripts_v2\02_build_temporal_process_features.py"
  & $Python "scripts_v2\03_assign_spatial_blocks.py"
  & $Python "scripts_v2\04_build_v2_model_table.py"
  & $Python "scripts_v2\05_fit_model_ladder.py"
  & $Python "scripts_v2\06_fit_hierarchical_bayesian.py"
  & $Python "scripts_v2\07_validate_v2_models.py"
  & $Python "scripts_v2\08_analyze_decision_stability.py"
  & $Python "scripts_v2\09_make_v2_figures.py"
  & $Python "scripts_v2\10_make_v2_tables.py"
  & $Python "scripts_v2\11_compile_v2_manuscript.py"
} finally {
  Pop-Location
}
