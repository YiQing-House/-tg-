import os
import shutil
import zipfile

def create_deploy_package():
    source_dir = os.getcwd()
    output_zip = os.path.join(source_dir, "TelegramVault_Deploy.zip")
    
    # Files/Dirs to include
    include_files = [
        "bot.py", "config.py", "database.py", "requirements.txt",
        "deploy.md", "README.md", "LICENSE", ".env",
        "fix_peer.py", "fix_type.py", # Useful scripts
        "rclone_115_guide.md"
    ]
    
    include_dirs = [
        "handlers", "services"
    ]
    
    # Glob patterns for dynamic files
    import glob
    sessions = glob.glob("*.session")
    session_journals = glob.glob("*.session-journal")
    dbs = glob.glob("*.db")
    
    all_files = include_files + sessions + session_journals + dbs
    
    print(f"Creating package: {output_zip}")
    
    ROOT_DIR = "TelegramPrivateVault"
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add files
        for f in all_files:
            if os.path.exists(f):
                print(f"Adding file: {f}")
                # Prepend ROOT_DIR to arcname
                zipf.write(f, arcname=os.path.join(ROOT_DIR, f))
            else:
                print(f"Skipping missing: {f}")
        
        # Add dirs
        for d in include_dirs:
            if os.path.exists(d):
                print(f"Adding dir: {d}")
                for root, _, files in os.walk(d):
                    if "__pycache__" in root:
                        continue
                    for file in files:
                        if file.endswith(".pyc"):
                            continue
                        file_path = os.path.join(root, file)
                        # Relative path from source_dir
                        rel_path = os.path.relpath(file_path, source_dir)
                        # Prepend ROOT_DIR
                        arcname = os.path.join(ROOT_DIR, rel_path)
                        print(f"  -> {arcname}")
                        zipf.write(file_path, arcname=arcname)
    
    print("✅ Package created successfully!")

if __name__ == "__main__":
    create_deploy_package()
