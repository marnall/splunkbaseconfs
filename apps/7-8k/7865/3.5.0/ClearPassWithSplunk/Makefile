# Current version get it from app.conf file
CURRENT_VERSION := 3.5.0

SOURCE_DIR := ClearPassWithSplunk

OUTPUT_FILE := $(SOURCE_DIR)-$(CURRENT_VERSION).tar.gz

# Environment variable
export COPYFILE_DISABLE=true

all: $(OUTPUT_FILE)

# tar.gz archive
$(OUTPUT_FILE):
	tar -czvf $(OUTPUT_FILE) --exclude="local" --exclude="metadata/local.meta" --exclude="default/addon_builder.conf" --exclude=".DS_Store" $(SOURCE_DIR)

# Clean up
clean:
	rm -f $(OUTPUT_FILE)

.PHONY: clean
