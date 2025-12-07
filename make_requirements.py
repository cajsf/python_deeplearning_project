import pkg_resources

used_packages = [
    "fastapi",
    "uvicorn",
    "torch",
    "ultralytics",
    "opencv-python",
    "pillow",
    "mysql-connector-python",
    "python-multipart",
    "requests",
    "google-generativeai"
]

installed = {pkg.key: pkg.version for pkg in pkg_resources.working_set}

with open("requirements.txt", "w", encoding="utf-8") as f:
    for pkg in used_packages:
        if pkg in installed:
            f.write(f"{pkg}=={installed[pkg]}\n")

print("✅ requirements.txt 생성 완료")
