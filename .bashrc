# If not running interactively, don't do anything
[ -z "$PS1" ] && return

# Add Homebrew to PATH (needed for M1/M2 Macs)
if [ -f /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
elif [ -f /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
fi

# Pyenv configuration
export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"

# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/Users/patrickwetherbee/opt/anaconda3/bin/conda' 'shell.bash' 'hook' 2>/dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/Users/patrickwetherbee/opt/anaconda3/etc/profile.d/conda.sh" ]; then
        . "/Users/patrickwetherbee/opt/anaconda3/etc/profile.d/conda.sh"
    else
        export PATH="/Users/patrickwetherbee/opt/anaconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

# Console Ninja configuration
PATH=~/.console-ninja/.bin:$PATH

# Aurite development environment variables
export NODE_ENV=development
export DATABASE_URL="postgresql://aurite_user:autumnBank36@localhost:5432/aurite_db"
export REDIS_URL="redis://localhost:6379"

# pnpm
export PNPM_HOME="/Users/patrickwetherbee/Library/pnpm"
case ":$PATH:" in
*":$PNPM_HOME:"*) ;;
*) export PATH="$PNPM_HOME:$PATH" ;;
esac
# pnpm end

# Add Visual Studio Code (code) to path if it exists
# This is Mac-specific path for VS Code
[[ -d "/Applications/Visual Studio Code.app/Contents/Resources/app/bin" ]] &&
    export PATH="$PATH:/Applications/Visual Studio Code.app/Contents/Resources/app/bin"
