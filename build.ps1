# MIT License
#
# Copyright (c) 2026 Kevin Thomas
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Author:  Kevin Thomas
# Email:   kevin@mytechnotalent.com
# GitHub:  https://github.com/mytechnotalent/encryption-c-rp2350
# File:    build.ps1
# Desc:    Builds the Pico firmware using detected local SDK/tool paths and Visual Studio host tools.
# Created: 2026

param(
	[string]$PicoSdkPath = $env:PICO_SDK_PATH,
	[string]$CmakePath,
	[string]$NinjaPath,
	[string]$Board = 'pico2',
	[string]$Platform = 'rp2350-arm-s',
	[string]$BuildDir = 'build',
	[switch]$Clean
)

$ErrorActionPreference = 'Stop'

function Get-DefaultToolPath {
	param(
		[string]$CommandName,
		[string[]]$Fallbacks
	)
	$command = Get-Command $CommandName -ErrorAction SilentlyContinue
	if ($null -ne $command) {
		return $command.Source
	}
	foreach ($candidate in $Fallbacks) {
		if ([string]::IsNullOrWhiteSpace($candidate)) {
			continue
		}
		if (Test-Path $candidate) {
			return $candidate
		}
	}
	return $null
}

function Require-Path {
	param(
		[string]$PathValue,
		[string]$Description
	)
	if ([string]::IsNullOrWhiteSpace($PathValue) -or -not (Test-Path $PathValue)) {
		throw "$Description not found: $PathValue"
	}
}

function Import-BatchEnvironment {
	param([string]$BatchFile)
	Require-Path $BatchFile 'Visual Studio environment script'
	$output = cmd.exe /c "call \"$BatchFile\" >nul && set"
	if ($LASTEXITCODE -ne 0) {
		throw "Failed to import Visual Studio environment from $BatchFile"
	}
	foreach ($line in $output) {
		$parts = $line -split '=', 2
		if ($parts.Count -eq 2) {
			[System.Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
		}
	}
}

$userHome = [Environment]::GetFolderPath('UserProfile')

if ([string]::IsNullOrWhiteSpace($PicoSdkPath)) {
	$PicoSdkPath = Join-Path $userHome '.pico-sdk\sdk\2.2.0'
}

if ([string]::IsNullOrWhiteSpace($CmakePath)) {
	$CmakePath = Get-DefaultToolPath 'cmake.exe' @(
		(Join-Path $userHome '.pico-sdk\cmake\v3.31.5\bin\cmake.exe')
	)
}

if ([string]::IsNullOrWhiteSpace($NinjaPath)) {
	$NinjaPath = Get-DefaultToolPath 'ninja.exe' @(
		(Join-Path $userHome '.pico-sdk\ninja\v1.12.1\ninja.exe')
	)
}

$vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
Require-Path $vswhere 'vswhere.exe'

$vsInstallPath = & $vswhere -latest -products * -property installationPath
if ([string]::IsNullOrWhiteSpace($vsInstallPath)) {
	throw 'Visual Studio Build Tools installation not found.'
}

$vcvars = Join-Path $vsInstallPath 'VC\Auxiliary\Build\vcvars64.bat'

Require-Path $PicoSdkPath 'Pico SDK path'
Require-Path $CmakePath 'CMake executable'
Require-Path $NinjaPath 'Ninja executable'

if ($Clean -and (Test-Path $BuildDir)) {
	Remove-Item -Recurse -Force $BuildDir
}

Import-BatchEnvironment $vcvars
$env:PICO_SDK_PATH = $PicoSdkPath

Write-Host "Using Pico SDK: $PicoSdkPath"
Write-Host "Using CMake: $CmakePath"
Write-Host "Using Ninja: $NinjaPath"
Write-Host "Configuring build in: $BuildDir"

& $CmakePath -S . -B $BuildDir -G Ninja -DCMAKE_MAKE_PROGRAM=$NinjaPath -DPICO_BOARD=$Board -DPICO_PLATFORM=$Platform
if ($LASTEXITCODE -ne 0) {
	throw 'CMake configure failed.'
}

& $CmakePath --build $BuildDir
if ($LASTEXITCODE -ne 0) {
	throw 'CMake build failed.'
}
