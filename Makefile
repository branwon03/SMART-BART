.PHONY: run-cli batch-label resize-images install-file-picker-deps

run-cli:
	python3 src/nemotron_cli.py

batch-label:
ifndef DATASET
	$(error DATASET is required. Usage: make batch-label DATASET="path/to/images")
endif
	python3 src/batch_label.py "$(DATASET)" -o "$(or $(OUTPUT),labels.json)" $(if $(DELAY),--delay $(DELAY),) $(if $(DESC),-d "$(DESC)",)

resize-images:
ifndef DATASET
	$(error DATASET is required. Usage: make resize-images DATASET="path/to/images")
endif
	python3 src/resize_images.py "$(DATASET)" $(if $(OUTPUT),-o "$(OUTPUT)",)

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
