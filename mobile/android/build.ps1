$ErrorActionPreference = 'Stop'
$toolsRoot = Join-Path $PSScriptRoot 'toolchain'
$jdkRoot = (Get-ChildItem -LiteralPath (Join-Path $toolsRoot 'jdk') -Directory | Select-Object -First 1).FullName
$platformRoot = (Get-ChildItem -LiteralPath (Join-Path $toolsRoot 'platform') -Directory | Select-Object -First 1).FullName
$buildTools = (Get-ChildItem -LiteralPath (Join-Path $toolsRoot 'build-tools') -Directory | Select-Object -First 1).FullName
if (-not $jdkRoot -or -not $platformRoot -or -not $buildTools) { throw 'Run download-tools.ps1 first' }
$java = Join-Path $jdkRoot 'bin/java.exe'
$javac = Join-Path $jdkRoot 'bin/javac.exe'
$jar = Join-Path $jdkRoot 'bin/jar.exe'
$androidJar = Join-Path $platformRoot 'android.jar'
$buildRoot = Join-Path $PSScriptRoot ('build/run-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$classes = Join-Path $buildRoot 'classes'
$dex = Join-Path $buildRoot 'dex'
$resources = Join-Path $buildRoot 'res/drawable-nodpi'
New-Item -ItemType Directory -Path $classes,$dex,$resources -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'app-icon.png') -Destination (Join-Path $resources 'app_icon.png')
function Run-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw ('Build failed: ' + [IO.Path]::GetFileName($Program)) }
}
$aapt2 = Join-Path $buildTools 'aapt2.exe'
$resourceZip = Join-Path $buildRoot 'resources.zip'
$unsigned = Join-Path $buildRoot 'unsigned.apk'
Run-Checked $aapt2 @('compile','--dir',(Join-Path $buildRoot 'res'),'-o',$resourceZip)
Run-Checked $aapt2 @('link','-I',$androidJar,'--manifest',(Join-Path $PSScriptRoot 'AndroidManifest.xml'),'-o',$unsigned,$resourceZip)
$sources = @(Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'src') -Recurse -Filter '*.java' | ForEach-Object { $_.FullName })
Run-Checked $javac (@('-encoding','UTF-8','-source','8','-target','8','-bootclasspath',$androidJar,'-d',$classes) + $sources)
$classesJar = Join-Path $buildRoot 'classes.jar'
Run-Checked $jar @('cf',$classesJar,'-C',$classes,'.')
Run-Checked $java @('-cp',(Join-Path $buildTools 'lib/d8.jar'),'com.android.tools.r8.D8','--release','--lib',$androidJar,'--min-api','24','--output',$dex,$classesJar)
Run-Checked $jar @('uf',$unsigned,'-C',$dex,'classes.dex')
$aligned = Join-Path $buildRoot 'aligned.apk'
Run-Checked (Join-Path $buildTools 'zipalign.exe') @('-p','-f','4',$unsigned,$aligned)

# Private signing material stays local, never in the public APK/download bundle.
# Keep both files for future updates. DPAPI protects the password for this Windows user.
$signRoot = Join-Path $PSScriptRoot '.private-signing'
$keystore = Join-Path $signRoot 'usaer02e-release.p12'
$protectedPassword = Join-Path $signRoot 'password.dpapi.xml'
New-Item -ItemType Directory -Path $signRoot -Force | Out-Null
if (Test-Path -LiteralPath $keystore) {
    if (-not (Test-Path -LiteralPath $protectedPassword)) { throw 'Signing password missing; do not replace the existing signing key' }
    $secure = Import-Clixml -LiteralPath $protectedPassword
} else {
    $random = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Fill($random)
    $secure = ConvertTo-SecureString ([Convert]::ToBase64String($random)) -AsPlainText -Force
    $secure | Export-Clixml -LiteralPath $protectedPassword
}
$env:USAER_APK_STORE_PASS = [System.Net.NetworkCredential]::new('', $secure).Password
try {
    if (-not (Test-Path -LiteralPath $keystore)) {
        Run-Checked (Join-Path $jdkRoot 'bin/keytool.exe') @('-genkeypair','-keystore',$keystore,'-storetype','PKCS12',
            '-storepass:env','USAER_APK_STORE_PASS','-alias','usaer02e','-keyalg','RSA','-keysize','3072',
            '-validity','10000','-dname','CN=USAER 02E, O=USAER 02E, C=MX')
    }
    $outputRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../output/mobile'))
    New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
    $apk = Join-Path $outputRoot 'USAER-02E-Android-1.0.0.apk'
    Run-Checked $java @('-jar',(Join-Path $buildTools 'lib/apksigner.jar'),'sign','--ks',$keystore,
        '--ks-key-alias','usaer02e','--ks-pass','env:USAER_APK_STORE_PASS','--out',$apk,$aligned)
    Run-Checked $java @('-jar',(Join-Path $buildTools 'lib/apksigner.jar'),'verify','--verbose','--print-certs',$apk)
    Run-Checked (Join-Path $buildTools 'zipalign.exe') @('-c','-v','4',$apk)
    Get-FileHash -LiteralPath $apk -Algorithm SHA256 | Select-Object Hash,Path
} finally {
    Remove-Item Env:USAER_APK_STORE_PASS
}
