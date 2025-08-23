# Test script to verify the Windows build setup
# This script simulates the build process without actually running Nuitka

Write-Host "Testing Windows Build Setup..."

# Create test build directory structure
Write-Host "Creating test build structure..."
if (Test-Path "build") {
    Remove-Item -Path "build" -Recurse -Force
}
if (Test-Path "dist") {
    Remove-Item -Path "dist" -Recurse -Force
}

New-Item -ItemType Directory -Path "build" -Force | Out-Null
New-Item -ItemType Directory -Path "dist" -Force | Out-Null

# Create mock build outputs
Write-Host "Creating mock build outputs..."
"Mock single-file executable" | Out-File -FilePath "build/main_onefile.exe" -Encoding UTF8
"Mock multi-file executable" | Out-File -FilePath "build/main_multifile.exe" -Encoding UTF8
New-Item -ItemType Directory -Path "build/main_multifile.dist" -Force | Out-Null
"Mock library file 1" | Out-File -FilePath "build/main_multifile.dist/lib1.dll" -Encoding UTF8
"Mock library file 2" | Out-File -FilePath "build/main_multifile.dist/lib2.dll" -Encoding UTF8

# Test package preparation logic (simulating what the GitHub Actions workflow does)
Write-Host "Testing package preparation..."

# Handle single-file build
if (Test-Path "build/main_onefile.exe") {
    Write-Host "✓ Moving 'build/main_onefile.exe' to 'dist/ClaudeWarp.exe'"
    Move-Item "build/main_onefile.exe" "dist/ClaudeWarp.exe"
} else {
    Write-Host "✗ Single-file output not found!"
}

# Handle multi-file build
if (Test-Path "build/main_multifile.exe") {
    Write-Host "✓ Creating multi-file distribution package..."
    New-Item -ItemType Directory -Path "dist/multifile" -Force | Out-Null
    Move-Item "build/main_multifile.exe" "dist/multifile/ClaudeWarp.exe"
    
    if (Test-Path "build/main_multifile.dist") {
        Write-Host "✓ Moving distribution files..."
        Copy-Item -Path "build/main_multifile.dist/*" -Destination "dist/multifile/" -Recurse
    }
} else {
    Write-Host "✗ Multi-file output not found!"
}

# Test package creation logic
Write-Host "Testing package creation..."
$version = "test"
$arch = "x64"

# Create single-file package
if (Test-Path "dist/ClaudeWarp.exe") {
    $zip_name = "ClaudeWarp-$version-windows-$arch-onefile.zip"
    Set-Location "dist"
    Compress-Archive -Path "ClaudeWarp.exe" -DestinationPath "../$zip_name" -Force
    Set-Location ".."
    Write-Host "✓ Single-file package created: $zip_name"
}

# Create multi-file package
if (Test-Path "dist/multifile") {
    $zip_name = "ClaudeWarp-$version-windows-$arch-multifile.zip"
    Set-Location "dist"
    Compress-Archive -Path "multifile/*" -DestinationPath "../$zip_name" -Force
    Set-Location ".."
    Write-Host "✓ Multi-file package created: $zip_name"
}

# Show final results
Write-Host ""
Write-Host "=== Test Results ==="
Write-Host "Created packages:"
Get-ChildItem -Path "." -Filter "*.zip" | ForEach-Object {
    $sizeKB = [math]::Round($_.Length / 1KB, 2)
    Write-Host "  $($_.Name) - $($sizeKB) KB"
}

Write-Host ""
Write-Host "Distribution structure:"
if (Test-Path "dist") {
    Get-ChildItem -Path "dist" -Recurse | ForEach-Object {
        $relativePath = $_.FullName.Replace((Get-Location).Path, "").TrimStart('\')
        Write-Host "  $relativePath"
    }
}

Write-Host ""
Write-Host "✅ Test completed successfully!"