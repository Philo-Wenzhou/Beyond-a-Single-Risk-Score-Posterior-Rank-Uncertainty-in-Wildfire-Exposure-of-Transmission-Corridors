@echo off
setlocal
set PROJECT=%~dp0
set PYTHON=C:\anaconda3\python.exe
pushd "%PROJECT%"

"%PYTHON%" "scripts_v2\00_audit_project.py" || goto :error
"%PYTHON%" "scripts_v2\01_build_support_aligned_covariates.py" || goto :error
"%PYTHON%" "scripts_v2\02_build_temporal_process_features.py" || goto :error
"%PYTHON%" "scripts_v2\03_assign_spatial_blocks.py" || goto :error
"%PYTHON%" "scripts_v2\04_build_v2_model_table.py" || goto :error
"%PYTHON%" "scripts_v2\05_fit_model_ladder.py" || goto :error
"%PYTHON%" "scripts_v2\06_fit_hierarchical_bayesian.py" || goto :error
"%PYTHON%" "scripts_v2\07_validate_v2_models.py" || goto :error
"%PYTHON%" "scripts_v2\08_analyze_decision_stability.py" || goto :error
"%PYTHON%" "scripts_v2\09_make_v2_figures.py" || goto :error
"%PYTHON%" "scripts_v2\10_make_v2_tables.py" || goto :error
"%PYTHON%" "scripts_v2\11_compile_v2_manuscript.py" || goto :error

popd
exit /b 0

:error
popd
exit /b 1
