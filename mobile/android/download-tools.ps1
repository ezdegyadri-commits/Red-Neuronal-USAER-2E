param([switch]$AndroidSdkTermsAccepted)
$ErrorActionPreference = 'Stop'
if (-not $AndroidSdkTermsAccepted) { throw 'The owner must first accept https://developer.android.com/studio/terms; then use -AndroidSdkTermsAccepted' }
$toolsRoot = Join-Path $PSScriptRoot 'toolchain'
New-Item -ItemType Directory -Path $toolsRoot -Force | Out-Null
# Download/use of the Android SDK is permitted only after the owner accepts
# https://developer.android.com/studio/terms. No license acceptance is automated.
$packages = @(
    @{ Name='jdk'; Url='https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.20.1%2B1/OpenJDK17U-jdk_x64_windows_hotspot_17.0.20.1_1.zip'; Algorithm='SHA256'; Hash='e53a79c3c3d86865bd7e787903884331068e71321714ffd44f145785affc7cb0' },
    @{ Name='platform'; Url='https://dl.google.com/android/repository/platform-35_r02.zip'; Algorithm='SHA1'; Hash='0bb560a90a7a2cbd0dd8348224d518b638fe7949' },
    @{ Name='build-tools'; Url='https://dl.google.com/android/repository/build-tools_r35_windows.zip'; Algorithm='SHA1'; Hash='af059bb67cf7786f45ee0db85e2d24985df1b4b6' }
)
foreach ($package in $packages) {
    $zip = Join-Path $toolsRoot ($package.Name + '.zip')
    if (-not (Test-Path -LiteralPath $zip)) {
        Write-Output ('Downloading official ' + $package.Name)
        Invoke-WebRequest -Uri $package.Url -OutFile $zip
    }
    if ((Get-FileHash -LiteralPath $zip -Algorithm $package.Algorithm).Hash.ToLowerInvariant() -ne $package.Hash) { throw 'Download checksum mismatch' }
    $folder = Join-Path $toolsRoot $package.Name
    if (-not (Test-Path -LiteralPath $folder)) {
        Expand-Archive -LiteralPath $zip -DestinationPath $folder
    }
    Write-Output ($package.Name + ' verified and extracted')
}
