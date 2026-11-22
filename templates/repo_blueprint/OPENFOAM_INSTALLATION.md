# OpenFOAM v2412 Installation Guide

`RocketCFD` uses **OpenFOAM v2412** (OpenCFD `openfoam.com` release) for 3D RANS/CFD meshing (`blockMesh`, `snappyHexMesh`) and flow solving (`simpleFoam`, `rhoSimpleFoam`). Install OpenFOAM using the steps for your operating system below, then launch the `RocketCFD` desktop app.

---

## Windows (Recommended: WSL2 + Ubuntu 24.04 LTS)

OpenFOAM runs inside Windows Subsystem for Linux 2 (WSL2) while `RocketCFD` connects automatically from the Windows desktop interface:

1. Open **PowerShell as Administrator** and install Ubuntu 24.04 on WSL2:
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
   Restart Windows if prompted, then open Ubuntu 24.04 from the Start menu and create your Linux username and password.
2. Inside the **Ubuntu 24.04 WSL2** terminal, add the official OpenCFD APT repository and install `openfoam2412-default`:
   ```bash
   curl -s https://dl.openfoam.com/add-debian-repo.sh | sudo bash
   sudo apt-get update
   sudo apt-get install -y openfoam2412-default
   ```
3. Configure `~/.bashrc` to source OpenFOAM automatically (checking both standard package prefixes `/usr/lib/openfoam/openfoam2412` and `/opt/openfoam2412`):
   ```bash
   BASHRC=$(ls /usr/lib/openfoam/openfoam2412/etc/bashrc /opt/openfoam2412/etc/bashrc 2>/dev/null | head -n1)
   echo "source $BASHRC" >> ~/.bashrc
   source "$BASHRC"
   ```
4. Verify installation in WSL2:
   ```bash
   simpleFoam -help
   ```
5. In `RocketCFD`, select **WSL2 (Ubuntu-24.04)** as the solver backend.

---

## Linux (Ubuntu 22.04 / 24.04 LTS & Debian Native)

1. Add the official OpenCFD APT repository and install `openfoam2412-default`:
   ```bash
   curl -s https://dl.openfoam.com/add-debian-repo.sh | sudo bash
   sudo apt-get update
   sudo apt-get install -y openfoam2412-default
   ```
2. Add the environment script to `~/.bashrc`:
   ```bash
   BASHRC=$(ls /usr/lib/openfoam/openfoam2412/etc/bashrc /opt/openfoam2412/etc/bashrc 2>/dev/null | head -n1)
   echo "source $BASHRC" >> ~/.bashrc
   source "$BASHRC"
   ```
3. Verify with `simpleFoam -help`, then select **Native Linux** in `RocketCFD`.

---

## macOS (Apple Silicon & Intel via Docker Desktop)

1. Install and start [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/).
2. Pull the multi-architecture OpenFOAM v2412 container image (`arm64` + `amd64`):
   ```bash
   docker pull microfluidica/openfoam:2412
   ```
3. Test the container in Terminal:
   ```bash
   docker run --rm microfluidica/openfoam:2412 simpleFoam -help
   ```
4. In `RocketCFD`, select **Docker Container (`microfluidica/openfoam:2412`)** as the solver backend.

---

## Related Documentation

- [Project Overview](../README.md)
- [Desktop Installation Guide](INSTALLATION.md)
- [User Guide](USER_GUIDE.md)
- [Validation Reference](VALIDATION.md)
- [Developer Guide](DEVELOPMENT.md)
- [Developer uv Installation](UV_INSTALLATION.md)
- [Security Policy](../SECURITY.md)
