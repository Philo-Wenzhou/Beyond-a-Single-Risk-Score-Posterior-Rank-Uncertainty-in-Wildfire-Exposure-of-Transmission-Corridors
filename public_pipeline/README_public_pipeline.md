# Public Wildfire–Transmission Line Exposure Experiment

这套脚本用于构建一个**完全公开数据、可复现**的输电线路野火暴露验证数据集，并输出第一批地图和统计图。

核心数据：

1. CAL FIRE / FRAP historical fire perimeters
2. California Energy Commission electric transmission lines
3. US Census California counties
4. 后续可扩展 LANDFIRE、gridMET、DEM

## 0. 安装

```bash
cd public_wildfire_line_exposure
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

## 1. 下载公开矢量数据

```bash
python scripts/01_download_public_vectors.py
```

如果在线接口失败，请手动下载以下文件并放入 `data_raw/`：

- `data_raw/calfire_fire_perimeters_all.geojson`
- `data_raw/cec_transmission_lines.geojson`
- `data_raw/ca_counties.geojson`

## 2. 预处理 + 第一批地图/统计图

```bash
python scripts/02_prepare_and_make_initial_figures.py
```

输出：

- `figures/fig01_california_overview.png`
- `figures/fig02_study_area_map.png`
- `figures/fig03_fire_counts_by_year_cause.png`
- `figures/fig04_burned_acres_by_year_cause.png`
- `figures/fig05_exogenous_fire_map.png`
- `figures/fig06_electrical_power_fire_map.png`
- `tables/table01_cause_summary_2017_2023.csv`
- `tables/table02_top_electrical_power_fires.csv`

## 3. 构建线路段与暴露标签

```bash
python scripts/03_build_segment_exposure_labels.py
```

输出：

- `data_processed/segments_1km.gpkg`
- `data_processed/segment_buffers_1000m.gpkg`
- `data_processed/segment_year_labels_1km_1000m.parquet`
- `tables/table03_label_summary_1km_1000m.csv`

## 4. 画标签对比图

```bash
python scripts/04_make_label_figures.py
```

输出：

- `figures/fig07_label_comparison_segment_count.png`
- `figures/fig08_label_comparison_segment_length.png`

## 5. 一键运行

```bash
python scripts/run_all_public_vectors.py
```

## 重要边界

本项目公开验证的是：

> 线路段作为线性基础设施受体，对历史火场边界的空间暴露。

不是：

- 电力线路真实致火概率
- 设备故障概率
- 停电概率
- 法律责任归因
- 内部业务系统准确率
