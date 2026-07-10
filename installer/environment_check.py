import sys
import os
import shutil
import platform
import psutil
import subprocess

def probe_hardware_environment() -> dict:
    """Gathers OS parameters, CPU, RAM and GPU drivers details."""
    stats = {}
    
    # 1. OS & CPU
    stats["os"] = f"{platform.system()} {platform.release()}"
    stats["cpu"] = platform.processor()
    
    # 2. RAM capacity
    ram = psutil.virtual_memory()
    stats["ram_total_gb"] = round(ram.total / (1024**3), 2)
    stats["ram_available_gb"] = round(ram.available / (1024**3), 2)
    
    # 3. Disk space
    disk = shutil.disk_usage(".")
    stats["disk_free_gb"] = round(disk.free / (1024**3), 2)
    
    # 4. GPU & CUDA
    gpu_name = "CPU Only"
    gpu_vram = 0.0
    cuda_detected = False
    cuda_version = "None"
    
    try:
        # Check NVIDIA Driver via nvidia-smi
        output = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], text=True)
        parts = output.strip().split(",")
        if len(parts) >= 2:
            gpu_name = parts[0].strip()
            gpu_vram = round(float(parts[1].strip()) / 1024.0, 2)
            cuda_detected = True
    except Exception:
        pass
        
    try:
        # Check nvcc for compiler cuda version
        nvcc_out = subprocess.check_output(["nvcc", "--version"], text=True)
        for line in nvcc_out.splitlines():
            if "release" in line:
                cuda_version = line.split("release")[-1].strip().split(",")[0]
                break
    except Exception:
        pass
        
    stats["gpu_name"] = gpu_name
    stats["gpu_vram_gb"] = gpu_vram
    stats["cuda_detected"] = cuda_detected
    stats["cuda_version"] = cuda_version
    
    return stats

def print_recommendation(stats: dict):
    print("=================== ENVIRONMENT CHECK ===================")
    print(f"OS: {stats['os']}")
    print(f"RAM: {stats['ram_total_gb']} GB (Available: {stats['ram_available_gb']} GB)")
    print(f"Disk Free: {stats['disk_free_gb']} GB")
    print(f"GPU: {stats['gpu_name']} (VRAM: {stats['gpu_vram_gb']} GB)")
    print(f"CUDA Version: {stats['cuda_version']}")
    print("=========================================================")
    
    # Recommendations
    if stats["ram_total_gb"] < 16.0:
        print("[WARNING] System RAM is under 16GB. Low-end models may experience slowdowns.")
    else:
        print("[OK] System RAM is optimal.")
        
    if stats["gpu_vram_gb"] < 8.0:
        print("[WARNING] GPU VRAM is under 8GB. Recommend enabling 'low_vram' mode inside configurations.")
    else:
        print("[OK] Dedicated GPU is optimal for SDXL/SVD operations.")
        
    if stats["disk_free_gb"] < 20.0:
        print("[WARNING] Available disk space is low (under 20GB). Download of model files will fail.")
    else:
        print("[OK] Disk space capacity is sufficient.")

if __name__ == "__main__":
    stats = probe_hardware_environment()
    print_recommendation(stats)
