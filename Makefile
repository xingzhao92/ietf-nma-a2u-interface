# Makefile for IETF Draft: draft-zhao-nmop-nma-a2u-framework

DRAFT = draft-zhao-nmop-nma-a2u-framework
VERSION = 00
XML = $(DRAFT)-$(VERSION).xml
BUILD_DIR = build

# Output formats
TXT = $(BUILD_DIR)/$(DRAFT)-$(VERSION).txt
HTML = $(BUILD_DIR)/$(DRAFT)-$(VERSION).html
PDF = $(BUILD_DIR)/$(DRAFT)-$(VERSION).pdf

.PHONY: all text html pdf clean validate

all: $(TXT) $(HTML)

text: $(TXT)

html: $(HTML)

pdf: $(PDF)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(TXT): $(XML) | $(BUILD_DIR)
	xml2rfc --text $< --out $@

$(HTML): $(XML) | $(BUILD_DIR)
	xml2rfc --html $< --out $@

$(PDF): $(XML) | $(BUILD_DIR)
	xml2rfc --pdf $< --out $@

validate: $(XML)
	xml2rfc --v3 $< --out /dev/null

clean:
	rm -rf $(BUILD_DIR)

# Extract YANG modules from XML to yang/ directory
extract-yang: $(XML)
	@echo "YANG modules are maintained separately in yang/ directory"
	@echo "Run 'make sync-yang' to update XML from yang/ files"

# Validate YANG modules
validate-yang:
	@for f in yang/*.yang; do 		echo "Validating $$f..."; 		pyang --ietf $$f || exit 1; 	done

help:
	@echo "Available targets:"
	@echo "  make all          - Generate text and HTML outputs"
	@echo "  make text         - Generate text output only"
	@echo "  make html         - Generate HTML output only"
	@echo "  make pdf          - Generate PDF output only"
	@echo "  make validate     - Validate XML structure"
	@echo "  make validate-yang - Validate YANG modules with pyang"
	@echo "  make clean        - Remove generated files"
