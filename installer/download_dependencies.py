import subprocess
import os
import sys
import webbrowser

def install_comfyui(target_dir: str):
    print("Installing ComfyUI inside project root...")
    comfy_dir = os.path.join(target_dir, "ComfyUI")
    if os.path.exists(comfy_dir):
        print("[!] ComfyUI directory already exists. Skipping clone.")
    else:
        try:
            print("[+] Cloning ComfyUI repository...")
            subprocess.check_call(["git", "clone", "https://github.com/comfyanonymous/ComfyUI", comfy_dir])
            print("✓ ComfyUI repo cloned.")
        except Exception as e:
            print(f"[-] Failed cloning ComfyUI repo: {str(e)}")
            return False

    # Create subfolders inside ComfyUI
    subfolders = ["models", "workflows", "custom_nodes", "input", "output"]
    for f in subfolders:
        os.makedirs(os.path.join(comfy_dir, f), exist_ok=True)
    print("✓ Created ComfyUI folder structures.")
    return True

def prompt_optional_downloads():
    print("\n=================== OPTIONAL MODEL DOWNLOADS ===================")
    print("AI Model files are large (2GB - 20GB). Downloading them automatically is not recommended.")
    print("We will open the official HuggingFace / download pages for you to download them manually.")
    print("==================================================================")
    
    choice = input("Would you like to open model download pages? (Y/N): ").strip().lower()
    if choice == 'y':
        models = {
            "1. SDXL Base Checkpoint (Stability AI)": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0",
            "2. Flux.1 Schnell Checkpoint (Black Forest Labs)": "https://huggingface.co/black-forest-labs/FLUX.1-schnell",
            "3. RealESRGAN Upscaler Model": "https://github.com/xinntao/Real-ESRGAN/releases",
            "4. CogVideoX Text-To-Video model": "https://huggingface.co/THUDM/CogVideoX-2b"
        }
        for name, url in models.items():
            print(f"  [+] Opening link for: {name}")
            webbrowser.open(url)
            
if __name__ == "__main__":
    base_proj_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "NovaStudioAI"))
    
    # Check if user wants ComfyUI installed
    comfy_choice = input("Do you want to install ComfyUI locally? (Y/N): ").strip().lower()
    if comfy_choice == 'y':
        install_comfyui(base_proj_dir)
        
    prompt_optional_downloads()
