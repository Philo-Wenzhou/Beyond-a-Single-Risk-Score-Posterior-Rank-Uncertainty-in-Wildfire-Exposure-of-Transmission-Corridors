$ErrorActionPreference = "Stop"
$env:PATH = "C:\rtools45\x86_64-w64-mingw32.static.posix\bin;" + $env:PATH
$CmdStan = "F:\Rprogram\WeiPHD\.cmdstan_local\cmdstan-2.38.0"
$Make = "C:\rtools45\usr\bin\make.exe"
$Model = "E:\WPSDrive\198731884\WPS云盘\2026 申请\Bayesian_Wildfire_Exposure_CA\data_model\v2\stan\hier_logit_block_year.stan"
$Exe = "E:\WPSDrive\198731884\WPS云盘\2026 申请\Bayesian_Wildfire_Exposure_CA\data_model\v2\stan\hier_logit_block_year.exe"
$Data = "E:\WPSDrive\198731884\WPS云盘\2026 申请\Bayesian_Wildfire_Exposure_CA\data_model\v2\stan\hier_logit_block_year_train.json"
& $Make -C $CmdStan "E:/WPSDrive/198731884/WPS云盘/2026 申请/Bayesian_Wildfire_Exposure_CA/data_model/v2/stan/hier_logit_block_year"
New-Item -ItemType Directory -Force -Path "data_model/v2/stan/chains" | Out-Null
for ($chain = 1; $chain -le 4; $chain++) {
  $seed = 20260708 + $chain
  & $Exe sample num_warmup=500 num_samples=500 save_warmup=0 thin=1 adapt delta=0.95 data file=$Data random seed=$seed output file="data_model/v2/stan/chains/hier_logit_block_year_chain${chain}.csv"
}
