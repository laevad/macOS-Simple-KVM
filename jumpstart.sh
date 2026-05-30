#!/bin/bash

# jumpstart.sh: Fetches macOS installer media.
# by Foxlet <foxlet@furcode.co>

TOOLS=$PWD/tools

print_usage() {
    echo
    echo "Usage: $0"
    echo
    echo " -s, --high-sierra   Fetch High Sierra media."
    echo " -m, --mojave        Fetch Mojave media."
    echo " -c, --catalina      Fetch Catalina media."
    echo " -l, --latest-compatible"
    echo "                    Fetch the latest BaseSystem-compatible media (Catalina)."
    echo " -v, --ventura       Check Ventura media availability."
    echo " -t, --tahoe         Fetch Tahoe InstallAssistant.pkg media."
    echo
}

error() {
    local error_message="$*"
    echo "${error_message}" 1>&2;
}

argument="$1"
case $argument in
    -h|--help)
        print_usage
        exit 0
        ;;
    -s|--high-sierra)
        "$TOOLS/FetchMacOS/fetch.sh" -v 10.13 || exit 1;
        ;;
    -m|--mojave)
        "$TOOLS/FetchMacOS/fetch.sh" -v 10.14 || exit 1;
        ;;
    -v|--ventura)
        "$TOOLS/FetchMacOS/fetch.sh" -v 13 || exit 1;
        ;;
    -t|--tahoe)
        "$TOOLS/FetchMacOS/fetch.sh" -v 26 -k InstallAssistant.pkg -o InstallAssistant || exit 1;
        echo
        echo "Downloaded Tahoe InstallAssistant.pkg to tools/FetchMacOS/InstallAssistant/."
        echo "Tahoe uses Docker-OSX's modern full-installer flow, so no BaseSystem.img was created."
        exit 0
        ;;
    -l|--latest-compatible)
        "$TOOLS/FetchMacOS/fetch.sh" -v 10.15 || exit 1;
        ;;
    -c|--catalina|*)
        "$TOOLS/FetchMacOS/fetch.sh" -v 10.15 || exit 1;
        ;;
esac

if [[ ! -e "$TOOLS/FetchMacOS/BaseSystem/BaseSystem.dmg" ]]; then
        error "No BaseSystem.dmg was downloaded."
        error "This project needs a standalone BaseSystem.dmg; use --latest-compatible for Catalina."
        exit 1
fi

"$TOOLS/dmg2img" "$TOOLS/FetchMacOS/BaseSystem/BaseSystem.dmg" "$PWD/BaseSystem.img"
