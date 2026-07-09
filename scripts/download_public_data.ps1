param(
    [string]$OutDir = "data/raw",
    [string]$StartYear = "2017",
    [string]$EndYear = "2023"
)

$ErrorActionPreference = "Stop"

function New-DataDir {
    param([string]$Path)
    if (!(Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

function Download-File {
    param(
        [string]$Url,
        [string]$OutFile
    )
    Write-Host "Downloading $Url"
    Invoke-WebRequest -Uri $Url -OutFile $OutFile -Headers @{"User-Agent"="Mozilla/5.0"}
}

function New-QueryString {
    param([hashtable]$Params)
    return (($Params.GetEnumerator() | ForEach-Object {
        [uri]::EscapeDataString($_.Key) + "=" + [uri]::EscapeDataString([string]$_.Value)
    }) -join "&")
}

function Download-ArcGisGeoJson {
    param(
        [string]$BaseQueryUrl,
        [hashtable]$BaseParams,
        [string]$OutFile,
        [int]$PageSize = 2000
    )

    if (Test-Path -LiteralPath $OutFile) {
        Write-Host "Exists: $OutFile"
        return
    }

    $countParams = $BaseParams.Clone()
    $countParams["f"] = "json"
    $countParams["returnCountOnly"] = "true"
    $countUri = $BaseQueryUrl + "?" + (New-QueryString -Params $countParams)
    $countResponse = Invoke-RestMethod -Uri $countUri -Headers @{"User-Agent"="Mozilla/5.0"}
    $total = [int]$countResponse.count
    Write-Host "Downloading $total features from $BaseQueryUrl"

    $features = New-Object System.Collections.ArrayList
    for ($offset = 0; $offset -lt $total; $offset += $PageSize) {
        $queryParams = $BaseParams.Clone()
        $queryParams["f"] = "geojson"
        $queryParams["outFields"] = "*"
        $queryParams["returnGeometry"] = "true"
        $queryParams["outSR"] = "4326"
        $queryParams["resultOffset"] = $offset
        $queryParams["resultRecordCount"] = $PageSize
        $uri = $BaseQueryUrl + "?" + (New-QueryString -Params $queryParams)
        Write-Host "  page offset=$offset"
        $page = Invoke-RestMethod -Uri $uri -Headers @{"User-Agent"="Mozilla/5.0"}
        if ($null -ne $page.features) {
            foreach ($feature in $page.features) {
                [void]$features.Add($feature)
            }
        }
    }

    $collection = [ordered]@{
        type = "FeatureCollection"
        name = [System.IO.Path]::GetFileNameWithoutExtension($OutFile)
        features = $features
    }
    $collection | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $OutFile -Encoding UTF8
}

New-DataDir $OutDir
New-DataDir "$OutDir/boundaries"
New-DataDir "$OutDir/cec"
New-DataDir "$OutDir/hifld"
New-DataDir "$OutDir/calfire"
New-DataDir "$OutDir/census"
New-DataDir "$OutDir/metadata"

# US county boundaries. California counties are filtered during preprocessing.
$countyZip = "$OutDir/census/tl_2024_us_county.zip"
if (!(Test-Path -LiteralPath $countyZip)) {
    Download-File `
        -Url "https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/tl_2024_us_county.zip" `
        -OutFile $countyZip
}

# California Energy Commission transmission lines, canonical receptor layer.
$cecGeoJson = "$OutDir/cec/california_electric_transmission_lines.geojson"
Download-ArcGisGeoJson `
    -BaseQueryUrl "https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/Transmission_Line/FeatureServer/2/query" `
    -BaseParams @{
        where = "1=1"
        orderByFields = "OBJECTID"
    } `
    -OutFile $cecGeoJson

# HIFLD transmission lines from the public ArcGIS FeatureServer.
# The HIFLD Hub file-export endpoint returned HTTP 403 in this environment, so
# the reproducible path uses the underlying public FeatureServer.
$hifldGeoJson = "$OutDir/hifld/electric_power_transmission_lines.geojson"
Download-ArcGisGeoJson `
    -BaseQueryUrl "https://services2.arcgis.com/LYMgRMwHfrWWEg3s/arcgis/rest/services/HIFLD_US_Electric_Power_Transmission_Lines/FeatureServer/0/query" `
    -BaseParams @{
        where = "1=1"
        geometry = "-125,32,-113,43"
        geometryType = "esriGeometryEnvelope"
        inSR = "4326"
        spatialRel = "esriSpatialRelIntersects"
        orderByFields = "OBJECTID_1"
    } `
    -OutFile $hifldGeoJson

# CAL FIRE historical fire perimeters for the default study period.
$firePerimetersGeoJson = "$OutDir/calfire/california_historic_fire_perimeters_${StartYear}_${EndYear}.geojson"
Download-ArcGisGeoJson `
    -BaseQueryUrl "https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services/California_Historic_Fire_Perimeters/FeatureServer/0/query" `
    -BaseParams @{
        where = "YEAR_ >= $StartYear AND YEAR_ <= $EndYear"
        orderByFields = "OBJECTID"
    } `
    -OutFile $firePerimetersGeoJson

# A lightweight manifest records the intended study window.
$manifest = [ordered]@{
    project = "Bayesian_Wildfire_Exposure_CA"
    downloaded_at = (Get-Date).ToString("s")
    default_region = "California"
    start_year = $StartYear
    end_year = $EndYear
    notes = "HIFLD is bbox-filtered to California and should be clipped to the California county boundary during preprocessing. Large meteorology and LANDFIRE rasters are pulled after fixing the exact subregion."
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$OutDir/metadata/download_manifest.json" -Encoding UTF8

Write-Host "Initial public-data download complete."
