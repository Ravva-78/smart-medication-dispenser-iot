import subprocess
import os
from pathlib import Path
from collections import defaultdict

# 1. Get all tracked files in git
res_tracked = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, check=True)
tracked = [f.strip() for f in res_tracked.stdout.strip().split('\n') if f.strip()]

# 2. Get all untracked but non-ignored files
res_status = subprocess.run(['git', 'status', '--porcelain', '-uall'], capture_output=True, text=True, check=True)
untracked = []
for line in res_status.stdout.strip().split('\n'):
    if not line.strip():
        continue
    code = line[:2]
    fname = line[3:].strip().strip('"')
    if code in ('??', 'A ', 'AM', 'M ', 'MM'):
        untracked.append(fname)

all_files = set(tracked + untracked)

folder_sizes = defaultdict(int)
folder_counts = defaultdict(int)
file_details = []
total_size = 0

for fpath_str in all_files:
    p = Path(fpath_str)
    if p.is_file():
        sz = p.stat().st_size
        total_size += sz
        parts = p.parts
        top_folder = parts[0] if len(parts) > 1 else 'root_files'
        folder_sizes[top_folder] += sz
        folder_counts[top_folder] += 1
        file_details.append((fpath_str, sz))

file_details.sort(key=lambda x: x[1], reverse=True)

print("=" * 65)
print("             GITHUB PUSH FILE SIZE ANALYSIS")
print("=" * 65)
print(f"Total Files to Push : {len(file_details)}")
print(f"Total Repository Size: {total_size / (1024*1024):.2f} MB ({total_size / 1024:.1f} KB)\n")

print("-" * 65)
print(f"{'DIRECTORY / FOLDER':<28} | {'SIZE (MB)':<10} | {'FILES':<8}")
print("-" * 65)
for folder, sz in sorted(folder_sizes.items(), key=lambda x: x[1], reverse=True):
    mb = sz / (1024*1024)
    print(f"{folder:<28} | {mb:8.2f} MB | {folder_counts[folder]:<8}")
print("-" * 65)

print("\n" + "=" * 65)
print("             TOP 25 LARGEST FILES TO BE PUSHED")
print("=" * 65)
print(f"{'FILE PATH':<48} | {'SIZE':<12}")
print("-" * 65)
for fpath_str, sz in file_details[:25]:
    mb = sz / (1024*1024)
    kb = sz / 1024
    if mb >= 1.0:
        size_str = f"{mb:6.2f} MB"
    else:
        size_str = f"{kb:6.1f} KB"
    print(f"{fpath_str:<48} | {size_str:<12}")
print("-" * 65)

# GitHub Limits Check
print("\n" + "=" * 65)
print("             GITHUB REPOSITORY LIMITS AUDIT")
print("=" * 65)
over_50mb = [f for f in file_details if f[1] > 50 * 1024 * 1024]
over_100mb = [f for f in file_details if f[1] > 100 * 1024 * 1024]

if over_100mb:
    print(f"🚨 CRITICAL WARNING: {len(over_100mb)} file(s) exceed GitHub 100MB hard limit!")
    for f, s in over_100mb:
        print(f"   - {f} ({s/(1024*1024):.2f} MB)")
elif over_50mb:
    print(f"⚠️ WARNING: {len(over_50mb)} file(s) exceed GitHub 50MB soft warning limit.")
    for f, s in over_50mb:
        print(f"   - {f} ({s/(1024*1024):.2f} MB)")
else:
    print("✅ All individual files are well below GitHub's 100MB limit.")

if total_size / (1024*1024) < 500:
    print(f"✅ Total repository size ({total_size / (1024*1024):.2f} MB) is well within GitHub recommended repo limit (< 1-2 GB).")
