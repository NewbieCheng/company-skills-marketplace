#!/bin/sh
set -eu

asset_url="${1:-https://github.com/NewbieCheng/company-skills-marketplace/releases/download/social-media-hangge-moments-v1.0.0/hangge-moments-universal-v1.0.0.zip}"
expected_sha256="${2:-BB3E1D97CE315C65520406C795E829CBF6C15176630DAFE3FF7888E41C4D297A}"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This installer currently supports macOS only. Use install_hangge_release.ps1 on Windows." >&2
  exit 1
fi

temporary_root="$(mktemp -d "${TMPDIR:-/tmp}/hangge-skill-install.XXXXXX")"
archive_path="$temporary_root/hangge-moments.zip"
expanded_path="$temporary_root/expanded"

cleanup() {
  case "$temporary_root" in
    "${TMPDIR:-/tmp}"/hangge-skill-install.*) rm -rf "$temporary_root" ;;
  esac
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$expanded_path"
echo "正在从 GitHub Release 下载航哥朋友圈授权版..."
curl --fail --location --silent --show-error \
  --user-agent "NewbieCheng-Skill-Installer" \
  "$asset_url" \
  --output "$archive_path"

actual_sha256="$(shasum -a 256 "$archive_path" | awk '{print toupper($1)}')"
expected_sha256="$(printf '%s' "$expected_sha256" | tr '[:lower:]' '[:upper:]')"
if [ "$actual_sha256" != "$expected_sha256" ]; then
  echo "BUNDLE_TAMPERED: SHA-256 校验失败。期望 $expected_sha256，实际 $actual_sha256" >&2
  exit 1
fi

unzip -q "$archive_path" -d "$expanded_path"
package_installer="$(find "$expanded_path" -type f -name '*macOS.command' -print | head -n 1)"
if [ -z "$package_installer" ]; then
  echo "RUNTIME_INCOMPATIBLE: 安装包中缺少 macOS 安装脚本" >&2
  exit 1
fi

printf '\n' | /bin/bash "$package_installer"
echo
echo "安装完成。请重启 Codex 或 Cursor，然后输入：激活航哥朋友圈"
echo "系统会返回 HGD1- 设备请求码；把它发给销售方换取本机专属 HGL1- 激活码。"
