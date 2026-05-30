# macOS-Simple-KVM
Documentation to set up a simple macOS VM in QEMU, accelerated by KVM.

By [@FoxletFox](https://twitter.com/foxletfox), and the help of many others. Find this useful? You can donate [on Coinbase](https://commerce.coinbase.com/checkout/96dc5777-0abf-437d-a9b5-a78ae2c4c227) or [Paypal!](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=QFXXKKAB2B9MA&item_name=macOS-Simple-KVM).

New to macOS and KVM? Check [the FAQs.](docs/FAQs.md)

## Getting Started
You'll need a Linux system with `qemu` (3.1 or later), `python3`, `pip` and the KVM modules enabled. A Mac is **not** required. Some examples for different distributions:

```
sudo apt-get install qemu-system qemu-utils python3 python3-pip  # for Ubuntu, Debian, Mint, and PopOS.
sudo pacman -S qemu python python-pip            # for Arch.
sudo xbps-install -Su qemu python3 python3-pip   # for Void Linux.
sudo zypper in qemu-tools qemu-kvm qemu-x86 qemu-audio-pa python3-pip  # for openSUSE Tumbleweed
sudo dnf install qemu qemu-img python3 python3-pip # for Fedora
```

## Step 1
Run `jumpstart.sh` to download bootable installation media for macOS (internet required). The default installation uses Catalina, which is also the latest media that still uses the standalone `BaseSystem.dmg` flow expected by this project. You can choose a bootable Simple-KVM recovery image with `--latest-compatible`, `--catalina`, `--mojave`, or `--high-sierra`. For example:
```
./jumpstart.sh --latest-compatible
```

For Tahoe, Apple uses the newer Docker-OSX-style full-installer path instead of a standalone `BaseSystem.dmg`. Download Tahoe's `InstallAssistant.pkg` from Apple's software update catalog with:
```
./jumpstart.sh --tahoe
```
That writes the package under `tools/FetchMacOS/InstallAssistant/`; it does not create `BaseSystem.img`.
> Note: You can skip this if you already have `BaseSystem.img` downloaded. If you have `BaseSystem.dmg`, you will need to convert it with the `dmg2img` tool.

## Step 2
Run the installer VM:
```
./basic.sh install
```

If `vol.qcow2` does not exist yet, `basic.sh install` creates a 200G qcow2 disk automatically. This is intentionally larger than the old 64G default so there is room for Tahoe and Xcode. If an older `vol.qcow2` already exists, it will keep using that file.

Choose `Catalina (latest compatible)` when prompted. Tahoe's `InstallAssistant.pkg` is not directly bootable by this repo, so install Catalina first, then upgrade from inside macOS.

Remember to partition the disk in Disk Utility first.

## Step 2a (Upgrade to Tahoe)
After Catalina is installed and booted, serve the Tahoe installer package from the Linux host:
```
cd tools/FetchMacOS/InstallAssistant
python3 -m http.server 8000
```

Inside the macOS VM, open Safari and download:
```
http://10.0.2.2:8000/InstallAssistant.pkg
```

Open `InstallAssistant.pkg` in macOS. It installs `Install macOS Tahoe.app` into `/Applications`. Open that app to upgrade the VM to Tahoe.

## Step 2b (Virtual Machine Manager)
1. If instead of QEMU, you'd like to import the setup into Virt-Manager for further configuration, just run `sudo ./make.sh --add`.
2. After running the above command, add `vol.qcow2` as storage in the properties of the newly added entry for VM.

## Step 2c (Headless Systems)
If you're using a cloud-based/headless system, you can use `headless.sh` to set up a quick VNC instance. Settings are defined through variables as seen in the following example. VNC will start on port `5900` by default.
```
HEADLESS=1 MEM=1G CPUS=2 SYSTEM_DISK=vol.qcow2 ./headless.sh
```

## Step 3

You're done!

To fine-tune the system and improve performance, look in the `docs` folder for more information on [adding memory](docs/guide-performance.md), setting up [bridged networking](docs/guide-networking.md), adding [passthrough hardware (for GPUs)](docs/guide-passthrough.md), tweaking [screen resolution](docs/guide-screen-resolution.md), and enabling sound features.
