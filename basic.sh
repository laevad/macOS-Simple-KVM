#!/bin/bash

OSK="ourhardworkbythesewordsguardedpleasedontsteal(c)AppleComputerInc"
VMDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OVMF=$VMDIR/firmware
#export QEMU_AUDIO_DRV=pa
#QEMU_AUDIO_DRV=pa

echo $VMDIR
if [[ "$EUID" != 0 && $1 == "vfio" ]]; then
    echo "Please run as root"
    exit 1
fi

if [[ $1 == "vfio" ]]; then
    modprobe vfio-pci
    if [[ $2 == '2' ]]; then
        host="00:14.0"
        BIND_PID1="8086 8c31"
    elif [[ $2 == '3' ]]; then
        host="03:00.3"
        BIND_PID1="1022 1639"
    elif [[ $2 == '4' ]]; then
        host="00:14.0"
        BIND_PID1="8086 51ed"
    else
        host="00:14.0"
        BIND_PID1="8086 9d2f"
        BIND_PID2="8086 9d31"
        BIND_BDF2="0000:00:14.2"
    fi
    BIND_BDF1="0000:$host"
    echo "$BIND_PID1" > /sys/bus/pci/drivers/vfio-pci/new_id
    echo "$BIND_BDF1" > /sys/bus/pci/devices/$BIND_BDF1/driver/unbind
    echo "$BIND_BDF1" > /sys/bus/pci/drivers/vfio-pci/bind
    echo "$BIND_PID1" > /sys/bus/pci/drivers/vfio-pci/remove_id
    if [[ -n $BIND_BDF2 && -n $BIND_PID2 ]]; then
        echo "$BIND_PID2" > /sys/bus/pci/drivers/vfio-pci/new_id
        echo "$BIND_BDF2" > /sys/bus/pci/devices/$BIND_BDF2/driver/unbind
        echo "$BIND_BDF2" > /sys/bus/pci/drivers/vfio-pci/bind
        echo "$BIND_PID2" > /sys/bus/pci/drivers/vfio-pci/remove_id
    fi
    extra="-device vfio-pci,host=$host"
elif [[ $1 == "install" ]]; then
    [[ ! -e vol.qcow2 ]] && qemu-img create -f qcow2 vol.qcow2 200G
    if [[ ! $(ls BaseSystem*) ]]; then
        select opt in "Catalina (latest compatible)" "Ventura" "Mojave" "High Sierra"; do
            selection=$opt
            [[ -n $selection ]] && break
        done
        case $selection in
            "Catalina (latest compatible)" ) ./jumpstart.sh --latest-compatible;;
            "Ventura" )                      ./jumpstart.sh --ventura;;
            "Mojave" )                       ./jumpstart.sh --mojave;;
            "High Sierra" )                  ./jumpstart.sh --high-sierra;;
        esac
    fi
    extra="-drive id=InstallMedia,format=raw,if=none,file=$VMDIR/BaseSystem.img \
           -device ide-hd,bus=sata.3,drive=InstallMedia"
elif [[ $1 == "custom" ]]; then
    extra="$2"
fi

if [[ ! -e $VMDIR/firmware/OVMF_VARS-1024x768.fd ]]; then
    curl -L https://github.com/foxlet/macOS-Simple-KVM/raw/master/firmware/OVMF_VARS-1024x768.fd -o firmware/OVMF_VARS-1024x768.fd
fi

TOTAL_RAM_KB=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
VM_RAM_GB=$((TOTAL_RAM_KB / 1024 / 1024 / 2))

TOTAL_CPUS=$(nproc --all)
VM_CPUS=$((TOTAL_CPUS / 2))

if (( VM_CPUS < 2 )); then
    VM_CPUS=2
fi

if (( VM_CPUS % 2 == 0 )); then
    VM_THREADS=2
    VM_CORES=$((VM_CPUS / 2))
else
    VM_THREADS=1
    VM_CORES=$VM_CPUS
fi

echo "Using RAM: ${VM_RAM_GB}G"
echo "Using CPU: ${VM_CPUS} threads"

qemu-system-x86_64 \
    -enable-kvm \
    -m "${VM_RAM_GB}G" \
    -machine q35,accel=kvm \
    -smp "$VM_CPUS",cores="$VM_CORES",threads="$VM_THREADS",sockets=1 \
    -cpu Penryn,vendor=GenuineIntel,kvm=on,+sse3,+sse4.2,+aes,+xsave,+avx,+xsaveopt,+xsavec,+xgetbv1,+avx2,+bmi2,+smep,+bmi1,+fma,+movbe,+invtsc \
    -device isa-applesmc,osk="$OSK" \
    -smbios type=2 \
    -drive if=pflash,format=raw,readonly=on,file="$OVMF/OVMF_CODE.fd" \
    -drive if=pflash,format=raw,file="$OVMF/OVMF_VARS-1024x768.fd" \
    -vga qxl \
    -display gtk,zoom-to-fit=off \
    -global qxl-vga.vram_size_mb=128 -global qxl-vga.ram_size_mb=128 \
    -device ich9-intel-hda -device hda-output \
    -usb -device usb-kbd -device usb-tablet \
    -netdev user,id=net0,hostfwd=tcp::5555-:22,hostfwd=tcp::5900-:5900 \
    -device e1000-82545em,netdev=net0,id=net0,mac=52:54:00:c9:18:27 \
    -device ich9-ahci,id=sata \
    -drive id=ESP,if=none,format=qcow2,file=$VMDIR/OpenCore-nopicker.qcow2 \
    -device ide-hd,bus=sata.2,drive=ESP \
    -drive id=SystemDisk,if=none,file=$VMDIR/vol.qcow2 \
    -device ide-hd,bus=sata.4,drive=SystemDisk \
    $extra

if [[ $1 == "vfio" ]]; then
    echo "$BIND_BDF1" > /sys/bus/pci/drivers/vfio-pci/unbind
    echo "$BIND_BDF1" > /sys/bus/pci/drivers/xhci_hcd/bind
    [[ -n $BIND_BDF2 ]] && echo "$BIND_BDF2" > /sys/bus/pci/drivers/vfio-pci/unbind
fi
