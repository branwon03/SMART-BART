.PHONY: run-cli install-file-picker-deps

run-cli:
	python3 nemotron_cli.py

install-file-picker-deps:
	@if command -v pacman >/dev/null 2>&1; then \
		sudo pacman -S --needed zenity kdialog; \
	elif command -v apt-get >/dev/null 2>&1; then \
		sudo apt-get update && sudo apt-get install -y zenity kdialog; \
	elif command -v dnf >/dev/null 2>&1; then \
		sudo dnf install -y zenity kdialog; \
	elif command -v zypper >/dev/null 2>&1; then \
		sudo zypper install -y zenity kdialog; \
	elif command -v brew >/dev/null 2>&1; then \
		brew install zenity; \
	else \
		echo "Unsupported package manager. Please install zenity and/or kdialog manually."; \
		exit 1; \
	fi
