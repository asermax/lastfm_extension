#!/bin/bash

################################ USAGE #######################################

usage=$(
cat <<EOF
Usage:
$0 [OPTION]
-h                      show this message.
-l, --local             install the plugin locally (default).
-g, --global            install the plugin globally.
--fingerprint-support   install needed libraries for fingerprint support


EOF
)

########################### OPTIONS PARSING #################################

#parse options
TMP=`getopt --name=$0 -a --longoptions=local,global,help,fingerprint-support -o l,g,h -- $@`

if [[ $? == 1 ]]
then
    echo
    echo "$usage"
    exit
fi

eval set -- $TMP

until [[ $1 == -- ]]; do
    case $1 in
        -l|--local)
            LOCAL=true
            ;;
        -g|--global)
            LOCAL=false
            ;;
        --fingerprint-support)
            FINGERPRINT=true
            ;;
        -h|--help)
            echo "$usage"
            exit
            ;;
    esac
    shift # move the arg list to the next option or '--'
done
shift # remove the '--', now $1 positioned at first argument if any

#default values
LOCAL=${LOCAL:=true}
FINGERPRINT=${FINGERPRINT:=false}

########################## START INSTALLATION ################################

#define constants
SCRIPT_NAME=`basename "$0"`
SCRIPT_PATH=${0%`basename "$0"`}
MATCHER="matcher.py"

#install the plugin; the install path depends on the install mode
if [[ $LOCAL == true ]]
then
    echo "Installing plugin locally"
    PLUGIN_PATH="/home/${USER}/.local/share/rhythmbox/plugins/lastfm_extension/"
    
    #build the dirs
    mkdir -p $PLUGIN_PATH

    #copy the files
    cp -r "${SCRIPT_PATH}"* "$PLUGIN_PATH"
    
    #make the matcher executable
    chmod +x "${PLUGIN_PATH}${MATCHER}"

    #remove the install script from the dir (not needed)
    rm "${PLUGIN_PATH}${SCRIPT_NAME}"
else
    echo "Installing plugin globally(admin password needed)"
    PLUGIN_PATH="/usr/lib/rhythmbox/plugins/lastfm_extension/"
    
    #build the dirs
    sudo mkdir -p $PLUGIN_PATH

    #copy the files
    sudo cp -r "${SCRIPT_PATH}"* "$PLUGIN_PATH"
    
    #make the matcher executable
    sudo chmod +x "${PLUGIN_PATH}${MATCHER}"

    #remove the install script from the dir (not needed)
    sudo rm "${PLUGIN_PATH}${SCRIPT_NAME}"        
fi

#try to install pylastfp
if [[ $FINGERPRINT == true ]]
then
    echo -n "Installing libraries needed for fingerprint support... "
    sudo apt-get install python-pip libfftw3-dev libsamplerate0-dev > /dev/null 2>&1 && pip install pylastfp > /dev/null 2>&1
    
    if [[ $? == 0 ]]
    then
        echo "Done"
    else
        echo "Failed"
    fi
fi

echo "Finished installing the plugin. Enjoy :]"

