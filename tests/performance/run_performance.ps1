# Performance Test Runner for Windows PowerShell
# This script provides easy access to DataMapper performance testing

param(
    [string]$Action = "run",  # run, baseline, compare, help
    [string]$TestFile = "",   # Specific test file to run
    [switch]$Verbose = $false # Enable verbose output
)

# Configuration
$PythonExe = "C:/Program Files (x86)/Python3.13/python.exe"
$ProjectRoot = $PSScriptRoot + "\..\..\"
$PerformanceDir = $PSScriptRoot
$TestRunner = Join-Path $PerformanceDir "run_performance_tests.py"

function Show-Help {
    Write-Host "DataMapper Performance Test Runner" -ForegroundColor Green
    Write-Host "=================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\run_performance.ps1 [Action] [Options]" 
    Write-Host ""
    Write-Host "Actions:" -ForegroundColor Yellow
    Write-Host "  run       - Run performance tests (default)"
    Write-Host "  baseline  - Run tests and save as new baseline"  
    Write-Host "  compare   - Compare current performance with baseline"
    Write-Host "  help      - Show this help message"
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -TestFile <file>  - Run specific test file only"
    Write-Host "  -Verbose          - Enable verbose output"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Cyan
    Write-Host "  .\run_performance.ps1                    # Run all performance tests"
    Write-Host "  .\run_performance.ps1 baseline           # Establish performance baseline"  
    Write-Host "  .\run_performance.ps1 compare            # Check for regression"
    Write-Host "  .\run_performance.ps1 run -Verbose       # Run with detailed output"
}

function Test-Prerequisites {
    # Check Python executable
    if (-not (Test-Path $PythonExe)) {
        Write-Error "Python executable not found: $PythonExe"
        Write-Host "Please update the `$PythonExe variable in this script" -ForegroundColor Yellow
        return $false
    }
    
    # Check test runner script
    if (-not (Test-Path $TestRunner)) {
        Write-Error "Test runner not found: $TestRunner"
        return $false
    }
    
    # Check project structure
    if (-not (Test-Path (Join-Path $ProjectRoot "xml_extractor"))) {
        Write-Error "xml_extractor package not found. Run from correct directory."
        return $false
    }
    
    return $true
}

function Invoke-PerformanceTests {
    param([string]$Mode, [string]$SpecificTest)
    
    Write-Host "Starting DataMapper Performance Tests" -ForegroundColor Green
    Write-Host "Mode: $Mode" -ForegroundColor Cyan
    
    # Change to project root directory
    Push-Location $ProjectRoot
    
    try {
        # Build Python command arguments
        $PythonArgs = @($TestRunner)
        
        if ($Mode -eq "baseline") {
            $PythonArgs += "--save-baseline"
        } elseif ($Mode -eq "compare") {
            $PythonArgs += "--compare-only"
        }
        
        if ($SpecificTest) {
            $PythonArgs += "--test-file", $SpecificTest
        }
        
        if ($Verbose) {
            Write-Host "Command: & `"$PythonExe`" $($PythonArgs -join ' ')" -ForegroundColor Gray
        }
        
        # Execute performance tests
        $ExitCode = 0
        & $PythonExe @PythonArgs
        $ExitCode = $LASTEXITCODE
        
        # Report results
        if ($ExitCode -eq 0) {
            Write-Host "Performance tests completed successfully" -ForegroundColor Green
        } else {
            Write-Host "Performance tests failed (Exit Code: $ExitCode)" -ForegroundColor Red
        }
        
        return $ExitCode
    }
    catch {
        Write-Error "Error running performance tests: $_"
        return 1
    }
    finally {
        Pop-Location
    }
}

function Show-PerformanceResults {
    $ResultsDir = Join-Path $PerformanceDir "performance_results"
    
    if (Test-Path $ResultsDir) {
        Write-Host "Performance Results Location:" -ForegroundColor Cyan
        Write-Host "  Directory: $ResultsDir"
        
        $HistoryFile = Join-Path $ResultsDir "performance_history.json"
        $BaselineFile = Join-Path $ResultsDir "performance_baseline.json"
        
        if (Test-Path $HistoryFile) {
            $FileSize = (Get-Item $HistoryFile).Length
            Write-Host "  History: performance_history.json ($FileSize bytes)"
        }
        
        if (Test-Path $BaselineFile) {
            $FileSize = (Get-Item $BaselineFile).Length  
            Write-Host "  Baseline: performance_baseline.json ($FileSize bytes)"
        }
    } else {
        Write-Host "No performance results found yet" -ForegroundColor Yellow
        Write-Host "   Run tests first to generate results"
    }
}

# Main execution logic
switch ($Action.ToLower()) {
    "help" {
        Show-Help
        exit 0
    }
    "run" {
        if (-not (Test-Prerequisites)) { exit 1 }
        $ExitCode = Invoke-PerformanceTests -Mode "run" -SpecificTest $TestFile
        Show-PerformanceResults
        exit $ExitCode
    }
    "baseline" {
        if (-not (Test-Prerequisites)) { exit 1 }
        Write-Host "Establishing Performance Baseline" -ForegroundColor Yellow
        $ExitCode = Invoke-PerformanceTests -Mode "baseline" -SpecificTest $TestFile
        Show-PerformanceResults
        exit $ExitCode
    }
    "compare" {
        if (-not (Test-Prerequisites)) { exit 1 }
        Write-Host "Comparing with Baseline" -ForegroundColor Yellow
        $ExitCode = Invoke-PerformanceTests -Mode "compare" -SpecificTest $TestFile
        Show-PerformanceResults
        exit $ExitCode
    }
    default {
        Write-Error "Unknown action: $Action"
        Write-Host "Use 'help' for usage information" -ForegroundColor Yellow
        exit 1
    }
}